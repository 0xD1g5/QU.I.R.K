---
phase: 147-backlog-drain-lifecycle-ledger-tail
plan: 02
subsystem: hardware-scanner-cve-correlation
tags: [bacnet, cve-correlation, curated-catalog, staleness-gate, docs]
dependency-graph:
  requires:
    - quirk/scanner/hw_cve.py (CVE_TABLE, correlate_device, staleness triad pattern)
    - quirk/scanner/hardware_scanner.py (Step 5 BACnet block)
    - quirk/scanner/bacnet_scanner.py (raw probe values)
  provides:
    - quirk/scanner/bacnet_vendors.py (resolve_bacnet_vendor, resolve_bacnet_model_family)
  affects:
    - quirk/scanner/hardware_scanner.py (device.vendor/device.model now resolved for BACnet)
    - hw_cve.py's ("Johnson Controls", "Facility Explorer") CVE_TABLE entry (now reachable)
tech-stack:
  added: []
  patterns:
    - "Fourth instance of the curated-catalog + staleness-gate triad (compliance/__init__.py, qramm/model_meta.py, hw_cve.py, bacnet_vendors.py)"
key-files:
  created:
    - quirk/scanner/bacnet_vendors.py
    - tests/test_bacnet_vendor_resolution.py
  modified:
    - quirk/scanner/hardware_scanner.py
    - .github/workflows/python-staleness.yml
    - docs/report-interpretation.md
    - docs/operators-guide.md
    - CLAUDE.md (gitignored, not tracked by git)
decisions:
  - "D-147-02-A: build-catalog (option a) — user confirmed via orchestrator checkpoint before plan dispatch"
metrics:
  duration: "~35min"
  completed: 2026-08-11
---

# Phase 147 Plan 02: BACnet CVE Key Coverage (DRAIN-02) Summary

Built a curated BACnet vendor-ID + model-family resolution layer so the pre-existing
`("Johnson Controls", "Facility Explorer")` CVE_TABLE entry in `hw_cve.py` — previously
unreachable dead weight — is now reachable end-to-end from a real BACnet FX16 fingerprint.

## Decision D-147-02-A

**Selected: option (a) "build-catalog"** — build the curated BACnet vendor-ID + model-family
resolution layer. This decision was made by the user live in the orchestrator session before
this plan was dispatched to the executor (Task 1's blocking checkpoint was pre-resolved per
the executor's dispatch instructions — not re-asked here). Recorded verbatim per the
orchestrator's instruction: "user confirmed via orchestrator checkpoint before plan dispatch."

Rationale carried from the checkpoint options: research recommended option (a) because the
fix is small (~1 curated module + 1 call-site edit + tests), the ASHRAE/BACnet vendor-ID
registry is authoritative and stable, and it makes an already-written CVE_TABLE entry
(Facility Explorer / FX16) actually functional instead of remaining dead code that would
confuse a future reader.

## What Was Built

**`quirk/scanner/bacnet_vendors.py` (new)** — the fourth instance of the curated-catalog +
staleness-gate triad already established by `quirk/compliance/__init__.py` (Phase 49),
`quirk/qramm/model_meta.py` (Phase 51), and `quirk/scanner/hw_cve.py` (Phase 142):
- `STALENESS_THRESHOLD_DAYS = 365` (ASHRAE vendor-ID assignments are append-only/stable —
  longer cadence than CVE data's 30-day threshold)
- `BACNET_VENDOR_TABLE_META` citing `bacnet.org/assigned-vendor-ids/` as source
- `is_bacnet_vendor_table_stale(today=None)` — strict `>` boundary, mirrors `hw_cve.py` exactly
- `BACNET_VENDOR_TABLE: dict[str, str]` — curated subset (mandatory: `"5"` → `"Johnson
  Controls"`, verified against the ASHRAE registry). Kept small and non-exhaustive
  deliberately — no bulk registry ingestion (Don't-Hand-Roll).
- `BACNET_MODEL_FAMILY_TABLE: dict[tuple, str]` — maps `(vendor_name, raw_model)` to the
  CVE_TABLE product-family key (mandatory: `("Johnson Controls", "FX16")` →
  `"Facility Explorer"`)
- `resolve_bacnet_vendor(vendor_id)` and `resolve_bacnet_model_family(vendor_name, model)` —
  pure lookups, `None` on miss/`None` input, never raise

**`quirk/scanner/hardware_scanner.py`** — Step 5's BACnet block now resolves the raw
`bacnet_vendor`/`bacnet_model` values via the new module **before** assigning
`device.vendor`/`device.model`, falling back to the raw value when the resolver misses
(`resolve_bacnet_vendor(raw) or raw`). The raw `device.bacnet_vendor`/`device.bacnet_model`
probe-artifact fields are untouched — they still carry the unresolved wire values. D-03
first-match-wins (Modbus Step 4 claims first) is preserved unchanged. `hw_cve.py` itself was
**not modified** — resolution stays the call site's responsibility per its documented
contract (RESEARCH.md Pitfall 3).

**`tests/test_bacnet_vendor_resolution.py` (new)** — 22 tests across four groups:
- Group A: resolver + model-family unit tests (str/int coercion, None/miss handling)
- Group B: end-to-end CVE reachability (resolved vendor+family reaches
  `hw_cve.correlate_device()` and matches CVE-2017-16744 at "medium" confidence) plus a
  negative control proving the raw pre-fix values (`"5"`, `"FX16"`) never matched
- Group C: staleness-gate boundary tests (365/366 day boundary, mirrors
  `tests/test_cve_staleness.py`)
- Group D: call-site regression tests against `hardware_scanner.fingerprint_one()` — known
  vendor resolves correctly, unrecognized vendor falls back to raw value with no crash, and
  Modbus-claimed devices are not overwritten by Step 5

RED confirmed before Task 3 (`ModuleNotFoundError: No module named
'quirk.scanner.bacnet_vendors'`); GREEN confirmed after Tasks 3/4 (22/22 passing).

**`.github/workflows/python-staleness.yml`** — added `tests/test_bacnet_vendor_resolution.py`
to the CI staleness-gate test list, alongside the pre-existing `tests/test_cve_staleness.py`
(this closes a small pre-existing gap: `hw_cve.py`'s own staleness test was already gated, but
this is the first phase where a fourth curated catalog is added, so the CI wiring pattern
needed to be applied fresh).

**`CLAUDE.md`** ("Staleness Review Cadence" section, gitignored — edited on disk, not
committed to git per repo policy) — updated from "Two project data files" to "Four project
data files," adding entries for `quirk/scanner/hw_cve.py` (30-day, a pre-existing
documentation gap this phase also closed) and `quirk/scanner/bacnet_vendors.py` (365-day).

**Documentation** — `docs/report-interpretation.md` gained new §10.8 "BACnet Vendor Name
Resolution & CVE Coverage" describing the resolved-vendor-name behavior, the
curated-not-exhaustive caveat, the preserved raw fields, and the advisory-only framing, with
decision traceability to D-147-02-A. `docs/operators-guide.md` §9.5 gained a matching
operator-facing paragraph. Both synced to the Obsidian vault `Digs` at
`20_Dev-Work/QUIRK/Guides/Report-Interpretation.md` and
`20_Dev-Work/QUIRK/Guides/Operators-Guide.md` with standard frontmatter.

## Verification

- `python -m pytest tests/test_bacnet_vendor_resolution.py tests/test_hw_cve_correlation.py -x` — 22 passed
- `python -m compileall -q quirk` — exits 0
- `python -m pytest -q` (full suite) — 103 pre-existing failures, **zero new failures**; none
  of the 103 mention `bacnet`, `hardware_scanner`, or `hw_cve` (confirmed via grep on the full
  failure list). Pre-existing failures span playwright/report-rendering environment gaps,
  SSRF-blocked DNS in ticketing tests, sensor_cmd retry-logic issues, and a genuinely stale
  QRAMM model catalog (`test_qramm_staleness.py` — QRAMM_MODEL is 98 days old, unrelated to
  this plan, tracked separately) — all documented in project memory as pre-existing/environment
  gated, not caused by this plan.
- `git diff --name-only` across this plan's commits lists exactly `quirk/scanner/bacnet_vendors.py`,
  `quirk/scanner/hardware_scanner.py`, `tests/test_bacnet_vendor_resolution.py`,
  `.github/workflows/python-staleness.yml`, `docs/report-interpretation.md`,
  `docs/operators-guide.md` (CLAUDE.md is gitignored, confirmed absent from `git status`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Registered the new catalog in the CI staleness
gate workflow, not just CLAUDE.md's prose**
- **Found during:** Task 4
- **Issue:** The plan's must_haves require the new catalog to be "staleness-gated ... like the
  three existing curated catalogs." The three existing catalogs are staleness-gated by BOTH a
  CLAUDE.md prose entry AND a `pytest` invocation in `.github/workflows/python-staleness.yml`.
  Editing only CLAUDE.md would leave the new catalog's staleness test unenforced by CI.
- **Fix:** Added `tests/test_bacnet_vendor_resolution.py` to the `python-staleness.yml`
  staleness-gate test list (also discovered `tests/test_cve_staleness.py` was already present
  there, so `hw_cve.py`'s 30-day gate was already CI-enforced — only the new module needed
  adding).
- **Files modified:** `.github/workflows/python-staleness.yml`
- **Commit:** `24c7aed`

None of the other three deviation rules were triggered — the plan's option-(a) implementation
proceeded exactly as researched and patterned.

## Known Stubs

None.

## Threat Flags

None — this plan's threat model was pre-declared in the PLAN.md `<threat_model>` block
(T-147-02-01/02/03/SC), and no new surface outside that register was introduced. Both
resolvers remain pure `dict.get()` lookups with no `eval`, filesystem, or network access.

## Self-Check: PASSED

- `quirk/scanner/bacnet_vendors.py` — FOUND
- `tests/test_bacnet_vendor_resolution.py` — FOUND
- Commit `bb69dcc` (test RED) — FOUND in `git log`
- Commit `84e8fce` (feat: catalog GREEN) — FOUND in `git log`
- Commit `24c7aed` (feat: call-site wiring) — FOUND in `git log`
- Commit `4e8a556` (docs + vault sync) — FOUND in `git log`
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Report-Interpretation.md` contains "bacnet" — FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Operators-Guide.md` contains "bacnet" — FOUND
