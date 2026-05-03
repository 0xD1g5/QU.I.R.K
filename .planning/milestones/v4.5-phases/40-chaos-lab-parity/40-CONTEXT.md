# Phase 40: Chaos Lab Parity - Context

**Gathered:** 2026-04-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Bring the chaos lab's three operator-facing surfaces — `lab.sh`, the chaos lab `README.md`, and a new `expected_results_v4.md` oracle — into full parity with every Docker Compose profile shipped through v4.4. Currently `./lab.sh all` silently drops 5 profiles (`vault`, `database`, `storage-s3`, `email`, `broker`); the README is a 28-line stub; the v3 oracle predates the v4.x DAR profiles. Phase output is documentation + a small dynamic profile-listing/all-profile mechanism in `lab.sh`. No new chaos lab services or Docker Compose changes are in scope. The recurring CLAUDE.md "lab.sh must be updated whenever profiles change" rule is addressed *structurally* by replacing the hard-coded `ALL_PROFILES` list with a dynamic derivation from `docker-compose.yml`, so future drift is impossible by construction.

</domain>

<decisions>
## Implementation Decisions

### Oracle Scope (`expected_results_v4.md`)
- **D-01:** v4 oracle is **superseding**, not additive. Covers every profile shipped v4.0 through v4.4. After this phase, `expected_results_v3.md` is no longer authoritative — it stays in the repo for historical reference with a top-of-file note saying so. Consultants and UAT use v4 only.
- **D-02:** Profiles in scope for the v4 oracle (deduped from `docker-compose.yml`):
  - **v4.0 baseline / Phase A:** `phaseA`, `cloud`, `identity`, `pki`
  - **v4.1–4.2 expansions:** `jwt`, `registry`, `source`, `storage` (legacy localstack-kms / vault / pgcrypto trio), `ssh-weak`, `ldaps`, `dnssec`, `saml`, `kerberos`
  - **v4.3 DAR additions:** `database`, `storage-s3`, `vault`
  - **v4.4 additions:** `email`, `broker`
- **D-03:** Oracle file naming: keep the `expected_results_v4.md` filename as specified by the roadmap success criterion. Do NOT rename to a version-less `expected_results.md` — version suffix is roadmap-locked.

### Oracle Schema
- **D-04:** **Per-profile sub-tables with category-tuned columns.** Each profile gets its own H2 section with a column set tuned to what the scanner detects for that profile type. Mirrors the Phase 39 DAR dashboard precedent (per-category tables in `motion.tsx`).
- **D-05:** Network-listener profiles (TLS/HTTP/SSH/etc — `phaseA`, `cloud`, `identity`, `pki`, `jwt`, `registry`, `source`, `ssh-weak`, `ldaps`, `dnssec`, `saml`, `kerberos`, `email`, `broker`) keep the v3-style schema:
  `Port | Service | Expected protocol | Expected condition / tag | Notes`
  This is the proven schema; do not invent a new one for these.
- **D-06:** DAR / config-introspection profiles (`database`, `storage-s3`, `vault`, `storage`) get category-tuned schemas:
  - **`database` profile (postgres-tls, mysql-tls, etc.):** `Port | Service | Engine | Expected protocol | TLS in Transit | Encryption-at-Rest | Expected condition / tag | Notes`
  - **`storage-s3` profile (MinIO):** `Port | Service | Provider | Expected protocol | Encryption Mode | Public Access | KMS Key | Versioning | Expected condition / tag | Notes`
  - **`vault` profile:** `Port | Service | Mount Type | Seal Type | Auto-Unseal | Expected condition / tag | Notes`
  - **`storage` profile (legacy bucket: localstack-kms + vault-dev + pgcrypto-lab):** Hybrid — port table for listeners, plus a small "config-introspection findings" sub-list per service for KMS-key / pgcrypto-extension / vault-seal data. This is the one profile that mixes types because it predates the v4.3 split into clean `database`/`storage-s3`/`vault`.
- **D-07:** Every profile section MUST also include: an H2 anchor (`## Profile: <name>`), a one-line "what this profile exercises" intro, the relevant `./lab.sh` invocation example, and the per-row `Expected condition / tag` values aligned with QUIRK scanner finding tags.

### README Rewrite (`quantum-chaos-enterprise-lab/README.md`)
- **D-08:** Restructure as **quick-start + compact profile summary table + prominent docs link**. NOT a full rewrite duplicating `docs/chaos-lab.md`. Sections, in order:
  1. Title + 1-paragraph what-is-this
  2. Quick Start (single `docker compose ... up -d` example, plus `./lab.sh all` and `./lab.sh up`)
  3. Profile Summary Table — compact, one row per profile (see D-09 schema)
  4. Link block: "Full operator guide → `docs/chaos-lab.md`. Expected scanner findings → `expected_results_v4.md`."
  5. Phase C (mTLS + step-ca) helper section (preserve existing content)
  6. Historical note pointing at `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` (preserve)
- **D-09:** Profile Summary Table column set:
  `Profile | Services / What it ships | Published Ports | Expected Findings (link) | Notes`
  - "Expected Findings (link)" cell links to the matching `## Profile: <name>` anchor in `expected_results_v4.md`. This is the **tight cross-reference** — README rows are navigable into the oracle.
  - Order rows by version era (v4.0 baseline → v4.1/4.2 → v4.3 → v4.4) then alphabetically within era. Helps consultants see what arrived when.
- **D-10:** `docs/chaos-lab.md` remains the **full prose authority**. Because the README split makes it the canonical deep reference, `docs/chaos-lab.md` MUST also be updated in this phase to cover the v4.3+v4.4 profiles (`database`, `storage-s3`, `vault`, `email`, `broker`) — otherwise the README's "full operator guide" link points at incomplete docs. Treat this as in-scope for the phase.

### Oracle Cross-Reference
- **D-11:** **Tight coupling.** Every README profile-summary-table row's "Expected Findings" cell is a markdown link to the matching `## Profile: <name>` anchor in `expected_results_v4.md`. Consultants navigate naturally between inventory (README) and findings detail (oracle).
- **D-12:** `docs/chaos-lab.md` also gets a top-level pointer to `expected_results_v4.md` ("For UAT-grade expected scanner findings, see…") in the intro. No row-level links from `docs/chaos-lab.md` — its narrative format doesn't suit them.

### `lab.sh` Changes
- **D-13:** **Tight scope** — fix `ALL_PROFILES` to cover all 18 profiles, plus add a single new `./lab.sh profiles` listing subcommand. Do NOT add per-profile up shortcuts (`./lab.sh up database`) — keeps the `PROFILE_ARGS=` env-var pattern as the single way to scope `up`, avoiding two-ways-to-do-the-same-thing.
- **D-14:** **Dynamically derive ALL_PROFILES from `docker-compose.yml` at runtime** — no hard-coded list. The `all` command and the new `profiles` command share one parser. This solves the recurring drift problem at the root (the CLAUDE.md "must be updated when profiles change" rule); it cannot drift if the source IS the compose file.
- **D-15:** Profile parser implementation: prefer `yq` if available, fall back to a `grep -E '^\s+profiles:' | tr-and-sort` pipeline. The fallback must handle both inline `profiles: ["a"]` and list `profiles:\n  - a` forms. Output: deduplicated, alphabetically sorted, one profile per line. Planner picks final exact form; both must work without external deps beyond what a chaos lab user already has (Docker + bash).
- **D-16:** New `./lab.sh profiles` subcommand prints the derived list (one per line) so consultants can `./lab.sh profiles | xargs -I{} echo "--profile {}"` or just discover what's available. Add a usage line in the `usage()` heredoc.
- **D-17:** Verify (manually or via a small smoke check) that `./lab.sh status` and `./lab.sh logs <service>` work cleanly against the previously-missing profiles (vault, database, storage-s3, email, broker). The compose-derived approach should make this Just Work, but goal #2 explicitly requires it, so leave evidence in the phase summary.

### Mandatory Companion Updates (per CLAUDE.md "Chaos Lab Maintenance" rule)
- **D-18:** This phase IS itself the lab.sh/README/expected_results sync that CLAUDE.md mandates for any compose change — but it's catching up on five accumulated profile additions at once instead of in-phase. The phase plan must explicitly enumerate the v4.3 (`database`, `storage-s3`, `vault`) and v4.4 (`email`, `broker`) sync work as separate plan steps so each profile's coverage is auditable.
- **D-19:** Per the project's per-phase doc/sync rules (memory-feedback): the phase must include explicit tasks for (a) updating `docs/UAT-SERIES.md` to add a UAT entry for the new v4 oracle as a stable reference, and (b) syncing the relevant Obsidian notes (`Chaos-Lab.md` guide note + Phase-40 phase note + UAT-Series sync).

### Claude's Discretion
- Exact wording of the "expected condition / tag" values — should reuse QUIRK scanner finding tags from `quirk/scanners/` source as the source of truth; researcher to enumerate.
- Whether the `storage` legacy profile gets explicit "deprecated, see `database`/`storage-s3`/`vault`" annotation in the oracle (probably yes, but exact wording is Claude's call).
- Exact yq-vs-grep parser implementation in lab.sh — both shapes are acceptable; pick whichever the planner judges most portable.
- README intro paragraph wording / tone.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 40: Chaos Lab Parity" — Goal, Success Criteria 1–4, dependency on Phase 37, requirement IDs LAB-01..04
- `.planning/REQUIREMENTS.md` — for LAB-01..04 source statements

### Project Rules (MANDATORY)
- `CLAUDE.md` §"Chaos Lab Maintenance" — explicit rule that lab.sh ALL_PROFILES + README.md + expected_results_*.md must be updated together for any chaos lab profile change. This phase IS that catch-up sync, applied structurally so it doesn't recur.
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note + UAT-SERIES.md update + sync + commit. Apply to this phase.

### Chaos Lab Source of Truth
- `quantum-chaos-enterprise-lab/docker-compose.yml` — the **definitional** source for what profiles exist. lab.sh's dynamic parser reads this. Any update to it triggers this rule.
- `quantum-chaos-enterprise-lab/lab.sh` — current bash control script; ALL_PROFILES at lines 63–68 is the broken hard-coded list this phase replaces.
- `quantum-chaos-enterprise-lab/README.md` — current 28-line stub being rewritten.
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — schema reference for network-listener rows; will be archived (historical-note header) after v4 lands.
- `docs/chaos-lab.md` — full prose operator guide; remains the deep authority and must be updated to cover v4.3+v4.4 profiles in this phase.

### Closest Reference Patterns
- `.planning/phases/39-data-at-rest-dashboard-tab/39-CONTEXT.md` §"Per-Finding Columns (Frontend)" — precedent for the per-category column-tuning approach (D-04..06). Same design philosophy applied to a different surface.
- `quirk/scanners/database.py`, `quirk/scanners/storage_s3.py`, `quirk/scanners/vault.py`, `quirk/scanners/email.py`, `quirk/scanners/broker.py` (or current equivalents) — researcher should verify finding-tag names by reading these so oracle's "Expected condition / tag" cells match the actual scanner output strings. Adjust paths if they differ.

### UAT & Obsidian Targets
- `docs/UAT-SERIES.md` — must gain a UAT entry referencing `expected_results_v4.md` as the new oracle.
- Obsidian vault: `20_Dev-Work/QUIRK/Phases/Phase-40-Chaos-Lab-Parity.md` (new), `20_Dev-Work/QUIRK/Guides/Chaos-Lab.md` (re-sync from updated `docs/chaos-lab.md`), `20_Dev-Work/QUIRK/UAT-Series.md` (re-sync from updated `docs/UAT-SERIES.md`).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lab.sh` `compose()` function and `usage()` heredoc — extend, don't replace. New `profiles` subcommand slots into the existing `case` block.
- v3 oracle table schema for network-listener rows — proven format, reuse verbatim for the v4.0–4.2 sections.
- Phase 39 DAR per-category column design — directly portable to oracle DAR sections (D-06).

### Established Patterns
- `set -euo pipefail` + `compose()` wrapper — preserve. Any new bash parser must respect strict-mode (`set -euo pipefail`).
- README delegating prose authority to `docs/chaos-lab.md` — preserved (D-08); README becomes a navigation surface, not a duplicate.
- Per-phase Obsidian + UAT-SERIES sync workflow (CLAUDE.md "Mandatory Phase Completion Steps") — applies.

### Integration Points
- `lab.sh` ↔ `docker-compose.yml`: structural binding via dynamic parser. After this phase, the only way to add a profile to "all" is to add it to docker-compose.yml.
- README ↔ `expected_results_v4.md`: per-row anchor links. Renaming a profile section in the oracle requires updating the matching README row.
- `docs/chaos-lab.md` ↔ `expected_results_v4.md`: top-level pointer only, no per-row coupling.

</code_context>

<specifics>
## Specific Ideas

- The Phase 39 dashboard work (`39-CONTEXT.md`) used per-category tables to handle the DAR/database/storage/vault category split — same structural answer applied here at the oracle layer. The oracle and the dashboard now mirror each other's category model, which is consistent for consultants moving between the report UI and the lab oracle.
- The dynamic profile-derivation idea is explicitly motivated by the recurring CLAUDE.md violation: every prior chaos lab phase added profiles without updating `lab.sh ALL_PROFILES`. Replacing the hard-coded list with a parsed list eliminates the rule's most common failure mode.

</specifics>

<deferred>
## Deferred Ideas

- **Per-profile `up` shortcut (`./lab.sh up database`):** Considered and rejected for this phase to keep `PROFILE_ARGS=` as the single canonical scoping mechanism. Could be revisited in a future ergonomics phase if consultants find env-var prefixing awkward.
- **CI/test guard asserting compose-profiles == lab.sh-known-profiles:** Made unnecessary by D-14 (dynamic derivation). Keep as a fallback option only if the dynamic parser turns out to be infeasible.
- **Drop the `_v4` version suffix entirely (rename to `expected_results.md`):** Considered but rejected — roadmap success criterion #4 explicitly names the file `expected_results_v4.md`. Future phases (v5+) can revisit naming.

</deferred>

---

*Phase: 40-chaos-lab-parity*
*Context gathered: 2026-04-29*
