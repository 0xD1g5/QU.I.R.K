---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §25 storyline / report narrative)
priority: medium
area: quirk/reports/content_model.py (_classify_finding)
status: pending
resolves_phase: null
---

# Report narrative matcher gives "HTTP on TLS-designated port" the DES narrative (substring match on "designated")

`_classify_finding` joins title/description into `search_text` (`quirk/reports/content_model.py:743`) and tests
`keyword.upper() in search_text` (`:751`), a plain substring test. The CLI evaluator's `HTTP on TLS-designated port`
title (`quirk/engine/findings_evaluator.py:433`) contains "DES" inside "designated", so the report gives plaintext HTTP
a DES/3DES narrative and an "Authentication exposure" top risk. Words such as "includes", "modes" or "provides" in
descriptions can do the same. Probe `gc3-r3-f7-narrative-classes-probe.py`. The dashboard never emits that title.

When fixed, update docs/report-interpretation.md §25 ("One report-side exception to 'no narrative for those classes'").

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `content_model.py:743,751`; `findings_evaluator.py:433`.
- Fix: whole-token matching with a word-boundary regex.
- Unknown: whether an intended match relies on substrings (e.g. "SHA1" in "SHA1WITHRSA"); run the storyline and content_model tests.
