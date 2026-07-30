from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .constants import (
    ENTITY_SCHEMA_BY_DIRECTORY,
    SCHEMA_BY_FILENAME,
    STAGE_FILES,
    SUPPORTED_YEARS,
    project_root,
)
from .ids import normalize_title

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    path: Path
    message: str

    def render(self, relative_to: Path | None = None) -> str:
        try:
            display_path = self.path.relative_to(relative_to) if relative_to else self.path
        except ValueError:
            display_path = self.path
        return f"{self.severity}: {display_path}: {self.message}"


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)
    files_checked: int = 0
    paper_bundles_checked: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "WARNING"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, severity: str, path: Path, message: str) -> None:
        self.issues.append(ValidationIssue(severity, path, message))


class DuplicateKeyError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value must be an object")
    return value


class SchemaStore:
    def __init__(self, root: Path) -> None:
        schema_directory = root / "schemas" / "v1"
        self.documents: dict[str, dict[str, Any]] = {}
        registry = Registry()
        for path in sorted(schema_directory.glob("*.schema.json")):
            document = load_json(path)
            schema_id = document.get("$id")
            if not isinstance(schema_id, str):
                raise ValueError(f"Schema lacks $id: {path}")
            self.documents[path.name] = document
            registry = registry.with_resource(schema_id, Resource.from_contents(document))
        self.registry = registry

    def validator(self, schema_filename: str) -> Draft202012Validator:
        return Draft202012Validator(
            self.documents[schema_filename],
            registry=self.registry,
            format_checker=FormatChecker(),
        )


def _json_path(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        rendered += f"[{part}]" if isinstance(part, int) else f".{part}"
    return rendered


def _schema_validate(
    path: Path,
    payload: dict[str, Any],
    schema_store: SchemaStore,
    report: ValidationReport,
) -> bool:
    schema_filename = SCHEMA_BY_FILENAME.get(path.name)
    if not schema_filename:
        return True
    validator = schema_store.validator(schema_filename)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    for error in errors:
        report.add("ERROR", path, f"{_json_path(error.absolute_path)}: {error.message}")
    return not errors


def _schema_validate_as(
    path: Path,
    payload: dict[str, Any],
    schema_filename: str,
    schema_store: SchemaStore,
    report: ValidationReport,
) -> bool:
    validator = schema_store.validator(schema_filename)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    for error in errors:
        report.add("ERROR", path, f"{_json_path(error.absolute_path)}: {error.message}")
    return not errors


def _load_for_validation(
    path: Path,
    schema_store: SchemaStore,
    report: ValidationReport,
) -> dict[str, Any] | None:
    try:
        payload = load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report.add("ERROR", path, str(exc))
        return None
    report.files_checked += 1
    return payload if _schema_validate(path, payload, schema_store, report) else None


def _known_values(root: Path) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    venues_document = load_json(root / "config" / "venues.json")
    taxonomy = load_json(root / "config" / "taxonomy.v1.json")
    venues = {item["slug"] for item in venues_document["venues"]}
    topics: set[str] = set()
    for track in taxonomy["tracks"]:
        topics.add(track["id"])
        topics.update(track["subtopics"])
    return (
        venues,
        topics,
        set(taxonomy["system_layers"]),
        set(taxonomy["contribution_types"]),
        set(taxonomy["methods"]),
    )


def _stage_source_map(
    payload: dict[str, Any],
    path: Path,
    report: ValidationReport,
) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for source in payload.get("sources", []):
        source_id = source.get("id")
        if source_id in sources:
            report.add("ERROR", path, f"duplicate source ID within stage: {source_id}")
        elif isinstance(source_id, str):
            sources[source_id] = source
    return sources


def _check_source_references(
    payload: dict[str, Any],
    path: Path,
    report: ValidationReport,
) -> None:
    sources = _stage_source_map(payload, path, report)
    referenced: list[tuple[str, str]] = []
    if path.name == "metadata.json":
        for author in payload.get("authors", []):
            for affiliation in author.get("affiliations", []):
                referenced.extend(
                    (source_id, "affiliation") for source_id in affiliation.get("source_ids", [])
                )
    elif path.name == "summary.json":
        for claim in payload.get("claims", []):
            referenced.extend(
                (source_id, f"claim {claim.get('id')}") for source_id in claim.get("source_ids", [])
            )
        for claim in payload.get("evaluation", {}).get("results", []):
            referenced.extend(
                (source_id, f"evaluation result {claim.get('id')}")
                for source_id in claim.get("source_ids", [])
            )
    elif path.name == "groups.json":
        for association in payload.get("associations", []):
            referenced.extend(
                (source_id, "group association")
                for source_id in association.get("evidence_source_ids", [])
            )
    elif path.name == "awards.json":
        referenced.extend(
            (award.get("official_source_id"), f"award {award.get('award_id')}")
            for award in payload.get("awards", [])
        )
    for source_id, context in referenced:
        if source_id not in sources:
            report.add("ERROR", path, f"{context} references missing stage source {source_id!r}")


def _check_release_stage(
    bundle: dict[str, dict[str, Any]],
    paths: dict[str, Path],
    report: ValidationReport,
) -> None:
    metadata = bundle["metadata.json"]
    relevance = bundle["relevance.json"]
    summary = bundle["summary.json"]
    groups = bundle["groups.json"]
    awards = bundle["awards.json"]
    review = bundle["review.json"]

    if metadata["workflow"]["status"] != "APPROVED":
        report.add("ERROR", paths["metadata.json"], "release requires metadata workflow APPROVED")
    if metadata["paper_type"] == "unknown":
        report.add("ERROR", paths["metadata.json"], "release requires a resolved paper_type")
    if not metadata["authors"]:
        report.add("ERROR", paths["metadata.json"], "release requires published-order authors")
    if not metadata["sources"]:
        report.add("ERROR", paths["metadata.json"], "release requires metadata sources")

    if relevance["workflow"]["status"] != "APPROVED":
        report.add("ERROR", paths["relevance.json"], "release requires relevance workflow APPROVED")
    if relevance["class"] == "NEEDS_HUMAN_REVIEW":
        report.add("ERROR", paths["relevance.json"], "release relevance cannot need human review")
    if not relevance["rationale"].strip():
        report.add("ERROR", paths["relevance.json"], "release requires a relevance rationale")

    included = relevance["class"] in {"CORE_SYSTEMS", "SYSTEMS_ADJACENT"}
    if included:
        for field_name in ("topics", "system_layers", "contribution_types", "methods"):
            if not relevance[field_name]:
                report.add(
                    "ERROR",
                    paths["relevance.json"],
                    f"included release paper requires at least one {field_name}",
                )
        if summary["workflow"]["status"] != "APPROVED":
            report.add("ERROR", paths["summary.json"], "included release paper needs APPROVED summary")
        required_text = (
            "takeaway",
            "background",
            "villain",
            "approach",
            "impact",
            "limitations",
            "phd_group_signal",
        )
        for field_name in required_text:
            value = summary.get(field_name)
            if not isinstance(value, str) or not value.strip():
                report.add("ERROR", paths["summary.json"], f"release summary requires {field_name}")
        takeaway = summary.get("takeaway") or ""
        if len(re.findall(r"\b[\w'-]+\b", takeaway)) > 35:
            report.add("ERROR", paths["summary.json"], "takeaway exceeds 35 words")
        concept_count = len(summary.get("beginner_concepts", []))
        if not 3 <= concept_count <= 8:
            report.add("ERROR", paths["summary.json"], "release needs 3–8 beginner concepts")
        official_pdf_available = bool(metadata["links"].get("official_pdf"))
        for section, state in summary["reading_coverage"].items():
            if official_pdf_available and state != "READ":
                report.add(
                    "ERROR",
                    paths["summary.json"],
                    f"full paper is available but reading_coverage.{section} is {state}",
                )
        if not official_pdf_available and summary["reading_coverage"]["abstract"] == "NOT_READ":
            report.add("ERROR", paths["summary.json"], "release summary must at least read the abstract")

    if included and groups["workflow"]["status"] != "APPROVED":
        report.add("ERROR", paths["groups.json"], "included release paper needs APPROVED group resolution")
    for association in groups.get("associations", []):
        if association["association_type"] != "unresolved" and not association["evidence_source_ids"]:
            report.add("ERROR", paths["groups.json"], "resolved PI/group association lacks evidence")
        if association["association_type"] != "unresolved":
            sources = _stage_source_map(groups, paths["groups.json"], report)
            for source_id in association["evidence_source_ids"]:
                if source_id in sources and not sources[source_id]["official"]:
                    report.add(
                        "ERROR",
                        paths["groups.json"],
                        f"group evidence source {source_id!r} is not marked official",
                    )

    if awards["workflow"]["status"] != "APPROVED":
        report.add(
            "ERROR",
            paths["awards.json"],
            "release requires award checking to be APPROVED, even when awards is empty",
        )
    award_sources = _stage_source_map(awards, paths["awards.json"], report)
    if not any(
        source["official"] and source["kind"] == "award-page"
        for source in award_sources.values()
    ):
        report.add(
            "ERROR",
            paths["awards.json"],
            "approved award check requires an official award-page source",
        )
    for award in awards.get("awards", []):
        source = award_sources.get(award["official_source_id"])
        if source and (not source["official"] or source["kind"] != "award-page"):
            report.add(
                "ERROR",
                paths["awards.json"],
                f"award {award['award_id']!r} lacks an official award-page source",
            )

    if review["decision"] != "APPROVED" or review["workflow"]["status"] != "APPROVED":
        report.add("ERROR", paths["review.json"], "release requires independent APPROVED review")
    stage_owners = {
        payload["workflow"].get("owner")
        for payload in (metadata, relevance, summary, groups, awards)
        if payload["workflow"].get("owner")
    }
    if review.get("reviewer") in stage_owners:
        report.add("ERROR", paths["review.json"], "stage owner cannot approve their own work")
    missing_independence = sorted(stage_owners - set(review["independent_from"]))
    if missing_independence:
        report.add(
            "ERROR",
            paths["review.json"],
            f"independent_from omits stage owners: {missing_independence}",
        )
    if included:
        for check, passed in review["checks"].items():
            if passed is not True:
                report.add("ERROR", paths["review.json"], f"release review check {check!r} did not pass")
    open_errors = [
        issue
        for issue in review.get("issues", [])
        if issue["severity"] == "ERROR" and issue["status"] == "OPEN"
    ]
    if open_errors:
        report.add("ERROR", paths["review.json"], "release has open ERROR review issues")


def _validate_entities(
    entities_root: Path,
    profile: str,
    schema_store: SchemaStore,
    topics: set[str],
    report: ValidationReport,
) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {
        "authors": set(),
        "faculty": set(),
        "research-groups": set(),
        "institutions": set(),
    }
    payloads: dict[str, list[tuple[dict[str, Any], Path]]] = {
        key: [] for key in ids
    }
    if not entities_root.exists():
        return ids

    for directory_name, (schema_filename, id_field) in ENTITY_SCHEMA_BY_DIRECTORY.items():
        directory = entities_root / directory_name
        for path in sorted(directory.glob("*.json")):
            try:
                payload = load_json(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                report.add("ERROR", path, str(exc))
                continue
            report.files_checked += 1
            if not _schema_validate_as(path, payload, schema_filename, schema_store, report):
                continue
            entity_id = payload.get(id_field)
            if isinstance(entity_id, str):
                if path.stem != entity_id:
                    report.add(
                        "ERROR",
                        path,
                        f"{id_field} {entity_id!r} does not match filename {path.stem!r}",
                    )
                if entity_id in ids[directory_name]:
                    report.add("ERROR", path, f"duplicate entity ID {entity_id!r}")
                ids[directory_name].add(entity_id)
            _check_source_references(payload, path, report)
            payloads[directory_name].append((payload, path))

    for payload, path in payloads["faculty"]:
        if payload.get("author_id") not in ids["authors"]:
            report.add("ERROR", path, f"faculty references missing author {payload.get('author_id')!r}")
        if payload.get("current_institution_id") not in ids["institutions"]:
            report.add(
                "ERROR",
                path,
                f"faculty references missing institution {payload.get('current_institution_id')!r}",
            )
        unknown_topics = sorted(set(payload.get("research_topics", [])) - topics)
        if unknown_topics:
            report.add("ERROR", path, f"unknown faculty research topics: {unknown_topics}")
        recruiting = payload.get("recruiting")
        if recruiting:
            source_ids = {source["id"] for source in payload.get("sources", [])}
            if recruiting["source_id"] not in source_ids:
                report.add("ERROR", path, "recruiting statement references a missing source")
            elif profile == "release":
                source = next(
                    source for source in payload["sources"] if source["id"] == recruiting["source_id"]
                )
                if not source["official"]:
                    report.add("ERROR", path, "recruiting statement source is not official")

    for payload, path in payloads["research-groups"]:
        institution_id = payload.get("institution_id")
        if institution_id and institution_id not in ids["institutions"]:
            report.add("ERROR", path, f"group references missing institution {institution_id!r}")
        missing_faculty = sorted(set(payload.get("faculty_ids", [])) - ids["faculty"])
        if missing_faculty:
            report.add("ERROR", path, f"group references missing faculty: {missing_faculty}")
        unknown_topics = sorted(set(payload.get("research_topics", [])) - topics)
        if unknown_topics:
            report.add("ERROR", path, f"unknown group research topics: {unknown_topics}")

    if profile == "release":
        for directory_payloads in payloads.values():
            for payload, path in directory_payloads:
                if payload["workflow"]["status"] != "APPROVED":
                    report.add("ERROR", path, "release entity workflow must be APPROVED")
    return ids


def validate_shards(
    shards_root: Path,
    profile: str = "draft",
    repository_root: Path | None = None,
) -> ValidationReport:
    if profile not in {"draft", "release"}:
        raise ValueError("profile must be 'draft' or 'release'")
    root = repository_root or project_root()
    shards_root = shards_root.resolve()
    report = ValidationReport()
    schema_store = SchemaStore(root)
    venues, topics, layers, contributions, methods = _known_values(root)
    entities_root = shards_root.parent / "entities"
    entity_ids = _validate_entities(entities_root, profile, schema_store, topics, report)

    global_source_ids: dict[str, tuple[dict[str, Any], Path]] = {}
    venue_year_payloads: dict[tuple[str, int], tuple[dict[str, Any], Path]] = {}
    for path in sorted(shards_root.rglob("venue-year.json")):
        payload = _load_for_validation(path, schema_store, report)
        if payload is None:
            continue
        venue = payload.get("venue")
        year = payload.get("year")
        if venue not in venues:
            report.add("ERROR", path, f"unknown venue {venue!r}")
        key = (venue, year)
        if key in venue_year_payloads:
            report.add("ERROR", path, f"duplicate venue-year record {key}")
        venue_year_payloads[key] = (payload, path)
        if profile == "release":
            if payload["collection_status"] == "UNVERIFIED":
                report.add("ERROR", path, "release venue-year cannot remain UNVERIFIED")
            if payload["workflow"]["status"] != "APPROVED":
                report.add("ERROR", path, "release venue-year workflow must be APPROVED")
            countable = payload["collection_status"] in {
                "COMPLETE_PROCEEDINGS",
                "ACCEPTED_PAPERS_ONLY",
                "PARTIAL",
            }
            if countable and any(value is None for value in payload["counts"].values()):
                report.add("ERROR", path, "collected release venue-year counts must all be resolved")
            if not countable and any(value is not None for value in payload["counts"].values()):
                report.add(
                    "ERROR",
                    path,
                    "upcoming or unavailable venue-year must use null counts, never inferred zeros",
                )

    metadata_paths = sorted(shards_root.rglob("metadata.json"))
    seen_ids: dict[str, Path] = {}
    seen_titles: dict[tuple[str, int, str], Path] = {}
    observed_counts: dict[tuple[str, int], dict[str, int]] = {}
    for metadata_path in metadata_paths:
        paper_directory = metadata_path.parent
        report.paper_bundles_checked += 1
        paths = {filename: paper_directory / filename for filename in STAGE_FILES}
        missing = [filename for filename, path in paths.items() if not path.exists()]
        if missing:
            report.add("ERROR", paper_directory, f"incomplete paper bundle; missing {missing}")
            continue

        bundle: dict[str, dict[str, Any]] = {}
        failed = False
        for filename, path in paths.items():
            payload = _load_for_validation(path, schema_store, report)
            if payload is None:
                failed = True
                continue
            bundle[filename] = payload
            _check_source_references(payload, path, report)
            for source in payload.get("sources", []):
                source_id = source.get("id")
                if not isinstance(source_id, str):
                    continue
                prior = global_source_ids.get(source_id)
                if prior and prior[0] != source:
                    report.add(
                        "ERROR",
                        path,
                        f"source ID {source_id!r} has different content in {prior[1]}",
                    )
                else:
                    global_source_ids[source_id] = (source, path)
        if failed:
            continue

        metadata = bundle["metadata.json"]
        record_id = metadata["paper_id"]
        if record_id != paper_directory.name:
            report.add(
                "ERROR",
                metadata_path,
                f"paper_id {record_id!r} does not match directory {paper_directory.name!r}",
            )
        for filename, payload in bundle.items():
            if payload["paper_id"] != record_id:
                report.add("ERROR", paths[filename], f"paper_id does not match {record_id!r}")

        path_parts = paper_directory.parts
        try:
            papers_index = len(path_parts) - 1 - tuple(reversed(path_parts)).index("papers")
            path_venue = path_parts[papers_index - 2]
            path_year = int(path_parts[papers_index - 1])
        except (ValueError, IndexError):
            report.add("ERROR", paper_directory, "paper path must be <venue>/<year>/papers/<id>")
            continue
        if metadata["venue"] != path_venue or metadata["year"] != path_year:
            report.add(
                "ERROR",
                metadata_path,
                "metadata venue/year does not match its shard directory",
            )
        if path_venue not in venues or path_year not in SUPPORTED_YEARS:
            report.add("ERROR", paper_directory, "paper is outside configured venue/year scope")
        if (path_venue, path_year) not in venue_year_payloads:
            report.add("ERROR", paper_directory, "paper shard lacks venue-year.json")

        if record_id in seen_ids:
            report.add("ERROR", metadata_path, f"duplicate paper ID also in {seen_ids[record_id]}")
        else:
            seen_ids[record_id] = metadata_path
        title_key = (metadata["venue"], metadata["year"], normalize_title(metadata["title"]))
        if title_key in seen_titles:
            report.add(
                "ERROR",
                metadata_path,
                f"duplicate normalized title also in {seen_titles[title_key]}",
            )
        else:
            seen_titles[title_key] = metadata_path

        doi = metadata["links"].get("doi")
        if doi and not DOI_PATTERN.fullmatch(doi.removeprefix("https://doi.org/")):
            report.add("ERROR", metadata_path, f"invalid DOI format: {doi!r}")
        positions = [author["position"] for author in metadata.get("authors", [])]
        if positions and sorted(positions) != list(range(1, len(positions) + 1)):
            report.add("ERROR", metadata_path, "author positions must be consecutive from 1")

        relevance = bundle["relevance.json"]
        if metadata["paper_type"] == "main-track":
            counts = observed_counts.setdefault(
                (metadata["venue"], metadata["year"]),
                {
                    "main_track": 0,
                    "core_systems": 0,
                    "systems_adjacent": 0,
                    "excluded": 0,
                    "needs_review": 0,
                },
            )
            counts["main_track"] += 1
            class_to_count = {
                "CORE_SYSTEMS": "core_systems",
                "SYSTEMS_ADJACENT": "systems_adjacent",
                "EXCLUDED": "excluded",
                "NEEDS_HUMAN_REVIEW": "needs_review",
            }
            counts[class_to_count[relevance["class"]]] += 1
        unknown_topics = sorted(set(relevance["topics"]) - topics)
        unknown_layers = sorted(set(relevance["system_layers"]) - layers)
        unknown_contributions = sorted(set(relevance["contribution_types"]) - contributions)
        unknown_methods = sorted(set(relevance["methods"]) - methods)
        for label, values in (
            ("topics", unknown_topics),
            ("system_layers", unknown_layers),
            ("contribution_types", unknown_contributions),
            ("methods", unknown_methods),
        ):
            if values:
                report.add("ERROR", paths["relevance.json"], f"unknown {label}: {values}")

        groups = bundle["groups.json"]
        for association in groups["associations"]:
            references = (
                ("group_id", "research-groups"),
                ("faculty_id", "faculty"),
                ("publication_institution_id", "institutions"),
                ("current_institution_id", "institutions"),
            )
            for field_name, entity_directory in references:
                entity_id = association[field_name]
                if entity_id and entity_id not in entity_ids[entity_directory]:
                    report.add(
                        "ERROR",
                        paths["groups.json"],
                        f"{field_name} references missing entity {entity_id!r}",
                    )

        if profile == "release":
            _check_release_stage(bundle, paths, report)

    if profile == "release":
        empty_counts = {
            "main_track": 0,
            "core_systems": 0,
            "systems_adjacent": 0,
            "excluded": 0,
            "needs_review": 0,
        }
        for key, (payload, path) in venue_year_payloads.items():
            if payload["collection_status"] not in {
                "COMPLETE_PROCEEDINGS",
                "ACCEPTED_PAPERS_ONLY",
                "PARTIAL",
            }:
                continue
            observed = observed_counts.get(key, empty_counts)
            if payload["counts"] != observed:
                report.add(
                    "ERROR",
                    path,
                    f"declared counts {payload['counts']} do not match staged papers {observed}",
                )

    return report
