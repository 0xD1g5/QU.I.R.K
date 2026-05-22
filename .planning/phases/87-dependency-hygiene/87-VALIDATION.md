---
phase: 87
slug: dependency-hygiene
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 87 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_nmap_hardening.py tests/test_xml_safe.py tests/test_packaging.py tests/test_audit_ledger_zero_open.py -x` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds (quick) / full suite per project baseline |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above.
- **After every plan wave:** Run `python -m pytest tests/ -v`.
- **Before `/gsd:verify-work`:** Full suite must be green.
- **Max feedback latency:** ~30 seconds (quick command).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 87-01-* | 01 (Node) | 1 | DEP-01 | — | `dashboard-quality` CI runs on Node 24 and goes green | smoke (GHA only) | Real GitHub Actions run on branch — not automatable locally (D-02) | N/A | ⬜ pending |
| 87-01-* | 01 (Node) | 1 | DEP-01 | — | No `node-version: '20'` remains in any workflow | unit (grep gate) | `grep -rn "node-version: '20'" .github/workflows/` returns empty | N/A | ⬜ pending |
| 87-02-* | 02 (lxml) | 0 | DEP-02 | WR-06 | `make_safe_parser()` returns a *fresh* hardened parser per call | unit | `python -m pytest tests/test_xml_safe.py -v` | ❌ W0 | ⬜ pending |
| 87-02-* | 02 (lxml) | 0 | DEP-02 | WR-06 | `parse_safely()` works on a valid XML file | unit | `python -m pytest tests/test_xml_safe.py -v` | ❌ W0 | ⬜ pending |
| 87-02-* | 02 (lxml) | 0 | DEP-02 | WR-06 | External-entity (XXE) payload raises | unit | `python -m pytest tests/test_xml_safe.py::test_parse_safely_blocks_xxe -v` | ❌ W0 | ⬜ pending |
| 87-02-* | 02 (lxml) | 0 | DEP-02 | WR-06 | `defusedxml` absent from all `quirk/` imports | unit (grep gate) | `python -m pytest tests/test_xml_safe.py::test_no_defusedxml_import_in_quirk -v` | ❌ W0 | ⬜ pending |
| 87-02-* | 02 (lxml) | 1 | DEP-02 | WR-06 | `parse_nmap_xml` succeeds on valid nmap fixture (regression) | unit | `python -m pytest tests/test_nmap_hardening.py -v` | ✅ (rewrite `test_nmap_parser_uses_defusedxml`) | ⬜ pending |
| 87-02-* | 02 (lxml) | 1 | DEP-02 | WR-06 | Billion-laughs payload raises `lxml.etree.XMLSyntaxError` (D-07 invariant) | unit | `python -m pytest tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe_lxml -v` | ❌ W0 (rename+rewrite) | ⬜ pending |
| 87-02-* | 02 (lxml) | 1 | DEP-02 | WR-06 | `defusedxml` absent / `lxml` present in `pyproject.toml` core deps | unit | `python -m pytest tests/test_packaging.py -v` | ❌ W0 (replace `test_defusedxml_in_core_deps`) | ⬜ pending |
| 87-02-* | 02 (lxml) | 1 | DEP-02 | WR-06 | WR-06 audit ledger stays `[x] closed` | integration | `python -m pytest tests/test_audit_ledger_zero_open.py -v` | ✅ | ⬜ pending |
| 87-02-* | 02 (lxml) | 1 | DEP-02 | — | `test_identity_infra.py:240` defusedxml assertion updated/inverted | unit | `python -m pytest tests/test_identity_infra.py -v` | ✅ (edit) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_xml_safe.py` — covers: `make_safe_parser()` returns a fresh instance per call; `parse_safely()` works on valid file; billion-laughs raises; XXE external entity raises; `no_network=True` blocks external URI; grep-gate `test_no_defusedxml_import_in_quirk` asserts `grep -r "defusedxml" quirk/` returns zero hits.
- [ ] Rewrite `tests/test_nmap_hardening.py::test_nmap_parser_uses_defusedxml` → `test_nmap_parser_uses_xml_safe` (asserts `make_safe_parser` used, not defusedxml).
- [ ] Rewrite `tests/test_nmap_hardening.py::test_nmap_parser_blocks_xxe` → lxml-native (`lxml.etree.XMLSyntaxError`, not `defusedxml.common.EntitiesForbidden`).
- [ ] Replace `tests/test_packaging.py::test_defusedxml_in_core_deps` with `test_defusedxml_not_in_core_deps` (+ confirm `test_lxml_in_core_deps`).
- [ ] Update `tests/test_identity_infra.py:240` assertion — remove/invert the defusedxml identity-group check (verify exact target before editing).

*Wave 0 is dense: the existing test suite encodes the OLD invariant (defusedxml present). These tests must flip to the new invariant before/with the migration, or the suite goes red on a correct change.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `dashboard-quality` CI job runs green on Node 24 | DEP-01 | GitHub Actions runner environment cannot be reproduced locally; D-02 requires a real GHA run as the definition of done | Push the phase branch, open/observe the `dashboard-quality` workflow run, confirm it executes on Node 24 and passes green |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
