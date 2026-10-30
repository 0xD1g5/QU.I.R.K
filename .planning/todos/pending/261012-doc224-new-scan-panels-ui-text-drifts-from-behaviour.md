---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-OPS-A-* (operators-guide.md sections 3.0-3.1.5)
priority: low
area: src/dashboard/src/components/EffectiveConfigPanel.tsx, src/dashboard/src/components/AdvancedPanel.tsx, quirk/dashboard/api/connector_availability.py
status: pending
resolves_phase: null
owner: "999.137"
---

# New Scan panels: three UI strings say something the code does not do

Found while checking the operators guide's New Scan sections against the dashboard source. The guide now states the real
behaviour; these are the product-side texts that still disagree with it.

- [ ] **Effective config "Raw YAML" tab renders JSON.** `EffectiveConfigPanel.tsx` renders
      `JSON.stringify(data.raw, null, 2)` under a tab labelled `Raw YAML`. JSON is valid YAML, so the text can be pasted
      into a config file, but the label promises YAML formatting. Rename the tab or serialise with a YAML dumper.
- [ ] **TLS-Designated Ports helper text overstates the effect.** `AdvancedPanel.tsx` says "Ports to treat as TLS even when
      plaintext is detected — overrides the plaintext-on-TLS-port classifier." In `quirk/engine/findings_evaluator.py`
      (`_postprocess_findings`) a plaintext HTTP service on a listed port is relabelled "HTTP on TLS-designated port" and
      raised to HIGH; nothing is treated as TLS. Reword to "Plaintext HTTP found on these ports is reported as
      'HTTP on TLS-designated port' (HIGH)".
- [ ] **Connector availability returns an empty `install_hint` for connectors that an extra would fix.**
      `GET /api/connectors/availability` reports `enable_gcp` unavailable (`GCP_AVAILABLE is False`) with
      `install_hint: ""`, because `CONNECTOR_AVAILABILITY_MAP` gives GCP no `hint_extra`; the panel therefore shows a reason
      but no remedy. `enable_k8s` and `enable_vault` have the same shape. Map them to the `cloud` extra's hint.

## Feasibility & Effort

**CONFIRMED** for all three: `grep -n "JSON.stringify(data.raw" src/dashboard/src/components/EffectiveConfigPanel.tsx`;
`grep -n "TLS-Designated" -A4 src/dashboard/src/components/AdvancedPanel.tsx` against `findings_evaluator.py:420-435`; and a live
`curl http://127.0.0.1:<port>/api/connectors/availability` on an install without google-api-python-client showing
`"flag":"enable_gcp"` with `"install_hint":""`. Effort **S** for the two wording fixes (one string each, plus the vitest
snapshot or text assertion that pins them) and **S** for the hint mapping (three map entries plus
`tests/test_connector_availability_mapping.py`). No unknowns; no spike needed. The install-hint wording itself is covered by
`261012-doc224-install-hints-name-wrong-pypi-package.md`; fix that first so the new hints do not repeat the wrong package name.
