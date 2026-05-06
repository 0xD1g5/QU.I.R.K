# Phase 38: Identity API Regression Fix — Context

**Gathered:** 2026-04-29
**Status:** Ready for planning
**Source:** Inline orchestrator clarification (3 questions, all recommendations accepted) — discuss-phase skipped per user directive (small regression-fix phase, requirements locked in REQUIREMENTS.md)

<domain>
## Phase Boundary

This phase closes three v4.4 deferred items (GAP-01, GAP-02, GAP-03) and brings the test suite to a clean green state. Out of scope: any new scanner work, any API-shape changes beyond what's needed to surface SAML/OIDC.

The bug is a **scan-window race** in the implicit-latest branch of `GET /api/scan/latest`, not a missing scanner field or filter. SAML/OIDC scanner output is correctly persisted; it falls outside a 1-second forward window when Kerberos finishes last.

</domain>

<decisions>
## Implementation Decisions (LOCKED)

### D-01: Scan-window fix strategy
- **Replace** the 1-second forward filter on the implicit-latest branch of `quirk/dashboard/api/routes/scan.py:593-608` with a **5-minute backward bracket** from `MAX(scanned_at)`.
- **Bracket value:** `SESSION_BRACKET = timedelta(minutes=5)` — defined as a module-level constant in `scan.py`.
- **Scope:** Fix the *implicit-latest* branch only. The explicit `?scan_id=` branch is untouched.
- **No env-var/config knob this phase** — `QUIRK_SCAN_WINDOW_SECONDS` deferred to Phase 41 (CI Stability) per researcher recommendation.

### D-02: Test suite green-up scope (SC4)
- Phase 38 success criterion 4 requires the full suite at zero failures.
- The pre-existing failure `test_all_completed_phase_validations_nyquist_compliant` (caused by Phases 01–14 missing VALIDATION.md files on disk) **is folded into Phase 38**.
- Resolution path: backfill missing VALIDATION.md stubs OR adjust the hygiene test to skip pre-Nyquist phases — planner decides the cleanest minimal path. Either is acceptable as long as the test goes green.

### D-03: Re-enable SAML scan-window pytest (GAP-02)
- Test today is a **hard failure**, not skip/xfail (REQUIREMENTS.md wording is loose). It will go green automatically once D-01 lands.
- Location: `tests/test_identity_surface.py:464-563`, `Issue3ScanWindowRegressionTest::test_issue3_scan_window_returns_all_identity_protocols`.
- No additional fixture work expected; verify after D-01 lands.

### D-04: Restore 36-VALIDATION.md (GAP-03)
- Recreate from commit `99f48d2` (last-known-good), then flip the matrix to `nyquist_compliant: true, wave_0_complete: true` after D-01/D-02/D-03 pass.
- File path: `.planning/phases/36-*/36-VALIDATION.md` (exact slug TBD by planner from existing dir name).
- Commit message: `docs(36): restore VALIDATION.md and flip wave_0_complete (closes DEF-v4.4-01)`.

### D-05: No scanner / persistence changes
- The Phase 24 SAML/OIDC scanner plumbing is correct. Do **not** touch scanner code, DB schema, or persistence — only the API window query.

### D-06: Mandatory phase completion steps (per CLAUDE.md)
Plans must include explicit tasks for:
- Obsidian phase note: `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-38-Identity-API-Regression-Fix.md` (write to vault filesystem, not via CLI `content=`)
- `docs/UAT-SERIES.md` update (UAT-1-02 if version bumps; identity-scan series for the new green path)
- Sync UAT-SERIES.md to Obsidian vault
- Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs`

### Claude's Discretion
- Exact code shape of the SQL/ORM bracket query (use existing patterns in `scan.py`)
- Whether to add a unit test for the 5-minute bracket itself in addition to the existing scan-window regression test (recommended: yes, one targeted unit test)
- Hygiene-test fix style for D-02 (backfill stubs vs. test skip-list)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Regression site
- `quirk/dashboard/api/routes/scan.py:593-608` — implicit-latest scan-window bug; primary fix site
- `tests/test_identity_surface.py:464-563` — failing regression test that pins the correct behavior

### Validation file (GAP-03)
- Commit `99f48d2` — last-known-good `36-VALIDATION.md` content (use `git show 99f48d2:.planning/phases/36-*/36-VALIDATION.md` to recover)

### Project standards
- `CLAUDE.md` — Mandatory Phase Completion Steps, PEP 8, `python -m compileall`, minimal-diff rules
- `.planning/STATE.md` — DEF-v4.4-01, DEF-v4.4-02 entries to update on completion
- `.planning/REQUIREMENTS.md` — GAP-01/02/03 wording (note: GAP-02 says "skip/xfail to GREEN" but the test is hard-failing — decision D-03 clarifies)

### Research
- `.planning/phases/38-identity-api-regression-fix/38-RESEARCH.md` — full root cause + fix sketch + risk register

</canonical_refs>

<specifics>
## Specific Ideas

- 5-minute bracket: use `timedelta(minutes=5)` — readable, matches typical scan duration spread observed in chaos lab runs.
- Update `STATE.md` Deferred Items table at phase close to mark DEF-v4.4-01 and DEF-v4.4-02 as `closed in Phase 38`.

</specifics>

<deferred>
## Deferred Ideas

- `QUIRK_SCAN_WINDOW_SECONDS` env-var configurability — deferred to Phase 41 (CI-04 candidate).
- Broader audit of other implicit-latest queries in the codebase that might share the same window bug — deferred to Phase 41 (ROBUST-04 audit).

</deferred>

---

*Phase: 38-identity-api-regression-fix*
*Context gathered: 2026-04-29 via inline orchestrator (3 locked decisions from research-driven clarification)*
