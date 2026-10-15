---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-OPS-A-* (operators-guide.md section 6.2, PQC-hybrid probe)
priority: medium
area: run_scan.py, quirk/intelligence/evidence.py, quirk/intelligence/scoring.py
status: pending
resolves_phase: null
owner: "999.131"
---

# An "OpenSSL too old" advisory counts as a detected PQC-hybrid endpoint and lifts the "no PQC, no 100" ceiling

`run_scan.py` (`_run_pqc_phase`, around line 2840) emits an `ADVISORY` endpoint with
`service_detail="pqc-hybrid-detected|advisory=openssl-too-old"` for every TLS target where `X25519MLKEM768` was not
detected AND the scanning host's own `openssl` does not list ML-KEM. `build_evidence_summary`
(`quirk/intelligence/evidence.py:234`) increments `pqc_hybrid_endpoint_count` on the substring `pqc-hybrid-detected`, so
the advisory is counted exactly like a real detection (the comment calls this deliberate: "so PQC-03 scoring works on
old-OpenSSL hosts").

Consequence, reproduced 2026-10-12 against the source:

    build_evidence_summary([CryptoEndpoint(protocol="ADVISORY",
        service_detail="pqc-hybrid-detected|advisory=openssl-too-old")])["pqc_hybrid_endpoint_count"]   -> 1
    _pqc_readiness_ceiling(0) -> (84, 'no post-quantum key exchange observed')
    _pqc_readiness_ceiling(1) -> (None, None)

So a scan run from a machine with an old OpenSSL removes the 84-point "no PQC, no 100" ceiling (and earns the
`agility_pqc_hybrid_bonus`) for targets on which nothing post-quantum was observed. The score then depends on the
scanner host's OpenSSL build rather than on the estate. The operators guide now states the behaviour plainly.

- [ ] Decide the intended behaviour: an inconclusive probe should probably contribute neither the bonus nor the ceiling
      relief (count it separately, e.g. `pqc_probe_inconclusive_count`, and surface it as a coverage gap).
- [ ] If the current behaviour is intended, say why in the score methodology doc and in the report's PQC line.
- [ ] Add a scoring test that feeds the advisory row and asserts the chosen outcome.

## Feasibility & Effort

**CONFIRMED** by calling `build_evidence_summary` and `_pqc_readiness_ceiling` directly (output above) and by reading
`run_scan.py` `_run_pqc_phase`. Effort **S** to **M**: a counter split in `evidence.py` plus one branch in `scoring.py`
and a test; **M** if report wording and golden fixtures (`REGEN_CBOM_FIXTURES`) move. Unknown: whether the D-05 decision was
made for a reason beyond the code comment (PQC-03 requirements text). No spike needed.
