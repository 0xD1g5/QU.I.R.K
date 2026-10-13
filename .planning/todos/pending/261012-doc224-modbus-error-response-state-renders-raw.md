---
type: todo
created: 2026-10-12
source: Phase 224 gap closure A (docs/report-interpretation.md section 10.6, Modbus / BACnet columns)
priority: low
area: quirk/scanner/modbus_scanner.py, quirk/reports/html_renderer.py, quirk/reports/docx_renderer.py, src/dashboard/src/pages/hardware-badge-labels.ts
status: pending
resolves_phase: null
---

# A Modbus device that answers with an error response renders as the raw string `aborted_error_response`

`quirk/scanner/modbus_scanner.py:108-110` sets `modbus_probe_state = "aborted_error_response"` when the device returns
`None` or an error response to the read-device-information request. The label maps know only
`no_response`, `no_match` and `aborted_anomalous_response`:

- `quirk/reports/html_renderer.py:242-247` (`_PROBE_STATE_LABEL_MAP`) and `_probe_state_label` (line 256-267) fall back to
  `str(raw)`;
- `quirk/reports/docx_renderer.py:200-228` does the same;
- `src/dashboard/src/pages/hardware-badge-labels.ts:14-33` (`probeStateLabel`) returns `rawState` in its default branch,
  so the dashboard shows an unstyled `aborted_error_response` badge.

The guide (section 10.6) says a Modbus anomaly renders as a red "Probe aborted" badge and the abort caveat appears. For
the error-response case none of that happens: the column shows the raw state name, no red badge, and the
`aborted_anomalous_response`-only caveat check (`html_renderer.py:409`, `docx_renderer.py:855`) does not fire.

- [ ] Decide whether `aborted_error_response` is a second "aborted" state (map it to "Probe aborted", red, and include
      it in the caveat condition) or a "No match" variant.
- [ ] Add it to all three label maps and the dashboard style table, and to the badge-variant coverage test.

## Feasibility & Effort

**CONFIRMED** by reading the four files above (no mapping for the string exists anywhere under `quirk/` or
`src/dashboard/src/`; `grep -rn aborted_error_response` finds only `modbus_scanner.py:109`). Effort **S**.
Unknown: the intended semantics of an error response from a device that did answer. **Spike**: not needed.
