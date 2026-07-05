---
phase: 138-chaos-lab-docs-living-docs-system
plan: "01"
subsystem: documentation
tags: [chaos-lab, hwcompat, snmp, obsidian-sync]
dependency_graph:
  requires: []
  provides: [chaos-lab-hwcompat-docs, obsidian-chaos-lab-sync]
  affects: [docs/chaos-lab.md]
tech_stack:
  added: []
  patterns: [profile-section-pattern, port-table-pattern]
key_files:
  created: []
  modified:
    - docs/chaos-lab.md
decisions:
  - "Document all three hwcompat services (ssh/http/snmp) in §3.22 rather than SNMP-only, consistent with multi-service profile sections like broker §3.19"
  - "Use PROFILE_ARGS=\"--profile hwcompat\" ./lab.sh up — no new lab.sh subcommand (documentation-only milestone scope)"
  - "Use hwcompat-snmp as service name, describe as Net-SNMP container simulating Cisco IOS — no cisco-ios invented service name"
metrics:
  duration: "12 minutes"
  completed: "2026-07-05"
  tasks_completed: 2
  files_modified: 1
---

# Phase 138 Plan 01: chaos-lab.md hwcompat Documentation Summary

**One-liner:** Added hwcompat §3.22 profile section with all three services (ssh/http/snmp), [hw] pip prerequisite, and port table rows 20221/20222/20223, then synced to Obsidian vault.

## What Was Built

### Task 1: Add hwcompat §3.22 section, [hw] prerequisite, and port table rows (commit 61da8ac)

Made three targeted edits to `docs/chaos-lab.md`:

**Edit 1 — §1 Prerequisites (LAB-02):** Added a new bullet under **Prerequisites:**
- `For hardware scanning profiles (hwcompat): pip install quirk-scanner[hw] — installs the SNMP probe libraries (pysnmp 7)`

**Edit 2 — §3.22 hwcompat Profile (LAB-01):** Inserted a new section after §3.21 fuzz-target and before §4 Starting Multiple Profiles. The section documents:
- Intro paragraph covering Phase 127 (ssh/http services) + Phase 133 (snmp service) origins, agentless hardware fingerprinting across all three paths, and advisory-only status
- Blockquote repeating the `pip install quirk-scanner[hw]` prerequisite
- Service table with all three services: hwcompat-ssh (20221/SSH), hwcompat-http (20222/HTTP), hwcompat-snmp (20223/UDP)
- `PROFILE_ARGS="--profile hwcompat" ./lab.sh up` start command
- SNMP scan command: `python run_scan.py --target 127.0.0.1 --ports 20223 --enable-snmp --snmp-community public`
- SNMP container prose: Net-SNMP on alpine:3.19 simulating Cisco IOS, community `public`, sysDescr "Cisco IOS Software, Version 15.2(4)M3, RELEASE SOFTWARE (fc2)", sysObjectID 1.3.6.1.4.1.9.1.1
- Expected scanner findings for all three services (vendor=Unknown/HPE/Cisco, appropriate confidence/pqc_status values)
- `See: quantum-chaos-enterprise-lab/expected_results_hwcompat.md` reference line

**Edit 3 — §5 Port Reference Table (LAB-01):** Added three rows in port-sorted order after the 20022 ssh-weak row:
- `20221 | hwcompat-ssh | hwcompat | vendor=Unknown (SSH banner)`
- `20222 | hwcompat-http | hwcompat | vendor=HPE model=iLO5 (HTTP mgmt)`
- `20223 | hwcompat-snmp | hwcompat | vendor=Cisco fingerprint_method=snmp`

### Task 2: Sync chaos-lab.md to Obsidian vault (no separate commit — vault is not git-tracked)

Wrote `docs/chaos-lab.md` with prepended frontmatter to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Chaos-Lab.md`. Frontmatter: `project: QU.I.R.K.`, `type: guide`, `status: active`, `source: docs/chaos-lab.md`, `updated: 2026-07-05`.

## Deviations from Plan

None — plan executed exactly as written. RESEARCH.md pitfall notes (no `cisco-ios` service name, no `./lab.sh up snmp` subcommand) were honored.

## Known Stubs

None.

## Threat Flags

None — documentation-only changes; no code, API surface, or schema modified.

## Self-Check: PASSED

- `docs/chaos-lab.md` exists and contains `### 3.22 hwcompat Profile`: FOUND
- `docs/chaos-lab.md` contains `quirk-scanner[hw]` (count 2): FOUND
- `docs/chaos-lab.md` contains `20221`, `20222`, `20223`: FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Chaos-Lab.md` exists and contains `hwcompat-snmp`: FOUND
- Commit `61da8ac` exists: FOUND
