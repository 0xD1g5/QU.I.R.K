---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork D); ledger row DCL-OPS-GC3D-0002 (docs/operators-guide.md §9.5 `quirk cve status` paragraph)
priority: low
area: quirk/compliance/__init__.py (status_report / check_compliance_staleness)
status: pending
resolves_phase: null
---

# `quirk compliance status` ignores `QUIRK_CI_STALENESS_OVERRIDE_DATE`

`quirk cve status`, `quirk qramm status`, `quirk compliance cmvp status` and the hardware catalog read
`QUIRK_CI_STALENESS_OVERRIDE_DATE` so an operator or CI can rehearse a future date. `quirk compliance status` does not:
`status_report()` calls `check_compliance_staleness()` with no `today` (`quirk/compliance/__init__.py:500`), which
falls back to `datetime.date.today()` (`:447`). Probe (isolated HOME): with the override set to `2030-01-01`,
`quirk qramm status` exits 1, while `quirk compliance status` exits 0 and prints no staleness warning, although
`check_compliance_staleness(today=datetime.date(2030, 1, 1))` raises "Compliance map has 94 stale or malformed
entries". The operators-guide previously said the override worked "like the QRAMM and compliance catalogs"; it now
names compliance status as the exception.

- [ ] Decide whether the compliance status path should honour the override (read it like `quirk/cli/qramm_cmd.py`).
- [ ] If so, pass the resolved date into `check_compliance_staleness(today=...)` and add a test; then drop the
      exception from the operators-guide sentence.

## Feasibility & Effort

- **CONFIRMED** the gap: `grep -rln QUIRK_CI_STALENESS_OVERRIDE_DATE quirk` lists `quirk/cli/cmvp_cmd.py`,
  `quirk/cli/cve_cmd.py`, `quirk/cli/qramm_cmd.py`, `quirk/scanner/hardware_meta.py`, and no compliance module;
  `quirk/compliance/__init__.py:500` calls `check_compliance_staleness()` with no argument.
- **CONFIRMED** the hook exists: `check_compliance_staleness(today=...)` already accepts an injected date
  (`quirk/compliance/__init__.py:418`), so the change is a few lines reusing the `_today()` pattern at
  `quirk/cli/cve_cmd.py:29-47`.
- **LIKELY** effort **S**. **UNKNOWN**: whether the compliance CI gate (`tests/test_compliance_freshness.py`) should
  share the override; it does not read it today. No spike needed.
