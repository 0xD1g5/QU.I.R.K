# Phase 141: OT/ICS Fingerprinting (Modbus + BACnet) - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Add opt-in, off-by-default Modbus/TCP (FC 43/14 read-only device identification) and BACnet/IP
(Who-Is/I-Am + read-only Device object property reads) fingerprinting to the existing hardware
fingerprint pipeline (`quirk/scanner/hardware_scanner.py`), safe enough to run against fragile
production OT/ICS gear, with results flowing into the same `HardwareDevice` inventory and CBOM
DEVICE/FIRMWARE hierarchy as SSH/HTTP/SNMP-fingerprinted devices. Covers OTICS-01..06 from
`.planning/REQUIREMENTS.md`. Sequenced after Phase 139 (mirror its dispatcher/config shape) but
has no functional dependency on Phases 139/140.

</domain>

<decisions>
## Implementation Decisions

### Waterfall integration
- **D-01:** OT/ICS probing fires on an **independent OT-port trigger**, not gated by "vendor still
  Unknown" the way SNMP is today. OT devices rarely expose SSH/HTTP/SNMP, so gating on the existing
  waterfall condition would usually be a no-op — but making the trigger explicit (port-based, not
  vendor-based) avoids silently skipping real OT fingerprinting on a device that happens to have an
  unrelated SSH honeypot or management port open.
- **D-02:** Modbus and BACnet are **two separate waterfall steps**, each with its own independent
  off-by-default flag (`enable_modbus`, `enable_bacnet` — mirrors OTICS-01/02 being two distinct
  requirements). Not one combined "OT/ICS step" — the two protocols use very different transports
  (TCP unicast request/response vs. UDP broadcast Who-Is/I-Am) and should stay isolated in
  probe logic and timeout budget.
- **D-03:** If both Modbus and BACnet identify a vendor on the same host (multi-protocol gateway
  case), **first-match wins** for the headline `device.vendor`/`device.model` — Modbus runs before
  BACnet in the waterfall, consistent with the existing SSH→HTTP→SNMP "first known match wins"
  precedent. Both raw probe results are stored regardless (separate `modbus_*`/`bacnet_*` fields),
  so nothing is lost even when only one sets the headline vendor.
- **D-04:** OT/ICS probing requires the target port (502/TCP for Modbus, 47808/UDP for BACnet) to
  already be **confirmed open by the existing port/service scan** before attempting a probe. Do
  NOT proactively probe those ports independent of port-scan results — avoids extra unsolicited
  traffic to hosts that were never going to speak the protocol, consistent with the
  minimal-footprint safety framing in Success Criteria #1-3.

### Safety posture
- **D-05:** A **one-strike-and-stop circuit-breaker** applies per host: any anomalous response
  (timeout, malformed frame, connection reset, exception) immediately aborts further OT/ICS
  probing of that host for the rest of the scan — no retries. This is stricter than the standard
  scan retry/backoff policy used elsewhere, and deliberately so: fragile PLCs/RTUs have a
  documented history of locking up or crashing under even benign read-only traffic, and a
  consulting-grade tool touching production OT gear needs the conservative default.
- **D-06:** `enable_modbus`/`enable_bacnet` are **scan-wide flags only** — no per-host allowlist.
  Matches the existing `enable_snmp`/`enable_email`/`enable_broker` precedent; a per-host allowlist
  would be new config surface not established anywhere else in the codebase and isn't required by
  OTICS-01/02's wording.
- **D-07:** Documentation (operators-guide.md + CLI `--help` text) MUST carry an **explicit risk
  warning** about OT/ICS scanning — this is a materially different risk class from SNMP/SSH
  scanning (industry-documented PLC/RTU crashes from benign read-only queries). Recommend written
  authorization before enabling on production OT networks. Not just a standard opt-in flag
  description.
- **D-08:** OT/ICS probes use a **shorter, dedicated conservative timeout** than the general scan
  default — minimizes time spent holding a connection open against fragile embedded devices and
  fails fast rather than lingering. Exact value is research/executor discretion; the intent
  (deliberately conservative, not reused wholesale from the general scan timeout) is locked.

### Chaos lab profile shape
- **D-09:** OT/ICS gets a **new dedicated `otics` compose profile** — not folded into the existing
  `hwcompat` profile the way SNMP was in Phase 133. OT/ICS is a genuinely distinct risk/protocol
  category (industrial fieldbus vs. IT management interfaces); a standalone profile mirrors how
  database/broker/email each got their own profile and keeps it separately startable/stoppable.
- **D-10:** The simulators must **behaviorally enforce fragility** — reject/hang on concurrent
  probes and/or reset the connection on malformed input — so `expected_results_*.md` can assert
  that OTICS-03's single-in-flight/read-only guarantee is actually enforced by the scanner, not
  just documented as a rule. Not a well-behaved responder that only validates identification logic.
- **D-11:** **Two separate simulator containers** under the `otics` profile — one Modbus simulator
  (TCP/502), one BACnet simulator (UDP/47808) — mirrors D-02's two-separate-waterfall-steps
  decision and keeps each protocol's fragility model isolated and independently testable.

### Result labeling
- **D-12:** Modbus/BACnet fingerprint results get a **distinct dashboard badge/chip** identifying
  the protocol source (e.g. "Modbus" / "BACnet"), placed alongside the existing hardware badges
  (CNSA tier, vendor, and the Phase 139 SNMP version badge) — mirrors the SNMPv3 badge precedent.
  OT/ICS identification carries different trust/risk implications than an IT management interface
  match, and a consultant reading the report should see the fingerprint source at a glance.
- **D-13:** When the circuit-breaker (D-05) aborts a probe, the report/dashboard shows a **distinct
  abort state** (e.g. "Modbus probe aborted — anomalous response") rather than looking identical to
  "not probed" or "no response" — mirrors the SNMPv3 D-03 precedent of never letting a real signal
  (device may be fragile/misbehaving) masquerade as "nothing happened." Operationally useful: tells
  the consultant the device is worth a closer, more careful look.
- **D-14:** New `HardwareDevice` columns follow the **established `snmp_*` naming convention** from
  Phase 139 — `modbus_vendor`/`modbus_model` (+ a probe-state field), `bacnet_vendor`/`bacnet_model`
  (+ a probe-state field), or equivalent. Keeps ORM/dict projection code predictable for the next
  engineer extending the fingerprint waterfall, continuing the precedent this phase is explicitly
  sequenced after (per OTICS-06 / the "v5.8 B-01" lesson: all three `HardwareDevice` projection
  sites — `reports/writer.py`, `merge/scan.py`, `dashboard/api/routes/scan.py` — must be updated
  together).
- **D-15:** Modbus/BACnet firmware version strings (when captured) flow into the **same
  `HardwareDevice.firmware` field and CBOM FIRMWARE component** SSH/HTTP/SNMP firmware already
  uses — no special-casing. Phase 142 (Firmware CVE Correlation) already plans to correlate against
  "the vendor/model values OT/ICS fingerprinting introduces" (per ROADMAP.md); keeping field shapes
  normalized here means Phase 142 can consume them without rework.

### Claude's Discretion
- Exact per-probe timeout value for the OT/ICS-specific conservative timeout (D-08) — intent
  locked (shorter than default), value is research-derived.
- Chaos lab simulator vendor/model identity for Modbus and BACnet (D-11) — pick realistic,
  well-documented vendor/model combos per protocol, consistent with the `hwcompat-snmp` precedent
  of simulating a recognizable real device (Cisco IOS sysDescr).
- Exact library selection for Modbus (e.g. `pymodbus`) and BACnet (e.g. `BAC0`/`bacpypes3`) — no
  existing dependency in `pyproject.toml`'s `[hw]` extras covers either protocol today; this is a
  research question (license, async support, read-only-code coverage), not a design decision.
- Exact probe-state field naming/values (D-13/D-14) beyond the `snmp_*` convention precedent.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — OTICS-01..06 (locked requirements for this phase)
- `.planning/ROADMAP.md` — Phase 141 section (goal, success criteria, dependency note re: Phase 142)

### Existing Code Precedents (mirror these patterns)
- `quirk/scanner/hardware_scanner.py` — `fingerprint_one()` waterfall (SSH→HTTP→SNMP, ~line 262
  onward); OT/ICS becomes Steps 4/5 gated on confirmed-open port (D-01/D-04), not on vendor==Unknown
- `quirk/scanner/snmp_scanner.py` — `_async_probe()` / `probe_snmp_target()` — the async probe
  dispatcher shape to mirror for Modbus/BACnet probe functions
- `quirk/config.py` — `enable_snmp: bool = False` (~line 295), `SnmpV3Credential` dataclass
  (~line 356) — the scan-wide opt-in flag pattern (D-06) to mirror for `enable_modbus`/
  `enable_bacnet`; no per-host credential/allowlist dataclass needed for this phase
- `quirk/reports/writer.py`, `quirk/merge/scan.py` (~line 232-260, `HardwareDevice` projection +
  `snmp_vendor` dict key), `quirk/dashboard/api/routes/scan.py::_derive_hw_components` (~line 802)
  — the three `HardwareDevice` projection sites that MUST all gain any new `modbus_*`/`bacnet_*`
  columns together in this same phase (OTICS-06 / repeats the v5.8 "B-01" lesson)
- `.planning/phases/139-snmpv3-auth-priv-support/139-CONTEXT.md` — D-04 badge precedent (distinct
  version/state badge next to hardware badges) and D-03 fallback-visibility precedent (distinct
  "configured but failed" state, mirrored here as D-13's abort state)

### Chaos Lab Precedents
- `quantum-chaos-enterprise-lab/docker-compose.yml` — `hwcompat-snmp` service (~line 1341-1360,
  "PHASE 133 / HWCOMPAT-SNMP" comment block) — the container-per-protocol pattern to mirror for the
  new `otics` profile's two containers (D-11)
- `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` (~line 111) dynamically derives
  `ALL_PROFILES` from compose file `profiles:` keys — a new `otics` profile requires zero lab.sh
  edits beyond what CLAUDE.md's chaos-lab maintenance checklist already mandates (README +
  `expected_results_*.md` updates, OTICS-04)
- `CLAUDE.md` §"Chaos Lab Maintenance" — mandatory `lab.sh`/README/`expected_results_*.md` sync
  rule for any new/changed compose profile

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fingerprint_one()`'s existing Step 1-3 waterfall structure (SSH→HTTP→SNMP) — Steps 4/5 append
  directly, no restructuring needed
- `snmp_scanner.py`'s async probe dispatcher shape — template for `modbus_scanner.py` /
  `bacnet_scanner.py` sibling modules
- Existing opt-in extras + boolean availability guard pattern (`_PYSNMP_AVAILABLE`-style) — reuse
  for `_PYMODBUS_AVAILABLE`/BACnet-library-available guards once libraries are selected

### Established Patterns
- Scan-wide boolean opt-in flags, default `False` (enable_snmp/enable_email/enable_broker/
  enable_modbus/enable_bacnet) — zero behavior change for existing scans without flags/extras
- Three-site `HardwareDevice` projection discipline (OTICS-06) — codified as a repeat-lesson after
  the v5.8 "B-01" miss; all three sites must land in the same phase, same plan wave if possible
- `snmp_vendor`/`snmp_version` column naming convention (Phase 139) — mirror for
  `modbus_vendor`/`modbus_model`, `bacnet_vendor`/`bacnet_model`

### Integration Points
- `fingerprint_one()` gains two new independently-flagged, port-gated steps after the existing
  SNMP step
- CBOM DEVICE/FIRMWARE hierarchy consumes `HardwareDevice.firmware` the same way regardless of
  fingerprint source (D-15) — no new CBOM builder logic needed beyond the three projection sites
- Phase 142 (Firmware CVE Correlation) depends on this phase's vendor/model output landing in
  normalized fields — no rework needed if D-14/D-15 naming conventions are followed

</code_context>

<specifics>
## Specific Ideas

No additional specific UI/behavior references beyond the fifteen decisions above — user confirmed
the "Recommended" option for every question except vendor identity and library selection, which
were explicitly left to Claude's discretion.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Firmware CVE correlation and the dashboard/security
tail are already scoped as separate Phases 142-143 in ROADMAP.md, not deferred ideas surfaced
during this discussion. Per-host OT/ICS allowlist config (D-06) was considered and explicitly
rejected, not deferred — it's out of scope, not a future-phase candidate, unless real consulting
usage later demonstrates a need.)

</deferred>

---

*Phase: 141-OT/ICS Fingerprinting (Modbus + BACnet)*
*Context gathered: 2026-07-31*
