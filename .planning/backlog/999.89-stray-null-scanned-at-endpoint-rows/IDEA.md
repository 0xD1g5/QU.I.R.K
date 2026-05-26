# Backlog 999.89 — Stray `scanned_at=None` endpoint rows in console DB

**Type:** investigate
**Source:** v5.4 live human-UAT (UAT-112-03), 2026-05-26
**Candidate for:** v5.5

## Problem

After `lab.sh distributed e2e`, the console `crypto_endpoints` table contains stray rows
with `scanned_at=None` for hosts `email_scanner` and `broker_scanner` at port 0
(segment-a/sensor-a and segment-b/sensor-b). Observed alongside the legitimate
`crypto.internal:443` rows. Likely placeholder rows emitted by the sensor scan config
(email/broker scanners that found nothing) rather than real endpoints.

These are excluded from `/api/scan/latest` (which anchors on `MAX(scanned_at)`), so they
don't corrupt the dashboard today — but they are noise in the DB and could surface in
other queries or counts.

## Investigate

Determine where the `scanned_at=None` / port-0 placeholder rows originate (sensor scan
config? a scanner that writes a row even on no-result?). Decide whether to suppress them
at write time or filter them at read time. Add a test pinning the expected row set after
a clean e2e.

## References

- `.planning/v5.4-deferred-uat.md` (Test 7 DB inspection)
- `quantum-chaos-enterprise-lab/sensor-config.yaml`
