# Pilot collectors

Collectors discover candidate main-track entries from a locally saved official
page. They print candidates to standard output and never write the canonical
database or paper shards directly.

This boundary is intentional:

1. save or cache a small official program/proceedings HTML response;
2. run the venue adapter;
3. review its candidate JSON;
4. initialize each accepted candidate with `init-paper`; and
5. fill `metadata.json` with source evidence.

The Phase 0 pilots are:

- `venues/usenix_osdi.py`: USENIX presentation-link pages for OSDI;
- `venues/acm_sosp.py`: ACM Digital Library DOI-link pages for SOSP.

Both parsers are conservative and mark output as candidates, not verified
papers. Page structures change, so a successful parse never proves complete
coverage. The venue collector must record expected counts and audit exclusions
against the official program.

Example:

```sh
python3 collectors/venues/usenix_osdi.py \
  --html data/cache/osdi25-program.html \
  --source-url "https://official.example/program"
```

Temporary HTML belongs in ignored `data/cache/`. Do not commit bulk page
archives.
