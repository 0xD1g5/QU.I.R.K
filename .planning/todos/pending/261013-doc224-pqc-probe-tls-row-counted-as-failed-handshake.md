---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §19.6 certificate inventory, §21)
priority: medium
area: run_scan.py (PQC probe row), quirk/dashboard/api/routes/scan.py (excluded_cert_count)
status: pending
resolves_phase: null
---

# PQC probe's extra TLS row is counted as a failed handshake and as an unfingerprinted key-reuse endpoint

For each confirmed hybrid server the PQC probe writes an extra `protocol="TLS"` row with no certificate
(`run_scan.py:2832` `service_detail=f"pqc-hybrid-detected|group=X25519MLKEM768"`). `/api/scan/latest` computes
`excluded_cert_count = len(tls_endpoints) - len(real_cert_endpoints)` (`quirk/dashboard/api/routes/scan.py:1923`),
which the dashboard shows as "N TLS endpoints failed handshake"; Key Reuse also counts the row in `M`
(`quirk/intelligence/key_reuse.py:90-97`). Probe `gc3-r3-f5-*`: one good certificate shows "1 TLS endpoints failed
handshake".

When fixed, update docs/report-interpretation.md §19.6 (`N` counts the PQC probe row) and §21 coverage line.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `run_scan.py:2832`; `scan.py:1923`; `key_reuse.py:90-97`.
- Fix: exclude `service_detail LIKE 'pqc-hybrid-detected%'` rows from both counts, or give them their own protocol.
- Unknown: check CBOM and `evidence.py` `pqc_hybrid_endpoint_count` consumers before changing the protocol.
