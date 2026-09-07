---
type: todo
created: 2026-09-07
source: phase-186.1 research (186.1-01/186.1-02 discovery, dormant risk deliberately left unfixed per CONTEXT.md Phase Boundary)
priority: medium
requirement: none (latent risk, not a reopening of TOOL-01/TOOL-04/TOOL-05)
---

# Bold-field search is document-wide, not heading-scoped — anchored (TOOL-04 fixed that) but UNSCOPED, dormant only by document-order luck

**Same defect class this phase just closed on the plain branch, found live on the bold branch and
deliberately left unfixed.** TOOL-04 (Phase 182) anchored every bold `**Field:**` regex instance
in both the read (`stateExtractField`) and write (`stateReplaceField`) paths, plus the write-path
instances inside `cmdStateBeginPhase` and `cmdStateUpdateProgress`. Anchoring closed the
mid-sentence-match hazard. It did **not** scope the search to a real field region — the bold
branch's `match()` still searches the entire document body and returns the FIRST hit, wherever it
occurs.

## The dormant hazard

`.planning/STATE.md` already contains two narrative sentences that quote the Current-focus bold
field verbatim, inside the SAME `## Project Reference` outer heading span as the real field:

- Line 24: the real `**Current focus:**` field.
- Line 202 and line 227: narrative sentences quoting that field's bold form verbatim, as part of
  documentation prose describing prior phase work.

This is dormant, not absent. `match()` is first-hit-wins in document order, and the real field
(line 24) currently precedes both decoys (lines 202, 227). If the real field were ever deleted, or
a future document restructuring moved a decoy ahead of it, the anchored-but-unscoped bold search
would silently match the decoy instead — the exact TOOL-05 failure mode, on the bold axis instead
of the plain axis.

## Why this is being filed now instead of fixed now

Deliberately left unfixed per `186.1-CONTEXT.md`'s Phase Boundary: Phase 186.1's scope is the
plain-field fallback (TOOL-05) discovered live in production. This bold-axis risk was found during
186.1's own research while building the two-axis (install x construct-shape) scan extension, not
by a live corruption report — it has never actually fired, because document order has protected it
so far. Fixing a risk that has not yet manifested, inside a phase scoped to a risk that already
has, would have expanded 186.1's blast radius without a falsifying reproduction to anchor the fix
against (the same anti-pattern CLAUDE.md clause (e) warns about: don't trust a fix that was never
proven against a real failure).

## What makes this fixable without new research

The `fieldRegion` helper (the "leading contiguous field-shaped run after a known heading" scoping
shape) landed in Phase 186.1 for the plain-field axis and is directly reusable here — the fix
shape does not need to be re-derived, only applied to the bold branch's search. The extended
guard scan (two axes: install set x construct shape) built in 186.1-02 will surface every bold-axis
site needing this scoping once a scoping detector (as opposed to an anchoring detector) is applied
to that axis — the scan already regenerates its occurrence set from installed source rather than a
hand-derived list, so extending its predicate is the correct next step, not writing a new list.

## Acceptance (for whoever picks this up)

- Apply the `fieldRegion` leading-contiguous-run scoping to the bold-field search path, in both
  installs.
- Extend the guard scan's disposition predicate to distinguish "scoped" from "anchored-only" on the
  bold axis, the way it already does on the plain axis after 186.1.
- Prove it at the command boundary with a fixture reproducing this project's actual line-24/202/227
  shape (decoy inside the same heading span, real field first in document order) before any live
  re-demonstration — per CLAUDE.md clause (e), a green function-level test alone is not sufficient.
