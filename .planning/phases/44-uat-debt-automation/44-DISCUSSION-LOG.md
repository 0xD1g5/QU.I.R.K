# Phase 44: UAT Debt Automation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 44-uat-debt-automation
**Areas discussed:** K8s testing strategy, DB live vs mock tests, 50% path — which items to close, Phase 43 open CR findings

---

## K8s Testing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Cloud-only — classify and close | All three UAT-29 scenarios (EKS, GKE, AKS) formally classified as cloud-only. Existing mock-based test_k8s_connector.py accepted as sufficient. No new infra. | ✓ |
| Add minikube/kind fixture | Local cluster for generic K8s API (_enumerate_secret_types); EKS/GKE/AKS encryption remains cloud-only. Adds CI complexity (~2-3 min startup). | |
| Expand mock coverage only | More test cases in test_k8s_connector.py for untested code paths. Close Phase 29 row as 'coverage-via-mocks + cloud-only'. | |

**User's choice:** Cloud-only — classify and close
**Notes:** All three UAT-29 scenarios require cloud-managed control plane APIs (AWS KMS, GCP database encryption, Azure disk encryption) that genuinely cannot be replicated locally. Mock coverage is already in place for the scanner logic.

---

## DB Live vs Mock Tests

| Option | Description | Selected |
|--------|-------------|----------|
| Live integration tests against chaos lab | New tests hit running Docker containers (live_infra skip pattern). Runs when Docker is up, skips in pure CI. Closes both Phase 27 rows. | ✓ |
| Extend mock-based unit tests only | More test cases in test_db_connector.py via mocks. Runs always in CI but doesn't validate real DB probe behavior. | |

**User's choice:** Live integration tests against the chaos lab
**Notes:** The `database` chaos lab profile (PostgreSQL 25432, MySQL 23306) provides the target environment. Follow the test_chaos_storage.py / test_kerberos_scanner.py live_infra skip pattern with registration in skip_registry.py.

---

## 50% Path — Which Items to Close

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 28 VERIFICATION — trivial cloud-only close | One-line STATE.md entry marking it cloud-only with rationale. No test work. | |
| Phase 31 VERIFICATION — automate with seeded DB | Pytest fixture with 2 pre-seeded scan sessions in in-memory SQLite, driving /api/trends. More work but real automation. | ✓ |
| Accept 43% — 6/14 is close enough | Target phases (25, 27, 29, 30) cover 6 rows; accept the result. | |

**User's choice:** Phase 31 VERIFICATION — automate with a seeded DB
**Notes:** The conftest.py dashboard_client fixture already provides in-memory SQLite with FastAPI TestClient. Extending this with two pre-seeded CryptoEndpoint sessions to drive /api/trends is well within the established pattern. The wire format to assert is flat (UAT-9-09): current_session_ts, previous_session_ts, new_high, new_medium, new_low, resolved_high, resolved_medium, resolved_low.

---

## Phase 43 Open CR Findings

| Option | Description | Selected |
|--------|-------------|----------|
| Fix the real bugs in Phase 44 | Fix CR-02, WR-01, WR-03, WR-04. Leave WR-05 (cosmetic) and WR-06 (CI hardcoded path) deferred. | ✓ |
| Fix all 6 in Phase 44 | Fix everything including WR-05 (cosmetic) and WR-06 (CI YAML). | |
| Leave all 6 deferred | Keep scope tight — log as standalone backlog items. | |

**User's choice:** Fix the real bugs in Phase 44
**Notes:** CR-02 (ValueError on bad port), WR-01 (browser.close() not in finally), WR-03 (missing data_in_motion in PDF executive summary), WR-04 (missing scope="col" in TableHead) are correctness/accessibility bugs. WR-05 and WR-06 are cosmetic/CI-only and do not affect functionality.

---

## Claude's Discretion

- Whether Phase 25 UAT tests extend existing scanner test files vs get a dedicated integration test file
- Whether Phase 30 UAT tests extend test_vault_connector.py vs get a dedicated integration test file
- Exact skip_registry.py line numbers for new live_infra entries
- Plan sequencing order (researcher/planner decides)

## Deferred Ideas

- WR-05 (cosmetic FAIL in summary table) — deferred to future cleanup
- WR-06 (hardcoded Chrome path in CI YAML) — deferred to future CI cleanup
- Phase 28 VERIFICATION trivial cloud-only close — not needed to hit 50%, deferred
- Other non-targeted deferred rows (Phase 04, 05, 07, 13, 31 HUMAN-UAT) — remain in STATE.md
