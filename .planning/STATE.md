---
gsd_state_version: 1.0
milestone: v5.11
milestone_name: Discovery at Scale + Backlog Drain
status: executing
stopped_at: Completed 145-01-PLAN.md
last_updated: "2026-08-10T13:51:29.652Z"
last_activity: 2026-08-10
progress:
  total_phases: 11
  completed_phases: 1
  total_plans: 6
  completed_plans: 4
  percent: 9
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-07-30)

**Core value:** Complete, defensible cryptographic inventory with CBOM deliverable and quantum-readiness score — handed to a client in under two hours — now extending agentless hardware PQC fingerprinting (SSH/HTTP/SNMP) with SNMPv3, SNMP-confirmed bridge mitigation, OT/ICS fingerprinting, firmware CVE correlation, and a small dashboard/security tail.

**Current focus:** Phase 145 — liveness-pre-pass

## Current Position

Phase: 145 (liveness-pre-pass) — EXECUTING
Plan: 2 of 3
Status: Ready to execute
Last activity: 2026-08-10

## v5.11 Phase Map

| Phase | Name | Requirements | Gate | Status |
|-------|------|--------------|------|--------|
| 144 | Chunked Discovery Core | DISC-01, DISC-02 | None (first, anchor) | Not started |
| 145 | Liveness Pre-Pass | DISC-03 | Phase 144 | Not started |
| 146 | Progress, Scaling & Disclosure | DISC-04, DISC-05, DISC-06, DISC-07 | Phase 144 | Not started |
| 147 | Backlog Drain — Lifecycle & Ledger Tail | DRAIN-01, DRAIN-02, DRAIN-03, DRAIN-04 | None (independent) | Not started |

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

## Accumulated Context

### Decisions

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

Acknowledged at v5.10 milestone close (2026-08-03):

| Category | Item | Status |
|----------|------|--------|
| uat_gap | Phase 143: 143-HUMAN-UAT.md (2 pending scenarios) | partial — user approved continuing 2026-08-03; live windows-latest CI run + browser click-through remain outstanding, both have strong automated/static substitutes in place |
| verification_gap | Phase 143: 143-VERIFICATION.md | human_needed — same reason as above, user-approved |
| quick_task | 260611-g0b-merge-healthcare-vertical-branch-into-ma | missing (audit flag) — PLAN + SUMMARY exist on disk and the healthcare vertical merge (commit 9967d8a) is documented as completed 2026-06-11; treated as stale bookkeeping, no further action needed |
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

## Session Continuity

Last session: 2026-08-10T13:51:29.646Z
Stopped at: Completed 145-01-PLAN.md

Both blocking human-verify checkpoints referenced in prior sessions (141-06 Task 3 badge colors,
141-07 Task 3 live Docker validation) were completed and approved during the Phase 141 gap-closure
rounds (141-09) on 2026-08-03 — no longer pending.

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
