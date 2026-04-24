---
phase: 25-identity-findings-accuracy
fixed_at: 2026-04-24T23:36:28Z
review_path: .planning/phases/25-identity-findings-accuracy/25-REVIEW.md
iteration: 1
fix_scope: critical_warning
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 25: Code Review Fix Report

**Fixed at:** 2026-04-24T23:36:28Z
**Source review:** .planning/phases/25-identity-findings-accuracy/25-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Certificate sort raises TypeError on naive datetimes

**Files modified:** `quirk/dashboard/api/routes/scan.py`
**Commit:** ffdf310
**Applied fix:** Replaced the inline sort lambda (`lambda c: c.cert_not_after or datetime.max.replace(tzinfo=timezone.utc)`) with a named helper function `_cert_expiry_key` inserted just before the `get_latest_scan` route handler. The helper normalises any timezone-naive `cert_not_after` datetime to UTC before comparison, preventing `TypeError: can't compare offset-naive and offset-aware datetimes` at runtime.

### WR-02: SAML branch size check fires for OIDC-safe algorithms when cert_pubkey_size is set

**Files modified:** `quirk/dashboard/api/routes/scan.py`
**Commit:** ffdf310 (committed together with WR-01 — both edits are in scan.py)
**Applied fix:** Added `alg not in OIDC_ALG_SEVERITY and` as an explicit guard at the start of the `elif size < 2048` branch (line 266). This prevents OIDC-safe algorithms (e.g. `ES256`, `HS256`, `EdDSA`) from falling through to the RSA weak-key check and emitting a spurious CRITICAL finding with an incorrect RSA remediation message.

### WR-03: pyproject.toml test uses relative path — fragile in non-root CWD

**Files modified:** `tests/test_identity_findings_accuracy.py`
**Commit:** 48273b1
**Applied fix:** Replaced the bare `pathlib.Path("pyproject.toml")` with a repo-root-anchored path: `_REPO_ROOT = pathlib.Path(__file__).parent.parent` followed by `(_REPO_ROOT / "pyproject.toml").read_text(...)`. This resolves correctly regardless of the process CWD, making the test reliable in CI and IDE runners.

## Skipped Issues

None

---

_Fixed: 2026-04-24T23:36:28Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
