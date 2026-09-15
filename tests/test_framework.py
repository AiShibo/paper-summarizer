from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from collectors.venues.acm_sosp import parse_candidates as parse_acm_candidates
from collectors.venues.usenix_osdi import parse_candidates as parse_usenix_candidates
from systems_phd_explorer.database import build_database
from systems_phd_explorer.export import build_site_data
from systems_phd_explorer.ids import normalize_title, paper_id
from systems_phd_explorer.manifest import build_manifest
from systems_phd_explorer.templates import initialize_paper, initialize_venue_year
from systems_phd_explorer.validation import SchemaStore, load_json, validate_shards

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class IdentifierTests(unittest.TestCase):
    def test_title_normalization_is_stable(self) -> None:
        self.assertEqual(normalize_title("A  Résumé: System!"), "a resume system")
        self.assertEqual(
            paper_id("osdi", 2025, "A Résumé: System!"),
            paper_id("osdi", 2025, "A  Resume — System"),
        )


class InitializerTests(unittest.TestCase):
    def test_venue_initializer_preserves_unknown_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shards = Path(directory) / "shards"
            path = initialize_venue_year("sosp", 2026, "test-agent", shards)
            payload = load_json(path)
            self.assertEqual(payload["collection_status"], "UNVERIFIED")
            self.assertTrue(all(value is None for value in payload["counts"].values()))

    def test_initializer_creates_stage_separated_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shards = Path(directory) / "shards"
            paper_directory = initialize_paper(
                "osdi",
                2025,
                "A Temporary Fixture",
                "test-agent",
                shards,
            )
            self.assertTrue((shards / "osdi" / "2025" / "venue-year.json").exists())
            self.assertEqual(
                {path.name for path in paper_directory.glob("*.json")},
                {
                    "metadata.json",
                    "relevance.json",
                    "summary.json",
                    "groups.json",
                    "awards.json",
                    "review.json",
                },
            )
            report = validate_shards(shards, profile="draft", repository_root=ROOT)
            self.assertTrue(report.ok, [issue.render(ROOT) for issue in report.errors])
            with self.assertRaises(FileExistsError):
                initialize_paper(
                    "osdi",
                    2025,
                    "A Temporary Fixture",
                    "test-agent",
                    shards,
                )


class ValidationTests(unittest.TestCase):
    def test_all_json_schemas_are_valid_draft_2020_12(self) -> None:
        schema_store = SchemaStore(ROOT)
        for name, document in schema_store.documents.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(document)

    def test_release_fixture_passes(self) -> None:
        report = validate_shards(
            FIXTURES / "shards",
            profile="release",
            repository_root=ROOT,
        )
        self.assertTrue(report.ok, [issue.render(ROOT) for issue in report.errors])
        self.assertEqual(report.paper_bundles_checked, 1)

    def test_committed_manifest_has_all_venue_years(self) -> None:
        schema_store = SchemaStore(ROOT)
        path = ROOT / "data" / "venue-year-manifest.json"
        payload = load_json(path)
        errors = list(
            schema_store.validator("venue-year-manifest.schema.json").iter_errors(payload)
        )
        self.assertEqual(errors, [])
        pairs = {(item["venue"], item["year"]) for item in payload["venue_years"]}
        self.assertEqual(len(pairs), 48)

    def test_generated_manifest_overrides_only_collected_shard(self) -> None:
        manifest = build_manifest(FIXTURES / "shards", ROOT)
        selected = {
            (item["venue"], item["year"]): item
            for item in manifest["venue_years"]
        }
        self.assertEqual(
            selected[("osdi", 2025)]["collection_status"],
            "COMPLETE_PROCEEDINGS",
        )
        self.assertEqual(selected[("sosp", 2025)]["collection_status"], "UNVERIFIED")


class BuildTests(unittest.TestCase):
    def test_sqlite_build_is_queryable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "database.sqlite"
            build_database(FIXTURES / "shards", output, ROOT)
            connection = sqlite3.connect(output)
            try:
                self.assertEqual(connection.execute("SELECT count(*) FROM paper").fetchone()[0], 1)
                self.assertEqual(
                    connection.execute("SELECT count(*) FROM venue_year").fetchone()[0],
                    48,
                )
                self.assertEqual(
                    connection.execute("SELECT count(*) FROM summary_claim").fetchone()[0],
                    1,
                )
                self.assertEqual(
                    connection.execute("PRAGMA integrity_check").fetchone()[0],
                    "ok",
                )
            finally:
                connection.close()

    def test_static_export_contains_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "papers.json"
            build_site_data(FIXTURES / "shards", output, ROOT)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["papers"]), 1)
            self.assertEqual(payload["papers"][0]["venue"], "osdi")
            self.assertEqual(payload["papers"][0]["authors"], ["Alice Fixture"])

    def test_static_export_carries_summary_and_review_for_the_interface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "papers.json"
            build_site_data(FIXTURES / "shards", output, ROOT)
            paper = json.loads(output.read_text(encoding="utf-8"))["papers"][0]
            self.assertIn("abstract", paper)
            self.assertEqual(paper["summary"]["status"], "APPROVED")
            self.assertTrue(paper["summary"]["background"])
            self.assertTrue(paper["summary"]["approach"])
            self.assertIsInstance(paper["summary"]["evaluation"]["results"], list)
            self.assertIsInstance(paper["summary"]["beginner_concepts"], list)
            self.assertEqual(paper["review"]["decision"], "APPROVED")
            self.assertIsInstance(paper["review"]["issues"], list)


class CollectorPilotTests(unittest.TestCase):
    def test_usenix_pilot_extracts_and_deduplicates_presentation_links(self) -> None:
        candidates = parse_usenix_candidates(
            FIXTURES / "collector" / "usenix.html",
            "https://www.usenix.org/conference/osdi25/technical-sessions",
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "A Fixture Systems Paper")
        self.assertTrue(candidates[0].human_review_required)

    def test_acm_pilot_ignores_non_title_pdf_link(self) -> None:
        candidates = parse_acm_candidates(
            FIXTURES / "collector" / "acm.html",
            "https://dl.acm.org/doi/proceedings/10.1145/1234567",
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "A Fixture ACM Systems Paper")


class CoordinationTaskTests(unittest.TestCase):
    def test_all_agent_briefs_and_ownership_entries_exist(self) -> None:
        task_directory = ROOT / "coordination" / "tasks"
        expected_briefs = {
            "coordinator": "task-00-coordinator.md",
            "agent-a": "agent-a-systems-collection.md",
            "agent-b": "agent-b-storage-networking-collection.md",
            "agent-c": "agent-c-asplos-collection.md",
            "agent-d": "agent-d-security-collection.md",
            "agent-e": "agent-e-paper-summaries.md",
            "agent-f": "agent-f-faculty-groups.md",
            "agent-g": "agent-g-awards.md",
            "agent-h": "agent-h-independent-review.md",
            "agent-i": "agent-i-frontend.md",
        }
        ownership = load_json(task_directory / "ownership.json")
        task_ids = {task["task_id"] for task in ownership["tasks"]}
        self.assertEqual(task_ids, set(expected_briefs))
        for task_id, filename in expected_briefs.items():
            with self.subTest(task=task_id):
                brief = task_directory / filename
                self.assertTrue(brief.exists())
                text = brief.read_text(encoding="utf-8")
                self.assertIn("## Paste-ready instruction", text)
                self.assertIn("## Handoff", text)


if __name__ == "__main__":
    unittest.main()
