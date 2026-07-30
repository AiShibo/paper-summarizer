from __future__ import annotations

import argparse
import hashlib
import json
import signal
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .constants import STAGE_FILES, project_root


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def snapshot(root: Path) -> dict[str, Any]:
    claims: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "coordination" / "claims").glob("*.json")):
        claim = _load_json(path)
        if not claim or claim.get("agent_id") == "replace-with-unique-agent-id":
            continue
        claims[str(claim.get("agent_id"))] = {
            "status": claim.get("status"),
            "shards": len(claim.get("shards", [])),
            "paper_ids": len(claim.get("paper_ids", [])),
        }

    papers_by_shard: Counter[str] = Counter()
    stage_workflows: dict[str, Counter[str]] = {
        filename: Counter() for filename in STAGE_FILES
    }
    unreadable: list[str] = []
    newest_change: tuple[float, str] | None = None
    shards_root = root / "data" / "shards"
    for metadata_path in sorted(shards_root.rglob("metadata.json")):
        try:
            relative = metadata_path.relative_to(shards_root)
            shard = f"{relative.parts[0]}/{relative.parts[1]}"
        except (ValueError, IndexError):
            shard = "invalid-path"
        papers_by_shard[shard] += 1
        paper_directory = metadata_path.parent
        for filename in STAGE_FILES:
            path = paper_directory / filename
            payload = _load_json(path)
            if payload is None:
                stage_workflows[filename]["MISSING_OR_UNREADABLE"] += 1
                unreadable.append(str(path.relative_to(root)))
            else:
                status = payload.get("workflow", {}).get("status", "MISSING_STATUS")
                stage_workflows[filename][str(status)] += 1
            if path.exists():
                modified = path.stat().st_mtime
                if newest_change is None or modified > newest_change[0]:
                    newest_change = (modified, str(path.relative_to(root)))

    venue_year_states: Counter[str] = Counter()
    for path in sorted(shards_root.rglob("venue-year.json")):
        payload = _load_json(path)
        if payload is None:
            venue_year_states["MISSING_OR_UNREADABLE"] += 1
            unreadable.append(str(path.relative_to(root)))
        else:
            key = (
                f"{payload.get('workflow', {}).get('status', 'MISSING_STATUS')}:"
                f"{payload.get('collection_status', 'MISSING_STATUS')}"
            )
            venue_year_states[key] += 1

    entity_counts = {
        directory: len(list((root / "data" / "entities" / directory).glob("*.json")))
        for directory in ("authors", "faculty", "research-groups", "institutions")
    }
    frontend_files: dict[str, str] = {}
    frontend_candidates = [
        root / "site" / "index.html",
        root / "site" / "styles.css",
        root / "site" / "app.js",
        root / "site" / "data" / "fixture-papers.json",
    ]
    for directory in (
        root / "site" / "pages",
        root / "site" / "components",
        root / "tests" / "frontend",
    ):
        if directory.exists():
            frontend_candidates.extend(path for path in directory.rglob("*") if path.is_file())
    for path in sorted(set(frontend_candidates)):
        if path.exists():
            frontend_files[str(path.relative_to(root))] = _file_digest(path)

    return {
        "observed_at": _timestamp(),
        "claims": claims,
        "papers_by_shard": dict(sorted(papers_by_shard.items())),
        "stage_workflows": {
            filename: dict(sorted(counts.items()))
            for filename, counts in stage_workflows.items()
        },
        "venue_year_states": dict(sorted(venue_year_states.items())),
        "entity_counts": entity_counts,
        "frontend_files": frontend_files,
        "unreadable_files": sorted(set(unreadable)),
        "newest_stage_change": newest_change[1] if newest_change else None,
    }


def fingerprint(value: dict[str, Any]) -> str:
    stable = {key: item for key, item in value.items() if key != "observed_at"}
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError:
        return "UNREADABLE"
    return hashlib.sha256(content).hexdigest()[:12]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only delegated-agent monitor")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--interval", type=int, default=120)
    args = parser.parse_args(argv)
    if args.interval < 10:
        parser.error("--interval must be at least 10 seconds")

    root = (args.root or project_root()).resolve()
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    previous_fingerprint: str | None = None
    while running:
        current = snapshot(root)
        current_fingerprint = fingerprint(current)
        output = {
            **current,
            "changed_since_previous_check": (
                previous_fingerprint is not None and current_fingerprint != previous_fingerprint
            ),
        }
        print(json.dumps(output, sort_keys=True), flush=True)
        previous_fingerprint = current_fingerprint
        for _ in range(args.interval):
            if not running:
                break
            time.sleep(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
