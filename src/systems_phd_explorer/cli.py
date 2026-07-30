from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .database import build_database
from .export import build_site_data
from .manifest import write_manifest
from .templates import initialize_paper, initialize_venue_year
from .validation import validate_shards


def _path(value: str) -> Path:
    return Path(value).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="systems-phd-explorer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_paper = subparsers.add_parser(
        "init-paper",
        help="Create all conflict-separated stage files for one paper",
    )
    init_paper.add_argument("--venue", required=True)
    init_paper.add_argument("--year", required=True, type=int)
    init_paper.add_argument("--title", required=True)
    init_paper.add_argument("--owner", required=True)
    init_paper.add_argument("--root", type=_path, default=Path("data/shards"))

    init_venue = subparsers.add_parser(
        "init-venue",
        help="Create an explicit venue-year status file without inventing paper counts",
    )
    init_venue.add_argument("--venue", required=True)
    init_venue.add_argument("--year", required=True, type=int)
    init_venue.add_argument("--owner", required=True)
    init_venue.add_argument("--root", type=_path, default=Path("data/shards"))

    validate = subparsers.add_parser("validate", help="Validate staged paper shards")
    validate.add_argument("--root", required=True, type=_path)
    validate.add_argument("--profile", choices=("draft", "release"), default="draft")

    database = subparsers.add_parser("build-db", help="Build SQLite atomically")
    database.add_argument("--root", required=True, type=_path)
    database.add_argument("--output", required=True, type=_path)

    manifest = subparsers.add_parser(
        "build-manifest",
        help="Regenerate live venue-year status from independent shard files",
    )
    manifest.add_argument("--root", required=True, type=_path)
    manifest.add_argument("--output", required=True, type=_path)

    site_data = subparsers.add_parser(
        "build-site-data",
        help="Generate the compact client-side paper index",
    )
    site_data.add_argument("--root", required=True, type=_path)
    site_data.add_argument("--output", required=True, type=_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init-paper":
            destination = initialize_paper(
                args.venue,
                args.year,
                args.title,
                args.owner,
                args.root,
            )
            print(destination)
            return 0
        if args.command == "init-venue":
            destination = initialize_venue_year(
                args.venue,
                args.year,
                args.owner,
                args.root,
            )
            print(destination)
            return 0
        if args.command == "validate":
            report = validate_shards(args.root, args.profile)
            for issue in report.issues:
                print(issue.render(Path.cwd()))
            print(
                f"Checked {report.paper_bundles_checked} paper bundle(s) and "
                f"{report.files_checked} JSON file(s): "
                f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)."
            )
            return 0 if report.ok else 1
        if args.command == "build-db":
            build_database(args.root, args.output)
            print(args.output)
            return 0
        if args.command == "build-manifest":
            write_manifest(args.root, args.output)
            print(args.output)
            return 0
        if args.command == "build-site-data":
            build_site_data(args.root, args.output)
            print(args.output)
            return 0
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
