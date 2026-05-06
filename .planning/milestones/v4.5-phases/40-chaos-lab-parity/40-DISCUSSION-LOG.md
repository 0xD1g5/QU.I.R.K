# Phase 40: Chaos Lab Parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-29
**Phase:** 40-chaos-lab-parity
**Areas discussed:** Oracle scope & schema, README rewrite vs. docs/chaos-lab.md split, lab.sh `all` fix scope, v4.0–4.2 profile coverage

---

## Oracle scope (`expected_results_v4.md` vs. v3)

| Option | Description | Selected |
|--------|-------------|----------|
| Superseding — v4 covers EVERY profile (v4.0–4.4), v3 archived | v4.md fully replaces v3.md. v3 stays for reference. One source of truth going forward. | ✓ |
| Additive — v4 covers ONLY v4.3+v4.4 additions | v3 still authoritative for v4.0–4.2. Smaller diff, two docs to maintain. | |
| Single rename to `expected_results.md` | Drop version suffix entirely; living doc. | |

**User's choice:** Superseding.
**Notes:** Resolved gray area #4 simultaneously — v4.0–4.2 profiles ARE included in the v4 oracle. v3 gets a historical-note header.

---

## Oracle schema (DAR / config-introspection findings)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-profile sub-tables with category-tuned columns | Mirrors Phase 39 DAR dashboard pattern. Most readable, matches scanner output structure. | ✓ |
| Single extended v3-style table with optional DAR columns | Keep one big port-anchored table; add nullable columns. Simplest diff but visually noisy. | |
| v3-style port table + separate config-introspection sections per DAR profile | Hybrid that respects two finding types. | |

**User's choice:** Per-profile sub-tables with category-tuned columns.
**Notes:** Network-listener profiles still use the v3 port-anchored schema (proven format); only DAR/config profiles get tuned columns. Hybrid `storage` (legacy) profile mixes both because it predates the v4.3 split.

---

## README authoritative profile catalog

| Option | Description | Selected |
|--------|-------------|----------|
| README = authoritative profile catalog; docs/chaos-lab.md = deep operator guide | Rewrite README as canonical at-a-glance reference; demote docs/chaos-lab.md. | |
| README = quick-start + profile summary table; docs/chaos-lab.md = full prose authority | Compact table in README, prominent link, prose stays in docs/. | ✓ |
| Keep README minimal; expand docs/chaos-lab.md to cover all profiles | Risk: doesn't match literal roadmap text. | |

**User's choice:** README = quick-start + summary table; docs/chaos-lab.md remains full prose authority.
**Notes:** Implication: docs/chaos-lab.md must also be updated in this phase to cover v4.3+v4.4 profiles, otherwise the "full operator guide" link points at incomplete docs. Locked into scope (D-10).

---

## Oracle cross-reference from README/docs

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — README profile table cells link to oracle anchors | Tight coupling; cells point to `## Profile: <name>` anchors. | ✓ |
| Yes — prominent link from README intro + docs/chaos-lab.md, no row-level links | Lower coupling, less link maintenance. | |
| Oracle is standalone — not linked | Decouples docs from oracle. | |

**User's choice:** Tight coupling — per-row anchor links.
**Notes:** README rows become navigable into the oracle. Renaming a profile section in the oracle requires updating the matching README row (acceptable maintenance cost).

---

## lab.sh change scope

| Option | Description | Selected |
|--------|-------------|----------|
| Tight — only fix ALL_PROFILES + verify status/logs | Minimum needed for criteria #1 and #2. | |
| Tight + add `./lab.sh profiles` listing command | Above plus a discoverability subcommand. | ✓ |
| Broader — add per-profile up shortcut (`./lab.sh up database`) | More ergonomic, but two ways to do the same thing. | |

**User's choice:** Tight + add `./lab.sh profiles`.
**Notes:** Single small additive change reuses the same parser as `all`. PROFILE_ARGS env-var pattern stays the only way to scope `up`.

---

## Profile-list source of truth (lab.sh)

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-coded list in lab.sh | Current pattern. Drift recurs. | |
| Dynamically derive from docker-compose.yml at runtime | Lab.sh stays in sync automatically; future drift impossible. | ✓ |
| Hard-coded + CI/test guard asserting parity | Best of both, more pieces. | |

**User's choice:** Dynamic derivation from docker-compose.yml.
**Notes:** Solves the recurring CLAUDE.md "Chaos Lab Maintenance" rule's most common failure mode at the root — every chaos lab phase to date has added profiles without updating ALL_PROFILES. Structural fix > recurring discipline.

---

## Claude's Discretion

- Exact "Expected condition / tag" string values — must match QUIRK scanner finding tags; researcher to enumerate from `quirk/scanners/` source.
- yq vs. grep parser choice in lab.sh — both acceptable; planner picks most portable.
- README intro paragraph wording / tone.
- Whether `storage` legacy profile gets explicit "deprecated, see database/storage-s3/vault" note in oracle.

## Deferred Ideas

- Per-profile `up` shortcut (`./lab.sh up <profile>`) — rejected for this phase; revisit in a future ergonomics pass if needed.
- CI/test guard for compose ↔ lab.sh parity — made unnecessary by dynamic derivation; fallback only.
- Dropping `_v4` version suffix — rejected, roadmap names the file explicitly.
