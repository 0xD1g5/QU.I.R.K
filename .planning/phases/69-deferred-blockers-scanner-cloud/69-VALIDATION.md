---
phase: 69
slug: deferred-blockers-scanner-cloud
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml / pytest.ini |
| **Quick run command** | `pytest tests/test_rate_limiter.py tests/test_cache.py tests/test_cloud_connectors.py tests/scanner/ -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~30s quick / ~2min full |

---

## Sampling Rate

- **After every task commit:** Run targeted module test (e.g. `pytest tests/test_rate_limiter.py -q`)
- **After every plan wave:** Run quick command above
- **Before `/gsd-verify-work`:** Full suite + `python -m compileall quirk/` must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Populated by planner during Step 8. Placeholder rows below mirror the six BLOCKERs and one wave shape from RESEARCH.md.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-02-* | 02 | A | BLOCK-02 | — | GCP Cloud SQL writes SSL severity to `severity`, not `cert_pubkey_alg` | unit | `pytest tests/test_cloud_connectors.py -k cloud_sql -q` | ✅ | ⬜ pending |
| 69-04-* | 04 | A | BLOCK-04 | — | Azure Blob distinguishes platform-managed vs absent key_source via service_detail + dat_scan_json.finding_id | unit | `pytest tests/test_cloud_connectors.py -k azure_blob -q` | ✅ | ⬜ pending |
| 69-05-* | 05 | A | BLOCK-05 | — | `load_cache(..., ttl_hours=0)` returns None even when cache file is fresh | unit | `pytest tests/test_cache.py -q` | ❌ W0 | ⬜ pending |
| 69-06-* | 06 | A | BLOCK-06 | — | `TokenBucket.acquire(n>capacity)` raises ValueError; threading.Condition replaces busy-wait | unit | `pytest tests/test_rate_limiter.py -q` | ❌ W0 | ⬜ pending |
| 69-01-* | 01 | B | BLOCK-01 | — | sslyze Scanner cleaned up on exception; fingerprint socket closed on all exception paths | unit | `pytest tests/scanner/test_tls_scanner.py tests/scanner/test_fingerprint.py -q` | ✅ | ⬜ pending |
| 69-03-* | 03 | B | BLOCK-03 | — | K8s with azure_cred=None emits K8S-03-conformant inaccessible finding; empty aks_clusters returns [] | unit | `pytest tests/test_cloud_connectors.py -k k8s -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rate_limiter.py` — new file (zero existing tests for TokenBucket per RESEARCH.md finding 3)
- [ ] `tests/test_cache.py` — verify exists; add `ttl_hours=0` test if missing

*All other targets have existing tests; BLOCK-02 will rewrite three existing assertions in `tests/test_cloud_connectors.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--cache-ttl-hours 0` user-facing behavior change documented in UAT-SERIES | BLOCK-05 | Doc deliverable, not code | After phase ships, verify `docs/UAT-SERIES.md` includes the cache-disable note and Obsidian sync ran |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test_rate_limiter.py creation)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (planner sets this once per-task verify map is filled)

**Approval:** pending
