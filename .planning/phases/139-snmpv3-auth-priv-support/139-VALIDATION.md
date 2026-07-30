---
phase: 139
slug: snmpv3-auth-priv-support
status: active
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-30
finalized: 2026-07-30
---

# Phase 139 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing project-wide) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (existing — not phase-specific) |
| **Quick run command** | `pytest tests/test_credential_leakage.py tests/test_snmp_scanner_contract.py -x` |
| **Full suite command** | `pytest -m "not slow"` |
| **Estimated runtime** | ~30-60 seconds (quick), several minutes (full, per project convention) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_credential_leakage.py tests/test_snmp_scanner_contract.py -x`
- **After every plan wave:** Run `pytest -m "not slow"`
- **Before `/gsd:verify-work`:** Full suite must be green; chaos-lab manual smoke test run at least once against the reconfigured `hwcompat-snmp` container.
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 139-00-01 | 00 | 0 | SNMPV3-02, -04 | Spoofing (assurance) / DoS | v3 dispatch null-safe shape + timeout-budget + distinct security-level RED tests | unit | `pytest tests/test_snmp_scanner_contract.py -k v3 --co -q` | ✅ | ⬜ pending |
| 139-00-02 | 00 | 0 | SNMPV3-03 | Information Disclosure | snmp_scanner in MODIFIED_FILES + SNMPv3 passphrase sentinel RED tests | unit + AST gate | `pytest tests/test_credential_leakage.py -k "snmp or import_safe_str" --co -q` | ✅ | ⬜ pending |
| 139-00-03 | 00 | 0 | SNMPV3-01 | — | SnmpV3Credential load + D-02 protocol-rejection RED tests | unit | `pytest tests/test_config.py -k snmp_v3 --co -q` | ✅ | ⬜ pending |
| 139-01-01 | 01 | 1 | SNMPV3-01 | T-139-01-01/02 | Per-host USM creds (username + auth/priv env-var names) load across full SHA/AES menu; non-SHA/AES rejected (D-02) | unit | `pytest tests/test_config.py -k snmp_v3 -x` | ✅ | ⬜ pending |
| 139-01-02 | 01 | 1 | SNMPV3-01 | T-139-01-03 | 3 nullable HardwareDevice SNMPv3 columns migrate additively | unit | `python -c "import quirk.db as d; ..."` (migration-registry assert, see plan) | ✅ | ⬜ pending |
| 139-02-01 | 02 | 2 | SNMPV3-02, -04 | T-139-02-02/03/04/05 | Configured protocol object used (not hardcoded SHA-1/AES-128); protocol-mismatch classified distinctly; distinct security levels; v3 timeout ≠ v2c | unit | `pytest tests/test_snmp_scanner_contract.py -k "v3 or mismatch or proto" -x` | ✅ | ⬜ pending |
| 139-02-02 | 02 | 2 | SNMPV3-03 | T-139-02-01 | SNMPv3 username/passphrases/engine-IDs never appear in raw exceptions/logs/JSON; safe_str on every path | unit + AST gate | `pytest tests/test_credential_leakage.py -k "snmp or import_safe_str" -x` | ✅ | ⬜ pending |
| 139-03-01 | 03 | 3 | SNMPV3-02 | T-139-03-01/02/03 | fingerprint_one ladder: distinct v3-failed vs v3-protocol-mismatch vs v2c; protocol cols only on success | unit | `pytest tests/ -k "hardware_scanner or fingerprint" -q` + grep gate (see plan) | ✅ | ⬜ pending |
| 139-03-02 | 03 | 3 | SNMPV3-02 | T-139-03-02/03/04 | run_scan.py ladder mirrors site 1; mismatch state recorded; no secret CLI flag | unit/smoke | `python -m compileall run_scan.py && grep -q SNMP_MODE_V3_PROTOCOL_MISMATCH run_scan.py && python run_scan.py --help` | ✅ | ⬜ pending |
| 139-04-01..03 | 04 | 2 | SNMPV3-02 | T-139-04-01/02 | All 3 projection sites + schema + CBOM Pass 4 carry the SNMPv3 fields (B-01 lesson) | unit | `pytest tests/ -k "cbom and schema" -q` + grep gates (see plan) | ✅ | ⬜ pending |
| 139-05-01..02 | 05 | 3 | SNMPV3-02 | T-139-05-01/02/03 | HTML + DOCX render the SNMP column; failed state renders distinctly; render-parity presence test | unit | `pytest tests/test_report_render_parity.py -k snmp -x` | ✅ | ⬜ pending |
| 139-06-01 | 06 | 3 | SNMPV3-02 | T-139-06-01/02 | /hardware SNMP badge column: noAuthNoPriv ≠ authPriv, v3-failed ≠ v2c; lint+build clean | build/lint | `cd src/dashboard && npm run lint && npm run build` | ✅ | ⬜ pending |
| 139-06-02 | 06 | 3 | SNMPV3-02 | T-139-06-01 | Visual confirmation of distinct badge colors + failed-state tooltip | manual (human-verify) | checkpoint (see plan how-to-verify) | ✅ | ⬜ pending |
| 139-07-01..02 | 07 | 4 | SNMPV3-01..04 | T-139-07-01/02 | hwcompat-snmp USM (SHA+AES) live target; chaos-lab oracle + user docs + Obsidian sync | manual/smoke | grep gates (see plan) + live scan smoke | ✅ | ⬜ pending |
| 139-08-0x | 08 | 5 | SNMPV3-04 | DoS (spurious timeout) | Empirical validation of `timeout_v3 = timeout_v2c * 2` against live USM discovery round-trip | manual/smoke | timed v3 vs v2c probes vs hwcompat-snmp (see plan) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs/Plan IDs/Waves finalized post-revision (2026-07-30) against the committed 139-00..139-08 plan set.*

---

## Wave 0 Requirements

- [ ] `tests/test_snmp_scanner_contract.py` — verify this file exists (referenced by `.planning/research/PITFALLS.md` but not independently confirmed present); if absent, create it covering v2c/v3 dispatch, null-safe failure shape, and timeout budgets — stubs for SNMPV3-02 and SNMPV3-04.
- [ ] `tests/test_credential_leakage.py` — extend `MODIFIED_FILES` to include `quirk/scanner/snmp_scanner.py`; add SNMPv3-specific sentinel tests mirroring `test_sentinel_not_in_safe_str_*` patterns (auth passphrase / priv passphrase shapes) — stubs for SNMPV3-03.
- [ ] `tests/test_config.py` — add `SnmpV3Credential` load + protocol-validation test stubs for SNMPV3-01 (verify exact filename at implementation time).
- [ ] `quantum-chaos-enterprise-lab/hwcompat-snmp/snmpd.conf` — add `createUser`/`rouser` USM line (SHA auth + AES priv) alongside the existing `rocommunity public default` line. Per CLAUDE.md chaos-lab-maintenance rule, this reconfiguration also requires updating `docs/chaos-lab.md` §3.22, `quantum-chaos-enterprise-lab/README.md` (~line 70), and `expected_results_hwcompat.md` in the same phase. No `lab.sh` edit needed (profile auto-discovery).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live SNMPv3 auth+priv scan against reconfigured chaos-lab `hwcompat-snmp` target succeeds end-to-end and dashboard/report shows "v3 auth+priv" badge | SNMPV3-01, SNMPV3-02 | Requires a running chaos-lab container with real USM credentials — not practical to fully automate against a live network stack in unit tests | Start `hwcompat-snmp` profile via `lab.sh`, run `python run_scan.py --enable-snmp --target 127.0.0.1 --port 20223` with the v3 credentials configured, confirm report/dashboard badge reads "v3 auth+priv" |
| Empirical validation of the `timeout_v3 = timeout_v2c * 2` multiplier against the live USM engine-ID discovery round-trip | SNMPV3-04 | Requires measuring actual round-trip latency against a live SNMPv3 responder; the multiplier is currently `[ASSUMED]` in research, not measured | After chaos-lab `snmpd.conf` USM reconfiguration lands, time several v3 probes vs v2c probes against `hwcompat-snmp` and confirm no spurious timeouts occur with the chosen multiplier (139-08) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (post-revision, 2026-07-30)
