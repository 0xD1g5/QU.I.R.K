# CHANGELOG parity qualifier list matches substrings (remaining review Infos)

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (f): IN-06 and the Infos not placed elsewhere)
**Priority:** P3.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` IN-06 (IN-05 is filed in the smoke-harness todo; IN-01 in the 3.15 cap todo; IN-02 in the doctor todo; IN-03/IN-04 in the source_scanner todo; every Warning has a home, so nothing else remains)
**Where it lives:** **[tests only]** `tests/test_changelog_5280_section.py:69, 124`.

## Items

- **IN-06:** the qualifier `"except"` matches "exception"/"exceptional", so an unqualified parity claim beside such a
  word passes. Use word-boundary regexes (`\bexcept\b`). Also, `_target_version()` `pytest.fail`s as soon as
  pyproject moves to 5.29 (by design); say so in the test docstring so the 5.29 bump does not surprise anyone.
  Note: 5.28.1 (the planned patch) will trip it too if pyproject moves to 5.28.1; check the helper's version
  matching before cutting 5.28.1.

## Feasibility & Effort

- **Feasibility: CONFIRMED by reading the test; fix LIKELY.**
- **Effort: S.**
- **Unknowns:** whether `_target_version()` fails on a patch bump (5.28.1) or only on a minor bump; this decides
  whether it blocks the 5.28.1 release PR.
- **Spike needed?** No; bump pyproject locally in a scratch copy and run the test.
