from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import STAGE_FILES, project_root
from .validation import load_json, validate_shards


def _summary_card(summary: dict[str, Any]) -> dict[str, Any] | None:
    """The beginner story for the interface, or None when nothing was written."""
    status = summary["workflow"]["status"]
    if status == "NOT_STARTED" and not summary.get("takeaway"):
        return None
    evaluation = summary.get("evaluation") or {}
    return {
        "status": status,
        "written_by": summary["workflow"].get("owner"),
        "updated_at": summary["workflow"].get("updated_at"),
        "confidence": (summary.get("verification") or {}).get("confidence"),
        "background": summary.get("background"),
        "villain": summary.get("villain"),
        "approach": summary.get("approach"),
        "impact": summary.get("impact"),
        "evaluation": {
            "overview": evaluation.get("overview"),
            "implemented": evaluation.get("implemented"),
            "setting": evaluation.get("setting"),
            "baselines": evaluation.get("baselines") or [],
            "results": [
                {"text": result.get("text"), "locator": result.get("locator")}
                for result in evaluation.get("results") or []
            ],
            "study_types": evaluation.get("study_types") or [],
        },
        "limitations": summary.get("limitations"),
        "phd_group_signal": summary.get("phd_group_signal"),
        "beginner_concepts": summary.get("beginner_concepts") or [],
        "reading_coverage": summary.get("reading_coverage") or {},
    }


def _review_card(review: dict[str, Any]) -> dict[str, Any] | None:
    """The independent reviewer's verdict, or None when no review has started."""
    status = review["workflow"]["status"]
    if status == "NOT_STARTED" and review.get("decision") == "NOT_REVIEWED":
        return None
    return {
        "status": status,
        "decision": review.get("decision"),
        "reviewer": review.get("reviewer"),
        "updated_at": review["workflow"].get("updated_at"),
        "issues": [
            {
                "severity": issue.get("severity"),
                "stage": issue.get("stage"),
                "description": issue.get("description"),
                "status": issue.get("status"),
            }
            for issue in review.get("issues") or []
        ],
    }


def _paper_card(paper_directory: Path) -> dict[str, Any]:
    bundle = {filename: load_json(paper_directory / filename) for filename in STAGE_FILES}
    metadata = bundle["metadata.json"]
    relevance = bundle["relevance.json"]
    summary = bundle["summary.json"]
    groups = bundle["groups.json"]
    awards = bundle["awards.json"]
    review = bundle["review.json"]
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
        "track_or_session": metadata.get("track_or_session"),
        "authors": [author["name"] for author in metadata["authors"]],
        # Abstracts are not part of the metadata contract yet; the key is
        # emitted so the interface can show and search them once collected.
        "abstract": metadata.get("abstract"),
        "takeaway": summary["takeaway"],
        "summary": _summary_card(summary),
        "review": _review_card(review),
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
