# Phase 13: Interactive Mode Overhaul - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-06
**Phase:** 13-interactive-mode-overhaul
**Mode:** discuss
**Areas discussed:** Data classification consolidation, Scan profile UX, Connector credential warnings

## Gray Areas Presented

Three areas selected for discussion out of the following analysis:

| Area | Status | Note |
|------|--------|------|
| Removed/auto-detect prompts | Pre-decided | INTER-01/02/03/07/09 fully specified in requirements |
| Additional scanners | Pre-decided | Already present in interactive.py lines 116–129 |
| Prompt reordering | Pre-decided | INTER-08 specifies targets→options→output→metadata |
| Data classification consolidation | Discussed | Two overlapping prompts across two functions |
| Scan profile UX | Discussed | Profile storage and UX labels not specified in requirements |
| Connector credential warnings | Discussed | Warning format and placement not specified |

## Discussion: Data Classification Consolidation

**Q: How should data classification be handled as a single prompt?**

Options presented:
1. Derive both from one answer (Recommended) — single 4-tier selection maps to both fields
2. Keep data_types only, drop data_classification
3. Keep data_classification only, derive data_types from it

**User selection:** Derive both from one answer (Recommended)

**Follow-up Q: What options should the prompt offer?**

Options presented:
1. 4-tier consulting labels (Recommended) — Public/Internal/Confidential/Regulated
2. Explicit data-type list — PCI/PHI/FINANCIAL/TRADE/PUBLIC multi-select
3. Separate questions merged in one section

**User selection:** 4-tier consulting labels (Recommended)

**Decision recorded:** D-10, D-11, D-12 in CONTEXT.md

## Discussion: Scan Profile UX

**Q: How should the profile selection be captured and stored?**

Options presented:
1. Ask in interactive mode, pass to apply_profile (Recommended) — return tuple, no config field
2. Store profile in ScanCfg — adds profile field to config YAML
3. Apply profile values directly — no profile string stored

**User selection:** Ask in interactive mode, pass to apply_profile (Recommended)

**Follow-up Q: What labels and descriptions should accompany each profile?**

Options presented:
1. Speed-focused labels (Recommended) — quick=fast sweep, standard=balanced, deep=thorough
2. Time estimate labels — ~10/30/60 min estimates
3. Bare names only

**User selection:** Speed-focused labels (Recommended)

**Decision recorded:** D-05 through D-09 in CONTEXT.md

## Discussion: Connector Credential Warnings

**Q: What warning should appear when AWS or Azure is enabled?**

Options presented:
1. Env var reminder (Recommended) — inline note after enabling, one line per connector
2. Pre-enable warning — shown before the yes/no question
3. Post-config summary — all warnings collected at end

**User selection:** Env var reminder (Recommended)

**Decision recorded:** D-13, D-14 in CONTEXT.md

## Corrections Made

No corrections — all recommended defaults accepted.
