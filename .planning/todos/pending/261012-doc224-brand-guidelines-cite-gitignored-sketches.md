---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-BRAND-*
priority: low
area: docs/brand/BRAND-GUIDELINES.md, tests/test_brand_guidelines_v2.py
status: pending
resolves_phase: null
owner: "999.129"
---

# BRAND-GUIDELINES cites "sketch 001" and "sketch 002", which live in a gitignored directory no reader can open

`docs/brand/BRAND-GUIDELINES.md` (section 2 and the Product UI subsection of section 5) justifies two design decisions
by "sketch 001 variant B" and "sketch 002 variant A". The sketches exist only under `.planning/sketches/` on the
author's machine; `.planning/` is gitignored (`git check-ignore -v .planning/sketches/x` -> `.gitignore:75`), so a
reader of the public repository cannot verify the sentences. The figures quoted from sketch 001 were recomputed in plan
224-11 from `index.css` and the pre-change accent in git history (old teal `#3a9696` on the light grounds: 3.28, 3.51,
3.16 and 3.51:1; `#ac84f5` slightly worse than the old teal on every dark ground), so the numbers stand on their own.
The comparison paragraph for sketch 002 (alternatives "declined") could not be verified from any user-facing source and
was removed, leaving only the checkable part (the sidebar renders the favicon-tier glyph at 24 px in the 48 px rail).

The sketch names stay in the document only because `tests/test_brand_guidelines_v2.py::test_sketch_evidence_quoted`
asserts `"sketch 001"`, `"sketch 002"` and `"3.16"` are present (D-10: a pinned string is reported, not edited).

- [ ] Decide whether the document should name the sketches at all. If not, drop the two names and keep the recomputed
      figures, and relax `test_sketch_evidence_quoted` to assert the figures only.
- [ ] If the names stay, publish the sketches (for example under `docs/brand/`) so the references resolve.

## Feasibility & Effort

**CONFIRMED** (gitignore rule and the pinned test above). Effort **S**: one sentence in the guidelines and one test
assertion. **No spike needed.**
