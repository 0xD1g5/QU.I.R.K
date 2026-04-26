---
phase: 29
plan: "03"
subsystem: kubernetes-secrets-inspection
tags: [kubernetes, k8s, eks, gke, aks, evidence, scoring, cbom, lab, docs, uat, dar]
dependency_graph:
  requires: [29-01, 29-02]
  provides: [dar_k8s_counters, K8S-cbom-skip, K8S-lab-docs, K8S-uat-cases]
  affects:
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
    - quirk/cbom/builder.py
    - tests/test_dar_k8s_scoring.py
    - labs/kubernetes/expected_results.md
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns:
    - dar-counter-pattern (mirroring Phase 27 DB and Phase 28 storage analogs)
    - cbom-skip-list-extension (proven by Phase 28 for S3/AZURE_BLOB)
    - tdd-red-green (test file created RED, source edits turn GREEN)
key_files:
  created:
    - tests/test_dar_k8s_scoring.py
    - labs/kubernetes/expected_results.md
  modified:
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
    - quirk/cbom/builder.py
    - docs/UAT-SERIES.md
decisions:
  - "dar_k8s_unencrypted_ratio weight = 10.0 (etcd plaintext is high-impact but narrower scope than DB-wide plaintext at 12.0)"
  - "dar_k8s_inaccessible_ratio weight = 4.0 (same as storage compliance gap dar_storage_aws_managed_ratio)"
  - "PROFILE_MULTIPLIERS unchanged — dar_ prefix auto-matches new keys (proven by Phase 28)"
  - "No Docker chaos lab for Phase 29 — managed K8s control planes only; live-cluster UAT path only"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-26"
  tasks_completed: 3
  files_modified: 4
  files_created: 2
---

# Phase 29 Plan 03: Intelligence, CBOM, Lab Docs, UAT — K8S Pipeline Wiring

Extended the intelligence and CBOM pipelines for `protocol="KUBERNETES"` findings from Plan 02, documenting the lab story (live-cluster UAT only — no Docker chaos lab for managed K8s control planes), and adding 3 Phase 29 UAT cases to UAT-SERIES.md.

## What Was Built

### Task 1: evidence.py + scoring.py + test file (c988725 RED, 70fd011 GREEN)

**tests/test_dar_k8s_scoring.py** — Created 12 tests covering all dar_k8s_* counter/scoring behaviors. RED scaffold committed first (c988725), then source edits turned all 12 GREEN (70fd011).

**quirk/intelligence/evidence.py** — Six coordinated edits:
1. `_PROTOCOL_KEYS` extended with `"KUBERNETES"` (tuple now has 13 entries)
2. `dar_k8s_unencrypted_count = 0` and `dar_k8s_inaccessible_count = 0` initialized after storage counters
3. `elif proto == "KUBERNETES":` block added to per-endpoint loop with severity ladder:
   - `"/unencrypted" in sd` → `dar_k8s_unencrypted_count += 1` (EKS/unencrypted, GKE/unencrypted)
   - `"encryption-config-inaccessible" in sd or "/platform-managed" in sd or "rbac-403" in sd` → `dar_k8s_inaccessible_count += 1`
   - EKS/encrypted, GKE/encrypted, AKS/kv-kms, secret-types-summary → no increment
4. Return dict extended with 4 new keys: `dar_k8s_unencrypted_count`, `dar_k8s_inaccessible_count`, `dar_k8s_unencrypted_ratio`, `dar_k8s_inaccessible_ratio`

**quirk/intelligence/scoring.py** — Three coordinated edits:
1. `SCORE_WEIGHTS` extended: `"dar_k8s_unencrypted_ratio": 10.0`, `"dar_k8s_inaccessible_ratio": 4.0`
2. Evidence extraction: `dar_k8s_unencrypted` and `dar_k8s_inaccessible` variables added
3. `dar_impacts` list extended from 4 to 6 entries:
   - `("Kubernetes etcd unencrypted", -_ratio(dar_k8s_unencrypted, denom) * w["dar_k8s_unencrypted_ratio"])`
   - `("Kubernetes etcd encryption inaccessible", -_ratio(dar_k8s_inaccessible, denom) * w["dar_k8s_inaccessible_ratio"])`

### Task 2: cbom/builder.py Pass 1/2/3 KUBERNETES skip (54fc9ed)

Three one-line edits to `quirk/cbom/builder.py`:
- **Pass 1** elif chain: `("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES")` — no key material
- **Pass 2** skip tuple: added `"KUBERNETES"` — no certificate data on managed control plane rows
- **Pass 3** skip tuple: added `"KUBERNETES"` — configuration protocol, not TLS/SSH network protocol

KUBERNETES endpoints produce zero CBOM components (verified: `build_cbom([KUBERNETES_ep]).components == []`).

### Task 3: labs/kubernetes/expected_results.md + docs/UAT-SERIES.md (b17e10d)

**labs/kubernetes/expected_results.md** — 145-line document (≥40 required) covering:
- Lab setup with explicit "No Docker chaos lab" callout and rationale
- Scanner configuration YAML for EKS, GKE, and AKS
- Expected scan output table for all 6 service_detail variants (K8S-01)
- Secret-type enumeration row format (K8S-02)
- Inaccessible/RBAC-degraded findings format (K8S-03)
- Evidence/scoring impact section with dar_k8s_* counter definitions and weight values
- CBOM expected output (zero components)
- Limitations section: no Docker lab, kubeconfig for K8S-02, CMK deferred, etcd API not queryable

**docs/UAT-SERIES.md** — Updated `Last Updated: 2026-04-26`; added Phase 29 section with 3 UAT cases:
- **UAT-29-01**: EKS encryption + secret-type enumeration (K8S-01/K8S-02 AWS path)
- **UAT-29-02**: GKE encryption + secret-type enumeration (K8S-01 GCP path)
- **UAT-29-03**: AKS encryption + RBAC degradation (K8S-01 Azure path + K8S-03 graceful degradation)

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| tests/test_dar_k8s_scoring.py | 12 | PASS (all GREEN) |
| tests/test_cbom_builder.py | 30 | PASS (no regressions) |
| tests/test_dar_storage_scoring.py | 9 | PASS (no Phase 28 regressions) |
| tests/test_intelligence_evidence.py | 6 | PASS |
| tests/test_intelligence_scoring.py | 4 | PASS |

Pre-existing failures (4, all confirmed pre-Phase-29):
- `test_cli_correctness.py::test_version_consistency` — expects 4.2.0, codebase at 4.3.0
- `test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0`
- `test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0`
- `test_identity_surface.py::Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`

None of these failures were introduced by this plan — all confirmed present at base commit.

## Deviations from Plan

None — plan executed exactly as written.

The CBOM acceptance criteria inline test (`build_cbom(...).get('components')`) used dict-style access on a `Bom` object; the actual API returns a `Bom` instance (not a dict). The behavior is correct — zero components produced — verified via `cbom.components`. No code change required; acceptance criteria wording is a documentation artifact.

## Mandatory Phase Completion Steps (for orchestrator — CLAUDE.md)

These steps are required after this plan ships per CLAUDE.md sections 1-4:

1. **Create Obsidian Phase Note** at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-29-Kubernetes-Secrets-Inspection.md`
2. **docs/UAT-SERIES.md updated** — completed in Task 3 (UAT-29-01/02/03 added, Last Updated: 2026-04-26)
3. **Sync docs/UAT-SERIES.md to Obsidian vault** (write to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`)
4. **Commit docs/UAT-SERIES.md** via `node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-29): update UAT-SERIES.md" --files docs/UAT-SERIES.md`

## Known Stubs

None — all implemented functions produce real findings or explicit inaccessible findings. No hardcoded empty values flow to UI rendering. labs/kubernetes/expected_results.md is documentation only.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes beyond the intelligence counter additions documented in the plan's threat model (T-29-10 through T-29-16). The defensive `str(getattr(ep, 'service_detail', '') or '')` pattern from Phase 28 is applied in the new KUBERNETES elif branch (T-29-10 mitigated).

## Self-Check: PASSED

- `quirk/intelligence/evidence.py` exists: FOUND
- `quirk/intelligence/scoring.py` exists: FOUND
- `quirk/cbom/builder.py` exists: FOUND
- `tests/test_dar_k8s_scoring.py` exists: FOUND
- `labs/kubernetes/expected_results.md` exists: FOUND
- `docs/UAT-SERIES.md` exists: FOUND
- RED commit `c988725` exists: FOUND
- GREEN commit `70fd011` exists: FOUND
- Task 2 commit `54fc9ed` exists: FOUND
- Task 3 commit `b17e10d` exists: FOUND
- `python -m pytest tests/test_dar_k8s_scoring.py` → 12 passed: CONFIRMED
- `python -m pytest tests/test_cbom_builder.py` → 30 passed: CONFIRMED
- `python -m pytest tests/test_dar_storage_scoring.py tests/test_intelligence_evidence.py tests/test_intelligence_scoring.py` → 19 passed: CONFIRMED
