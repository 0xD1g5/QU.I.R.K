---
phase: 52
slug: compliance-uplift-health-check
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| **Config file** | pyproject.toml |
| **Quick run command** | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py tests/test_cbom_builder.py tests/test_saml_scanner.py -q` |
| **Full suite command** | `.venv/bin/python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick suite (`test_compliance_schema.py tests/test_cbom_builder.py tests/test_saml_scanner.py`)
- **After every plan wave:** Run full suite (`tests/ -q`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 52-W0-01 | Wave 0 | 0 | COMPLY-10 | — | `_fips_status()` returns `approved`/`non-approved` based on nist_level | unit | `.venv/bin/python3 -m pytest tests/test_cbom_builder.py -k fips_status -x` | ❌ Wave 0 | ⬜ pending |
| 52-W0-02 | Wave 0 | 0 | COMPLY-10 | — | Every algo component has `quirk:fips140-3-status` property | unit | `.venv/bin/python3 -m pytest tests/test_cbom_builder.py -k fips -x` | ❌ Wave 0 | ⬜ pending |
| 52-W0-03 | Wave 0 | 0 | COMPLY-11 | — | SOC2 CC6.x entries present in COMPLIANCE_MAP (≥3 CC6.x IDs) | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ (needs SOC2 assert) | ⬜ pending |
| 52-W0-04 | Wave 0 | 0 | COMPLY-12 | — | ISO 27001:2022 entries present; no `A.x.x` IDs; version string exact | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ (needs ISO asserts) | ⬜ pending |
| 52-W0-05 | Wave 0 | 0 | DOCS-05 | — | `quirk doctor` exit 0 on all-pass; exit 1 on non-informational failure; informational never exits 1 | unit | `.venv/bin/python3 -m pytest tests/test_doctor_cmd.py -x` | ❌ Wave 0 | ⬜ pending |
| 52-01-01 | CBOM | 1 | COMPLY-10 | — | `_fips_status()` encodes nist_level>=1→approved, 0→non-approved, None→non-approved | unit | `.venv/bin/python3 -m pytest tests/test_cbom_builder.py -k fips -x` | ✅ after Wave 0 | ⬜ pending |
| 52-02-01 | COMPLY | 1 | COMPLY-11/12 | — | All 23 COMPLIANCE_MAP keys have `_soc2()` + `_iso()` entries | unit | `.venv/bin/python3 -m pytest tests/test_compliance_schema.py -x` | ✅ after Wave 0 | ⬜ pending |
| 52-03-01 | DOCTOR | 1 | DOCS-05 | — | `quirk doctor` produces Rich table with 8 rows, correct symbols | unit | `.venv/bin/python3 -m pytest tests/test_doctor_cmd.py -x` | ✅ after Wave 0 | ⬜ pending |
| 52-04-01 | DEBT | 2 | DEBT-02 | — | PROFILE_ARGS snapshot before `.env` source | manual | `PROFILE_ARGS="--profile tls" ./quantum-chaos-enterprise-lab/lab.sh up --dry-run 2>&1 \| grep "profile tls"` | N/A | ⬜ pending |
| 52-04-02 | DEBT | 2 | DEBT-03 | — | run-stats JSON contains `ports_scanned`+`hosts_scanned` | integration | `.venv/bin/python3 -m pytest tests/test_writer.py -k ports_scanned -x` | ❌ Wave 0 | ⬜ pending |
| 52-04-03 | DEBT | 2 | DEBT-04 | — | 27 SAML tests pass GREEN; no DeprecationWarning | unit | `.venv/bin/python3 -W error::DeprecationWarning -m pytest tests/test_saml_scanner.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cbom_builder.py` — add `test_fips_status_helper()` and `test_algorithm_component_has_fips_property()` test stubs
- [ ] `tests/test_compliance_schema.py` — add `test_soc2_entries_present()`, `test_iso_entries_present()`, `test_iso_rejects_legacy_control_ids()`, `test_iso_version_string()` test stubs
- [ ] `tests/test_doctor_cmd.py` — new file; covers `run_doctor()` with mock checks for all 8 categories and exit code semantics
- [ ] `tests/test_writer.py` — add `test_run_stats_ports_and_hosts_scanned()` stub (or verify fields already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PROFILE_ARGS snapshot before `.env` | DEBT-02 | Bash env variable precedence — no pytest coverage for shell variable ordering | `PROFILE_ARGS="--profile tls" ./quantum-chaos-enterprise-lab/lab.sh up --dry-run 2>&1 \| grep "profile tls"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
