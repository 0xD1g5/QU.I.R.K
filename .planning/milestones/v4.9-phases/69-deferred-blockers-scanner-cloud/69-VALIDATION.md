---
phase: 69
slug: deferred-blockers-scanner-cloud
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-14
updated: 2026-05-14
---

# Phase 69 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml / pytest.ini |
| **Quick run command** | `pytest tests/test_rate_limiter.py tests/test_cache.py tests/test_cloud_connectors.py tests/test_azure_blob.py tests/test_k8s_connector.py tests/test_tls_scanner_resource_cleanup.py tests/test_fingerprint_socket_cleanup.py -x -q` |
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

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-02-T1 | 02 | A | BLOCK-02 | — | gcp_connector._scan_cloud_sql writes severity to severity column, omits cert_pubkey_alg | grep+compile | `grep -n 'cert_pubkey_alg' quirk/scanner/gcp_connector.py \| grep -i 'HIGH\|MEDIUM' returns nothing` | ✅ | ⬜ pending |
| 69-02-T2 | 02 | A | BLOCK-02 | — | Three Cloud SQL pytest cases assert severity (not cert_pubkey_alg) | unit | `pytest tests/test_cloud_connectors.py -k cloud_sql -x -q` | ✅ | ⬜ pending |
| 69-04-T1 | 04 | A | BLOCK-04 | — | Azure Blob distinguishes BLOB-PLATFORM / BLOB-UNKNOWN / BLOB-CMK via service_detail + dat_scan_json.finding_id | unit | `pytest tests/test_azure_blob.py -x -q` | ✅ (modify) | ⬜ pending |
| 69-05-T1 | 05 | A | BLOCK-05 | — | load_cache(ttl_hours=0) returns None on fresh file | unit | `pytest tests/test_cache.py -x -q` | ❌ W0 (create) | ⬜ pending |
| 69-05-T2 | 05 | A | BLOCK-05 | — | UAT-SERIES.md documents --cache-ttl-hours 0 behavior change | doc | `grep -n 'BLOCK-05' docs/UAT-SERIES.md` returns >=1 | ✅ (modify) | ⬜ pending |
| 69-06-T1 | 06 | A | BLOCK-06 | — | TokenBucket capacity guard + Condition (no busy-wait) + rate=0 fast path | unit | `pytest tests/test_rate_limiter.py -x -q && grep -c 'time.sleep' quirk/engine/rate_limiter.py == 0` | ❌ W0 (create) | ⬜ pending |
| 69-01-T1 | 01 | B | BLOCK-01 | — | sslyze Scanner deleted in try/finally on get_results exception | unit | `pytest tests/test_tls_scanner_resource_cleanup.py -x -q` | ❌ W0 (create) | ⬜ pending |
| 69-01-T2 | 01 | B | BLOCK-01 | — | fingerprint socket .close() invoked on KeyboardInterrupt between _tcp_connect and with-block | unit | `pytest tests/test_fingerprint_socket_cleanup.py -x -q` | ❌ W0 (create) | ⬜ pending |
| 69-03-T1 | 03 | B | BLOCK-03 | — | scan_k8s_targets returns [] (no raise, no finding) when aks_clusters=[] AND credential present — per locked decision D-09 | unit | `pytest tests/test_k8s_connector.py::test_aks_empty_cluster_list_returns_empty -x -q` | ✅ (append) | ⬜ pending |
| 69-03-T2 | 03 | B | (closing) | — | python -m compileall quirk/ green; full pytest green; AUDIT-TASKS rows flipped | suite | `python -m compileall quirk/ && pytest tests/ -x -q && grep -c 'closed by Phase 69' .planning/audit-2026-05-08/AUDIT-TASKS.md >= 8` | n/a | ⬜ pending |
| 69-03-T3 | 03 | B | (closing) | — | Obsidian phase note exists; UAT-SERIES sync + commit done | manual | human-verify checkpoint | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rate_limiter.py` — new file (zero existing tests for TokenBucket per RESEARCH.md finding 3) — created in 69-06-T1
- [ ] `tests/test_cache.py` — new file (does not currently exist; verified 2026-05-14) — created in 69-05-T1
- [ ] `tests/test_tls_scanner_resource_cleanup.py` — new file — created in 69-01-T1
- [ ] `tests/test_fingerprint_socket_cleanup.py` — new file — created in 69-01-T2

*BLOCK-02 will rewrite three existing assertions in `tests/test_cloud_connectors.py` (no Wave 0 file needed); BLOCK-04 modifies `tests/test_azure_blob.py`; BLOCK-03 appends to `tests/test_k8s_connector.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--cache-ttl-hours 0` user-facing behavior change documented in UAT-SERIES | BLOCK-05 | Doc deliverable, not code | After phase ships, verify `docs/UAT-SERIES.md` includes the cache-disable note and Obsidian sync ran |
| Obsidian Phase 69 note exists | CLAUDE.md mandatory | Vault filesystem write outside repo | Verify `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-69-Deferred-BLOCKERs-Scanner-Cloud.md` exists with frontmatter |

---

## Wave Structure

| Wave | Plans | Files Touched (no overlap within wave) |
|------|-------|-----------------------------------------|
| A (parallel) | 69-02, 69-04, 69-05, 69-06 | gcp_connector.py · azure_connector.py · cache.py + UAT-SERIES.md · rate_limiter.py |
| B (parallel after A) | 69-01, 69-03 | tls_scanner.py + fingerprint.py · k8s_connector.py + AUDIT-TASKS.md + Obsidian note |

69-03 hosts the closing tasks (compileall, full pytest, ledger flip, Obsidian note) and is the LAST plan to complete.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: every task has automated verify (no 3-consecutive gap)
- [x] Wave 0 covers all MISSING references (test_rate_limiter.py, test_cache.py, test_tls_scanner_resource_cleanup.py, test_fingerprint_socket_cleanup.py)
- [x] No watch-mode flags
- [x] Feedback latency < 30s per quick command
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-signed 2026-05-14
