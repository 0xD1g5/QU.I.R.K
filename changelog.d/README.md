# changelog.d — towncrier news fragments

This directory holds **per-PR news fragments** that `towncrier` consumes at release
time to build [`CHANGELOG.md`](../CHANGELOG.md). Every PR that ships a user-visible
change should drop a single fragment here. No more merge conflicts on `CHANGELOG.md`.

## Filename convention

```
<issue-or-pr-id>.<kind>.md
```

- `<issue-or-pr-id>` — the GitHub issue or PR number that motivates the change. If
  there is no associated issue/PR, use a short slug (e.g. `phase-84.feature.md`,
  `v4.10.feature.md`).
- `<kind>` — one of the configured section types (see below).

### Kinds

| Kind      | Renders as       | When to use                                                              |
| --------- | ---------------- | ------------------------------------------------------------------------ |
| `feature` | **Added**        | New capability, scanner, connector, CLI flag, UI surface                 |
| `bugfix`  | **Fixed**        | Behavior correction, crash fix, false-positive/negative repair           |
| `doc`     | **Documentation**| Guide additions, README changes, release-note prep                       |
| `removal` | **Removed**      | Deprecated/dropped feature, removed CLI flag, removed dependency         |
| `misc`    | **Misc**         | Housekeeping (deps bump, refactor, CI). **Content is NOT surfaced** —   |
|           |                  | only the version section gets a "Misc" bullet count.                     |

Examples:

```
42.feature.md
73.bugfix.md
v4.10.feature.md
phase-84.doc.md
```

## Fragment content

A single line of prose describing the change in past tense. Link to the issue/PR
inline if useful. No leading bullet (`towncrier` adds it).

Good:

```
Added PyPI Trusted Publisher workflow with Sigstore attestations
([#142](https://github.com/digirolamo/quirk/pull/142)).
```

Bad:

```
- Fixes stuff  ← past tense, no leading bullet, describe *what* changed
```

## Building the changelog

**Preview** (does not mutate fragments or `CHANGELOG.md`):

```bash
towncrier build --draft --version 4.10.0
```

**Release** (prepends rendered section to `CHANGELOG.md`, deletes consumed
fragments via `git rm`):

```bash
towncrier build --version 4.10.0 --yes
```

The rendered section lands immediately above the `<!-- towncrier release notes start -->`
marker in `CHANGELOG.md`, preserving the file's header.

## See also

- [`pyproject.toml`](../pyproject.toml) — `[tool.towncrier]` config block defines
  the section types, title format, and start-string marker.
- [towncrier docs](https://towncrier.readthedocs.io/) — full reference.
