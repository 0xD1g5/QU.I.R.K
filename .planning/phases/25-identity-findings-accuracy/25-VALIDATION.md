---
phase: 25
slug: identity-findings-accuracy
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
---

# Phase 25 — Validation Strategy

> Per-phase validation contract reconstructed from SUMMARY.md artifacts (State B).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + unittest.TestCase |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_identity_findings_accuracy.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~0.3 seconds (quick), ~30 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_identity_findings_accuracy.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 25-01-01 | 01 | 1 | SAML-04, IDENT-02, IDENT-03, KERB-03 | T-25-01 | Test scaffold only — no production attack surface | unit (RED scaffold) | `python -m pytest tests/test_identity_findings_accuracy.py -v` | ✅ | ✅ green |
| 25-02-01 | 02 | 2 | SAML-04, IDENT-02, IDENT-03 | T-25-02, T-25-03 | SAML/OIDC endpoints must NOT appear in TLS findings (source isolation) | unit | `python -m pytest tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_rs256_oidc_produces_identity_finding tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_rs384_oidc_produces_identity_finding tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_saml_endpoint_absent_from_tls_findings -v` | ✅ | ✅ green |
| 25-02-02 | 02 | 2 | KERB-03, INFRA-03 | T-25-04 | ldap3>=2.9.1 supply chain trust — no upper-bound pin | unit | `python -m pytest tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_pyproject_ldap3_in_identity_extras -v` | ✅ | ✅ green |
| 25-03-01 | 03 | 2 | INFRA-03 | T-25-05 | Documentation oracle — no executable content | unit (doc assertion) | `python -m pytest tests/test_identity_findings_accuracy.py::TestIdentityFindingsAccuracy::test_chaos_lab_expected_results_phase25 -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements. Phase 25 was a TDD phase — the test file was created as Plan 01 (RED scaffold) before any implementation. No additional Wave 0 setup was needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SAML/OIDC findings appear in Identity tab (not TLS Findings tab) in dashboard UI | IDENT-02 | Requires running dashboard + chaos lab (simpla-samlphp Docker container); visual confirmation of tab routing | Start chaos lab: `docker compose --profile simpla-samlphp up -d`. Run scan. Open dashboard scan detail. Confirm RSA-1024/RS256 findings appear in Identity tab only, absent from TLS Findings tab. |
| `pip install -e ".[identity]"` installs ldap3>=2.9.1 without conflicts | INFRA-03 | Requires clean venv + pip install; cannot run without environment side effects | In a fresh venv: `pip install -e ".[identity]" && pip show ldap3`. Confirm version >= 2.9.1 alongside impacket. |
| Kerberos scanner returns RC4-HMAC findings with ldap3 present | INFRA-03 | Requires samba-dc container + live Kerberos AS-REQ exchange | Start chaos lab: `docker compose --profile samba-dc up -d`. Run `quirk scan --targets localhost:88`. Confirm rc4-hmac HIGH finding in Identity tab. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (gap filled: test_chaos_lab_expected_results_phase25 added 2026-04-24)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated to manual-only | 0 |
| Pre-existing manual-only items | 3 |
