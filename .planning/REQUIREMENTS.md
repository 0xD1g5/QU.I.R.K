# QU.I.R.K. — v5.9 Requirements
# Documentation Audit & Living Docs System

**Milestone:** v5.9  
**Phases:** 135+  
**Status:** Active  
**Last updated:** 2026-07-03

---

## Milestone Goal

Audit all project documentation against features shipped in v5.4–v5.8, bring every doc current,
fill structural coverage gaps (hardware fingerprinting, SNMP, admin guide for the distributed
console/sensor split), and embed an auto-enforced per-phase documentation checklist into CLAUDE.md
so docs stay accurate as development continues.

---

## Requirements

### CORE — Core Documentation Refresh

- [x] **CORE-01**: README version string updated to v5.8.0 and "What's New" section covers v5.6, v5.7, and v5.8 milestones
- [x] **CORE-02**: README feature list reflects hardware fingerprinting (SSH/HTTP banner + SNMP), CNSA 2.0 remediation tiers, crypto-bridge detection, and CBOM DEVICE/FIRMWARE hierarchy
- [x] **CORE-03**: `docs/getting-started.md` 3-step quickstart remains accurate and documents the optional `[hw]` extras install step for SNMP hardware scanning
- [x] **CORE-04**: `docs/architecture.md` covers the hardware scan signal chain (SSH banner → HTTP mgmt → SNMP), SNMP probe path (pysnmp 7 HLAPI, 3-OID, sysdescrparser dual-path), and CBOM DEVICE parent + FIRMWARE children hierarchy

### OPS — Operators Guide & Report Interpretation

- [x] **OPS-01**: `docs/operators-guide.md` has a SNMP hardware scanning section covering `[hw]` extras install (`pip install quirk-scanner[hw]`), community string configuration (`snmp_community`), 3-OID probe targets (sysDescr/sysName/sysObjectID), and expected output
- [x] **OPS-02**: `docs/operators-guide.md` has a hardware lifecycle tiers section explaining CNSA 2.0 Tier 1/2/3/N-A classification, how to read tier assignments in the dashboard and reports, and what remediation action each tier implies
- [x] **OPS-03**: `docs/operators-guide.md` has a crypto-bridge detection section explaining what `upstream_mitigated` means, when bridge detection fires, and how to interpret the conservative `partial_only` default in findings
- [x] **OPS-04**: `docs/report-interpretation.md` covers the CBOM DEVICE/FIRMWARE component hierarchy, the HardwareInventory dashboard tab, and how hardware findings relate to the quantum-readiness score

### ADMIN — New Admin Guide

- [ ] **ADMIN-01**: New `docs/admin-guide.md` created covering console deployment (install, start, network requirements, port 8512) and sensor enrollment workflow (`quirk sensor enroll`, `sensor.yaml`, verifying connectivity)
- [ ] **ADMIN-02**: `docs/admin-guide.md` covers per-sensor auth lifecycle: token issuance at enrollment, revocation via `quirk console revoke-sensor`, rotation procedure, and what to do when a sensor token is compromised
- [ ] **ADMIN-03**: `docs/admin-guide.md` covers SNMP network requirements (UDP 161 inbound to scan targets, read-only community string hygiene, SNMPv2c scope limitations, `[hw]` package install) and troubleshooting SNMP probe failures

### LAB — Chaos Lab Documentation

- [x] **LAB-01**: `docs/chaos-lab.md` documents the SNMP hardware fingerprinting profile: Cisco IOS Net-SNMP container (`hwcompat-snmp` service), port 20223/udp, `PROFILE_ARGS="--profile hwcompat" ./lab.sh up` / `./lab.sh down` commands to start/stop the hwcompat profile, and expected scanner output
- [x] **LAB-02**: `docs/chaos-lab.md` documents the `[hw]` extras requirement for hardware scanning profiles and includes the install step in the lab setup prerequisites

### LIVE — Living Docs System

- [x] **LIVE-01**: `CLAUDE.md` gains a mandatory per-phase documentation checklist: a mapping of change types (new CLI command, new scanner signal, new chaos lab profile, new config option, new API endpoint, version bump) to the specific docs that must be checked and updated before a phase is considered complete
- [x] **LIVE-02**: `CLAUDE.md` gains a milestone-boundary doc review template: a structured checklist run at every `/gsd-new-milestone` covering version drift audit, coverage gaps against shipped features, and Obsidian vault sync verification
- [x] **LIVE-03**: The per-phase checklist in CLAUDE.md explicitly includes Obsidian vault sync as a required step whenever a user-facing doc is updated

---

## Future Requirements (deferred)

- Release notes for v5.1–v5.5 (gaps in `docs/release-notes/` — exist for 4.4, 4.5, 4.6, 5.0, 5.6 only)
- `docs/connectors/` refresh (AWS/Azure/Docker/Git connectors predate v5.x substantially)
- API reference doc (no `docs/api-reference.md` exists; dashboard REST API is undocumented for external consumers)
- SNMPv3 auth documentation (deferred until SNMPv3 ships in a later milestone)
- OT/ICS (Modbus/BACnet) lab and operator docs (deferred — capability not yet shipped)

---

## Out of Scope

- **No new features** — this is a documentation-only milestone; no scanner capability changes
- **SaaS multi-tenancy** — stays parked; no SaaS docs
- **Authenticode code-signing** — Windows sensor signing docs deferred pending cert + CI secret spike
- **SNMPv3 docs** — deferred; v5.8 ships SNMPv2c community read-only only
- **Full connectors refresh** — AWS/Azure/Git/Docker connector docs are large scope; deferred to a future docs pass

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 135 | Complete |
| CORE-02 | Phase 135 | Complete |
| CORE-03 | Phase 135 | Complete |
| CORE-04 | Phase 138.1 | Complete |
| OPS-01 | Phase 136 | Complete |
| OPS-02 | Phase 136 | Complete |
| OPS-03 | Phase 136 | Complete |
| OPS-04 | Phase 137 | Complete |
| ADMIN-01 | Phase 137 | Pending |
| ADMIN-02 | Phase 137 | Pending |
| ADMIN-03 | Phase 137 | Pending |
| LAB-01 | Phase 138 | Complete |
| LAB-02 | Phase 138 | Complete |
| LIVE-01 | Phase 138 | Complete |
| LIVE-02 | Phase 138 | Complete |
| LIVE-03 | Phase 138 | Complete |
