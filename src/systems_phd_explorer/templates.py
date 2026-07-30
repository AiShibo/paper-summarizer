from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .constants import SCHEMA_VERSION, STAGE_FILES, SUPPORTED_YEARS, project_root
from .ids import paper_id

SCHEMA_BASE = "https://systems-phd-explorer.local/schemas/v1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def workflow(status: str, owner: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "owner": owner,
        "updated_at": utc_now() if owner else None,
        "notes": [],
    }


def verification() -> dict[str, Any]:
    return {
        "collected_at": None,
        "last_verified_at": None,
        "collector_version": None,
        "confidence": "UNRESOLVED",
        "verified_by": None,
        "unresolved_fields": [],
    }


def _base(schema_name: str, record_id: str) -> dict[str, Any]:
    return {
        "$schema": f"{SCHEMA_BASE}/{schema_name}",
        "schema_version": SCHEMA_VERSION,
        "paper_id": record_id,
    }


def paper_bundle(venue: str, year: int, title: str, owner: str) -> dict[str, dict[str, Any]]:
    record_id = paper_id(venue, year, title)
    metadata = {
        **_base("paper-metadata.schema.json", record_id),
        "title": title,
        "venue": venue,
        "year": year,
        "track_or_session": None,
        "paper_type": "unknown",
        "publication_date": None,
        "page_count": None,
        "venue_year_completion_status": "UNVERIFIED",
        "authors": [],
        "links": {
            "doi": None,
            "official_page": None,
            "official_pdf": None,
            "artifact": None,
            "code": None,
            "project": None,
            "slides": None,
            "video": None,
            "bibtex": None,
        },
        "alternate_versions": [],
        "sources": [],
        "workflow": workflow("IN_PROGRESS", owner),
        "verification": {
            **verification(),
            "unresolved_fields": [
                "paper_type",
                "authors",
                "links.official_page",
                "venue_year_completion_status",
            ],
        },
    }
    relevance = {
        **_base("relevance.schema.json", record_id),
        "class": "NEEDS_HUMAN_REVIEW",
        "score": 0,
        "rationale": "",
        "topics": [],
        "system_layers": [],
        "contribution_types": [],
        "methods": [],
        "sources": [],
        "workflow": workflow("NOT_STARTED", None),
        "verification": verification(),
    }
    summary = {
        **_base("summary.schema.json", record_id),
        "takeaway": None,
        "background": None,
        "villain": None,
        "approach": None,
        "impact": None,
        "evaluation": {
            "overview": None,
            "implemented": None,
            "setting": None,
            "baselines": [],
            "results": [],
            "study_types": [],
        },
        "limitations": None,
        "phd_group_signal": None,
        "beginner_concepts": [],
        "reading_coverage": {
            "abstract": "NOT_READ",
            "introduction": "NOT_READ",
            "conclusion": "NOT_READ",
            "system_overview_or_design": "NOT_READ",
            "evaluation_overview": "NOT_READ",
        },
        "claims": [],
        "sources": [],
        "workflow": workflow("NOT_STARTED", None),
        "verification": verification(),
    }
    groups = {
        **_base("groups.schema.json", record_id),
        "associations": [],
        "unresolved_authors": [],
        "sources": [],
        "workflow": workflow("NOT_STARTED", None),
        "verification": verification(),
    }
    awards = {
        **_base("awards.schema.json", record_id),
        "awards": [],
        "sources": [],
        "workflow": workflow("NOT_STARTED", None),
        "verification": verification(),
    }
    review = {
        **_base("review.schema.json", record_id),
        "reviewer": None,
        "independent_from": [],
        "checks": {
            "metadata": None,
            "relevance": None,
            "summary_accuracy": None,
            "numerical_claims": None,
            "pi_attribution": None,
            "awards": None,
            "duplicates": None,
            "links": None,
        },
        "issues": [],
        "decision": "NOT_REVIEWED",
        "workflow": workflow("NOT_STARTED", None),
        "verification": verification(),
    }
    return {
        "metadata.json": metadata,
        "relevance.json": relevance,
        "summary.json": summary,
        "groups.json": groups,
        "awards.json": awards,
        "review.json": review,
    }


def venue_year_record(venue: str, year: int, owner: str) -> dict[str, Any]:
    return {
        "$schema": f"{SCHEMA_BASE}/venue-year.schema.json",
        "schema_version": SCHEMA_VERSION,
        "venue": venue,
        "year": year,
        "official_conference_url": None,
        "official_program_url": None,
        "conference_dates": {"start": None, "end": None},
        "collection_status": "UNVERIFIED",
        "counts": {
            "main_track": None,
            "core_systems": None,
            "systems_adjacent": None,
            "excluded": None,
            "needs_review": None,
        },
        "sources": [],
        "workflow": workflow("IN_PROGRESS", owner),
        "verification": {
            **verification(),
            "unresolved_fields": [
                "official_conference_url",
                "official_program_url",
                "conference_dates",
                "collection_status",
                "counts",
            ],
        },
    }


def write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(serialized)


def _validate_venue_year(venue: str, year: int, root: Path) -> None:
    venue_config = json.loads((root / "config" / "venues.json").read_text(encoding="utf-8"))
    venue_slugs = {item["slug"] for item in venue_config["venues"]}
    if venue not in venue_slugs:
        raise ValueError(f"Unsupported venue {venue!r}; choose one of {sorted(venue_slugs)}")
    if year not in SUPPORTED_YEARS:
        raise ValueError(f"Unsupported year {year}; choose one of {SUPPORTED_YEARS}")


def initialize_venue_year(
    venue: str,
    year: int,
    owner: str,
    shards_root: Path | None = None,
) -> Path:
    root = project_root()
    _validate_venue_year(venue, year, root)
    if not owner.strip():
        raise ValueError("Owner must not be empty")
    shard_root = (shards_root or root / "data" / "shards").resolve()
    destination = shard_root / venue / str(year) / "venue-year.json"
    write_json_exclusive(destination, venue_year_record(venue, year, owner.strip()))
    return destination


def initialize_paper(
    venue: str,
    year: int,
    title: str,
    owner: str,
    shards_root: Path | None = None,
) -> Path:
    root = project_root()
    _validate_venue_year(venue, year, root)
    if not title.strip():
        raise ValueError("Paper title must not be empty")
    if not owner.strip():
        raise ValueError("Owner must not be empty")

    shard_root = (shards_root or root / "data" / "shards").resolve()
    shard = shard_root / venue / str(year)
    venue_year_path = shard / "venue-year.json"
    if not venue_year_path.exists():
        initialize_venue_year(venue, year, owner, shard_root)

    bundle = paper_bundle(venue, year, title.strip(), owner.strip())
    record_id = bundle["metadata.json"]["paper_id"]
    paper_directory = shard / "papers" / record_id
    if paper_directory.exists():
        raise FileExistsError(f"Paper bundle already exists: {paper_directory}")
    paper_directory.mkdir(parents=True, exist_ok=False)
    try:
        for filename in STAGE_FILES:
            write_json_exclusive(paper_directory / filename, bundle[filename])
    except Exception:
        for filename in STAGE_FILES:
            candidate = paper_directory / filename
            if candidate.exists():
                candidate.unlink()
        paper_directory.rmdir()
        raise
    return paper_directory
