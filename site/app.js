"use strict";

const APP_NAME = "Systems PhD Explorer";
const PAGE_SIZE = 60;
const LIBRARY_KEY = "systems-phd-explorer:library:v1";
const LEGACY_FAVORITES_KEY = "systems-phd-explorer:favorites:v1";
const SAVED_SEARCHES_KEY = "systems-phd-explorer:saved-searches:v1";
const THEME_KEY = "systems-phd-explorer:theme";

const LABEL_OVERRIDES = {
  asplos: "ASPLOS",
  atc: "USENIX ATC",
  ccs: "CCS",
  eurosys: "EuroSys",
  fast: "FAST",
  ndss: "NDSS",
  nsdi: "NSDI",
  osdi: "OSDI",
  sigcomm: "SIGCOMM",
  sosp: "SOSP",
  sp: "IEEE S&P",
  "usenix-security": "USENIX Security",
  "CORE_SYSTEMS": "Core systems",
  "SYSTEMS_ADJACENT": "Systems-adjacent",
  "NEEDS_HUMAN_REVIEW": "Needs human review",
  "EXCLUDED": "Excluded",
  "COMPLETE_PROCEEDINGS": "Complete proceedings",
  "ACCEPTED_PAPERS_ONLY": "Accepted papers only",
  "PARTIAL": "Partial proceedings",
  "UPCOMING": "Upcoming",
  "UNAVAILABLE": "Unavailable",
  "UNVERIFIED": "Coverage unverified",
  VERIFIED: "Verified",
  HIGH: "High confidence",
  MEDIUM: "Medium confidence",
  LOW: "Low confidence",
  UNRESOLVED: "Unresolved confidence",
  "eBPF": "eBPF",
  "ml-systems": "ML systems",
  "mobile-edge-embedded-and-iot": "Mobile, edge, embedded & IoT",
  "compilers-languages-and-runtimes": "Compilers, languages & runtimes",
  "formal-methods-and-systems-verification": "Formal methods & systems verification",
};

const DEFAULT_FILTERS = Object.freeze({
  query: "",
  timeWindow: "application",
  venue: "",
  year: "",
  relevance: "",
  availability: "",
  topic: "",
  method: "",
  layer: "",
  contribution: "",
  institution: "",
  group: "",
  faculty: "",
  award: "",
  region: "",
  country: "",
  city: "",
  sector: "",
  completeOnly: false,
  starredOnly: false,
  reading: "",
  shortlist: "",
  sort: "newest",
  view: "cards",
});

const URL_FIELDS = Object.freeze({
  query: "q",
  timeWindow: "window",
  venue: "venue",
  year: "year",
  relevance: "relevance",
  availability: "availability",
  topic: "topic",
  method: "method",
  layer: "layer",
  contribution: "contribution",
  institution: "institution",
  group: "group",
  faculty: "faculty",
  award: "award",
  region: "region",
  country: "country",
  city: "city",
  sector: "sector",
  completeOnly: "complete",
  sort: "sort",
  view: "view",
});

const FILTER_LABELS = Object.freeze({
  query: "Search",
  timeWindow: "Window",
  venue: "Venue",
  year: "Year",
  relevance: "Relevance",
  availability: "Availability",
  topic: "Topic",
  method: "Method",
  layer: "Layer",
  contribution: "Contribution",
  institution: "Institution",
  group: "Group",
  faculty: "Faculty",
  award: "Award",
  region: "Region",
  country: "Country",
  city: "City",
  sector: "Collaboration",
  completeOnly: "Complete venue-years",
  starredOnly: "Starred only",
  reading: "Reading state",
  shortlist: "Shortlist",
});

const ADVANCED_FILTER_KEYS = Object.freeze([
  "topic",
  "method",
  "layer",
  "contribution",
  "institution",
  "group",
  "faculty",
  "award",
  "region",
  "country",
  "city",
  "sector",
  "completeOnly",
  "starredOnly",
  "reading",
  "shortlist",
]);

const app = {
  papers: [],
  filters: { ...DEFAULT_FILTERS },
  library: {},
  savedSearches: [],
  results: [],
  visibleLimit: PAGE_SIZE,
  fixtureExport: false,
  hasFixtureRecords: false,
  loading: true,
  elements: {},
  searchTimer: null,
  toastTimer: null,
};

function asArray(value) {
  if (value === null || value === undefined || value === "") return [];
  return Array.isArray(value) ? value : [value];
}

function uniqueStrings(values) {
  const seen = new Set();
  return values
    .map((value) => String(value ?? "").trim())
    .filter((value) => {
      const key = value.toLocaleLowerCase();
      if (!value || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function humanize(value) {
  const text = String(value ?? "");
  if (!text) return "";
  if (LABEL_OVERRIDES[text]) return LABEL_OVERRIDES[text];
  const words = text
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\s+/g, " ")
    .trim();
  return words.replace(/\b\p{L}/gu, (letter) => letter.toLocaleUpperCase());
}

function normalizeForSearch(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function tokenize(value) {
  return normalizeForSearch(value).match(/[\p{L}\p{N}]+/gu) || [];
}

function parseQuery(input) {
  const source = String(input ?? "");
  const terms = [];
  let index = 0;

  while (index < source.length) {
    while (index < source.length && /\s/.test(source[index])) index += 1;
    if (index >= source.length) break;

    let excluded = false;
    if ((source[index] === "-" || source[index] === "+") && !/\s/.test(source[index + 1] || "")) {
      excluded = source[index] === "-";
      index += 1;
    }

    let phrase = false;
    let raw = "";
    if (source[index] === '"') {
      phrase = true;
      index += 1;
      while (index < source.length && source[index] !== '"') {
        raw += source[index];
        index += 1;
      }
      if (source[index] === '"') index += 1;
    } else {
      while (index < source.length && !/\s/.test(source[index])) {
        raw += source[index];
        index += 1;
      }
    }

    const value = normalizeForSearch(raw);
    if (value) terms.push({ value, raw: raw.trim(), excluded, phrase });
  }

  return terms;
}

function maxTypoDistance(term) {
  if (term.length >= 8) return 2;
  if (term.length >= 4) return 1;
  return 0;
}

function editDistanceWithin(left, right, maximum) {
  if (Math.abs(left.length - right.length) > maximum) return false;
  if (left === right) return true;
  if (maximum === 0) return false;

  let previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    const current = [leftIndex];
    let rowMinimum = current[0];
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const cost = left[leftIndex - 1] === right[rightIndex - 1] ? 0 : 1;
      current[rightIndex] = Math.min(
        current[rightIndex - 1] + 1,
        previous[rightIndex] + 1,
        previous[rightIndex - 1] + cost
      );
      rowMinimum = Math.min(rowMinimum, current[rightIndex]);
    }
    if (rowMinimum > maximum) return false;
    previous = current;
  }
  return previous[right.length] <= maximum;
}

function fuzzyTokenMatches(token, term) {
  const maximum = maxTypoDistance(term);
  if (!maximum) return token === term;
  const tokenForms = token.endsWith("s") && token.length > 4 ? [token, token.slice(0, -1)] : [token];
  const termForms = term.endsWith("s") && term.length > 4 ? [term, term.slice(0, -1)] : [term];
  return tokenForms.some((tokenForm) =>
    termForms.some((termForm) => editDistanceWithin(tokenForm, termForm, maximum))
  );
}

function termMatchesValue(term, value) {
  const normalized = normalizeForSearch(value);
  if (!normalized) return false;
  if (normalized.includes(term.value)) return true;
  if (term.phrase) return false;
  const distance = maxTypoDistance(term.value);
  if (!distance) return false;
  return tokenize(normalized).some((token) => fuzzyTokenMatches(token, term.value));
}

function findHighlightRanges(value, terms) {
  const text = String(value ?? "");
  const lowered = text.toLocaleLowerCase();
  const ranges = [];

  terms
    .filter((term) => !term.excluded)
    .forEach((term) => {
      let start = 0;
      let foundExact = false;
      while (start < lowered.length) {
        const index = lowered.indexOf(term.value, start);
        if (index < 0) break;
        ranges.push([index, index + term.value.length]);
        foundExact = true;
        start = index + Math.max(1, term.value.length);
      }
      if (foundExact || term.phrase || !maxTypoDistance(term.value)) return;

      for (const match of text.matchAll(/[\p{L}\p{N}]+/gu)) {
        const token = normalizeForSearch(match[0]);
        if (fuzzyTokenMatches(token, term.value)) {
          ranges.push([match.index, match.index + match[0].length]);
        }
      }
    });

  return ranges
    .sort((left, right) => left[0] - right[0] || left[1] - right[1])
    .reduce((merged, range) => {
      const previous = merged.at(-1);
      if (previous && range[0] <= previous[1]) {
        previous[1] = Math.max(previous[1], range[1]);
      } else {
        merged.push([...range]);
      }
      return merged;
    }, []);
}

function flattenText(value) {
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.map(flattenText).filter(Boolean).join(" ");
  if (value && typeof value === "object") {
    return Object.values(value).map(flattenText).filter(Boolean).join(" ");
  }
  return "";
}

function normalizeEntities(primary, fallbackIds = []) {
  const entities = [];
  const seen = new Set();

  function add(item) {
    if (item === null || item === undefined || item === "") return;
    const object = typeof item === "object" ? item : null;
    const rawValue = object
      ? object.id || object.value || object.name || object.label
      : item;
    const value = String(rawValue ?? "").trim();
    if (!value || seen.has(value.toLocaleLowerCase())) return;
    const rawLabel = object ? object.name || object.label || value : value;
    const label =
      String(rawLabel).includes(" ") || /[A-Z]/.test(String(rawLabel))
        ? String(rawLabel)
        : humanize(rawLabel);
    seen.add(value.toLocaleLowerCase());
    entities.push({ value, label });
  }

  asArray(primary).forEach(add);
  asArray(fallbackIds).forEach(add);
  return entities;
}

function normalizeAwards(value) {
  return asArray(value)
    .map((award) => {
      if (typeof award === "string") return { name: award, category: award };
      if (!award || typeof award !== "object") return null;
      const name = String(award.name || award.official_name || award.category || "").trim();
      const category = String(award.category || award.name || award.official_name || "").trim();
      return name || category ? { name, category } : null;
    })
    .filter(Boolean);
}

function normalizeSources(value) {
  return asArray(value)
    .map((source) => {
      if (typeof source === "string") return { label: source, url: null, type: "" };
      if (!source || typeof source !== "object") return null;
      return {
        label: String(source.label || source.title || source.type || "Source"),
        url: source.url || null,
        type: String(source.type || ""),
      };
    })
    .filter(Boolean);
}

function parseLocations(locations) {
  const cities = [];
  const countries = [];
  asArray(locations).forEach((location) => {
    const parts = String(location).split(",").map((part) => part.trim()).filter(Boolean);
    if (parts.length > 1) {
      cities.push(parts[0]);
      countries.push(parts.at(-1));
    }
  });
  return { cities: uniqueStrings(cities), countries: uniqueStrings(countries) };
}

function normalizePaper(raw, fixtureExport = false) {
  const id = String(raw.id || raw.paper_id || "").trim();
  const title = String(raw.title || "").trim();
  const authors = uniqueStrings(
    asArray(raw.authors).map((author) =>
      typeof author === "object" ? author.name || author.label || author.id : author
    )
  );
  const institutions = normalizeEntities(raw.institutions);
  const faculty = normalizeEntities(raw.faculty || raw.faculty_members, raw.faculty_ids);
  const groups = normalizeEntities(raw.groups || raw.research_groups, raw.group_ids);
  const locationText = uniqueStrings(raw.locations || []);
  const parsedLocations = parseLocations(locationText);
  const cities = uniqueStrings([...asArray(raw.cities), ...parsedLocations.cities]);
  const countries = uniqueStrings([...asArray(raw.countries), ...parsedLocations.countries]);
  const regions = uniqueStrings(raw.regions || raw.geographic_regions || []);
  const topics = uniqueStrings(raw.topics || []);
  const methods = uniqueStrings(raw.methods || []);
  const systemLayers = uniqueStrings(raw.system_layers || []);
  const contributionTypes = uniqueStrings(raw.contribution_types || []);
  const mechanisms = uniqueStrings(raw.mechanisms || []);
  const sectors = uniqueStrings(
    raw.sectors || raw.collaboration_types || raw.paper_sectors || raw.institution_types || []
  );
  const awards = normalizeAwards(raw.awards);
  const summarySource =
    raw.story && typeof raw.story === "object"
      ? raw.story
      : raw.summary && typeof raw.summary === "object"
        ? raw.summary
        : {};
  const takeaway = String(raw.takeaway || summarySource.takeaway || "").trim();
  const story = {
    background: flattenText(summarySource.background || raw.background),
    villain: flattenText(summarySource.villain || raw.villain),
    approach: flattenText(summarySource.approach || raw.approach),
    impact: flattenText(summarySource.impact || raw.impact),
    evaluation: flattenText(summarySource.evaluation || raw.evaluation),
    limitations: flattenText(summarySource.limitations || raw.limitations),
    phd_group_signal: flattenText(
      summarySource.phd_group_signal || raw.phd_group_signal
    ),
  };
  const completionStatus = String(
    raw.completion_status ||
      raw.collection_status ||
      raw.venue_year_completion_status ||
      "UNVERIFIED"
  ).toLocaleUpperCase();
  const knownIncompleteStatuses = new Set([
    "ACCEPTED_PAPERS_ONLY",
    "PARTIAL",
    "UPCOMING",
    "UNAVAILABLE",
  ]);
  const explicitIncomplete =
    typeof raw.is_incomplete_venue_year === "boolean"
      ? raw.is_incomplete_venue_year
      : null;
  const incompleteVenueYear =
    explicitIncomplete === null
      ? knownIncompleteStatuses.has(completionStatus)
      : explicitIncomplete;
  const confidence = String(raw.confidence || "UNRESOLVED").toLocaleUpperCase();
  const links = raw.links && typeof raw.links === "object" ? raw.links : {};
  const hasCode = Boolean(raw.has_code || links.code);
  const hasArtifact = Boolean(raw.has_artifact || links.artifact);
  const sourceList = normalizeSources(raw.sources);
  const publicationDate = raw.publication_date ? String(raw.publication_date) : null;

  const searchFields = [
    { key: "title", label: "Title", values: [title] },
    { key: "takeaway", label: "Takeaway", values: [takeaway] },
    { key: "background", label: "Background", values: [story.background] },
    { key: "villain", label: "Problem", values: [story.villain] },
    { key: "approach", label: "Approach", values: [story.approach] },
    { key: "impact", label: "Impact", values: [story.impact] },
    { key: "evaluation", label: "Evaluation", values: [story.evaluation] },
    { key: "limitations", label: "Limitations", values: [story.limitations] },
    { key: "phd_group_signal", label: "PhD-group signal", values: [story.phd_group_signal] },
    { key: "mechanisms", label: "Mechanism", values: mechanisms },
    { key: "topics", label: "Topic", values: topics.map(humanize) },
    { key: "methods", label: "Method", values: methods.map(humanize) },
    { key: "layers", label: "System layer", values: systemLayers.map(humanize) },
    {
      key: "contributions",
      label: "Contribution",
      values: contributionTypes.map(humanize),
    },
    { key: "authors", label: "Author", values: authors },
    { key: "faculty", label: "Faculty", values: faculty.flatMap((item) => [item.label, item.value]) },
    { key: "groups", label: "Research group", values: groups.flatMap((item) => [item.label, item.value]) },
    {
      key: "institutions",
      label: "Institution",
      values: institutions.flatMap((item) => [item.label, item.value]),
    },
    { key: "locations", label: "Location", values: [...locationText, ...cities, ...countries, ...regions] },
    {
      key: "awards",
      label: "Award",
      values: awards.flatMap((award) => [award.name, award.category]),
    },
  ].map((field) => ({ ...field, values: field.values.filter(Boolean) }));

  return {
    raw,
    id,
    title,
    venue: String(raw.venue || "").trim(),
    year: Number(raw.year),
    publicationDate,
    authors,
    takeaway,
    story,
    topics,
    methods,
    systemLayers,
    contributionTypes,
    mechanisms,
    institutions,
    faculty,
    groups,
    locations: locationText,
    cities,
    countries,
    regions,
    sectors,
    awards,
    relevanceClass: String(raw.relevance_class || "NEEDS_HUMAN_REVIEW"),
    relevanceScore:
      raw.relevance_score === null || raw.relevance_score === undefined
        ? null
        : Number(raw.relevance_score),
    confidence,
    completionStatus,
    incompleteVenueYear,
    coverageUnknown: completionStatus === "UNVERIFIED",
    hasCode,
    hasArtifact,
    links,
    sources: sourceList,
    lastVerifiedAt: raw.last_verified_at || null,
    isFixture: Boolean(fixtureExport || raw.is_fixture),
    searchFields,
  };
}

function validatePayload(payload) {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("The paper export is not a JSON object.");
  }
  if (!Array.isArray(payload.papers)) {
    throw new Error("The paper export does not contain a papers array.");
  }
  payload.papers.forEach((paper, index) => {
    if (!paper || typeof paper !== "object") {
      throw new Error(`Paper ${index + 1} is not an object.`);
    }
    if (!(paper.id || paper.paper_id) || !paper.title || !paper.venue || !Number.isInteger(paper.year)) {
      throw new Error(`Paper ${index + 1} is missing a required identity field.`);
    }
  });
  return payload;
}

function annotationFor(library, paperId) {
  const value = library[paperId] && typeof library[paperId] === "object"
    ? library[paperId]
    : {};
  return {
    starred: Boolean(value.starred),
    reading: ["unread", "skimmed", "read"].includes(value.reading)
      ? value.reading
      : "unread",
    notes: String(value.notes || ""),
    tags: uniqueStrings(value.tags || []),
    shortlists: uniqueStrings(value.shortlists || []),
  };
}

function searchFieldsWithAnnotation(paper, annotation) {
  return [
    ...paper.searchFields,
    { key: "private_note", label: "Private note", values: [annotation.notes].filter(Boolean) },
    { key: "custom_tags", label: "Your tag", values: annotation.tags },
    { key: "shortlists", label: "Shortlist", values: annotation.shortlists },
  ];
}

function evaluateTerms(fields, terms) {
  const included = terms.filter((term) => !term.excluded);
  const excluded = terms.filter((term) => term.excluded);
  const matchedFields = new Set();

  if (
    excluded.some((term) =>
      fields.some((field) => field.values.some((value) => termMatchesValue(term, value)))
    )
  ) {
    return { matches: false, matchedFields: [] };
  }

  for (const term of included) {
    const matching = fields.filter((field) =>
      field.values.some((value) => termMatchesValue(term, value))
    );
    if (!matching.length) return { matches: false, matchedFields: [] };
    matching.forEach((field) => matchedFields.add(field.label));
  }

  return { matches: true, matchedFields: [...matchedFields] };
}

function hasFilterValue(values, selected) {
  if (!selected) return true;
  return values.some((value) => String(value) === String(selected));
}

function matchesTimeWindow(paper, filters, now = new Date()) {
  if (filters.timeWindow === "all") return true;
  if (filters.timeWindow === "application") {
    return paper.year >= 2023 && paper.year <= 2026;
  }
  if (filters.timeWindow === "rolling36") {
    const start = new Date(now);
    start.setUTCMonth(start.getUTCMonth() - 36);
    if (paper.publicationDate) {
      const published = new Date(`${paper.publicationDate}T00:00:00Z`);
      return !Number.isNaN(published.valueOf()) && published >= start && published <= now;
    }
    return paper.year >= start.getUTCFullYear() && paper.year <= now.getUTCFullYear();
  }
  return true;
}

function matchesStructuredFilters(paper, filters, annotation, now = new Date()) {
  if (!matchesTimeWindow(paper, filters, now)) return false;
  if (filters.year && String(paper.year) !== String(filters.year)) return false;
  if (filters.venue && paper.venue !== filters.venue) return false;
  if (filters.relevance) {
    if (paper.relevanceClass !== filters.relevance) return false;
  } else if (!["CORE_SYSTEMS", "SYSTEMS_ADJACENT"].includes(paper.relevanceClass)) {
    return false;
  }
  if (filters.completeOnly && (paper.incompleteVenueYear || paper.coverageUnknown)) return false;
  if (filters.topic && !hasFilterValue(paper.topics, filters.topic)) return false;
  if (filters.method && !hasFilterValue(paper.methods, filters.method)) return false;
  if (filters.layer && !hasFilterValue(paper.systemLayers, filters.layer)) return false;
  if (
    filters.contribution &&
    !hasFilterValue(paper.contributionTypes, filters.contribution)
  ) return false;
  if (
    filters.institution &&
    !hasFilterValue(paper.institutions.map((item) => item.value), filters.institution)
  ) return false;
  if (
    filters.group &&
    !hasFilterValue(paper.groups.map((item) => item.value), filters.group)
  ) return false;
  if (
    filters.faculty &&
    !hasFilterValue(paper.faculty.map((item) => item.value), filters.faculty)
  ) return false;
  if (
    filters.award &&
    !hasFilterValue(
      paper.awards.flatMap((award) => [award.category, award.name]),
      filters.award
    )
  ) return false;
  if (filters.region && !hasFilterValue(paper.regions, filters.region)) return false;
  if (filters.country && !hasFilterValue(paper.countries, filters.country)) return false;
  if (filters.city && !hasFilterValue(paper.cities, filters.city)) return false;
  if (filters.sector && !hasFilterValue(paper.sectors, filters.sector)) return false;
  if (filters.starredOnly && !annotation.starred) return false;
  if (filters.reading && annotation.reading !== filters.reading) return false;
  if (filters.shortlist && !hasFilterValue(annotation.shortlists, filters.shortlist)) return false;

  if (filters.availability === "either" && !paper.hasCode && !paper.hasArtifact) return false;
  if (filters.availability === "code" && !paper.hasCode) return false;
  if (filters.availability === "artifact" && !paper.hasArtifact) return false;
  if (filters.availability === "both" && (!paper.hasCode || !paper.hasArtifact)) return false;
  return true;
}

function filterPapers(papers, filters, library = {}, now = new Date()) {
  const terms = parseQuery(filters.query);
  return papers.reduce((results, paper) => {
    const annotation = annotationFor(library, paper.id);
    if (!matchesStructuredFilters(paper, filters, annotation, now)) return results;
    const search = evaluateTerms(searchFieldsWithAnnotation(paper, annotation), terms);
    if (!search.matches) return results;
    results.push({ paper, annotation, matchedFields: search.matchedFields });
    return results;
  }, []);
}

function sortResults(results, sort) {
  const collator = new Intl.Collator(undefined, { sensitivity: "base", numeric: true });
  const sorted = [...results];
  sorted.sort((left, right) => {
    const a = left.paper;
    const b = right.paper;
    if (sort === "oldest") {
      return a.year - b.year || collator.compare(a.title, b.title);
    }
    if (sort === "title") return collator.compare(a.title, b.title);
    if (sort === "venue") {
      return (
        collator.compare(humanize(a.venue), humanize(b.venue)) ||
        b.year - a.year ||
        collator.compare(a.title, b.title)
      );
    }
    return b.year - a.year || collator.compare(a.title, b.title);
  });
  return sorted;
}

function parseUrlState(search) {
  const params = new URLSearchParams(String(search || "").replace(/^\?/, ""));
  const filters = { ...DEFAULT_FILTERS };
  Object.entries(URL_FIELDS).forEach(([key, parameter]) => {
    if (!params.has(parameter)) return;
    if (key === "completeOnly") {
      filters[key] = params.get(parameter) === "1";
    } else {
      filters[key] = params.get(parameter) || DEFAULT_FILTERS[key];
    }
  });
  if (!["application", "rolling36", "all"].includes(filters.timeWindow)) {
    filters.timeWindow = DEFAULT_FILTERS.timeWindow;
  }
  if (!["newest", "oldest", "title", "venue"].includes(filters.sort)) {
    filters.sort = DEFAULT_FILTERS.sort;
  }
  if (!["cards", "table"].includes(filters.view)) {
    filters.view = DEFAULT_FILTERS.view;
  }
  return filters;
}

function serializeFilters(filters) {
  const params = new URLSearchParams();
  Object.entries(URL_FIELDS).forEach(([key, parameter]) => {
    const value = filters[key];
    if (key === "completeOnly") {
      if (value) params.set(parameter, "1");
      return;
    }
    if (value !== "" && value !== DEFAULT_FILTERS[key]) {
      params.set(parameter, String(value));
    }
  });
  return params.toString();
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function exportRecords(results) {
  return results.map(({ paper, annotation }) => ({
    id: paper.id,
    title: paper.title,
    venue: paper.venue,
    year: paper.year,
    authors: paper.authors,
    takeaway: paper.takeaway,
    relevance_class: paper.relevanceClass,
    topics: paper.topics,
    system_layers: paper.systemLayers,
    contribution_types: paper.contributionTypes,
    methods: paper.methods,
    institutions: paper.institutions.map((item) => item.label),
    faculty: paper.faculty.map((item) => item.label),
    groups: paper.groups.map((item) => item.label),
    cities: paper.cities,
    countries: paper.countries,
    regions: paper.regions,
    awards: paper.awards,
    has_code: paper.hasCode,
    has_artifact: paper.hasArtifact,
    links: paper.links,
    confidence: paper.confidence,
    completion_status: paper.completionStatus,
    last_verified_at: paper.lastVerifiedAt,
    is_fixture: paper.isFixture,
    local_annotation: annotation,
  }));
}

function recordsToCsv(records) {
  const columns = [
    "id",
    "title",
    "venue",
    "year",
    "authors",
    "takeaway",
    "relevance_class",
    "topics",
    "methods",
    "institutions",
    "faculty",
    "groups",
    "countries",
    "has_code",
    "has_artifact",
    "reading_state",
    "starred",
    "custom_tags",
    "shortlists",
    "private_notes",
  ];
  const rows = records.map((record) => [
    record.id,
    record.title,
    record.venue,
    record.year,
    record.authors.join("; "),
    record.takeaway,
    record.relevance_class,
    record.topics.join("; "),
    record.methods.join("; "),
    record.institutions.join("; "),
    record.faculty.join("; "),
    record.groups.join("; "),
    record.countries.join("; "),
    record.has_code,
    record.has_artifact,
    record.local_annotation.reading,
    record.local_annotation.starred,
    record.local_annotation.tags.join("; "),
    record.local_annotation.shortlists.join("; "),
    record.local_annotation.notes,
  ]);
  return [columns, ...rows].map((row) => row.map(csvCell).join(",")).join("\n");
}

function bibtexKey(record) {
  const firstAuthor = record.authors[0] || "paper";
  const surname = firstAuthor.split(/\s+/).at(-1).replace(/[^\p{L}\p{N}]/gu, "");
  const suffix = record.id.replace(/[^\p{L}\p{N}]/gu, "").slice(-6);
  return `${surname || "paper"}${record.year}${suffix}`.toLocaleLowerCase();
}

function bibtexValue(value) {
  return String(value ?? "").replaceAll("\\", "\\\\").replaceAll("{", "\\{").replaceAll("}", "\\}");
}

function recordsToBibtex(records) {
  return records
    .map((record) => {
      const fields = [
        `  title = {${bibtexValue(record.title)}},`,
        `  author = {${bibtexValue(record.authors.join(" and "))}},`,
        `  booktitle = {${bibtexValue(humanize(record.venue))}},`,
        `  year = {${record.year}}`,
      ];
      const officialPage = record.links?.official_page;
      if (officialPage) {
        fields[fields.length - 1] += ",";
        fields.push(`  url = {${bibtexValue(officialPage)}}`);
      }
      return `@inproceedings{${bibtexKey(record)},\n${fields.join("\n")}\n}`;
    })
    .join("\n\n");
}

function createElement(tagName, className = "", text = null) {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text !== null && text !== undefined) element.textContent = String(text);
  return element;
}

function appendHighlightedText(parent, value, terms) {
  const text = String(value ?? "");
  const ranges = findHighlightRanges(text, terms);
  if (!ranges.length) {
    parent.append(document.createTextNode(text));
    return;
  }
  let cursor = 0;
  ranges.forEach(([start, end]) => {
    if (start > cursor) parent.append(document.createTextNode(text.slice(cursor, start)));
    const mark = document.createElement("mark");
    mark.textContent = text.slice(start, end);
    parent.append(mark);
    cursor = end;
  });
  if (cursor < text.length) parent.append(document.createTextNode(text.slice(cursor)));
}

function badge(text, className = "") {
  return createElement("span", `badge ${className}`.trim(), text);
}

function tagItem(text, className = "") {
  const item = createElement("li", `tag ${className}`.trim());
  item.textContent = humanize(text);
  return item;
}

function entityLabels(entities) {
  return entities.map((item) => item.label);
}

function paperBadges(paper) {
  const row = createElement("div", "badge-row");
  if (paper.isFixture) row.append(badge("Synthetic fixture", "badge-fixture"));
  if (paper.incompleteVenueYear) {
    row.append(badge(humanize(paper.completionStatus), "badge-warning"));
  } else if (paper.coverageUnknown) {
    row.append(badge("Coverage unknown", "badge-warning"));
  }
  if (["LOW", "UNRESOLVED"].includes(paper.confidence)) {
    row.append(badge(humanize(paper.confidence), "badge-low"));
  }
  paper.awards.forEach((award) => row.append(badge(award.name, "badge-award")));
  if (paper.hasCode) row.append(badge("Code", "badge-code"));
  if (paper.hasArtifact) row.append(badge("Artifact", "badge-code"));
  return row;
}

function paperTitle(paper, terms, className = "") {
  const hasOfficialPage = Boolean(paper.links?.official_page);
  const title = createElement(hasOfficialPage ? "a" : "span", className);
  if (hasOfficialPage) {
    title.href = paper.links.official_page;
    title.target = "_blank";
    title.rel = "noreferrer";
  }
  appendHighlightedText(title, paper.title, terms);
  return title;
}

function contextBlock(title, values, terms) {
  const block = createElement("div", "context-block");
  block.append(createElement("h4", "", title));
  const text = createElement("p");
  appendHighlightedText(text, values.filter(Boolean).join(" · ") || "Unresolved", terms);
  block.append(text);
  return block;
}

function readingControl(paper, annotation) {
  const label = createElement("label", "reading-control");
  label.append(createElement("span", "", "Reading"));
  const select = createElement("select");
  select.dataset.action = "reading";
  select.dataset.paperId = paper.id;
  select.setAttribute("aria-label", `Reading state for ${paper.title}`);
  [
    ["unread", "Unread"],
    ["skimmed", "Skimmed"],
    ["read", "Read"],
  ].forEach(([value, text]) => {
    const option = createElement("option", "", text);
    option.value = value;
    select.append(option);
  });
  select.value = annotation.reading;
  label.append(select);
  return label;
}

function paperActions(paper, annotation) {
  const actions = createElement("div", "paper-actions");
  const star = createElement(
    "button",
    "star-button",
    annotation.starred ? "★ Starred" : "☆ Star"
  );
  star.type = "button";
  star.dataset.action = "star";
  star.dataset.paperId = paper.id;
  star.setAttribute("aria-pressed", annotation.starred ? "true" : "false");
  star.setAttribute("aria-label", `${annotation.starred ? "Unstar" : "Star"} ${paper.title}`);

  const annotate = createElement(
    "button",
    "paper-action",
    annotation.notes || annotation.tags.length || annotation.shortlists.length
      ? "Edit local note"
      : "Add local note"
  );
  annotate.type = "button";
  annotate.dataset.action = "annotate";
  annotate.dataset.paperId = paper.id;
  actions.append(star, readingControl(paper, annotation), annotate);
  return actions;
}

function storyDetails(paper, terms) {
  const details = createElement("details", "paper-details");
  details.append(createElement("summary", "", "Story, evaluation & evidence"));
  const grid = createElement("div", "story-grid");
  const fields = [
    ["Background", paper.story.background],
    ["The problem", paper.story.villain],
    ["Approach", paper.story.approach],
    ["Impact", paper.story.impact],
    ["Evaluation", paper.story.evaluation],
    ["Limitations", paper.story.limitations],
    ["PhD-group signal", paper.story.phd_group_signal],
  ].filter(([, value]) => value);

  if (fields.length) {
    fields.forEach(([title, value]) => {
      const block = createElement("section", "story-block");
      block.append(createElement("h4", "", title));
      const paragraph = createElement("p");
      appendHighlightedText(paragraph, value, terms);
      block.append(paragraph);
      grid.append(block);
    });
  } else {
    const block = createElement("section", "story-block");
    block.append(
      createElement("h4", "", "Summary status"),
      createElement("p", "", "The compact export does not yet include detailed story fields.")
    );
    grid.append(block);
  }
  details.append(grid);

  const sources = createElement("p", "source-row");
  if (paper.sources.length) {
    sources.append(document.createTextNode("Sources: "));
    paper.sources.forEach((source, index) => {
      if (index) sources.append(document.createTextNode(" · "));
      if (source.url && !paper.isFixture) {
        const link = createElement("a", "", source.label);
        link.href = source.url;
        link.target = "_blank";
        link.rel = "noreferrer";
        sources.append(link);
      } else {
        sources.append(document.createTextNode(source.label));
      }
    });
  } else {
    sources.textContent = paper.isFixture
      ? "Synthetic fixture: no external factual source."
      : "Source links are not included in this compact index.";
  }
  details.append(sources);
  return details;
}

function formatVerification(paper) {
  const date = paper.lastVerifiedAt
    ? new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        timeZone: "UTC",
      }).format(new Date(paper.lastVerifiedAt))
    : "not recorded";
  return `${humanize(paper.confidence)} · checked ${date}`;
}

function paperCard(result, terms) {
  const { paper, annotation, matchedFields } = result;
  const article = createElement("article", "paper-card");
  article.dataset.paperId = paper.id;
  const grid = createElement("div", "paper-card-grid");
  const main = createElement("div");
  const kicker = createElement("div", "paper-kicker");
  kicker.append(
    createElement(
      "span",
      "paper-identity",
      `${humanize(paper.venue)} · ${paper.year} · ${humanize(paper.relevanceClass)}`
    ),
    paperBadges(paper)
  );
  const heading = createElement("h3");
  heading.append(paperTitle(paper, terms));
  const takeaway = createElement("p", "takeaway");
  appendHighlightedText(
    takeaway,
    paper.takeaway || "Beginner summary not yet available.",
    terms
  );
  main.append(kicker, heading, takeaway);

  if (terms.some((term) => !term.excluded) && matchedFields.length) {
    main.append(
      createElement("p", "match-line", `Matches in ${matchedFields.join(", ")}`)
    );
  }

  const tags = createElement("ul", "tag-list");
  paper.topics.slice(0, 5).forEach((value) => tags.append(tagItem(value)));
  paper.methods.slice(0, 3).forEach((value) => tags.append(tagItem(value, "tag-method")));
  annotation.tags.forEach((value) => tags.append(tagItem(value, "tag-personal")));
  main.append(tags);

  const context = createElement("aside", "paper-context", "");
  context.setAttribute("aria-label", "People and place");
  context.append(
    contextBlock("Authors", paper.authors, terms),
    contextBlock(
      "Faculty & groups",
      [...entityLabels(paper.faculty), ...entityLabels(paper.groups)],
      terms
    ),
    contextBlock(
      "Institution & place",
      [
        ...entityLabels(paper.institutions),
        ...paper.cities,
        ...paper.countries,
        ...paper.regions,
      ],
      terms
    )
  );
  grid.append(main, context);

  const bottom = createElement("div", "paper-bottom");
  bottom.append(
    paperActions(paper, annotation),
    createElement("p", "verification", formatVerification(paper))
  );
  article.append(grid, storyDetails(paper, terms), bottom);
  return article;
}

function tableCell(label) {
  const cell = createElement("td");
  cell.dataset.label = label;
  return cell;
}

function paperTable(results, terms) {
  const wrapper = createElement("div", "paper-table-wrap");
  const table = createElement("table", "paper-table");
  table.append(createElement("caption", "", "Filtered systems research papers"));
  const head = createElement("thead");
  const headRow = createElement("tr");
  ["Paper", "Research signal", "People & place", "Evidence", "Your library"].forEach(
    (label) => headRow.append(createElement("th", "", label))
  );
  head.append(headRow);
  const body = createElement("tbody");

  results.forEach(({ paper, annotation, matchedFields }) => {
    const row = createElement("tr");
    row.dataset.paperId = paper.id;

    const identity = tableCell("Paper");
    identity.append(paperTitle(paper, terms, "table-title"));
    identity.append(
      createElement(
        "span",
        "table-meta",
        `${humanize(paper.venue)} · ${paper.year} · ${humanize(paper.relevanceClass)}`
      ),
      paperBadges(paper)
    );

    const research = tableCell("Research signal");
    const takeaway = createElement("p", "table-takeaway");
    appendHighlightedText(takeaway, paper.takeaway || "Summary not available.", terms);
    research.append(takeaway);
    const topicText = [...paper.topics.slice(0, 3), ...paper.methods.slice(0, 2)]
      .map(humanize)
      .join(" · ");
    research.append(createElement("span", "table-secondary", topicText));
    if (matchedFields.length && terms.some((term) => !term.excluded)) {
      research.append(
        createElement("span", "match-line", `Matches: ${matchedFields.join(", ")}`)
      );
    }

    const people = tableCell("People & place");
    const peopleText = createElement("span");
    appendHighlightedText(
      peopleText,
      [
        ...paper.authors,
        ...entityLabels(paper.faculty),
        ...entityLabels(paper.groups),
      ].join(" · ") || "Unresolved",
      terms
    );
    const placeText = createElement("span", "table-secondary");
    appendHighlightedText(
      placeText,
      [...entityLabels(paper.institutions), ...paper.cities, ...paper.countries].join(" · "),
      terms
    );
    people.append(peopleText, placeText);

    const evidence = tableCell("Evidence");
    evidence.append(
      createElement("span", "", humanize(paper.confidence)),
      createElement("span", "table-secondary", humanize(paper.completionStatus)),
      createElement(
        "span",
        "table-secondary",
        `${paper.hasCode ? "Code" : "No code"} · ${paper.hasArtifact ? "Artifact" : "No artifact"}`
      )
    );

    const library = tableCell("Your library");
    const controls = createElement("div", "table-library");
    controls.append(paperActions(paper, annotation));
    library.append(controls);
    row.append(identity, research, people, evidence, library);
    body.append(row);
  });

  table.append(head, body);
  wrapper.append(table);
  return wrapper;
}

function uniqueOptions(items) {
  const map = new Map();
  items.forEach((item) => {
    const option =
      typeof item === "object" && item
        ? { value: String(item.value), label: String(item.label || item.value) }
        : { value: String(item), label: humanize(item) };
    if (option.value && !map.has(option.value)) map.set(option.value, option);
  });
  return [...map.values()].sort((left, right) =>
    left.label.localeCompare(right.label, undefined, { numeric: true, sensitivity: "base" })
  );
}

function replaceOptions(select, placeholder, options) {
  const current = select.value;
  const placeholderOption = createElement("option", "", placeholder);
  placeholderOption.value = "";
  const nodes = [placeholderOption];
  uniqueOptions(options).forEach(({ value, label }) => {
    const option = createElement("option", "", label);
    option.value = value;
    nodes.push(option);
  });
  select.replaceChildren(...nodes);
  if (current) {
    ensureOption(select, current);
    select.value = current;
  }
}

function ensureOption(select, value) {
  if (!value || [...select.options].some((option) => option.value === String(value))) return;
  const option = createElement("option", "", `${humanize(value)} (not in current data)`);
  option.value = String(value);
  select.append(option);
}

function populatePaperOptions() {
  const { elements } = app;
  const papers = app.papers;
  replaceOptions(
    elements.venue,
    "All venues",
    papers.map((paper) => ({ value: paper.venue, label: humanize(paper.venue) }))
  );
  replaceOptions(
    elements.year,
    "All years",
    [...new Set(papers.map((paper) => paper.year))]
      .sort((left, right) => right - left)
      .map((year) => ({ value: year, label: year }))
  );
  replaceOptions(
    elements.relevance,
    "Core + adjacent",
    papers.map((paper) => ({
      value: paper.relevanceClass,
      label: humanize(paper.relevanceClass),
    }))
  );
  replaceOptions(elements.topic, "All topics", papers.flatMap((paper) => paper.topics));
  replaceOptions(elements.method, "All methods", papers.flatMap((paper) => paper.methods));
  replaceOptions(elements.layer, "All layers", papers.flatMap((paper) => paper.systemLayers));
  replaceOptions(
    elements.contribution,
    "All contributions",
    papers.flatMap((paper) => paper.contributionTypes)
  );
  replaceOptions(
    elements.institution,
    "All institutions",
    papers.flatMap((paper) => paper.institutions)
  );
  replaceOptions(elements.group, "All groups", papers.flatMap((paper) => paper.groups));
  replaceOptions(elements.faculty, "All faculty", papers.flatMap((paper) => paper.faculty));
  replaceOptions(
    elements.award,
    "Any award status",
    papers.flatMap((paper) =>
      paper.awards.map((award) => ({ value: award.category, label: humanize(award.category) }))
    )
  );
  replaceOptions(elements.region, "All regions", papers.flatMap((paper) => paper.regions));
  replaceOptions(elements.country, "All countries", papers.flatMap((paper) => paper.countries));
  replaceOptions(elements.city, "All cities", papers.flatMap((paper) => paper.cities));
  replaceOptions(
    elements.sector,
    "Any collaboration type",
    papers.flatMap((paper) => paper.sectors)
  );
  populateShortlistOptions();
}

function populateShortlistOptions() {
  if (!app.elements.shortlist) return;
  const names = Object.keys(app.library).flatMap(
    (paperId) => annotationFor(app.library, paperId).shortlists
  );
  replaceOptions(app.elements.shortlist, "Any shortlist", names);
  ensureOption(app.elements.shortlist, app.filters.shortlist);
  app.elements.shortlist.value = app.filters.shortlist;
}

function selectLabel(key, value) {
  const select = app.elements[key];
  if (select && select.tagName === "SELECT") {
    const option = [...select.options].find((item) => item.value === String(value));
    if (option) return option.textContent;
  }
  if (typeof value === "boolean") return value ? "On" : "Off";
  return humanize(value);
}

function activeFilterEntries() {
  return Object.keys(FILTER_LABELS).reduce((entries, key) => {
    const value = app.filters[key];
    const defaultValue = DEFAULT_FILTERS[key];
    if (value === defaultValue || value === "" || value === false) return entries;
    entries.push({
      key,
      label: FILTER_LABELS[key],
      value: key === "query" ? value : selectLabel(key, value),
    });
    return entries;
  }, []);
}

function renderActiveFilters() {
  const entries = activeFilterEntries();
  app.elements.activeFilters.hidden = entries.length === 0;
  const fragment = document.createDocumentFragment();
  entries.forEach(({ key, label, value }) => {
    const button = createElement("button", "filter-chip");
    button.type = "button";
    button.dataset.clearFilter = key;
    button.setAttribute("aria-label", `Remove ${label} filter: ${value}`);
    button.append(
      createElement("span", "", `${label}: ${value}`),
      createElement("span", "", "×")
    );
    fragment.append(button);
  });
  app.elements.activeFilterList.replaceChildren(fragment);

  const advancedCount = ADVANCED_FILTER_KEYS.filter((key) => {
    const value = app.filters[key];
    return value !== DEFAULT_FILTERS[key] && value !== "" && value !== false;
  }).length;
  app.elements.advancedCount.textContent = advancedCount ? String(advancedCount) : "";
  if (advancedCount) app.elements.advancedFilters.open = true;

  app.elements.presets.querySelectorAll("[data-preset]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      app.filters.topic === button.dataset.preset ? "true" : "false"
    );
  });
}

function setSelectValue(select, value) {
  ensureOption(select, value);
  select.value = String(value ?? "");
}

function syncControls() {
  const { filters, elements } = app;
  elements.search.value = filters.query;
  setSelectValue(elements.timeWindow, filters.timeWindow);
  [
    "venue",
    "year",
    "relevance",
    "availability",
    "topic",
    "method",
    "layer",
    "contribution",
    "institution",
    "group",
    "faculty",
    "award",
    "region",
    "country",
    "city",
    "sector",
    "reading",
    "shortlist",
    "sort",
  ].forEach((key) => setSelectValue(elements[key], filters[key]));
  elements.completeOnly.checked = filters.completeOnly;
  elements.starredOnly.checked = filters.starredOnly;
  elements.viewButtons.forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.view === filters.view ? "true" : "false");
  });
  renderActiveFilters();
}

function updateUrl() {
  const query = serializeFilters(app.filters);
  const next = `${location.pathname}${query ? `?${query}` : ""}${location.hash || ""}`;
  history.replaceState(null, "", next);
}

function render({ writeUrl = true } = {}) {
  if (app.loading) return;
  const terms = parseQuery(app.filters.query);
  app.results = sortResults(
    filterPapers(app.papers, app.filters, app.library),
    app.filters.sort
  );
  const visible = app.results.slice(0, app.visibleLimit);
  const total = app.papers.length;
  const shown = Math.min(visible.length, app.results.length);

  app.elements.paperList.className =
    app.filters.view === "table" ? "paper-list table-view" : "paper-list";
  if (visible.length) {
    if (app.filters.view === "table") {
      app.elements.paperList.replaceChildren(paperTable(visible, terms));
    } else {
      app.elements.paperList.replaceChildren(
        ...visible.map((result) => paperCard(result, terms))
      );
    }
  } else {
    app.elements.paperList.replaceChildren();
  }

  const fixtureLabel = app.hasFixtureRecords ? " synthetic" : "";
  app.elements.resultCount.textContent =
    app.results.length > app.visibleLimit
      ? `${app.results.length} of ${total}${fixtureLabel} records match · showing ${shown}`
      : `${app.results.length} of ${total}${fixtureLabel} records match`;
  app.elements.emptyTitle.textContent =
    total === 0 ? "No papers are available yet" : "No papers match this route";
  app.elements.emptyMessage.textContent =
    total === 0
      ? "The index loaded successfully, but this corpus export contains no paper records."
      : "Try removing an exclusion, including incomplete venue-years, or widening the time window.";
  app.elements.empty.hidden = app.results.length !== 0;
  app.elements.error.hidden = true;
  app.elements.loadMore.hidden = shown >= app.results.length;
  app.elements.loadMore.textContent = `Show ${Math.min(
    PAGE_SIZE,
    app.results.length - shown
  )} more papers`;
  app.elements.results.setAttribute("aria-busy", "false");
  app.elements.exportButtons.forEach((button) => {
    button.disabled = app.results.length === 0;
  });
  renderActiveFilters();
  if (writeUrl) updateUrl();
}

function setLoading(loading) {
  app.loading = loading;
  app.elements.loading.hidden = !loading;
  app.elements.results.setAttribute("aria-busy", loading ? "true" : "false");
  if (loading) {
    app.elements.paperList.replaceChildren();
    app.elements.empty.hidden = true;
    app.elements.error.hidden = true;
    app.elements.loadMore.hidden = true;
    app.elements.resultCount.textContent = "Loading…";
  }
}

function setNotice(kind, text) {
  app.elements.notice.className = `data-notice ${kind ? `is-${kind}` : ""}`.trim();
  app.elements.noticeText.textContent = text;
  if (kind === "error") {
    app.elements.notice.setAttribute("role", "alert");
  } else {
    app.elements.notice.removeAttribute("role");
  }
}

async function fetchPayload(path) {
  const response = await fetch(path, { cache: "no-cache" });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  const payload = await response.json();
  return validatePayload(payload);
}

async function loadData() {
  setLoading(true);
  setNotice("loading", "Loading the generated paper index…");
  let payload;
  let primaryError;
  try {
    payload = await fetchPayload("data/papers.json");
  } catch (error) {
    primaryError = error;
    try {
      payload = await fetchPayload("data/fixture-papers.json");
    } catch (fixtureError) {
      const message = `${fixtureError.message} (generated index: ${primaryError.message})`;
      setLoading(false);
      setNotice("error", "Neither the generated index nor the local fixture could be loaded.");
      app.elements.errorMessage.textContent = message;
      app.elements.error.hidden = false;
      app.elements.resultCount.textContent = "Data unavailable";
      return;
    }
  }

  try {
    app.fixtureExport = Boolean(payload.is_fixture_export);
    app.papers = payload.papers.map((paper) =>
      normalizePaper(paper, app.fixtureExport)
    );
    app.hasFixtureRecords = app.papers.some((paper) => paper.isFixture);
    populatePaperOptions();
    app.filters = {
      ...DEFAULT_FILTERS,
      ...parseUrlState(location.search),
    };
    syncControls();
    setLoading(false);

    if (app.hasFixtureRecords) {
      setNotice(
        "fixture",
        "Synthetic pilot mode — every result is invented interface-test data, not a real paper, person, institution, award, or coverage claim."
      );
    } else {
      const incomplete = app.papers.filter((paper) => paper.incompleteVenueYear).length;
      const lowConfidence = app.papers.filter((paper) =>
        ["LOW", "UNRESOLVED"].includes(paper.confidence)
      ).length;
      setNotice(
        "",
        `${app.papers.length} papers loaded. ${incomplete} have incomplete venue-year coverage; ${lowConfidence} have low or unresolved confidence.`
      );
    }
    render();
  } catch (error) {
    setLoading(false);
    setNotice("error", "The paper index loaded but could not be interpreted.");
    app.elements.errorMessage.textContent = error.message;
    app.elements.error.hidden = false;
    app.elements.resultCount.textContent = "Data unavailable";
  }
}

function readJsonStorage(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function writeJsonStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    showToast("This browser could not save the local change.");
    return false;
  }
}

function loadLibrary() {
  const value = readJsonStorage(LIBRARY_KEY, {});
  const library = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const legacy = readJsonStorage(LEGACY_FAVORITES_KEY, []);
  let migrated = false;
  if (Array.isArray(legacy)) {
    legacy.forEach((paperId) => {
      const annotation = annotationFor(library, paperId);
      if (!annotation.starred) {
        library[paperId] = { ...annotation, starred: true };
        migrated = true;
      }
    });
  }
  if (migrated) writeJsonStorage(LIBRARY_KEY, library);
  return library;
}

function saveLibrary() {
  writeJsonStorage(LIBRARY_KEY, app.library);
}

function updateAnnotation(paperId, changes) {
  app.library[paperId] = {
    ...annotationFor(app.library, paperId),
    ...changes,
  };
  saveLibrary();
  populateShortlistOptions();
}

function loadSavedSearches() {
  const value = readJsonStorage(SAVED_SEARCHES_KEY, []);
  return Array.isArray(value)
    ? value.filter((item) => item && item.id && item.name && item.filters)
    : [];
}

function populateSavedSearches(selectedId = "") {
  const placeholder = createElement("option", "", "Saved searches");
  placeholder.value = "";
  const options = app.savedSearches
    .slice()
    .sort((left, right) => left.name.localeCompare(right.name))
    .map((saved) => {
      const option = createElement("option", "", saved.name);
      option.value = saved.id;
      return option;
    });
  app.elements.savedSearches.replaceChildren(placeholder, ...options);
  app.elements.savedSearches.value = selectedId;
  app.elements.deleteSearch.disabled = !selectedId;
}

function showToast(message) {
  if (!app.elements.toast) return;
  clearTimeout(app.toastTimer);
  app.elements.toast.textContent = message;
  app.elements.toast.hidden = false;
  app.toastTimer = setTimeout(() => {
    app.elements.toast.hidden = true;
  }, 3600);
}

function openDialog(dialog) {
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function closeDialog(dialog) {
  if (typeof dialog.close === "function") {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function splitCommaList(value) {
  return uniqueStrings(String(value || "").split(","));
}

function openAnnotation(paperId) {
  const paper = app.papers.find((item) => item.id === paperId);
  if (!paper) return;
  const annotation = annotationFor(app.library, paperId);
  app.elements.annotationTitle.textContent = `Your notes · ${paper.title}`;
  app.elements.annotationPaperId.value = paperId;
  app.elements.annotationStarred.checked = annotation.starred;
  app.elements.annotationReading.value = annotation.reading;
  app.elements.annotationNotes.value = annotation.notes;
  app.elements.annotationTags.value = annotation.tags.join(", ");
  app.elements.annotationShortlists.value = annotation.shortlists.join(", ");
  openDialog(app.elements.annotationDialog);
  app.elements.annotationNotes.focus();
}

function resetFilters({ preserveDisplay = true } = {}) {
  const view = app.filters.view;
  const sort = app.filters.sort;
  app.filters = { ...DEFAULT_FILTERS };
  if (preserveDisplay) {
    app.filters.view = view;
    app.filters.sort = sort;
  }
  app.visibleLimit = PAGE_SIZE;
  syncControls();
  render();
}

function clearOneFilter(key) {
  if (!Object.hasOwn(DEFAULT_FILTERS, key)) return;
  app.filters[key] = DEFAULT_FILTERS[key];
  app.visibleLimit = PAGE_SIZE;
  syncControls();
  render();
}

function handleResultClick(event) {
  const action = event.target.closest("[data-action]");
  if (!action) return;
  const paperId = action.dataset.paperId;
  if (action.dataset.action === "star") {
    const annotation = annotationFor(app.library, paperId);
    updateAnnotation(paperId, { starred: !annotation.starred });
    render();
    showToast(annotation.starred ? "Removed from starred papers." : "Saved to starred papers.");
  } else if (action.dataset.action === "annotate") {
    openAnnotation(paperId);
  }
}

function handleResultChange(event) {
  const control = event.target.closest('[data-action="reading"]');
  if (!control) return;
  updateAnnotation(control.dataset.paperId, { reading: control.value });
  if (app.filters.reading) render();
  showToast(`Marked as ${control.value}.`);
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function exportVisible(format) {
  if (!app.results.length) return;
  const records = exportRecords(app.results);
  const stamp = new Date().toISOString().slice(0, 10);
  const prefix = app.hasFixtureRecords ? "synthetic-fixture-papers" : "systems-papers";
  if (format === "csv") {
    downloadText(`${prefix}-${stamp}.csv`, `${recordsToCsv(records)}\n`, "text/csv;charset=utf-8");
  } else if (format === "bibtex") {
    downloadText(`${prefix}-${stamp}.bib`, `${recordsToBibtex(records)}\n`, "application/x-bibtex");
  } else {
    const payload = {
      schema_version: "1.0.0",
      export_notice: app.hasFixtureRecords
        ? "Synthetic interface-test data; no record is real."
        : "User-initiated browser export.",
      exported_at: new Date().toISOString(),
      papers: records,
    };
    downloadText(
      `${prefix}-${stamp}.json`,
      `${JSON.stringify(payload, null, 2)}\n`,
      "application/json"
    );
  }
  showToast(`Exported ${records.length} visible records as ${format.toLocaleUpperCase()}.`);
}

function initializeTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem(THEME_KEY);
  } catch {
    stored = null;
  }
  const prefersDark =
    typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme =
    stored === "light" || stored === "dark" ? stored : prefersDark ? "dark" : "light";
  updateThemeControl();
}

function updateThemeControl() {
  const current = document.documentElement.dataset.theme;
  const next = current === "dark" ? "light" : "dark";
  app.elements.theme.setAttribute("aria-label", `Use ${next} theme`);
  app.elements.theme.title = `Use ${next} theme`;
  app.elements.theme.querySelector(".theme-icon").textContent = current === "dark" ? "☀" : "◐";
}

function changeFilter(key, value) {
  app.filters[key] = value;
  app.visibleLimit = PAGE_SIZE;
  render();
}

function wireControls() {
  const { elements } = app;
  const selectBindings = [
    ["timeWindow", "timeWindow"],
    ["venue", "venue"],
    ["year", "year"],
    ["relevance", "relevance"],
    ["availability", "availability"],
    ["topic", "topic"],
    ["method", "method"],
    ["layer", "layer"],
    ["contribution", "contribution"],
    ["institution", "institution"],
    ["group", "group"],
    ["faculty", "faculty"],
    ["award", "award"],
    ["region", "region"],
    ["country", "country"],
    ["city", "city"],
    ["sector", "sector"],
    ["reading", "reading"],
    ["shortlist", "shortlist"],
    ["sort", "sort"],
  ];
  selectBindings.forEach(([elementKey, filterKey]) => {
    elements[elementKey].addEventListener("change", () => {
      changeFilter(filterKey, elements[elementKey].value);
    });
  });

  elements.search.addEventListener("input", () => {
    app.filters.query = elements.search.value.trim();
    app.visibleLimit = PAGE_SIZE;
    clearTimeout(app.searchTimer);
    app.searchTimer = setTimeout(render, 90);
  });
  elements.completeOnly.addEventListener("change", () => {
    changeFilter("completeOnly", elements.completeOnly.checked);
  });
  elements.starredOnly.addEventListener("change", () => {
    changeFilter("starredOnly", elements.starredOnly.checked);
  });
  elements.clear.addEventListener("click", () => {
    resetFilters();
    elements.search.focus();
  });
  elements.emptyClear.addEventListener("click", () => {
    resetFilters();
    elements.search.focus();
  });
  elements.activeFilterList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-clear-filter]");
    if (button) clearOneFilter(button.dataset.clearFilter);
  });
  elements.presets.addEventListener("click", (event) => {
    const button = event.target.closest("[data-preset]");
    if (!button) return;
    const next = app.filters.topic === button.dataset.preset ? "" : button.dataset.preset;
    app.filters.topic = next;
    app.visibleLimit = PAGE_SIZE;
    setSelectValue(elements.topic, next);
    render();
  });
  elements.viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      app.filters.view = button.dataset.view;
      syncControls();
      render();
    });
  });
  elements.paperList.addEventListener("click", handleResultClick);
  elements.paperList.addEventListener("change", handleResultChange);
  elements.loadMore.addEventListener("click", () => {
    app.visibleLimit += PAGE_SIZE;
    render();
  });
  elements.retry.addEventListener("click", loadData);
  elements.exportButtons.forEach((button) => {
    button.addEventListener("click", () => {
      exportVisible(button.dataset.export);
      button.closest("details").open = false;
    });
  });

  elements.theme.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      showToast("Theme changed for this page but could not be saved.");
    }
    updateThemeControl();
  });

  elements.annotationForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const paperId = elements.annotationPaperId.value;
    updateAnnotation(paperId, {
      starred: elements.annotationStarred.checked,
      reading: elements.annotationReading.value,
      notes: elements.annotationNotes.value.trim(),
      tags: splitCommaList(elements.annotationTags.value),
      shortlists: splitCommaList(elements.annotationShortlists.value),
    });
    closeDialog(elements.annotationDialog);
    syncControls();
    render();
    showToast("Private paper notes saved in this browser.");
  });
  [elements.annotationClose, elements.annotationCancel].forEach((button) => {
    button.addEventListener("click", () => closeDialog(elements.annotationDialog));
  });

  elements.saveSearch.addEventListener("click", () => {
    elements.savedSearchName.value = app.filters.query
      ? `Search: ${app.filters.query}`.slice(0, 80)
      : "My systems search";
    openDialog(elements.savedSearchDialog);
    elements.savedSearchName.select();
  });
  [elements.savedSearchClose, elements.savedSearchCancel].forEach((button) => {
    button.addEventListener("click", () => closeDialog(elements.savedSearchDialog));
  });
  elements.savedSearchForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const id =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `search-${Date.now()}`;
    const saved = {
      id,
      name: elements.savedSearchName.value.trim(),
      filters: { ...app.filters },
      saved_at: new Date().toISOString(),
    };
    app.savedSearches.push(saved);
    writeJsonStorage(SAVED_SEARCHES_KEY, app.savedSearches);
    populateSavedSearches(id);
    closeDialog(elements.savedSearchDialog);
    showToast(`Saved “${saved.name}” in this browser.`);
  });
  elements.savedSearches.addEventListener("change", () => {
    const saved = app.savedSearches.find(
      (item) => item.id === elements.savedSearches.value
    );
    elements.deleteSearch.disabled = !saved;
    if (!saved) return;
    app.filters = { ...DEFAULT_FILTERS, ...saved.filters };
    app.visibleLimit = PAGE_SIZE;
    syncControls();
    render();
    showToast(`Loaded “${saved.name}”.`);
  });
  elements.deleteSearch.addEventListener("click", () => {
    const id = elements.savedSearches.value;
    const saved = app.savedSearches.find((item) => item.id === id);
    if (!saved || !window.confirm(`Delete the saved search “${saved.name}”?`)) return;
    app.savedSearches = app.savedSearches.filter((item) => item.id !== id);
    writeJsonStorage(SAVED_SEARCHES_KEY, app.savedSearches);
    populateSavedSearches();
    showToast("Saved search deleted.");
  });

  window.addEventListener("popstate", () => {
    app.filters = { ...DEFAULT_FILTERS, ...parseUrlState(location.search) };
    app.visibleLimit = PAGE_SIZE;
    syncControls();
    render({ writeUrl: false });
  });
  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isTyping =
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target instanceof HTMLSelectElement ||
      target?.isContentEditable;
    if (event.key === "/" && !isTyping && !event.metaKey && !event.ctrlKey && !event.altKey) {
      event.preventDefault();
      elements.search.focus();
    }
  });
}

function cacheElements() {
  const byId = (id) => document.getElementById(id);
  app.elements = {
    notice: byId("data-notice"),
    noticeText: byId("data-notice-text"),
    search: byId("search"),
    timeWindow: byId("window-filter"),
    venue: byId("venue-filter"),
    year: byId("year-filter"),
    relevance: byId("relevance-filter"),
    availability: byId("availability-filter"),
    topic: byId("topic-filter"),
    method: byId("method-filter"),
    layer: byId("layer-filter"),
    contribution: byId("contribution-filter"),
    institution: byId("institution-filter"),
    group: byId("group-filter"),
    faculty: byId("faculty-filter"),
    award: byId("award-filter"),
    region: byId("region-filter"),
    country: byId("country-filter"),
    city: byId("city-filter"),
    sector: byId("sector-filter"),
    completeOnly: byId("complete-filter"),
    starredOnly: byId("starred-filter"),
    reading: byId("reading-filter"),
    shortlist: byId("shortlist-filter"),
    sort: byId("sort-results"),
    clear: byId("clear-filters"),
    emptyClear: byId("empty-clear"),
    paperList: byId("paper-list"),
    results: byId("results"),
    resultCount: byId("result-count"),
    empty: byId("empty-state"),
    emptyTitle: byId("empty-title"),
    emptyMessage: byId("empty-message"),
    error: byId("error-state"),
    errorMessage: byId("error-message"),
    loading: byId("loading-state"),
    retry: byId("retry-load"),
    loadMore: byId("load-more"),
    theme: byId("theme-toggle"),
    presets: byId("preset-list"),
    activeFilters: byId("active-filters"),
    activeFilterList: byId("active-filter-list"),
    advancedFilters: byId("advanced-filters"),
    advancedCount: byId("advanced-count"),
    viewButtons: [...document.querySelectorAll("[data-view]")],
    exportButtons: [...document.querySelectorAll("[data-export]")],
    savedSearches: byId("saved-searches"),
    saveSearch: byId("save-search"),
    deleteSearch: byId("delete-search"),
    annotationDialog: byId("annotation-dialog"),
    annotationForm: byId("annotation-form"),
    annotationTitle: byId("annotation-title"),
    annotationPaperId: byId("annotation-paper-id"),
    annotationStarred: byId("annotation-starred"),
    annotationReading: byId("annotation-reading"),
    annotationNotes: byId("annotation-notes"),
    annotationTags: byId("annotation-tags"),
    annotationShortlists: byId("annotation-shortlists"),
    annotationClose: byId("annotation-close"),
    annotationCancel: byId("annotation-cancel"),
    savedSearchDialog: byId("saved-search-dialog"),
    savedSearchForm: byId("saved-search-form"),
    savedSearchName: byId("saved-search-name"),
    savedSearchClose: byId("saved-search-close"),
    savedSearchCancel: byId("saved-search-cancel"),
    toast: byId("toast"),
  };
}

function initialize() {
  cacheElements();
  app.library = loadLibrary();
  app.savedSearches = loadSavedSearches();
  populateSavedSearches();
  initializeTheme();
  wireControls();
  loadData();
}

const testApi = {
  DEFAULT_FILTERS,
  annotationFor,
  editDistanceWithin,
  evaluateTerms,
  exportRecords,
  filterPapers,
  findHighlightRanges,
  humanize,
  matchesStructuredFilters,
  normalizeForSearch,
  normalizePaper,
  parseQuery,
  parseUrlState,
  recordsToBibtex,
  recordsToCsv,
  serializeFilters,
  sortResults,
  termMatchesValue,
  validatePayload,
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = testApi;
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
}
