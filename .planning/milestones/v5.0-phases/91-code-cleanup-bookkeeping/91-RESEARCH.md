# Phase 91: Code Cleanup + Bookkeeping — Research

**Researched:** 2026-05-22
**Domain:** Python dead-code removal, deprecation fixes, documentation bookkeeping
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (CLEAN-01 / Tier-A):** Apply BACK-53, BACK-55, BACK-56. CI guard: `python -W error::DeprecationWarning -m pytest` passes with zero deprecation-related failures (run with `QUIRK_DB_PATH` set).
- **D-02 (CLEAN-02 / Tier-B):** Delete **only** BACK-49/50/51/52/54. Each deletion is vulture/AST call-graph confirmed (NOT grep). Clean-venv smoke test (`pip install -e . && quirk --version && quirk doctor`) after each Tier-B deletion batch. Tier-A ships before Tier-B.
- **D-02b:** Run repo-wide `vulture` pass and write `dead-code-candidates.md` — WITHOUT deleting anything else. This is a reviewed backlog for a future phase.
- **D-03 (CLEAN-03):** Update VALIDATION.md files affected by v5.0 (BACK-62). Plus carry-ins: (a) add `QUIRK_DB_PATH` autouse fixture to `tests/conftest.py`; (b) remove stale CONCERNS.md §1.11 dual-scoring-engine entry.
- **D-04 (CLEAN-04):** Document JWT `verify=False` inspection-mode behavior with an inline code comment at the call site AND a brief docs note in `docs/operators-guide.md`.

### Claude's Discretion

- Exact files for each BACK item (researcher/vulture determine reachability)
- Precise conftest fixture shape
- Docs location for the JWT note (implementation detail)

### Carried forward (locked)

- Tier-A before Tier-B (v5.0-D-06)
- Clean-venv smoke test after each Tier-B batch
- Vulture/AST not grep for reachability

### Deferred Ideas (OUT OF SCOPE)

- Opportunistic dead-code beyond BACK-49/50/51/52/54
- BACK-A11Y-01 (dashboard a11y baselines)
</user_constraints>

---

## Summary

Phase 91 closes the code cleanup and bookkeeping requirements for the v5.0 stabilization milestone. The central research finding is that **several BACK items are partially or fully resolved already** by prior phases — the planner must not re-do completed work but must resolve the remaining gaps. Tier-A (CLEAN-01) has one real item left: fix `datetime.utcnow()` in `tests/test_dashboard_scan_history.py` (9 occurrences) to unblock the deprecation-as-error CI gate; the production `quirk/` code is already clean. Tier-B (CLEAN-02) has two real deletion targets: `_extract_cert_key_type` in `quirk/reports/writer.py` (confirmed dead by vulture) and `quirk/intelligence/schema.py` (test-only dataclasses, not instantiated in production). Both require deleting their corresponding test files too. BACK-53, BACK-49, BACK-51, and most of BACK-52 were already resolved in previous phases and need only CONCERNS.md cleanup.

The carry-in D-03a (conftest DB isolation) is confirmed unimplemented: `tests/conftest.py` exists but has no `QUIRK_DB_PATH` autouse fixture, causing 7 test modules to fail collection without the env var. D-03b (CONCERNS.md §1.11) refers to the §4.1 dual-scoring-engine section — no §1.11 exists; the actual target is §4.1 (and associated §4.2, §4.3, §4.4 which are all stale). The BACK-58 JWT advisory in `jwt_scanner.py` already has a good function-level docstring; the gap is only an inline comment at the `httpx.get` call sites (lines 73, 88) and a docs note in `docs/operators-guide.md`.

**Primary recommendation:** Sequence Tier-A as one plan (BACK-55 comment sweep + BACK-56 test fix + CONCERNS.md bookkeeping + VALIDATION.md updates + conftest fixture + JWT advisory) then Tier-B as a second plan (vulture-confirm _extract_cert_key_type + schema.py deletions + D-02b vulture report). This matches v5.0-D-06 sequencing.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dead-code deletion | Python source | tests/ | Pure source changes; no API or DB migration |
| Deprecation fix | tests/ source | quirk/ (already clean) | utcnow() only in test files now |
| Comment/version-tag cleanup | Python source (quirk/) | docs/ | Cosmetic source cleanup |
| Conftest DB isolation | tests/ | quirk/dashboard/api/deps.py | Fixture intercepts env-var path before deps.py resolver |
| CONCERNS.md bookkeeping | .planning/codebase/ | — | Planning artifact only |
| VALIDATION.md updates | .planning/phases/ | — | Planning artifact only |
| JWT advisory | quirk/scanner/jwt_scanner.py | docs/operators-guide.md | Two surfaces: code + operator docs |

---

## BACK Item Resolution Status

### BACK-49 — `quirk/engine/rules.py`

**Status: ALREADY DELETED.** [VERIFIED: git log shows no file at that path in current tree]

- `quirk/engine/rules.py` does not exist. It was a single-comment stub (`# Reserved for future: load YAML rules…`) and was removed in a prior cleanup.
- No imports reference `quirk.engine.rules` anywhere in the codebase.
- **Remaining work for Phase 91:** Remove stale CONCERNS.md §1.2 entry (it describes a file that no longer exists).

### BACK-50 — Dead helper functions in `writer.py` + orphaned `scorecard.py`

**Status: PARTIALLY RESOLVED.** [VERIFIED: file inspection + vulture 2.16]

The original 5 dead functions named in CONCERNS §1.4 (`_count_findings`, `_extract_cert_dates`, `_is_self_signed`, `_mtls_present`, plus an early `_extract_cert_key_type`) were replaced in rewrites. `quirk/reports/scorecard.py` is also already deleted (confirmed by filesystem search; BACK-61 reference in ROADMAP confirms it).

**One target remains:**
- `quirk/reports/writer.py:73` — `_extract_cert_key_type()` is defined but **never called in production**. Vulture 2.16 confirms: `unused function '_extract_cert_key_type' (60% confidence)`. It is only imported and tested by `tests/test_cert_pubkey_fix.py`. The CBOM builder (`quirk/cbom/builder.py`) reads `ep.cert_pubkey_alg` directly without using this helper.
- `tests/test_cert_pubkey_fix.py` — must be deleted when the function is removed (tests a dead function).
- There is also an unused import: `writer.py:9` — `RichText` from `rich.text` — flagged at 90% confidence by vulture, not called anywhere.

**Deletion reachability:** No dynamic imports, no `__init__` re-exports, no optional-extra path references `_extract_cert_key_type`. Safe to delete. [VERIFIED: grep + vulture + __init__.py inspection]

**Remaining work for Phase 91:**
1. Delete `_extract_cert_key_type()` from `quirk/reports/writer.py` (lines 73–88).
2. Delete the unused `RichText` import at `writer.py:9`.
3. Delete `tests/test_cert_pubkey_fix.py`.
4. Remove stale CONCERNS.md §1.4 and §1.8 entries.

### BACK-51 — `migration_planner.py` dual categorization

**Status: ALREADY DELETED.** [VERIFIED: filesystem + writer.py:35-56 comment]

`quirk/engine/migration_planner.py` was deleted and its `categorize_waves()` function inlined directly into `quirk/reports/writer.py` (lines 35–56, with a comment citing the Phase 83 CLEAN-01 action). No import conflicts.

**Remaining work for Phase 91:** Remove stale CONCERNS.md §1.3 entry.

### BACK-52 — Dead intelligence modules: `driver_text`, `calibration`, schema dataclasses

**Status: PARTIALLY RESOLVED.** [VERIFIED: filesystem inspection]

- `quirk/intelligence/driver_text.py` — DELETED.
- `quirk/intelligence/calibration.py` — DELETED.
- `quirk/intelligence/schema.py` — **EXISTS** and is the only remaining target.

`schema.py` defines five frozen dataclasses (`ScoreInputs`, `ScoreResult`, `ConfidenceResult`, `RoadmapItem`, `IntelligenceReport`) exported via `quirk/intelligence/__init__.py`. Production code (`scoring.py`, `confidence.py`, `roadmap.py`, `writer.py`, `executive.py`) returns plain dicts and never instantiates any of these classes. They are only used in `tests/test_intelligence_schema.py`.

Vulture confirms: `unused class 'IntelligenceReport' (60% confidence)`, `unused method 'to_json' (60% confidence)`.

**Deletion reachability:** No production module imports from `quirk.intelligence.schema` directly. The `__init__.py` re-exports them, but no production caller uses the exported names. Optional-extra paths (`[adcs]`, `[motion]`, etc.) do not reference schema. [VERIFIED: grep across quirk/]

**Remaining work for Phase 91:**
1. Delete `quirk/intelligence/schema.py`.
2. Remove the schema re-exports from `quirk/intelligence/__init__.py` (lines 5–11, 15–24).
3. Delete `tests/test_intelligence_schema.py`.
4. Remove stale CONCERNS.md §1.5, §1.6, §1.7 entries.

**NOTE on `quirk/intelligence/trends.py`:** This file IS actively imported by production code (`quirk/dashboard/api/routes/scan.py:45` and `quirk/dashboard/api/routes/trends.py:31`). It is NOT dead and must NOT be deleted.

### BACK-53 — `data/qcscan-legacy.sqlite`

**Status: ALREADY DELETED.** [VERIFIED: filesystem — `data/` contains only `quirk.db` and empty `_archive/`; git log confirms removal in commit 708402b]

**Remaining work for Phase 91:** Remove stale CONCERNS.md §6.1 entry.

### BACK-54 — `tqdm = None` dead branch and dependency audit

**Status: DEAD BRANCH ALREADY REMOVED.** [VERIFIED: grep found zero `tqdm = None` assignments in run_scan.py; git log confirms removal pre-v4.10]

The `tqdm = None; if tqdm:` dead branch described in CONCERNS §6.2 was cleaned up in an early phase. Current state:

- `quirk/logging_util.py` uses a **legitimate** lazy `from tqdm import tqdm` inside `__init__` (lines 19–25) when `use_tqdm=True` is passed (for `--progress` CLI flag). This is not dead code.
- `tqdm>=4.67` in `pyproject.toml` line 15 is a **live production dependency** because tqdm IS used via the `--progress` flag path.
- There is NO reason to remove tqdm from hard deps; it is actively installed and conditionally used.

**Remaining work for Phase 91:** Remove stale CONCERNS.md §6.2 entry. No code deletion needed.

### BACK-55 — Stale comments (D-reference tickets and version tags)

**Status: ACTIVE — NEEDS CLEANUP.** [VERIFIED: grep across quirk/]

The CONCERNS §6.3 concern has two sub-categories:

**1. Version tags in GENERATED CLIENT REPORTS** — already fixed:
- `quirk/reports/technical.py:55` now emits `"## TLS Capabilities"` (without `(v3.6)`). [VERIFIED]

**2. Version tags and D-references in CODE COMMENTS** — still present:

Files with `v3.x` / `v4.x` version-era comments:

| File | Lines | Comments |
|------|-------|----------|
| `quirk/models.py` | 41, 53, 58, 66, 75, 80, 86, 92 | `# v3.6 TLS capability fields`, `# v4.0 SSH audit fields`, etc. |
| `quirk/db.py` | 173–175 | `# v4.2 identity`, `# v4.3 GCP`, `# v4.3 DAT` inline comments |
| `quirk/scanner/tls_scanner.py` | 441 | `# v3.6 TLS capability enum` |

Files with version strings in USER-VISIBLE PRINTED OUTPUT:

| File | Line | Content |
|------|------|---------|
| `quirk/assessment/operator_context.py` | 33 | `print("\n🧠 Assessment Context (v3.5.1)")` — printed to stdout during interactive mode |
| `quirk/scanner/fingerprint.py` | 138 | `Protocol classifier v3.7.3` — in a docstring (not printed, low urgency) |
| `quirk/engine/findings_evaluator.py` | 343 | `v3.7.1 classifier patch companion:` — in a comment block |

The `operator_context.py` stdout print with `v3.5.1` is the highest priority: it is user-visible and reports a false version.

The 441 `# D-NN` / `# Phase NN D-NN` internal planning comments in `config.py` and other files are widespread. BACK-55 scope is the WORST examples from CONCERNS §6.3 (those listed above), not wholesale removal of all Phase/D-ref comments.

**Remaining work for Phase 91:**
1. Remove/replace `# v3.x`, `# v4.x` era-tagging comments in `models.py`, `db.py`, `tls_scanner.py`.
2. Fix `operator_context.py:33` — remove `(v3.5.1)` from the printed string.
3. Clean the `fingerprint.py` and `findings_evaluator.py` version references in docstrings/comments.

### BACK-56 — `datetime.utcnow()` deprecation

**Status: PRODUCTION CODE CLEAN; TEST CODE NEEDS FIX.** [VERIFIED: grep]

Production `quirk/` code is already clean:
- `quirk/logging_util.py:82–83` uses `datetime.now(timezone.utc)` (already fixed).
- `quirk/discovery/nmap_provider.py:74` uses `datetime.now(timezone.utc)` (already fixed).
- `quirk/cli/qramm_cmd.py:9` contains the string `datetime.utcnow()` only in a comment ("Per Phase 51 DEBT-01, no datetime.utcnow()").

**Remaining targets:**

| File | Count | Type |
|------|-------|------|
| `tests/test_dashboard_scan_history.py` | 9 occurrences (lines 71, 95, 115, 156, 191, 223, 248, 286, 314) | Test code |
| `quantum-chaos-enterprise-lab/jwt/algnone/main.py` | 1 | Lab Docker container (not quirk core) |
| `quantum-chaos-enterprise-lab/jwt/rsa1024/main.py` | 1 | Lab Docker container |
| `quantum-chaos-enterprise-lab/jwt/hs256/main.py` | 1 | Lab Docker container |
| `quantum-chaos-enterprise-lab/jwt/rs256/main.py` | 1 | Lab Docker container |

**CI gate status:** `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -x` FAILS immediately at line 71. [VERIFIED: live test run]

The chaos-lab JWT containers use `datetime.datetime.utcnow()` for token generation. These are standalone Docker images not part of the quirk package — they do not run under pytest and do not trigger the DeprecationWarning gate. They are OUT OF SCOPE for CLEAN-01 (no CI failure, not part of quirk/ package).

**Remaining work for Phase 91:**
- Fix `tests/test_dashboard_scan_history.py`: replace all 9 `datetime.utcnow()` calls with `datetime.now(timezone.utc)` and add `from datetime import timezone` if not already present.
- Chaos-lab JWT files: OUT OF SCOPE (not quirk package, not CI-gated).

### BACK-58 — JWT `verify=False` advisory (CLEAN-04)

**Status: NEEDS DOCUMENTATION.** [VERIFIED: file inspection]

After Phase 57 (HARDEN-SCAN-01), the JWT scanner was refactored to use `verify_tls: bool = True` parameter (not hardcoded `verify=False`). The parameter is passed through to `httpx.get` at:

- `quirk/scanner/jwt_scanner.py:73` — `resp = httpx.get(url, ..., verify=verify_tls)`
- `quirk/scanner/jwt_scanner.py:88` — `resp2 = httpx.get(jwks_uri, ..., verify=verify_tls)`

The `scan_jwt_endpoint()` docstring (lines 116–117) already explains: "When allow_insecure_jwks=True, TLS certificate verification is disabled for JWKS fetches (verify_tls=False)." The `ADVISORY_JWKS_VERIFY_DISABLED` sentinel is emitted when the insecure path is used.

**What's missing:**
1. No inline comment at the `httpx.get` call sites (lines 73, 88) explaining why `verify=verify_tls` is used and what the threat model is.
2. No operator-facing documentation in `docs/operators-guide.md` explaining that `allow_insecure_jwks: true` disables TLS verification and when an operator should use it.
3. `docs/configuration.md` does not document `allow_insecure_jwks` at all (the key exists in `quirk/config.py:310` and is accepted by `run_scan.py:67`).

**BACK-58 scope:** Add a `# WHY:` comment block above the `httpx.get` calls in `_fetch_jwks()` (following the pattern established by Phase 77 D-01 / IN-01 for tls_capabilities.py). Add a security note to `docs/operators-guide.md` §6 near the JWT scanner entry. Optionally document `allow_insecure_jwks` in `docs/configuration.md`.

---

## CLEAN-03 Carry-In Details

### D-03a — Conftest DB Isolation

**Status of conftest.py:** EXISTS but missing the autouse fixture. [VERIFIED: file inspection]

`tests/conftest.py` currently has:
- SHA1 signing compatibility shim (for vault_connector tests with OpenSSL 3.x)
- `dashboard_client()` fixture with in-memory SQLite override

**What is missing:** An autouse fixture that sets `QUIRK_DB_PATH` to an isolated path so the suite never calls `_default_db_path()` in `quirk/dashboard/api/deps.py`.

**The bug it fixes:** `_default_db_path()` at `quirk/dashboard/api/deps.py:12–33` raises `ValueError: Multiple QU.I.R.K. DBs found` when multiple `.db` files exist in candidate paths. This causes 7 test modules to fail collection when run without `QUIRK_DB_PATH` set:

- `tests/test_api_auth.py`
- `tests/test_api_scan_window.py`
- `tests/test_dashboard_scan_history.py`
- `tests/test_jobs_api.py`
- `tests/test_qramm_evidence_bridge.py`
- `tests/test_qramm_multiplier.py`
- `tests/test_schedules_api.py`

**Recommended fixture shape** (Claude's discretion):

```python
@pytest.fixture(autouse=True)
def _isolate_quirk_db(tmp_path, monkeypatch):
    """CLEAN-03 D-03a: Point QUIRK_DB_PATH at an isolated tmp_path DB.

    Prevents _default_db_path() in quirk/dashboard/api/deps.py from raising
    'Multiple QU.I.R.K. DBs found' when stale scan DBs exist in the working tree.
    Applies to ALL tests automatically; does not affect tests that mock get_db.
    """
    monkeypatch.setenv("QUIRK_DB_PATH", str(tmp_path / "quirk_test.db"))
```

**Note:** This is NOT the same as the `dashboard_client()` fixture which overrides `get_db` via FastAPI dependency injection. The autouse fixture works at the env-var level and is simpler/broader. The existing `dashboard_client()` fixture should be kept as-is.

### D-03b — CONCERNS.md Stale Entry Removal

**The §1.11 reference:** CONTEXT.md says "CONCERNS.md §1.11 dual-scoring-engine entry" but CONCERNS.md has only sections §1.1 through §1.8. The intended target is **§4.1 ("Two Parallel Scoring Systems")** and its companion sections §4.2, §4.3, §4.4 — which together constitute the "dual-scoring-engine" concern.

**Why §4.1–§4.4 are now stale:** [VERIFIED: file inspection]

- `quirk/assessment/readiness_score.py` — DELETED (only `migration_advisor.py` and `operator_context.py` remain in `assessment/`).
- Both `quirk/reports/executive.py` and `quirk/reports/writer.py` now import `compute_readiness_score` from `quirk.intelligence.scoring` (single engine). [VERIFIED: grep]
- `quirk/assessment/confidence.py` — DELETED.
- `quirk/assessment/transition_planner.py` — DELETED.
- `quirk/reports/scorecard.py` — DELETED.

**Additional stale entries discovered** (all confirmed by filesystem):

| Section | Describes | Current Status |
|---------|-----------|----------------|
| §1.1 | `quirk/connectors/` directory | DELETED |
| §1.2 | `quirk/engine/rules.py` | DELETED |
| §1.3 | `quirk/engine/migration_planner.py` | DELETED |
| §1.4 | 5 dead functions in `writer.py` | MOSTLY DELETED (only `_extract_cert_key_type` remains, targeted by BACK-50) |
| §1.6 | `intelligence/driver_text.py` | DELETED |
| §1.7 | `intelligence/calibration.py` | DELETED |
| §1.8 | `reports/scorecard.py` | DELETED |
| §4.1 | Dual scoring systems | RESOLVED (single engine) |
| §4.2 | Dual confidence engines | RESOLVED |
| §4.3 | Dual roadmap builders | RESOLVED |
| §4.4 | Dual interpretation engines | RESOLVED |
| §6.1 | `data/qcscan-legacy.sqlite` | DELETED |
| §6.2 | `tqdm = None` dead branch | REMOVED |

**D-03b scope:** Remove/mark-resolved all the above sections. The planner should decide whether to delete these sections outright or add a `**Resolved:**` annotation.

### D-03b — VALIDATION.md Updates (BACK-62)

**Phases needing VALIDATION.md update:** [VERIFIED: grep for nyquist_compliant: false]

| Phase | Location | Current Status | Action |
|-------|----------|----------------|--------|
| 87-dependency-hygiene | `.planning/phases/87-dependency-hygiene/87-VALIDATION.md` | `nyquist_compliant: false`, `wave_0_complete: false`, `status: draft` | Update to `true`/`true`/`complete` |
| 88-scoring-residuals | `.planning/phases/88-scoring-residuals/88-VALIDATION.md` | `nyquist_compliant: false`, `wave_0_complete: false`, `status: draft` | Update to `true`/`true`/`complete` |
| 89-chaos-lab-profiles | `.planning/phases/89-chaos-lab-profiles/89-VALIDATION.md` | `nyquist_compliant: false`, `wave_0_complete: false`, `status: draft` | Update to `true`/`true`/`complete` |
| 90-oqs-nginx-pqc-hybrid | `.planning/phases/90-oqs-nginx-pqc-hybrid/` | NO VALIDATION.md (has VERIFICATION.md only) | Create `90-VALIDATION.md` |

**INFRA-03 status:** `test_infra03_nyquist_coverage.py` passes 18/18. [VERIFIED: live run] INFRA-03 tests scanner coverage (email/kafka/redis/rabbitmq), not VALIDATION.md frontmatter — it is not blocked by this cleanup.

**test_hygiene.py HYGN-04:** Only checks phases 01–14 in `.planning/phases/` (hardcoded `COMPLETED_PHASES` list). v5.0 phases 87–90 are NOT in this list and NOT checked by HYGN-04. The planner may optionally extend `COMPLETED_PHASES` to include the v5.0 slugs to gate future regressions.

**Older milestone VALIDATION.md files:** 13 files in `.planning/milestones/v4.x-phases/` also have `nyquist_compliant: false`. These are NOT checked by any test and are OUT OF SCOPE for Phase 91 (only v5.0 phases are "affected by v5.0").

---

## Vulture D-02b Report Preview

**Tool:** vulture 2.16 [VERIFIED: slopcheck [OK], PyPI registry confirmed]
**Install:** `pip install vulture` (not in pyproject.toml dev deps; add to phase Wave 0)
**Command for D-02b report:** `vulture quirk/ --min-confidence 60 > dead-code-candidates.md`

**At 80%+ confidence (high-signal, actionable):**

| Location | Finding | Confidence | Notes |
|----------|---------|------------|-------|
| `quirk/reports/writer.py:9` | Unused import `RichText` | 90% | Not called anywhere |
| `quirk/scanner/azure_connector.py:22` | Unused import `CertificateClient` | 90% | try/except import block |
| `quirk/scanner/gcp_connector.py:27` | Unused import `DefaultCredentialsError` | 90% | try/except import block |
| `quirk/scanner/k8s_connector.py:37` | Unused import `ApiException` | 90% | try/except import block |
| `quirk/scanner/k8s_connector.py:75` | Unused import `_AKSClient` | 90% | try/except import block |
| `quirk/reports/html_renderer.py:110` | Unreachable `else` expression | 100% | Structural dead branch |
| `quirk/cli/scheduler_cmd.py:29` | Unused variables `frame`, `signum` | 100% | Signal handler params |

**At 60%+ confidence (includes scanner entry points — mostly false positives):**
255 total findings. The bulk are scanner entry-point functions (`scan_*_targets`) flagged because vulture cannot see `run_scan.py`'s dynamic dispatch. These are NOT dead and must NOT be in the deletion list. The 60% report is for the `dead-code-candidates.md` catalogue (D-02b), not an action list.

---

## Package Legitimacy Audit

> This phase installs `vulture` as a temporary dev tool for the D-02b report.

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| `vulture` | PyPI | [OK] | Approved — legitimate static analysis tool |

**Verified version:** 2.16 (latest as of 2026-05-22) [VERIFIED: pip index versions]
**No postinstall scripts.** [ASSUMED: standard pure-Python tool]

No new runtime packages are added to `pyproject.toml`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dead-code detection | grep + manual search | `vulture quirk/ --min-confidence 80` | grep misses dynamic imports, `__init__` re-exports, optional-extra paths |
| Reachability for deletion | "it looks unused" inspection | `vulture` AST + confirmed grep for `__init__` re-exports | QUIRK has optional extras and dynamic scanner registration that hide callers |
| DB isolation in tests | Per-test `os.environ["QUIRK_DB_PATH"]` in each test | Autouse `monkeypatch.setenv` fixture in `conftest.py` | Single fix eliminates all 7 collection errors simultaneously |

---

## Common Pitfalls

### Pitfall 1: Deleting schema.py Without Updating `__init__.py`

**What goes wrong:** If `schema.py` is deleted but `quirk/intelligence/__init__.py` still re-exports `ScoreInputs`, `ScoreResult`, `ConfidenceResult`, `RoadmapItem`, `IntelligenceReport` — any `import quirk.intelligence` will raise `ImportError`.

**How to avoid:** Delete schema.py AND update `__init__.py` in the same commit. Remove the 7 affected lines from `__init__.py` (lines 5–11 imports and lines 15–24 `__all__` entries).

### Pitfall 2: Assuming BACK-49/51/53 Are Active Tasks

**What goes wrong:** Planner creates tasks to delete files that are already gone.

**How to avoid:** All three are already deleted. The only remaining action for each is updating the corresponding CONCERNS.md section to reflect the resolved state.

### Pitfall 3: Fixing `utcnow()` in Chaos-Lab JWT Containers

**What goes wrong:** Treating the 4 occurrences in `quantum-chaos-enterprise-lab/jwt/*/main.py` as part of BACK-56 scope.

**How to avoid:** These are standalone Docker container entry points, not part of the `quirk` package. They do NOT run under pytest and do NOT trigger the `DeprecationWarning` CI gate. Leave them unchanged.

### Pitfall 4: Local-Import Shadow Trap When Fixing `datetime.utcnow()`

**What goes wrong:** Adding `from datetime import timezone` inside a function branch where it is already imported at module scope — this makes `timezone` function-local for the entire function (Python compile-time scoping), silently breaking unrelated branches.

**How to avoid:** Add `timezone` to the EXISTING `from datetime import datetime, timedelta` import line at the top of `test_dashboard_scan_history.py` (line 13). Do not add a second import inside a function.

### Pitfall 5: Vulture False Positives for Scanner Entry Points

**What goes wrong:** Treating vulture's 60% findings on `scan_*_targets` functions as dead code and deleting them.

**How to avoid:** Scanner entry points are called from `run_scan.py` by name lookup (not discoverable by vulture's AST analysis). Always verify with a grep of `run_scan.py` before deleting any scanner function.

### Pitfall 6: Conftest Fixture Breaking `dashboard_client()`

**What goes wrong:** The autouse `QUIRK_DB_PATH` env var fixture conflicts with tests that override `get_db` via FastAPI dependency injection (like `dashboard_client()`).

**How to avoid:** The `dashboard_client()` fixture uses `app.dependency_overrides[get_db]` which bypasses `_default_db_path()` entirely. The autouse env-var fixture is harmless for those tests — `monkeypatch.setenv` is still safe even if the path is never consulted.

---

## Validation Architecture

> `workflow.nyquist_validation: true` in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version from `.venv`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/test_dashboard_scan_history.py tests/test_hygiene.py tests/test_infra03_nyquist_coverage.py tests/test_cert_pubkey_fix.py tests/test_intelligence_schema.py -x -q` |
| Deprecation gate | `QUIRK_DB_PATH=/tmp/quirk91.db python -W error::DeprecationWarning -m pytest tests/ -q` |
| Full suite command | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/ -v` |

### Observable Success Signals

| Signal | What to Run | Expected Outcome |
|--------|-------------|-----------------|
| Deprecation-as-error gate passes | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -q` | All tests PASS (was failing at line 71) |
| Collection errors gone | `python -m pytest tests/ --collect-only -q` (NO QUIRK_DB_PATH) | 0 collection errors (was 7) |
| Tier-B deletions verified dead | vulture on writer.py, schema.py before deletion | Zero production callers confirmed |
| Clean-venv smoke test | `pip install -e . && quirk --version && quirk doctor` | No import errors |
| Full suite no regression | `QUIRK_DB_PATH=/tmp/quirk91.db python -m pytest tests/ -q` | No NEW failures vs pre-phase baseline |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| CLEAN-01 | `datetime.utcnow()` eliminated from test suite | unit | `python -W error::DeprecationWarning -m pytest tests/test_dashboard_scan_history.py -x -q` |
| CLEAN-01 | No stale D-ref/version comments in generated output | manual review | `grep -n "v3\." quirk/assessment/operator_context.py` |
| CLEAN-02 | `_extract_cert_key_type` and schema.py deleted | unit | `python -m pytest tests/ -q --collect-only` (confirms test files removed) |
| CLEAN-02 | vulture D-02b report created | manual | File existence: `docs/dead-code-candidates.md` |
| CLEAN-03 | Collection errors eliminated | integration | `python -m pytest tests/ --collect-only -q` (no QUIRK_DB_PATH) |
| CLEAN-03 | VALIDATION.md frontmatter updated | manual | `grep nyquist_compliant .planning/phases/87*/87-VALIDATION.md` |
| CLEAN-04 | JWT advisory comment present | manual | `grep -n "WHY:\|inspection.mode\|MITM" quirk/scanner/jwt_scanner.py` |
| CLEAN-04 | Docs note present | manual | `grep -n "allow_insecure_jwks\|verify" docs/operators-guide.md` |

### Wave 0 Gaps

- [ ] `vulture` not in `pyproject.toml` dev deps — add for D-02b execution: `pip install vulture`
- [ ] Phase 91 `VALIDATION.md` — created as part of this phase
- [ ] `tests/conftest.py` autouse fixture — implemented in this phase (Plan 91-01 Tier-A)

---

## Environment Availability

| Dependency | Required By | Available | Version | Notes |
|------------|------------|-----------|---------|-------|
| Python 3.11+ | All | Yes | 3.14 (venv) | OK |
| pytest | All | Yes | venv install | OK |
| vulture | D-02b report | No (system) | 2.16 on PyPI | Install via `pip install vulture` in dev session |
| `quirk` package | Smoke test | Yes | editable install | `pip install -e .` |

**Missing dependencies with no fallback:**
- vulture (needed for D-02b report and Tier-B reachability confirmation)

---

## Security Domain

> `security_enforcement` not set to `false` in config — security domain applies.

### Applicable ASVS Categories

| ASVS Category | Applies | Notes |
|---------------|---------|-------|
| V2 Authentication | No | No auth changes |
| V3 Session Management | No | No session changes |
| V4 Access Control | No | No access control changes |
| V5 Input Validation | No | Dead-code removal only |
| V6 Cryptography | Indirectly | BACK-58 documents the intentional `verify=False` inspection-mode; no cryptographic behavior changes |

### BACK-58 Threat Model (for advisory wording)

The `allow_insecure_jwks` flag disables TLS certificate verification for JWKS endpoint fetches. This is intentionally accepted for an inspection-mode scanner:

- **Accepted risk:** MITM attack on JWKS URI would inject attacker-supplied key material; scanner would report it as legitimate keys.
- **Why acceptable:** The scanner is a passive inventory tool running in a controlled assessment environment, not a relying-party verifying tokens for auth decisions.
- **Mitigations already in place:** (1) `allow_insecure_jwks: false` is the default — operators must explicitly opt in; (2) When enabled, a `HIGH` advisory `CryptoEndpoint` with `service_detail=ADVISORY_JWKS_VERIFY_DISABLED` is always emitted (Phase 57 / CR-01); (3) `validate_external_url()` still runs on JWKS URIs.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chaos-lab JWT container `utcnow()` calls do NOT need fixing for the CLEAN-01 CI gate | BACK-56 | If somehow included in the pytest run, would need fixing too — but lab containers have no pytest integration |
| A2 | The 39 pre-existing test failures baseline is unchanged since Phase 88 | Validation | If new failures appeared in Phase 89/90, the "no new failures" gate needs recalibration |

---

## Open Questions (RESOLVED)

1. **Should older milestone VALIDATION.md files (phases 38, 41, 42, 52, 55, 59, 63–66, 68, 70) be updated?**
   - What we know: 13 files in `.planning/milestones/v4.x-phases/` have `nyquist_compliant: false`; none are checked by any CI test.
   - What's unclear: Is "affected by v5.0" scoped to just v5.0 phases (87–90) or all stale files?
   - Recommendation: Scope to v5.0 phases only (87–90) per D-03 literal wording. Leave milestone files for a future archival sweep.

2. **Should `test_hygiene.py` COMPLETED_PHASES be extended to include v5.0 slugs?**
   - What we know: HYGN-04 only checks 01–14 which have no VALIDATION.md on disk, so the test is a no-op for the current `.planning/phases/` dir.
   - What's unclear: This was not explicitly asked for in D-03.
   - Recommendation: Add it as a discretion task — small effort, high CI value for future phases.

3. **Should `quirk/intelligence/schema.py` be deleted or kept as a public API surface?**
   - What we know: Not used in production; only tested; BACK-52 explicitly lists it for removal.
   - Recommendation: Delete per D-02 locked decision. The dataclasses represent an unimplemented typed API.

---

## Sources

### Primary (HIGH confidence)
- Live filesystem inspection — all file existence/deletion claims verified by `ls`, `find`, `grep`
- `vulture 2.16` run on `quirk/` — dead-code findings [VERIFIED: tool output]
- `pytest` live run — deprecation-as-error failure and collection errors [VERIFIED: tool output]
- CONTEXT.md decisions D-01..D-04 — scope locked by user

### Secondary (MEDIUM confidence)
- ROADMAP.md backlog table — BACK item definitions
- CONCERNS.md — original issue descriptions (cross-referenced against current codebase)
- Git log — historical deletion evidence for BACK-49, BACK-51, BACK-53, BACK-54

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- BACK item status: HIGH — filesystem-verified for each item
- Vulture findings: HIGH — tool output, 2.16 release
- VALIDATION.md scope: HIGH — grep confirmed all files
- D-03a conftest shape: MEDIUM — recommended pattern, not yet run to confirm no fixture interaction issues

**Research date:** 2026-05-22
**Valid until:** 2026-06-21 (stable domain; Python deprecation timeline is fixed)
