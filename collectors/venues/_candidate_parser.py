from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin


@dataclass(frozen=True)
class Anchor:
    href: str
    text: str
    attributes: dict[str, str]


@dataclass(frozen=True)
class Candidate:
    title: str
    official_page: str
    source_url: str
    discovery_confidence: str = "LOW"
    human_review_required: bool = True


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[Anchor] = []
        self._href: str | None = None
        self._attributes: dict[str, str] = {}
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._attributes = {key: value or "" for key, value in attrs}
            self._href = self._attributes.get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            text = " ".join("".join(self._text).split())
            self.anchors.append(Anchor(self._href, html.unescape(text), self._attributes))
            self._href = None
            self._attributes = {}
            self._text = []


def anchors_from_file(path: Path) -> list[Anchor]:
    parser = AnchorParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.anchors


def candidates_as_json(candidates: list[Candidate]) -> str:
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "candidate_count": len(candidates),
            "candidates": [asdict(candidate) for candidate in candidates],
        },
        indent=2,
        ensure_ascii=False,
    )


def clean_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def deduplicate(candidates: list[Candidate]) -> list[Candidate]:
    result: list[Candidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        key = (candidate.title.casefold(), candidate.official_page)
        if key not in seen:
            seen.add(key)
            result.append(candidate)
    return result


def absolute_url(source_url: str, href: str) -> str:
    return urljoin(source_url, href)
