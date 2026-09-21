# Phase 206: Reclassification Record — the SC#3 Denominator

**Written by plan 206-12 on 2026-09-21. Every number and every case ID below was derived at run
time from `docs/uat-coverage-gaps.md` and the ten fragments under `red-proof/`, by the commands
shown. None was transcribed from `206-CONTEXT.md`, from `.planning/ROADMAP.md`, or from any plan's
prose.**

`206-CONTEXT.md` § Specific Ideas and `206-VALIDATION.md` § SC#3 denominator warning both name the
same failure mode: reaching "zero open GAPs" by quietly shrinking the set the zero is measured
against. This document exists so that every case which leaves the jsdom-tractable set does so
visibly, with re-runnable evidence, and so the arithmetic closes in public.

---

## 1. The starting denominator, re-derived

`206-CONTEXT.md` asserts 28. That assertion is **confirmed**, independently, from the corpus:

```
$ grep -c "^| UAT-7-" docs/uat-coverage-gaps.md
31

$ grep "^| UAT-7-" docs/uat-coverage-gaps.md | grep -iE "headless|browser|playwright|puppeteer" | grep -o "UAT-7-[0-9]*"
UAT-7-01
UAT-7-17
UAT-7-32
```

31 open series-7 GAPs, of which exactly 3 name a headless browser in their own GAP reason →
**28 jsdom-tractable**. This is the denominator SC#3's "zero" is measured against.

## 2. What this phase converted, re-derived

```
$ grep -h '^UAT-7-[0-9]* ->' red-proof/206-RED-PROOF-*.md | sed 's/ ->.*//' | sort -u | wc -l
25
```

**25 converted.** The non-converted remainder falls out as a set difference, not as a claim:

```
$ comm -23 <(grep -o "^| UAT-7-[0-9]*" docs/uat-coverage-gaps.md | sed 's/^| //' | sort -u \
             | grep -vE "UAT-7-(01|17|32)$") \
           <(grep -h '^UAT-7-[0-9]* ->' red-proof/*.md | sed 's/ ->.*//' | sort -u)
UAT-7-12
UAT-7-23
UAT-7-29
```

**3 not converted: `UAT-7-12`, `UAT-7-23`, `UAT-7-29`.** 25 + 3 = 28. The arithmetic closes.

---

## 3. Movements out of the jsdom-tractable set

Two cases leave. A third (`UAT-7-12`) did **not** convert but does **not** leave — the distinction
is the point of this table, and collapsing it would be exactly the silent shrink the warning
forbids.

| Case | Left | Joined | Evidence (verbatim fragment output) | Routes to |
|---|---|---|---|---|
| **UAT-7-23** — Sidebar Responsive Collapse | jsdom-tractable (28) | browser-only, alongside `UAT-7-01`, `UAT-7-17`, `UAT-7-32` | `red-proof/206-RED-PROOF-shell.md` § UAT-7-23 reclassification evidence — quoted in full in §3.1 below | **Phase 207** (operator-led browser verdict). Stays **GAP**, reason rewritten to name the CSS-breakpoint blocker |
| **UAT-7-29** — Roadmap Node Drag | jsdom-tractable (28) | browser-only, same group | `red-proof/206-RED-PROOF-roadmap.md` § Non-conversions — quoted in §3.2 below | **Phase 207**. Stays **GAP** (not DEFERRED — no substitute exists) |
| **UAT-7-12** — Certificates Expiry Sorting | *— does not leave —* | *— stays in the jsdom-tractable set —* | `red-proof/206-RED-PROOF-certificates-identity.md` § UAT-7-12 non-conversion evidence — quoted in §3.3 below | A **filed todo**, `.planning/todos/pending/certificates-expiry-sort-absent.md`. Disposition **FAIL**, not GAP — see §3.3 |

### 3.1 UAT-7-23 — the evidence, quoted verbatim

From `red-proof/206-RED-PROOF-shell.md`, commands run from the repository root on 2026-09-21
against the unmodified, post-revert `sidebar.tsx`:

> **Command 1 — is there any JavaScript media-query listener to assert against?**
>
> ```
> $ grep -n "matchMedia\|useMediaQuery" src/dashboard/src/components/sidebar.tsx
> $ echo $?
> 1
> ```
>
> Literal output: **none** (no matching lines; grep exit status `1` = no match).
>
> **Command 2 — what actually implements the collapse?**
>
> ```
> $ grep -n "lg:w-\|w-12" src/dashboard/src/components/sidebar.tsx
> 78:        "w-12 lg:w-60",
> $ echo $?
> 0
> ```

**Why this is a reclassification and not a shortfall.** The collapse is a pure Tailwind responsive
breakpoint. jsdom has no layout engine and evaluates no media queries, so the rendered DOM is
byte-identical above and below 1024px — every element the case asks about (240px vs 48px width,
wordmark vs monogram, tooltip visibility) is present in **both** states, distinguished only by
which CSS rule a real browser would apply. No honest jsdom assertion can tell the states apart; a
test that appeared to would be asserting class strings, i.e. the banned source-text substitution
wearing a render test's clothes. The case was never jsdom-tractable; the original 28/3 split
mis-graded it, and this is the correction.

The shell fragment also records the counterfactual explicitly: *"if command 1 had returned a JS
media-query listener, `UAT-7-23` would have been convertible after all and this block would say
so. It did not."* The reclassification is an outcome of the check, not a premise of it.

### 3.2 UAT-7-29 — the evidence, quoted verbatim

From `red-proof/206-RED-PROOF-roadmap.md` § Non-conversions:

> Node drag is entirely internal to the real Cytoscape renderer. `roadmap.tsx` registers no drag,
> `grab`, `free`, `position`, or `dragfree` handler and never reads or writes node positions — it
> hands an `elements` array with no `position` key to `cytoscape()` and lets dagre lay the graph
> out. Every one of the case's five Pass Criteria ("Node moves smoothly during drag", "All
> connected edges update position in real-time", "Node stays in new position after release",
> "Other nodes not affected by the drag", "Layout does not reset on node release") is a property of
> the renderer's own hit-testing, position bookkeeping and repaint, none of which a mocked
> `cytoscape` module performs. Requires a real browser.

**The rejected alternative is recorded, because rejecting it is the honest act.** Plan 206-08 was
offered a data-layer invariant — "every edge's `source` and `target` still resolve to nodes in the
elements array independent of node positions" — and declined it on two grounds, both of which
survive review:

1. It covers **zero** of the case's five Pass Criteria. A citation whose carve-out list is the
   case's entire criteria set is a false attestation, not a partial one.
2. "After a position update" has no referent in this product. Positions exist in no state
   `roadmap.tsx` owns, so the test would have to synthesise an event the product never handles and
   then assert that an array built *before* that event is unchanged — faking the thing under test.

That invariant is nonetheless real, and is already asserted as a *supporting* assertion inside
UAT-7-15's cited node. It is simply not UAT-7-29's subject.

### 3.3 UAT-7-12 — a non-conversion that is NOT a reclassification

From `red-proof/206-RED-PROOF-certificates-identity.md`, re-confirmed by plan 206-12 against
today's source (2026-09-21) rather than carried forward:

```
$ grep -n "sort\|Sort\|tanstack" src/dashboard/src/pages/certificates.tsx
$ echo $?
1
```

Literal output: **none**, across all 116 lines of the file. The comparison page still implements
the pattern:

```
$ grep -n "tanstack" src/dashboard/src/pages/findings.tsx
11:} from "@tanstack/react-table"
```

**This case stays in the jsdom-tractable set, and the distinction is load-bearing.** The blocker is
not jsdom — a click-to-sort interaction is exactly the kind of thing jsdom tests well, and
`findings-sorting.test.tsx` (UAT-7-07) does it on the sibling page. The blocker is that **the
feature does not exist in the product.** Moving UAT-7-12 to the browser-only group would be a
category error: Phase 207 with a real browser would find the same absent sort control.

Its honest disposition is therefore **FAIL** — the product does not do what the case describes —
with the gap filed as `.planning/todos/pending/certificates-expiry-sort-absent.md`. A FAIL is a
*dispositioned* case, so it leaves the GAP count without leaving the denominator. **Plan 206-13
owns the actual flip in `docs/UAT-SERIES.md`; this document only states what is true.**

---

## 4. The arithmetic, stated in full

```
Starting jsdom-tractable set                                    28
  − UAT-7-23  (pure CSS breakpoint; no matchMedia/useMediaQuery)  −1   → browser-only, Phase 207
  − UAT-7-29  (renderer-internal drag; no position handler)       −1   → browser-only, Phase 207
                                                                ────
Revised jsdom-tractable denominator                             26

Of those 26:
  converted, with a red-proved cited node                         25
  UAT-7-12, dispositioned FAIL (feature absent, todo filed)         1
                                                                ────
  remaining at GAP inside the jsdom-tractable set                   0
```

**SC#3's "zero" is reached at a denominator of 26, not 28, and the two subtracted cases are named,
evidenced and routed above.** Nothing else was removed. There is no unexplained arithmetic gap.

The browser-only group routed to Phase 207 grows from 3 to 5: `UAT-7-01`, `UAT-7-17`, `UAT-7-32`,
plus `UAT-7-23` and `UAT-7-29`.

### Agreement with the red-proof tally

`206-RED-PROOF.md` § Tally records **25 converted**, **25 red-proved**, **3 honestly
non-converted** (`UAT-7-12`, `UAT-7-23`, `UAT-7-29`) and **2 reclassified out** (`UAT-7-23`,
`UAT-7-29`). Those are the same numbers and the same case IDs used above. The two documents agree.

---

## 5. Verdict against each of the four ROADMAP success criteria

Stated from the derived tally, not from intent. Two of the four are **not met as written**, and
saying so is the point of this section.

### SC#1 — "Each of the 28 cases has a vitest test asserting that case's own subject"

**NOT MET AS WRITTEN — met at 25 of 28, with all 3 shortfalls dispositioned.**

25 cases have a newly written node asserting their own subject, each cited in a fragment's
`## Citations` section. Three do not: `UAT-7-23` and `UAT-7-29` because no honest jsdom assertion
exists (§3.1, §3.2), and `UAT-7-12` because the feature it describes is absent from the product
(§3.3). Against the *revised* denominator of 26 the criterion is met at 25 of 26, with the 26th
(`UAT-7-12`) blocked by product absence rather than by test-writing.

`206-CONTEXT.md` is explicit that **"28 is a ceiling and a hypothesis, not a target"** and that
*"a shortfall that is honestly dispositioned is a successful outcome of this phase; a 28/28
achieved by approximate tests is a failed one."* This is that shortfall, and it is dispositioned.
It is recorded as not-met rather than reported as 25/25 against a quietly redefined denominator.

One qualification a reader must not lose: **of the 25 conversions, only 5 are full coverage.** The
other 20 carry explicitly-named uncovered Pass Criteria bullets. `206-CONTEXT.md`'s rule is that
partial coverage is citable *only* if those bullets are carried verbatim into the case's
`**Notes:**`. **206-13 must qualify those dispositions rather than flip an unqualified PASS.**

The split was derived by parsing each fragment's `## Citations` and `## Uncovered Pass Criteria`
sections, not written out by hand:

```
$ python3 <parse each fragment's Citations + Uncovered Pass Criteria sections>
ALL cited: 25
PARTIAL (derived): 20  7-04 7-05 7-06 7-07 7-09 7-10 7-14 7-15 7-16 7-21
                       7-22 7-24 7-25 7-26 7-27 7-28 7-30 7-31 7-40 7-41
FULL (no uncovered bullets): 5  7-03 7-08 7-20 7-34 7-37
```

**A drift worth recording:** plan 206-12's own first draft of this paragraph listed **18** cases,
hand-assembled while reading the fragments. The derived set is **20** — the hand list silently
omitted `UAT-7-21` and `UAT-7-30`. The list was replaced with the derived one. This is the sixth-
plus instance of the failure mode `CLAUDE.md` names repeatedly: *a hand-maintained list of sites
drifts from the real set.* It is recorded rather than quietly corrected, because the correction is
the evidence that the rule is worth keeping.

Two of the 20 need handling that differs from "partial PASS", so the set 206-13 should flip to a
**qualified PASS** is the 20 minus these two, i.e. **18** cases:

- **`UAT-7-30` → unqualified PASS.** It appears in the derived partial set only because
  `print-view-layout.test.tsx` alone leaves Criterion 1 uncovered. **It requires a TWO-NODE
  citation** — `print-view-layout.test.tsx` for Pass Criteria 2-6 and `app-print-chrome.test.tsx`
  for Criterion 1 ("No sidebar visible"). Cited together, all six criteria are covered and all six
  hold against current source. The print-style fragment states "neither node covers the case
  alone"; cite both, and the case is fully covered.
- **`UAT-7-21` → FAIL**, not a qualified PASS. Its criteria 3 and 4 are uncovered *and* its
  criterion 2 outright fails (§7). See SC#4 below.

### SC#2 — "Each new test has been shown to fail when the behaviour it claims to cover is broken"

**MET.**

All 25 converted cases have at least one red-proof row in `206-RED-PROOF.md` with a real captured
failure message — no empty cell, no `n/a`. The set of case IDs in the ledger's body rows is
*identical* to the set of cited case IDs (`comm -3` returns empty), so there is no cited case
without a red-proof and no red-proof row for an uncited case. The 13 `TEMPORARY(206-NN)` commits
and their 13 matching reverts all resolve under `git cat-file -e`.

Two red-proofs deserve naming as the strongest evidence that the discipline was real rather than
ceremonial:

- **UAT-7-37**: the first plausible mutation (constant-true protocol predicate) *did* make the node
  fail — but at the protocol-only assertion, not the combination assertion that is the case's
  distinctive subject. A second attempt on the severity branch passed **green**, because severity
  is applied first. Only the third mutation isolated the seam. A mutation that fails the test is
  not automatically a mutation that exercises the claim.
- **UAT-7-21**: the audit's `it.fails` shape was proved in **both** directions — sensitivity
  (injecting one literal moved the reported set 95 → 96 and named the exact site) and contingency
  (with the scan returning no source lines the node went red with `Error: Expect test to fail`,
  proving the green result is caused by real violations, not by a test that always throws), plus a
  module-scope vacuity guard that `it.fails` cannot absorb.

### SC#3 — "the regenerated worklist shows the jsdom-tractable series-7 GAP count at zero, derived from the corpus"

**ACHIEVABLE, AND NOT YET MEASURED — the measurement belongs to plan 206-13.**

This plan touches no `docs/` artifact by design (the Phase 203 coordination fence), so the worklist
has not been regenerated and no derived zero exists yet. What this document establishes is that a
zero is reachable **honestly**: at the revised denominator of 26, all 26 have a route out of GAP
(25 conversions + 1 FAIL), and the 2 subtractions are named and evidenced in §3, not assumed.

**The warning `206-VALIDATION.md` attaches to this criterion is live, not hypothetical.** If 206-13
regenerates the worklist and finds a non-zero jsdom-tractable series-7 GAP count, **that is the
finding** — it must be reported, not closed by removing another case from the denominator. Any
further subtraction beyond `UAT-7-23` and `UAT-7-29` requires its own evidenced row in §3 of this
file before it may be counted.

### SC#4 — "Any case that resists honest conversion is re-dispositioned with its reason instead of covered by an approximate test"

**MET.**

All three non-conversions carry a specific, re-runnable reason rather than a generic one, and each
reason is of a *different kind*: a CSS-breakpoint blocker (`7-23`), a renderer-internal blocker
(`7-29`), and an absent-feature blocker (`7-12`). None was papered over with an approximate test,
and in `UAT-7-29`'s case a concrete approximate test was offered by the plan and explicitly
declined on the record (§3.2).

Two further pieces of evidence that the criterion was honoured in spirit, not just in letter:

- **`UAT-7-21` is dispositioned FAIL, not PASS**, even though its node runs green — because it runs
  green *by being `it.fails`*. A reader who scores the node by its result gets the wrong answer;
  the fragment says so in bold, and this document repeats it.
- **`UAT-7-30` is dispositioned PASS, reversing CONTEXT's D-A2 FAIL ruling** — see §6. That reversal
  came from re-running D-A2's own commands at execution time instead of citing the decision
  forward.

Five product defects were filed rather than fixed, per CONTEXT's test-only fence:
`certificates-expiry-sort-absent.md`, `certificates-self-signed-flag-absent.md`,
`cbom-table-no-results-empty-state-absent.md`, `lifecycle-event-row-unknown-event-type-crash.md`,
`roadmap-detail-panel-owner-and-dependencies-absent.md`, plus this plan's
`dashboard-hardcoded-colour-literals-bypass-theme-tokens.md`.

---

## 6. A stale CONTEXT decision, recorded as a finding

**`206-CONTEXT.md`'s decision D-A2 is STALE. Its instruction must not be followed.**

D-A2 (gathered 2026-09-13) ruled `UAT-7-30` a confirmed product defect — `/print` was a `<Route>`
inside `AppShell`, so the navigation sidebar shipped into every exported PDF — and instructed this
phase to disposition the case **FAIL** and to **file a todo**. Plan 206-12's own `files_modified`
list named that todo file, `print-route-renders-sidebar-into-pdf-export.md`.

**The defect is fixed. The todo was NOT filed.** Plan 206-11 re-ran D-A2's four prescribed commands
at execution time rather than citing the ruling forward, and they falsified it. Plan 206-12
re-confirmed independently on 2026-09-21:

```
$ grep -c 'path="/print"' src/dashboard/src/App.tsx
0

$ grep -n 'pathname.replace\|<Sidebar />' src/dashboard/src/App.tsx
80:  if (location.pathname.replace(/\/+$/, "") === "/print") {
87:      <Sidebar />

$ git log -1 --format="%h %ad %s" --date=iso 93e5afb1
93e5afb1 2026-09-14 06:41:57 -0400 fix(print): render /print without the dashboard chrome

$ git merge-base --is-ancestor 93e5afb1 HEAD; echo $?
0
```

`/print` is no longer a route at all. `App.tsx:80` short-circuits and returns `<PrintPage />`
**before** the shell holding `<Sidebar />` at line 87 is ever constructed — the sidebar is not
hidden on `/print`, it is never mounted. The fix shipped in commit `93e5afb1`, **2026-09-14** —
*one day after* `206-CONTEXT.md` was gathered — with a 7-case regression suite at
`src/dashboard/src/__tests__/app-print-chrome.test.tsx` that runs green today. The commit message
names the same PDF-export blast radius D-A2 did, and states the fix was made structural rather than
CSS precisely so a class rename cannot silently reintroduce it.

**Consequences:**

- **`UAT-7-30`'s disposition is PASS**, citing both nodes (§5, SC#1). D-A2's FAIL instruction is obsolete.
- **No todo is filed for the print sidebar.** It would describe an already-fixed defect, and a
  pending todo for fixed work is worse than no todo — it consumes review attention and inflates the
  backlog.
- D-A2's blast-radius note is likewise resolved by `93e5afb1`.

**D-A2's reasoning was sound when written; only its facts expired — in eight days.** That is the
general hazard, and it is the same one this project's `CLAUDE.md` names repeatedly in other
directions: a record that reads as authoritative can still be stale. The only thing that caught it
was re-confirming the evidence **by command at execution time** instead of citing a decision
forward. Plan 206-12 applied the same treatment to the sibling UAT-7-12 finding, which came back
**still valid** — the check is not a formality that always reverses a ruling.

---

## 7. Two derived-vs-written disagreements, recorded rather than smoothed

Both concern the `UAT-7-21` colour inventory. In each case the derived value is the one carried
forward, and the written value is recorded so the discrepancy is not lost.

**(a) "95 violations across 10 files" is 95 across 9 files.** The phrase appears in
`red-proof/206-RED-PROOF-print-style.md` and in `hardcoded-color-audit.test.tsx`'s own docstring.
Plan 206-12's independent re-scan reproduces the 95 exactly, but finds them in **9** files —
because the fragment's inventory table has **10 rows**, the tenth being `components/sidebar.tsx`
with a count of **0** ("Clean"). A zero row was counted as a file. Excluding `print.tsx`'s 45
by-design print-deliverable literals, the honest remediation headline is **50 literals across 8
dashboard page files**, not "across 9 pages".

**(b) The inline-style subset is 4 sites, not 8.** The fragment lists `executive.tsx:545`,
`healthcare.tsx:134/150/204`, `roadmap.tsx:296/305` and `cbom.tsx:436` as surviving UAT-7-21's
narrowest "inline styles only" reading. An independent grep for an actual JSX `style={{ … }}`
attribute carrying a literal returns only the first four:

```
$ grep -nE 'style=\{\{[^}]*#[0-9a-fA-F]{3,6}' src/dashboard/src/pages/*.tsx src/dashboard/src/components/sidebar.tsx
pages/executive.tsx:545 ... style={{ color: "#d4893a" }} ...
pages/healthcare.tsx:134 ... style={{ color: "#4ba8a8" }} ...
pages/healthcare.tsx:150 ... style={{ color: "#4ba8a8" }} ...
pages/healthcare.tsx:204 ... style={{ color: risk === "high" ? "#e05555" : "#d4893a" }}>
```

`roadmap.tsx:296/305` and `cbom.tsx:436` are **Cytoscape stylesheet object literals**, not JSX
inline styles. They are genuine violations of the case's broad reading and remain in the 50; they
simply do not belong to the narrow "inline styles" subset.

**Neither disagreement changes the verdict.** `UAT-7-21` fails on 95 literals under the broad
reading and on 4 under the narrowest possible one. The corrected figures are the ones written into
`.planning/todos/pending/dashboard-hardcoded-colour-literals-bypass-theme-tokens.md`.

---

## 8. What plan 206-13 must carry from this document

1. **Denominator is 26, not 28.** `UAT-7-23` and `UAT-7-29` are browser-only; route both to
   Phase 207 with the reasons in §3.1/§3.2. Do not subtract anything else without adding an
   evidenced row to §3 first.
2. **`UAT-7-30` → PASS, citing BOTH nodes.** D-A2's FAIL is stale (§6). File no print todo.
3. **`UAT-7-21` → FAIL.** Its node is green because it is `it.fails`. Do not score it by its result.
4. **`UAT-7-12` → FAIL**, not GAP; the feature is absent, the todo is filed, and the case stays in
   the jsdom-tractable denominator.
5. **Qualify every partial conversion** with its uncovered Pass Criteria bullets quoted verbatim
   from its fragment. The list is in §5 under SC#1. An unqualified PASS on any of those is a false
   attestation by `206-CONTEXT.md`'s own rule.
6. **If the regenerated worklist does not show zero, report it.** Do not close the gap by shrinking
   the denominator (§5, SC#3).
