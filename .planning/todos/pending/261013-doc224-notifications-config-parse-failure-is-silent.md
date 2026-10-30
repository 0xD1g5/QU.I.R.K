---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork E); ledger row DCL-OPS-B-0352 (docs/operators-guide.md §9.12 "Failure isolation")
priority: low
area: quirk/notify/config.py (load_notifications_config)
status: pending
resolves_phase: null
owner: "999.135"
---

# A malformed notification config disables lifecycle (and scan) notifications with no log line

`load_notifications_config()` wraps the YAML read in `except Exception: return None`
(`quirk/notify/config.py:191-193`, comment "Binary / malformed / non-YAML files (Pitfall 1) return None silently").
The lifecycle dispatcher treats `None` as "notifications off" and returns before it writes any
`integration_deliveries` row (`quirk/notify/dispatcher.py:342-344`). An operator who enabled
`notify_on_hardware_lifecycle` and has a webhook block, but has an unrelated YAML syntax error anywhere in the file,
gets no notification, no audit row and no warning.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-E-lifecycle-norows-probe.py`, isolated
HOME, TEST-NET webhook): valid config -> 1 `integration_deliveries` row (`webhook`, `failed`); the same config plus
`scan: {ports_tls: [443` appended -> 0 rows, nothing logged.

The operators-guide now lists "the file failed to parse" as a third cause of "no rows at all".

- [ ] Log a WARNING (path + parse error class, no content) when `QUIRK_CONFIG_PATH` names a file that exists but
      fails to parse. Keep the silent `None` for the documented `.db`-file case (Pitfall 1) if that is still wanted.
- [ ] Test: malformed YAML at `QUIRK_CONFIG_PATH` produces the warning and still never raises.

## Feasibility & Effort

- **CONFIRMED** the swallow at `quirk/notify/config.py:191-193` and the early return at
  `quirk/notify/dispatcher.py:343-344`, by the probe above.
- **CONFIRMED** `quirk/notify/dispatcher.py:187` (scan notifications) calls the same loader, so the fix covers both
  dispatchers.
- **LIKELY** effort **S**: one `logger.warning` in the except branch plus a test; `safe_str` is already used in
  `quirk/notify/dispatcher.py:39` for the same purpose. **UNKNOWN**: whether Pitfall 1 (a `.db` path passed as the
  config) should stay silent; a `.db` suffix check would keep it. No spike needed.
