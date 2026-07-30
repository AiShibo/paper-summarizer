from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import STAGE_FILES, project_root
from .validation import load_json, validate_shards


def _paper_card(paper_directory: Path) -> dict[str, Any]:
    bundle = {filename: load_json(paper_directory / filename) for filename in STAGE_FILES}
    metadata = bundle["metadata.json"]
    relevance = bundle["relevance.json"]
    summary = bundle["summary.json"]
    groups = bundle["groups.json"]
    awards = bundle["awards.json"]
    institutions = sorted(
        {
            affiliation["normalized_name"] or affiliation["name_as_published"]
            for author in metadata["authors"]
            for affiliation in author["affiliations"]
        }
    )
    locations = sorted(
        {
            ", ".join(filter(None, (affiliation["city"], affiliation["country"])))
            for author in metadata["authors"]
            for affiliation in author["affiliations"]
            if affiliation["city"] or affiliation["country"]
        }
    )
    return {
        "id": metadata["paper_id"],
        "title": metadata["title"],
        "venue": metadata["venue"],
        "year": metadata["year"],
        "authors": [author["name"] for author in metadata["authors"]],
        "takeaway": summary["takeaway"],
        "relevance_class": relevance["class"],
        "relevance_score": relevance["score"],
        "topics": relevance["topics"],
        "system_layers": relevance["system_layers"],
        "methods": relevance["methods"],
        "institutions": institutions,
        "locations": locations,
        "faculty_ids": sorted(
            {
                association["faculty_id"]
                for association in groups["associations"]
                if association["faculty_id"]
            }
        ),
        "group_ids": sorted(
            {
                association["group_id"]
                for association in groups["associations"]
                if association["group_id"]
            }
        ),
        "awards": [
            {"name": award["official_name"], "category": award["category"]}
            for award in awards["awards"]
        ],
        "has_code": bool(metadata["links"]["code"]),
        "has_artifact": bool(metadata["links"]["artifact"]),
        "links": {
            "official_page": metadata["links"]["official_page"],
            "official_pdf": metadata["links"]["official_pdf"],
            "code": metadata["links"]["code"],
            "artifact": metadata["links"]["artifact"],
        },
        "confidence": relevance["verification"]["confidence"],
        "last_verified_at": metadata["verification"]["last_verified_at"],
        "is_fixture": False,
    }


def build_site_data(
    shards_root: Path,
    output: Path,
    repository_root: Path | None = None,
) -> None:
    root = repository_root or project_root()
    report = validate_shards(shards_root, profile="draft", repository_root=root)
    if not report.ok:
        rendered = "\n".join(issue.render(root) for issue in report.errors)
        raise ValueError(f"Cannot export invalid shards:\n{rendered}")
    papers = [
        _paper_card(metadata_path.parent)
        for metadata_path in sorted(shards_root.resolve().rglob("metadata.json"))
    ]
    payload = {
        "schema_version": "1.0.0",
        "is_fixture_export": False,
        "papers": papers,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(output)
