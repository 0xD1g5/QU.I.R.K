# CLAUDE.md — QU.I.R.K. Project

## Project Identity

**QU.I.R.K.** (Quantum Infrastructure Readiness Kit) is a consulting-grade cryptographic inventory
scanner. It discovers TLS, SSH, JWT/API, container, source code, and cloud KMS crypto posture,
then produces a CycloneDX CBOM, quantum-readiness score, and prioritized remediation roadmap.

**Stack:** Python 3.11+, FastAPI, React + shadcn/ui + Tailwind, SQLite
**Planning artifacts:** `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`

---

## Code Standards

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- If detection logic changes, update `labs/*/expected_results.md` accordingly.

---

## Mandatory Phase Completion Steps

These steps are **required at the end of every `/gsd:execute-phase` run**, after verification passes and `update_roadmap` / `update_project_md` complete. Do not skip them.

### 1. Create Obsidian Phase Note

Write the phase note directly to the vault filesystem (do NOT use `obsidian CLI content=` — files are too large for shell expansion):

```
/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-NN-<Slug>.md
```

Format: frontmatter (`status: complete`, `type: phase`, `source`, `updated`) + Goal + Requirements Covered + Success Criteria + What Was Built (one subsection per plan, sourced from SUMMARY.md files) + `[[Roadmap]]` link.

See existing notes at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/` for the template pattern.

### 2. Update `docs/UAT-SERIES.md`

After each phase, update the relevant test series to reflect what changed:
- If version bumped: update version strings in UAT-1-02 pass criteria and the document header
- If output paths changed: update affected pass criteria
- If new features added: add new test cases to the relevant series
- Update `**Last Updated:**` date at the top

### 3. Sync UAT-SERIES.md to Obsidian

Write directly to vault filesystem (file is too large for CLI `content=` parameter):

```bash
printf "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/UAT-SERIES.md\nupdated: YYYY-MM-DD\n---\n\n" > /tmp/uat_vault.md
cat docs/UAT-SERIES.md >> /tmp/uat_vault.md
cp /tmp/uat_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
```

### 4. Commit `docs/UAT-SERIES.md`

```bash
node "/Users/digs/.claude/get-shit-done/bin/gsd-tools.cjs" commit "docs(phase-NN): update UAT-SERIES.md" --files docs/UAT-SERIES.md
```

---

## Obsidian Vault Integration

### Vault Targeting

All Obsidian operations target:

- **Vault name:** `Digs`
- **QUIRK root folder:** `20_Dev-Work/QUIRK`

Always pass `vault="Digs"` when calling the obsidian CLI skill. Use `silent` on create/append
operations to prevent Obsidian from switching focus unless the user explicitly wants to open a note.

```bash
# Pattern for all obsidian commands in this project
obsidian vault="Digs" <command> [path="20_Dev-Work/QUIRK/..."] [silent]
```

### Invoke the `obsidian:obsidian-cli` skill whenever the user asks to:

- Sync, push, or update planning notes to Obsidian
- Create or update any guide or documentation note
- Capture phase summaries or completion status
- Build or update the project hub / index
- Add reference or architecture notes

---

### Vault Folder Structure

```
20_Dev-Work/QUIRK/
├── _QUIRK-Hub.md              ← Central MOC — links to everything
├── Roadmap.md                 ← Synced from .planning/ROADMAP.md
├── Requirements.md            ← Synced from .planning/REQUIREMENTS.md
├── Phases/
│   ├── Phase-01-Foundation-Fixes.md
│   ├── Phase-02-CBOM-Pipeline.md
│   ├── Phase-03-Scanner-Coverage.md
│   ├── Phase-04-Chaos-Lab-Expansion.md
│   ├── Phase-05-Web-Dashboard.md
│   ├── Phase-06-Documentation.md
│   └── Phase-07-Polish-and-Packaging.md
├── Guides/
│   ├── Getting-Started.md     ← Synced from docs/getting-started.md
│   ├── Installation.md        ← Synced from docs/installation.md
│   ├── Configuration.md       ← Synced from docs/configuration.md
│   ├── Report-Interpretation.md ← Synced from docs/report-interpretation.md
│   ├── Chaos-Lab.md           ← Synced from docs/chaos-lab.md
│   └── Connectors/            ← One note per connector (synced from docs/connectors/)
└── Reference/
    ├── Architecture.md        ← Maintained manually
    ├── API-Reference.md       ← Maintained manually
    └── Changelog.md           ← Maintained manually
```

---

### Frontmatter Standards

Every note created or synced into the vault must include these properties:

```yaml
---
project: QU.I.R.K.
type: <roadmap | phase | guide | reference | hub>
status: <active | complete | draft>
source: <repo-relative path if synced, e.g. .planning/ROADMAP.md>
updated: <YYYY-MM-DD>
---
```

- `source` is omitted for manually maintained notes (Architecture, API Reference, Changelog).
- `status: complete` for phases marked `[x]` in the roadmap.
- `status: active` for the current in-progress phase.
- `status: draft` for notes that are stubs or not yet accurate.

---

### Sync Workflows

#### Roadmap sync

Source: `.planning/ROADMAP.md`
Target: `path="20_Dev-Work/QUIRK/Roadmap.md"`

Read the source file, then create or overwrite the vault note with the full content plus
frontmatter. Use `overwrite` flag.

```bash
obsidian vault="Digs" create name="Roadmap" path="20_Dev-Work/QUIRK/Roadmap.md" \
  content="<frontmatter + roadmap content>" overwrite silent
```

#### Phase notes

Source: `.planning/phases/<slug>/` — read PLAN.md and SUMMARY.md if present
Target: `path="20_Dev-Work/QUIRK/Phases/Phase-NN-<Name>.md"`

Each phase note should contain:
1. Frontmatter (type: phase, status: complete/active/draft)
2. Goal statement
3. Requirements covered
4. Success criteria
5. Link back to `[[Roadmap]]`
6. Summary of what was built (from SUMMARY.md if available)

#### Guide sync

Source: `docs/<filename>.md`
Target: `path="20_Dev-Work/QUIRK/Guides/<Title>.md"`

Read the source doc, prepend frontmatter, then create or overwrite. Preserve all content as-is —
do not summarize or rewrite guide content.

#### Hub note

`_QUIRK-Hub.md` is the central MOC. Maintain it with:
- Project overview (1 paragraph)
- Wikilinks to Roadmap, Requirements, all Phase notes
- Wikilinks to all Guides
- Wikilinks to Reference notes
- Current phase callout showing active work

Recreate the hub from scratch whenever structure changes. Use `overwrite`.

---

### Property Updates

To mark a phase complete after finishing work:

```bash
obsidian vault="Digs" property:set name="status" value="complete" \
  path="20_Dev-Work/QUIRK/Phases/Phase-NN-<Name>.md"
obsidian vault="Digs" property:set name="updated" value="YYYY-MM-DD" \
  path="20_Dev-Work/QUIRK/Phases/Phase-NN-<Name>.md"
```

---

### Search

To find notes in the QUIRK vault folder:

```bash
obsidian vault="Digs" search query="path:20_Dev-Work/QUIRK <term>"
```
