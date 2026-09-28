# GSD plan-phase's frontend detector is unanchored and fires on EVERY phase of this project

**Found:** 2026-09-28, while executing `/gsd-plan-phase 211 --skip-ui` (verifying that `--skip-ui`
was genuinely necessary rather than cargo-culted).

**Severity:** Medium — not a data-corruption defect, but it makes a HARD-EXIT gate
unconditionally true for this repository, so the gate can only ever be satisfied by suppressing
it. A gate that always fires carries no information, and the habitual `--skip-ui` it forces would
also suppress the gate on a phase that genuinely needs a UI-SPEC.

## What was found

`$HOME/.claude/get-shit-done/workflows/plan-phase.md` §5.6 (UI Design Contract Gate) detects
frontend phases with an **unanchored, case-insensitive** alternation:

```bash
PHASE_SECTION=$(gsd-sdk query roadmap.get-phase "${PHASE}")
echo "$PHASE_SECTION" | grep -iE "UI|interface|frontend|component|layout|page|screen|view|form|dashboard|widget" > /dev/null 2>&1
HAS_UI=$?
```

The first alternative is the bare two-letter string `UI`, with no word boundary. Reproduced against
Phase 211 — a phase touching **only Python and Markdown**, with no frontend surface whatsoever:

```
$ gsd-sdk query roadmap.get-phase 211 | grep -ioE "UI|interface|...|widget" | sort | uniq -c
   6 ui
$ echo "HAS_UI=$?"   # the workflow's own test
HAS_UI=0             # 0 == frontend indicators found
```

All six matches are **substrings inside unrelated words**:

| Matched text | Real word |
|---|---|
| `req`**`ui`**`res` | requires |
| `gen`**`ui`**`ne` | genuine |
| `q`**`ui`**`rk-output` | quirk-output |
| `q`**`ui`**`rk/intelligence` | quirk/intelligence |

A word-anchored form of the same grep (`grep -ioE "\b(UI|interface|...)\b"`) returns **zero
matches** on the identical input — the honest answer.

## Why this is permanent for this repository

The project is named **QU.I.R.K.**, and its Python package is `quirk/`. Every ROADMAP phase section
cites a `quirk/...` path or the string `quirk-output/`. **`q-u-i-r-k` contains `u-i`.** So
`HAS_UI=0` is guaranteed for every phase this project will ever have, including pure-backend ones.

Consequence: §5.6 hard-exits with *"⚠ UI-SPEC.md missing for Phase N — Exit the plan-phase
workflow. Do not continue."* unless `--skip-ui` is passed. `--skip-ui` is therefore **mandatory
boilerplate** on this repo, which is exactly how a real UI phase's missing UI-SPEC would slip
through unnoticed.

## Defect class

This is the **same unanchored-matching class** the project has now been bitten by repeatedly:

- `CLAUDE.md` §GSD `state.*` Verb Integrity, TOOL-01 — the unanchored `**Field:**` regex in
  `stateReplaceField()`, which matched a field name quoted mid-sentence in prose.
- `.planning/phases/211-denominator-correctness/.continue-here.md`, Critical Anti-Patterns —
  *"Unanchored grep invents findings"*: `grep -o "D-[0-9][0-9]"` matched the tail of
  `DASHBOARD-006` and produced a phantom `D-00` decision.

Both of those are in the *project's* code and planning artifacts. **This instance is in the GSD
toolchain's own workflow**, which is a new location for the same class — and it is a location the
project cannot patch by editing its own files.

## Feasibility & Effort

- **Root cause: CONFIRMED.** Reproduced directly with the workflow's own command, with the
  anchored form returning zero as the control. No inference.
- **Fix in the upstream workflow: CONFIRMED feasible, effort S.** Anchor the alternation —
  `grep -iE "\b(UI|interface|frontend|component|layout|page|screen|view|form|dashboard|widget)\b"`.
  Note anchoring alone leaves `view`, `form` and `page` as plausible false positives in prose about
  a "view" of data or a "form" of penalty, so a stronger fix would drop the bare `UI` alternative
  in favour of `UI-SPEC|\bUI\b` and require two or more distinct hits before hard-exiting.
- **Local mitigation: CONFIRMED, effort S, already in force.** Keep passing `--skip-ui` for
  backend phases. **Unknown:** whether a local patch to `plan-phase.md` survives `/gsd-update`
  regeneration — the `~/.claude/gsd-local-patches/` durability layer described in CLAUDE.md covers
  `bin/lib/*.cjs`, and it is UNVERIFIED whether it extends to `workflows/*.md`.
- **Spike needed:** no.

## Recommended action

1. File upstream against `open-gsd/gsd-core` (the live successor; `gsd-build/get-shit-done` is
   archived and redirects there). This is a separate defect from issue #4243's bold-field class —
   same *class*, different file and different entry point — so it warrants its own issue rather
   than a comment on that one.
2. Until then, treat `--skip-ui` on this repo as **required boilerplate for backend phases**, and
   — because the gate can no longer tell you — decide whether a phase needs a UI-SPEC by reading
   the phase's actual `files_modified` surface, never by trusting §5.6's verdict.
