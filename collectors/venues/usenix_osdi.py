from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from ._candidate_parser import (
        Candidate,
        absolute_url,
        anchors_from_file,
        candidates_as_json,
        clean_title,
        deduplicate,
    )
except ImportError:
    from _candidate_parser import (
        Candidate,
        absolute_url,
        anchors_from_file,
        candidates_as_json,
        clean_title,
        deduplicate,
    )

PRESENTATION_LINK = re.compile(r"/conference/osdi\d+/presentation/[a-z0-9-]+/?$", re.IGNORECASE)


def parse_candidates(html_path: Path, source_url: str) -> list[Candidate]:
    candidates = []
    for anchor in anchors_from_file(html_path):
        if PRESENTATION_LINK.search(anchor.href):
            title = clean_title(anchor.text)
            if title:
                candidates.append(
                    Candidate(
                        title=title,
                        official_page=absolute_url(source_url, anchor.href),
                        source_url=source_url,
                    )
                )
    return deduplicate(candidates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract OSDI candidates from saved USENIX HTML")
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args(argv)
    candidates = parse_candidates(args.html, args.source_url)
    print(candidates_as_json(candidates))
    if not candidates:
        print(
            "warning: no OSDI presentation links found; the page format may have changed",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
