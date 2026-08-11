# Phase 145: Liveness Pre-Pass - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-10
**Phase:** 145-liveness-pre-pass
**Areas discussed:** Privilege-fallback disclosure, Liveness-probe port scope, Non-responsive host accounting (interim, pre-Phase-146), Non-root verification approach

---

## Privilege-fallback disclosure

| Option | Description | Selected |
|--------|-------------|----------|
| Log + advisory row | Mirror `_emit_missing_extra_advisory` (run_scan.py:167) — logger message AND a CryptoEndpoint advisory row | ✓ |
| Log only | logger.warning/info the fallback and move on | |
| Hard-fail the batch | Treat the fallback as an error and abort that batch | |

**User's choice:** Log + advisory row (recommended)
**Notes:** Matches how QUIRK already surfaces degraded-mode conditions elsewhere.

| Option | Description | Selected |
|--------|-------------|----------|
| Once per scan | Check `os.geteuid()==0` once before the batch loop, reuse for every batch | ✓ |
| Per batch, from nmap's own output | Parse each batch's nmap stderr/XML for fallback evidence independently | |

**User's choice:** Once per scan (recommended)
**Notes:** Root/non-root is a process-level fact that doesn't change mid-run.

---

## Liveness-probe port scope

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse the batch's full sweep port list | Same `ports_for_nmap`/`port_spec_override` the batch's own `-sT` sweep uses | ✓ |
| Small fixed fast-probe subset (e.g. 80,443,22) | Cheaper/faster, but risks false negatives on sweep-scoped ports outside the subset | |

**User's choice:** Reuse the batch's full sweep port list (recommended)
**Notes:** Optimization cost now scales with how targeted the scan already is; avoids wrongly skipping hosts only reachable on non-standard sweep ports.

---

## Non-responsive host accounting (interim, pre-Phase-146)

| Option | Description | Selected |
|--------|-------------|----------|
| CryptoEndpoint error rows | Mirror the Phase 144 batch-failure precedent (`error_endpoints.append(...)`, run_scan.py:1318-1324) | ✓ |
| Lightweight run_stats counter | Thread a simple integer count through run_stats, similar to `_tls_pf`/`_ssh_pf` flags | |
| Log only, no structured accounting yet | logger.info the skip and count per-batch, nothing persisted/queryable | |

**User's choice:** CryptoEndpoint error rows (recommended)
**Notes:** Gives Phase 146 a ready-made queryable source for DISC-07's undetermined-host disclosure.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, distinct category | e.g. `scan_error_category="liveness_skip"` vs. Phase 144's `"exception"` | ✓ |
| Same category as batch failures | Reuse `"exception"` for both | |

**User's choice:** Yes, distinct category (recommended)
**Notes:** These are semantically different outcomes — individual host non-response vs. whole-batch subprocess failure.

---

## Non-root verification approach

| Option | Description | Selected |
|--------|-------------|----------|
| Chaos lab, as a documented human-UAT step | Non-root chaos lab scenario, gated as human-UAT, consistent with existing environment-dependent checks (e.g. UAT-118-01) | ✓ |
| CI runner (non-root by default) | GitHub Actions integration test job asserting fallback-detection fires | |

**User's choice:** Chaos lab, as a documented human-UAT step (recommended)
**Notes:** Automated verification covers everything up to the final non-root confirmation, which the user signs off on manually.

---

## Claude's Discretion

None — every gray area reached an explicit user decision.

## Deferred Ideas

- CI-runner-based automated non-root verification job — set aside in favor of the chaos-lab human-UAT approach; could be revisited if the manual pass proves insufficient or too slow to repeat regularly.
- Per-batch privilege re-derivation from nmap's own output — rejected in favor of a once-per-scan `os.geteuid()` check.
