# Coordination

Each active agent creates one uniquely named JSON file in `claims/` from the
example. Agents never edit a shared claim registry.

Recommended IDs include the role and a unique suffix, for example
`collector-osdi-2025-a`. Remove or mark the claim `COMPLETE` only in that same
file. Claims communicate ownership; schema validation and code review still
enforce the handoff.

Paste-ready assignments and execution waves are under `tasks/README.md`.
