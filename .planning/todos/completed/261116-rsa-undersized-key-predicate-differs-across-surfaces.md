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

## Resolution (2026-11-17)

Fixed by Phase 238 (D-20): both surfaces use one predicate, `quirk.util.weak_crypto.is_undersized_rsa` (RSA or RSA-PSS, integer size, 0 < size < 2048). Size 0 is undetermined and raises no HIGH on either surface; an RSA-PSS key under 2048 bits is HIGH on both. This departs from the todo's "report predicate verbatim" on purpose (238 D-20). Families rsa_size_0 and rsa_pss_1024 added to FAMILY_ROWS with no residual. Commits main 82ebe634 (PR #86 merge; ba1df9aa, 78f0a7e2, 6039349a). Tests: tests/test_rsa_undersized_parity.py (3 nodes), tests/test_weak_crypto_helper.py. Behaviour change: report-mode scans of RSA size-0 rows lose a HIGH; RSA-PSS rows under 2048 bits gain one. Related open rows: 261117-rsa-pss-keys-reported-as-rsa, 261117-rsa-pss-large-key-no-quantum-vulnerable-finding.
