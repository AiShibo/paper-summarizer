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

DOI_LINK = re.compile(r"(?:doi\.org/|dl\.acm\.org/doi/)(?:abs/|fullHtml/|pdf/)?10\.1145/", re.IGNORECASE)
NON_TITLE_TEXT = re.compile(r"^(?:pdf|html|doi|abstract|view|download)$", re.IGNORECASE)


def parse_candidates(html_path: Path, source_url: str) -> list[Candidate]:
    candidates = []
    for anchor in anchors_from_file(html_path):
        title = clean_title(anchor.attributes.get("data-title") or anchor.text)
        if DOI_LINK.search(anchor.href) and len(title.split()) >= 3 and not NON_TITLE_TEXT.match(title):
            candidates.append(
                Candidate(
                    title=title,
                    official_page=absolute_url(source_url, anchor.href),
                    source_url=source_url,
                )
            )
    return deduplicate(candidates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract SOSP candidates from saved ACM HTML")
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args(argv)
    candidates = parse_candidates(args.html, args.source_url)
    print(candidates_as_json(candidates))
    if not candidates:
        print(
            "warning: no title-bearing ACM DOI links found; the page format may have changed",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
