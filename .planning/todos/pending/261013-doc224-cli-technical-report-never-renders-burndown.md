---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §16 Remediation Burndown)
priority: medium
area: quirk/reports/writer.py (build_tech_markdown call)
status: pending
resolves_phase: null
owner: "999.133"
---

# CLI technical markdown never shows the Remediation Burndown section or a closure refusal

`build_tech_markdown` accepts `burndown` and `closure_refusal` (`quirk/reports/technical.py:70-71`, rendered at
`:283`), but `write_reports` calls it without them (`quirk/reports/writer.py:531-539`). Both values are only computed
later (`writer.py:858-863`) for `exec_content`. So `technical-findings-*.md` never carries closure state; the existing
test calls the renderer directly and never exercised the writer. Probe `gc3-r3-f4-closure-refusal-probe.py`.
Also note `261013-doc224-dashboard-burndown-hides-closure-refusal` lists the "CLI technical summary" as showing the
refusal, which this contradicts. `docs/operators-guide.md:3329` repeats the false CLI claim (other owner).

When fixed, update docs/report-interpretation.md §16 ("The CLI technical markdown report does not carry closure state").

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `writer.py:531-539` (call without kwargs); `writer.py:858-863` (computed later); `technical.py:70-71,283`.
- Fix: compute `_closure_refusal`/`_burndown` before the tech_md build (neither depends on the score) and pass them; add a writer-level test.
