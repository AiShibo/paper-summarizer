"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const {
  DEFAULT_FILTERS,
  annotationFor,
  editDistanceWithin,
  filterPapers,
  findHighlightRanges,
  normalizePaper,
  parseQuery,
  parseUrlState,
  recordsToBibtex,
  recordsToCsv,
  serializeFilters,
  termMatchesValue,
  validatePayload,
} = require("../../site/app.js");

const ROOT = path.resolve(__dirname, "../..");
const fixturePayload = JSON.parse(
  fs.readFileSync(path.join(ROOT, "site/data/fixture-papers.json"), "utf8")
);
const papers = fixturePayload.papers.map((paper) => normalizePaper(paper, true));

test("query parser preserves quoted phrases and exclusions", () => {
  assert.deepEqual(parseQuery('"distributed debugging" trace -security +"causal sketch"'), [
    {
      value: "distributed debugging",
      raw: "distributed debugging",
      excluded: false,
      phrase: true,
    },
    { value: "trace", raw: "trace", excluded: false, phrase: false },
    { value: "security", raw: "security", excluded: true, phrase: false },
    {
      value: "causal sketch",
      raw: "causal sketch",
      excluded: false,
      phrase: true,
    },
  ]);
});

test("ordinary terms tolerate bounded typos while quoted phrases remain exact", () => {
  const typo = parseQuery("kernal")[0];
  const exactPhrase = parseQuery('"kernal safety"')[0];
  assert.equal(termMatchesValue(typo, "kernel memory safety"), true);
  assert.equal(termMatchesValue(exactPhrase, "kernel safety"), false);
  assert.equal(editDistanceWithin("kernel", "kernal", 1), true);
  assert.equal(editDistanceWithin("kernel", "runtime", 2), false);
});

test("search spans story, mechanism, people, group, and geography fields", () => {
  const cases = [
    ["causal sketches", "fixture-distributed-debugging"],
    ['"bounded drift"', "fixture-distributed-debugging"],
    ["placeholder theorem", "fixture-formal-memory"],
    ["chiplet taipei", "fixture-architecture-ml"],
    ['"reliable storage example lab"', "fixture-storage-crash"],
  ];
  cases.forEach(([query, expectedId]) => {
    const results = filterPapers(papers, { ...DEFAULT_FILTERS, query }, {});
    assert.equal(results.length, 1, query);
    assert.equal(results[0].paper.id, expectedId, query);
    assert.ok(results[0].matchedFields.length > 0, query);
  });
});

test("excluded terms remove otherwise matching papers", () => {
  const included = filterPapers(
    papers,
    { ...DEFAULT_FILTERS, query: "runtime" },
    {}
  );
  const excluded = filterPapers(
    papers,
    { ...DEFAULT_FILTERS, query: "runtime -security" },
    {}
  );
  assert.ok(included.some((result) => result.paper.id === "fixture-security-isolation"));
  assert.ok(!excluded.some((result) => result.paper.id === "fixture-security-isolation"));
});

test("an impossible query returns the explicit empty result used by the UI", () => {
  const results = filterPapers(
    papers,
    { ...DEFAULT_FILTERS, query: '"no such synthetic mechanism"' },
    {}
  );
  assert.deepEqual(results, []);
});

test("advanced filters compose across the fixture export", () => {
  const filters = {
    ...DEFAULT_FILTERS,
    topic: "operating-systems-and-kernels",
    method: "implementation",
    layer: "kernel",
    contribution: "new-mechanism",
    institution: "North Coast Example University",
    group: "group-fixture-safe-systems",
    faculty: "faculty-avery-fixture",
    award: "distinguished-paper",
    country: "Canada",
    region: "Canada",
    city: "Vancouver",
    sector: "academic",
    availability: "both",
    completeOnly: true,
  };
  const results = filterPapers(papers, filters, {});
  assert.deepEqual(results.map((result) => result.paper.id), ["fixture-os-kernel"]);
});

test("complete-only filtering excludes partial and accepted-only 2026 records", () => {
  const all2026 = filterPapers(
    papers,
    { ...DEFAULT_FILTERS, year: "2026" },
    {}
  );
  const complete2026 = filterPapers(
    papers,
    { ...DEFAULT_FILTERS, year: "2026", completeOnly: true },
    {}
  );
  assert.equal(all2026.length, 2);
  assert.equal(complete2026.length, 0);
});

test("private library filters and private search fields remain local inputs", () => {
  const library = {
    "fixture-network-congestion": {
      starred: true,
      reading: "read",
      notes: "Revisit the uncertainty model",
      tags: ["favorite transport"],
      shortlists: ["Networking faculty"],
    },
  };
  const filters = {
    ...DEFAULT_FILTERS,
    query: '"uncertainty model"',
    starredOnly: true,
    reading: "read",
    shortlist: "Networking faculty",
  };
  const results = filterPapers(papers, filters, library);
  assert.deepEqual(results.map((result) => result.paper.id), [
    "fixture-network-congestion",
  ]);
  assert.deepEqual(annotationFor(library, "missing-paper"), {
    starred: false,
    reading: "unread",
    notes: "",
    tags: [],
    shortlists: [],
  });
});

test("URL serialization round-trips public search state and omits private filters", () => {
  const filters = {
    ...DEFAULT_FILTERS,
    query: '"distributed systems" -security',
    timeWindow: "rolling36",
    venue: "sosp",
    topic: "distributed-systems",
    completeOnly: true,
    view: "table",
    sort: "title",
    starredOnly: true,
    reading: "read",
    shortlist: "Private shortlist",
  };
  const serialized = serializeFilters(filters);
  const restored = parseUrlState(`?${serialized}`);
  assert.equal(restored.query, filters.query);
  assert.equal(restored.timeWindow, "rolling36");
  assert.equal(restored.venue, "sosp");
  assert.equal(restored.topic, "distributed-systems");
  assert.equal(restored.completeOnly, true);
  assert.equal(restored.view, "table");
  assert.equal(restored.sort, "title");
  assert.equal(restored.starredOnly, false);
  assert.equal(restored.reading, "");
  assert.equal(restored.shortlist, "");
});

test("highlight ranges include fuzzy token matches", () => {
  const text = "Safer extensible kernels";
  const ranges = findHighlightRanges(text, parseQuery("kernal"));
  assert.deepEqual(ranges, [[17, 24]]);
  assert.equal(text.slice(ranges[0][0], ranges[0][1]), "kernels");
});

test("CSV and BibTeX exports explicitly carry local state and core identity", () => {
  const record = {
    id: "fixture-export",
    title: "Synthetic, Quoted Paper",
    venue: "osdi",
    year: 2025,
    authors: ["Avery Example", "Morgan Sample"],
    takeaway: "A fixture.",
    relevance_class: "CORE_SYSTEMS",
    topics: ["operating-systems-and-kernels"],
    methods: ["implementation"],
    institutions: ["Example University"],
    faculty: [],
    groups: [],
    countries: ["Canada"],
    has_code: true,
    has_artifact: false,
    links: {},
    local_annotation: {
      reading: "skimmed",
      starred: true,
      tags: ["follow up"],
      shortlists: ["Canada"],
      notes: "Compare assumptions.",
    },
  };
  const csv = recordsToCsv([record]);
  const bibtex = recordsToBibtex([record]);
  assert.match(csv, /"Synthetic, Quoted Paper"/);
  assert.match(csv, /Compare assumptions\./);
  assert.match(bibtex, /@inproceedings/);
  assert.match(bibtex, /author = \{Avery Example and Morgan Sample\}/);
});

test("fixture export is valid and every record is unmistakably synthetic", () => {
  assert.equal(validatePayload(fixturePayload), fixturePayload);
  assert.equal(fixturePayload.is_fixture_export, true);
  assert.ok(fixturePayload.papers.length >= 8);
  fixturePayload.papers.forEach((paper) => {
    assert.equal(paper.is_fixture, true);
    assert.match(paper.title, /^\[Synthetic fixture\]/);
    assert.equal(paper.links.official_page, null);
    assert.equal(paper.links.official_pdf, null);
  });
  assert.ok(fixturePayload.papers.some((paper) => paper.is_incomplete_venue_year));
  assert.ok(
    fixturePayload.papers.some((paper) =>
      ["LOW", "UNRESOLVED"].includes(paper.confidence)
    )
  );
});
