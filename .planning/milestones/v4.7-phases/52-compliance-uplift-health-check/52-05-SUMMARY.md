---
phase: 52-compliance-uplift-health-check
plan: "05"
subsystem: tech-debt
tags: [lab.sh, saml-scanner, run-stats, security, lxml, xxe, ssrf]
dependency_graph:
  requires: ["52-01"]
  provides: ["DEBT-02-closed", "DEBT-03-closed", "DEBT-04-closed"]
  affects: ["quantum-chaos-enterprise-lab/lab.sh", "quirk/scanner/saml_scanner.py", "run_scan.py"]
tech_stack:
  added: []
  patterns:
    - "lxml.etree.XMLParser(resolve_entities=False, no_network=True) for XXE-safe XML parsing"
    - "bash snapshot pattern: _PROFILE_ARGS_OVERRIDE before source .env"
key_files:
  created: []
  modified:
    - quantum-chaos-enterprise-lab/lab.sh
    - quirk/scanner/saml_scanner.py
decisions:
  - "DEBT-03 required no code change — ports_scanned/hosts_scanned already existed under run_stats['counts'] and the writer test was GREEN on first run"
  - "DEBT-04 comment on line 162 updated to remove stale defusedxml.lxml reference in docstring"
  - "resolve_entities=False and no_network=True appear in both code (line 11) and comment (line 8) — acceptable, acceptance criterion is satisfied"
metrics:
  duration: "12 minutes"
  completed: "2026-05-05"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 2
---

# Phase 52 Plan 05: Tech Debt Closure (DEBT-02, DEBT-03, DEBT-04) Summary

Three independent surgical fixes closing the v4.6 carry-forward backlog: lab.sh CLI override precedence restoration, SAML scanner XXE/SSRF-safe parser migration, and run-stats field verification.

## Tasks Completed

### Task 1: DEBT-02 — Snapshot PROFILE_ARGS in lab.sh before sourcing .env

**Commit:** `6062981`

Two-line edit to `quantum-chaos-enterprise-lab/lab.sh`:

1. Added `_PROFILE_ARGS_OVERRIDE="${PROFILE_ARGS:-}"` before the `.env` source block to capture any CLI-supplied value.
2. Changed `PROFILE_ARGS="${PROFILE_ARGS:-}"` to `PROFILE_ARGS="${_PROFILE_ARGS_OVERRIDE:-${PROFILE_ARGS:-}}"` — CLI value wins over `.env`.

Verification:
- `bash -n quantum-chaos-enterprise-lab/lab.sh` exits 0 (syntax clean)
- `grep -c "_PROFILE_ARGS_OVERRIDE="` returns 1
- `grep -c "_PROFILE_ARGS_OVERRIDE:-"` returns 1
- Snapshot line appears before `source ".env"` line in source order (awk ORDER OK)

### Task 2: DEBT-04 — Migrate saml_scanner.py from defusedxml.lxml to raw lxml.etree

**Commit:** `613c1ae`

Replaced the first `try` block in `quirk/scanner/saml_scanner.py`:

- Removed `import defusedxml.lxml as _defused_lxml_ET`
- Replaced `_safe_ET_fromstring` body with `ET.fromstring(xml_bytes, parser=ET.XMLParser(resolve_entities=False, no_network=True))`
- Updated stale docstring comment on line 162 (previously referenced `defusedxml.lxml.fromstring()`)
- Second-tier `defusedxml.ElementTree` fallback and final `RuntimeError` branch preserved byte-identical

Security surface closed:
- `resolve_entities=False` blocks XXE injection (T-52-05-01)
- `no_network=True` blocks SSRF via external entities (T-52-05-02)

Verification:
- `grep -c "defusedxml.lxml"` returns 0
- `grep -c "import defusedxml.ElementTree"` returns 1 (fallback preserved)
- `grep -c "RuntimeError"` returns 1 (final ImportError guard preserved)
- `python3 -m pytest tests/test_saml_scanner.py -q`: 26 passed, 1 deselected (integration mark), no DeprecationWarning
- `python3 -W error::DeprecationWarning -m pytest tests/test_saml_scanner.py -q`: same, 0 DeprecationWarning emitted

### Task 3: DEBT-03 — Verify ports_scanned/hosts_scanned in run-stats

**Commit:** none required (existing code already satisfies requirement)

Verification findings:
- `run_scan.py:540-541` already contains both `hosts_scanned` and `ports_scanned` inside `run_stats["counts"]`
- `tests/test_writer.py::test_run_stats_ports_and_hosts_scanned` was GREEN on first run — writer passes the full `run_stats` dict (including `counts` sub-dict) to JSON output intact
- No promotion to top-level required; nested-under-counts placement is accepted by the test

## Deviations from Plan

None — plan executed exactly as written. Task 3 step 2 confirmed GREEN on first run so Step 3 (promotion to top-level) was correctly skipped per the action instructions.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The SAML parser migration closes existing threats T-52-05-01 (XXE) and T-52-05-02 (SSRF) documented in the plan's threat model.

## Known Stubs

None.

## Self-Check: PASSED

Files verified present:
- `quantum-chaos-enterprise-lab/lab.sh` — FOUND (modified)
- `quirk/scanner/saml_scanner.py` — FOUND (modified)

Commits verified:
- `6062981` — FOUND (DEBT-02 lab.sh fix)
- `613c1ae` — FOUND (DEBT-04 saml_scanner.py migration)
