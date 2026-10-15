---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §16 burndown buckets)
priority: medium
area: quirk/intelligence/burndown.py
status: pending
resolves_phase: null
owner: "999.133"
---

# EO 14412 burndown never counts TLS or SSH findings against the key-establishment deadline

The burndown reads only `cert_pubkey_alg`, `cert_sig_alg` and `cipher_suite` (`quirk/intelligence/burndown.py:120-124`)
and classifies each raw string (`quirk/scanner/pqc_deadlines.py:220-227`). A TLS suite name resolves to no deadline,
and SSH rows store the marker `SSH` (`quirk/scanner/ssh_scanner.py:59`). So no TLS/SSH finding is ever counted under
key establishment, the HNDL-relevant deadline. Probe `gc3-r3-f4-burndown-bucket-probe.py`.

When fixed, update docs/report-interpretation.md §16 "Known gap: TLS and SSH findings do not reach the key-establishment row today".

## Feasibility & Effort

- **Verdict: LIKELY, effort M.** `burndown.py:120-124`; `pqc_deadlines.py:220-227`; `ssh_scanner.py:59`.
- Fix: decompose TLS suites with the CBOM's existing `_decompose_cipher_suite` (`quirk/cbom/builder.py:246`, `_KEX_MAP` `:200`) and read SSH kex from `ssh_audit_json`.
- Unknown: whether existing closure fingerprints need re-bucketing.
