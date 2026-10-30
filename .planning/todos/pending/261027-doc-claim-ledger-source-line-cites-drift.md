---
type: todo
created: 2026-10-27
source: Phase 234 plan 234-07 (SUMMARY, "Ledger line-cite drift, pre-existing")
priority: medium
area: docs/doc-claim-ledger.jsonl, tests/test_doc_claim_ledger_gate.py (find_malformed_evidence)
status: pending
resolves_phase: null
owner: "999.139"
---

# About 441 doc-claim-ledger evidence cites point at source lines that no longer hold the quoted text

**Owner:** 999.139

Plan 234-07 found that about 441 `quirk/intelligence/{scoring,evidence,roadmap,score_lift}.py:N` cites in
`docs/doc-claim-ledger.jsonl` evidence, across 12 docs (275 in `docs/report-interpretation.md`, 107 in
`docs/operators-guide.md`), no longer point at the text they quote. The cause is the Phase 234-03 line shifts
plus earlier phases. `tests/test_doc_claim_ledger_gate.py` stays green because `find_malformed_evidence` only
checks that a cited file exists (`evidence cites ... which does not exist`), not that the cited line holds the
cited text. 234-07 refreshed the rows it touched and left the rest.

The anchors (the doc side) still hold, so the claims themselves are not known to be wrong; the evidence pointers
are stale, which makes re-verifying a claim slower and lets a real drift hide behind a stale pointer.

## Proposed fix shape

Either add a cite-content check to the gate (for `path:line text` evidence, the quoted text must appear at, or
near, the cited line, with a re-anchor helper to fix rows in bulk), or do a one-time scripted refresh that
re-locates each quoted text and rewrites the line number, then add the check so it cannot drift again. Count the
stale cites with a script before and after; do not trust the 441 figure as a target.

## Feasibility & Effort

**CONFIRMED** by 234-07's scripted count. Effort **M**: the refresh is mechanical; the gate check needs a
tolerance rule for quoted text that spans lines.
