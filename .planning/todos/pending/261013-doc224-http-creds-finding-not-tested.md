---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md REST Fuzzing findings table)
priority: low
area: quirk/scanner/rest_fuzzer.py
status: pending
resolves_phase: null
owner: "999.136"
---

# `http_creds` HIGH finding is raised without testing the endpoint

`quirk/scanner/rest_fuzzer.py:699` raises "HTTP-only credential transmission" (HIGH, feeds
`agility_fuzz_crypto_posture_ratio`) for any spec-declared `http://` URL whenever an `--auth-*` credential
exists. It never sends the credential to see whether the endpoint accepts it (the comment says "Open
Question 2 resolution"). docs/configuration.md's finding table now says what triggers it.

- [ ] Decide: keep the finding as a spec-level risk (and rename/describe it so), or test acceptance.

## Feasibility & Effort

- **Feasibility: LIKELY** (design gap, not a crash).
- **Effort: S-M**, since sending a credential over HTTP needs a safety decision.
- **Unknowns:** the scoring impact of re-labelling.
- **Spike:** no.
