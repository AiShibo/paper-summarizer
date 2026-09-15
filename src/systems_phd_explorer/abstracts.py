"""Collect published abstracts into each paper's ``metadata.json``.

The run is a sequence of passes over the papers that still lack an abstract,
fastest and most authoritative sources first:

1. Official paper pages that publish the abstract in HTML (USENIX, NDSS).
2. The OpenAlex API, by DOI and then by title search.
3. The Semantic Scholar batch endpoint, by DOI (hundreds of papers per request).
4. Semantic Scholar exact-title matching, for papers without a DOI.
5. The arXiv API, by exact title, for papers with a preprint.

ACM and IEEE pages are never scraped; their abstracts come from the APIs.
Every stored abstract is accompanied by a ``sources`` record so the text can be
traced back to where it was read. Papers that already have an abstract are
skipped, which makes an interrupted run resumable.
"""

from __future__ import annotations

import difflib
import hashlib
import html
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .validation import load_json

USER_AGENT = "systems-phd-explorer/1.0 (abstract collector)"
MIN_ABSTRACT_LENGTH = 80
TITLE_MATCH_RATIO = 0.92

SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
OPENALEX_API = "https://api.openalex.org"
ARXIV_API = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_BATCH_SIZE = 100
ALL_SOURCES = ("official", "openalex", "s2-batch", "s2-match", "arxiv")

# Minimum seconds between requests to the same host. Semantic Scholar's
# unauthenticated pool is strict, so it is spaced widely and asked in batches;
# OpenAlex's polite pool allows ten requests per second; arXiv asks for one
# request every three seconds.
LANE_INTERVALS = {
    "usenix": 0.6,
    "ndss": 0.6,
    "semantic-scholar": 5.0,
    "openalex": 0.25,
    "arxiv": 3.0,
}

Log = Callable[[str], None]


# --------------------------------------------------------------------------
# Pure helpers (unit tested)
# --------------------------------------------------------------------------


def clean_text(fragment: str) -> str:
    """Strips HTML/JATS tags, unescapes entities, and normalizes whitespace.

    Paragraph breaks are kept as blank lines so multi-paragraph abstracts stay
    readable.
    """
    text = re.sub(r"(?i)</p\s*>|<br\s*/?>|</jats:p>", "\n\n", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    paragraphs = [re.sub(r"\s+", " ", paragraph).strip() for paragraph in text.split("\n\n")]
    text = "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
    text = re.sub(r"(?i)^abstract[:.\s—-]*", "", text).strip()
    return text


def usable_abstract(text: str | None) -> str | None:
    """Returns the cleaned abstract, or None when it is missing or a placeholder."""
    if not text:
        return None
    cleaned = clean_text(text) if "<" in text else clean_text(html.escape(text, quote=False))
    if len(cleaned) < MIN_ABSTRACT_LENGTH:
        return None
    if re.match(r"(?i)^(no abstract|abstract (is )?(not )?available|n/a)\b", cleaned):
        return None
    return cleaned


def extract_usenix(page: str) -> str | None:
    """The abstract lives in the ``field-name-field-paper-description`` block."""
    match = re.search(
        r'field-name-field-paper-description.*?<div class="field-item[^"]*">(.*?)</div>\s*</div>',
        page,
        re.S,
    )
    return usable_abstract(match.group(1)) if match else None


def extract_ndss(page: str) -> str | None:
    """The abstract is the longest paragraph inside ``div.paper-data``."""
    start = page.find('class="paper-data"')
    if start < 0:
        return None
    end = page.find('class="entry-footer"', start)
    section = page[start : end if end > 0 else start + 60000]
    best = ""
    for candidate in re.findall(r"<p[^>]*>(.*?)</p>", section, re.S):
        if "<strong>" in candidate:
            continue
        text = clean_text(candidate)
        if len(text) > len(best):
            best = text
    return usable_abstract(best)


def openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Rebuilds the abstract text from OpenAlex's inverted index."""
    if not inverted_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, indexes in inverted_index.items():
        positions.extend((index, word) for index in indexes)
    positions.sort()
    return usable_abstract(" ".join(word for _, word in positions))


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def titles_match(expected: str, candidate: str | None) -> bool:
    if not candidate:
        return False
    left = normalize_title(expected)
    right = normalize_title(candidate)
    if not left or not right:
        return False
    if left == right:
        return True
    return difflib.SequenceMatcher(None, left, right).ratio() >= TITLE_MATCH_RATIO


def normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"(?i)^doi:\s*", "", doi)
    return doi or None


def lane_for(metadata: dict[str, Any]) -> str:
    """Which throttled lane fetches this paper: an official page or an API."""
    page = (metadata.get("links") or {}).get("official_page") or ""
    host = urllib.parse.urlparse(page).netloc.lower()
    if host.endswith("usenix.org"):
        return "usenix"
    if host.endswith("ndss-symposium.org"):
        return "ndss"
    return "api"


def source_record(
    *,
    source_id: str,
    url: str,
    kind: str,
    title: str,
    publisher: str,
    official: bool,
    content: bytes,
    retrieved_at: str,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "url": url,
        "kind": kind,
        "title": title,
        "publisher": publisher,
        "retrieved_at": retrieved_at,
        "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
        "official": official,
        "supports": ["Published abstract text."],
    }


def with_abstract(metadata: dict[str, Any], text: str, source: dict[str, Any]) -> dict[str, Any]:
    """Returns a copy of the metadata with the abstract inserted after the title."""
    updated: dict[str, Any] = {}
    for key, value in metadata.items():
        if key in ("abstract", "abstract_source_id"):
            continue
        updated[key] = value
        if key == "title":
            updated["abstract"] = text
            updated["abstract_source_id"] = source["id"]
    sources = [entry for entry in metadata.get("sources", []) if entry.get("id") != source["id"]]
    sources.append(source)
    updated["sources"] = sources
    return updated


def unique_source_id(metadata: dict[str, Any]) -> str:
    """Source IDs are unique across the whole corpus, so they carry the venue-year."""
    base = f"src-abstract-{metadata['venue']}-{metadata['year']}-" + metadata["paper_id"].rsplit("-", 1)[-1]
    existing = {entry.get("id") for entry in metadata.get("sources", [])}
    candidate = base
    suffix = 2
    while candidate in existing:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


class FetchError(RuntimeError):
    pass


@dataclass
class Response:
    status: int
    body: bytes
    url: str

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Fetcher:
    """urllib wrapper with a user agent, per-lane throttling, and retries."""

    def __init__(self, mailto: str | None = None, s2_api_key: str | None = None, timeout: float = 30.0,
                 log: Log | None = None):
        self.mailto = mailto
        self.s2_api_key = s2_api_key
        self.timeout = timeout
        self.log = log or (lambda message: None)
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, threading.Lock] = {}

    def _throttle(self, lane: str) -> None:
        lock = self._locks.setdefault(lane, threading.Lock())
        with lock:
            wait = LANE_INTERVALS.get(lane, 1.0) - (time.monotonic() - self._last_request.get(lane, 0.0))
            if wait > 0:
                time.sleep(wait)
            self._last_request[lane] = time.monotonic()

    def get(self, url: str, lane: str, *, accept: str = "*/*", retries: int = 3,
            payload: bytes | None = None, delay: float = 2.0) -> Response:
        """Returns the response; a 404 is returned, other failures retry then raise.

        A 429 waits for the server's Retry-After (capped at a minute) or the
        current back-off delay, which doubles on every attempt.
        """
        headers = {"User-Agent": USER_AGENT + (f" (mailto:{self.mailto})" if self.mailto else ""), "Accept": accept}
        if lane == "semantic-scholar" and self.s2_api_key:
            headers["x-api-key"] = self.s2_api_key
        if payload is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(retries + 1):
            self._throttle(lane)
            request = urllib.request.Request(url, data=payload, headers=headers, method="POST" if payload is not None else "GET")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return Response(response.status, response.read(), response.geturl())
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return Response(404, b"", url)
                if error.code == 429 or error.code >= 500:
                    retry_after = error.headers.get("Retry-After") if error.headers else None
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    if attempt < retries:
                        pause = min(pause, 60.0)
                        self.log(f"    {lane}: HTTP {error.code}, retrying in {pause:.0f}s ({attempt + 1}/{retries})")
                        time.sleep(pause)
                        delay *= 2
                        continue
                raise FetchError(f"HTTP {error.code} for {url}") from error
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt < retries:
                    self.log(f"    {lane}: {error}, retrying in {delay:.0f}s ({attempt + 1}/{retries})")
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise FetchError(f"{error} for {url}") from error
        raise FetchError(f"gave up on {url}")


# --------------------------------------------------------------------------
# Strategies
# --------------------------------------------------------------------------


@dataclass
class Found:
    text: str
    source: dict[str, Any]
    lane: str


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _official_page(metadata: dict[str, Any], fetcher: Fetcher, lane: str, publisher: str,
                   extract: Callable[[str], str | None]) -> Found | None:
    url = metadata["links"]["official_page"]
    response = fetcher.get(url, lane, accept="text/html")
    if response.status != 200:
        return None
    text = extract(response.text())
    if not text:
        return None
    source = source_record(
        source_id=unique_source_id(metadata), url=url, kind="paper-page", title=metadata["title"],
        publisher=publisher, official=True, content=response.body, retrieved_at=_now(),
    )
    return Found(text, source, lane)


def _semantic_scholar_match(metadata: dict[str, Any], fetcher: Fetcher) -> Found | None:
    """Exact-title match, for papers without a DOI."""
    lane = "semantic-scholar"
    url = f"{SEMANTIC_SCHOLAR_API}/paper/search/match?query={urllib.parse.quote(metadata['title'])}&fields=title,abstract"
    response = fetcher.get(url, lane, accept="application/json", retries=4, delay=15.0)
    if response.status != 200:
        return None
    payload = response.json()
    records = payload.get("data") if isinstance(payload.get("data"), list) else []
    for record in records:
        if not titles_match(metadata["title"], record.get("title")):
            continue
        text = usable_abstract(record.get("abstract"))
        if not text:
            continue
        source = source_record(
            source_id=unique_source_id(metadata), url=url, kind="semantic-scholar", title=record.get("title"),
            publisher="Semantic Scholar", official=False, content=response.body, retrieved_at=_now(),
        )
        return Found(text, source, lane)
    return None


def _semantic_scholar_batch(batch: list[dict[str, Any]], fetcher: Fetcher) -> dict[str, Found]:
    """Looks up many DOIs in one request; returns findings keyed by paper ID."""
    lane = "semantic-scholar"
    dois = {metadata["paper_id"]: normalize_doi(metadata["links"].get("doi")) for metadata in batch}
    ids = [f"DOI:{doi}" for doi in dois.values() if doi]
    if not ids:
        return {}
    url = f"{SEMANTIC_SCHOLAR_API}/paper/batch?fields=title,abstract,externalIds"
    payload = json.dumps({"ids": ids}).encode("utf-8")
    response = fetcher.get(url, lane, accept="application/json", retries=4, delay=15.0, payload=payload)
    if response.status != 200:
        return {}
    records = response.json()
    if not isinstance(records, list):
        return {}
    by_doi: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        doi = normalize_doi((record.get("externalIds") or {}).get("DOI"))
        if doi:
            by_doi[doi.lower()] = record
    found: dict[str, Found] = {}
    for metadata in batch:
        doi = dois[metadata["paper_id"]]
        record = by_doi.get(doi.lower()) if doi else None
        text = usable_abstract(record.get("abstract")) if record else None
        if not text:
            continue
        source = source_record(
            source_id=unique_source_id(metadata), url=url, kind="semantic-scholar", title=record.get("title"),
            publisher="Semantic Scholar", official=False, content=response.body, retrieved_at=_now(),
        )
        found[metadata["paper_id"]] = Found(text, source, lane)
    return found


def _arxiv(metadata: dict[str, Any], fetcher: Fetcher) -> Found | None:
    """Exact-title search on arXiv, for papers with a preprint."""
    lane = "arxiv"
    query = urllib.parse.quote(f'ti:"{metadata["title"]}"')
    url = f"{ARXIV_API}?search_query={query}&max_results=3"
    response = fetcher.get(url, lane, accept="application/atom+xml")
    if response.status != 200:
        return None
    for entry in re.findall(r"<entry>(.*?)</entry>", response.text(), re.S):
        title = re.search(r"<title>(.*?)</title>", entry, re.S)
        summary = re.search(r"<summary>(.*?)</summary>", entry, re.S)
        if not title or not summary or not titles_match(metadata["title"], clean_text(title.group(1))):
            continue
        text = usable_abstract(html.escape(clean_text(summary.group(1)), quote=False))
        if not text:
            continue
        source = source_record(
            source_id=unique_source_id(metadata), url=url, kind="other", title=clean_text(title.group(1)),
            publisher="arXiv", official=False, content=response.body, retrieved_at=_now(),
        )
        return Found(text, source, lane)
    return None


def _openalex(metadata: dict[str, Any], fetcher: Fetcher) -> Found | None:
    doi = normalize_doi(metadata["links"].get("doi"))
    lane = "openalex"
    select = "id,title,abstract_inverted_index"
    mailto = f"&mailto={urllib.parse.quote(fetcher.mailto)}" if fetcher.mailto else ""
    attempts: list[tuple[str, bool]] = []
    if doi:
        attempts.append((f"{OPENALEX_API}/works/doi:{urllib.parse.quote(doi, safe='/')}?select={select}{mailto}", False))
    attempts.append((
        f"{OPENALEX_API}/works?filter=title.search:{urllib.parse.quote(metadata['title'])}"
        f"&select={select}&per-page=3{mailto}",
        True,
    ))
    for url, is_search in attempts:
        response = fetcher.get(url, lane, accept="application/json")
        if response.status != 200:
            continue
        payload = response.json()
        records = payload.get("results", []) if is_search else [payload]
        for record in records:
            if is_search and not titles_match(metadata["title"], record.get("title")):
                continue
            text = openalex_abstract(record.get("abstract_inverted_index"))
            if not text:
                continue
            source = source_record(
                source_id=unique_source_id(metadata), url=url, kind="openalex", title=record.get("title"),
                publisher="OpenAlex", official=False, content=response.body, retrieved_at=_now(),
            )
            return Found(text, source, lane)
    return None


def official_page_strategy(lane: str) -> Callable[[dict[str, Any], Fetcher], Found | None] | None:
    if lane == "usenix":
        return lambda metadata, fetcher: _official_page(metadata, fetcher, lane, "USENIX", extract_usenix)
    if lane == "ndss":
        return lambda metadata, fetcher: _official_page(metadata, fetcher, lane, "NDSS", extract_ndss)
    return None


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------


@dataclass
class Report:
    considered: int = 0
    skipped: int = 0
    found: int = 0
    missing: int = 0
    failed: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    missing_ids: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)

    def summary(self) -> str:
        sources = ", ".join(f"{name} {count}" for name, count in sorted(self.by_source.items())) or "none"
        return (
            f"Considered {self.considered} paper(s): {self.found} abstract(s) stored "
            f"({sources}), {self.skipped} already present, {self.missing} not found, {self.failed} failed."
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def collect_abstracts(
    shards_root: Path,
    *,
    venue: str | None = None,
    year: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    force: bool = False,
    mailto: str | None = None,
    s2_api_key: str | None = None,
    sources: tuple[str, ...] = ALL_SOURCES,
    log: Log = print,
) -> Report:
    """Fills ``metadata.abstract`` for every paper under ``shards_root``.

    Official-page lanes run concurrently; the API passes then run one after
    another over whatever is still missing, fastest source first. ``sources``
    selects which passes run (see ``ALL_SOURCES``).
    """
    report = Report()
    fetcher = Fetcher(mailto=mailto, s2_api_key=s2_api_key, log=log)
    lock = threading.Lock()
    stored: set[str] = set()

    pending: list[Path] = []
    for metadata_path in sorted(shards_root.resolve().rglob("metadata.json")):
        relative = metadata_path.relative_to(shards_root.resolve()).parts
        if venue and relative[0] != venue:
            continue
        if year and relative[1] != str(year):
            continue
        metadata = load_json(metadata_path)
        report.considered += 1
        if metadata.get("abstract") and not force:
            report.skipped += 1
            continue
        pending.append(metadata_path)
        if limit and len(pending) >= limit:
            break

    def store(metadata_path: Path, metadata: dict[str, Any], found: Found, label: str) -> None:
        with lock:
            report.found += 1
            report.by_source[found.source["kind"]] = report.by_source.get(found.source["kind"], 0) + 1
            stored.add(metadata["paper_id"])
            log(f"[{label}] {metadata['paper_id']} <- {found.source['kind']} ({len(found.text)} chars)")
        if not dry_run:
            _write_json(metadata_path, with_abstract(metadata, found.text, found.source))

    def remaining() -> list[Path]:
        return [path for path in pending if load_json(path)["paper_id"] not in stored]

    # Pass 1: official pages, one thread per site.
    lanes: dict[str, list[Path]] = {}
    for metadata_path in pending if "official" in sources else []:
        lane = lane_for(load_json(metadata_path))
        if official_page_strategy(lane) is not None:
            lanes.setdefault(lane, []).append(metadata_path)

    def run_lane(lane: str, paths: list[Path]) -> None:
        strategy = official_page_strategy(lane)
        assert strategy is not None
        for index, metadata_path in enumerate(paths, start=1):
            metadata = load_json(metadata_path)
            try:
                found = strategy(metadata, fetcher)
            except FetchError as error:
                with lock:
                    log(f"[{lane} {index}/{len(paths)}] {metadata['paper_id']}: {error}; deferred to the API passes")
                continue
            if found:
                store(metadata_path, metadata, found, f"{lane} {index}/{len(paths)}")

    threads = [threading.Thread(target=run_lane, args=(lane, paths), name=lane) for lane, paths in lanes.items()]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Pass 2: OpenAlex, quick and generous.
    paths = remaining() if "openalex" in sources else []
    for index, metadata_path in enumerate(paths, start=1):
        metadata = load_json(metadata_path)
        try:
            found = _openalex(metadata, fetcher)
        except FetchError as error:
            log(f"[openalex {index}/{len(paths)}] {metadata['paper_id']}: {error}")
            continue
        if found:
            store(metadata_path, metadata, found, f"openalex {index}/{len(paths)}")

    # Pass 3: Semantic Scholar batches by DOI.
    paths = [path for path in remaining() if normalize_doi(load_json(path)["links"].get("doi"))] if "s2-batch" in sources else []
    for start in range(0, len(paths), SEMANTIC_SCHOLAR_BATCH_SIZE):
        chunk = paths[start:start + SEMANTIC_SCHOLAR_BATCH_SIZE]
        batch = [load_json(path) for path in chunk]
        label = f"s2-batch {start // SEMANTIC_SCHOLAR_BATCH_SIZE + 1}/{(len(paths) - 1) // SEMANTIC_SCHOLAR_BATCH_SIZE + 1}"
        try:
            found_by_id = _semantic_scholar_batch(batch, fetcher)
        except FetchError as error:
            log(f"[{label}] {error}")
            continue
        for metadata_path, metadata in zip(chunk, batch):
            found = found_by_id.get(metadata["paper_id"])
            if found:
                store(metadata_path, metadata, found, label)
        log(f"[{label}] {len(found_by_id)}/{len(batch)} abstracts")

    # Pass 4: Semantic Scholar title match; pass 5: arXiv.
    for name, strategy in (("s2-match", _semantic_scholar_match), ("arxiv", _arxiv)):
        if name not in sources:
            continue
        paths = remaining()
        for index, metadata_path in enumerate(paths, start=1):
            metadata = load_json(metadata_path)
            try:
                found = strategy(metadata, fetcher)
            except FetchError as error:
                log(f"[{name} {index}/{len(paths)}] {metadata['paper_id']}: {error}")
                continue
            if found:
                store(metadata_path, metadata, found, f"{name} {index}/{len(paths)}")

    for metadata_path in remaining():
        paper_id = load_json(metadata_path)["paper_id"]
        report.missing += 1
        report.missing_ids.append(paper_id)
        log(f"no abstract found for {paper_id}")
    return report
