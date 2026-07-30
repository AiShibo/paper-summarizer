from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .constants import STAGE_FILES, project_root
from .ids import normalize_title
from .manifest import build_manifest
from .validation import load_json, validate_shards


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _label_from_slug(slug: str) -> str:
    return " ".join(part.upper() if part in {"ml", "iot", "hpc", "rdma", "ebpf"} else part.title()
                    for part in slug.split("-"))


def _apply_migrations(connection: sqlite3.Connection, root: Path) -> None:
    for migration in sorted((root / "migrations").glob("[0-9][0-9][0-9]_*.sql")):
        connection.executescript(migration.read_text(encoding="utf-8"))


def _load_taxonomy(connection: sqlite3.Connection, root: Path) -> None:
    taxonomy = load_json(root / "config" / "taxonomy.v1.json")
    version = taxonomy["schema_version"]
    for track in taxonomy["tracks"]:
        connection.execute(
            "INSERT OR IGNORE INTO topic (id, label, taxonomy_version) VALUES (?, ?, ?)",
            (track["id"], track["label"], version),
        )
    for track in taxonomy["tracks"]:
        for subtopic in track["subtopics"]:
            connection.execute(
                "INSERT OR IGNORE INTO topic (id, label, taxonomy_version) VALUES (?, ?, ?)",
                (subtopic, _label_from_slug(subtopic), version),
            )
            connection.execute(
                "INSERT OR IGNORE INTO topic_parent (topic_id, parent_id) VALUES (?, ?)",
                (subtopic, track["id"]),
            )


def _insert_venue_years(
    connection: sqlite3.Connection,
    shards_root: Path,
    root: Path,
) -> None:
    manifest = build_manifest(shards_root, root)
    for item in manifest["venue_years"]:
        path = shards_root / item["venue"] / str(item["year"]) / "venue-year.json"
        if path.exists():
            record = load_json(path)
            dates = record["conference_dates"]
            counts = record["counts"]
            official_conference_url = record["official_conference_url"]
            official_program_url = record["official_program_url"]
            workflow_status = record["workflow"]["status"]
            verification = record["verification"]
            source_path = str(path)
        else:
            dates = {"start": None, "end": None}
            counts = {
                "main_track": None,
                "core_systems": None,
                "systems_adjacent": None,
                "excluded": None,
                "needs_review": None,
            }
            official_conference_url = None
            official_program_url = None
            workflow_status = item["workflow_status"]
            verification = {"last_verified_at": item["last_verified_at"]}
            source_path = item["shard"]
        connection.execute(
            """
            INSERT INTO venue_year (
                venue, year, official_conference_url, official_program_url,
                conference_start, conference_end, collection_status, workflow_status,
                main_track_count, core_systems_count, systems_adjacent_count,
                excluded_count, needs_review_count, last_verified_at, source_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["venue"],
                item["year"],
                official_conference_url,
                official_program_url,
                dates["start"],
                dates["end"],
                item["collection_status"],
                workflow_status,
                counts["main_track"],
                counts["core_systems"],
                counts["systems_adjacent"],
                counts["excluded"],
                counts["needs_review"],
                verification["last_verified_at"],
                source_path,
            ),
        )
        if path.exists():
            _insert_sources(
                connection,
                "venue-year",
                f"{item['venue']}:{item['year']}",
                "venue-year",
                record["sources"],
            )


def _insert_sources(
    connection: sqlite3.Connection,
    record_type: str,
    record_id: str,
    stage: str,
    sources: Iterable[dict[str, Any]],
) -> None:
    for source in sources:
        connection.execute(
            """
            INSERT OR IGNORE INTO source (
                id, url, kind, title, publisher, retrieved_at,
                content_hash, official, supports_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["id"],
                source["url"],
                source["kind"],
                source["title"],
                source["publisher"],
                source["retrieved_at"],
                source["content_hash"],
                int(source["official"]),
                _json(source["supports"]),
            ),
        )
        existing = connection.execute(
            "SELECT url, kind FROM source WHERE id = ?", (source["id"],)
        ).fetchone()
        if existing != (source["url"], source["kind"]):
            raise ValueError(f"Conflicting source ID {source['id']!r}")
        connection.execute(
            """
            INSERT OR IGNORE INTO record_source (record_type, record_id, stage, source_id)
            VALUES (?, ?, ?, ?)
            """,
            (record_type, record_id, stage, source["id"]),
        )


def _insert_entities(connection: sqlite3.Connection, entities_root: Path) -> None:
    if not entities_root.exists():
        return
    for path in sorted((entities_root / "institutions").glob("*.json")):
        entity = load_json(path)
        location = entity["location"]
        connection.execute(
            """
            INSERT INTO institution (
                id, normalized_name, institution_type, city, state_or_province,
                country, region, official_url, current_record_confidence,
                last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity["institution_id"],
                entity["normalized_name"],
                entity["institution_type"],
                location["city"],
                location["state_or_province"],
                location["country"],
                location["region"],
                entity["official_url"],
                entity["verification"]["confidence"],
                entity["verification"]["last_verified_at"],
            ),
        )
        _insert_sources(
            connection,
            "institution",
            entity["institution_id"],
            "entity",
            entity["sources"],
        )

    for path in sorted((entities_root / "authors").glob("*.json")):
        entity = load_json(path)
        connection.execute(
            """
            INSERT INTO author (
                id, canonical_name, orcid, identity_confidence
            ) VALUES (?, ?, ?, ?)
            """,
            (
                entity["author_id"],
                entity["display_name"],
                entity["orcid"],
                entity["verification"]["confidence"],
            ),
        )
        _insert_sources(
            connection,
            "author",
            entity["author_id"],
            "entity",
            entity["sources"],
        )

    for path in sorted((entities_root / "faculty").glob("*.json")):
        entity = load_json(path)
        location = entity["current_location"]
        recruiting = entity["recruiting"]
        connection.execute(
            """
            INSERT INTO faculty (
                id, author_id, display_name, official_profile_url,
                current_institution_id, department, faculty_rank, city,
                state_or_province, country, region, recruiting_statement,
                recruiting_source_id, confidence, last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity["faculty_id"],
                entity["author_id"],
                entity["display_name"],
                entity["official_profile_url"],
                entity["current_institution_id"],
                entity["department"],
                entity["faculty_rank"],
                location["city"],
                location["state_or_province"],
                location["country"],
                location["region"],
                recruiting["exact_statement"] if recruiting else None,
                recruiting["source_id"] if recruiting else None,
                entity["verification"]["confidence"],
                entity["verification"]["last_verified_at"],
            ),
        )
        _insert_sources(
            connection,
            "faculty",
            entity["faculty_id"],
            "entity",
            entity["sources"],
        )

    group_entities: list[dict[str, Any]] = []
    for path in sorted((entities_root / "research-groups").glob("*.json")):
        entity = load_json(path)
        group_entities.append(entity)
        connection.execute(
            """
            INSERT INTO research_group (
                id, name, official_url, institution_id, department,
                group_kind, research_topics_json, confidence, last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity["group_id"],
                entity["name"],
                entity["official_url"],
                entity["institution_id"],
                entity["department_or_division"],
                entity["group_kind"],
                _json(entity["research_topics"]),
                entity["verification"]["confidence"],
                entity["verification"]["last_verified_at"],
            ),
        )
        _insert_sources(
            connection,
            "research-group",
            entity["group_id"],
            "entity",
            entity["sources"],
        )
    for entity in group_entities:
        for faculty_id in entity["faculty_ids"]:
            connection.execute(
                """
                INSERT INTO research_group_faculty (group_id, faculty_id)
                VALUES (?, ?)
                """,
                (entity["group_id"], faculty_id),
            )


def _insert_paper(
    connection: sqlite3.Connection,
    paper_directory: Path,
) -> None:
    bundle = {filename: load_json(paper_directory / filename) for filename in STAGE_FILES}
    metadata = bundle["metadata.json"]
    relevance = bundle["relevance.json"]
    summary = bundle["summary.json"]
    groups = bundle["groups.json"]
    awards = bundle["awards.json"]
    review = bundle["review.json"]
    paper_id = metadata["paper_id"]

    connection.execute(
        """
        INSERT INTO paper (
            id, title, normalized_title, venue, year, track_or_session, paper_type,
            publication_date, page_count, venue_year_completion_status,
            relevance_class, relevance_score, relevance_rationale,
            relevance_confidence, links_json, alternate_versions_json,
            metadata_workflow_status, relevance_workflow_status, source_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_id,
            metadata["title"],
            normalize_title(metadata["title"]),
            metadata["venue"],
            metadata["year"],
            metadata["track_or_session"],
            metadata["paper_type"],
            metadata["publication_date"],
            metadata["page_count"],
            metadata["venue_year_completion_status"],
            relevance["class"],
            relevance["score"],
            relevance["rationale"],
            relevance["verification"]["confidence"],
            _json(metadata["links"]),
            _json(metadata["alternate_versions"]),
            metadata["workflow"]["status"],
            relevance["workflow"]["status"],
            str(paper_directory),
        ),
    )

    for filename, payload in bundle.items():
        _insert_sources(connection, "paper", paper_id, filename.removesuffix(".json"), payload.get("sources", []))

    for author in metadata["authors"]:
        author_id = author["author_id"]
        if author_id:
            connection.execute(
                """
                INSERT OR IGNORE INTO author (id, canonical_name, orcid)
                VALUES (?, ?, ?)
                """,
                (author_id, author["name"], author["orcid"]),
            )
        connection.execute(
            """
            INSERT INTO authorship (
                paper_id, position, author_id, name_as_published, orcid_as_published
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (paper_id, author["position"], author_id, author["name"], author["orcid"]),
        )
        for affiliation in author["affiliations"]:
            institution_id = affiliation["institution_id"]
            if institution_id:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO institution (
                        id, normalized_name, institution_type, city, state_or_province,
                        country, region
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        institution_id,
                        affiliation["normalized_name"] or affiliation["name_as_published"],
                        affiliation["institution_type"],
                        affiliation["city"],
                        affiliation["state_or_province"],
                        affiliation["country"],
                        affiliation["region"],
                    ),
                )
            connection.execute(
                """
                INSERT INTO affiliation (
                    paper_id, author_position, institution_id, name_as_published,
                    normalized_name, institution_type, city, state_or_province,
                    country, region, source_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    author["position"],
                    institution_id,
                    affiliation["name_as_published"],
                    affiliation["normalized_name"],
                    affiliation["institution_type"],
                    affiliation["city"],
                    affiliation["state_or_province"],
                    affiliation["country"],
                    affiliation["region"],
                    _json(affiliation["source_ids"]),
                ),
            )

    for topic in relevance["topics"]:
        connection.execute(
            "INSERT INTO paper_topic (paper_id, topic_id) VALUES (?, ?)", (paper_id, topic)
        )
    for layer in relevance["system_layers"]:
        connection.execute(
            "INSERT INTO paper_system_layer (paper_id, system_layer) VALUES (?, ?)",
            (paper_id, layer),
        )
    for contribution in relevance["contribution_types"]:
        connection.execute(
            """
            INSERT INTO paper_contribution_type (paper_id, contribution_type)
            VALUES (?, ?)
            """,
            (paper_id, contribution),
        )
    for method in relevance["methods"]:
        connection.execute(
            "INSERT INTO paper_method (paper_id, method) VALUES (?, ?)", (paper_id, method)
        )

    connection.execute(
        """
        INSERT INTO summary (
            paper_id, takeaway, background, villain, approach, impact,
            evaluation_json, limitations, phd_group_signal,
            beginner_concepts_json, reading_coverage_json, workflow_status,
            confidence, last_verified_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paper_id,
            summary["takeaway"],
            summary["background"],
            summary["villain"],
            summary["approach"],
            summary["impact"],
            _json(summary["evaluation"]),
            summary["limitations"],
            summary["phd_group_signal"],
            _json(summary["beginner_concepts"]),
            _json(summary["reading_coverage"]),
            summary["workflow"]["status"],
            summary["verification"]["confidence"],
            summary["verification"]["last_verified_at"],
        ),
    )
    claims = [*summary["claims"], *summary["evaluation"]["results"]]
    for claim in {item["id"]: item for item in claims}.values():
        connection.execute(
            """
            INSERT INTO summary_claim (id, paper_id, text, locator, source_ids_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (claim["id"], paper_id, claim["text"], claim["locator"], _json(claim["source_ids"])),
        )

    for association in groups["associations"]:
        connection.execute(
            """
            INSERT INTO paper_group_association (
                paper_id, group_id, faculty_id, publication_institution_id,
                current_institution_id, association_type, rationale,
                evidence_source_ids_json, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                association["group_id"],
                association["faculty_id"],
                association["publication_institution_id"],
                association["current_institution_id"],
                association["association_type"],
                association["rationale"],
                _json(association["evidence_source_ids"]),
                association["confidence"],
            ),
        )

    for award in awards["awards"]:
        connection.execute(
            """
            INSERT INTO award (
                id, paper_id, official_name, category, venue, year,
                official_source_id, last_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                award["award_id"],
                paper_id,
                award["official_name"],
                award["category"],
                award["venue"],
                award["year"],
                award["official_source_id"],
                award["last_verified_at"],
            ),
        )

    for issue in review["issues"]:
        connection.execute(
            """
            INSERT INTO review_issue (
                id, paper_id, severity, stage, description, status, reviewer
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue["issue_id"],
                paper_id,
                issue["severity"],
                issue["stage"],
                issue["description"],
                issue["status"],
                review["reviewer"],
            ),
        )


def build_database(
    shards_root: Path,
    output: Path,
    repository_root: Path | None = None,
) -> None:
    root = repository_root or project_root()
    report = validate_shards(shards_root, profile="draft", repository_root=root)
    if not report.ok:
        rendered = "\n".join(issue.render(root) for issue in report.errors)
        raise ValueError(f"Cannot build database from invalid shards:\n{rendered}")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            _apply_migrations(connection, root)
            _load_taxonomy(connection, root)
            _insert_entities(connection, shards_root.resolve().parent / "entities")
            _insert_venue_years(connection, shards_root.resolve(), root)
            for metadata_path in sorted(shards_root.resolve().rglob("metadata.json")):
                _insert_paper(connection, metadata_path.parent)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError(f"SQLite integrity check failed: {integrity}")
            connection.execute(
                """
                CREATE TABLE build_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.executemany(
                "INSERT INTO build_metadata (key, value) VALUES (?, ?)",
                [
                    ("built_at", datetime.now(UTC).isoformat(timespec="seconds")),
                    ("schema_version", "1"),
                    ("validation_profile", "draft"),
                ],
            )
            connection.commit()
        finally:
            connection.close()
        temporary.replace(output)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise
