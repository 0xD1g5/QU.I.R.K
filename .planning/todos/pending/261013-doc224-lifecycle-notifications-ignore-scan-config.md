---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork B3); docs/operators-guide.md hardware lifecycle notifications ("Enable it with the key in ... notifications:" claim, narrowed)
priority: medium
area: quirk/notify/dispatcher.py (dispatch_hardware_lifecycle_notifications), quirk/notify/config.py (load_notifications_config)
status: pending
resolves_phase: null
---

# Hardware lifecycle notifications ignore the scan's `--config`; only `QUIRK_CONFIG_PATH` enables them

`dispatch_hardware_lifecycle_notifications` (`quirk/notify/dispatcher.py:316`) gates on
`load_notifications_config()` called with no path (`dispatcher.py:342`). That resolves only `QUIRK_CONFIG_PATH`
(`quirk/notify/config.py:181`) and returns `None` (disabled) when it is unset. The scan that triggers the dispatch
(through `quirk/scanner/hardware_drift.py:489`) never passes its own `--config` path. So an operator who sets
`notifications.notify_on_hardware_lifecycle: true` in the config they pass with `--config` gets no notification and
no delivery row. Fork B3's probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-b3-lifecycle-notify-config-probe.py`)
showed 0 delivery rows with the variable unset and 1 row with it set to the same file.

The `QUIRK_CONFIG_PATH` rule was written for the scheduler (`dispatcher.py:186` "never from scheduler DB path"), where
it makes sense. For an in-scan dispatch the scan's own config is the obvious source. The operators-guide now documents
the env-var requirement.

- [ ] Pass the scan's config path into the lifecycle dispatch (keep `QUIRK_CONFIG_PATH` as the fallback).
- [ ] Test: a scan with `--config` holding the notifications block writes a delivery row with the env var unset.
- [ ] Relax the operators-guide sentence once fixed.

## Feasibility & Effort

- **CONFIRMED** by reading `quirk/notify/dispatcher.py:342`, `quirk/notify/config.py:168-190` and the B3 probe.
- **LIKELY** effort **S**: thread one path argument from the hardware-persistence caller to `load_notifications_config(path)`,
  which already accepts an explicit path (`config.py:171`). **UNKNOWN**: whether the scheduler should keep its
  env-var-only rule. No spike needed.
