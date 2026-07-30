# Database migrations

Migrations are immutable and applied in filename order to a fresh temporary
SQLite database during each build. Never edit an applied migration; add the
next zero-padded migration instead.

Agent-authored JSON shards remain the merge input. `data/database.sqlite` is
the canonical local query database after a successful build, but it is a
generated artifact and must never be edited directly or committed.
