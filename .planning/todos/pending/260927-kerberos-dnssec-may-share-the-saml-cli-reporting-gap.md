# Kerberos and DNSSEC may share the SAML "CLI scores it but never reports it" gap

**Filed:** 2026-09-27 (Phase 210 planning — RESEARCH.md Open Question 2, dispositioned not fixed)
**Priority:** P2 — **CONFIRMED 2026-10-13** (Phase 224 GC2-LAB, re-checked in 224-17; see "Confirmation" below). Cost it.
**Source:** `.planning/phases/210-cross-surface-score-parity/210-RESEARCH.md` §Open Questions (RESOLVED) Q2

## The suspicion

XSURF-02's bug report names SAML only: `grep SAML` over a fresh `findings-*.json` returns nothing
while the same run's `intelligence-*.json` carries a non-zero `identity_saml_weak_signing_ratio`.
The root cause Phase 210 fixes is structural, not SAML-specific — identity finding synthesis lived
only inside `quirk/dashboard/api/routes/scan.py`, so the CLI report pipeline could not reach it,
while `quirk/intelligence/evidence.py` counted the same weakness independently off raw
`CryptoEndpoint` rows.

`KERBEROS` and `DNSSEC` are sibling `if`/`elif` branches in the **same** dashboard-route function and
have **the same** independent counters in `evidence.py`
(`identity_weak_etype_count`, `dnssec_weak_algo_count`, around `evidence.py:229-250`). If the code
shape is the same, the defect is the same: the CLI scores those weaknesses and never reports them.

Phase 210 deliberately extracted the three SAML sub-branches only (CONTEXT D-08), because absorbing
Kerberos/DNSSEC would cross that phase's own `Deferred Ideas: any new detection capability` boundary.

## Confirm it before fixing it — the check is cheap

This is a suspicion derived from code shape, not a reproduced defect. Do not cost a fix until a live
run confirms it. Bring up a lab profile that exercises Kerberos (the `multihost` profile has a
Kerberos KDC beside `mh-saml-idp` — see `quantum-chaos-enterprise-lab/docker-compose.yml:2059`) and
DNSSEC, then run the XSURF-02 comparison in both directions:

```bash
grep -c KERBEROS quirk-output/findings-*.json
grep -o '"identity_weak_etype_count": *[0-9]*' quirk-output/intelligence-*.json
grep -c DNSSEC quirk-output/findings-*.json
grep -o '"dnssec_weak_algo_count": *[0-9]*' quirk-output/intelligence-*.json
```

A non-zero count on the `intelligence-*.json` side with zero on the `findings-*.json` side confirms
it. **A zero on BOTH sides confirms nothing** — it may just mean the lab profile published no weak
Kerberos etype or weak DNSSEC algorithm, so verify the lab actually carries one before reading a
double zero as "no bug".

## Confirmation (2026-10-13, Phase 224)

Confirmed from source plus an in-process run; no live lab was needed, because the gap is in the
evaluator wiring, not in detection.

- `run_scan.py:4077-4104` (the CLI "Findings + persistence + reports" block) builds `findings` from
  `evaluate_endpoints`, `evaluate_email_endpoints`, `evaluate_broker_endpoints`,
  `evaluate_codesign_endpoints`, and `evaluate_identity_endpoints(saml_endpoints)` only. There is no
  Kerberos or DNSSEC evaluator call.
- In-process (224-17, scratch HOME/XDG, repo `config.yaml` read-only), four synthetic endpoint rows
  (DNSSEC `RSASHA1`, `NONE`, `NSEC`; KERBEROS `etype:23:rc4-hmac:HIGH`):
  `evaluate_endpoints(cfg, rows)` -> 0 findings; `evaluate_identity_endpoints(rows)` -> 0;
  `quirk/dashboard/api/routes/scan.py::_derive_identity_findings(rows)` -> 4
  (`DNSSEC: RSASHA1` CRITICAL, `DNSSEC: NONE` HIGH, `DNSSEC: NSEC` MEDIUM,
  `Kerberos weak etype: rc4-hmac` HIGH).
- The scoring side still counts them: `quirk/intelligence/evidence.py:286`
  (`identity_weak_etype_count += 1`) and `:309` (`dnssec_weak_algo_count += 1`).

So the CLI scores Kerberos/DNSSEC weaknesses and never lists them in `findings-*.json`, while the
dashboard lists them (Identity page and the merged findings list from `/api/scan/latest`). The docs
now say so: `docs/chaos-lab.md` §3 "Reading the finding columns" and the chaos-lab oracle
`quantum-chaos-enterprise-lab/expected_results_v4.md` (dnssec and kerberos sections, corrected in
224-17).

## Feasibility & Effort

- **Feasibility: CONFIRMED defect (2026-10-13); fix LIKELY.** The extraction mechanism Phase 210 builds
  (`quirk/engine/findings_evaluator.py::evaluate_identity_endpoints()` plus the dict→pydantic adapter
  at the route call site) is reusable as-is; two more branches move through the same door. CONFIRMED
  that the door exists once Phase 210 lands; LIKELY that the two branches need nothing new.
- **Effort: S**, contingent on the confirmation above. Two branch extractions into an existing
  function, two evidence-counter checks, two tests, no new dependency, no new detection logic.
- **Unknowns:** whether Kerberos/DNSSEC also double-count per row the way the SAML dual-`use` case
  did (the dedupe key `(host, port, cert serial)` is certificate-shaped and may not apply to an
  etype or a zone algorithm — a different dedupe key, or none, may be correct).
- **Spike needed?** No. The confirmation commands above are the whole investigation.

## Do not

- Do not fold this into Phase 210 retroactively. Its scope boundary was a recorded decision (D-08),
  and the phase's verification is written against SAML.
- Do not assume the SAML dedupe key transfers. A Kerberos weak etype is not a certificate.
