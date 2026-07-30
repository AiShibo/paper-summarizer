from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_title))


def slugify(value: str, max_length: int = 56) -> str:
    slug = normalize_title(value).replace(" ", "-").strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or "untitled"


def paper_id(venue: str, year: int, title: str) -> str:
    normalized = normalize_title(title)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]
    return f"{venue}-{year}-{slugify(title)}-{digest}"
