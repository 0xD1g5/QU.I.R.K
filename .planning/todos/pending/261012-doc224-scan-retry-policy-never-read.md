---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Timeout & Retry Policy)
priority: medium
area: quirk/config.py (RetryCfg), every scanner
status: pending
resolves_phase: null
owner: "999.136"
---

# scan.retry (retry_count, backoff_base_seconds, backoff_max_seconds) is not read by any scanner

`RetryCfg` and the dashboard's retry overlay (`retry_count` 0-10, backoff bounds) accept and validate values, but
`grep -rn "retry_count\|backoff_base_seconds\|backoff_max_seconds" quirk run_scan.py --include='*.py'` finds only
`quirk/config.py` (the dataclass) and the dashboard schema/job-overlay code. No scanner retries a failed probe, so an
operator who sets `retry_count: 3` (or sets it in the dashboard) gets no behaviour change. `docs/timeout-retry-audit.md`
says "Operators ... can raise `cfg.scan.retry.retry_count` globally; exponential backoff ... is bounded by"
`backoff_base_seconds`/`backoff_max_seconds`; `docs/configuration.md` now says nothing reads these keys yet.

- [ ] Decide: implement a shared retry helper and wire it into the TLS/SSH/fingerprint/connector probes, or
      deprecate the keys and remove them from the dashboard form.
- [ ] If implemented, add a test that a failing probe is retried `retry_count` times with bounded backoff.
- [ ] Then remove the "not yet read" notes from `docs/configuration.md` and fix `docs/timeout-retry-audit.md`.

## Feasibility & Effort

**CONFIRMED** by the negative grep above (re-run it before starting). Effort **L** if implemented across all scanners
(a retry wrapper plus per-scanner idempotency review), **S** if the keys are deprecated instead. Unknown: which probes
are safe to repeat (OT/ICS probes must never retry; see `modbus_scanner.py` / `bacnet_scanner.py` one-strike aborts).
A short spike listing the call sites is worth doing first.
