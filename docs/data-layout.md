# Data layout

## Design objective

Agent-authored data is partitioned first by venue and year, then by paper, then
by work stage. This keeps collection agents from touching the same directories
and keeps specialist agents from touching the same files.

SQLite becomes the canonical local query store only after a deterministic,
validated merge. Agents never edit it directly.

## Venue/year shard

```text
data/shards/<venue>/<year>/
├── venue-year.json
└── papers/
    └── <paper-id>/
        ├── metadata.json
        ├── relevance.json
        ├── summary.json
        ├── groups.json
        ├── awards.json
        └── review.json
```

Canonical venue slugs are defined in `config/venues.json`. Supported years are
2023, 2024, 2025, and 2026.

`venue-year.json` holds official venue/year URLs, conference dates, coverage
status, counts, sources, and verification. It is owned by the venue collector.

## Paper ID

The initializer creates:

```text
<venue>-<year>-<normalized-title-prefix>-<title-hash>
```

The hash is derived from the normalized exact title, so independent agents get
the same candidate ID for the same venue paper. Deduplication may later mark
aliases, but an established ID must not be renamed casually.

Always run `init-paper`; do not invent IDs by hand:

```sh
PYTHONPATH=src python3 -m systems_phd_explorer.cli init-paper \
  --venue nsdi --year 2025 --title "Exact Title" --owner agent-b
```

## Stage files

### `metadata.json`

Collector-owned identity and publication facts:

- exact title and ordered authors;
- publication-time affiliations;
- track/session and paper type;
- DOI and official links;
- alternate versions;
- dates and venue-year status; and
- source and verification records.

### `relevance.json`

Classifier-owned decision:

- relevance class and 0–5 fit score;
- one-sentence rationale;
- topic IDs;
- system layers;
- contribution types;
- methods; and
- supporting evidence and confidence.

### `summary.json`

Summary-writer-owned story:

- one-line takeaway;
- background, villain, approach, impact;
- structured evaluation;
- limitations and assumptions;
- PhD-group signal;
- beginner concepts;
- reading coverage; and
- claim-level provenance for important facts and numbers.

### `groups.json`

Resolver-owned evidence:

- zero or more group and faculty associations;
- publication-time and current institution references;
- exact evidence supporting each association;
- unresolved authors; and
- confidence and verification date.

### `awards.json`

Award-verifier-owned facts:

- exact official award name;
- award category;
- venue/year and paper;
- official source; and
- verification date.

An empty, verified list means “checked and no official paper-level award was
found.” A `NOT_STARTED` list means “not checked”; those are not equivalent.

### `review.json`

Independent-reviewer-owned checks and issues. The summary writer or original
collector must not approve their own work.

## Resolved entities

Resolved entities use one file per stable entity:

```text
data/entities/
├── authors/<author-id>.json
├── faculty/<faculty-id>.json
├── research-groups/<group-id>.json
└── institutions/<institution-id>.json
```

One-file-per-entity makes normal Git merges independent. Agent F normally owns
these directories. If two candidate files refer to the same person, keep both,
flag a possible duplicate, and let the merge/review process resolve it.

## Generated paths

These are not agent editing surfaces:

- `data/database.sqlite`
- `data/exports/`
- `data/venue-year-manifest.generated.json`
- `data/review_queue/generated/`
- `site/data/papers.json`

The committed `data/venue-year-manifest.json` is the initial Phase 0 coverage
contract. The merge command emits the generated live manifest from independent
shard files.

## Schemas and profiles

All JSON files declare schema version `1.0.0` and point to `schemas/v1/`.

- `draft`: validates structure, identity, paths, enumerations, and cross-file
  paper IDs while allowing incomplete workflow stages.
- `release`: additionally requires approved core-paper summaries, evidence for
  PI associations and awards, resolved coverage counts, and reading/provenance
  requirements.
