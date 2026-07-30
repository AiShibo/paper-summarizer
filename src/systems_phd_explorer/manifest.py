from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .constants import project_root
from .validation import load_json


def build_manifest(shards_root: Path, repository_root: Path | None = None) -> dict[str, Any]:
    root = repository_root or project_root()
    baseline = load_json(root / "data" / "venue-year-manifest.json")
    generated = {
        **baseline,
        "$schema": "https://systems-phd-explorer.local/schemas/v1/venue-year-manifest.schema.json",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "venue_years": [],
    }
    for item in baseline["venue_years"]:
        result = dict(item)
        shard_file = shards_root / item["venue"] / str(item["year"]) / "venue-year.json"
        if shard_file.exists():
            shard = load_json(shard_file)
            result["workflow_status"] = shard["workflow"]["status"]
            result["collection_status"] = shard["collection_status"]
            result["last_verified_at"] = shard["verification"]["last_verified_at"]
        generated["venue_years"].append(result)
    return generated


def write_manifest(
    shards_root: Path,
    output: Path,
    repository_root: Path | None = None,
) -> None:
    payload = build_manifest(shards_root.resolve(), repository_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
