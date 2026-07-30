Build a production-quality research discovery website named:

    Systems PhD Explorer

Primary user:

A student preparing for Fall 2027 PhD applications who needs to:

1. Understand the major research directions in computer systems.
2. Discover active faculty members and research groups.
3. Compare potential supervisors.
4. Read beginner-friendly summaries of recent papers.
5. Search and filter papers without manually navigating conference programs.

This is not merely a paper-list scraper. It is a structured paper,
research-group, and potential-supervisor discovery system.

======================================================================
1. TIME AND VENUE SCOPE
======================================================================

Default application-oriented window:

    2023 through 2026 year-to-date

Also support:

- strict rolling 36-month filtering
- individual-year selection
- complete years only
- inclusion or exclusion of incomplete 2026 proceedings

Venues:

Systems:
1. OSDI — USENIX Symposium on Operating Systems Design and Implementation
2. SOSP — ACM Symposium on Operating Systems Principles
3. EuroSys — ACM European Conference on Computer Systems
4. ASPLOS — ACM International Conference on Architectural Support for
   Programming Languages and Operating Systems
5. USENIX ATC — USENIX Annual Technical Conference
6. FAST — USENIX Conference on File and Storage Technologies

Networking:
7. SIGCOMM — ACM SIGCOMM
8. NSDI — USENIX Symposium on Networked Systems Design and Implementation

Security:
9. ACM CCS — ACM Conference on Computer and Communications Security
10. NDSS — Network and Distributed System Security Symposium
11. IEEE S&P — IEEE Symposium on Security and Privacy
12. USENIX Security — USENIX Security Symposium

For every venue and year, record:
- venue
- year
- official conference URL
- official proceedings or accepted-paper URL
- conference start and end dates
- collection status:
    - complete proceedings
    - accepted papers only
    - partial
    - upcoming
    - unavailable
- date last verified
- number of main-track papers found
- number included as core systems
- number included as systems-adjacent
- number excluded

Never treat an unpublished or upcoming program as containing zero papers.

Exclude workshops, posters, demos, keynotes, invited talks, doctoral
consortium papers, and non-archival abstracts unless the item is officially
part of the main peer-reviewed technical paper program.

======================================================================
2. DEFINITION OF “RELEVANT”
======================================================================

The database should contain all papers that are relevant to a broad
computer-systems PhD search.

Assign every paper one of:

- CORE_SYSTEMS
- SYSTEMS_ADJACENT
- EXCLUDED
- NEEDS_HUMAN_REVIEW

CORE_SYSTEMS includes work whose primary contribution is in:

- operating systems
- kernels and kernel verification
- distributed systems
- databases and transaction systems
- storage and file systems
- networking and networked systems
- cloud computing
- serverless computing
- datacenter systems
- virtualization
- containers and isolation
- resource management and scheduling
- hardware/software co-design
- computer architecture
- compilers and runtimes with a systems contribution
- programming-language mechanisms for systems
- systems verification
- reliability, fault tolerance, testing, and debugging
- observability and performance diagnosis
- mobile, edge, embedded, and IoT systems
- machine-learning systems
- high-performance computing
- energy-efficient and sustainable systems
- privacy-preserving systems
- systems security

SYSTEMS_ADJACENT includes work useful to a systems applicant but whose
primary contribution may lie in:

- program analysis
- formal methods
- software security
- hardware security
- trusted execution environments
- fuzzing and vulnerability discovery
- network security
- privacy infrastructure
- robotics or cyber-physical infrastructure
- applied machine learning with a significant systems artifact

For broad security venues, do not automatically include every paper.

Usually exclude:

- pure cryptographic protocol or primitive design
- purely theoretical security
- purely social-science security studies
- phishing/user-perception studies without a systems contribution
- policy-only work
- pure ML attacks or defenses without a systems artifact
- content moderation
- misinformation analysis
- biometric classification without a systems contribution

For ASPLOS, exclude papers that are purely about a new ML algorithm with
no architecture, compiler, runtime, or systems contribution.

For every inclusion or exclusion, store:

- relevance class
- relevance score from 0 to 5
- one-sentence inclusion or exclusion rationale
- relevant system layer
- confidence level

Do not use the relevance score as a quality or prestige score.

======================================================================
3. PAPER METADATA
======================================================================

For every included paper, collect:

Identity:
- stable internal paper ID
- exact title
- authors in published order
- conference
- year
- track or session, when available
- DOI
- official paper page
- official PDF
- artifact or code URL
- project website
- slides
- presentation video
- official BibTeX

Publication:
- publication date
- paper type
- page count
- venue-year completion status
- source URLs
- last-verified timestamp

Affiliations:
- affiliation of each author at publication time
- normalized institution name
- institution type:
    - university
    - industrial research lab
    - government lab
    - nonprofit
    - independent
- city
- state or province
- country
- broad geographic region

Do not merge publication-time affiliation with a person’s current
affiliation.

Deduplicate:
- duplicate conference entries
- title punctuation variations
- arXiv versus conference versions
- extended journal versions
- papers appearing on multiple program pages

Retain the official conference paper as the canonical record while linking
other versions.

======================================================================
4. BEGINNER-FRIENDLY SUMMARY
======================================================================

Read at least:

- abstract
- introduction
- conclusion
- system overview or design section
- evaluation overview

Do not summarize from the title or abstract alone when the full paper is
available.

For each paper produce:

A. One-line takeaway
Maximum 35 words.

B. Background
Explain the realm and the normal way the relevant systems currently work.
Assume the reader is a computer-science student but new to this subfield.

C. Villain
Describe the concrete bottleneck, failure mode, cost, limitation, security
risk, or missing capability.

D. How they beat the villain
Explain the central idea and system design.
Focus on the conceptual mechanism rather than low-level implementation
details.

E. So what
Explain what becomes possible or meaningfully better if the work succeeds.

F. Evaluation
At a high level:
- what they implemented
- where they tested it
- what baselines they compared against
- one to three important quantitative results
- whether the evaluation is simulation, prototype, production deployment,
  trace replay, formal proof, user study, or measurement study

G. Limitations and assumptions
Record important limitations, deployment assumptions, special hardware
requirements, trusted components, workload assumptions, or missing
evaluations.

H. Why this paper is useful for choosing a PhD group
Explain what the paper reveals about:
- the group’s research taste
- preferred methodology
- systems layer
- typical artifacts
- relationship between theory and implementation

I. Beginner concepts
List three to eight concepts a newcomer may need to understand first.

J. Tags
Assign hierarchical and multi-label taxonomy tags.

Summary requirements:

- Avoid unexplained jargon.
- Do not reproduce the abstract.
- Do not make unsupported claims.
- Clearly distinguish the paper’s claim from independently verified fact.
- Do not call a result “state of the art” unless that is both relevant and
  supported.
- Do not invent limitations merely to fill the field.
- Store source provenance for factual claims and important numbers.

======================================================================
5. TAXONOMY
======================================================================

Use a hierarchical, multi-label taxonomy.

Top-level tracks:

1. Operating Systems and Kernels
2. Distributed Systems
3. Databases and Data Processing
4. Storage and File Systems
5. Networking
6. Cloud and Datacenter Systems
7. Virtualization and Isolation
8. Computer Architecture
9. Compilers, Languages, and Runtimes
10. Formal Methods and Systems Verification
11. Systems Security
12. Hardware Security
13. Network Security
14. Reliability, Testing, and Debugging
15. Resource Management and Scheduling
16. ML Systems
17. Mobile, Edge, Embedded, and IoT
18. High-Performance Computing
19. Privacy Systems
20. Energy and Sustainable Computing
21. Measurement and Empirical Systems Studies

Example subtopics:

Operating Systems and Kernels:
- Linux
- eBPF
- kernel extensibility
- memory management
- concurrency
- synchronization
- scheduling
- device drivers
- memory safety
- capability systems
- unikernels
- kernel verification

Distributed Systems:
- consensus
- replication
- fault tolerance
- distributed transactions
- consistency
- geo-distribution
- coordination
- distributed debugging
- Byzantine systems

Storage:
- file systems
- key-value stores
- persistent memory
- SSD and flash
- disaggregated storage
- caching
- crash consistency
- deduplication
- storage reliability

Networking:
- transport protocols
- congestion control
- programmable networks
- datacenter networking
- wireless
- network measurement
- middleboxes
- RDMA
- network verification

Architecture:
- processors
- memory hierarchy
- accelerators
- chiplets
- heterogeneous computing
- persistent memory
- secure architecture
- hardware/software co-design

Systems Security:
- kernel security
- memory safety
- isolation
- sandboxing
- trusted computing
- confidential computing
- supply-chain security
- fuzzing
- vulnerability discovery
- program analysis
- authentication infrastructure

ML Systems:
- training systems
- inference systems
- distributed ML
- model serving
- GPU scheduling
- accelerator systems
- data pipelines
- LLM systems

Also classify each paper by:

System layer:
- hardware
- firmware
- hypervisor
- kernel
- runtime
- middleware
- distributed service
- application infrastructure
- network
- storage

Contribution type:
- new system
- new mechanism
- optimization
- formal model or proof
- measurement study
- bug-finding or testing tool
- benchmark
- dataset
- language or API
- deployment experience
- security attack
- defense

Method:
- implementation
- formal verification
- static analysis
- dynamic analysis
- fuzzing
- simulation
- trace analysis
- production deployment
- hardware prototype
- user study

Do not force a paper into only one topic.

======================================================================
6. RESEARCH GROUP AND PI RESOLUTION
======================================================================

The purpose is to help select potential supervisors.

A paper can belong to multiple research groups. Do not force one “owner.”

For every academic group associated with a paper, collect:

- group or lab name
- official lab URL
- PI or faculty member name
- official faculty profile URL
- institution
- department
- publication-time institution
- current institution
- faculty rank, when officially available
- city
- state or province
- country
- geographic region
- research topics
- papers in this corpus
- years active in this corpus
- student and collaborator names represented in this corpus
- evidence supporting the group-paper association
- confidence level
- last-verified date

For industrial groups, collect:

- company or organization
- research division
- group page, when available
- location
- associated authors

Critical attribution rule:

Never infer that the last author is the PI merely from author order.

Associate a paper with a lab or PI only when supported by evidence such as:

- an official lab publication page
- an official faculty publication page
- an official student profile naming the advisor
- an institution page
- the paper or project page itself

When no reliable group attribution is available:

- preserve the author and affiliation data
- mark the group as unresolved
- place it in a human-review queue

Store both:
- publication-time affiliation
- current affiliation as of the last verification date

Faculty moves must not rewrite historical affiliation.

Optionally record whether a faculty member explicitly says they are
recruiting students, but only when:

- an official current source states it
- the exact wording is not paraphrased misleadingly
- the source and verification date are stored

Never infer recruiting status from the existence of recent papers.

======================================================================
7. AWARDS
======================================================================

Collect:

- best paper
- distinguished paper
- best student paper
- best practical paper
- community award
- test-of-time award
- artifact award
- honorable mention
- other official paper-level awards

For each award store:

- exact official award name
- venue
- year
- paper
- official award source
- last-verified date

Use official conference or sponsoring-organization sources.

Do not infer an award from:
- an author CV alone
- a lab news page alone
- social-media posts
- search-result snippets

Those sources may be used only to locate the official source.

Display different award categories separately rather than reducing them to
one generic “award winner” field.

======================================================================
8. WEBSITE FEATURES
======================================================================

The website must support four primary entity types:

- Papers
- Faculty / potential PIs
- Research groups
- Institutions

Global search:

Search across:
- paper titles
- summaries
- problem statements
- mechanisms
- tags
- authors
- faculty
- lab names
- institutions
- cities and countries

Search should support:
- exact phrase
- normal keyword search
- multiple keywords
- include and exclude terms
- typo tolerance
- highlighting of matching fields

Paper filters:

- conference
- year
- complete versus partial conference year
- core versus adjacent systems relevance
- top-level track
- subtopic
- system layer
- contribution type
- method
- award
- institution
- institution type
- academic versus industrial paper
- faculty member
- research group
- country
- geographic region
- city
- artifact or code availability

Faculty and group filters:

- research topic
- conference activity
- publication year
- institution
- country
- region
- academic rank
- number of relevant papers
- core versus adjacent topic activity
- experimental versus formal methodology
- hardware versus software emphasis

Views:

1. Paper table
2. Paper cards
3. Paper detail page
4. Faculty directory
5. Faculty detail page
6. Lab/group directory
7. Lab/group detail page
8. Institution page
9. Topic explorer
10. Geographic explorer
11. Compare supervisors
12. Saved shortlist

Paper detail page:

- title and metadata
- award badges
- story summary
- taxonomy
- evaluation summary
- limitations
- author and affiliation list
- associated labs and faculty
- paper/PDF/project/code links
- related papers
- provenance and last verification date

Faculty detail page:

- current institution and location
- official profile and lab links
- research-topic distribution
- recent paper timeline
- papers grouped by topic
- venues represented
- frequent collaborators
- student authors visible in the corpus
- contribution and methodology distribution
- saved notes
- shortlist control

Do not present paper count as a direct measure of advisor quality.

Supervisor comparison:

Allow comparison of two to five faculty members.

Show:
- institution and location
- research-topic distribution
- recent papers
- systems layers
- common methodologies
- venues
- academic and industrial collaborators
- award-winning papers
- project/code availability
- overlap with user-selected interests

Any match score must be transparent and user-configurable.
It must explain which selected criteria caused the score.
Do not generate a hidden prestige ranking.

User features:

- star a paper
- star a faculty member
- mark paper as unread / skimmed / read
- add private notes
- add custom tags
- create named shortlists
- save searches
- export selected records to CSV, JSON, or BibTeX
- preserve these locally without requiring an account

Provide presets:

- OS and Kernels
- Distributed Systems
- Storage
- Networking
- Architecture
- Systems Security
- Formal Verification
- Programming Languages for Systems
- Cloud and Datacenter
- ML Systems
- Embedded and Edge

Also permit user-defined tracks with include/exclude tags.

======================================================================
9. GEOGRAPHY
======================================================================

Normalize:

- institution
- city
- state or province
- country
- continent
- broad region

Suggested broad regions:

- United States
- Canada
- Europe
- United Kingdom and Ireland
- East Asia
- Southeast Asia
- South Asia
- Middle East
- Australia and New Zealand
- Latin America
- Africa

Support:

- region filtering
- country filtering
- city filtering
- institution filtering
- optional map view
- displaying publication-time and current faculty locations separately

Do not geocode personal home addresses.
Use only institution or official lab locations.

======================================================================
10. DATA PROVENANCE AND QUALITY
======================================================================

Source priority:

1. Official conference program or proceedings
2. Official publisher page
3. Official paper PDF
4. Official artifact or project page
5. Official institution, faculty, or lab page
6. DBLP
7. OpenAlex, Crossref, or Semantic Scholar as fallback metadata sources

Every record must include:

- source URLs
- collection timestamp
- verification timestamp
- collector version
- confidence level
- unresolved fields
- human-review status

Confidence values:

- VERIFIED
- HIGH
- MEDIUM
- LOW
- UNRESOLVED

Use separate agents or passes for:

1. Collection
2. Relevance classification
3. Summary generation
4. Group and PI resolution
5. Award verification
6. Independent factual review

A summary generator must not approve its own output as verified.

Validation:

- check DOI format
- verify paper links
- verify PDF links
- detect duplicate papers
- detect duplicate faculty
- normalize institution aliases
- ensure award claims have official sources
- ensure every PI attribution has evidence
- flag summaries containing unsupported numerical claims
- randomly audit at least 10% of records
- place ambiguous records in a human-review queue

Never silently fill missing information by guessing.

======================================================================
11. DATA MODEL
======================================================================

Use stable versioned schemas.

Minimum entities:

Paper
Author
Authorship
Institution
Affiliation
Faculty
ResearchGroup
PaperGroupAssociation
Topic
PaperTopic
Award
VenueYear
Source
Summary
UserAnnotation

A paper record should roughly support:

{
  "id": "paper-stable-id",
  "title": "...",
  "venue": "OSDI",
  "year": 2025,
  "relevance": {
    "class": "CORE_SYSTEMS",
    "score": 5,
    "reason": "...",
    "confidence": "HIGH"
  },
  "summary": {
    "takeaway": "...",
    "background": "...",
    "villain": "...",
    "approach": "...",
    "impact": "...",
    "evaluation": "...",
    "limitations": "...",
    "phd_group_signal": "...",
    "beginner_concepts": []
  },
  "topics": [],
  "system_layers": [],
  "contribution_types": [],
  "methods": [],
  "authors": [],
  "groups": [],
  "awards": [],
  "links": {},
  "sources": [],
  "verification": {}
}

Do not store everything in one giant hand-edited JSON file.

Use:
- SQLite as canonical local storage
- migrations for schema changes
- JSON export for the static website
- CSV and BibTeX export
- validation schemas

======================================================================
12. IMPLEMENTATION ARCHITECTURE
======================================================================

Use a static-first design so the site remains easy to host.

Recommended structure:

systems-phd-explorer/
├── collectors/
│   ├── venues/
│   ├── papers/
│   ├── awards/
│   └── labs/
├── pipeline/
│   ├── normalize/
│   ├── relevance/
│   ├── summarize/
│   ├── resolve_groups/
│   ├── validate/
│   └── export/
├── data/
│   ├── database.sqlite
│   ├── review_queue/
│   └── exports/
├── schemas/
├── site/
├── tests/
├── docs/
└── reports/

Technical requirements:

- resumable and incremental collection
- idempotent collectors
- per-record failure logging
- rate limiting
- caching of small metadata responses
- no permanent local archive of all PDFs
- download a PDF temporarily when needed
- delete temporary PDFs after extraction
- retain URL, hash, metadata, and structured summary
- do not store conference videos
- do not create multiple copies of the dataset
- support static deployment
- support GitHub Pages or equivalent hosting
- perform search entirely client-side where practical

Keep the complete project, excluding optional temporary files, below 5 GiB.

The final paper metadata and summaries should generally occupy far less.

======================================================================
13. USER EXPERIENCE
======================================================================

The interface should be optimized for research exploration, not visual
decoration.

Required:

- dense but readable information
- responsive layout
- keyboard-accessible search and filters
- shareable URLs encoding current filters
- no horizontal scrolling for normal use
- persistent selected filters
- clear indication of incomplete 2026 data
- clear indication of low-confidence records
- visible source and verification information
- fast page load
- no mandatory login
- light and dark themes
- accessible contrast
- desktop-first but usable on mobile

Search results should show:

- title
- venue and year
- one-line takeaway
- primary topics
- institution and group
- faculty
- award badges
- relevance class
- availability of code/artifact
- location

======================================================================
14. REPORTS FOR THE USER
======================================================================

Generate reports in addition to the website:

1. Topic overview
   - major realms
   - beginner description
   - representative papers
   - active groups

2. Faculty activity report
   - faculty by topic
   - recent papers
   - institution and geography
   - no prestige ranking

3. Institution overview
   - groups and faculty
   - topic distribution
   - recent relevant papers

4. Venue coverage report
   - expected venue-years
   - collection status
   - included/excluded counts
   - unresolved records

5. Data-quality report
   - broken links
   - unresolved labs
   - uncertain classifications
   - missing summaries
   - unsupported award claims

6. Application shortlist export
   - selected PIs
   - related papers
   - reasons selected
   - notes
   - official links

======================================================================
15. EXECUTION PHASES
======================================================================

Do not attempt to scrape, summarize, resolve faculty, and build the entire
interface in one uncontrolled run.

Phase 0 — Specification and infrastructure
- define schemas
- define taxonomy
- define inclusion rules
- create database and migrations
- create test fixtures
- implement source and provenance model

Phase 1 — One-year pilot
- collect all 2025 venue programs
- classify all papers
- fully summarize a representative sample
- resolve groups and awards
- build a minimal searchable website
- review error patterns

Phase 2 — Complete recent corpus
- add 2023 and 2024
- add available 2026 data
- mark incomplete venue-years
- complete all core-systems summaries
- process systems-adjacent papers

Phase 3 — Faculty and lab explorer
- resolve faculty and labs
- normalize institution geography
- build faculty, lab, and institution pages
- build supervisor comparison

Phase 4 — Quality review
- independent review
- fix duplicates
- verify award claims
- audit PI attribution
- audit summaries
- resolve or expose uncertain cases

Phase 5 — Deployment
- produce static export
- build searchable frontend
- add local annotations and shortlist
- write maintenance documentation

At the end of every phase:

- run tests
- generate coverage statistics
- report unresolved issues
- record exact source coverage
- do not claim completeness without evidence

======================================================================
16. PARALLEL AGENT PLAN
======================================================================

Use independent bounded agents.

Agent A:
OSDI, SOSP, EuroSys, and ATC collection.

Agent B:
FAST, NSDI, and SIGCOMM collection.

Agent C:
ASPLOS collection and architecture taxonomy.

Agent D:
CCS, NDSS, IEEE S&P, and USENIX Security collection and systems-relevance
screening.

Agent E:
Paper-summary generation.

Agent F:
Faculty, lab, institution, and geography resolution.

Agent G:
Award verification.

Agent H:
Independent reviewer that challenges:
- paper inclusion
- summary accuracy
- PI attribution
- awards
- duplicate detection

Agent I:
Frontend and search interface.

Agents must write to separate data shards or branches.
Do not allow multiple agents to edit the same canonical database directly.
Merge only after schema validation.

======================================================================
17. COMPLETION CRITERIA
======================================================================

The project is not complete merely because a webpage renders.

Completion requires:

- every expected venue-year has an explicit status
- every main-track paper has been considered
- every included paper has a relevance rationale
- every core paper has a complete story summary
- every award has an official source
- every PI/lab attribution has evidence or is marked unresolved
- every paper has taxonomy tags
- every record has provenance
- duplicate and broken-link checks pass
- the website supports paper, PI, lab, institution, topic, and geographic
  exploration
- saved searches, annotations, shortlists, and export work
- incomplete 2026 coverage is visibly marked
- a human-review queue remains available instead of guessed data

Begin by creating:

1. `docs/scope.md`
2. `docs/inclusion-policy.md`
3. `docs/taxonomy.md`
4. `docs/source-policy.md`
5. versioned database schemas
6. venue-year manifest for 2023–2026
7. a pilot collector for one USENIX venue and one ACM venue
8. a minimal searchable frontend using fixture data

Do not begin bulk summarization until the schema, source policy, and pilot
records have passed review.