from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .abstracts import ALL_SOURCES, collect_abstracts
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
    abstracts = subparsers.add_parser(
        "collect-abstracts",
        help="Fetch published abstracts into metadata.json (resumable)",
    )
    abstracts.add_argument("--root", required=True, type=_path)
    abstracts.add_argument("--venue", help="Only this venue slug")
    abstracts.add_argument("--year", type=int, help="Only this year")
    abstracts.add_argument("--limit", type=int, help="Stop after this many papers without an abstract")
    abstracts.add_argument("--dry-run", action="store_true", help="Fetch but do not write")
    abstracts.add_argument("--force", action="store_true", help="Refetch papers that already have an abstract")
    abstracts.add_argument("--mailto", help="Contact address sent to the APIs' polite pools")
    abstracts.add_argument("--s2-api-key", help="Semantic Scholar API key, if you have one")
    abstracts.add_argument(
        "--sources",
        default=",".join(ALL_SOURCES),
        help="Comma-separated passes to run, in order: " + ",".join(ALL_SOURCES),
    )
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
        if args.command == "collect-abstracts":
            report = collect_abstracts(
                args.root,
                venue=args.venue,
                year=args.year,
                limit=args.limit,
                dry_run=args.dry_run,
                force=args.force,
                mailto=args.mailto,
                s2_api_key=args.s2_api_key,
                sources=tuple(source.strip() for source in args.sources.split(",") if source.strip()),
                log=lambda message: print(message, flush=True),
            )
            print(report.summary())
            return 0 if report.failed == 0 else 1
    except (FileExistsError, OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
