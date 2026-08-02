---
gsd_state_version: 1.0
milestone: v5.10
milestone_name: Hardware Lifecycle Depth
status: executing
stopped_at: Completed 142-00-PLAN.md
last_updated: "2026-08-02T13:16:11.480Z"
last_activity: 2026-08-02
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 29
  completed_plans: 23
  percent: 60
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-30)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours — now extending agentless hardware PQC fingerprinting (SSH/HTTP/SNMP) with SNMPv3, SNMP-confirmed bridge mitigation, OT/ICS fingerprinting, firmware CVE correlation, and a small dashboard/security tail.

**Current focus:** Phase 142 — firmware-cve-correlation

## Current Position

Phase: 142 (firmware-cve-correlation) — EXECUTING
Plan: 2 of 7
Status: Ready to execute
Last activity: 2026-08-02

Progress: [████████░░] 79%

## v5.10 Phase Map

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 139 | SNMPv3 Auth+Priv Support | SNMPV3-01..04 | None (first) | Complete |
| 140 | SNMP-Confirmed Bridge Mitigation | BRIDGE-01..05 | Phase 139 | Not started |
| 141 | OT/ICS Fingerprinting (Modbus + BACnet) | OTICS-01..06 | None new (sequenced after 139) | Complete (BACnet-scoped; Modbus e2e deferred, see follow-up note) |
| 142 | Firmware CVE Correlation | CVE-01..04 | Phase 141 | Not started |
| 143 | Dashboard & Security Tail | TAIL-01..04 | None (independent) | Not started |

## v5.9 Final State

Shipped 2026-07-30, Phases 135–138 + 138.1/138.2, 10 plans, 16/16 requirements, tech_debt
disposition (deferred human-UAT only, no content gaps). Archive: `.planning/milestones/v5.9-ROADMAP.md`.

## Performance Metrics

**Velocity:**

- v5.9: 10 plans, 4 phases + 2 gap-closures (2026-06-18 → 2026-07-30)
- v5.8: 21 plans, 5 phases (2026-06-14 → 2026-06-18, 4 days)
- v5.7: 24 plans, 7 phases (2026-06-13 → 2026-06-14, 2 days)
- v5.6: 20 plans, 6 phases (2026-06-12)

## Accumulated Context

### Decisions

- Numbering continues at Phase 139 (v5.9 ended at 138 + gap-closures 138.1/138.2).
- Phase order is dependency-driven, not feature-list order: SNMPv3 (139) must precede bridge
  confirmation (140) because the confirmation probe needs authenticated SNMP transport to reach
  gateway forwarding/ARP tables. Bridge confirmation gets its own dedicated phase — not bundled
  with SNMPv3 — because of the false-assurance risk in an over-eager `upstream_mitigated`
  promotion. OT/ICS (141) is independent but sequenced after 139 to mirror dispatcher shape.
  CVE correlation (142) is sequenced after OT/ICS so it inherits new vendor/model values. The
  dashboard/security tail (143) is fully independent, sequenced last per its "small tail" framing.

- Package layout: no `quirk/hardware/` package exists or should be introduced — all new modules
  (`modbus_scanner.py`, `bacnet_scanner.py`, `otics_meta.py`, `hw_cve.py`) follow the existing flat
  `quirk/scanner/` (and `quirk/cbom/`) convention.

- Repeats the v5.8 "B-01" lesson: every phase adding `HardwareDevice` columns must update all
  three projection sites (`reports/writer.py`, `merge/scan.py`,
  `dashboard/api/routes/scan.py`) in the same phase (OTICS-06 makes this explicit for Phase 141;
  applies equally to 139/140/142's derived fields).

- TAIL-02 (trusted-targets allowlist) and TAIL-03 (Windows code-signing CI) each require a
  dedicated `/gsd-secure-phase` review given the repo's 5-strikes SSRF history and the Phase 120
  PEM-in-history incident.

- [Phase 139]: snmp_v3_credentials lives under connectors: in YAML (ConnectorsCfg field), matching 139-00 RED test shape, unlike top-level broker_credentials
- [Phase 139]: D-02 validation raises plain ValueError (no dedicated ConfigError class) — matches 139-00 RED test and existing config-validation convention
- [Phase 139]: SNMP_MODE_V3_NO_AUTH_PRIV is canonical (matches 139-00 RED test); SNMP_MODE_V3_NOAUTH kept as an alias so both spec artifacts pass
- [Phase 139]: _classify_v3_failure only treats decryptionError as protocol-mismatch when it co-occurs with security-level text, avoiding over-classifying generic decryption failures
- [Phase 139]: Wired the SNMPv3 v3->v2c->none fallback ladder into both independent SNMP entry points (hardware_scanner.py Step 3 and run_scan.py --enable-snmp pass), each honestly labeling v3-failed-fell-back (D-03) vs v3-protocol-mismatch (D-02) vs plain v2c/none, writing auth/priv protocol columns only on v3 success
- [Phase ?]: SNMP badge label map duplicated verbatim in html_renderer.py and docx_renderer.py rather than extracted to a shared module, matching existing per-renderer helper precedent
- [Phase 139]: SNMP badge column (139-06) reuses existing Badge primitive + native title= tooltip; snmpLabel() raw-fallback mirrors 139-05 report renderer for cross-surface parity
- [Phase ?]: Phase 139-07: hwcompat-snmp lab USM user quirkv3user (SHA/AES) added directly via createUser+rouser in snmpd.conf; lab passphrases are non-secret test values (accepted risk, same posture as rocommunity public)
- [Phase 139]: SNMP_V3_TIMEOUT_MULTIPLIER kept at 2 — empirically confirmed against live hwcompat-snmp target (~0.05s round-trip vs 6s budget), no spurious timeouts
- [Phase 139]: hwcompat-snmp exposes both port 161 (for run_scan.py live scans) and 20223 (existing direct snmpget/snmpwalk docs) — additive, non-breaking
- [Phase 140]: bridge_evidence_json/bridge_confirmed_at reuse the exact Phase 139 SNMPv3-column precedent (module-level tuple + _ADDITIVE_MIGRATIONS append) — no new migration machinery
- [Phase 140]: [Phase 140]: _confirm_upstream_mitigation evidence check operates at /24 subnet-group level (not device-identity) — symmetric promotion matching _detect_crypto_bridges' existing group-assignment shape
- [Phase 140]: 140-03: HTML caveat kept inside existing pre-collapsed <details> block per plan text (pre-existing PDF-visibility scope, not fixed this plan); badge colors sourced from UI-SPEC hsl() values (amber F59E0B / blue 60A5FA)
- [Phase 140]: [Phase 140] 140-04: bridge_status dashboard lookup keyed by host, matching _detect_crypto_bridges'/_confirm_upstream_mitigation's own host-based subnet grouping
- [Phase 140]: No lab compose/port/service/seed change was required for BRIDGE-01/04 empirical validation — Docker's bridge networking seeds the gateway ARP entry automatically, resolving Assumption A3. — Resolves 140-RESEARCH.md assumptions A2/A3 without new lab config
- [Phase 140]: Fixed a Rule 1 evidence-shape mismatch: sensor writer persisted (ip, mac) tuples while the console reader expected {target_ip, mac} dicts, silently blocking upstream_mitigated promotion from real sensor data. — Caught during Task 3 checkpoint prep; writer normalized to match the more broadly tested reader contract
- [Phase 141]: pip install must target .venv explicitly — default PATH pip/python3 resolve to a stray Python 3.9 user install that fails the project's requires-python >=3.10 gate
- [Phase 141]: pymodbus pinned <4 and bacpypes3 pinned <0.1; both in [hw] extras only, never [all]
- [Phase 141]: No modbus_port/bacnet_port or per-host allowlist config field — ports 502/47808 hardcoded in scanner modules per D-06/RESEARCH Pitfall 3
- [Phase 141]: pymodbus 3.14.0 moved mei_message under pymodbus.pdu — resolved with nested try/except import fallback covering both layouts within the >=3.8.0,<4 pin
- [Phase 141]: bacpypes3 who_is(address=, timeout=) + read_property(source, objid, prop) signatures confirmed live against installed 0.0.106 source before implementation
- [Phase 141]: BACnet safety docstring prose rewritten to avoid literal write_property/broadcast substrings so documentary text doesn't trip its own acceptance-criteria grep
- [Phase 141]: OTICS-01/02/05: Modbus Step 4 gates on enable_modbus+port==502 (D-04); BACnet Step 5 gates on enable_bacnet only (Who-Is is its own gate); neither nested under vendor==Unknown (D-01); first-match-wins Modbus-before-BACnet headline (D-03)
- [Phase ?]: [Phase 141]: Test harness pattern for embedded (non-extracted) projection dict code — spy-wrap the real downstream function (_confirm_upstream_mitigation) via monkeypatch to capture the dict without perturbing behavior, instead of mocking/extracting
- [Phase 141]: 141-06 Tasks 1-2 complete (Modbus blue/BACnet purple badge columns on /hardware + matching HTML/DOCX report columns + D-13 abort caveat); Task 3 human-verify checkpoint is open — dashboard/report visual colors and abort-state distinctness await explicit user approval before 141-06 is marked done
- [Phase 141]: 141-07 Tasks 1-2 complete — new `otics` chaos-lab compose profile (D-09 standalone, not folded into hwcompat) with two fragile simulators: otics-modbus (port 502/TCP, pymodbus-backed FC 43/14 Read Device Identification, Schneider Electric M221) and otics-bacnet (port 47808/UDP, bacpypes3-backed Who-Is/I-Am + ReadProperty, Johnson Controls FX16). Both simulators sit behind a custom asyncio "gatekeeper" (raw-socket admission layer only — protocol framing/encode/decode is real pymodbus/bacpypes3, never hand-rolled) enforcing D-10 fragility: single-in-flight-only (second concurrent connection/datagram reset/dropped) and malformed-header reset/drop. Locally verified (not via Docker) against real pymodbus/bacpypes3 clients: normal round trip returns correct vendor/model/firmware, concurrent connection gets reset, malformed frame gets reset/dropped. expected_results_otics.md oracle + README.md otics row + operators-guide.md §9.4 (D-07 risk warning) + report-interpretation.md §10.6 (five-state vocabulary + Probe aborted) + chaos-lab.md §3.23 all added and synced to Obsidian vault Digs. Task 3 (live Docker end-to-end validation) is a blocking-human-verify checkpoint — NOT executed by the agent per plan instructions.

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 140's evidence-sufficiency bar (what SNMP facts constitute "confirmed" vs "assumed") is
  not fully specified by research — flagged as a planning-time design decision to make explicit
  before implementation, not skip.

- Phase 141 OT-safety norms are MEDIUM confidence — do a web-search verification pass during
  `/gsd:plan-phase 141`, not skip it (fragile-device probing has real-world outage history).

- Phase 142 CVE/CPE version-matching guidance is MEDIUM confidence — verify current NVD API/CPE
  guidance and vendor firmware version-string normalization (Cisco/Juniper/etc.) during planning.

## Deferred Items

Carried forward from v5.9 close (2026-07-30):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 132: 132-VERIFICATION.md | human_needed — pre-existing, already shipped/tagged |
| verification_gap | Phase 135: 135-VERIFICATION.md | human_needed — README What's New visual render check |
| verification_gap | Phase 137: 137-VERIFICATION.md | human_needed — prose quality/live enroll walkthrough |
| human-UAT (118) | UAT-118-01 — live Windows-host install + Scheduled Task walkthrough | deferred — needs a real Windows host |
| human-UAT (114) | UAT-114-03 — operators-guide §8.9 auto-merge visual review | deferred — non-blocking |
| human-UAT (93/95/96) | getpass/live PDF, ldaps code-signing, fuzzing TTY gates | deferred — environment-gated |
| human-UAT (101–105) | Live Slack/email/webhook/syslog/Jira/ServiceNow delivery | deferred — needs live infra |
| horizon | Continuous hardware lifecycle monitoring | deferred — v5.11+, needs its own research pass |
| Phase 139 P00 | 12min | 3 tasks | 3 files |
| Phase 139 P01 | 15min | 2 tasks | 4 files |
| Phase 139 P02 | 25min | 2 tasks | 2 files |
| Phase 139 P04 | 12min | 3 tasks | 5 files |
| Phase 139 P03 | 20min | 2 tasks | 2 files |
| Phase 139 P06 | 15min | 3 tasks | 4 files |
| Phase 139 P07 | 20min | 2 tasks | 7 files |
| Phase 139 P08 | 45min | 2 tasks | 3 files |
| Phase 140 P00 | 6min | 2 tasks | 3 files |
| Phase 140 P02 | 20min | 3 tasks | 4 files |
| Phase 140 P03 | 25min | 3 tasks | 6 files |
| Phase 140 P04 | 18min | 3 tasks | 7 files |
| Phase 140 P05 | 10min | 3 tasks | 4 files |
| Phase 141 P01 | 12min | 2 tasks | 3 files |
| Phase 141 P02 | 12min | 2 tasks | 2 files |
| Phase 141 P03 | 18min | 2 tasks | 2 files |
| Phase 141 P04 | 25min | 3 tasks | 3 files |
| Phase 141 P05 | 20min | 2 tasks | 7 files |
| Phase 142 P00 | 25min | 3 tasks | 5 files |

## Session Continuity

Last session: 2026-08-02T13:16:11.475Z
Stopped at: Completed 142-00-PLAN.md

  1. 141-06-PLAN.md Task 3 — Modbus/BACnet badge colors + abort-state distinctness + report caveat (dashboard/report visual review)
  2. 141-07-PLAN.md Task 3 — otics chaos-lab profile live end-to-end validation (Docker + real network traffic against the fragile Modbus/BACnet simulators)

Resume files: .planning/phases/141-ot-ics-fingerprinting-modbus-bacnet/141-06-SUMMARY.md,
  .planning/phases/141-ot-ics-fingerprinting-modbus-bacnet/141-07-SUMMARY.md
