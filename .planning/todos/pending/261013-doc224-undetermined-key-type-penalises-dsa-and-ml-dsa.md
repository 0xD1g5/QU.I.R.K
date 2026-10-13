---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §3 Agility table)
priority: medium
area: quirk/intelligence/evidence.py (cert_key_type_counts), quirk/intelligence/scoring.py
status: pending
resolves_phase: null
---

# ML-DSA and DSA certificates take the "Certificate key types undetermined" -8 penalty

`cert_key_type_counts` buckets only RSA, EC/ECDSA and EdDSA prefixes (`quirk/intelligence/evidence.py:258-264`).
Any other `cert_pubkey_alg` (DSA, ML-DSA-65, ...) is uncounted, so when no certificate falls in a bucket the scorer
applies "Certificate key types undetermined" (`quirk/intelligence/scoring.py:546-548`), the same worst-case penalty as
RSA-only. A post-quantum ML-DSA certificate is therefore penalised as if its key type were unknown. Confirmed by a
`gc3-r3-f1-*` scoring probe.

When fixed, update docs/report-interpretation.md §3 Agility table, "Certificate key types undetermined" row.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `evidence.py:258-264` (three prefix branches only); `scoring.py:546-548` (penalty).
- Fix: add a PQC bucket (ML-DSA/SLH-DSA) that counts as determined (and arguably earns a bonus), and decide DSA.
- Unknown: CBOM classifier naming for PQC signature algs (`quirk/cbom/classifier.py`) to keep prefixes consistent.
