---
phase: 50-enterprise-documentation
type: patterns
status: active
source: /gsd-plan-phase 50 (pattern-mapper)
updated: 2026-05-05
---

# Phase 50: Enterprise Documentation — Pattern Map

**Mapped:** 2026-05-05
**Files analyzed:** 8
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/architecture.md` (NEW) | reference doc (markdown) | static-content | `docs/cbom-guide.md` | exact |
| `docs/operators-guide.md` (NEW) | guide doc (markdown, hybrid narrative+links) | static-content | `docs/chaos-lab.md` | exact |
| `docs/UAT-SERIES.md` (MODIFY) | gating doc (markdown, append series) | append | itself, Series 18 (UAT-49-NN) at lines 6405–6601 | exact (self) |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md` (NEW) | vault reference note | filesystem write (printf+cat+cp) | UAT-Series sync block in `CLAUDE.md` lines 73–80 | exact |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md` (NEW) | vault reference note | filesystem write (printf+cat+cp) | same as above | exact |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md` (MODIFY) | vault MOC | overwrite via obsidian CLI | CLAUDE.md "Hub note" §, existing hub (recreate-with-overwrite pattern) | role-match |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-50-Enterprise-Documentation.md` (NEW) | vault phase note | filesystem write | `Phases/Phase-49-Compliance-Mapping.md` | exact |
| `tests/test_phase50_docs_presence.py` (NEW) | pytest gate (file/text presence) | read-and-substring | `tests/test_pqc_terminology_gate.py` | exact |

---

## Pattern Assignments

### `docs/architecture.md` (reference doc, static-content)

**Analog:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/docs/cbom-guide.md`

**Repo-doc convention (no frontmatter):** repo `docs/*.md` files do NOT carry YAML frontmatter — only the vault copies do. Plain markdown rendered by GitHub + Obsidian.

**Title + audience-framed intro pattern** (cbom-guide.md lines 1–9):

```markdown
# Cryptographic Bill of Materials (CBOM) Guide

This guide covers three topics:

1. **What a CBOM is** — plain-English explanation for compliance officers and executives
2. **How QU.I.R.K. produces the CBOM** — technical pipeline for consultants and engineers
3. **Citing the CBOM as compliance evidence** — audit language for NIST SP 800-208, CNSA 2.0, and ISO 27001

---
```

**Section-with-audience-tag pattern** (cbom-guide.md lines 11–14):

```markdown
## Section 1: What Is a CBOM?

*(Audience: compliance officers, executives, risk managers)*
```

**Mermaid diagram convention** (per CONTEXT.md D-04 — no existing repo example to copy literally; embed inline as fenced ```mermaid blocks per Phase 50 D-04):

```markdown
\`\`\`mermaid
flowchart LR
  CLI[quirk CLI] --> Reg[scanner registry]
  Reg --> DB[(SQLite)]
  DB --> Reports[HTML/PDF/JSON]
  DB --> Dash[React dashboard]
\`\`\`
```

---

### `docs/operators-guide.md` (guide doc, hybrid narrative+links)

**Analog:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/docs/chaos-lab.md`

**Top-level structure pattern** (chaos-lab.md lines 1–22):

```markdown
# QU.I.R.K. Chaos Lab — Operator Guide

## 1. Overview

[1-paragraph framing]

[bullet list of why-this-matters]

> **For UAT-grade expected scanner findings, see `quantum-chaos-enterprise-lab/expected_results_v4.md`** — the authoritative per-profile oracle used by chaos lab UAT runs and dashboard cross-references.

**Prerequisites:**
- ...

---

## 2. Quick Start
```

**Numbered top-level sections + horizontal-rule separators** — `chaos-lab.md` uses `## 1. Overview`, `## 2. Quick Start`, etc., separated by `---`. Use the same convention for `operators-guide.md` (install → configure → scan → troubleshoot → per-scanner reference → compliance map maintenance).

**"See also" link convention** (configuration.md / installation.md style — plain markdown link, no frontmatter):

```markdown
> See also: [`docs/installation.md`](installation.md) for full install reference.
```

**Per-scanner table column order** (per CONTEXT.md specifics):

```markdown
| Scanner | Scans | Config flag | Optional deps | Sample finding |
|---------|-------|-------------|---------------|----------------|
| TLS     | TCP/TLS endpoints | `enable_tls` (default true) | sslyze (optional) | "TLS certificate is expired" |
```

**Scanner enumeration source:** researcher must walk `quirk/scanners/` and `quirk/connectors/` against the live tree (per CONTEXT.md D-05 / "Claude's Discretion"). Do not copy the protocol-scanner list from CONTEXT.md verbatim.

---

### `docs/UAT-SERIES.md` (MODIFY — append Series 19)

**Analog:** `docs/UAT-SERIES.md` itself, Series 18 (Phase 49) at lines 6405–6601.

**Series header pattern** (UAT-SERIES.md lines 6405–6413):

```markdown
# Series 19: Phase 50 — Enterprise Documentation

**Covers:** DOCS-01..04 from Phase 50

**Note:** UAT-50-NN are documentation/presence gates. None require a live chaos lab or completed scan. UAT-50-04 verifies the Obsidian vault sync produced the expected files with correct frontmatter — run only on a workstation with the QUIRK vault mounted at `/Users/digs/vaults/Digs/`.

---
```

**Per-test-case body pattern** (UAT-SERIES.md UAT-49-01, lines 6415–6435):

```markdown
### UAT-50-01: <Title> (<REQ-ID>)

**ID:** UAT-50-01
**Title:** <one-line title>

**Prerequisites:** Repo on `QUIRK-v4`; clean working tree; <preconditions>.

**Steps:**
1. <command>

**Expected:** <observable outcome>

**Pass Criteria:**
- <bullet, exit-code or substring assertion>
- <bullet>

**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
**Date:** __________  **Tester:** __________
**Notes:**

---
```

**Document-header `Last Updated:` ratchet pattern** (UAT-SERIES.md lines 1–6):

```markdown
# QU.I.R.K. — UAT Test Series (Gating Document)

**Version:** 4.4.0
**Last Updated:** 2026-05-XX (Phase 50 wrap: UAT-50-NN added for Enterprise Documentation — <one-line per case>. Closes DOCS-01..04. Earlier: Phase 49 wrap: <existing 49 wrap text preserved verbatim, prepended with "Earlier: ">)
```

The `Last Updated:` line is a single ever-growing line: each phase prepends its wrap clause and the prior contents are preserved verbatim behind `Earlier:` markers. Do not truncate.

---

### Vault sync writes — `Reference/Architecture.md`, `Reference/Operators-Guide.md`

**Analog:** `CLAUDE.md` §"Mandatory Phase Completion Steps" → step 3 (UAT-SERIES sync), lines 73–80.

**Filesystem write pattern (mandatory for large files — NOT `obsidian CLI content=`):**

```bash
printf -- "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/architecture.md\nupdated: 2026-05-XX\n---\n\n" > /tmp/arch_vault.md
cat docs/architecture.md >> /tmp/arch_vault.md
cp /tmp/arch_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Architecture.md"
```

```bash
printf -- "---\nproject: QU.I.R.K.\ntype: reference\nstatus: active\nsource: docs/operators-guide.md\nupdated: 2026-05-XX\n---\n\n" > /tmp/ops_vault.md
cat docs/operators-guide.md >> /tmp/ops_vault.md
cp /tmp/ops_vault.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/Operators-Guide.md"
```

**Frontmatter standard** (CLAUDE.md §"Frontmatter Standards"):

```yaml
---
project: QU.I.R.K.
type: reference
status: active
source: docs/<filename>.md
updated: 2026-05-XX
---
```

The `Reference/` folder currently contains zero notes — these will be the first. CLAUDE.md folder structure at line 50 enumerates the expected `Reference/Architecture.md`, `Reference/API-Reference.md`, `Reference/Changelog.md` slots (latter two out of scope here).

---

### `_QUIRK-Hub.md` (MOC — add wikilinks to two new Reference notes)

**Analog:** CLAUDE.md §"Hub note" (lines 134–143) — recreate from scratch with `overwrite`.

**Pattern guidance (from CLAUDE.md):**
- Project overview (1 paragraph)
- Wikilinks to Roadmap, Requirements, all Phase notes
- Wikilinks to all Guides
- Wikilinks to Reference notes — add `[[Reference/Architecture]]` and `[[Reference/Operators-Guide]]`
- Current phase callout

**CLI invocation** (CLAUDE.md line 21):

```bash
obsidian vault="Digs" create name="_QUIRK-Hub" path="20_Dev-Work/QUIRK/_QUIRK-Hub.md" \
  content="<full hub content with frontmatter>" overwrite silent
```

The hub is small enough to use `obsidian CLI content=` (unlike architecture.md / operators-guide.md). If hub content grows beyond shell-expansion safe size, fall back to the printf+cat+cp filesystem-write pattern.

---

### `Phases/Phase-50-Enterprise-Documentation.md` (NEW phase note)

**Analog:** `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-49-Compliance-Mapping.md`

**Frontmatter pattern** (Phase-49 lines 1–7):

```yaml
---
project: QU.I.R.K.
type: phase
status: complete
source: .planning/phases/50-enterprise-documentation/
updated: 2026-05-XX
---
```

**Body section structure** (Phase-49 lines 9–121):

```markdown
# Phase 50 — Enterprise Documentation

## Goal
<1-paragraph goal statement, sourced from CONTEXT.md `<domain>`>

## Requirements Covered
- **DOCS-01** — ...
- **DOCS-02** — ...
- **DOCS-03** — ...
- **DOCS-04** — ...

## Success Criteria (verified end-to-end)
1. <criterion>. ✓ (Plan 50-NN, <verification mechanism>)
2. ...

## What Was Built

### Plan 50-01 — <plan name>

<2–4 paragraph summary sourced from `.planning/phases/50-enterprise-documentation/plans/50-01-*-SUMMARY.md`>

### Plan 50-02 — <plan name>

<...>

## Key Decisions
- **D-01** — <decision verbatim from CONTEXT.md `<decisions>`>
- **D-02** — ...

## Forward Pointer
<what later phase / milestone consumes this output>

## Out of Scope (deferred)
<bullets sourced from CONTEXT.md `<deferred>`>

## Links
- [[Roadmap]]
- [[Requirements]]
- [[UAT-Series]]
- [[Phase-49-Compliance-Mapping]]
- [[Reference/Architecture]]
- [[Reference/Operators-Guide]]
- [[_QUIRK-Hub|QUIRK Hub]]
```

**Write strategy:** the phase note will exceed shell-expansion safe size once each Plan 50-NN summary is inlined. Use the printf+cat+cp filesystem-write pattern, NOT `obsidian CLI content=` (CLAUDE.md mandate, "Mandatory Phase Completion Steps" §1).

```bash
# Pattern — write file body to a temp file first, then cp into vault.
printf -- '%s\n' "<content>" > /tmp/phase50_note.md
cp /tmp/phase50_note.md "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-50-Enterprise-Documentation.md"
```

(Or use the `Write` tool with the absolute vault path directly — both satisfy the CLAUDE.md mandate, since both bypass `obsidian CLI content=`.)

---

### `tests/test_phase50_docs_presence.py` (pytest file/text presence gate)

**Analog:** `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/test_pqc_terminology_gate.py`

**Full pattern to copy** (test_pqc_terminology_gate.py lines 1–47):

```python
"""Phase 50 docs presence gate: enforce architecture.md + operators-guide.md
ship with the required sections so docs cannot silently regress.

Pattern modelled on tests/test_pqc_terminology_gate.py — read source file
from disk, substring-check the contents.
"""
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_REQUIRED_DOCS = [
    "docs/architecture.md",
    "docs/operators-guide.md",
]

# Required substrings (case-insensitive) per doc.
_REQUIRED_SECTIONS = {
    "docs/architecture.md": (
        "data flow",
        "trust boundar",      # tolerates "boundary"/"boundaries"
        "```mermaid",
    ),
    "docs/operators-guide.md": (
        "troubleshoot",
        "compliance map maintenance",
        "quirk compliance status",
        "staleness_threshold_days",
        "tests/test_compliance_freshness.py",
        "https://www.pcisecuritystandards.org",   # PCI source URL
        "https://www.hhs.gov",                    # HIPAA source URL
        "https://csrc.nist.gov",                  # FIPS / NIST source URL
    ),
}


def _read(rel: str) -> str:
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def test_required_docs_resolve():
    """Each required doc file must exist."""
    for rel in _REQUIRED_DOCS:
        assert os.path.isfile(os.path.join(_REPO_ROOT, rel)), (
            f"Required Phase 50 doc missing: {rel}"
        )


def test_required_sections_present():
    """Each doc must contain its required substrings."""
    missing = []
    for rel, needles in _REQUIRED_SECTIONS.items():
        text = _read(rel)
        for needle in needles:
            if needle.lower() not in text:
                missing.append((rel, needle))
    assert not missing, (
        f"Phase 50 docs missing required sections: {missing}"
    )
```

**Why this analog:** `test_pqc_terminology_gate.py` is the project's canonical "read repo file from disk + substring check" pattern (Phase 48). It is the only test in the suite whose sole job is markdown/source presence assertions, and CLAUDE.md "Code Standards" mandates running `python -m compileall` + relevant tests after changes. Sticking to the established `_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))` shape and lower-cased substring check keeps the new gate diff-minimal (per CLAUDE.md "Code Standards"). The freshness gate `tests/test_compliance_freshness.py` is a different role (date-staleness assertions) — not the right analog.

---

## Shared Patterns

### Repo-doc convention (no frontmatter)

**Source:** `docs/cbom-guide.md`, `docs/getting-started.md`, `docs/chaos-lab.md`, `docs/configuration.md`, `docs/installation.md` — every existing repo doc starts with `# <Title>` directly, no YAML.

**Apply to:** `docs/architecture.md`, `docs/operators-guide.md`. Frontmatter is added only when the file is sync'd into the vault (printf prepend), never in the repo copy.

### Vault frontmatter standard

**Source:** `CLAUDE.md` §"Frontmatter Standards" (lines 113–125).

**Apply to:** every vault file written by this phase (`Reference/Architecture.md`, `Reference/Operators-Guide.md`, `Phases/Phase-50-Enterprise-Documentation.md`).

```yaml
---
project: QU.I.R.K.
type: <reference | phase>
status: <active | complete>
source: <repo-relative path>
updated: 2026-05-XX
---
```

### Filesystem-write for large vault files

**Source:** `CLAUDE.md` §"Mandatory Phase Completion Steps" step 3 (lines 73–80).

**Apply to:** all three new vault files in this phase. Both new docs and the Phase 50 note are too large for `obsidian CLI content=` shell expansion — use `printf` + `cat` + `cp` (or the `Write` tool with the absolute vault path).

### CLAUDE.md mandatory phase completion checklist

**Source:** `CLAUDE.md` §"Mandatory Phase Completion Steps" (lines 53–96).

**Apply to:** the final Plan 50-NN (docs + sync wrap-up plan). Required steps:
1. Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-50-Enterprise-Documentation.md`
2. Update `docs/UAT-SERIES.md` (add Series 19, bump `Last Updated:` line)
3. Sync `docs/UAT-SERIES.md` to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` via the `printf | cat | cp` pattern
4. Commit `docs/UAT-SERIES.md` via `gsd-tools.cjs commit`

These four steps are non-negotiable per CLAUDE.md.

### Citation discipline (compliance maintenance section)

**Source:** `CONTEXT.md` D-09 + `quirk/compliance/__init__.py` (Phase 49 mechanisms).

**Apply to:** `docs/operators-guide.md` "Compliance Map Maintenance" subsection. Must literally name:
- `quirk compliance status` — CLI subcommand (Phase 49)
- `STALENESS_THRESHOLD_DAYS` — module constant
- `tests/test_compliance_freshness.py` — exact test path
- `tests/test_compliance_schema.py` — schema gate
- `tests/test_compliance_title_join.py` — title-join gate
- `COMPLIANCE_MAP`, `UNMAPPED_TITLES` — module symbols
- Source URLs: PCI Security Standards Council (https://www.pcisecuritystandards.org), HHS.gov (https://www.hhs.gov), NIST CSRC (https://csrc.nist.gov)

The `tests/test_phase50_docs_presence.py` gate (above) enforces these substrings in CI, mirroring the Phase 48 PQC-terminology-gate precedent.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Every Phase 50 file has a clear analog. Mermaid diagrams are net-new content but use a standard fenced ```mermaid block — no project-specific precedent needed. |

---

## Metadata

**Analog search scope:**
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/docs/` (all `*.md` + `connectors/`)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/tests/` (presence/gate-style tests)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/` (vault phase-note conventions)
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Reference/` (currently empty — this phase populates it)
- `CLAUDE.md` (frontmatter, sync, and phase-completion mandates)

**Files scanned:** 9 docs files, 12 test files, 39 vault phase notes, 1 root CLAUDE.md.

**Pattern extraction date:** 2026-05-05
