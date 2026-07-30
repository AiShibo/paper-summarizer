# Scope

## Product goal

Systems PhD Explorer helps a student preparing for Fall 2027 PhD applications
understand systems research, discover active faculty and groups, compare
potential supervisors, and read source-backed beginner summaries of recent
papers.

It is a discovery system, not a paper-count ranking and not a claim that every
recent author is recruiting students.

## Time window

The default application-oriented window is calendar years 2023 through 2026
year-to-date. The data model must also support:

- a strict rolling 36-month window;
- a single selected year;
- complete years only; and
- explicit inclusion or exclusion of incomplete 2026 proceedings.

Conference dates, publication dates, and collection verification dates are
separate fields. An upcoming or unpublished program is never represented as
having zero papers.

## Venues

| Area | Venue | Canonical slug |
| --- | --- | --- |
| Systems | OSDI | `osdi` |
| Systems | SOSP | `sosp` |
| Systems | EuroSys | `eurosys` |
| Systems/architecture | ASPLOS | `asplos` |
| Systems | USENIX ATC | `atc` |
| Storage | FAST | `fast` |
| Networking | SIGCOMM | `sigcomm` |
| Networking | NSDI | `nsdi` |
| Security | ACM CCS | `ccs` |
| Security | NDSS | `ndss` |
| Security | IEEE S&P | `sp` |
| Security | USENIX Security | `usenix-security` |

Only official main peer-reviewed technical papers are corpus candidates.
Workshops, posters, demos, keynotes, invited talks, doctoral consortium items,
and non-archival abstracts are excluded unless the venue explicitly treats the
item as part of its archival main technical-paper program.

## Primary entities

- papers;
- authors and publication-time affiliations;
- faculty and potential PIs;
- research groups;
- institutions;
- topics;
- venue-years;
- awards;
- sources and claim provenance; and
- local user annotations.

The same paper may be associated with multiple groups. Historical affiliations
must remain distinct from current faculty affiliations.

## Phase 0 boundary

This repository starts with schemas, policies, migrations, agent-safe shards,
validation, merge tooling, isolated fixtures, pilot collector contracts, and a
minimal static frontend. Phase 0 does not claim real corpus completeness.

Bulk summarization must not start until the schema, source policy, and pilot
records have been reviewed.

## Completion semantics

Three independent statuses must not be conflated:

1. `workflow.status`: whether an agent has started or completed its stage;
2. `collection_status`: what is known about a venue-year program; and
3. `verification.confidence`: the strength of evidence for a record.

`NOT_STARTED`, `UNVERIFIED`, and `UNRESOLVED` are honest states, not zero values.
