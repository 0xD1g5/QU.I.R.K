# Plan 86-03 — Release Engineering + Operator UAT — SUMMARY

**Phase:** 86 — Scoring Correctness Hotfix
**Plan:** 86-03 (Wave 3)
**Status:** Complete
**Completed:** 2026-05-22
**Mode:** mvp (vertical-slice phase closeout)

---

## Goal

Bump version to v4.10.1, document the scoring-correctness fix in operator-facing release notes, and verify end-to-end that the live dashboard now displays scores correctly through a human-operator walkthrough against the canonical `tls-cert-defects` chaos lab profile.

## Requirements Satisfied

- **RELEASE-01** — Changelog entry documenting scoring-correctness fix with canonical 25+25+23+3+25+19 → 100→80 before/after example and visual-jump note for old stored scores. Penalty math unchanged. ✓
- **RELEASE-02** — `pyproject.toml [project.version]` bumped from `4.10.0` to `4.10.1`. Version single-source-of-truth invariant preserved. ✓

## Tasks Completed

| # | Task | Commit |
|---|------|--------|
| 1 | Version bump (pyproject 4.10.0 → 4.10.1) + changelog fragment with canonical before/after example | `94ac361` |
| 2 | Author HUMAN-UAT.md + stage chaos-lab targets file at `quantum-chaos-enterprise-lab/uat-targets-86.txt` | `34eb1f9` |
| 3 | Operator walks live dashboard against `tls-cert-defects` profile; signs HUMAN-UAT.md result | (this commit) |
| 4 | Finalize phase artifacts — SUMMARY.md, STATE.md/ROADMAP update | (this commit) |

## Operator UAT Result

**Result:** PASS

- **Criterion 1 (Overall < 100, non-EXCELLENT):** PASS — overall score on the live `tls-cert-defects` scan rendered correctly, no longer pegged at 100/EXCELLENT.
- **Criterion 2 (Six subscore radials match fraction-of-25):** PASS *(after hard browser refresh)*. Initial attempt produced screenshot `uat-86-hf1.png` showing the pre-fix red gauges — diagnosed live as a stale browser bundle: the dashboard tab was open against the pre-rebuild static assets even though `quirk/dashboard/static/` had been refreshed by commit `620e5db`. Hard refresh (Cmd+Shift+R) produced the correctly-colored gauges in `uat-86-hf2.png`. Hygiene=25 → green; Agility=3 → red; mid-range → amber.
- **Criterion 3 (Data at Rest tab parity):** PASS — standalone Data at Rest tab gauge matches the Executive Summary subscore radial both in numeric value and color (the iter-1 plan-checker BLOCKER fix carrying its weight).
- **Criterion 4 (Screenshots captured):** PASS — evidence stored as `uat-86-hf1.png` (pre-hard-refresh, diagnostic) and `uat-86-hf2.png` (post-hard-refresh, canonical fix-verified).

## Lessons Captured

The browser-cache trap is a sibling to the `npm run build` rebuild trap already documented in durable memory `feedback_dashboard_build_required.md`. The memory's "tell them to hard refresh (Cmd+Shift+R)" guidance is correct; the failure mode was not propagating it into HUMAN-UAT.md pre-flight. Added an explicit pre-flight warning to `HUMAN-UAT.md` in this commit so future phase UATs surface it before the operator opens the dashboard.

## Files Modified

- `pyproject.toml` (version 4.10.0 → 4.10.1)
- `changelog.d/v4.10.1.bugfix.md` (new towncrier fragment)
- `quantum-chaos-enterprise-lab/uat-targets-86.txt` (UAT chaos-lab targets)
- `.planning/phases/86-scoring-correctness-hotfix/HUMAN-UAT.md` (authored, result filled in PASS, pre-flight browser-cache note added)
- `.planning/phases/86-scoring-correctness-hotfix/uat-86-hf1.png` (pre-refresh diagnostic)
- `.planning/phases/86-scoring-correctness-hotfix/uat-86-hf2.png` (post-refresh canonical evidence)
- `.planning/phases/86-scoring-correctness-hotfix/86-03-SUMMARY.md` (this file)

## Verification

- `python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"` → `4.10.1` ✓
- `ls changelog.d/v4.10.1.bugfix.md` → present ✓
- UAT screenshots both on disk in phase directory ✓
- HUMAN-UAT.md `**Result:** PASS` recorded ✓

## Out of Scope (deferred to v5.0 Phase 01)

Per CONTEXT.md decisions D-14 / D-15 / D-16:

- CLI HTML report scoring display (`quirk/reports/executive.py`, `quirk/reports/html_renderer.py`) — `RENDER-CLI-01`, `RENDER-PDF-01` deferred
- Evidence-tally gap (3 of 6 subscores at exactly 25 with HIGH/CRITICAL findings present) — `EVIDENCE-TALLY-01` deferred
- Historical-score backfill in SQLite — accepted "visual jump" trade-off, documented in changelog

## Next

Phase 86 is now ready for `gsd-verifier` to validate goal-backward against the 5 success criteria in ROADMAP.md. After verification passes, v4.10.1 can be tagged and released.
