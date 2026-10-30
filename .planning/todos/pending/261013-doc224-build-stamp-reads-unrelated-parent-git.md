---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §27 scanner build)
priority: low
area: quirk/build_stamp.py
status: pending
resolves_phase: null
owner: "999.129"
---

# Scanner build stamp reports the commit of an unrelated parent git checkout

`scanner_build_stamp()` walks every parent of the installed package looking for `.git`
(`quirk/build_stamp.py:54` `for parent in [start, *start.parents]:`). A wheel installed into a venv inside any git
checkout reports that checkout's HEAD as the "Scanner build", recreating the misattribution the stamp exists to
prevent. Probe `gc3-r3-f7-build-stamp-parent-git-probe.py`.

When fixed, update docs/report-interpretation.md §27 (the `.git` lookup paragraph).

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `build_stamp.py:54`.
- Fix: stop the walk at site-packages/dist-packages, or accept `.git` only when the same directory holds a pyproject.toml with `name = "quirk-scanner"` (`pyproject.toml:6`); extend `tests/test_build_stamp.py`.
