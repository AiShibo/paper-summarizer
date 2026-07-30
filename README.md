# Systems PhD Explorer

Systems PhD Explorer is a static-first research discovery project for students
preparing systems PhD applications. It organizes recent papers, beginner
summaries, research groups, potential supervisors, institutions, and evidence
provenance without turning paper counts into prestige rankings.

This repository currently contains the Phase 0 framework. Paper data is staged
as conflict-resistant JSON fragments and merged into a local SQLite database
only after validation.

## Quick start

Requirements:

- Python 3.11 or newer
- `jsonschema` 4.23 or newer

Run the checks:

```sh
make check
```

Create a paper bundle in an agent-owned venue/year shard:

```sh
PYTHONPATH=src python3 -m systems_phd_explorer.cli init-paper \
  --venue osdi \
  --year 2025 \
  --title "Exact published title" \
  --owner agent-a
```

Initialize an upcoming or unavailable venue-year even when it has no paper
records yet:

```sh
PYTHONPATH=src python3 -m systems_phd_explorer.cli init-venue \
  --venue sosp \
  --year 2026 \
  --owner agent-a
```

Validate staged data:

```sh
PYTHONPATH=src python3 -m systems_phd_explorer.cli validate \
  --root data/shards \
  --profile draft
```

Build the canonical local database:

```sh
PYTHONPATH=src python3 -m systems_phd_explorer.cli build-db \
  --root data/shards \
  --output data/database.sqlite
```

Preview the fixture website:

```sh
python3 -m http.server 8000 --directory site
```

Then open `http://localhost:8000`.

## Where paper information goes

Every paper gets its own directory:

```text
data/shards/<venue>/<year>/papers/<paper-id>/
├── metadata.json       # venue collector
├── relevance.json      # relevance classifier
├── summary.json        # summary writer
├── groups.json         # faculty/lab resolver
├── awards.json         # award verifier
└── review.json         # independent reviewer
```

For example:

```text
data/shards/osdi/2025/papers/osdi-2025-example-title-a1b2c3d4/
```

The files are deliberately separated by responsibility so agents working on
the same paper do not edit the same file. See
[`docs/data-layout.md`](docs/data-layout.md) and
[`docs/paper-field-map.md`](docs/paper-field-map.md) for exact field placement,
then read [`docs/agent-workflow.md`](docs/agent-workflow.md) before delegating
work.

## Repository map

```text
collectors/             Venue collector adapters and pilot configuration
config/                 Stable venue and taxonomy configuration
coordination/           Per-agent claim files
data/shards/            Agent-authored paper fragments, by venue and year
data/entities/          One-file-per-entity resolved people/groups/institutions
data/review_queue/      Generated human-review items
docs/                   Scope and policy documents
migrations/             Versioned SQLite migrations
schemas/v1/             Versioned JSON Schemas
site/                   Static client-side interface and fixture export
src/                    Validation, initialization, and merge tooling
tests/                  Unit tests and isolated fixtures
```

`data/database.sqlite`, exports, logs, caches, and downloaded PDFs are generated
artifacts and are not edited or committed by collection agents.

## Delegating work

Use the paste-ready briefs in
[`coordination/tasks/README.md`](coordination/tasks/README.md). They define a
coordinator plus Agents A–I, execution waves, exclusive paths, validation
commands, and handoff criteria. Give each agent one brief and require a unique
claim file before it edits data.

## Current status

The structure, policies, schemas, 2023–2026 venue/year manifest, merge tooling,
and fixture frontend are present. The corpus is intentionally empty. No venue
coverage, award, group association, or paper summary should be treated as
verified until its source-backed stage file passes review.
