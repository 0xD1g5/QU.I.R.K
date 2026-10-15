---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §10.3 SNMP)
priority: medium
area: quirk/scanner/hardware_scanner.py (fingerprint Step 3)
status: pending
resolves_phase: null
owner: "999.130"
---

# Hardware fingerprint SNMP probe always uses community "public", ignoring snmp_community / QUIRK_SNMP_COMMUNITY

The fingerprint Step 3 v2c probe hardcodes `community="public"` (`quirk/scanner/hardware_scanner.py:524`, `:530`,
`:532`). The bulk SNMP sweep resolves `connectors.snmp_community` / `QUIRK_SNMP_COMMUNITY` (`run_scan.py:2896-2906`)
and so does the bridge walk in the same module (`hardware_scanner.py:273-285`). An estate with a non-default
community gets no SNMP identification from fingerprinting. Related but distinct:
`261013-doc224-fingerprint-snmp-probe-ignores-enable-snmp` (that todo is about the probe running at all).

When fixed, update docs/report-interpretation.md §10.3 ("hardware fingerprinting sends an SNMP probe ... community public").

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `hardware_scanner.py:524/530/532` vs `:273-285` and `run_scan.py:2896-2906`.
- Fix: reuse the bridge-walk resolution; never log the community (T-140-03).
