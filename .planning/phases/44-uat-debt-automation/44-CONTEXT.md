# Phase 44: UAT Debt Automation - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Automate deferred UAT scenarios from Phase 27 (DB encryption), Phase 29 (K8s secrets), Phase 25 (identity: DNSSEC/SAML/Kerberos), and Phase 30 (HashiCorp Vault) — moving them from `deferred`/`partial` status to `automated` (chaos lab) or formally `cloud-only` in the STATE.md Deferred Items table. Additionally: automate Phase 31 VERIFICATION (trend analysis) using a seeded DB fixture, and fix the 4 real bugs from the Phase 43 code review (CR-02, WR-01, WR-03, WR-04).

Success is a net reduction of ≥7 of the 14 pre-v4.5 carry-over deferred rows in STATE.md.

This phase does NOT add new scanner capability, new chaos lab profiles, or new connector code.

</domain>

<decisions>
## Implementation Decisions

### K8s Testing Strategy (Phase 29 UAT)
- **D-01:** All three Phase 29 UAT scenarios (UAT-29-01 EKS, UAT-29-02 GKE, UAT-29-03 AKS) are formally classified as **cloud-only**. They require live cloud-managed clusters with provider-specific encryption features (AWS KMS for EKS, GCP database encryption for GKE, Azure disk encryption for AKS) that cannot be replicated by a local minikube/kind cluster.
- **D-02:** The existing `tests/test_k8s_connector.py` mock-based coverage is accepted as sufficient for unit-level validation. No new Docker or cluster infrastructure is added.
- **D-03:** The Phase 29 UAT row in STATE.md is closed as `cloud-only` with rationale: "EKS/GKE/AKS encryption detection requires cloud-managed control plane APIs not available in a local cluster. Scanner logic is covered by mock-based unit tests in test_k8s_connector.py."

### DB Testing Approach (Phase 27 UAT)
- **D-04:** New live integration tests run against the existing `database` chaos lab profile (PostgreSQL on port 25432, MySQL on port 23306). These follow the **same live_infra skip pattern** as `tests/test_chaos_storage.py` and `tests/test_kerberos_scanner.py` — tests are registered in `tests/skip_registry.py` with `category="live_infra"` and skip automatically when Docker is not available.
- **D-05:** Both Phase 27 rows in STATE.md are closed as `automated (chaos lab)` — `27-HUMAN-UAT.md` (1 pending) and `27-UAT.md` (7 pending).
- **D-06:** New tests live in a dedicated `tests/test_uat_db_integration.py` (not folded into the existing mock-based `tests/test_db_connector.py` which remains unit-only). This keeps the unit/integration boundary clean.

### 50% Reduction Path (which 7 items to close)
- **D-07:** The 7 target rows for STATE.md closure:
  1. Phase 25 HUMAN-UAT (2 pending) — automated via `kerberos` + `saml` chaos lab profiles
  2. Phase 25 VERIFICATION — automated (same chaos lab coverage)
  3. Phase 27 HUMAN-UAT (1 pending) — automated via `database` chaos lab
  4. Phase 27 UAT (7 pending) — automated via `database` chaos lab
  5. Phase 29 UAT (10 pending) — formally closed as `cloud-only`
  6. Phase 30 HUMAN-UAT (1 pending) — automated via `vault` chaos lab (UAT-30-01 already specifies this path)
  7. Phase 31 VERIFICATION — automated via pytest seeded-DB fixture against `/api/trends`
- **D-08:** Phase 31 VERIFICATION automation uses the existing `conftest.py` `dashboard_client` fixture pattern — two pre-seeded `CryptoEndpoint` scan sessions in an in-memory SQLite DB, driving `GET /api/trends` and asserting the response shape matches the UAT-9-09/10 wire format.

### Phase 43 Open CR Findings
- **D-09:** Fix the 4 **real bugs** identified in `43-REVIEW.md`:
  - **CR-02:** Wrap `int(os.environ.get("QUIRK_SERVE_PORT", "8080"))` in a `try/except ValueError` in `pdf.py:45` — raises `ValueError` on bad port value
  - **WR-01:** Move `browser.close()` into a `finally` block in `pdf.py:62` — currently skipped on exception
  - **WR-03:** Add `data_in_motion` subscore to the PDF executive summary in `print.tsx` — it's present in the dashboard but missing from the PDF printout
  - **WR-04:** Add `scope="col"` to `<TableHead>` in `data-at-rest.tsx` and `motion.tsx` — accessibility compliance
- **D-10:** Leave WR-05 (FAIL cosmetic in summary table — exit code is correct) and WR-06 (hardcoded Chrome path in CI YAML) as deferred backlog items. They don't affect correctness or accessibility.

### Vault + Identity Testing
- **D-11:** Phase 25 identity (Kerberos + SAML) and Phase 30 Vault automation all run against **existing chaos lab profiles** — `kerberos` (Samba DC), `saml` (SimpleSAMLphp), and `vault`. These already have live_infra skip entries in `skip_registry.py` (test_kerberos_scanner.py:360, test_saml_scanner.py:366). New UAT tests extend those files or add parallel integration test files following the same pattern.
- **D-12:** UAT-30-01 explicitly describes the Vault chaos lab path (all 5 expected findings). Phase 44 automates this as a pytest integration test — not a new test design, just wiring what was previously manual.

### Claude's Discretion
- Whether Phase 25 UAT tests extend the existing `test_kerberos_scanner.py` / `test_saml_scanner.py` or get a dedicated `tests/test_uat_identity_integration.py` file.
- Whether Phase 30 UAT tests extend `test_vault_connector.py` or get a dedicated `tests/test_uat_vault_integration.py` file.
- Exact skip_registry line numbers for new live_infra entries (determined during implementation).
- Order of plan execution — researcher/planner sequences by risk or dependency; outcome is identical.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §UAT Debt Automation — UAT-01, UAT-02, UAT-03, UAT-04 requirements
- `.planning/ROADMAP.md` §Phase 44 — goal, success criteria, and dependency list

### Phase State
- `.planning/STATE.md` §Deferred Items — the 14 carry-over rows; this is the primary target to update
- `.planning/phases/43-dashboard-polish/.continue-here.md` — open CR findings list (source for D-09/D-10)

### UAT Scenario Definitions
- `docs/UAT-SERIES.md` §Phase 27, §Phase 29, §Phase 30 — exact UAT scenario steps and pass criteria to automate

### Existing Test Infrastructure
- `tests/skip_registry.py` — ALL new live_infra tests must be registered here (Phase 41 D-02 requirement)
- `tests/conftest.py` — `dashboard_client` fixture pattern (in-memory SQLite) for Phase 31 VERIFICATION automation
- `tests/test_chaos_storage.py` — reference implementation for live_infra skip pattern against Docker chaos lab
- `tests/test_kerberos_scanner.py` — existing live_infra pattern against `kerberos` chaos lab profile
- `tests/test_saml_scanner.py` — existing live_infra pattern against `saml` chaos lab profile

### Scanner / Connector Source
- `quirk/scanner/db_connector.py` — Phase 27 DB connector (PostgreSQL, MySQL, RDS)
- `quirk/scanner/vault_connector.py` — Phase 30 Vault connector (transit, PKI, auth methods)
- `quirk/scanner/k8s_connector.py` + `quirk/scanner/aws_connector.py` §_scan_eks_encryption — Phase 29 K8s scanner

### Files to Fix (Phase 43 CR Findings)
- `quirk/pdf.py` — CR-02 (ValueError on bad port, lines ~45) + WR-01 (browser.close() not in finally, line ~62)
- `src/dashboard/src/pages/print.tsx` — WR-03 (missing data_in_motion subscore in PDF executive summary)
- `src/dashboard/src/pages/data-at-rest.tsx` — WR-04 (missing scope="col" on TableHead)
- `src/dashboard/src/pages/motion.tsx` — WR-04 (missing scope="col" on TableHead)

### Chaos Lab
- `quantum-chaos-enterprise-lab/docker-compose.yml` — `database`, `vault`, `kerberos`, `saml` profiles and port assignments
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — expected scanner output oracle for each profile

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_chaos_storage.py`: live_infra skip pattern — `@pytest.mark.skipif(not docker_available(), ...)` with skip_registry entry. Copy this pattern for all new chaos lab integration tests.
- `tests/conftest.py` `dashboard_client` fixture: in-memory SQLite with `dependency_overrides[get_db]`. Use this for Phase 31 VERIFICATION seeded-DB tests.
- `tests/test_kerberos_scanner.py:360` + `tests/test_saml_scanner.py:366`: existing live_infra skip entries in skip_registry — new Phase 25 UAT tests can extend these files or parallel them.
- `tests/test_vault_connector.py`: mock-based Vault tests exist; Phase 44 adds integration tests separately, does not modify the mock-based file.

### Established Patterns
- **Skip registry discipline (Phase 41 D-02):** Every `pytest.skip` or `@pytest.mark.skipif` for live infra MUST have a corresponding entry in `tests/skip_registry.py`. The meta-test `tests/test_skip_registry.py` enforces this and will fail CI if a new unregistered skip appears.
- **live_infra skip format:** `(file, line, "live_infra", "Requires {service} chaos lab")` — use the exact category string.
- **Test naming:** `test_<feature_or_module>.py` — e.g., `test_uat_db_integration.py`, `test_uat_vault_integration.py`.
- **No new conftest.py fixtures** unless genuinely shared — keep helpers in the test file.

### Integration Points
- `tests/skip_registry.py` — must be updated whenever a new live_infra test is added
- `.planning/STATE.md` §Deferred Items — update via `gsd-sdk query` (not direct Write) after automation is confirmed
- `docs/UAT-SERIES.md` — add UAT-44-XX entries for each automated scenario at phase close

</code_context>

<specifics>
## Specific Requirements

- Phase 29 cloud-only rationale must be explicit in STATE.md: cite which features require cloud-managed control planes and confirm mock coverage exists.
- Phase 31 VERIFICATION: the seeded DB fixture must produce output that matches the `UAT-9-09` wire format: `current_session_ts`, `previous_session_ts`, `new_high`, `new_medium`, `new_low`, `resolved_high`, `resolved_medium`, `resolved_low` — flat, not nested.
- CR-02 fix: use `try/except ValueError` — do not silently fall back to a default, surface the misconfiguration with a clear error message.
- WR-03 fix: `data_in_motion` is the 6th subscore (added Phase 34); it must appear in the PDF executive summary alongside the other 5 subscores.

</specifics>

<deferred>
## Deferred Ideas

- WR-05: FAIL cosmetic in summary table — exit code is correct; deferred to future cleanup
- WR-06: Hardcoded Chrome binary path in CI YAML — deferred to future CI cleanup phase
- Phase 04/05/07/13/28/31 deferred items (other than Phase 31 VERIFICATION) — not targeted in Phase 44; remain in STATE.md Deferred Items table
- Phase 28 VERIFICATION (cloud-only object storage) — could be trivially closed as `cloud-only` in a future pass but not Phase 44's concern

</deferred>

---

*Phase: 44-uat-debt-automation*
*Context gathered: 2026-05-03*
