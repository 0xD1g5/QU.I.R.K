---
phase: 202-finding-storyline-drawer
plan: 02
subsystem: ui
tags: [typescript, react-hooks, vitest, msw, dashboard, api-contract]

requires:
  - phase: 202-01
    provides: title-bridge ledger and constituency reachability census (not consumed directly by this plan, but the phase's Wave-1 gate this plan runs alongside)
provides:
  - FindingStoryline TS interface (ten locked fields, zero optional members) in src/dashboard/src/types/api.ts
  - FindingItem.id corrected from `id?: number` to `id: number | null`
  - useFindingStoryline hook — lazy per-(id, title) fetch with retry, cancellation, and error-vs-absence separation
affects: [202-03, 202-04, 202-05, 202-06]

tech-stack:
  added: []
  patterns:
    - "Required-and-nullable (T | null, never ?:) for every field crossing the API boundary in this feature — the 201-UI-E2 class"
    - "Hook keyed on a (id, title) compound dependency, not id alone, because FindingItem.id is CryptoEndpoint.id and is shared across findings"

key-files:
  created:
    - src/dashboard/src/hooks/useFindingStoryline.ts
    - src/dashboard/src/hooks/__tests__/useFindingStoryline.test.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/components/__tests__/ExecutiveVerdict.test.tsx

key-decisions:
  - "FindingItem.id literals in ExecutiveVerdict.test.tsx given explicit numeric ids (not deliberately id-less fixtures, so a number rather than null was correct per the plan's own guidance)"
  - "A known production FindingItem-without-id site exists and was left unmodified per plan scope: quirk/dashboard/api/routes/scan.py:1421 appends identity findings from _derive_identity_findings() with no id= kwarg, so they arrive with id: null under the corrected Optional[int] = None schema. This is a genuine A6 source, not a fixture gap, and is out of this plan's files_modified."

requirements-completed: [STORY-01, STORY-02]

duration: ~35min
completed: 2026-09-12
---

# Phase 202 Plan 02: FindingStoryline Contract + useFindingStoryline Hook Summary

**Landed the locked ten-field `FindingStoryline` TS contract, corrected `FindingItem.id`'s
201-UI-E2-class nullability defect, and shipped a fully TDD'd `useFindingStoryline` hook that
tells a failed fetch apart from an honest absence.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-12
- **Tasks:** 2/2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `FindingStoryline` interface added verbatim from `202-UI-SPEC.md`'s Type Contract — ten fields,
  zero `?:` members, each with an inline comment tying the shape rule to 201-UI-E2 and D-01.
- `FindingItem.id` corrected from `id?: number` to `id: number | null`, with a comment explaining
  it is `CryptoEndpoint.id` (non-unique per finding, D-06) and the exact A6 disabled-trigger
  significance of the `null`-vs-`undefined` distinction.
- `useFindingStoryline` hook: lazy fetch keyed on `(finding.id, finding.title)`, A6 guard (no
  request when `id == null` or no finding selected), `cancelled`-flag cancellation, synchronous
  pre-await state clearing on finding change, one fixed error string with `data` staying `null`
  on any failure, and a `retry()` that bumps a nonce without remounting.

## Task Commits

1. **Task 1: FindingStoryline interface and the FindingItem.id nullability correction** — `c607679f` (feat)
2. **Task 2 (RED): failing test for useFindingStoryline** — `487660e1` (test)
3. **Task 2 (GREEN): useFindingStoryline hook implementation** — `9d3b2c83` (feat)

**Validation row flips:** `fe71ea5e` (202-02-T1 → green), `15c9dc73` (202-02-T2 → green)

_TDD: Task 2 ran RED → GREEN. No REFACTOR commit was needed — the GREEN implementation was
already clean against the idiom mirrored from `useHardwareDrift`._

## `tsc` Fallout from the `id` Change

Repo-wide search (`grep -rln "FindingItem"` under `src/` and `tests/` in `src/dashboard/`) found
four files referencing `FindingItem`; only one required a code change:

- **`src/dashboard/src/components/__tests__/ExecutiveVerdict.test.tsx`** — three `FindingItem`
  literals inside `findings: [...]` arrays, contextually typed via `ScanLatestResponse`, were
  missing `id`. All three fixtures represent ordinary derived findings (not deliberately id-less
  A6 fixtures), so each was given an explicit numeric `id` (`1`, `2`, `3`).
- `src/pages/findings.tsx`, `src/pages/print.tsx`, `src/pages/__tests__/findings-columns-memo.test.tsx`
  — type-only references (`FindingItem[]`, `ColumnDef<FindingItem>`), no object literals, no
  change needed.

`npx tsc --noEmit` exits 0 after the fix, with only that one file's fallout — no other
`FindingItem`- or `ScanLatestResponse`-shaped fixture in the dashboard source or test tree
constructs a non-empty `findings` array.

**Production site flagged, not fixed (out of this plan's `files_modified`):**
`quirk/dashboard/api/routes/scan.py:1421` — `_derive_identity_findings()`'s results are appended
into `session_findings` via `FindingItem(host=..., ..., source=idf.source)` with no `id=` kwarg,
so identity findings genuinely arrive with `id: null` under the now-explicit
`Optional[int] = None` schema. This is a real, already-known A6 source (the plan named it as
"one known to exist"), not a fixture gap — left as-is per plan scope (schemas.py is not in this
plan's `files_modified`).

## RED Transcript (Task 2)

Ran `npm run test -- useFindingStoryline` against the test file before the hook existed:

```
FAIL src/hooks/__tests__/useFindingStoryline.test.tsx [ src/hooks/__tests__/useFindingStoryline.test.tsx ]
Error: Failed to resolve import "../useFindingStoryline" from "src/hooks/__tests__/useFindingStoryline.test.tsx". Does the file exist?
  Plugin: vite:import-analysis
Test Files  1 failed (1)
     Tests  no tests
```

This is the correct RED shape for a hook that does not exist yet (an import-resolution failure,
not a runtime assertion failure) — the test file was written first, covering every behavior
bullet in the plan, then the hook was implemented to make all 9 tests pass.

## Captured URL Prefix (202-07's extractor)

Ran `extractTemplateLiteralPrefix`'s exact regex (`/fetchApi\(\s*`([^$`]+)\$\{/`) against
`src/dashboard/src/hooks/useFindingStoryline.ts`:

```
"/api/findings/"
```

Confirms 202-07's `fixture-coverage.test.ts` extractor will read the literal prefix out of the
source once its `HOOK_TARGETS` entry is added (that entry itself is 202-07's job, not this
plan's).

## Vitest Counts

- **Before this plan:** 46 test files / 351 tests (full suite, prior to `useFindingStoryline.test.tsx` existing).
- **After this plan:** 47 test files / 360 tests — `src/hooks/__tests__/useFindingStoryline.test.tsx`
  contributes the 9 new tests; the other 46 files' pass counts are unchanged (`ExecutiveVerdict.test.tsx`'s
  own test count is unaffected — only its fixture data changed).
- Full suite run: `Test Files  47 passed (47)` / `Tests  360 passed (360)`.
- Scoped run (`npm run test -- use`): `Test Files  5 passed (5)` / `Tests  18 passed (18)`.

## Build / Lint / Test Exit Statuses

- `npx tsc --noEmit` — exit 0.
- `npm run test -- useFindingStoryline` — exit 0, 9/9 passed.
- `npm run test` (full frontend suite) — exit 0, 360/360 passed.
- `npm run lint` — exit 0 (`eslint .` clean of errors; one pre-existing, unrelated warning in
  `ConnectorsPanel.test.tsx` about an unused `eslint-disable` for `no-bitwise` — out of this
  plan's scope per the Scope Boundary rule, not touched).
- `npm run build` — **not run**, per the plan's explicit hard constraint: this plan touches no
  rendered component, so no build/statics step is required.

## Statics

No `.tsx` component rendering changed (only a hook, a type file, and two test files were
touched). `git status --short quirk/dashboard/static` is empty before and after — no statics
diff was produced, confirmed rather than silently skipped.

## Deviations from Plan

None — plan executed exactly as written. Both auto-fix rules that could plausibly apply were not
needed:

- No Rule 1/2/3 fixes were required beyond the plan's own explicitly-anticipated `tsc` fallout
  (which the plan itself instructed be discovered and fixed, not an unplanned deviation).
- One lint error was introduced and self-corrected during Task 2 authoring (a
  `no-constant-binary-expression` on `Number(params.id) ?? 7` in the test's MSW handler, since
  `params.id` is always a string and the `?? 7` fallback was dead code) — fixed inline before
  the GREEN commit, so it never reached a commit and is not tracked as a deviation.

## Authentication Gates

None encountered.

## Known Stubs

None. Both artifacts are fully wired: the type contract has no placeholder fields, and the hook
has no mock data path — it always calls the real `fetchApi` endpoint (mocked only in tests via
MSW).

## Threat Flags

None. This plan implements exactly the two mitigations threat-modeled for it (T-202-04 title
URL-encoding, tested for `&`/`?`/`#`/non-ASCII round-trip; T-202-05 one fixed error string, no
status/URL/exception leakage) and introduces no new network endpoint, auth path, or schema
change — the actual `/api/findings/{id}/storyline` route is 202-03's responsibility.

## Self-Check: PASSED

- FOUND: `src/dashboard/src/types/api.ts` (FindingStoryline + corrected FindingItem.id)
- FOUND: `src/dashboard/src/hooks/useFindingStoryline.ts`
- FOUND: `src/dashboard/src/hooks/__tests__/useFindingStoryline.test.tsx`
- FOUND: `src/dashboard/src/components/__tests__/ExecutiveVerdict.test.tsx` (modified)
- FOUND commit `c607679f` (feat: FindingStoryline + FindingItem.id)
- FOUND commit `487660e1` (test: RED)
- FOUND commit `9d3b2c83` (feat: GREEN)
- FOUND commit `fe71ea5e` (docs: 202-02-T1 → green)
- FOUND commit `15c9dc73` (docs: 202-02-T2 → green)

## Confirmation of Override 1

No mutating GSD verb was invoked (`phase.complete`, `milestone.complete`,
`requirements mark-complete`, any `state.*`/`roadmap.*` write verb). `.planning/STATE.md`,
`.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were not touched by this plan. All git
operations used plain `git add` / `git commit` (with `-f` only for the already-tracked,
gitignored `202-VALIDATION.md`, per the documented repo gotcha that plain `add` on an
already-tracked ignored path can still require `-f` to stage cleanly without the wrapper's false
failure).
