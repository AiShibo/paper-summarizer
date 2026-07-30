# Delegated task set

These briefs are paste-ready instructions for independent agents. Give each
agent exactly one brief. The ownership boundaries are designed so agents can
work in parallel without editing the same source file.

## Execution order

| Wave | Parallel tasks | Gate |
| --- | --- | --- |
| 0 | Coordinator freezes schemas and task boundaries | Framework checks pass |
| 1 | Agents A–D collect and classify the 2025 pilot | Draft validation and coverage audit |
| 2 | Agents E, F, G, and I work on approved pilot IDs | Summary/group/award evidence ready |
| 3 | Agent H independently reviews the pilot | No open release-blocking issues |
| 4 | Agents A–G repeat for 2023, 2024, and available 2026 data | Per-venue coverage reports pass |
| 5 | Coordinator merges, exports, and hands data to Agent I | Release validation and integrity checks pass |

Do not start bulk 2023–2026 summarization merely because collection has begun.
The coordinator must explicitly open Wave 4 after the 2025 pilot exposes and
resolves schema or policy problems.

## Ownership matrix

| Brief | Role | Exclusive writes |
| --- | --- | --- |
| [Coordinator](task-00-coordinator.md) | Merge and phase gates | Shared contracts and generated artifacts |
| [Agent A](agent-a-systems-collection.md) | OSDI, SOSP, EuroSys, ATC | `venue-year.json`, `metadata.json`, `relevance.json` in assigned shards |
| [Agent B](agent-b-storage-networking-collection.md) | FAST, NSDI, SIGCOMM | Same stages in assigned shards |
| [Agent C](agent-c-asplos-collection.md) | ASPLOS | Same stages in ASPLOS shards |
| [Agent D](agent-d-security-collection.md) | CCS, NDSS, IEEE S&P, USENIX Security | Same stages in security shards |
| [Agent E](agent-e-paper-summaries.md) | Beginner summaries | Assigned `summary.json` files only |
| [Agent F](agent-f-faculty-groups.md) | Faculty, labs, institutions, geography | Assigned `groups.json` and `data/entities/**` |
| [Agent G](agent-g-awards.md) | Official awards | Assigned `awards.json` files only |
| [Agent H](agent-h-independent-review.md) | Independent audit | Assigned `review.json` and own review-queue directory |
| [Agent I](agent-i-frontend.md) | Static frontend and search | Frontend source and frontend-only tests |

## Universal rules

Every agent must:

1. Read `AGENTS.md`, `docs/data-layout.md`, `docs/paper-field-map.md`, and the
   policy named by their brief.
2. Create only `coordination/claims/<agent-id>.json` from the claim template.
3. Work only on explicitly assigned paths.
4. Preserve null/unknown states instead of guessing.
5. Use official sources first and record provenance.
6. Run the validation command in the brief.
7. Hand off exact changed paths, source URLs, counts, unresolved fields, and
   review items.

No collection or specialist agent may edit:

- `data/database.sqlite`;
- `data/venue-year-manifest.json`;
- `data/venue-year-manifest.generated.json`;
- `data/exports/`;
- `site/data/papers.json`;
- schemas, migrations, shared configuration, or policies; or
- another agent's claim file.

If a shared contract appears wrong, stop only that affected record, document
the issue in the handoff, and ask the coordinator for a versioned change.

## Assignment granularity

Collector tasks are partitioned by venue folders. Specialist tasks span venues
but are partitioned by stage filename. If more than one summary, group, award,
or review agent is used, the coordinator must assign disjoint paper-ID lists;
two agents must never own the same stage file.

The machine-readable read-only ownership map is
`coordination/tasks/ownership.json`.
