---
type: todo
status: resolved
resolves_phase: "185"
resolved: 2026-09-06
created: 2026-09-02
source: Phase 177-07 (release toolchain repair) — remote CI first-run discovery
priority: medium
---

# a11y baselines were generated on macOS; the gate enforces on Linux CI

All 33 `tests/a11y/baseline-*.json` files were generated locally on macOS on 2026-08-27 in a
single batch (`--update-baselines` run, ~12:11–12:13 UTC). The `Dashboard Quality` GitHub Actions
workflow enforces those baselines on `ubuntu-latest`. Font metrics differ between the two
environments, and `scrollable-region-focusable` (and potentially other overflow-triggered axe
rules) fire based on whether a container is *actually overflowing at render time* — a property of
viewport/font metrics, not markup. A rule that never fires on macOS can fire on Linux, and vice
versa.

**How this was found:** Phase 165 (v5.16) shipped this a11y suite, but v5.16 and v5.17 were both
"developed complete" and never pushed to `origin` until Phase 177-07's release push (2026-09-02) —
six days after the baselines were authored. That push was the *first-ever execution* of
`Dashboard Quality` against this `main` history. It immediately surfaced two previously-invisible
gaps on `/data-at-rest`:

- `scrollable-region-focusable` baseline was `1` (default variant) but Linux CI observed `2`.
- The `empty` and `loading` fixture variants had baseline `0` (never observed on macOS) but Linux
  CI observed `2` for both.

All three were fixed in Phase 177-07 by bumping the specific baselines to the real, CI-observed
counts, each with a written justification recording the run ID, date, and environment-mismatch
root cause (see `baseline-data-at-rest-default.json`, `-empty.json`, `-loading.json`, and their
git history for the reasoning). This is a genuine record-of-observed-truth correction, not a
design/scope debt — but it exposes a structural gap:

**31 of 33 baseline files currently record zero instances of `scrollable-region-focusable`.**
Only `data-at-rest`'s three variants have ever been checked against a Linux render. Any other
route whose tables/containers sit near an overflow boundary may be carrying the same latent gap,
simply never exercised because `Dashboard Quality` had never run on this content until now.

**The real fix — not scoped to Phase 177:**

1. Regenerate all baselines (`npm run a11y:baseline`, `:empty`, `:loading`) by running the
   generator **on a Linux CI runner** (e.g. a manual `workflow_dispatch`-triggered job, or a
   one-off script step in `Dashboard Quality` gated behind a flag), not on a contributor's local
   macOS machine. Commit the Linux-generated baselines as the new source of truth.
2. Alternatively/additionally, consider whether the count-pinning model itself is too fragile —
   a tolerance/range instead of an exact integer would absorb legitimate viewport/font jitter
   without masking genuine new violations. Evaluate before choosing over (1); a loose tolerance
   could hide a real regression, so this needs design thought, not a quick swap.
3. `components/ui/table.tsx` — adding `tabIndex`/`role` to the scrolling wrapper is the structural
   fix that would zero `scrollable-region-focusable` app-wide, eliminating the render-dependent
   count problem entirely for this rule. Deliberately NOT done in Phase 177-07 (nor should it be
   done opportunistically elsewhere): 165-CONTEXT.md explicitly excludes keyboard-navigation/
   focus-order audits from that milestone's scope, and it's a focus-order change with app-wide
   blast radius that deserves its own dedicated phase, not a drive-by fix.

**Triage together with `a11y-route-coverage-gap.md`** (this same `.planning/todos/pending/`
directory) — both are coverage/fidelity gaps in the same a11y gate, discovered independently
(code review vs. first-ever remote CI execution), and a future phase addressing one should almost
certainly address both: `/hardware` and `/compare` are entirely unswept, and the 31 swept-but-
zero-violation baselines on the other 9 routes may still be macOS-generated and unverified against
Linux the same way `data-at-rest` was until this phase.

**Do NOT** regenerate all 33 baselines opportunistically to "get ahead of it," and do NOT fix
`table.tsx` now — both are real fixes that belong to a dedicated frontend-a11y phase with its own
CONTEXT/PLAN, not a drive-by inside a release-handoff plan.


---

## Disposition (Phase 185, 2026-09-06)

**Item 1 (regenerate on Linux CI) — DONE.** Plan 185-01 added a permanent `workflow_dispatch`
regeneration job (`a11y-regenerate-baselines`) on `ubuntu-latest`. Plan 185-05 installed a real
Linux-generated artifact. **Measured finding, correcting this todo's own premise:** the
Linux-regenerated baselines for all 11 pre-existing routes are content-identical to the committed
macOS-generated ones — zero (route, rule) count changes across all 33, only the `generated`
timestamp differs. Phase 177's hand-patched `data-at-rest` `count: 2` values were already correct.
The macOS-vs-Linux mismatch produced no enforced drift for these 31 baselines after all; several
Phase 177 justification texts asserting Linux/macOS font-metric divergence are not reproducible at
the current commit and should not be repeated as fact going forward.

**Item 2 (tolerance model) — EVALUATED AND REJECTED (D-06).** Plan 185's CONTEXT/RESEARCH
considered a tolerance/range model instead of exact-integer counts and rejected it: a loose
tolerance could hide a real regression, which is the opposite of what this todo exists to prevent.
The exact-integer count-budget model (Phase 165 A11Y-01/A11Y-04) stands unchanged.

**Item 3 (`table.tsx` structural fix for `scrollable-region-focusable`) — DEFERRED, not done.**
Per 165-CONTEXT.md's explicit exclusion of keyboard-navigation/focus-order audits from that
milestone's scope, and per this todo's own instruction not to fix it opportunistically: still not
done. Remains a real, scoped future fix — the shared `Table` wrapper gap now also appears on
`/hardware` (see `a11y-route-coverage-gap.md`'s disposition) in addition to `/data-at-rest`.

**D-03/D-10 procedures documented** in `docs/operators-guide.md` §5.3 (185-07) so the correct
regeneration path is discoverable by reading, not archaeology, going forward.

See `185-07-SUMMARY.md` and `Phase-185-A11y-Baseline-Environment.md` (vault) for full evidence.
