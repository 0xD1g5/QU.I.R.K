---
phase: 166-gate-robustness
plan: 02
subsystem: testing
tags: [xml, xxe, lxml, security, uat-tooling, ci-gate]

# Dependency graph
requires:
  - phase: 87-dep-migration (historical, not this milestone)
    provides: "quirk/util/xml_safe.py — make_safe_parser()/parse_safely() hardened lxml chokepoint"
provides:
  - "uat_runner.py CBOM XML parsing routed through the hardened lxml chokepoint (no XXE/billion-laughs path)"
  - "AST-based forward-locking gate covering repo-root tooling (tests/test_xml_safe.py)"
  - "Corrected GATE-02 requirement text in REQUIREMENTS.md and ROADMAP.md"
affects: [166-04-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AST-based (ast.Import/ast.ImportFrom) forward-locking import gates over substring/regex grep, to tolerate legitimate string-literal mentions of forbidden module names"

key-files:
  created: []
  modified:
    - uat_runner.py
    - tests/test_xml_safe.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "uat_runner.py adopts quirk.util.xml_safe.parse_safely(), NOT defusedxml — GATE-02's original premise (matching a v5.0 SAML/defusedxml migration) was factually backwards; Phase 87/DEP-02 migrated away from defusedxml to the lxml chokepoint"
  - "New grep gate is AST-based, not substring-based, specifically to tolerate uat_runner.py:191's 'lxml.etree'/'defusedxml' string literals in its optional-dependency probe list"
  - "REQUIREMENTS.md is actually tracked by git in this repo (committed by 166-01), contrary to the plan's stated assumption that it is gitignored/untracked — followed actual git state, committed it alongside ROADMAP.md"

requirements-completed: [GATE-02]

# Metrics
duration: 25min
completed: 2026-08-27
---

# Phase 166 Plan 02: UAT XML Hardening (GATE-02) Summary

Migrated `uat_runner.py`'s two CBOM XML parse sites from stdlib `xml.etree.ElementTree` to
the Phase 87/DEP-02 hardened lxml chokepoint (`quirk.util.xml_safe.parse_safely()`), added an
AST-based forward-locking import gate, and corrected the GATE-02 requirement text, which had
incorrectly instructed migrating to `defusedxml` — the opposite of this repo's established
security pattern.

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-08-27
- **Tasks:** 3/3 completed
- **Files modified:** 4 (`uat_runner.py`, `tests/test_xml_safe.py`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`)

## Accomplishments
- Closed the last unhardened XML parse path in the repo's tooling surface (`uat_runner.py:823`,
  `:1190`) — both now route through `parse_safely()` and catch `lxml.etree.XMLSyntaxError`
  specifically, preserving the existing FAIL-with-notes behaviour character-for-character.
- Added a new AST-based gate (`test_no_stdlib_xml_or_defusedxml_import_in_repo_root_tooling`)
  that forward-locks `uat_runner.py` against a future stdlib-xml or `defusedxml` regression,
  proven correct with both a negative control (fails when the forbidden import is injected)
  and a positive control (passes with the file's legitimate string-literal mentions of those
  same names present).
- Corrected the factually-backwards GATE-02 premise in both `.planning/REQUIREMENTS.md` and
  `.planning/ROADMAP.md`, naming Phase 87/DEP-02 as the real precedent and marking GATE-02
  complete.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate uat_runner.py's two XML parse sites to parse_safely()** - `8f0ebfa` (fix)
2. **Task 2: Extend the XML grep gate to cover repo-root tooling** - `f5d7a4b` (test)
3. **Task 3: Amend the incorrect GATE-02 premise in REQUIREMENTS.md and ROADMAP.md** - `9a6dd7b` (docs)

**Plan metadata:** this file's commit (see below)

## Files Created/Modified
- `uat_runner.py` - two `ET.parse`/`ET.ParseError` call sites replaced with
  `parse_safely()`/`etree.XMLSyntaxError`; import block replaced with
  `from lxml import etree` + `from quirk.util.xml_safe import parse_safely`; line 191's
  optional-dependency probe list (containing the string literals `'lxml.etree'`,
  `'defusedxml'`) left byte-identical
- `tests/test_xml_safe.py` - new `test_no_stdlib_xml_or_defusedxml_import_in_repo_root_tooling`
  AST-based gate, plus `_REPO_ROOT_TOOLING_FILES`/`_FORBIDDEN_IMPORT_PREFIXES` constants and a
  `_forbidden_imports_in_file()` helper; existing `test_no_defusedxml_import_in_quirk` untouched
- `.planning/REQUIREMENTS.md` - GATE-02 bullet rewritten to name the lxml chokepoint, corrected
  premise note dated 2026-08-27, checkbox and traceability row marked Complete
- `.planning/ROADMAP.md` - Phase 166 Success Criterion 2 rewritten to match, `166-02-PLAN.md`
  checkbox marked done, progress table row updated to 2/4

## Decisions Made
- Followed CONTEXT.md's explicit, user-approved decision to use `parse_safely()` rather than
  `defusedxml` — this is a hard constraint, not discretionary.
- Used the AST-based gate design over a substring/regex grep per the plan's explicit
  instruction, since `uat_runner.py:190-191` legitimately contains the forbidden strings as
  probe-list literals, not imports.
- REQUIREMENTS.md turned out to be git-tracked in this repo already (committed in the prior
  166-01 plan), contradicting the plan's stated assumption that it's gitignored/untracked.
  Followed the actual on-disk/git-tracked reality rather than the stale assumption — committed
  it alongside ROADMAP.md in the Task 3 commit. `git add` on it printed the repo's known
  "ignored by .gitignore" hint (see project memory: `gsd-tools/gsd-sdk commit --files falsely
  reports failure on gitignored .planning/`) but staged and committed successfully, matching
  the previously observed gotcha.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] REQUIREMENTS.md commit-scope instruction did not match actual git state**
- **Found during:** Task 3
- **Issue:** The plan instructed `.planning/REQUIREMENTS.md` must NOT be `git add`'d because
  `.planning/` is gitignored and REQUIREMENTS.md is an "untracked" exception file. In reality,
  `git ls-files --error-unmatch .planning/REQUIREMENTS.md` succeeds (exit 0) — the file is
  already tracked, having been committed by the prior 166-01 plan (`903ccfd docs(166-01):
  complete plan 01 execution — state, roadmap, requirements`).
- **Fix:** Committed `.planning/REQUIREMENTS.md` alongside `.planning/ROADMAP.md` in the Task 3
  commit, following actual git-tracked state rather than the plan's stale assumption. This
  matches the precedent already set by 166-01's own commit.
- **Files modified:** `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`
- **Verification:** `git ls-files --error-unmatch .planning/REQUIREMENTS.md` exits 0 both
  before and after; `git show --stat HEAD` confirms both files are in the commit.
- **Committed in:** `9a6dd7b`

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** No scope creep — the deviation only affects which git-add path is taken
for a docs file the plan already required to be amended; content of the amendment matches the
plan's specification exactly.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
GATE-02 is fully satisfied: `pytest tests/test_xml_safe.py -x -q` passes (7 pre-existing + 1
new test, all green), `pytest tests/test_xml_safe.py tests/test_packaging.py -x -q` passes (17
total), `python -m compileall -q uat_runner.py` exits 0, and zero `defusedxml` imports or
dependency additions exist anywhere in the diff. Ready for 166-03 (GATE-03) and the 166-04
full-suite verification plan.

### Control verification (required by plan)
- **Negative control:** temporarily inserted `import xml.etree.ElementTree` at the top of
  `uat_runner.py` → `pytest tests/test_xml_safe.py::test_no_stdlib_xml_or_defusedxml_import_in_repo_root_tooling`
  **FAILED** with `AssertionError: Forbidden XML import(s) found in repo-root tooling:
  {'uat_runner.py': ['xml.etree.ElementTree']}`. File was then restored from backup
  (`cp /tmp/uat_runner.py.bak uat_runner.py`), confirmed byte-identical to the committed state
  via `git status --short` showing no diff.
- **Positive control:** with `uat_runner.py` in its final committed state (line 191 still
  containing the `'lxml.etree'`/`'defusedxml'` string literals in the dependency probe list),
  the same test **PASSED** — proving the gate is AST-aware and does not false-positive on
  those literals.

---
*Phase: 166-gate-robustness*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: commit `8f0ebfa` (Task 1)
- FOUND: commit `f5d7a4b` (Task 2)
- FOUND: commit `9a6dd7b` (Task 3)
- FOUND: `uat_runner.py`
- FOUND: `tests/test_xml_safe.py`
- FOUND: `.planning/REQUIREMENTS.md`
- FOUND: `.planning/ROADMAP.md`
