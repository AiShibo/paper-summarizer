# Schema version 1

Every agent-authored JSON file has:

- a `$schema` URI;
- `schema_version: "1.0.0"`;
- a stable record or paper ID;
- explicit workflow state; and
- verification/provenance where applicable.

The schemas use JSON Schema Draft 2020-12. Structural validation is followed by
cross-file and release-profile checks implemented in
`src/systems_phd_explorer/validation.py`.

Schema changes are additive within a minor version. Breaking field or semantic
changes require `schemas/v2/` and a database migration.
