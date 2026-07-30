from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = "1.0.0"
SUPPORTED_YEARS = (2023, 2024, 2025, 2026)
STAGE_FILES = (
    "metadata.json",
    "relevance.json",
    "summary.json",
    "groups.json",
    "awards.json",
    "review.json",
)
SCHEMA_BY_FILENAME = {
    "venue-year.json": "venue-year.schema.json",
    "metadata.json": "paper-metadata.schema.json",
    "relevance.json": "relevance.schema.json",
    "summary.json": "summary.schema.json",
    "groups.json": "groups.schema.json",
    "awards.json": "awards.schema.json",
    "review.json": "review.schema.json",
    "venue-year-manifest.json": "venue-year-manifest.schema.json",
}
ENTITY_SCHEMA_BY_DIRECTORY = {
    "authors": ("author.schema.json", "author_id"),
    "faculty": ("faculty.schema.json", "faculty_id"),
    "research-groups": ("research-group.schema.json", "group_id"),
    "institutions": ("institution.schema.json", "institution_id"),
}


def project_root(start: Path | None = None) -> Path:
    """Find the repository root without depending on the current directory."""
    candidate = (start or Path.cwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for directory in (candidate, *candidate.parents):
        if (directory / "pyproject.toml").exists() and (directory / "schemas").is_dir():
            return directory
    module_root = Path(__file__).resolve().parents[2]
    if (module_root / "pyproject.toml").exists():
        return module_root
    raise RuntimeError("Could not locate the Systems PhD Explorer project root")
