---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Scan Block hardware retention)
priority: low
area: quirk/cli/console_cmd.py (_ingest_envelope)
status: pending
resolves_phase: null
---

# Sensor ingestion purges hardware history with the 180-day default

`quirk/cli/console_cmd.py:678-679` calls `persist_and_reconcile(db, hw_rows, None, ...)` with `cfg=None`,
so sensor-ingested hardware rows (a push, or `quirk console import-results`) are purged with the
180-day default, never `scan.hardware_history_retention_days`. The code comment at `:658-669` records
this as a documented limitation. docs/configuration.md now says so.

- [ ] Thread a fail-closed config load into ingestion (mirror
      `quirk/dashboard/api/routes/sensor.py:129 _load_auto_merge_config`), or keep it documented.

## Feasibility & Effort

- **Feasibility: LIKELY.** The loader pattern exists (`sensor.py:129`). The call site is one argument.
- **Effort: S.**
- **Unknowns:** which config file the console process should trust (`QUIRK_CONFIG_PATH`).
- **Spike:** no.
