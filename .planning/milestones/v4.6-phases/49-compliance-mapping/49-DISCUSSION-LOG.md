---
phase: 49-compliance-mapping
type: discussion-log
status: archived
source: /gsd-discuss-phase 49
updated: 2026-05-05
---

# Phase 49 — Compliance Mapping — Discussion Log

**Audience:** human reference (audit / retrospective). Not consumed by
researcher, planner, or executor — those agents read `49-CONTEXT.md`.

**Discussed:** 2026-05-05
**Mode:** default (single-batch question)
**Areas selected for discussion:** all 4

---

## Area 1 — Mapping shape & lookup key

**Question:** What should `COMPLIANCE_MAP` be keyed by, and what shape are its values?

**Options presented:**
1. Key by finding `title`, value = flat list of `{framework, control, version, last_verified, source_url}` *(Recommended)*
2. Key by finding `title`, value = nested dict `{pci_dss: [...], hipaa: [...], fips: [...]}`
3. Add new `category` enum field to findings, key by category

**User selected:** Option 1 — title-keyed flat list

**Rationale captured:** Finding `title` is already a stable string post-Phase 48. Flat list iterates cleanly for both staleness walk and report rendering; no schema change required to finding dict. Avoids the broader blast radius of adding a `category` field.

→ Captured as **D-01** in CONTEXT.md.

---

## Area 2 — Eager vs. lazy attachment

**Question:** Where should compliance references attach to findings?

**Options presented:**
1. Eager — inject `compliance: [...]` in `_build_finding` *(Recommended)*
2. Lazy — renderer-time lookup only
3. Hybrid — lazy for renderer, eager for JSON export

**User selected:** Option 1 — eager attachment in `_build_finding`

**Rationale captured:** Single chokepoint mirrors Phase 48 D-02 / D-06 pattern. JSON exports gain compliance refs automatically (useful for downstream consultant tooling). Future BACK-72 dashboard work reads from existing DTO instead of re-implementing lookup.

→ Captured as **D-02** in CONTEXT.md.

---

## Area 3 — "Compliance Summary" report format

**Question:** How should the report's Compliance Summary section be structured?

**Options presented:**
1. Grouped by framework, full finding→control table *(Recommended)*
2. Grouped by framework, counts-only summary
3. Single matrix table (findings × frameworks)
4. Flat list grouped by severity, framework-tagged

**User selected:** Option 1 — framework-grouped, full finding→control table

**Rationale captured:** Maximum value as audit evidence — assessor receives directly usable control references. Unmapped-findings subsection prevents silent under-reporting (a missing mapping otherwise looks like "no compliance impact" in the framework-grouped view).

→ Captured as **D-03** in CONTEXT.md.

---

## Area 4 — Staleness check + CLI subcommand wiring

**Question:** How should the 12-month staleness check + `quirk compliance status` CLI subcommand be wired?

**Options presented:**
1. Pytest staleness gate + argparse subcommand refactor *(Recommended)*
2. Pytest staleness gate + flag-based CLI (`quirk --compliance-status`)
3. GitHub Actions warning step + argparse subcommand

**User selected:** Option 1 — pytest gate + argparse subcommand refactor

**Rationale captured:** Pytest-as-CI-gate is the established Phase 48 D-07/08 precedent. Argparse subcommand refactor pays a one-time cost while the CLI surface is small; avoids the "side-quest flag" precedent that would compound for future subcommands (e.g., `quirk db migrate`, `quirk cbom export`).

→ Captured as **D-04** (gates) and **D-05** (CLI) in CONTEXT.md.

---

## Follow-up — Title-join guardrail

**Question:** Finding `title` is now the join key between findings and `COMPLIANCE_MAP`. How should we guard against silent mismatches?

**Options presented:**
1. Pytest assertion: every emitted title is in `COMPLIANCE_MAP` or in `UNMAPPED_TITLES` allow-set *(Recommended)*
2. Module-level constant set: `TITLES = frozenset(...)` imported by both producer + map
3. No guard — accept the risk
4. Both pytest assertion + module constant

**User selected:** Option 1 — pytest title-join gate with `UNMAPPED_TITLES` allow-set

**Rationale captured:** Loud test failure on rename without doubling indirection (option 2's import-everywhere cost). Allow-set with mandatory inline comments keeps reviewers honest about why a finding lacks compliance mapping.

→ Folded into **D-04** in CONTEXT.md.

---

## Claude's Discretion (not asked)

- Exact PCI/HIPAA/FIPS control text and per-finding mapping rationale — researcher proposes initial map
- ASCII vs JSON output for `quirk compliance status` — recommend ASCII default with optional `--format json`
- Renderer template insertion point — planner picks against existing template structure
- File-system layout for `quirk/compliance/` (single `__init__.py` vs. split into `pci_dss.py` / `hipaa.py` / `fips_140_3.py`) — planner picks based on initial map size

---

## Deferred Ideas (captured during discussion)

None raised that weren't already captured under `<deferred>` in CONTEXT.md.

No scope-creep redirects required — user stayed within the Phase 49 envelope throughout.
