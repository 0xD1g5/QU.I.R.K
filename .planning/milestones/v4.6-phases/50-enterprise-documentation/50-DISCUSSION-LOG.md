# Phase 50: Enterprise Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 50-enterprise-documentation
**Areas discussed:** Operator's guide structure, Architecture doc audience & diagrams, Per-scanner reference depth, Compliance Map Maintenance section

---

## Operator's Guide Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid narrative + links | Continuous read with short canonical sections inline + "See also" links to existing docs/installation.md, configuration.md, getting-started.md, chaos-lab.md, connectors/* | ✓ |
| Pure aggregator / index | Mostly a TOC with one-paragraph summaries pointing to existing docs | |
| Self-contained rewrite | Duplicates install/config/scanning content; stands alone but creates two-place edit burden | |

**User's choice:** Hybrid narrative + links
**Notes:** Avoids two-place edits; admin can read top-to-bottom or jump. Existing docs are the canonical source — operators-guide.md adds connective tissue, troubleshooting, per-scanner reference, and compliance maintenance.

### Follow-up — Troubleshooting section coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Common scan failures | Permission denied, timeouts, missing optional deps, TLS handshake errors | ✓ |
| Database / output issues | quirk.db migrations, output dir perms, CBOM gen, PDF render | ✓ |
| Dashboard issues | Vite build, dashboard not loading data, stale .vite/, port conflicts | ✓ |
| Connector-specific gotchas | AWS profile, Azure auth, Docker socket, Git auth | ✓ |

**User's choice:** All four
**Notes:** Connector-specific gotchas live in `docs/connectors/*.md` with a one-line pointer in operators-guide.md (preserves the hybrid principle).

---

## Architecture Doc Audience & Diagrams

### Audience

| Option | Description | Selected |
|--------|-------------|----------|
| Enterprise architect evaluating QUIRK | Data flow, trust boundaries, what touches the network, where credentials live, SQLite schema, CBOM pipeline, dashboard architecture | ✓ |
| New engineer joining the project | Module-level walkthrough: quirk/scanners/ structure, plugin pattern, _build_finding flow, test layout | |
| Both, layered | Top half enterprise reference, bottom half engineer onboarding | |

**User's choice:** Enterprise architect evaluating QUIRK
**Notes:** Matches DOCS-01 success criterion ("understand the full system without reading source code"). Engineer-onboarding doc deferred — could be a future CONTRIBUTING.md / docs/development.md phase.

### Diagrams

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid in markdown | Code blocks render in GitHub + Obsidian, diff-friendly, no external assets | ✓ |
| Text-only ASCII boxes | Zero rendering dependencies; limited expressiveness | |
| External SVG/PNG checked in | Sharper visuals; loses diff-ability and risks silent staleness | |

**User's choice:** Mermaid in markdown
**Notes:** At minimum: system overview, data flow (scan → DB → CBOM → reports), dashboard architecture.

---

## Per-Scanner Reference Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Compact table + linked details | One row per scanner (name, scans, config flags, optional deps, sample finding); cloud connectors link to docs/connectors/*; protocol scanners get 1–2 paragraph inline subsections | ✓ |
| Full inline reference for every scanner | Each of ~16 scanners gets a full subsection; operators-guide.md ~1500–2000 lines | |
| Minimal table only + new docs/scanners/ folder | docs/scanners/<name>.md per protocol scanner; adds 12+ new files | |

**User's choice:** Compact table + linked details
**Notes:** No new `docs/scanners/<name>.md` files — rejected as scope creep. Researcher must enumerate the actual protocol-scanner list from `quirk/scanners/` against the live codebase.

---

## Compliance Map Maintenance Section

### Format and location

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered runbook inside operators-guide.md | Subsection: prose intro → numbered quarterly checklist → source URL table → drift detection → upgrade path worked example | ✓ |
| Standalone docs/compliance-maintenance.md | Same content as own file linked from operators-guide.md; splits the operator entry point | |
| Prose narrative only, in operators-guide.md | Conversational; harder to follow as a quarterly task | |

**User's choice:** Numbered runbook inside operators-guide.md
**Notes:** Single canonical operator entry point per DOCS-02. Worked example: PCI-DSS 4.0.1 → 4.1 upgrade.

### CI mechanisms cited

| Option | Description | Selected |
|--------|-------------|----------|
| `quirk compliance status` command | Operators run before customer engagements | ✓ |
| Staleness gate (12mo / STALENESS_THRESHOLD_DAYS) | CI fails when last_verified >12mo old | ✓ |
| Schema + title-join gates | Schema (every entry has version/last_verified/source_url) and title-join (titles in COMPLIANCE_MAP or UNMAPPED_TITLES) | ✓ |
| `tests/test_compliance_freshness.py` path | Cite the actual test file so maintainers can find it | ✓ |

**User's choice:** All four
**Notes:** Runbook references Phase 49's existing CI mechanisms rather than restating them — single source of truth for what must not break.

---

## Claude's Discretion

- Exact section headings, ordering, tone, prose density.
- Mermaid diagram count beyond the minimum three.
- Exact protocol-scanner list — researcher enumerates from `quirk/scanners/` rather than from this CONTEXT.md.

## Deferred Ideas

- Docs site generator (mkdocs / docusaurus) — future phase if needed.
- `docs/scanners/<name>.md` per-protocol-scanner files — future docs-split phase.
- `CONTRIBUTING.md` / `docs/development.md` (engineer-onboarding architecture audience) — separate phase if needed.
- Video walkthroughs / screencasts — out of scope for v4.6.
- New connector docs for protocol scanners (gap currently filled only for aws/azure/docker/git) — not in this phase.
