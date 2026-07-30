PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    applied_at TEXT NOT NULL
);

CREATE TABLE venue_year (
    venue TEXT NOT NULL,
    year INTEGER NOT NULL CHECK (year BETWEEN 2023 AND 2026),
    official_conference_url TEXT,
    official_program_url TEXT,
    conference_start TEXT,
    conference_end TEXT,
    collection_status TEXT NOT NULL CHECK (
        collection_status IN (
            'UNVERIFIED',
            'COMPLETE_PROCEEDINGS',
            'ACCEPTED_PAPERS_ONLY',
            'PARTIAL',
            'UPCOMING',
            'UNAVAILABLE'
        )
    ),
    workflow_status TEXT NOT NULL,
    main_track_count INTEGER CHECK (main_track_count >= 0),
    core_systems_count INTEGER CHECK (core_systems_count >= 0),
    systems_adjacent_count INTEGER CHECK (systems_adjacent_count >= 0),
    excluded_count INTEGER CHECK (excluded_count >= 0),
    needs_review_count INTEGER CHECK (needs_review_count >= 0),
    last_verified_at TEXT,
    source_path TEXT NOT NULL,
    PRIMARY KEY (venue, year)
);

CREATE TABLE paper (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    venue TEXT NOT NULL,
    year INTEGER NOT NULL,
    track_or_session TEXT,
    paper_type TEXT NOT NULL,
    publication_date TEXT,
    page_count INTEGER CHECK (page_count IS NULL OR page_count > 0),
    venue_year_completion_status TEXT NOT NULL,
    relevance_class TEXT NOT NULL,
    relevance_score INTEGER NOT NULL CHECK (relevance_score BETWEEN 0 AND 5),
    relevance_rationale TEXT NOT NULL,
    relevance_confidence TEXT NOT NULL,
    links_json TEXT NOT NULL,
    alternate_versions_json TEXT NOT NULL,
    metadata_workflow_status TEXT NOT NULL,
    relevance_workflow_status TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    FOREIGN KEY (venue, year) REFERENCES venue_year (venue, year)
);

CREATE INDEX paper_venue_year_idx ON paper (venue, year);
CREATE INDEX paper_relevance_idx ON paper (relevance_class, relevance_score);
CREATE INDEX paper_normalized_title_idx ON paper (normalized_title);

CREATE TABLE author (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    orcid TEXT,
    identity_confidence TEXT NOT NULL DEFAULT 'UNRESOLVED'
);

CREATE TABLE institution (
    id TEXT PRIMARY KEY,
    normalized_name TEXT NOT NULL,
    institution_type TEXT NOT NULL,
    city TEXT,
    state_or_province TEXT,
    country TEXT,
    region TEXT,
    official_url TEXT,
    current_record_confidence TEXT NOT NULL DEFAULT 'UNRESOLVED',
    last_verified_at TEXT
);

CREATE TABLE authorship (
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position > 0),
    author_id TEXT REFERENCES author (id),
    name_as_published TEXT NOT NULL,
    orcid_as_published TEXT,
    PRIMARY KEY (paper_id, position),
    UNIQUE (paper_id, author_id)
);

CREATE TABLE affiliation (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL,
    author_position INTEGER NOT NULL,
    institution_id TEXT REFERENCES institution (id),
    name_as_published TEXT NOT NULL,
    normalized_name TEXT,
    institution_type TEXT NOT NULL,
    city TEXT,
    state_or_province TEXT,
    country TEXT,
    region TEXT,
    source_ids_json TEXT NOT NULL,
    FOREIGN KEY (paper_id, author_position)
        REFERENCES authorship (paper_id, position) ON DELETE CASCADE
);

CREATE TABLE faculty (
    id TEXT PRIMARY KEY,
    author_id TEXT UNIQUE REFERENCES author (id),
    display_name TEXT NOT NULL,
    official_profile_url TEXT,
    current_institution_id TEXT REFERENCES institution (id),
    department TEXT,
    faculty_rank TEXT,
    city TEXT,
    state_or_province TEXT,
    country TEXT,
    region TEXT,
    recruiting_statement TEXT,
    recruiting_source_id TEXT,
    confidence TEXT NOT NULL,
    last_verified_at TEXT
);

CREATE TABLE research_group (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    official_url TEXT,
    institution_id TEXT REFERENCES institution (id),
    department TEXT,
    group_kind TEXT NOT NULL CHECK (group_kind IN ('academic', 'industrial', 'other')),
    research_topics_json TEXT NOT NULL,
    confidence TEXT NOT NULL,
    last_verified_at TEXT
);

CREATE TABLE research_group_faculty (
    group_id TEXT NOT NULL REFERENCES research_group (id) ON DELETE CASCADE,
    faculty_id TEXT NOT NULL REFERENCES faculty (id),
    PRIMARY KEY (group_id, faculty_id)
);

CREATE TABLE paper_group_association (
    id INTEGER PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    group_id TEXT REFERENCES research_group (id),
    faculty_id TEXT REFERENCES faculty (id),
    publication_institution_id TEXT REFERENCES institution (id),
    current_institution_id TEXT REFERENCES institution (id),
    association_type TEXT NOT NULL,
    rationale TEXT NOT NULL,
    evidence_source_ids_json TEXT NOT NULL,
    confidence TEXT NOT NULL,
    UNIQUE (paper_id, group_id, faculty_id)
);

CREATE TABLE topic (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL
);

CREATE TABLE topic_parent (
    topic_id TEXT NOT NULL REFERENCES topic (id),
    parent_id TEXT NOT NULL REFERENCES topic (id),
    PRIMARY KEY (topic_id, parent_id),
    CHECK (topic_id <> parent_id)
);

CREATE TABLE paper_topic (
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    topic_id TEXT NOT NULL REFERENCES topic (id),
    PRIMARY KEY (paper_id, topic_id)
);

CREATE TABLE paper_system_layer (
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    system_layer TEXT NOT NULL,
    PRIMARY KEY (paper_id, system_layer)
);

CREATE TABLE paper_contribution_type (
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    contribution_type TEXT NOT NULL,
    PRIMARY KEY (paper_id, contribution_type)
);

CREATE TABLE paper_method (
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    method TEXT NOT NULL,
    PRIMARY KEY (paper_id, method)
);

CREATE TABLE source (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT,
    publisher TEXT,
    retrieved_at TEXT NOT NULL,
    content_hash TEXT,
    official INTEGER NOT NULL CHECK (official IN (0, 1)),
    supports_json TEXT NOT NULL
);

CREATE INDEX source_url_idx ON source (url);

CREATE TABLE record_source (
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES source (id),
    PRIMARY KEY (record_type, record_id, stage, source_id)
);

CREATE TABLE summary (
    paper_id TEXT PRIMARY KEY REFERENCES paper (id) ON DELETE CASCADE,
    takeaway TEXT,
    background TEXT,
    villain TEXT,
    approach TEXT,
    impact TEXT,
    evaluation_json TEXT NOT NULL,
    limitations TEXT,
    phd_group_signal TEXT,
    beginner_concepts_json TEXT NOT NULL,
    reading_coverage_json TEXT NOT NULL,
    workflow_status TEXT NOT NULL,
    confidence TEXT NOT NULL,
    last_verified_at TEXT
);

CREATE TABLE summary_claim (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    locator TEXT,
    source_ids_json TEXT NOT NULL
);

CREATE TABLE award (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    official_name TEXT NOT NULL,
    category TEXT NOT NULL,
    venue TEXT NOT NULL,
    year INTEGER NOT NULL,
    official_source_id TEXT NOT NULL REFERENCES source (id),
    last_verified_at TEXT NOT NULL
);

CREATE TABLE review_issue (
    id TEXT NOT NULL,
    paper_id TEXT NOT NULL REFERENCES paper (id) ON DELETE CASCADE,
    severity TEXT NOT NULL,
    stage TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    reviewer TEXT,
    PRIMARY KEY (paper_id, id)
);

CREATE TABLE user_annotation (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (
        entity_type IN ('paper', 'faculty', 'research-group', 'institution')
    ),
    entity_id TEXT NOT NULL,
    starred INTEGER NOT NULL DEFAULT 0 CHECK (starred IN (0, 1)),
    reading_status TEXT CHECK (reading_status IN ('unread', 'skimmed', 'read')),
    private_note TEXT,
    custom_tags_json TEXT NOT NULL DEFAULT '[]',
    shortlist_ids_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

INSERT INTO schema_migrations (version, name, applied_at)
VALUES (1, '001_initial.sql', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));
