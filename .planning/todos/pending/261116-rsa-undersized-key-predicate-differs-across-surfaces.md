---
type: todo
created: 2026-11-16
source: Phase 236 review WR-03 (236-REVIEW.md), filed by plan 236-09
priority: medium
area: quirk/dashboard/api/finding_derivation.py, quirk/engine/findings_evaluator.py
status: pending
resolves_phase:
owner: "999.132"
---

# The undersized RSA key predicate differs between the dashboard and the report

The dashboard fires on `cert_pubkey_alg.upper().startswith("RSA")` with a truthy `cert_pubkey_size` below 2048
(`quirk/dashboard/api/finding_derivation.py`, the undersized RSA block). The report fires on `alg.strip().upper() == "RSA"` with
`size is not None` below 2048 (`quirk/engine/findings_evaluator.py`, the undersized RSA block). So a size of 0 is a report-only
HIGH and an RSA-PSS key at 1024 bits is a dashboard-only HIGH.

Verified still open at the 236-09 fix commit. The families `rsa_size_0` and `rsa_pss_1024` were deliberately not added to
`FAMILY_ROWS` in plan 236-09 because they diverge today; add them when this is fixed. Fix: use the report predicate verbatim on the
dashboard (review WR-03).

## Feasibility & Effort

**Feasibility: HIGH.** One predicate, a few lines. **Effort: S.** Score-moving on both sides for the odd rows, so pin the new headline numbers.
