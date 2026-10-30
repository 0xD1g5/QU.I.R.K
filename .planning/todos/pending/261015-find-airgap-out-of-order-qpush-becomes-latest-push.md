---
type: todo
created: 2026-10-15
source: Phase 229 (Finding & State Correctness) D-13 / Pitfall 8
priority: low
area: quirk/cli/console_cmd.py (_ingest_envelope, import-results)
status: pending
resolves_phase: null
owner: "999.134"
---

# Importing an older .qpush after a newer one makes it the sensor's latest push

**Owner:** 999.134 (Trends, history, sensors and merge)

`SensorPush.received_at` is ingest time (`quirk/cli/console_cmd.py` around lines 521 and 537) and `import-results` skips the replay window, so importing an older air-gap `.qpush` after a newer one makes the older file the sensor latest push under the D-13 rule that merge uses.

- [ ] Order the latest push by the envelope capture time, or reject out-of-order imports.

## Feasibility & Effort

- **LIKELY**. Effort **S**. Unknown: whether envelopes carry a trustworthy capture time. Spike: no.
