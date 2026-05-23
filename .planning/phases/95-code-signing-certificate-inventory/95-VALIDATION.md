---
phase: 95
slug: code-signing-certificate-inventory
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-23
---

# Phase 95 — Code-Signing Certificate Inventory — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project standard) |
| **Config file** | `pytest.ini` / `pyproject.toml [tool.pytest]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_codesign_scanner.py tests/test_codesign_cbom.py tests/test_score_weights_invariant.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 s quick / ~3–5 min full |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds (quick command)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 95-01-01 | 01 | 1 | CSIGN-01, CSIGN-02 | T-95-01/02/03 | LDAP filter is hardcoded literal; DER parse try/except; safe_str logging | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py -q` (RED expected) | ❌ W0 | ⬜ pending |
| 95-01-02 | 01 | 1 | CSIGN-01, CSIGN-02 | T-95-01/02/03 | EKU filter; EC<256 inline; ldap3-only; safe_str; BOTH LDAP AND TLS-EKU (`test_tls_eku_check`) sources | unit | `.venv/bin/python -m pytest tests/test_codesign_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 95-02-01 | 02 | 2 | CSIGN-03 | T-95-05/06 | fingerprint token parse; bounded dedup; cross-source TLS+codesign stable count (`test_cbom_tls_plus_codesign_no_dup`) | unit | `.venv/bin/python -m pytest tests/test_codesign_cbom.py -x -q` | ❌ W0 | ⬜ pending |
| 95-02-02 | 02 | 2 | SCORE-01 | — | dual sum+count invariant | unit | `.venv/bin/python -m pytest tests/test_score_weights_invariant.py tests/test_evidence.py -x -q` | ✅ (update) / ❌ W0 | ⬜ pending |
| 95-03-01 | 03 | 3 | CSIGN-01 | T-95-08 | opt-in gate; lazy import on flag-off | unit | `.venv/bin/python -m pytest tests/test_run_scan_codesign_wiring.py -x -q` | ❌ W0 | ⬜ pending |
| 95-03-02 | 03 | 3 | LAB-01 | T-95-09 | local throwaway fixture; triple-update | integration/oracle | `test -f .../ldaps/ldif/codesign-users.ldif && grep -q "CODE-SIGN/weak-algorithm" .../expected_results_v4.md` | ❌ W0 | ⬜ pending |
| 95-04-01 | 04 | 4 | CSIGN-01/02/03, SCORE-01, LAB-01 | T-95-11 | no secrets in docs | doc-grep | `grep -q "inventory-code-signing" docs/configuration.md` | ✅ (edit) | ⬜ pending |
| 95-04-02 | 04 | 4 | CSIGN-01/02/03, SCORE-01, LAB-01 | T-95-11 | no secrets in vault | vault-grep | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-95-Code-Signing-Certificate-Inventory.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_codesign_scanner.py` — CSIGN-01/02 stubs (created test-first in 95-01-01)
- [ ] `tests/fixtures/codesign/{codesign_rsa1024_sha1,codesign_ec192,codesign_rsa2048_sha256,codesign_rsa2048_sha256_noncoding}.der` + `regen.sh` (created in 95-01-01)
- [ ] `tests/test_codesign_cbom.py` — CSIGN-03 dedup stubs (created test-first in 95-02-01)
- [ ] `tests/test_score_weights_invariant.py` — assertion updates 293.0→299.0 / 39→40 (existing file; edit in 95-02-02)
- [ ] `tests/test_evidence.py` — codesign counter assertion (extend existing; in 95-02-02)
- [ ] `tests/test_run_scan_codesign_wiring.py` — wiring stubs (created test-first in 95-03-01)

*Wave 0 test files are created test-first within their owning tasks (each code task is `tdd="true"` with a `<behavior>` block).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live chaos-lab `ldaps` profile end-to-end (real OpenLDAP) | LAB-01 | Requires Docker + running `ldaps` profile; loopback bind | `PROFILE_ARGS="--profile ldaps" ./lab.sh up`; run `python run_scan.py --inventory-code-signing --allow-internal-targets` from repo root against ldaps:636; expect 1 HIGH CODE_SIGNING finding |

*Unit/integration tests cover all requirement logic automatically; only the live-Docker oracle is environment-gated (consistent with prior LDAP-profile phases).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (quick command)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-23
