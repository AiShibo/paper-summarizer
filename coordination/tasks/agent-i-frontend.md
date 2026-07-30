# Agent I — Static frontend and client-side search

## Paste-ready instruction

You are Agent I, responsible for the static user interface, client-side search,
filters, comparison views, and local-only user features. Treat generated corpus
data as a read-only contract.

Read `AGENTS.md`, `docs/scope.md`, `docs/architecture.md`,
`docs/data-layout.md`, and the website/UX requirements in `Tasks.md`.

## Exclusive write scope

You may edit only:

```text
site/index.html
site/styles.css
site/app.js
site/pages/**
site/components/**
site/data/fixture-papers.json
tests/frontend/**
coordination/claims/<your-agent-id>.json
```

Do not edit `site/data/papers.json`, real shards, SQLite, exports, schemas,
taxonomy, entities, or pipeline code. Ask the coordinator for an export-contract
change rather than patching generated JSON.

## Work phases

### Pilot interface

Use clearly synthetic fixture data to implement:

- dense readable paper cards/table;
- keyword and exact-phrase search;
- include/exclude terms;
- matching-field highlights;
- venue, year, relevance, topic, method, layer, geography, institution, group,
  faculty, award, and artifact/code filters supported by fixture fields;
- filter state encoded in shareable URLs;
- visible incomplete-2026 and low-confidence states;
- keyboard access, responsive layout, accessible contrast, and light/dark
  themes; and
- graceful empty/loading/error states.

### Entity discovery

After the coordinator provides stable exports, add paper details, faculty,
group, institution, topic, geography, and two-to-five-supervisor comparison.
Any match score must expose its inputs and weights; never create a hidden
prestige ranking.

### Local user features

Store stars, unread/skimmed/read state, private notes, custom tags, shortlists,
and saved searches in local browser storage without login. Support explicit
CSV, JSON, and BibTeX export when the export contract is available.

## Search requirements

Search across title, story fields, mechanisms, tags, authors, faculty, groups,
institutions, cities, and countries. Support multiple terms, quoted phrases,
exclusions, typo tolerance, and match highlighting. Keep search client-side
where practical.

## Quality rules

- Do not show fixture records as real.
- Do not present paper count as advisor quality.
- Show source/verification and confidence where the export provides them.
- No horizontal scrolling for ordinary use.
- Preserve usable mobile layouts while optimizing for desktop research.
- Do not add network-dependent fonts or decorative assets that slow initial
  load without a clear UX benefit.

## Validation

Run:

```sh
node --check site/app.js
```

```sh
python3 -m http.server 8000 --directory site
```

Then test keyboard navigation, URL restoration, local state persistence,
responsive breakpoints, both themes, fixture fallback, and the empty state.

## Handoff

Report files changed, fixture/export schema assumptions, implemented views and
filters, accessibility checks, browser/manual tests, known performance limits,
and any data-contract changes requested from the coordinator.
