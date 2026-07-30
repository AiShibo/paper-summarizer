# Architecture

```text
official sources
      │
      ▼
agent-owned JSON stage files
      │
      ├── schema validation
      ├── cross-file validation
      ├── duplicate checks
      └── review queue
      │
      ▼
atomic SQLite merge
      │
      ├── static JSON search export
      ├── CSV / BibTeX exports
      └── coverage and quality reports
      │
      ▼
static client-side website
```

## Invariants

- Collection is resumable and idempotent.
- One exact paper has one canonical conference record.
- The official conference version remains canonical; preprints and journal
  versions are linked as alternates.
- Generated artifacts are reproducible from validated shards.
- PDFs and videos are not permanent repository data.
- Every externally visible factual record exposes provenance and verification.
- Release validation fails closed on unsupported awards and PI associations.
- Local user notes and shortlists remain in the browser unless explicitly
  exported.

## Atomic database build

The merge command creates a temporary SQLite file, applies ordered migrations,
imports validated fragments in stable path order, runs integrity checks, and
atomically replaces the requested output. A failed build leaves the prior
database untouched.

## Static-first frontend

The website reads a compact generated paper index and performs search and
filtering in the browser. Detail exports can be split by entity later without
changing the staging layout. Filter state belongs in the URL, while private
stars, reading state, notes, tags, and shortlists belong in local browser
storage.
