---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md REST Fuzzing)
priority: medium
area: run_scan.py (fuzz phase), quirk/scanner/openapi_scanner.py
status: pending
resolves_phase: null
owner: "999.136"
---

# `--fuzz` never fuzzes a URL OpenAPI spec

The OpenAPI phase fetches a URL spec (`quirk/scanner/openapi_scanner.py:126`
`_fetch_spec_bytes_from_url`). The fuzz phase then re-reads the spec with `_load_spec_bytes_from_file`
(`run_scan.py:3268`), which needs a local file (`openapi_scanner.py:106`). With a URL it logs
"REST fuzz: spec re-parse error", returns `[]` and never shows the CONFIRM prompt (fork TTY run).
docs/configuration.md now says `--fuzz` needs a local spec file, and its examples use `./openapi.json`.

- [ ] Reuse the dict the OpenAPI phase already parsed, or route URL specs through the scope-gated fetch.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (TTY run; call site `run_scan.py:3262-3270`).
- **Effort: S.**
- **Unknowns:** whether the fuzz phase should re-check scope for a URL spec (it should, via the fetch path).
- **Spike:** no.
