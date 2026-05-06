---
phase: 50-enterprise-documentation
type: context
status: active
source: /gsd-discuss-phase 50
updated: 2026-05-05
milestone: v4.6 Enterprise Readiness
requirements: [DOCS-01, DOCS-02, DOCS-03, DOCS-04]
---

# Phase 50: Enterprise Documentation - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Two production-quality reference documents are added to the repo and synced
to the Obsidian vault, sufficient for an enterprise admin to deploy and
operate QUIRK without reading source code:

1. `docs/architecture.md` — system architecture reference framed for an
   **enterprise architect evaluating QUIRK**: data flow, trust boundaries,
   what touches the network, where credentials live, scanner phase model,
   SQLite schema, dashboard architecture, and CBOM pipeline. Diagrams are
   **mermaid blocks** rendered inline in markdown.

2. `docs/operators-guide.md` — single canonical operator entry point,
   structured as a **hybrid narrative + links** doc covering install →
   configure → scan → troubleshoot → per-scanner reference, with short
   canonical sections inline and "See also" links into existing docs
   (`docs/installation.md`, `docs/configuration.md`,
   `docs/getting-started.md`, `docs/chaos-lab.md`,
   `docs/connectors/*.md`). Includes:
   - **Troubleshooting** subsection — net-new content covering common scan
     failures, database / output issues, dashboard issues, with a one-line
     pointer to per-connector gotchas in `docs/connectors/*`.
   - **Per-scanner reference** — compact one-row-per-scanner table (name,
     what it scans, config flags, optional deps, sample finding) with
     1–2 paragraph inline subsections for the ~12 protocol scanners that
     have no dedicated connector doc, and links to `docs/connectors/*`
     for cloud / infra connectors.
   - **Compliance Map Maintenance** subsection — numbered quarterly review
     runbook citing Phase 49's `quirk compliance status` command, the
     12-month staleness gate (`STALENESS_THRESHOLD_DAYS`), schema +
     title-join gates, and the actual `tests/test_compliance_freshness.py`
     test path.

Both documents are synced into the Obsidian vault at
`20_Dev-Work/QUIRK/Reference/` with frontmatter `type: reference`,
`source: docs/<filename>.md`, `updated: 2026-05-XX` per CLAUDE.md.
Sync writes go via vault filesystem (`/Users/digs/vaults/Digs/...`) — not
`obsidian CLI content=` — because both files are too large for shell
expansion.

**In scope:**
- `docs/architecture.md` (enterprise-architect framing, mermaid diagrams)
- `docs/operators-guide.md` (hybrid narrative + links, troubleshooting,
  per-scanner reference, compliance maintenance runbook)
- Vault sync: `20_Dev-Work/QUIRK/Reference/Architecture.md` and
  `20_Dev-Work/QUIRK/Reference/Operators-Guide.md` with standard
  frontmatter
- `_QUIRK-Hub.md` MOC update + roadmap/STATE.md updates per CLAUDE.md
  Mandatory Phase Completion Steps
- `docs/UAT-SERIES.md` update + Obsidian sync per CLAUDE.md mandate

**Out of scope:**
- Docs site generator (mkdocs / docusaurus) — own phase, not v4.6
- Video walkthroughs / screencasts — not v4.6
- New per-scanner doc files for protocol scanners (`docs/scanners/*.md`) —
  inline subsections in operators-guide.md instead; a future doc-split
  phase can extract them
- Rewriting `docs/installation.md`, `docs/configuration.md`,
  `docs/getting-started.md`, `docs/chaos-lab.md`, or
  `docs/connectors/*.md` — operators-guide.md links to them; content is
  not duplicated
- New protocol-scanner connector docs — current state has connector docs
  only for `aws / azure / docker / git`; the gap is acknowledged but not
  filled here
- Compliance map *content* changes — Phase 49 owns COMPLIANCE_MAP; this
  phase only documents the maintenance process

</domain>

<decisions>
## Implementation Decisions

### Operator's Guide Structure
- **D-01:** `docs/operators-guide.md` is a **hybrid narrative + links**
  doc. Continuous read flow (install → configure → scan → troubleshoot →
  per-scanner reference) with short canonical sections inline and
  "See also: `docs/<file>.md`" links for deep dives. Avoids two-place
  edits; admin can read top-to-bottom or jump.
- **D-02:** Troubleshooting section covers all four areas: common scan
  failures (perms, timeouts, missing optional deps, TLS handshake),
  database/output (db migrations, output dir perms, CBOM gen, PDF render),
  dashboard (Vite build, stale `.vite/`, port conflicts, data loading),
  and a one-line pointer to per-connector gotchas in
  `docs/connectors/*` (AWS profile, Azure auth, Docker socket, Git auth)
  rather than duplicating them inline.

### Architecture Doc Audience & Diagrams
- **D-03:** `docs/architecture.md` is framed for an **enterprise architect
  evaluating QUIRK** — data flow, trust boundaries, network surface,
  credential handling, SQLite schema overview, scanner-phase model,
  dashboard architecture, CBOM pipeline. Not a code tour for new
  engineers (that may come later as a separate `CONTRIBUTING.md` /
  `docs/development.md` phase if needed).
- **D-04:** Diagrams are **mermaid code blocks** embedded in markdown.
  Renders in GitHub + Obsidian, diff-friendly, no external assets.
  No SVG/PNG checked in.

### Per-Scanner Reference Depth
- **D-05:** Per-scanner reference is a **compact table + linked details**
  pattern. One row per scanner: name, what it scans, config flags,
  optional deps, sample finding. Cloud/infra connectors (AWS, Azure,
  Docker, Git) link to the existing `docs/connectors/*.md`. The ~12
  protocol scanners (TLS, SSH, JWT/API, container, source code, KMS,
  DNSSEC, Kerberos, SAML, MQ/AMQP, email/SMTP, registry, vault, database,
  S3, nmap discovery — actual list to be confirmed by researcher
  against `quirk/scanners/`) get a 1–2 paragraph inline subsection
  beneath the table.
- **D-06:** No new `docs/scanners/<name>.md` files are created in this
  phase. Rejected as scope creep — adds 12+ files; inline subsections
  satisfy DOCS-02 ("per-scanner reference") without spawning a new doc
  hierarchy.

### Compliance Map Maintenance Section
- **D-07:** Compliance Map Maintenance lives **inside
  `docs/operators-guide.md`** as a numbered runbook subsection — not a
  standalone file. Single canonical operator entry point per DOCS-02.
- **D-08:** Section structure: short prose intro → numbered quarterly
  review checklist → source URL table (PCI SSC, HHS.gov, NIST CSRC) →
  "How to detect drift" → "Upgrade path" worked example
  (e.g. PCI-DSS 4.0.1 → 4.1: bump `version` + `last_verified`,
  re-run gates).
- **D-09:** Runbook explicitly references Phase 49's existing CI
  mechanisms rather than restating them:
  - `quirk compliance status` CLI command (run before customer
    engagements)
  - 12-month staleness gate via `STALENESS_THRESHOLD_DAYS`
    (forces quarterly review by failing CI)
  - Schema gate (every entry has `version` + `last_verified` +
    `source_url`) and title-join gate (every finding title is in
    `COMPLIANCE_MAP` or `UNMAPPED_TITLES`)
  - Cite the actual test file path: `tests/test_compliance_freshness.py`

### Claude's Discretion
- Exact section headings, section ordering within each doc, tone, and
  prose density — researcher/planner decide based on what reads well.
- Mermaid diagram count and granularity in `architecture.md` — at minimum:
  one system overview, one data flow (scan → DB → CBOM → reports), one
  dashboard architecture diagram. More if needed for clarity.
- Exact set of protocol scanners listed in the per-scanner table —
  researcher must enumerate from `quirk/scanners/` against the live
  codebase, not from this CONTEXT.md.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` §"Phase 50: Enterprise Documentation" — phase
  goal, depends on Phase 49, success criteria 1–4
- `.planning/REQUIREMENTS.md` — DOCS-01 (architecture.md scope),
  DOCS-02 (operators-guide.md scope), DOCS-03 (Obsidian sync target +
  frontmatter), DOCS-04 (compliance maintenance content)

### Existing Docs to Link From operators-guide.md (NOT rewrite)
- `docs/installation.md` — install procedures; operators-guide cites
- `docs/configuration.md` — config flags / sample-config; operators-guide
  cites
- `docs/getting-started.md` — first-scan walkthrough; operators-guide
  cites
- `docs/chaos-lab.md` — chaos lab usage; operators-guide cites in the
  "validation / smoke test" section
- `docs/connectors/aws.md`, `docs/connectors/azure.md`,
  `docs/connectors/docker.md`, `docs/connectors/git.md` — per-connector
  gotchas; operators-guide table links here
- `docs/cbom-guide.md`, `docs/cbom-classifier-coverage.md` — CBOM
  pipeline; architecture.md cites
- `docs/intelligence-schema.md` — finding schema; architecture.md cites
- `docs/timeout-retry-audit.md` — operational defaults; relevant to
  troubleshooting + architecture
- `docs/quirk-overview.md` — high-level pitch; architecture.md should be
  consistent with framing

### Phase 49 Mechanisms Cited in Compliance Maintenance Runbook
- `quirk/compliance/__init__.py` — `COMPLIANCE_MAP`,
  `UNMAPPED_TITLES`, `STALENESS_THRESHOLD_DAYS`
- `tests/test_compliance_freshness.py` — staleness gate (CI fail at
  >12mo)
- `tests/test_compliance_schema.py` — schema gate
- `tests/test_compliance_title_join.py` — title-join gate
- `tests/test_compliance_cli.py`,
  `tests/test_compliance_report_section.py` — surrounding behavior
- `.planning/phases/49-compliance-mapping/49-CONTEXT.md` — Phase 49
  decisions on CLI subcommand, eager `compliance` field injection,
  HTML/PDF "Compliance Summary" section
- `.planning/phases/49-compliance-mapping/49-SUMMARY.md` (per plan, where
  present) — what shipped

### Project / Workflow Mandates (CLAUDE.md)
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian phase note,
  UAT-SERIES.md update + sync, commit pattern via gsd-tools
- `CLAUDE.md` §"Obsidian Vault Integration" — frontmatter standard,
  vault path `20_Dev-Work/QUIRK/Reference/`, vault filesystem write
  pattern (NOT `obsidian CLI content=` — files too large for shell
  expansion)

### Vault Targets (write paths)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md` — MOC update
  to add wikilinks to the two new Reference notes
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-50-Enterprise-Documentation.md`
  — phase note per CLAUDE.md mandate

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Existing docs/ corpus** — installation.md, configuration.md,
  getting-started.md, chaos-lab.md, cbom-guide.md,
  cbom-classifier-coverage.md, intelligence-schema.md,
  timeout-retry-audit.md, quirk-overview.md, report-interpretation.md,
  release-notes/, sample-config.yaml, connectors/ — operators-guide.md
  links to these rather than duplicating.
- **Phase 49 compliance module** — `quirk/compliance/` exposes
  `COMPLIANCE_MAP`, `STALENESS_THRESHOLD_DAYS`, `UNMAPPED_TITLES`;
  `quirk compliance status` CLI subcommand prints per-framework state.
  Compliance maintenance runbook references these directly.

### Established Patterns
- **Markdown-first docs** — repo has no docs site generator; everything
  is plain markdown rendered by GitHub + Obsidian. Mermaid is the
  natural diagram choice (already used in Obsidian via Mermaid plugin).
- **Vault frontmatter standard** — `project: QU.I.R.K.`, `type`,
  `status`, `source`, `updated`. Both new vault notes follow this.
- **Vault filesystem write for large files** — CLAUDE.md mandates writing
  via `printf` + `cat` + `cp` for large files; UAT-SERIES.md sync
  already uses this pattern.
- **Phase completion mandate** — CLAUDE.md §"Mandatory Phase Completion
  Steps" enumerates Obsidian phase note + UAT-SERIES.md update + sync
  + dedicated commit. Plans must include explicit tasks for each.

### Integration Points
- `_QUIRK-Hub.md` MOC — add wikilinks to `[[Reference/Architecture]]`
  and `[[Reference/Operators-Guide]]`.
- `docs/UAT-SERIES.md` — add a UAT-50-NN series exercising:
  (a) architecture.md exists + covers required sections,
  (b) operators-guide.md exists + covers required sections,
  (c) Obsidian sync produced both Reference notes with correct
  frontmatter,
  (d) compliance maintenance section names the three source URLs +
  cites `quirk compliance status` + cites the staleness gate test path.
- `.planning/ROADMAP.md` and `.planning/STATE.md` — mark Phase 50
  complete on success per CLAUDE.md mandate.

</code_context>

<specifics>
## Specific Ideas

- Architecture diagrams must include at minimum: (1) system overview
  (CLI → scanner registry → SQLite → reports/dashboard), (2) data flow
  (scan → finding dict → CBOM pipeline → HTML/PDF/JSON outputs),
  (3) dashboard architecture (Vite + React + shadcn → JSON ingest).
- Compliance maintenance runbook must include a worked upgrade-path
  example: "PCI-DSS 4.0.1 → 4.1: edit `version` field for affected
  entries, set `last_verified` to today, re-run schema + freshness
  gates, run `quirk compliance status` to confirm, commit."
- Operator's guide table column order suggestion: `Scanner | Scans |
  Config flag | Optional deps | Sample finding`.

</specifics>

<deferred>
## Deferred Ideas

- **Docs site generator (mkdocs / docusaurus)** — not v4.6; could be a
  future phase if the docs corpus outgrows raw markdown.
- **`docs/scanners/<name>.md` per-protocol-scanner doc files** — would
  be a docs-split phase after Phase 50; current decision is inline
  subsections.
- **`CONTRIBUTING.md` / `docs/development.md`** — engineer-onboarding
  audience for architecture content was rejected for Phase 50; if
  needed, separate phase.
- **Video walkthroughs / screencasts** — out of scope for v4.6.
- **New connector docs for protocol scanners** — gap acknowledged
  (currently only aws/azure/docker/git have connector docs); not
  filled in this phase.

</deferred>

---

*Phase: 50-enterprise-documentation*
*Context gathered: 2026-05-05*
