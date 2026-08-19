---
gsd_state_version: 1.0
milestone: v5.15
milestone_name: Lifecycle Tail Drain
status: planning
last_updated: "2026-08-19T20:52:44.379Z"
last_activity: 2026-08-19
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-19)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours — now with continuous hardware lifecycle monitoring (drift detection, EOL tracking, sensor-fleet coverage, lightweight check-in re-probes, and catalog-level vendor PQC trend tracking) layered on top of the v5.7–v5.10 agentless hardware PQC fingerprinting foundation.

**Current focus:** Planning next milestone (v5.14 shipped 2026-08-19 — run `/gsd:new-milestone`)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-08-19 — Milestone v5.15 started

## v5.14 Phase Map (planning)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 157 | Drift-Event Retention + Forecast Narrative Foundation | HWLC-16, HWLC-18 | None (first, fully independent) | Ready for verification (2026-08-16; 5/5 plans executed, HWLC-16/HWLC-18 satisfied — `/gsd:verify-phase 157` not yet run) |
| 158 | Sensor Fleet Drift Coverage | HWLC-15 | None new (independent of 157; extends Phase 107/109/154 plumbing) | Ready for verification (2026-08-17; 3/3 plans, HWLC-15 satisfied — `158-VERIFICATION.md` on disk, VALIDATION.md rows not yet reconciled) |
| 159 | Check-in Scan Mode | HWLC-13 | Phase 158 (reuses shared persist_and_reconcile() for drift writes) | Ready for verification (2026-08-17; 5/5 plans executed, HWLC-13 satisfied — docs + UAT Series 159 + Obsidian vault sync closed; `/gsd:verify-phase 159` not yet run) |
| 160 | Catalog-Level PQC Vendor Trend Tracking | HWLC-17 | Phase 158 (reuses persist_and_reconcile() call site; needs complete fleet population) | Ready for verification (2026-08-18; 3/3 plans executed, HWLC-17 satisfied — GET /api/hardware/vendor-trends live, docs + UAT Series 160 + Obsidian vault sync closed; `/gsd:verify-phase 160` not yet run) |

## v5.13 Phase Map (SHIPPED 2026-08-15)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 154 | Identity & Data-Model Foundation | HWLC-01, HWLC-02, HWLC-03 | None (first, blocks 155/156) | Ready to plan |
| 155 | Drift Detection + EOL Tracking | HWLC-04..09 | Phase 154 | Not started |
| 156 | Reporting & OT/ICS Safety | HWLC-10, HWLC-11, HWLC-12 | Phase 155 | Complete (2026-08-15; /gsd-secure-phase 156 SECURED 19/19 threats closed, 0 high-severity findings) |

## v5.12 Phase Map (SHIPPED 2026-08-14)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 148 | Release Pipeline Repair + Windows Asset Backfill | RELEASE-02, RELEASE-03, RELEASE-04 | None (first, demonstrable early win) | Complete (2026-08-11) |
| 149 | Test Suite Triage | SUITE-01 | None (independent, highest-variance item run early/alone) | Complete (2026-08-12) |
| 150 | Test Suite Green Baseline + CI Gate | SUITE-02, SUITE-03 | Phase 149 (scope depends on triage output) | Complete (2026-08-13; VERIFICATION passed 4/4 — green run 31723764281, red run 31725715958, both live-fire proven on real GitHub Actions) |
| 151 | Phase-Completion Artifact Gates | ARTIFACT-01, ARTIFACT-02, ARTIFACT-03, ARTIFACT-04 | None (independent) | Complete (2026-08-13; VERIFICATION passed 4/4 — scripts/verify_phase_gates.py + .githooks/pre-commit, now installed and live via `core.hooksPath` as of the v5.12 milestone audit) |
| 152 | Discovery Empirical Closure | DISC-09, DISC-10, DISC-11 | None (DISC-10 depends on DISC-09 within-phase) | Complete (2026-08-13; VERIFICATION 4/4 — segmented-network lab profile live-verified, Phase 144 nmap timing artifact DOES NOT REPRODUCE per 152-DISC09-FINDING.md, enable_nmap defaults True) |
| 153 | Release Tag Cut | RELEASE-01 | Phases 148, 150, 151 | Complete (2026-08-14; VERIFICATION 12/13 live-verified — v5.12.0 tagged, pushed, real release.yml green (event=push), Windows zip attached to GitHub Release, published on PyPI, tag-hygiene guard OK) |

## v5.11 Phase Map (SHIPPED 2026-08-11)

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 144 | Chunked Discovery Core | DISC-01, DISC-02 | None (first, anchor) | Complete (2026-08-10; VERIFICATION passed 6/6 with 1 user-accepted override — nmap timing-engine artifact on a mostly-silent loopback target list) |
| 145 | Liveness Pre-Pass | DISC-03 | Phase 144 | Complete (2026-08-10; VERIFICATION written retroactively at v5.11 audit closeout — passed 4/4, 0 overrides) |
| 146 | Progress, Scaling & Disclosure | DISC-04, DISC-05, DISC-06, DISC-07 | Phase 144 | Complete (2026-08-11; VERIFICATION passed 4/4; code review CR-01 undetermined-host miscount fixed before close) |
| 147 | Backlog Drain — Lifecycle & Ledger Tail | DRAIN-01, DRAIN-02, DRAIN-03, DRAIN-04 | None (independent) | Complete (2026-08-11; VERIFICATION passed 4/4; VALIDATION reconciled to nyquist_compliant at audit closeout) |

## v5.10 Phase Map

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 139 | SNMPv3 Auth+Priv Support | SNMPV3-01..04 | None (first) | Complete |
| 140 | SNMP-Confirmed Bridge Mitigation | BRIDGE-01..05 | Phase 139 | Complete |
| 141 | OT/ICS Fingerprinting (Modbus + BACnet) | OTICS-01..06 | None new (sequenced after 139) | Complete (both Modbus and BACnet validated end-to-end, live-verified 2026-08-03) |
| 142 | Firmware CVE Correlation | CVE-01..04 | Phase 141 | Complete |
| 143 | Dashboard & Security Tail | TAIL-01..04 | None (independent) | Complete (human_needed 12/13 — 2 items approved-to-continue, see Deferred Items) |

## v5.9 Final State

Shipped 2026-07-30, Phases 135–138 + 138.1/138.2, 10 plans, 16/16 requirements, tech_debt
disposition (deferred human-UAT only, no content gaps). Archive: `.planning/milestones/v5.9-ROADMAP.md`.

## Performance Metrics

**Velocity:**

- v5.9: 10 plans, 4 phases + 2 gap-closures (2026-06-18 → 2026-07-30)
- v5.8: 21 plans, 5 phases (2026-06-14 → 2026-06-18, 4 days)
- v5.7: 24 plans, 7 phases (2026-06-13 → 2026-06-14, 2 days)
- v5.6: 20 plans, 6 phases (2026-06-12)

**Per-plan execution metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
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
| Phase 142 P01 | 20min | 2 tasks | 1 files |
| Phase 142 P02 | ~10min | 2 tasks | 3 files |
| Phase 142 P03 | ~20min | 3 tasks | 4 files |
| Phase 142 P04 | 20min | 2 tasks | 4 files |
| Phase 142 P05 | 15min | 3 tasks | 5 files |
| Phase 144 P01 | 12min | 2 tasks | 4 files |
| Phase 144 P02 | 35min | 2 tasks | 3 files |
| Phase 145 P01 | 8min | 2 tasks | 4 files |
| Phase 145 P02 | 20min | 2 tasks | 3 files |
| Phase 146 P01 | 20min | 3 tasks | 8 files |
| Phase 146 P02 | 15min | 2 tasks | 3 files |
| Phase 146 P03 | 18min | 3 tasks | 8 files |
| Phase 146 P04 | 20min | 3 tasks | 3 files |
| Phase 146 P05 | 10min | 1 tasks | 4 files |
| Phase 147 P01 | 12min | 3 tasks | 2 files |
| Phase 147 P02 | 35min | 5 tasks | 6 files |
| Phase 147 P03 | 25min | 3 tasks | 4 files |
| Phase 147 P04 | 25min | 2 tasks | 2 files |
| Phase 148 P01 | 25min | 3 tasks | 3 files |
| Phase 148 P03 | 15min | 2 tasks | 3 files |
| Phase 148 P02 | 35min | 3 tasks | 5 files |
| Phase 148 P04 | 40min | 3 tasks | 1 files |
| Phase 149 P01 | 45min | 3 tasks | 4 files |
| Phase 149 P02 | 20min | 3 tasks | 6 files |
| Phase 149 P03 | 25min | 3 tasks | 12 files |
| Phase 149 P04 | 25min | 3 tasks | 6 files |
| Phase 149 P05 | 20min | 3 tasks | 4 files |
| Phase 149 P06 | 40min | 3 tasks | 8 files |
| Phase 149 P07 | 45min | 3 tasks | 7 files |
| Phase 149 P08 | 40min | 3 tasks | 5 files |
| Phase 149 P09 | 45min | 3 tasks | 8 files |
| Phase 149 PP10 | 40min | 3 tasks | 6 files |
| Phase 149 P11 | 75min | 2 tasks | 10 files |
| Phase 150 P01 | 35min | 3 tasks | 4 files |
| Phase 150 P02 | 40min | 3 tasks | 2 files |
| Phase 150 P04 | 55min | 3 tasks | 3 files |
| Phase 150 P05 | 40min | 3 tasks | 8 files |
| Phase 150 P06 | 50min | 3 tasks | 13 files |
| Phase 150 P07 | 35min | 3 tasks | 4 files |
| Phase 150 P08 | ~90min | 3 tasks | 2 files |
| Phase 150 P09 | 35min | 3 tasks | 5 files |
| Phase 154 P01 | 15min | 2 tasks | 6 files |
| Phase 154 P02 | 35min | 2 tasks | 5 files |
| Phase 154 P03 | 40min | 3 tasks | 5 files |
| Phase 154 P04 | 15min | 2 tasks | 2 files |
| Phase 154 P05 | 45min | 3 tasks | 4 files |
| Phase 155 P01 | 20min | 2 tasks | 4 files |
| Phase 155 P02 | 25min | 3 tasks | 7 files |
| Phase 155 P03 | 25min | 3 tasks | 6 files |
| Phase 155 P04 | 20min | 2 tasks | 3 files |
| Phase 155 P05 | 35min | 2 tasks | 4 files |
| Phase 155 P06 | 15min | 2 tasks | 2 files |
| Phase 156 P01 | 12min | 2 tasks | 4 files |
| Phase 156 P03 | 35min | 3 tasks | 5 files |
| Phase 156 PP02 | 25min | 3 tasks tasks | 4 files files |
| Phase 156 P04 | ~30min | 3 tasks | 8 files |
| Phase 156 P05 | ~55min | 4 tasks | 8 files |
| Phase 156 P06 | 45min | 3 tasks | 7 files |
| Phase 157 PP01 | 18min | 2 tasks | 3 files |
| Phase 157 P02 | 12min | 3 tasks | 3 files |
| Phase 157 P03 | 15min | 3 tasks | 5 files |
| Phase 157 P04 | 25min | 2 tasks | 5 files |
| Phase 157 PP05 | 35min | 3 tasks | 4 files |
| Phase 158 P01 | 15min | 2 tasks | 3 files |
| Phase 158 P02 | 15min | 2 tasks | 4 files |
| Phase 158 P03 | 35min | 3 tasks | 4 files |
| Phase 159 P01 | 35min | 2 tasks | 6 files |
| Phase 159 P02 | 12min | 2 tasks | 2 files |
| Phase 159 P03 | 12min | 2 tasks | 4 files |
| Phase 159 P04 | 30min | 3 tasks | 7 files |
| Phase 159 P05 | 20min | 2 tasks | 4 files |
| Phase 160 P01 | 25min | 2 tasks | 6 files |
| Phase 160 P02 | 20min | 2 tasks | 3 files |
| Phase 160 P03 | 35min | 3 tasks | 6 files |

## Accumulated Context

**v5.14 shipped 2026-08-19.** Decisions below predate the shipped v5.14 milestone (Phases
157–160, HWLC-13/15/16/17/18) and are kept for historical continuity — full milestone decision
log lives in PROJECT.md's Key Decisions table and `.planning/RETROSPECTIVE.md`'s v5.14 section.
Next milestone's numbering continues at Phase 161.

### Decisions

- Numbering continues at Phase 154 (v5.12 ended at 153). Phase order is dependency-driven:
  identity/data-model (154) must land before drift detection (155) since every diff feature
  reconciles "the same device across two scans"; reporting/OT-ICS safety (156) depends on
  drift events existing before they can be surfaced or scheduled. Research (4 unanimous passes)
  resolved the milestone's flagged 3x sizing uncertainty toward the smaller estimate — a
  scheduling/diffing/reporting layer over existing `HardwareDevice` data, not a new scanner
  surface; no new dependencies, database, or background worker. Sensor-push hardware coverage
  (extending `PushEnvelope`) is explicitly deferred to v2+, not included in v5.13 — console-direct
  scans only. Phase 156's OT/ICS cadence-floor work requires a dedicated `/gsd-secure-phase`
  review before shipping, per REQUIREMENTS.md HWLC-12.

- Numbering continues at Phase 144 (v5.10 ended at 143). Phase order is dependency-driven:
  chunked discovery core (144) must land before liveness pre-pass (145) or progress/scaling (146)
  since both depend on batches existing. 144 explicitly bundles the gate-relaxation work
  (`target_expander.py::_MAX_HOSTS_PER_CIDR` + `jobs.py`'s 422 stopgap) with the chunking core
  itself — per research PITFALLS.md, splitting them risks a repeat of the Phase 141 outer-gating
  bug shape (feature built, never reachable). Liveness pre-pass (145) gets its own phase for
  isolated non-root privilege-fallback verification. Progress/scaling/CLI-parity/disclosure (146)
  groups DISC-04/05/06/07 as one phase per explicit instruction. Backlog drain (147) is fully
  independent of the DISC phases — different code paths, sequenced last but not blocking.

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
- [Phase 142]: Combined Task 1 (table/staleness) and Task 2 (comparator/correlation) into a single commit — verified together as one cohesive module before the first commit
- [Phase 142]: RESEARCH.md illustrative regex fixed: [A-Za-z]* widened to [A-Za-z0-9]* so Cisco's parenthetical+train-letter suffix (e.g. '(4)M3') parses; added explicit R<release> capture group so Juniper's '12.3R12-S19' correctly compares greater than '12.3R12'
- [Phase ?]: [Phase 142] run_cve_status() accepts an optional argv list (unlike qramm_cmd's zero-arg signature) to support --format json pass-through to hw_cve.status_report
- [Phase 142]: 142-03: cve_snapshot_stale computed once on exec_content in writer.py, then stamped onto every device dict at the html_renderer call site rather than passed as a second render_hardware_section parameter, keeping the render function a pure devices-list contract matching its test
- [Phase 142]: 142-04: cve_matches serialized as reduced {cve_id, severity, source_url}; CVE_BADGE_STYLE reuses the existing SNMP-confirmed blue hue rather than a new color
- [Phase 142]: 142-05: docs/getting-started.md had no pre-existing catalog-status command list; added a new Catalog Status Commands section for compliance/qramm/cve
- [Phase 144]: Split Task 1's combined helper+cap-removal edit into two atomic commits (helpers-only, then cap-removal+test-rewrites) to preserve the plan's intended per-task checkpoint granularity
- [Phase ?]: [Phase 144]: Relocated error_endpoints init to before the discovery block (Pitfall 1) rather than inventing a parallel discovery-only bookkeeping list
- [Phase ?]: [Phase 144]: Guarded the discovery ScanCheckpoint write with a _discovery_batch_loop_ran flag so it fires only on the nmap batch-loop path, not cache-hit/fallback sub-branches
- [Phase ?]: [Phase 144]: Batch-loop failure-isolation tests exercise the loop's exact shape directly (mirroring inline run_scan.py code) rather than invoking full main(), per RESEARCH.md's stated fallback
- [Phase 145]: parse_nmap_host_status() deliberately omits parse_nmap_xml's skip-if-not-up filter so down hosts survive as up=False rows — D-04: record don't drop non-responsive hosts
- [Phase 145]: _resolve_liveness_port_spec narrowed the plan's literal any-other-override-to-dash wording to a startswith(--top-ports) check with pass-through for unrecognized overrides — makes the mandated _SAFE_NMAP_ARG_RE allowlist gate reachable/testable instead of dead code
- [Phase 145]: liveness_endpoints kept as a dedicated accumulator separate from error_endpoints, merged in only after the discovery ScanCheckpoint partial-failure snapshot, so normal liveness_skip/privilege_fallback rows never flip discovery status to partial
- [Phase 145]: Survivor set for the sweep computed by excluding known-down hosts from the batch (not including known-up hosts), so a host nmap omits entirely from the liveness XML defaults to being swept rather than silently dropped
- [Phase 146]: named tuple _PHASE146_SCANJOB_COLUMNS to avoid _PHASE46_COLUMNS collision; corrected _ADDITIVE_MIGRATIONS header comment since scan_jobs is now the first pure table to require a migration
- [Phase ?]: Phase 146-02: Both discovery helpers degrade to base/T4 default on non-int input rather than raising, since they feed directly into subprocess timeout/argv
- [Phase ?]: Phase 146-02: discovery_timing_template_for_batch returns only hardcoded -T4/-T3 literals via if/else per threat T-146-01 - never config/input-built
- [Phase 146]: 146-03: _compute_undetermined_hosts() gates on port==0 AND scan_error_category in ('exception','liveness_skip') — port==0 conjunct is load-bearing so a live-host TLS/SSH/API handshake error is never counted as undetermined
- [Phase 146]: 146-04: Combined Tasks 1+2 into one commit since both edit the exact same discovery-loop-body statements (pre-count/progress-write + timeout/timing scaling); resolved Open Q1 as batch formula fully replacing args.nmap_timeout inside the loop, and Open Qs 2/3 as accepting one throwaway O(n) pre-count pass so the dashboard batch total is correct from batch 1
- [Phase 146]: 146-05 executed exactly per PATTERNS.md conditional shape — no deviations
- [Phase 147]: DRAIN-01 — hoisted run_ot_supplemental_and_persist() above run_scan.py's ssh-stage if/else so a --resume-scan-id continuation still fingerprints OT-only (Modbus/BACnet) hosts; ssh-stage checkpoint write stays fresh-run-branch-only, reordered before the hoisted (advisory) hardware persist
- [Phase 147]: D-147-02-A: build-catalog (option a) — user confirmed via orchestrator checkpoint before plan dispatch
- [Phase 147]: D-147-03-WR02: wr02-fix - ship the port-aware default CORS allowlist fix via a new QUIRK_DASHBOARD_PORT env var
- [Phase 147]: D-147-03-CD03: cd03-accept - accept the SSRF TOCTOU/DNS-rebinding risk with refreshed rationale (answered after an orchestrator-level clarification exchange), citing Phase 120 T-120-04 and Phase 123 SSRF-05
- [Phase 147]: D-147-04-AUTHENTICODE: user confirmed no production Windows Authenticode code-signing cert acquired/loaded into GitHub Actions secrets — UAT-143-03 finalized STILL BLOCKED, re-triage at next milestone close
- [Phase 147]: DRAIN-04 re-triaged all Deferred Items rows with dated 2026-08-10 dispositions; gh evidence shows origin/main unpushed since 2026-06-18 (no live windows-latest CI run for Phase 139-147 work); relocated 36 stray per-plan duration rows to Performance Metrics; removed stale healthcare-vertical-merge quick_task row
- [Phase 148]: [Phase 148]: Scoped test_no_guard_is_ref_shape_only to actual if: directive lines only, excluding explanatory comments that quote the guard literal by name
- [Phase 148]: 148-03: Reworded 5.11.0.md See Also section to avoid the literal missing-filename substrings (5.7/5.8/5.9/5.10 dot-md) while still conveying the gap, satisfying the plan's own no-link acceptance criterion and the new test's guard
- [Phase 148]: 148-02 RELEASE-03 tag-hygiene guard: TDD gate via temporary implementation relocation for genuine RED; LOOSE_RELEASE_TAG_RE (^v[0-9]) deliberately broader than release.yml's v*.*.* glob; baseline seeded with all 32 pre-existing tags for a green-from-day-one first scheduled run
- [Phase 148]: 148-04 live-run evidence: dry-run run 31524058796 (publish job skipped, windows-package success incl. SELF_TEST_SIGNING: OK); tag-hygiene run 31524420671 (EXEMPT names v5.9/v5.10.0/v5.11.0 correctly, zero flagged); bare v5.11.0 GitHub Release created with zero assets, isDraft false, latest=false
- [Phase 149]: D-04 drift repair: 30 unregistered skip markers registered/updated in tests/skip_registry.py (optional_extra/live_infra only); AST walker extended to detect skip/skipif/xfail decorators; pre_existing_triage_149 category reserved for Plans 02-10
- [Phase ?]: Phase 149 Plan 02: All 23 Cluster 1 (SSRF/DNS-blocked sandbox) tests dispositioned quarantined-xfail with matching skip_registry entries and ledger rows; meta-gate confirmed green
- [Phase 149]: Plan 03: All 20 Cluster 2/6 tests dispositioned quarantined-skip (not xfail), per D-03: running them under full-suite pollution is not useful signal and they are expected to run cleanly once Phase 150 fixes the shared fixture/lifecycle issue
- [Phase 149]: Plan 04: reassigned test_cli_correctness.py::test_version_consistency from Cluster 3 (environment) to Cluster 4 (stale assertion) per RESEARCH.md ground truth; TARGET now derives from quirk.__version__ instead of a hardcoded literal, preserving cross-module consistency coverage without every-release edits
- [Phase 149]: [Phase 149]: Plan 05: test_sensor_push_id_revalidation.py's 2 failures are shared in-memory SQLite cache pollution across test files (file::memory:?cache=shared&uri=true), NOT an AUDIT-08 write-before-reject defect; individually investigated per RESEARCH.md Open Question 3, distinct sub-reason from test_auto_merge_trigger.py's 8 outdated-fixture failures
- [Phase 149]: Plan 06: closed the tests/scanner/ non-recursive glob gap (Assumption A3) before quarantining any Cluster 9 Group A test in that subdirectory; individually investigated all 18, converging on DNS-blocked-sandbox SSRF guard (9), stale CR-06 opt-in guard (2), stale test fixture (2) for 13 xfail quarantines, while 5 were found not reproducible in this sandbox (already-registered optional_extra skips or currently-passing) and left unmarked
- [Phase 149]: Plan 07: test_route_coverage.py's AUTH-02 GET /api/config finding confirmed as stale test inventory (route intentionally public per its own docstring, no sensitive data exposed), explicitly not flagged SECURITY, per must_haves requirement
- [Phase 149]: Plan 07: 4 of 5 /api/compare test failures were a test-construction bug (unescaped + UTC offset in raw f-string query URL decoded as space by query parsing), not API-contract drift as RESEARCH.md suspected; verified via urllib.parse.quote()-encoded params returning 200
- [Phase 149]: Plan 08: test_qramm_staleness.py SIGSEGV pair investigated but not reproducible in this sandbox (3/3 isolated runs, direct CLI hand-invocation, and a ~550-test full-suite slice all pass); left unmarked per Plan 06 precedent, flagged HIGH-PRIORITY for Phase 150 re-verification given a segfault's severity class
- [Phase 149]: Plan 08: test_no_risk_engine_import's failure is cross-test sys.modules pollution from test_findings_evaluator_dedupe.py's risk_engine shim test (alphabetically earlier), not a real QRAMM-12 import-graph violation in evidence_bridge.py itself
- [Phase 149]: test_cbom_schema_validation.py's otics chaos-lab profile drift is a genuine Chaos Lab Maintenance gap (Phase 141-07's synthesizer never landed in PROFILE_ENDPOINTS), flagged for Phase 150 follow-up
- [Phase 149]: Plan 09: 3 of 11 Group D1 tests (test_errors_cmd + 2 GCP-403 posture tests) investigated but found NOT reproducible in this sandbox; POSTURE-02's scan_error emission on GCP 403 already works correctly despite file's stale RED-scaffold docstring
- [Phase 149]: Plan 10: both security-gate meta-test failures confirmed as gate-logic gaps (Jinja-only detection can't see Python-side pre-escaping/static-dict sourcing; AST classifier has no ast.IfExp case), not real unsanitized-usage or safe_str-bypass findings; neither flagged SECURITY
- [Phase 149]: Plan 10: test_sensor_windows_smoke.py's SIGSEGV confirmed not reproducible and explicitly not sharing Plan 08's QRAMM SIGSEGV root cause (different subsystem/subprocess construction, no crash when run together); flagged as a second independent Phase 150 re-verification item
- [Phase 149]: Plan 11: fixed 2 real production bugs (sslyze __version__ submodule shape, impacket MethodData rename) surfaced by fresh-run reconciliation; consolidated 5 scattered SIGSEGV findings across Plans 06/08/10 into one systemic macOS fork()-under-full-suite-load root cause; quarantined 9 tests with corrected root causes; ledger reconciled to 116 rows, 0 orphaned failures, fresh full-suite run 0 failed
- [Phase ?]: [Phase 150]: Fixed _build_as_req via constants.encodeFlags([...].value) on the modern impacket path, preserving the legacy KDCOptions(...) constructor call behind an else branch for impacket <0.13.0 (Phase 150 D-05)
- [Phase ?]: [Phase 150]: Rule 1 auto-fix — test_build_as_req_nonce_uses_secrets asserted secrets.randbits(31), but commit 830ad6a (Phase 71 review, D-09) had deliberately switched the scanner to a 32-bit nonce; corrected the stale assertion to randbits(32) in the same edit that removed the xfail marker
- [Phase 150]: Local sandbox python/pip interpreter mismatch (python -> Homebrew 3.14, pip -> stray ~/Library/Python/3.9) caused 11 false full-suite failures in bacnet/modbus/openapi tests; .venv/bin/python confirmed correct interpreter, 0-failed baseline (3089 passed, 42 skipped, 80 xfailed)
- [Phase 150]: Plan 04 -- stood up $HOME/.cache/quirk-ci-parity-venv (outside repo tree, pip install -e ".[all]" + pytest only, zero identity/hw/api extras); no Python 3.11 available on this machine so venv built on 3.14.6 (known, accepted parity gap -- documented, doesn't block extras-boundary verification). Full-suite run there: 32 failed, exactly matching CI Categories B+C+D+F+G (6+18+6+1+1); Categories A/E/H (4+1+1) did not reproduce due to concrete local-vs-CI differences (working-copy .planning/ present, Docker not running, stale gitignored quirk.egg-info from pre-rename install) -- no unexplained local-only failures.
- [Phase 150]: Plan 04 D-16 -- deleted test_package_manifest_version_is_4_1_0 outright (not fixed in place); its local-only pass was traced to a stale gitignored quirk.egg-info directory in the repo working tree, absent from any fresh checkout, matching CI's real PackageNotFoundError.
- [Phase 150]: Plan 04 D-17 -- root-caused /api/sensor/push 404 as a test-construction defect: fastapi 0.141.1/starlette 1.6.0 no longer flatten include_router() routes into application.routes at include time (lazy _IncludedRouter wrapper instead), so the old isinstance(r, APIRoute) walk missed every /api/* route, not just sensor/push. Confirmed via TestClient the route dispatches correctly end-to-end (401/200). Fixed with a recursive _IncludedRouter-aware route-path walker in the test; assertion contract unchanged, no skip registered.
- [Phase 150]: Plan 05: cleaned up leftover empty labs/grpc-tls/certs directories from a prior Docker bind-mount failure before generating certs -- confirmed untracked/gitignored, filesystem-only cleanup not a git operation
- [Phase 150]: Guarded 35 extras-gated/gitignored-fixture tests with per-test skips (D-09..D-11, D-15); test_identity_surface.py and test_rest_fuzzer_probes.py deltas from plan estimates documented in 150-06-SUMMARY.md
- [Phase 150]: ROADMAP.md Phase 150 header corrected to 9 plans (not the plan's literal '6 plans' instruction) — the plan checklist already listed all 9 plan entries (150-01 through 150-09) before this plan dispatched; matched the header to that ground truth
- [Phase 150]: Live-fire CI proof closed SUITE-02/SUITE-03 -- real Linux Full Suite run 31723764281 green (0 failed, .[all]-only, ubuntu-latest, Python 3.11.15) after D-03 SIGSEGV quarantine (bbe8b55); real red run 31725715958 via throwaway PR #10 proved the gate bites (1 failed, isolated to the deliberate smoke test), PR closed unmerged and branch deleted, evidence in 150-CI-EVIDENCE.md
- [Phase 150]: Plan 09 closed the phase -- 150-VERIFICATION.md written against all 4 ROADMAP success criteria (all PASS, Criterion 1 anchored to the real CI run not the corroborating local venv run); SUITE-02/SUITE-03 confirmed Complete (already flipped by 150-08's metadata commit, this plan replaced the stale in-progress status note with a 150-CI-EVIDENCE.md pointer); ROADMAP.md's 150-09 checkbox and the Phase 150 heading both ticked -- the plan's own literal "tick all six" instruction was stale (mirrors 150-07's "6 plans" deviation) since the true count is 9 plans, all already checked; `.continue-here.md` deleted (resolved blocker, filesystem-only per PUBREPO-01 gitignore convention)
- [Phase ?]: [Phase 154]: match_confidence kept as a column distinct from the pre-existing confidence column (D-04/D-05) — cross-scan identity confidence vs. probe-result confidence
- [Phase 154]: match_confidence upgrade to high is unconditional on Step 1's vendor match outcome — a correctly-identified device still gets its SSH host-key fingerprint (RESEARCH §1)
- [Phase 154]: Rule 3 fix: three test fixture _make_ep() helpers needed ssh_audit_json=None pre-populated in __dict__, since fingerprint_one's unconditional getattr hit SQLAlchemy UnmappedInstanceError (not AttributeError) on __new__-constructed test doubles missing that key
- [Phase 154]: implemented the true D-13 per-device latest-success join at all four HardwareDevice projection sites (dashboard findings/components, merge/CBOM, CLI/PDF/DOCX writer), not a shallow probe_status filter on the old MAX(scanned_at) window - a failed re-probe never removes a device, it shows the last-known-good row
- [Phase 154]: Rule 3 fix - pre-existing Phase 141 OTICS-parity test fixtures (test_hardware_projection_sites.py, test_dashboard_api.py) needed probe_status=success added since their seeded HardwareDevice rows predate the new per-site probe_status filter and would otherwise silently vanish from every projection
- [Phase 154]: 154-04: purge call placed before the hw_batch add() loop (deviation from PATTERNS §8, plan-authorized) — avoids autoflush interaction between pending inserts and synchronize_session=False delete
- [Phase 154]: 154-05: UAT-154-01 automated gate narrowed from a broad -k "fingerprint" selector to explicit test node IDs after discovering it matched an unrelated pre-existing flaky test not caused by this plan
- [Phase 155]: Shipped 4 citation-backed EOL_TABLE entries (F5 BIG-IP, Fortinet FortiGate, Palo Alto PAN-OS, Cisco IOS) instead of the plan's 6-entry target — Fail-closed fallback per plan text -- Juniper/HPE/Thales/Schneider Electric/Johnson Controls candidates had no independently fetchable, dated vendor lifecycle page reachable in this sandbox; guessing dates was disallowed
- [Phase 155]: Fortinet entry sourced via endoflife.date/fortios aggregator — No static Fortinet-owned EOL bulletin page was fetchable (JS-rendered); endoflife.date is a well-known aggregator that itself cites Fortinet's official EOL bulletins, cross-verified live
- [Phase 155]: [Phase 155] HardwareDriftEvent placed immediately after MergeRun in models.py, before HardwareDevice; recent_successful_hardware_rows() docstring kept terse to satisfy the plan's grep -A12 acceptance window while preserving the full documented contract; TIER_ORDER promoted verbatim into hardware_tier.py, dashboard route imports it aliased to the old private name so both existing call sites needed zero edits
- [Phase 155]: firmware_for_correlation() consolidated into hw_cve.py rather than duplicated a third time in hardware_drift.py::cve_delta() — closes RESEARCH.md Open Question 1 per the Phase 154 WR-02 lesson
- [Phase 155]: compute_drift_candidates() reads the STORED remediation_tier column, not a re-derived assign_tier() call — the reconciliation engine diffs persisted scan-row state
- [Phase 155]: bridge_evidence_state() reads only persisted bridge_confirmed_at/bridge_evidence_json columns, never a transient bridge_status dict key owned by quirk/cbom/bridge.py
- [Phase 155]: [Phase 155] 155-04: session.commit() runs unconditionally once after the reconcile candidate loop (even with zero inserts), matching plan text exactly; CVE-delta test fixtures monkeypatch hw_cve.correlate_device() rather than depending on live CVE_TABLE catalog content
- [Phase ?]: Phase 155-05: Confirmed live run_scan.py has exactly 2 real HardwareDevice commit sites (not 3) — run_ot_supplemental_and_persist() and the SNMP-only block; _run_ssh_phase() only accumulates into hw_batch. Resolved RESEARCH.md Open Question 2 as option (a) — reconcile at both real commit sites.
- [Phase ?]: Phase 155-05: apply_eol_date() single terminal call site placed immediately before the Phase 154 D-07 probe_status assignment in fingerprint_one() — covers every vendor/model resolution path (SSH, HTTP, SNMP, Modbus, BACnet).
- [Phase ?]: Phase 155-05: Site (B) SNMP-only block reconciles _snmp_new_batch (rows actually committed there), not _snmp_flush_batch — the pre-existing detached _existing_dev mutation-persistence gap is documented inline as a backlog candidate, not fixed (out of scope per HWLC-04..09).
- [Phase 155]: 155-06: docs/report-interpretation.md deliberately left untouched, deferred to Phase 156 when drift events gain a dashboard/report surface; REQUIREMENTS.md HWLC-04..09 verified already complete on disk (no diff needed)
- [Phase 156]: OTICS_MIN_INTERVAL_HOURS is a hardcoded, non-config-overridable floor (168h/7 days, D-19); min_gap_hours takes the MINIMUM of 9 consecutive gaps across 10 firings, never the average (D-20); strip_otics_keys uses explicit named pop over a 2-entry allowlist only, never substring matching (T-156-03)
- [Phase ?]: Phase 156-03: TIER_ORDER lower-int-is-more-urgent means Tier 2 -> Tier 1 is worsened, not improved
- [Phase ?]: Phase 156-03: hardware_drift.py module docstring paraphrases forbidden scoring-module names to avoid tripping its own T-156-04 acceptance-criteria grep
- [Phase ?]: [Phase 156] 156-02: dispatch-time gate in _materialize_scan_config uses stdlib logging.getLogger(__name__).info matching scheduler_cmd.py's existing idiom, not a threaded Logger param, per D-22's actual requirement (always-visible level)
- [Phase ?]: [Phase 156] 156-02: write-path inventory test asserts exact HTTP route/CLI subcommand/import-confinement sets as literal expected-value constants; negative-proof (temporary dummy route) confirmed the guard fails loudly before revert
- [Phase ?]: [Phase 156] 156-04: writer.py drift-serialization mirrors (not imports) quirk/dashboard/api/routes/hardware_drift.py's lookup/direction helpers — writer.py has no existing dependency on the dashboard API package
- [Phase 156]: Lifecycle advisory guard test comments avoid literal RegressionAlertChip/ui-badge substrings so raw grep acceptance criteria pass (156-03 docstring precedent); guard test resolves component sources via path.resolve not new URL(import.meta.url); section eyebrow/icon teal applied via inline style since .label-eyebrow is unlayered CSS and always wins the cascade over Tailwind utilities
- [Phase ?]: [Phase 156]: 156-06: enable_modbus/enable_bacnet had never been documented in docs/configuration.md's Connectors Block before this plan (pre-existing Phase 141 gap) — added both alongside enable_recurring_otics under Rule 2
- [Phase ?]: [Phase 156]: 156-06: /gsd-secure-phase 156 SECURED — 19/19 threats closed, zero high-severity findings, all four D-23 threat surfaces verified against real implementation code and tests; artifact written correctly to 156-SECURITY.md on first attempt (no root-SECURITY.md relocation needed)
- [Phase ?]: [Phase 157]: hardware_drift_event_retention_days is a dedicated ScanCfg field (D-02), not shared with hardware_history_retention_days; default 365 (D-03) matches the codebase's 365-day-cadence convention
- [Phase ?]: [Phase 157]: 157-01 call site is a dedicated if db_path: block, separate from the existing if hw_batch and db_path: block, so the drift-event purge runs even when a scan fingerprints zero fresh devices
- [Phase ?]: [Phase 157]: 157-02 build_eol_forecast(devices, today=None) signature intentionally constrained to devices/today only — no score input can be threaded through, verified by inspect.signature test (T-157-05)
- [Phase ?]: [Phase 157]: 157-02 quirk/reports/executive.py deliberately excluded from the T-157-05 advisory-only firewall module set — it legitimately imports compute_readiness_score, mirroring the Phase 155/156 precedent
- [Phase 157]: 157-03 eol_forecast population block placed after hardware_devices' final assignment (post bridge-detection/mitigation), no new DB session — forecast input always matches the hardware table's device set
- [Phase 157]: 157-03 render_eol_forecast_section uses h3 one level below render_drift_section's h2, bucket sentences as p not table, template placeholder after (not inside) drift_section conditional so forecast renders independent of drift events
- [Phase 157]: 157-04 DOCX forecast subsection is level-3 heading, one below the drift section's level-2, narrative paragraphs only (no table), guarded independently of hardware_drift_events
- [Phase 157]: 157-04 CLI forecast is a net-new sibling of the Hardware PQC Advisory block, gated solely on exec_content.eol_forecast — executive.py never shipped CLI drift rendering (Phase 156 D-12), so this is genuinely new prose, not an extension
- [Phase 157]: 157-04 new dedicated tests/test_executive_forecast_section.py module created, resolving 157-VALIDATION.md's open Wave 0 item about build_exec_markdown's scattered test coverage
- [Phase 157]: 157-05 report-interpretation.md's §10.11 EOL/Tier Forecast section expanded in place (not duplicated) with the literal bucket-label vocabulary and an explicit reader-facing guarantee that hardware_drift_event_retention_days places no limit on the forecast (ROADMAP success criterion #5)
- [Phase 158]: 158-01: D-158-A/B/C implemented as locked — persist_and_reconcile() always commits internally (no commit:bool param); purge_stale_hardware_history() relocated into hardware_drift.py with a run_scan.py alias; Site B (SNMP-only) now applies the retention purge for the first time — intentional behavior expansion
- [Phase 158]: 158-02: PushEnvelope.hardware_devices uses a bare None default (D-158-D/E/F implemented as locked) — absent vs confirmed-empty structurally distinguished; _hardware_device_to_dict()/_read_scan_hardware_devices() mirror the existing _endpoint_to_dict()/_read_scan_endpoints() shapes; both push and export _build_envelope() call sites updated identically
- [Phase 158]: 158-03: persist_and_reconcile() rolls back the session on internal exception before returning (0, []) -- a missing rollback previously let a failed hardware insert (e.g. NOT NULL scanned_at) poison the shared session and fail the whole sensor push, violating the advisory-only contract
- [Phase 158]: 158-03: HardwareDevice.scanned_at (NOT NULL) falls back to ingest time when the wire value is missing/malformed, instead of passing None through to a column that rejects it and silently dropping the whole device row
- [Phase 159]: 159-01 D-159-A..E implemented as locked; Rule 1 fix wired is_partial_scan through sensor_cmd.py::_hardware_device_to_dict()/console_cmd.py envelope reconstruction in the same commit to keep the Phase 158 sensor round-trip future-proofing gate green
- [Phase ?]: [Phase 159]: 159-02 D-159-F/G/H implemented as locked; run_check_in() docstring paraphrases compute_readiness_score to avoid tripping test_skips_discovery_and_scanner_phases' own forbidden-substring grep; test_check_in_flag_parses exercises the real argparse parser via main() + sys.argv patching since main() has no factored parser accessor
- [Phase ?]: [Phase 159]: 159-03 D-159-I/J/K implemented as locked; badge-not-filter on /compare's hardware_drift block, zero new filtering on /trends/compare score paths, /api/hardware/drift latest-bucket side effect documented not fixed
- [Phase 159]: 159-04 D-159-M..Q implemented as locked; is_partial_scan threaded through writer.py's existing (host,port) drift lookup with no new DB query; HTML banner sits outside <details> (D-159-N), CLI banner lives inside existing Hardware PQC Advisory block with an explicit no-Recent-Lifecycle-Changes-heading test to keep Phase 156 D-12 intact
- [Phase ?]: [Phase 159]: 159-05 D-159-R/S/T confirmed and applied — no api-reference.md placeholder created, no chaos-lab files touched, no version string changed; docs/UAT-SERIES.md Series 159 (UAT-159-01..04) and all 4 touched docs synced to Obsidian vault
- [Phase ?]: [Phase 160]: 160-01 D-160-A..G implemented as locked; VendorPqcTrendEvent has no host/port columns (D-160-E); VENDOR_EVENT_TYPES separate allowlist from EVENT_TYPES (D-160-D); reconcile_vendor_pqc_trend() reuses _confirmed_value()/DEFAULT_N/DEFAULT_M verbatim (D-160-A)
- [Phase 160]: 160-02 D-160-H/I implemented as locked; Rule 1 fix reworded hardware_drift.py module docstring's literal SCORE_WEIGHTS mention (Phase 155 legacy) to pass the new T-160-04 guard
- [Phase 160]: 160-03 D-160-B/F/G/J implemented as locked; VendorPqcTrendEventItem has no host/port/severity/numeric field; Query(50, ge=1, le=200) bound and .limit(limit+1) truncation pattern reused verbatim from the existing /hardware/drift endpoint

### Pending Todos

None yet.

### Blockers/Concerns

- **Phase 156 plan-phase decision-coverage gate override (2026-08-14):** the mechanical
  `check.decision-coverage-plan` gate flagged 18 CONTEXT.md decisions (D-01..D-25) as uncovered.
  This is the same false positive documented for Phase 150 (2026-08-12) — the gate scans only
  structured `must_haves.truths`/frontmatter fields, not full plan body prose, even though its own
  message says "(or body)". Direct grep confirms **17 of the 18 flagged decisions are cited by ID
  in plan bodies** (`.planning/phases/156-*/156-0{1..6}-PLAN.md`); the one exception, D-12
  (CLI/terminal drift rendering out of scope), is correctly absent because it's a deliberate
  deferral already listed in CONTEXT.md's own `<deferred>` section — a plan citing it would be
  wrong. The independent `gsd-plan-checker` agent's semantic review separately confirmed full
  decision coverage with zero blockers/warnings, specifically calling out D-26/D-18's corrected
  write-path handling, D-07's palette layers, D-13's caption, and D-23's secure-phase gate as
  correctly implemented. Proceeded past the gate on this documented override. Re-surface at
  `/gsd:verify-phase 156` only if the same coverage question resurfaces there.

- Phase 140's evidence-sufficiency bar (what SNMP facts constitute "confirmed" vs "assumed") is
  not fully specified by research — flagged as a planning-time design decision to make explicit
  before implementation, not skip.

- Phase 141 OT-safety norms are MEDIUM confidence — do a web-search verification pass during
  `/gsd:plan-phase 141`, not skip it (fragile-device probing has real-world outage history).

- Phase 142 CVE/CPE version-matching guidance is MEDIUM confidence — verify current NVD API/CPE
  guidance and vendor firmware version-string normalization (Cisco/Juniper/etc.) during planning.

- **Phase 150 plan-phase decision-coverage gate override (2026-08-12):** the mechanical
  `check.decision-coverage-plan` gate flagged D-01, D-02, D-04, D-06, D-07, D-08 as uncovered
  (only D-05 registered). This is a false positive — the gate appears to scan only structured
  `must_haves.truths`/frontmatter fields, not full plan body prose, even though its own message
  says "(or body)". `grep -n "D-0[1-8]" .planning/phases/150-*/*-PLAN.md` confirms all 7 decisions
  are extensively cited in plan bodies, and the independent `gsd-plan-checker` agent's semantic
  review separately verified "D-01 through D-08 all traced to specific tasks" (Context Compliance
  dimension: Pass). User selected "Proceed anyway" at the /gsd-plan-phase 150 override prompt.
  Re-surface at `/gsd:verify-phase 150` only if the same coverage question resurfaces there.

- **RESOLVED (Plan 150-08, 2026-08-13):** Phase 150 Plan 03's original blocker — real GitHub Actions Linux Full Suite run (31598809033) failed with 38 failures on a genuine .[all]-only ubuntu-latest install — is closed. Plans 150-04 through 150-07 fixed all 8 failure categories; Plan 150-08 re-ran the live-fire proof end to end: green run 31723764281 (0 failed) + red run 31725715958 (1 failed, isolated to the deliberate smoke test) via PR #10 (closed unmerged). SUITE-02/SUITE-03 both proven and marked complete in REQUIREMENTS.md. See 150-08-SUMMARY.md and 150-CI-EVIDENCE.md.

## Deferred Items

**Last re-triaged:** 2026-08-18 (v5.14 milestone close — pre-close artifact audit, 3 items
acknowledged, see table below)

Acknowledged at v5.14 milestone close (2026-08-18):

| Category | Item | Status |
|----------|------|--------|
| quick_task | `260611-g0b-merge-healthcare-vertical-branch-into-ma` | missing (recurring false positive — same row already documented as false-positive at v5.10, v5.11, and v5.13 close: PLAN+SUMMARY both exist on disk; `audit-open`'s scanner has a persistent bug that cannot see this task's completion) |
| uat_gap (158) | `158-HUMAN-UAT.md` — 2 pending scenarios | partial (UAT-158-01/02 — visual confirmation that sensor-pushed hardware devices/drift render on `/hardware` and `/compare`; not a functional gap — HWLC-15 independently SATISFIED at the code/test level per `158-VERIFICATION.md` (4/4 must-haves) and `v5.14-MILESTONE-AUDIT.md`; deferred by explicit user choice at the Phase 158 verification checkpoint) |
| verification_gap (158) | `158-VERIFICATION.md` | human_needed (same underlying item as the uat_gap row above — one shared pair of pending visual checks, no separate defect) |

Acknowledged at v5.13 milestone close (2026-08-15):

| Category | Item | Status |
|----------|------|--------|
| quick_task | `260611-g0b-merge-healthcare-vertical-branch-into-ma` | missing (confirmed false positive — same row already documented as false-positive at v5.11 close: PLAN+SUMMARY both exist on disk, merge commit `9967d8a` is in history; `audit-open` scanner cannot see it) |
| uat_gap (155) | `155-HUMAN-UAT.md` — 1 pending scenario | partial (human read-through of `docs/operators-guide.md` §9.7 + `docs/UAT-SERIES.md` Series 155 for prose clarity; not a functional gap — HWLC-04..09 all independently SATISFIED per `155-VERIFICATION.md` and `v5.13-MILESTONE-AUDIT.md`) |
| verification_gap (155) | `155-VERIFICATION.md` | human_needed (same underlying item as the uat_gap row above — one shared pending human doc-read, no separate defect) |

**Last re-triaged (carried-forward items):** 2026-08-14 (Phase 152 Plan 03 — Phase 144 nmap timing artifact closed via
3-run live-fire evidence; see Resolved section below)

Resolved (2026-08-14):

| Category | Item | Status | Resolution |
|----------|------|--------|------------|
| verification_gap (144) | Phase 144 nmap adaptive RTT/timing-engine artifact — accepted VERIFICATION override, `OPEN (needs real hardware)` in v5.11-MILESTONE-AUDIT.md | **RESOLVED — DOES NOT REPRODUCE** | Empirically settled via `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md` — 3 independent live-fire runs against the DISC-09 `segmented-network` chaos lab profile (Plan 152-01) showed the chunked discovery batch loop's production timing template produces an identical `segnet-live` open-port set to a direct, non-throttled nmap run every time. No mitigation applied; `quirk/discovery/nmap_provider.py` unchanged. |

**Last re-triaged (carried-forward items):** 2026-08-11 (v5.11 milestone-audit closeout; supersedes the 2026-08-10
Phase 147 DRAIN-04 pass, whose Phase 143 `uat_gap` rationale went stale within a day — see that
row's `Re-triaged (2026-08-11)` note)

Carried forward from v5.9 close (2026-07-30):

| Category | Item | Status | Re-triaged (2026-08-10) |
|----------|------|--------|--------------------------|
| verification_gap | Phase 132: 132-VERIFICATION.md | human_needed — pre-existing, already shipped/tagged | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| verification_gap | Phase 135: 135-VERIFICATION.md | human_needed — README What's New visual render check | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| verification_gap | Phase 137: 137-VERIFICATION.md | human_needed — prose quality/live enroll walkthrough | STILL BLOCKED — visual/prose human review, no codebase evidence can close it |
| human-UAT (118) | UAT-118-01 — live Windows-host install + Scheduled Task walkthrough | deferred — needs a real Windows host | STILL BLOCKED — requires a physical or VM Windows host |
| human-UAT (114) | UAT-114-03 — operators-guide §8.9 auto-merge visual review | deferred — non-blocking | STILL BLOCKED — non-blocking visual doc review of operators-guide §8.9 |
| human-UAT (93/95/96) | getpass/live PDF, ldaps code-signing, fuzzing TTY gates | deferred — environment-gated | STILL BLOCKED — environment-gated by design (TTY, live LDAPS server) |
| human-UAT (101–105) | Live Slack/email/webhook/syslog/Jira/ServiceNow delivery | deferred — needs live infra | STILL BLOCKED — requires live Slack/email/webhook/syslog/Jira/ServiceNow endpoints |
| horizon | Continuous hardware lifecycle monitoring | deferred — v5.11+, needs its own research pass | NOT A DEFERRED UAT — feature-horizon item, v5.11+ |

Acknowledged at v5.10 milestone close (2026-08-03):

| Category | Item | Status | Re-triaged (2026-08-10) |
|----------|------|--------|--------------------------|
| uat_gap | Phase 143: 143-HUMAN-UAT.md (2 pending scenarios) | partial — user approved continuing 2026-08-03; live windows-latest CI run + browser click-through remain outstanding, both have strong automated/static substitutes in place | **STILL BLOCKED, corrected rationale (2026-08-11).** The 2026-08-10 basis for this row is now factually wrong and has been replaced: `git ls-remote` confirms `origin/main` is `83ba306` — identical to local HEAD — so the Phase 139–147 work IS pushed, and `gh run list` shows Python CI, Dashboard Quality and Python Staleness Gate all green on it. The real blocker is narrower and structural: the `windows-package` job (and its Authenticode signing step) lives in `.github/workflows/release.yml`, which triggers **only** on `push: tags: ['v*.*.*']`. The newest remote tag is `v5.9` — no `v5.10` or `v5.11` tag exists — so no windows-latest release build has run for this work regardless of push state, and none will until a release tag is cut. Unblocks automatically at the next tagged release; the browser click-through remains separately human-gated. |
| verification_gap | Phase 143: 143-VERIFICATION.md | human_needed — same reason as above, user-approved | STILL BLOCKED — browser click-through still requires human execution; no new evidence since v5.10 close |
| human-UAT (143) | UAT-143-03 — Windows Authenticode signing CI (production signing cert) | BLOCKED — awaiting real production signing secrets; mechanism SECURED 7/7 threats via /gsd-secure-phase, signing step no-ops cleanly until secrets exist | **PARTIALLY EXERCISED 2026-08-11 — first real evidence in three milestones.** Pushing `v5.11.0` fired `release.yml` for the first time since `v5.8.0` (v5.10.0 was never pushed; `v5.9` is a two-component tag that never matched the `v*.*.*` glob). Confirmed working: the Windows onedir EXE builds, and the production-signing step skips cleanly with no cert present — exactly as designed. Confirmed BROKEN: the "CI self-test — ephemeral cert signing round-trip" step (added 2026-08-02, `6ed6ec1`, Phase 143 TAIL-03) had never once run and fails by construction — it verifies a self-signed cert with `signtool verify /pa`, which demands a trusted root. It hard-failed the job, so v5.11.0 shipped to PyPI with **no Windows release asset**. Fixed in `1a6effc` (trust the ephemeral root for the verify, remove it in cleanup); per user decision the asset ships with v5.12 rather than burning a patch version. Production-cert half remains genuinely blocked. |

Resolved and removed (2026-08-10): one stale `quick_task` bookkeeping row (healthcare-vertical
merge) confirmed complete via git history and removed — see 147-04-SUMMARY.md for the commit hash
and disposition detail.

## Session Continuity

Last session: 2026-08-18T13:26:48.106Z
Stopped at: Completed 160-03-PLAN.md
Phase 156 (Reporting & OT/ICS Safety) has no directory or CONTEXT.md yet, awaiting discuss/plan.

Both blocking human-verify checkpoints referenced in prior sessions (141-06 Task 3 badge colors,
141-07 Task 3 live Docker validation) were completed and approved during the Phase 141 gap-closure
rounds (141-09) on 2026-08-03 — no longer pending.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
