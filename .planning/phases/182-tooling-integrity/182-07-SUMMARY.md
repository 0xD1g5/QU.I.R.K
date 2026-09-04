---
phase: 182-tooling-integrity
plan: 07
subsystem: tooling
tags: [gsd-tools, node, pytest, regex-anchoring, durability, defect-class-enumeration]

# Dependency graph
requires:
  - phase: 182-01
    provides: "Bug A write-side patch (stateReplaceField), GSD_TOOLCHAIN_AVAILABLE skip idiom, --cwd argv contract, gsd-local-patches/ + gsd-pristine/ convention"
  - phase: 182-06
    provides: "stateExtractField anchored, Session-scoping guard widened, focusPattern anchored, durability layer re-seeded to 72 required lines for state.cjs"
provides:
  - "A run-time-generated, dispositioned enumeration gate (test_bold_field_regex_class_is_fully_dispositioned) over every bold-field regex construction in state.cjs and state-document.generated.cjs"
  - "boldProgressPattern (cmdStateUpdateProgress, a real .planning/STATE.md write path) anchored and newline-safe -- the third instance of the Bug A defect class"
  - "A NEW, previously-undocumented site found by the scan: cmdStateGet's unanchored boldPattern, dispositioned accepted-read-only"
  - "Durability layer re-seeded; verify-reapply-patches.cjs reports {checked:2, failures:0} against a grown state.cjs required-line count (72 -> 86)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Run-time-generated occurrence set, ledger-supplies-disposition-only: the gate reads the installed .cjs source with Path.read_text() every run and asserts a matching, non-empty-reason ledger entry for each occurrence; the ledger dict in the test body is never the occurrence source, only the disposition source. This is the design response to three hand-derived enumerations (182-01, then 182-06's planner draft, then 182-07's own <interfaces> orientation list) each independently missing an instance of the same defect class."
    - "Ledger keyed by (relative file path, literal field-name text, enclosing function name) -- never by line number. The enclosing-function lookup (scan backward for the nearest `function NAME(` declaration) exists specifically to disambiguate two textually-identical template-literal occurrences (stateExtractField and stateReplaceField both literally contain `${escaped}` between the markers) without resorting to a line index."
    - "Dual-marker scan for two distinct escaping conventions in the same defect class: `\\*\\*Field:\\*\\*` (plain regex literal, 4 raw chars) in state.cjs vs. `\\\\*\\\\*${expr}:\\\\*\\\\*` (template-literal string passed to new RegExp, 6 raw chars) in state-document.generated.cjs. A dedicated zero-occurrence guard fails by naming the escaping-convention cause specifically, rather than surfacing downstream as a confusing 'stale ledger row' error."

key-files:
  created: []
  modified:
    - "tests/test_gsd_state_patch.py"
    - "~/.claude/get-shit-done/bin/lib/state.cjs (outside repo, not git-tracked)"
    - "~/.claude/gsd-local-patches/get-shit-done/bin/lib/state.cjs (outside repo, not git-tracked)"

key-decisions:
  - "The run-time scan found a genuinely NEW bold-field site not present in the plan's <interfaces> orientation list: cmdStateGet's `boldPattern` (state.cjs line 101, backing the read-only `state get <field>` CLI command). This is disclosed prominently because it is a live, empirical instance of the exact failure mode the plan warns about -- a hand-derived list read as complete while being partial -- caught specifically because the design mandated generating the occurrence set from source rather than trusting the list. Dispositioned accepted-read-only: the match result only ever reaches output() for stdout display, never a STATE.md write."
  - "Ledger keys use (relpath, field-name-text, enclosing-function) rather than (relpath, field-name-text) alone, because state-document.generated.cjs's two occurrences (stateExtractField, stateReplaceField) are textually IDENTICAL between the markers (`${escaped}`) -- the function name is the only textual discriminator available without falling back to a line number."
  - "The three session-extraction sites in cmdStateSnapshot (Last Date, Stopped At, Resume File) and the plan's <interfaces>-listed ~line 708 `state json` session-header matcher (`/##\\s*Session\\s*\\n/i`) are NOT the same construct: the session-header matcher has no `\\*\\*Field:\\*\\*` shape at all (it matches a `##` markdown header, not a bold field), so it does not appear in this gate's scan or ledger. It remains dispositioned informationally in this SUMMARY's enumeration table (accepted, read-only, unchanged from 182-06) rather than folded into _BOLD_FIELD_DISPOSITIONS, since including a non-matching construct in a ledger keyed by 'occurrences the scan finds' would immediately trip the plan's own stale-ledger-row guard."

requirements-completed: [TOOL-04]

duration: 55min
completed: 2026-09-04
---

# Phase 182 Plan 07: TOOL-04 Gap-Closure — Bold-Field Defect-Class Enumeration Gate

**Closed the remaining Bug-A-shaped defect class instance by instance rather than one instance at a time: enumerated every `**Field:**`-shaped regex construction in the two STATE.md-owning libs via a run-time source scan (not a hand-written list), locked it with a dispositioned gate, anchored the one remaining write-path instance (`boldProgressPattern`), and re-seeded the durability layer.**

## Full Enumeration Table

One row per hit family, from `grep -rn '\*\*' ~/.claude/get-shit-done/bin/lib/*.cjs` (broad, all files) narrowed to the two files this gate scans, PLUS the two-convention Python scan the gate actually runs (`_MARK4` / `_MARK6`) which additionally found the `cmdStateGet` site the grep-based orientation list did not surface as a distinct row:

| File | Function | Field / construct | Convention | Disposition | Reason |
|---|---|---|---|---|---|
| `state-document.generated.cjs` | `stateExtractField` | `${escaped}` | 6-char template-literal | **anchored** | TOOL-04 read-side twin of Bug A; anchored 182-06 |
| `state-document.generated.cjs` | `stateReplaceField` | `${escaped}` | 6-char template-literal | **anchored** | Bug A original write-side instance; anchored 182-01 |
| `state.cjs` | `cmdStateBeginPhase` | `Current focus` | 4-char regex-literal | **anchored** | 182-06 Edit C; write path |
| `state.cjs` | `cmdStateUpdateProgress` | `Progress` (`boldProgressPattern`) | 4-char regex-literal | **anchored** | T-182-25/TOOL-04 third write-path instance; **anchored by this plan's Task 2** |
| `state.cjs` | `cmdStateSnapshot` | `Last Date` | 4-char regex-literal | accepted-read-only | T-182-29: feeds `state json` session object, display only |
| `state.cjs` | `cmdStateSnapshot` | `Stopped At` | 4-char regex-literal | accepted-read-only | T-182-29: same read path as Last Date |
| `state.cjs` | `cmdStateSnapshot` | `Resume File` | 4-char regex-literal | accepted-read-only | T-182-29: same read path as Last Date |
| `state.cjs` | `cmdStateGet` | `${fieldEscaped}` (`boldPattern`) | 6-char template-literal | accepted-read-only | **NEW SITE, found by the run-time scan, absent from the plan's orientation list.** Backs the read-only `state get <field>` CLI command; result only reaches `output()`, never a STATE.md write. |
| `state.cjs` | (module-scope, `buildStateFrontmatter`'s guard) | `/##\s*Session\s*\n/i` (session-HEADER matcher, not a `**Field:**` construct) | n/a — different regex shape | accepted, informational only | Already widened by 182-06 Edit B to the `^##\s+Session\b...` form for the frontmatter-write path; the `state json` sibling at ~line 708 is a separate, still-unpatched instance of the SAME header-matching pattern, but it does not construct a bold field and so is out of scope for this gate's ledger. Recorded here per the plan's explicit instruction to enumerate it, not silently omit it. |
| `commands.cjs:911` | (status report) | `Last Activity` | 4-char regex-literal | accepted, out of gate scope | Read-only console display, not one of the two durability-registered files; patching it would grow the registered patch set from 2 files to 4 with no integrity gain (per the plan's stated blast-radius call, T-182-29) |
| `init.cjs:1487` | (resume-hint display) | `Paused At` | 4-char regex-literal | accepted, out of gate scope | Same reasoning as `commands.cjs` above |
| `core.cjs`, `roadmap.cjs`, `phase.cjs`, `init.cjs`, `decisions.cjs`, `milestone.cjs`, `gsd2-import.cjs` | various | `Goal`, `Depends on`, `Mode`, `Requirements`, `Tasks`, `D-*` decision IDs, etc. | mixed | accepted, out of gate scope, grouped | These parse `ROADMAP.md`/`PLAN.md`, not `STATE.md`; grouped as a single row per the plan's explicit instruction rather than one row each |

The gate itself (`_BOLD_FIELD_DISPOSITIONS` in `tests/test_gsd_state_patch.py`) contains exactly the first 8 rows above (the two STATE.md-owning files' bold-field constructs); the remaining rows are recorded here for human visibility per the plan's instruction but are correctly excluded from the ledger since including a non-matching construct (the `##Session` header row) or an out-of-file construct (`commands.cjs`/`init.cjs`/etc.) would immediately trip the gate's own stale-ledger-row guard.

## Task 1: Enumerate and lock with a dispositioned gate

Added to `tests/test_gsd_state_patch.py`:
- `_MARK4` / `_MARK6` — literal marker strings for the two escaping conventions
- `_enclosing_function_name()` — text-based (backward scan for `function NAME(`), used only to disambiguate two textually-identical occurrences, never as a substitute for line-based keying
- `_has_m_flag()` — checks the `/m` flag under either `new RegExp(pattern, 'im')` or `/pattern/im` conventions
- `_scan_bold_field_occurrences()` — the run-time scan itself; skips `//`-prefixed lines; returns `{relpath, line_no, line, field_text, function, convention, var_name}` per hit
- `_BOLD_FIELD_DISPOSITIONS` — the 8-entry ledger, keyed `(relpath, field_text, function)` -> `(disposition, reason)`
- `test_bold_field_regex_class_is_fully_dispositioned` — guarded by the existing `_GSD_SKIP`; asserts (1) every occurrence matches a ledger entry, (2) every ledger entry matches an occurrence (no stale rows), (3) `state-document.generated.cjs` contributes at least one occurrence (convention-blindness guard)

**Verbatim RED output** (run before Task 2, with `boldProgressPattern` ledgered `"anchored"` while the source was still unpatched):

```
FAILED tests/test_gsd_state_patch.py::test_bold_field_regex_class_is_fully_dispositioned
AssertionError: ('bin/lib/state.cjs', 'Progress', 'cmdStateUpdateProgress') (variable 'boldProgressPattern', line 426) is ledgered 'anchored' but its line has no `^` anchor: '    const boldProgressPattern = /(\*\*Progress:\*\*\s*).*/i;'
assert '^' in '    const boldProgressPattern = /(\*\*Progress:\*\*\s*).*/i;'
tests/test_gsd_state_patch.py:937: AssertionError
1 failed, 9 passed in 0.55s
```

The failure names `boldProgressPattern`, its containing function, and its line number explicitly -- a real, diagnosable RED, not a collection error.

**Gate-sensitivity demonstration (convention-blindness guard):** temporarily narrowed the scan's marker loop to `_MARK4` only (single-backslash convention) in a scratch copy, re-ran the same test, and observed:

```
FAILED tests/test_gsd_state_patch.py::test_bold_field_regex_class_is_fully_dispositioned
Failed: the run-time scan collected ZERO bold-field occurrences from state-document.generated.cjs. That file uses the template-literal-string escaping convention (`\\*\\*${expr}:\\*\\*`, six raw characters), not the plain regex-literal convention (`\*\*Field:\*\*`, four raw characters) that state.cjs uses. ... Fix the scan's marker set (_MARK4/_MARK6), not the ledger.
1 failed in 0.11s
```

The scratch file was then discarded and the original restored, confirmed byte-identical via `diff` against a pre-scratch backup.

Confirmed via direct execution:
```
grep -c '\*\*' ~/.claude/get-shit-done/bin/lib/state-document.generated.cjs        -> 0
grep -c '\\\*\\\*' ~/.claude/get-shit-done/bin/lib/state-document.generated.cjs    -> 2
```
(shown here with shell-escaping collapsed one level relative to the raw grep invocation; both commands confirm the single-backslash convention cannot see that file at all, while the double-backslash convention finds its two occurrences.)

Acceptance-criteria greps, all confirmed:
- `grep -c "_BOLD_FIELD_DISPOSITIONS" tests/test_gsd_state_patch.py` -> `7` (>= 2 required)
- `grep -c "focusPattern" tests/test_gsd_state_patch.py` -> `1`
- `grep -c "state-document.generated.cjs" tests/test_gsd_state_patch.py` -> `27`
- `grep -v '^\s*#' tests/test_gsd_state_patch.py | grep -c "LINENO"` -> `0`
- `.venv/bin/pytest tests/test_cli_helper_usage.py -q` -> `2 passed` (baseline unchanged)

Committed as `78c5d094`.

## Task 2: Anchor `boldProgressPattern`

**Before:**
```js
const boldProgressPattern = /(\*\*Progress:\*\*\s*).*/i;
```

**After:**
```js
const boldProgressPattern = /^(\s*\*\*Progress:\*\*[ \t]*).*$/im;
```

`LOCAL PATCH (2026-09-03)` comment added, naming TOOL-04, the write path (`updateProgress` -> `readModifyWriteStateMd`), the `\s*`-spans-newline detail, and the upstream issue (`open-gsd/gsd-core#4243`). No other code in `updateProgress` changed -- the `.replace()` callback already reconstructs from the captured `prefix` group alone.

**Verbatim GREEN output** (full module, after the patch):
```
.venv/bin/pytest tests/test_gsd_state_patch.py -q
..........                                                               [100%]
10 passed in 0.53s
```

10 passed = the 9-test 182-06 baseline plus the new gate, now green. `test_begin_phase_does_not_read_body_prose_as_machine_fields` re-run in isolation also passes (1 passed, 9 deselected) -- confirming the `state.cjs` edit did not regress 182-06's guarantee.

Acceptance-criteria greps, all confirmed:
- `grep -c "boldProgressPattern = /\^" state.cjs` -> `1`
- `grep -c 'boldProgressPattern = /(' state.cjs` -> `0` (old unanchored form gone, not merely supplemented)
- `grep -c "LOCAL PATCH (2026-09-03)" state.cjs` -> `4` (Bug B, 182-06 session guard, 182-06 Current-focus anchor, this plan's Progress anchor)
- `grep -c "focusPattern = /\^" state.cjs` -> `1` (182-06 Edit C undisturbed)
- `node -e "require('state.cjs')"` -> exit `0`

This file lives outside the QUIRK git repository (`~/.claude/get-shit-done/bin/lib/state.cjs`), so there is no QUIRK commit for this task individually -- consistent with how 182-06 handled the same class of edit, folded into the plan's closing docs commit below.

## Task 3: Re-seed the durability snapshot

**Pristine-hash comparison** (must equal `backup-meta.json`'s recorded `pristine_hashes`, confirming pristine baselines untouched):
```
sha256(gsd-pristine/.../state-document.generated.cjs) = 6157fcee866734c9931d3d49ec06e46951c59ed6fb5926667c07ede4dba31c38  -- matches
sha256(gsd-pristine/.../state.cjs)                    = 2f0fa21e5b9587176168f65c7e788d61edb32700de96845ba7b004b4d31c2155  -- matches
```

**Byte-copy re-seed:** `~/.claude/gsd-local-patches/get-shit-done/bin/lib/state.cjs` overwritten with the Task-2-patched installed file. `diff` against the installed file: no output (byte-identical). `state-document.generated.cjs`'s snapshot (182-06's re-seed) verified still byte-identical to installed -- untouched by this plan, as expected (this plan edits `state.cjs` only).

**Per-file required-line counts** (via the verifier's own `computeUserAddedLines`, installed-vs-pristine, matching what the freshly-reseeded snapshot now equals):
- `state-document.generated.cjs`: **19** required lines (182-06 recorded 19) -- unchanged, as expected, since this plan does not touch that file.
- `state.cjs`: **86** required lines (182-06 recorded **72**) -- **grew by 14**, confirming the copy took and reflects this plan's new `LOCAL PATCH` comment block plus the anchored `boldProgressPattern` line. `grep -c "focusPattern = /\^" gsd-local-patches/.../state.cjs` -> `1`, confirming 182-06's Edit C is still present in the re-seeded snapshot alongside this plan's hunk.

**Verifier result after re-seed:**
```
node ~/.claude/get-shit-done/bin/verify-reapply-patches.cjs \
  --patches-dir ~/.claude/gsd-local-patches --config-dir ~/.claude \
  --pristine-dir ~/.claude/gsd-pristine --json
{
  "checked": 2,
  "failures": 0,
  "results": [
    {"file": "get-shit-done/bin/lib/state-document.generated.cjs", "status": "ok", "missing": [], "reason": null},
    {"file": "get-shit-done/bin/lib/state.cjs", "status": "ok", "missing": [], "reason": null}
  ]
}
```

`.venv/bin/pytest tests/test_gsd_state_patch.py -q` -> `10 passed` (re-run after the re-seed).

## Full Verification Sweep

- `.venv/bin/pytest tests/test_gsd_state_patch.py -q` -> `10 passed`
- `.venv/bin/pytest tests/test_cli_helper_usage.py -q` -> `2 passed` (GATE-03's baseline unchanged -- no raw `subprocess`/`cwd=` call site introduced; the scan reads files with `Path.read_text` and spawns nothing)
- `node ~/.claude/get-shit-done/bin/verify-reapply-patches.cjs ... --json` -> `{"checked":2,"failures":0}`
- `git status --porcelain .planning/ROADMAP.md` -> empty (this plan does not touch the roadmap)
- `.venv/bin/pytest tests/test_skip_registry.py -q` -> the sole expected failure (`test_no_unregistered_skips`, DEFER-172-01, Phase 184's) and nothing else
- `python -m compileall tests/test_gsd_state_patch.py` -> compiles clean

## Known Stubs

None.

## Threat Flags

None -- no new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries. This plan extends an existing enumeration/detection surface (bold-field regex anchoring in `state.cjs`/`state-document.generated.cjs`) and anchors one more write-path regex within an already-identified trust boundary (body prose -> frontmatter/body fields).

## Deviations from Plan

### Auto-fixed Issues (Rule 2 -- auto-add missing critical functionality)

**1. A NEW, previously undispositioned bold-field site was found by the mandated run-time scan: `cmdStateGet`'s `boldPattern` (state.cjs line 101)**
- **Found during:** Task 1, while building the scan (before writing the ledger).
- **Issue:** `cmdStateGet` (the `state get <field>` CLI command) constructs `new RegExp(\`\\*\\*${fieldEscaped}:\\*\\*\\s*(.*)\`, 'i')` -- unanchored, no `^`, no `/m`, using the 6-char template-literal convention. Neither the plan's `<interfaces>` orientation list nor any prior plan's SUMMARY mentions this site.
- **Fix:** Dispositioned as `accepted-read-only` in `_BOLD_FIELD_DISPOSITIONS` with a written reason: the match result only ever reaches `output()` for stdout display via the `state get` diagnostic command, never a STATE.md write, matching the same accepted blast-radius class as `commands.cjs`/`init.cjs`'s read-only sites (T-182-29). Not patched, since patching it would not change scope (it is already inside a durability-registered file) but the plan's Task 2 explicitly scoped the write-path fix to `boldProgressPattern` alone (T-182-25); expanding that scope was not requested and the site poses no STATE.md-corruption risk.
- **Files modified:** `tests/test_gsd_state_patch.py` (ledger entry only; no `.cjs` change).
- **Commit:** `78c5d094` (Task 1).
- **Why this is disclosed prominently rather than folded in silently:** this is the third time in Phase 182 that a hand-derived enumeration (182-01's original patch scope, then this plan's own `<interfaces>` orientation list) missed an instance of the same defect class. The run-time-scan design caught it specifically because the gate never trusts a written list -- which is the empirical proof the plan asked for that this design choice is not decorative.

### Non-issues confirmed, not fixed (in scope per plan's explicit instruction)
- `state.cjs`'s `state json` session-extraction sites (`Last Date`, `Stopped At`, `Resume File`, ~lines 711-716) and the `~line 708` session-HEADER matcher were read and confirmed unpatched, per the plan's explicit blast-radius disposition (T-182-29) and because the header matcher is not a bold-field construct in the first place.
- `commands.cjs`, `init.cjs`, and the `ROADMAP.md`/`PLAN.md`-parsing sites in `core.cjs`/`roadmap.cjs`/`phase.cjs`/`decisions.cjs`/`milestone.cjs`/`gsd2-import.cjs` were confirmed present via the informational full-repo grep, and left unpatched as explicitly scoped by the plan (T-182-29) -- they are outside the two durability-registered files.

## Self-Check: PASSED

- `tests/test_gsd_state_patch.py` -- FOUND, contains `_BOLD_FIELD_DISPOSITIONS` (count 7), `test_bold_field_regex_class_is_fully_dispositioned` (count 1), `cmdStateGet` (count >=1)
- `~/.claude/get-shit-done/bin/lib/state.cjs` -- FOUND, contains `LOCAL PATCH (2026-09-03)` (count 4), anchored `boldProgressPattern = /^`
- `~/.claude/gsd-local-patches/get-shit-done/bin/lib/state.cjs` -- FOUND, byte-identical to installed `state.cjs` (`diff` empty)
- Commit `78c5d094` -- FOUND: `git log --oneline --all | grep -q 78c5d094` -> match
- `git status --porcelain .planning/ROADMAP.md` -- empty, confirmed untouched
- `node ~/.claude/get-shit-done/bin/verify-reapply-patches.cjs ... --json` -- `{"checked":2,"failures":0}`, confirmed live
