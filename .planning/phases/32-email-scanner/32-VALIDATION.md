---
phase: 32
slug: email-scanner
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
updated: 2026-04-27
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_email_scanner.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~2 minutes (full) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (email scanner tests only)
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirements | Threat Ref | Test Type | Automated Command | File Exists | Status |
|---------|------|------|--------------|------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | STRUCT-01, EMAIL-00..10 | T-32-01 | unit (RED) | `pytest --collect-only tests/test_email_scanner.py` | ❌ W0 | ⬜ pending |
| 32-01-02 | 01 | 1 | EMAIL-00..10 | T-32-02 | unit (RED) | `pytest tests/test_email_scanner.py` (expect fail until 32-03) | ❌ W0 | ⬜ pending |
| 32-02-01 | 02 | 1 | STRUCT-02, STRUCT-03, EMAIL-00 | T-32-03 | unit | `python3 -m compileall quirk/models.py quirk/db.py && pytest tests/test_email_scanner.py::test_email_scan_json_column` | ✅ | ⬜ pending |
| 32-02-02 | 02 | 1 | STRUCT-02, STRUCT-03 | T-32-04, T-32-05 | unit | `python3 -m compileall quirk/config.py && grep -c "enable_email" quirk/config.py` | ✅ | ⬜ pending |
| 32-03-01 | 03 | 2 | STRUCT-01, EMAIL-01..07, EMAIL-10 | T-32-06..10 | unit | `pytest tests/test_email_scanner.py` (all GREEN) | ✅ | ⬜ pending |
| 32-03-02 | 03 | 2 | EMAIL-01..07 | T-32-06..10 | unit | `python3 -m compileall quirk/scanner/email_scanner.py` | ✅ | ⬜ pending |
| 32-04-01 | 04 | 3 | STRUCT-01, EMAIL-08, EMAIL-09 | T-32-11 | unit | `pytest tests/test_risk_engine.py -k email` | ✅ | ⬜ pending |
| 32-04-02 | 04 | 3 | EMAIL-08, EMAIL-09 | T-32-12, T-32-13 | integration | `pytest tests/test_run_scan.py -k email` | ✅ | ⬜ pending |
| 32-05-01 | 05 | 1 | EMAIL-11 | T-32-14..16 | manual | `docker compose --profile email config` | ❌ W0 | ⬜ pending |
| 32-05-02 | 05 | 1 | EMAIL-11 | T-32-17 | manual | `docker compose --profile email build` | ❌ W0 | ⬜ pending |
| 32-05-03 | 05 | 1 | EMAIL-11 | — | checkpoint | manual: `docker compose --profile email up && openssl s_client -starttls smtp -connect localhost:30025` | — | ⬜ pending |
| 32-06-01 | 06 | 4 | EMAIL-12 | — | checkpoint | manual: live scan against running lab |  — | ⬜ pending |
| 32-06-02 | 06 | 4 | EMAIL-12 | T-32-18 | manual | `test -f labs/email/expected_results.md && grep -c "weak-cipher\\|starttls-downgrade-risk" labs/email/expected_results.md` | ❌ W0 | ⬜ pending |
| 32-07-01 | 07 | 5 | all 16 IDs | T-32-19 | manual | `grep -c "Phase 32" docs/UAT-SERIES.md` | ✅ | ⬜ pending |
| 32-07-02 | 07 | 5 | all 16 IDs | T-32-20 | manual | `test -f /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-32-Email-Scanner.md` | ❌ W0 | ⬜ pending |
| 32-07-03 | 07 | 5 | — | — | checkpoint | manual: vault render + commit | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_email_scanner.py` — RED-state stubs for STRUCT-01 + EMAIL-00..10 (created by Plan 32-01)
- [ ] `tests/fixtures/email/__init__.py` — package marker for future recorded handshake fixtures (created by Plan 32-01)
- [ ] `labs/email/` directory — Postfix+Dovecot weak-TLS lab scaffolding (created by Plan 32-05)
- [ ] `labs/email/expected_results.md` — populated from live scan output (created by Plan 32-06, gated on checkpoint)
- [ ] Obsidian Phase-32 note — created during execution per CLAUDE.md ritual (created by Plan 32-07)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lab container produces ≥1 HIGH weak-cipher + ≥1 MEDIUM starttls-downgrade-risk finding | EMAIL-11 / Success #5 | Requires `docker compose --profile email up` and a real scan against the lab | 1) `docker compose --profile email up -d` 2) `quirk scan --target localhost --ports 25,465,587,993,143,995,110` 3) Inspect findings for the two expected categories |
| Port 25 cloud-egress block does not crash scan | Success #3 | Network-layer behavior depends on host egress policy | Run scan against an unreachable port-25 host (or simulate with iptables drop); confirm graceful `CONNECTION_REFUSED` log + scan completes |
| Live-scan-derived expected_results.md | EMAIL-12 / Success #5 | Must reflect what actually negotiates against OpenSSL 3.x scanner host (cannot pre-author) | Run lab scan, capture output, transcribe finding titles + severities into `labs/email/expected_results.md` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies declared
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (checkpoints are explicit gates, not silent gaps)
- [x] Wave 0 covers MISSING references — Plan 01 creates test files, Plan 05 creates lab scaffolding
- [x] No watch-mode flags
- [x] Feedback latency < 30s (quick run is single-file pytest)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-27
