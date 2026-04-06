# Phase 12: CLI Correctness - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-06
**Phase:** 12-cli-correctness
**Mode:** discuss
**Areas discussed:** Version Strings, Install Documentation

---

## Codebase Findings (Pre-Discussion)

### CLI-01 (Config field alignment)
Phase 8 VERIFICATION.md confirmed: config_template.yaml has correct field names matching
ConnectorsCfg, ScanCfg, TargetsCfg. One residual gap was `enable_windows_adcs: false` on
line 61 — noted as PARTIAL in Phase 8 but resolved inline. Current template confirmed clean.
config_from_dict() also strips enable_windows_adcs via dict comprehension for backward compat.

### CLI-02 (quirk scan references)
Phase 8 VERIFICATION.md confirmed: zero `quirk scan` references in quirk/ or docs/.
docs/getting-started.md correctly shows `quirk --config config.yaml` at lines 52 and 70.
Already satisfied — Phase 12 re-verifies and guards against regression.

### CLI-03 ([owner] placeholder)
Found in docs/getting-started.md lines 22 and 28:
  `pip install 'git+https://github.com/[owner]/quirk.git'`
config_template.yaml was fixed in Phase 8 (changed to `./docs/configuration.md` reference).
The docs were not updated — this is the remaining gap.

### CLI-04 (Version consistency)
Current state before Phase 12:
  quirk/__init__.py:      __version__ = "4.0.0"
  quirk/reports/writer.py: PLATFORM_VERSION = "4.0"       ← inconsistent
  quirk/reports/writer.py: INTELLIGENCE_VERSION = "4.0.0"
  quirk/cbom/builder.py:  PLATFORM_VERSION = "4.0"        ← inconsistent
  quirk/config.py:        intelligence_version = "4.0.0"

Bug: "4.0" vs "4.0.0" — PLATFORM_VERSION missing the patch component.

---

## Gray Areas Presented

### Area 1 — Version target
Two options were presented: bump to 4.1.0 (matches v4.1 milestone) or stay at 4.0.0 (fix
inconsistency only).

**User choice:** 4.1.0 everywhere
**Reason:** Aligns with v4.1 milestone; CBOM deliverables should carry the correct stamp.

### Area 2 — [owner] URL replacement
Three options were presented: dev install (pip install -e .), real GitHub URL, omit section.

**User choice:** Dev install (pip install -e .)
**Reason:** No public GitHub release yet — dev install is honest about distribution model.

---

## Corrections Made

None — both gray areas resolved through direct user selection with no follow-up corrections.
