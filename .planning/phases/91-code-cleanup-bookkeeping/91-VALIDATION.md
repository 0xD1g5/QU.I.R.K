---
phase: 91
slug: code-cleanup-bookkeeping
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 91 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from 91-RESEARCH.md "Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (venv) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/test_dashboard_scan_history.py tests/test_infra03_nyquist_coverage.py -x -q` |
| **Deprecation gate** | `QUIRK_DB_PATH=/tmp/quirk91.db python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` |
| **Full suite command** | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/ -q` |
| **Estimated runtime** | ~30–60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (+ deprecation gate for Tier-A)
- **After every plan wave:** Run the full suite command
- **After each Tier-B deletion batch:** clean-venv smoke test (`pip install -e . && quirk --version && quirk doctor`)
- **Before completion:** Full suite green (no NEW failures vs pre-phase baseline); collection-error count = 0

---

## Observable Success Signals

| Signal | Command | Expected |
|--------|---------|----------|
| Deprecation-as-error gate passes | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` | PASS (was failing — 9 `datetime.utcnow()`) |
| Collection errors gone | `python -m pytest tests/ --collect-only -q` (NO QUIRK_DB_PATH) | 0 errors (was 7) |
| Tier-B deletions provably dead | `vulture quirk/reports/writer.py quirk/intelligence/schema.py --min-confidence 60` before delete | zero production callers |
| Clean-venv smoke | `pip install -e . && quirk --version && quirk doctor` | no import errors |
| Full suite no regression | `python -m pytest tests/ -q` | no NEW failures vs baseline |

---

## Per-Requirement Verification Map

| Req | Behavior | Test Type | Automated Command |
|-----|----------|-----------|-------------------|
| CLEAN-01 | `datetime.utcnow()` eliminated from test suite | unit | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -x -q` |
| CLEAN-01 | stale v3.x comments / version print removed | grep | `grep -rn "v3\." quirk/assessment/operator_context.py quirk/db.py quirk/scanner/tls_scanner.py` → none in output strings |
| CLEAN-02 | `_extract_cert_key_type` + 5 unused dataclasses deleted | unit | `python -m pytest tests/ --collect-only -q` (removed test files absent) |
| CLEAN-02 | D-02b vulture catalogue created (no deletions) | file-exists | `test -f docs/dead-code-candidates.md` |
| CLEAN-03 | collection errors eliminated | integration | `python -m pytest tests/ --collect-only -q` (no QUIRK_DB_PATH) |
| CLEAN-03 | VALIDATION.md current for 87/88/89 + 90 created | grep | `grep -l nyquist_compliant .planning/phases/{87,88,89,90}*/`*`-VALIDATION.md` |
| CLEAN-03 | stale CONCERNS.md entries removed | grep | dual-engine entry absent from `.planning/codebase/CONCERNS.md` |
| CLEAN-04 | JWT `verify=False` advisory comment present | grep | `grep -n "WHY:" quirk/scanner/jwt_scanner.py` |
| CLEAN-04 | operator docs note present | grep | `grep -n "allow_insecure_jwks\|verify" docs/operators-guide.md` |

---

## Wave 0 Requirements

- [ ] `vulture` installed in dev session (`pip install vulture`) — needed for CLEAN-02 reachability + D-02b report
- [ ] `tests/conftest.py` autouse `QUIRK_DB_PATH=tmp_path` fixture — implemented in CLEAN-03 (fixes 7 collection errors)
- [ ] Phase 91 VALIDATION.md — this file

---

## Manual-Only Verifications

| Behavior | Req | Why Manual | Instructions |
|----------|-----|------------|--------------|
| Tier-B symbol genuinely unreachable | CLEAN-02 | vulture over-reports on optional-extra/dynamic-import paths | Confirm each deletion target has no dynamic-import / `__init__` re-export / optional-extra caller before removing |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Tier-A ships before Tier-B (v5.0-D-06)
- [ ] clean-venv smoke after each Tier-B batch
- [ ] `nyquist_compliant: true` set when plans satisfy the map above

**Approval:** pending
