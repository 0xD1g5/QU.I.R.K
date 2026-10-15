---
type: todo
created: 2026-10-13
source: Phase 224 FD-README (front-door exhaustive pass, ledger rows DCL-README-0210, DCL-README-0219)
priority: high
area: quirk/dashboard/api/routes/scan.py (findings_for_endpoint), quirk/engine/findings_evaluator.py
status: pending
resolves_phase: 228
---

# A certificate expiring within 30 days is HIGH on the dashboard and MEDIUM in the report

The two pipelines rate the same near-expiry certificate differently, so a plain TLS scan gives a different headline
score on each surface:

- Dashboard: `quirk/dashboard/api/routes/scan.py:211` `elif days_to_expiry < 30:` emits
  `severity="HIGH"` (`:216`), title `Certificate expiring in {N} day(s)`.
- Report / CLI: `quirk/engine/findings_evaluator.py:610` `elif na < now_naive + timedelta(days=30):` emits
  `severity="MEDIUM"` (`:612`), title `TLS certificate expiring within 30 days`.

Because v3 scoring caps the number by the open HIGH count, the difference moves the score, not only the list.

Observed end to end (isolated HOME, QUIRK_* unset; `quirk init` starter config, two loopback TLS listeners sharing
one self-signed RSA-2048 certificate that expires in 30 days; `quirk --config config.yaml`; then `quirk serve` from
the same directory). Probe scripts: `work/probes/fd-README-serve-findings-probe.sh` in the phase 224 directory.

- Report (`findings-*.json`, `executive-summary-*.md`): 2 HIGH (self-signed), 2 MEDIUM (expiring), cap
  "2 open HIGH findings — score limited to 49 (computed 71)".
- Dashboard (`GET /api/scans`, `/api/scan/latest`): 4 HIGH (self-signed + "Certificate expiring in 29 day(s)" per
  endpoint), cap "4 open HIGH findings — score limited to 38 (computed 71)".

`docs/operators-guide.md` §3.1 lists the known causes of a dashboard/report score difference and says "Any other
divergence is a defect to file". This one is not in that list. The README now names it (DCL-README-0210).

- [ ] Pick one severity for a certificate that expires within 30 days and use it on both paths (and align the titles,
      which `quirk/compliance/__init__.py` FINGERPRINT_TITLE_ALIASES already has to bridge).
- [ ] Extend `tests/test_cross_surface_parity.py` with a near-expiry TLS row so XSURF-04 covers it.
- [ ] Then drop the clause from README.md "What's New" and, if listed there by then, from operators-guide.md §3.1.

## Feasibility & Effort

- **CONFIRMED.** `quirk/dashboard/api/routes/scan.py:211-216` (HIGH) vs `quirk/engine/findings_evaluator.py:610-615`
  (MEDIUM), reproduced by the live probe above (49 vs 38 for the same scan).
- **Effort S** for the code change (one constant on one side); **M** with the parity-test extension and a check of
  `tests/test_score_lift_cross_surface_numbers.py` and any test that pins either title or severity.
- Unknown: which severity is intended. The report-interpretation table rates "TLS certificate expired" CRITICAL; there
  is no documented decision for the expiring case. Product call, no spike needed.
