# Phase 141: OT/ICS Fingerprinting (Modbus + BACnet) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-31
**Phase:** 141-OT/ICS Fingerprinting (Modbus + BACnet)
**Areas discussed:** Waterfall integration, Safety posture, Chaos lab profile shape, Result labeling

---

## Waterfall integration

| Option | Description | Selected |
|--------|-------------|----------|
| Independent OT-port trigger | Probe based on OT-specific open ports regardless of prior SSH/HTTP/SNMP vendor result | ✓ |
| Same waterfall gate as SNMP | Only attempt if vendor still "Unknown" after SSH→HTTP→SNMP | |

**User's choice:** Independent OT-port trigger
**Notes:** OT devices rarely expose SSH/HTTP, so gating on "still Unknown" would usually be a no-op anyway, but explicit port-based gating avoids a false skip.

| Option | Description | Selected |
|--------|-------------|----------|
| Two separate steps | Modbus (Step 4) and BACnet (Step 5), each independently flagged | ✓ |
| One combined OT/ICS step | Single step branching internally on enable_modbus/enable_bacnet | |

**User's choice:** Two separate steps

| Option | Description | Selected |
|--------|-------------|----------|
| First-match wins, keep both raw | Modbus runs before BACnet; first known-vendor match sets headline vendor/model; both raw results stored | ✓ |
| BACnet wins if both match | Prefer BACnet's richer Device object properties | |
| You decide | No strong preference | |

**User's choice:** First-match wins, keep both raw

| Option | Description | Selected |
|--------|-------------|----------|
| Gate on confirmed-open port | Only probe if existing port scan already found 502/47808 open | ✓ |
| Always probe proactively when flag is on | Send bounded probe regardless of prior port-scan results | |

**User's choice:** Gate on confirmed-open port

---

## Safety posture

| Option | Description | Selected |
|--------|-------------|----------|
| Circuit-breaker: one strike and stop | Any anomalous response aborts further probing of that host, no retries | ✓ |
| Standard scan retry/timeout policy | Reuse existing 2-3 retry with backoff | |

**User's choice:** Circuit-breaker: one strike and stop

| Option | Description | Selected |
|--------|-------------|----------|
| Scan-wide flag only | One boolean per scan, matches enable_snmp precedent | ✓ |
| Scan-wide flag + optional per-host allowlist | Adds Dict[str, bool]-style per-host override | |

**User's choice:** Scan-wide flag only

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit risk warning in docs | Caution callout in operators-guide.md + CLI --help about fragility/authorization | ✓ |
| Standard opt-in documentation only | Document like enable_snmp with no special warning | |

**User's choice:** Explicit risk warning in docs

| Option | Description | Selected |
|--------|-------------|----------|
| Shorter dedicated timeout | Conservative purpose-specific timeout, shorter than general scan default | ✓ |
| Reuse existing default scan timeout | Same budget as SSH/HTTP/SNMP | |

**User's choice:** Shorter dedicated timeout

---

## Chaos lab profile shape

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated 'otics' profile | Standalone compose profile, mirrors database/broker/email precedent | ✓ |
| Fold into existing 'hwcompat' profile | Matches Phase 133/139 SNMP precedent exactly | |

**User's choice:** New dedicated 'otics' profile

| Option | Description | Selected |
|--------|-------------|----------|
| Behaviorally fragile simulator | Simulator enforces single-connection rule itself, resets on malformed input | ✓ |
| Well-behaved responder only | Simple, reliable identification-only simulator | |

**User's choice:** Behaviorally fragile simulator

| Option | Description | Selected |
|--------|-------------|----------|
| Two separate containers | One Modbus (TCP/502), one BACnet (UDP/47808) | ✓ |
| One combined container | Single container speaking both protocols | |

**User's choice:** Two separate containers

| Option | Description | Selected |
|--------|-------------|----------|
| You decide | No strong preference on exact vendor/model identity | ✓ |
| Let me specify vendors | User has specific vendor/model combos in mind | |

**User's choice:** You decide

---

## Result labeling

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct protocol-source badge | New badge/chip showing "Modbus"/"BACnet" as fingerprint source | ✓ |
| Fold into existing fields, no new badge | No new visible UI element | |

**User's choice:** Distinct protocol-source badge

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, show abort state distinctly | Circuit-breaker abort shows distinct state, not identical to "no response" | ✓ |
| No, just show success/no-match | Aborted probe looks the same as no response | |

**User's choice:** Yes, show abort state distinctly

| Option | Description | Selected |
|--------|-------------|----------|
| Mirror snmp_* naming convention | modbus_vendor/modbus_model, bacnet_vendor/bacnet_model, + probe-state field | ✓ |
| You decide | No strong preference on exact column names | |

**User's choice:** Mirror snmp_* naming convention

| Option | Description | Selected |
|--------|-------------|----------|
| Same as existing firmware handling | Firmware strings flow into same HardwareDevice.firmware field, no special-casing | ✓ |
| You decide | Trust researcher to check Phase 142 dependency alignment | |

**User's choice:** Same as existing firmware handling

---

## Claude's Discretion

- Exact per-probe timeout value for the OT/ICS-specific conservative timeout
- Chaos lab simulator vendor/model identity for Modbus and BACnet
- Exact library selection for Modbus (e.g. pymodbus) and BACnet (e.g. BAC0/bacpypes3) — no existing dependency covers either protocol today
- Exact probe-state field naming/values beyond the snmp_* convention precedent

## Deferred Ideas

None — discussion stayed within phase scope. Per-host OT/ICS allowlist config was considered and explicitly rejected (not deferred to a future phase).
