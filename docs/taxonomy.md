# Taxonomy

The canonical machine-readable taxonomy is
[`config/taxonomy.v1.json`](../config/taxonomy.v1.json). Paper tags use stable
IDs from that file, not display labels typed by hand.

## Principles

- Taxonomy is hierarchical and multi-label.
- A paper can have several top-level tracks and subtopics.
- Topic, system layer, contribution type, and method are separate axes.
- A tag indicates subject matter, not quality.
- New tags require a versioned taxonomy change and an alias or migration when a
  prior ID is replaced.

## Top-level tracks

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

## Orthogonal axes

System layers:

`hardware`, `firmware`, `hypervisor`, `kernel`, `runtime`, `middleware`,
`distributed-service`, `application-infrastructure`, `network`, and `storage`.

Contribution types:

`new-system`, `new-mechanism`, `optimization`, `formal-model-or-proof`,
`measurement-study`, `bug-finding-or-testing-tool`, `benchmark`, `dataset`,
`language-or-api`, `deployment-experience`, `security-attack`, and `defense`.

Methods:

`implementation`, `formal-verification`, `static-analysis`, `dynamic-analysis`,
`fuzzing`, `simulation`, `trace-analysis`, `production-deployment`,
`hardware-prototype`, and `user-study`.

## Adding a tag

1. Confirm no existing tag or alias expresses the concept.
2. Add a stable kebab-case ID to a new taxonomy version.
3. Give it one parent track.
4. Document any alias or replacement.
5. Add a validation test.
6. Migrate records through tooling; do not search-and-replace agent shards
   during active collection.
