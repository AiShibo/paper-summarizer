# Source and provenance policy

## Priority

Use sources in this order:

1. official conference program or proceedings;
2. official publisher page;
3. official paper PDF;
4. official artifact or project page;
5. official institution, faculty, or lab page;
6. DBLP; and
7. OpenAlex, Crossref, or Semantic Scholar as fallback metadata sources.

Lower-priority sources may locate an official source but do not override one
without an explicit review note.

## Source records

Each stage file contains the sources it used. A source record includes:

- stable source ID;
- URL;
- source kind;
- page title when known;
- publisher or owner when known;
- retrieval timestamp;
- optional content hash;
- whether it is official; and
- notes about what it supports.

Important numerical summary claims additionally cite source IDs and a page,
section, figure, or table locator when available.

Do not cite search-result snippets as evidence.

## Verification

Every stage file records:

- collection timestamp;
- last-verification timestamp;
- collector/tool version;
- confidence (`VERIFIED`, `HIGH`, `MEDIUM`, `LOW`, or `UNRESOLVED`);
- unresolved fields; and
- workflow/review status.

`VERIFIED` means the field was checked against an appropriate authoritative
source. It does not mean the authors' scientific claims were independently
replicated.

## Faculty and group evidence

Never infer a PI from author position. A paper-group association requires at
least one of:

- an official lab publication page;
- an official faculty publication page;
- an official student profile naming the advisor;
- an institution page; or
- the paper/project page explicitly naming the group.

When evidence is insufficient, retain author and affiliation data, set the
association unresolved, and create a review item.

Publication-time affiliation and current affiliation are different fields.
Faculty moves never rewrite historical authorship data.

## Awards

An award requires an official conference or sponsoring-organization source.
Author CVs, lab news posts, social media, and snippets can help locate that
source but cannot be the final evidence.

Store the exact award name and its category. Do not collapse distinct awards
into a generic winner flag.

## PDFs and media

Paper PDFs may be downloaded temporarily for text extraction. Delete the
temporary file after extraction and retain only the URL, content hash, metadata,
reading record, and structured summary. Do not archive conference videos or
bulk PDF collections in this repository.

## Failed and conflicting evidence

Record per-record failures in `data/logs/` locally. Put unresolved factual
conflicts in the appropriate `review.json` or generated review queue. Never
silently choose a value simply to make a field non-null.
