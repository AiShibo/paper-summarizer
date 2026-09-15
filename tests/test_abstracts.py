"""Tests for the abstract collector's pure helpers (no network)."""

from __future__ import annotations

import unittest

from systems_phd_explorer.abstracts import (
    clean_text,
    extract_ndss,
    extract_usenix,
    lane_for,
    normalize_doi,
    openalex_abstract,
    titles_match,
    unique_source_id,
    usable_abstract,
    with_abstract,
)

LONG = "This sentence is long enough to count as a real abstract for testing purposes, honestly."


class CleaningTests(unittest.TestCase):
    def test_strips_tags_entities_and_leading_label(self) -> None:
        self.assertEqual(
            clean_text("<jats:p>Abstract: We &amp; they   build</jats:p><jats:p>Second.</jats:p>"),
            "We & they build\n\nSecond.",
        )

    def test_rejects_short_or_placeholder_abstracts(self) -> None:
        self.assertIsNone(usable_abstract(None))
        self.assertIsNone(usable_abstract("Too short."))
        self.assertIsNone(usable_abstract("No abstract available for this paper at this time, sorry about that."))
        self.assertEqual(usable_abstract(LONG), LONG)


class ExtractorTests(unittest.TestCase):
    def test_usenix_page(self) -> None:
        page = (
            '<div class="field field-name-field-paper-description field-type-text-long">'
            '<div class="field-items"><div class="field-item even"><p>' + LONG + "</p></div></div></div>"
        )
        self.assertEqual(extract_usenix(page), LONG)
        self.assertIsNone(extract_usenix("<html><body>no abstract here</body></html>"))

    def test_ndss_page_takes_longest_non_author_paragraph(self) -> None:
        page = (
            '<div class="paper-data"><p><strong><p>Author One (Uni), Author Two (Uni)</p></strong></p>'
            "<p>" + LONG + " " + LONG + "</p><p>Short trailing note.</p></div>"
            '<footer class="entry-footer"></footer>'
        )
        self.assertEqual(extract_ndss(page), LONG + " " + LONG)
        self.assertIsNone(extract_ndss("<div>nothing</div>"))

    def test_openalex_inverted_index_is_reordered(self) -> None:
        words = LONG.split()
        index: dict[str, list[int]] = {}
        for position, word in enumerate(words):
            index.setdefault(word, []).append(position)
        self.assertEqual(openalex_abstract(index), LONG)
        self.assertIsNone(openalex_abstract(None))


class MatchingTests(unittest.TestCase):
    def test_titles_match_ignores_case_and_punctuation(self) -> None:
        self.assertTrue(titles_match("Fast: A Storage System!", "fast a storage system"))
        self.assertTrue(titles_match("Fast: A Storage System", "Fast: A Storage Systems"))
        self.assertFalse(titles_match("Fast: A Storage System", "Slow: A Network Protocol"))
        self.assertFalse(titles_match("Fast", None))

    def test_doi_normalization(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1145/1.2"), "10.1145/1.2")
        self.assertEqual(normalize_doi("doi:10.1145/1.2"), "10.1145/1.2")
        self.assertIsNone(normalize_doi(None))

    def test_lane_selection(self) -> None:
        self.assertEqual(lane_for({"links": {"official_page": "https://www.usenix.org/x"}}), "usenix")
        self.assertEqual(lane_for({"links": {"official_page": "https://www.ndss-symposium.org/x"}}), "ndss")
        self.assertEqual(lane_for({"links": {"official_page": "https://dl.acm.org/doi/10.1145/1"}}), "api")
        self.assertEqual(lane_for({"links": {"official_page": None}}), "api")


class WriteTests(unittest.TestCase):
    def test_abstract_is_inserted_after_title_with_its_source(self) -> None:
        metadata = {
            "paper_id": "osdi-2025-example-01234567",
            "title": "Example",
            "venue": "osdi",
            "year": 2025,
            "sources": [{"id": "src-abstract-osdi-2025-01234567"}],
        }
        self.assertEqual(unique_source_id(metadata), "src-abstract-osdi-2025-01234567-2")
        source = {"id": "src-abstract-osdi-2025-01234567-2", "kind": "paper-page"}
        updated = with_abstract(metadata, LONG, source)
        self.assertEqual(list(updated)[:4], ["paper_id", "title", "abstract", "abstract_source_id"])
        self.assertEqual(updated["abstract"], LONG)
        self.assertEqual(updated["abstract_source_id"], "src-abstract-osdi-2025-01234567-2")
        self.assertEqual([entry["id"] for entry in updated["sources"]],
                         ["src-abstract-osdi-2025-01234567", "src-abstract-osdi-2025-01234567-2"])
        self.assertNotIn("abstract", metadata)


if __name__ == "__main__":
    unittest.main()
