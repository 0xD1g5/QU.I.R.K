---
title: audit-open's counts.todos is capped at 5 by a display slice — understates deferred work at milestone close
created: 2026-09-27
source: v5.24 milestone-close pre-flight (found by cross-checking the count against `ls`, not by a report)
severity: high
area: gsd toolchain — gsd-sdk query audit-open
status: pending
---

## The bug

`gsd-sdk query audit-open` reported `counts.todos: 5` while `.planning/todos/pending/` held **32**
files. The count is not a display limit that leaves the count intact — **the count itself is wrong.**

In `query/audit-open.js`:

```js
const mdFiles  = files.filter(e => e.isFile() && e.name.endsWith('.md'));
const results  = [];
const displayFiles = mdFiles.slice(0, 5);   // <-- line ~181
for (const entry of displayFiles) { ... results.push({...}) }
return results;
```

and then at ~490:

```js
const counts = { ... todos: countReal(todos), ... };
```

`countReal()` is applied to the **already-truncated** array, so `counts.todos` can never exceed 5.
`mdFiles.length` — the real figure — is computed and then discarded.

## Why this is HIGH and not cosmetic

`audit-open` is the **pre-close gate** in the `complete-milestone` workflow. That workflow presents
the counts and asks the operator to choose:

> `[R] Resolve` / `[A] Acknowledge all — document as deferred and proceed` / `[C] Cancel`

and on `[A]` it writes the acknowledged items into `STATE.md` under `## Deferred Items` and records
`Known deferred items at close: {count}` in `MILESTONES.md`. So the defect does three things at once:

1. The operator accepts "5 deferred todos" when there are 32.
2. `MILESTONES.md` — the permanent historical record — gets a wrong count written into it.
3. `STATE.md`'s `## Deferred Items` table is populated from the truncated list, so **27 items become
   invisible** rather than merely uncounted. They are not deferred-and-tracked; they are dropped.

Check prior milestone entries for already-corrupted counts. v5.22's entry reads "Known deferred
items at close: 4" — plausible at the time, but it should be re-derived rather than trusted, since a
`<= 5` value is exactly what this bug produces and is indistinguishable from a true small count.
That indistinguishability is the nastiest property here.

## Scope

Affects the npx install `~/.npm/_npx/<hash>/node_modules/get-shit-done-cc/sdk/dist/query/audit-open.js`.
The `~/.claude/get-shit-done/` install should be checked for the same code — **do not assume one
install's state describes the other**, per CLAUDE.md §TOOL-05.

Other sections use per-type collectors and may carry the same shape; verify each rather than
assuming `todos` is the only one. `verification_gaps`, `debug_sessions` and `quick_tasks` returned
small true values here so the bug would not have shown itself in them.

## Fix shape

Separate display truncation from counting: keep `mdFiles.slice(0, 5)` for the `items` array, and
return `mdFiles.length` as the count (or a `total` alongside a `shown`). Patching the npx install is
**not durable** — the cache dir is content-addressed and a version bump silently creates a new hash
with none of the patch. File upstream.

## Workaround until fixed

At every milestone close, count deferred work from disk and never from this gate:

```bash
ls .planning/todos/pending/*.md | wc -l
```

This is the "measure with a method independent of the audited code" rule again: the gate's own
reporter presented its blind spot as a confident number, and only a different instrument caught it.
