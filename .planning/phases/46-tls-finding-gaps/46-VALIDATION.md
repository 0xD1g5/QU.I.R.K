---
phase: 46
slug: tls-finding-gaps
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
audited: 2026-05-05
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `pytest tests/test_tls_scanner_chain_verified.py tests/test_risk_engine_cert_defects.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q --ignore=tests/test_cbom_schema_validation.py` |
| **Estimated runtime** | ~1s quick · ~5s full |

Live-fire chaos lab verification (manual gate):
- Bring up profile: `docker compose -p chaoslab --profile tls-cert-defects up -d tls-cert-expired tls-cert-selfsigned tls-cert-untrusted-ca tls-cert-rsa1024`
- Run scanner: `python run_scan.py --config /tmp/phase46-uat-config.yaml --quiet`
- Inspect findings: confirm CRITICAL/HIGH/MEDIUM/HIGH across ports 13444–13447 + D-04 exclusivity + D-02 independence
- Note: use `docker compose` directly — `lab.sh up` affected by BACK-87 precedence bug

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite green + chaos lab live-fire pass
- **Max feedback latency:** ~1s (quick) / ~5s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | TLS-FIND-06 | D-01 | `chain_verified` column exists; migration shim is idempotent; no legacy-DB breakage | unit | `pytest tests/test_tls_scanner_chain_verified.py -k "schema or default or migration or idempotent" -x -q` | ✅ | ✅ green |
| 46-01-02 | 01 | 1 | TLS-FIND-06 | D-01 | Every `scan_one()` return path sets `chain_verified`; D-01 gate merges fallback fields when sslyze half-populates ep | unit | `pytest tests/test_tls_scanner_chain_verified.py tests/test_sslyze_integration.py -x -q` | ✅ | ✅ green (9p + 2 skip) |
| 46-02-01 | 02 | 2 | TLS-FIND-01..05 | D-02 / D-04 | Expired → CRITICAL; self-signed → HIGH; untrusted-CA → MEDIUM; RSA-1024 → HIGH; EC<256 → HIGH; D-04 mutual exclusivity enforced; D-02 multi-defect emits N independent findings | unit | `pytest tests/test_risk_engine.py tests/test_risk_engine_cert_defects.py -x -q` | ✅ | ✅ green (34p) |
| 46-03-01 | 03 | 2 | TLS-FIND-07 | — | untrusted-CA leaf cert has `issuer != subject`; RSA-2048 key (no double-fire with RSA-1024 finding); scenario-root-CA NOT in host trust store | infra | `docker compose --profile tls-cert-defects config` (exits 0); `openssl x509 -in certs/scenarios/untrusted-ca/leaf.crt -noout -subject -issuer` | ✅ | ✅ verified |
| 46-03-02 | 03 | 2 | TLS-FIND-07 | — | `tls-cert-defects` profile exposes 4 services on ports 13444–13447; oracle and README updated per CLAUDE.md chaos-lab rule | integration | `grep -c 'tls-cert-defects' quantum-chaos-enterprise-lab/docker-compose.yml` (≥5); `./lab.sh profiles \| grep tls-cert-defects` | ✅ | ✅ verified |
| 46-04-01 | 04 | 3 | TLS-FIND-01..05 | — | UAT-46-01..05 added to docs/UAT-SERIES.md; all 5 cases reference correct severities and D-02/D-04 rules | manual | `grep -c 'UAT-46-0' docs/UAT-SERIES.md` (≥5) | ✅ | ✅ verified |
| 46-04-02 | 04 | 3 | TLS-FIND-01..07 | — | Live-fire end-to-end: all 4 cert-defect findings produced at correct severities; D-04 exclusivity on port 13445; D-02 multi-defect on ports 13444 + 13447 | manual | Docker (see Manual-Only section) | N/A | ✅ verified |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_tls_scanner_chain_verified.py` — sentinel: sslyze success → `chain_verified` set; sslyze ERROR → fallback fires AND sets `chain_verified`; no `cert_not_after=None` half-populated rows (11 tests: 9p + 2 skip)
- [x] `tests/test_risk_engine_cert_defects.py` — one finding per defect class (D-02), self-signed vs untrusted-CA mutually exclusive (D-04), expected severities CRITICAL/HIGH/MEDIUM/HIGH/HIGH (10 tests)
- [x] DB migration shim — `_ensure_phase46_columns()` in quirk/db.py adds `chain_verified BOOLEAN` column to existing SQLite DBs via idempotent ALTER TABLE; wired into `init_db()` after `_ensure_phase41_columns()`
- [x] Update **existing** `tests/test_risk_engine.py` cases that assert old severities (TLS-FIND-01: HIGH→CRITICAL; TLS-FIND-02: MEDIUM→HIGH) — landed in same commit as engine fix (commit `386e1bd`)

---

## Unplanned Fix — Plan 46-04 Live-Fire Discovery

**Task 46-04-BUG (Rule 1):** `verify pre-pass check_hostname ValueError on hostname-less targets`

- **Symptom:** First live-fire scan produced 0 untrusted-CA findings — `chain_verified` was NULL for all 4 chaos lab endpoints.
- **Root cause:** `_scan_one_fallback` verify pre-pass set `verify_ctx.check_hostname = True` unconditionally, but passed `server_hostname=None` when SNI was off or the target was an IP. `wrap_socket` raised `ValueError` before chain validation ran; the broad `except Exception` routed to `chain_verified = None`, making the untrusted-CA branch dead end-to-end for all IP/localhost targets.
- **Fix:** When `verify_hostname is None`, set `verify_ctx.check_hostname = False`. CERT_REQUIRED still validates chain trust; hostname-mismatch is a separate concern (out of scope per CONTEXT.md "Boundaries"). Commit: `de70301`.
- **Verified by:** `pytest tests/test_tls_scanner_chain_verified.py tests/test_risk_engine.py tests/test_risk_engine_cert_defects.py -x -q` → 43 passed, 2 skipped; plus live-fire re-run producing full 4-finding matrix.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chaos lab `tls-cert-defects` profile boots cleanly with all 4 nginx services | TLS-FIND-07 | Requires Docker daemon | `docker compose -p chaoslab --profile tls-cert-defects up -d ...; docker ps` (all 4 Up on 13444–13447) |
| End-to-end scan produces CRITICAL/HIGH/MEDIUM/HIGH findings across 4 ports | TLS-FIND-01..05 | Requires running lab | `python run_scan.py --config /tmp/phase46-uat-config.yaml --quiet` and inspect findings JSON |
| D-04: port 13445 (self-signed) emits HIGH self-signed, NOT untrusted-CA | TLS-FIND-02 / D-04 | Requires running lab | Inspect findings at port 13445 — exactly 1 cert-trust finding with title "TLS certificate is self-signed" |
| D-02: ports 13444 + 13447 each emit 2 independent Phase 46 findings | D-02 | Requires running lab | Port 13444: CRITICAL expired + MEDIUM untrusted-CA (issuer≠subject AND chain_verified=False). Port 13447: HIGH RSA-1024 + MEDIUM untrusted-CA. No rollup. |
| `docker compose down` cleanly tears down the new profile | CLAUDE.md chaos lab rule | Stateful Docker | `docker compose -p chaoslab --profile tls-cert-defects down; docker ps` shows no leftover tls-cert-* containers |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (chain_verified field, severity-fix tests, cert fixtures)
- [x] No watch-mode flags
- [x] Feedback latency < 60s (quick) / 180s (full)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** retroactively audited 2026-05-05

---

## Validation Audit 2026-05-05

| Metric | Count |
|--------|-------|
| Gaps found (empty Per-Task Map) | 7 tasks undocumented |
| Gaps resolved | 7 (map filled from SUMMARY.md artifacts) |
| Escalated to manual-only | 0 |
| Unplanned fixes recorded | 1 (46-04-BUG verify pre-pass) |
| Final test count | 68 passed, 2 skipped (sslyze-gated) |
| Wave 0 files confirmed present | 2 (test_tls_scanner_chain_verified.py, test_risk_engine_cert_defects.py) |
