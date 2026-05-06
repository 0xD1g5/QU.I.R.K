---
phase: 49-compliance-mapping
type: context
status: active
source: /gsd-discuss-phase 49
updated: 2026-05-05
milestone: v4.6 Enterprise Readiness
requirements: [COMPLY-01, COMPLY-02, COMPLY-03, COMPLY-04, COMPLY-05, COMPLY-06, COMPLY-07, COMPLY-08, COMPLY-09]
---

# Phase 49 — Compliance Mapping — Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

A new `quirk/compliance/` Python module exposes `COMPLIANCE_MAP`, a dict
keyed by **finding `title` string** whose values are flat lists of control
references — one entry per `(framework, control)` pair, each carrying
`version`, `last_verified` (ISO date), and `source_url`. The map covers
PCI-DSS 4.0.1, HIPAA 45 CFR, and FIPS 140-3.

Phase 48's `_build_finding(...)` helper is extended to look up
`COMPLIANCE_MAP[title]` and inject a `compliance: [...]` field into every
finding dict at construction (eager attachment). The HTML and PDF
renderers gain a "Compliance Summary" section grouped by framework, each
showing a full finding→control table plus an "Unmapped findings"
subsection so coverage gaps are visible.

Three pytest gates enforce correctness:
1. Schema gate — every COMPLIANCE_MAP entry has `version` + `last_verified` + `source_url`
2. Title-join gate — every finding title emitted by the engine over the chaos-lab fixture set is either in COMPLIANCE_MAP or in an explicit `UNMAPPED_TITLES` allow-set
3. Staleness gate — no entry's `last_verified` is older than 12 months (configurable via `STALENESS_THRESHOLD_DAYS`)

`run_scan:main` is refactored from a single entry point into an argparse
subcommand dispatcher: `quirk scan` (default, preserves all current
behavior) and `quirk compliance status` (prints per-framework version /
last_verified / source_url for operator pre-engagement verification).

**In scope (from ROADMAP.md):**
- `quirk/compliance/__init__.py` module with `COMPLIANCE_MAP`
- PCI-DSS 4.0.1 controls 4.2.1, 4.2.1.1, 6.3.3, 8.3.2 mapped to relevant TLS / key-storage findings
- HIPAA 45 CFR §164.312(a)(2)(iv), §164.312(e)(1), §164.312(e)(2)(ii) mapped to relevant findings
- FIPS 140-3 approved/not-approved classification for findings touching algorithm choice (RSA, ECDSA, AES, SHA-1, MD5)
- `compliance` field eagerly injected into every finding dict via `_build_finding`
- "Compliance Summary" section in HTML + PDF reports
- Three pytest gates (schema / title-join / staleness)
- `quirk compliance status` CLI subcommand
- `docs/UAT-SERIES.md` update + Obsidian phase note + `_QUIRK-Hub.md` refresh per CLAUDE.md mandate

**Out of scope:**
- Dashboard UI compliance view — covered by deferred BACK-72 (QRAMM Compliance Mapping View)
- Combined governance + technical PDF export — deferred BACK-73
- Other frameworks (NIST CSF, ISO 27001, NSA CNSA 2.0, ETSI, BSI TR-02102, CMMC, Common Criteria) — deferred to v4.7+ via COMPLY-10/11
- JSON-export schema migration for `compliance` field consumers (downstream tooling) — out of scope; field flows transparently via dict propagation
- Renaming `recommendation` → `remediation` — explicitly preserved by Phase 48 D-01

</domain>

<decisions>
## Implementation Decisions

### Mapping data model

- **D-01 — Key by finding `title`, value = flat list of framework entries.**
  `COMPLIANCE_MAP[finding_title]` returns a `list[dict]` where each dict
  has the shape `{framework, control, version, last_verified, source_url}`.

  ```python
  COMPLIANCE_MAP = {
      "TLS legacy protocol enabled": [
          {"framework": "PCI-DSS 4.0.1",
           "control": "4.2.1",
           "version": "4.0.1",
           "last_verified": "2026-05-04",
           "source_url": "https://docs-prv.pcisecuritystandards.org/..."},
          {"framework": "HIPAA 45 CFR",
           "control": "§164.312(e)(1)",
           "version": "2024-rev",
           "last_verified": "2026-05-04",
           "source_url": "https://www.ecfr.gov/..."},
      ],
      "RSA key size below NIST minimum": [...],
      ...
  }
  ```

  *Why:* Finding `title` is already a stable string (Phase 48 D-02 made
  `_build_finding` the chokepoint). A flat list iterates cleanly for the
  staleness walk and the report-render walk. No schema change to the
  finding dict beyond the `compliance` injection (D-02). Keeping framework
  metadata at the entry level (vs. nested-by-framework) avoids two-level
  descent and makes "all entries needing freshness check" a single
  `for entries in COMPLIANCE_MAP.values() for e in entries` walk.

  *How to apply:* Researcher should enumerate every distinct finding
  `title` literal currently produced by `_build_finding` callers in
  `risk_engine.py:343–489` and propose initial PCI-DSS / HIPAA / FIPS
  mappings for each. Planner splits the map population into framework
  blocks if the table grows large.

### Attachment

- **D-02 — Eager attachment in `_build_finding`.** The Phase 48 helper
  performs `compliance = COMPLIANCE_MAP.get(title, [])` and injects the
  result as a new `compliance: list[dict]` key on every finding dict at
  construction time. JSON exports, dashboard DTO, and renderers all see
  the field automatically because findings flow through them as dicts.

  *Why:* Single chokepoint (mirrors Phase 48 D-02 / D-06 pattern). Findings
  in JSON exports gain compliance refs without separate plumbing — useful
  for downstream consultant tooling. Future dashboard work (BACK-72)
  reads compliance from the existing DTO instead of re-implementing a
  lookup. Cost is one extra dict key on every finding (negligible).

  *How to apply:* Update `_build_finding` signature in
  `quirk/engine/risk_engine.py` to perform the lookup. Update
  `quirk/dashboard/api/schemas.py` finding DTO to declare
  `compliance: list[ComplianceRef] = []`. JSON export path requires no
  change — the dict propagates. Renderer templates pick up the field for
  the new Compliance Summary section.

### Report format

- **D-03 — Compliance Summary section: framework-grouped, full
  finding→control table.** Three sub-sections (PCI-DSS 4.0.1 / HIPAA
  45 CFR / FIPS 140-3). Each sub-section renders a table with columns:
  Finding title, Severity, Control reference, source_url. A final
  "Findings without compliance mapping" subsection lists any findings
  whose title is not in COMPLIANCE_MAP — surfaces coverage gaps to
  reviewers.

  *Why:* Maximum value as audit evidence — a consultant can hand the
  report to a PCI assessor and the control references are already there.
  The unmapped subsection prevents silent under-reporting (a missing
  mapping looks like "no compliance impact" in the framework-grouped
  view, which is wrong).

  *How to apply:* Both `quirk/reports/html_renderer.py` and the PDF
  pipeline (renders the same HTML via Playwright per BACK-73 context)
  need a new template block. Planner identifies the existing template
  insertion point (likely near the Findings section). The unmapped list
  uses set-difference between emitted finding titles and
  `COMPLIANCE_MAP.keys()`.

### Enforcement gates

- **D-04 — Three pytest gates (schema, title-join, staleness).** All
  three live as pytest tests under `tests/` — same pattern as Phase 48's
  `tests/test_pqc_terminology_gate.py`. Auto-collected, no
  Makefile/workflow changes required.

  - `tests/test_compliance_schema.py` — every `COMPLIANCE_MAP` entry
    contains `version`, `last_verified`, `source_url`, `framework`,
    `control` keys and `last_verified` parses as ISO date. Satisfies
    COMPLY-06 + COMPLY-07.
  - `tests/test_compliance_title_join.py` — runs the engine over the
    chaos-lab fixture set, collects every emitted finding `title`, and
    asserts `title in COMPLIANCE_MAP or title in UNMAPPED_TITLES`.
    Renaming a title without updating the map (or the allow-set) is a
    loud test failure.
  - `tests/test_compliance_freshness.py` — walks every entry; fails if
    any `last_verified` is older than `STALENESS_THRESHOLD_DAYS = 365`
    (module-level constant for configurability per COMPLY-08).

  *Why:* Pytest-as-CI-gate is the established Phase 48 D-07/08 precedent
  in this repo. Auto-collection means no scripts/Makefile/workflow
  surface to maintain. Each gate fails for a structurally different
  reason — three-test split (rather than one big test) makes failures
  trivially diagnosable. The title-join gate is the load-bearing
  guardrail because finding `title` is the cross-phase contract surface
  (Phase 48 emits it; Phase 49 keys off it).

  *How to apply:* `UNMAPPED_TITLES` lives in `quirk/compliance/__init__.py`
  as a module-level frozenset, exported alongside `COMPLIANCE_MAP`. Each
  entry in the allow-set should carry an inline comment explaining why
  it has no compliance mapping (e.g., observability findings, scan-error
  categories) so future reviewers don't grow the set casually.

### CLI subcommand

- **D-05 — Argparse subcommand refactor: `quirk scan` + `quirk compliance status`.**
  Refactor `run_scan:main` to dispatch via argparse subparsers. The
  `quirk scan` subcommand preserves every current flag and behavior —
  bare `quirk` (no subcommand) defaults to `scan` for backward
  compatibility with existing user muscle memory. `quirk compliance
  status` reads `COMPLIANCE_MAP`, groups by framework, and prints a
  fixed-width table (Framework / Version / Last Verified / source_url).

  *Why:* The flag-based alternative (`quirk --compliance-status`) sets a
  precedent of "side-quest flags on the scan entry" that doesn't compose
  for future subcommands (e.g., a future `quirk db migrate` or `quirk
  cbom export`). Pay the one-time argparse refactor cost now while the
  CLI surface is still small and the migration is mechanical.

  *How to apply:* Researcher locates the current `main()` argparse setup
  in `run_scan.py`. Planner splits into: (1) wrap existing parser as
  the `scan` subparser; (2) add `compliance` parent + `status` child;
  (3) preserve the no-subcommand-defaults-to-scan path; (4) update
  `pyproject.toml` if needed (entry remains `quirk = "run_scan:main"`).
  Verify `--help` output is sensible at every level.

### Claude's Discretion

- Exact PCI-DSS / HIPAA / FIPS 140-3 control text and per-finding
  mapping rationale — researcher proposes the initial map; planner
  finalizes per finding category. Each entry's `source_url` should
  point to the authoritative regulator publication, not a third-party
  summary.
- Whether `quirk compliance status` output is plain ASCII table, JSON
  (via `--format json`), or both — recommend ASCII default with
  `--format json` for piping; planner finalizes.
- Renderer template insertion point for the Compliance Summary section —
  planner picks against existing template structure (likely after the
  Findings section, before the CBOM appendix).
- File-system layout for the `quirk/compliance/` module — single
  `__init__.py` if map is small, or split into
  `pci_dss.py` / `hipaa.py` / `fips_140_3.py` re-exported from
  `__init__.py` if the map grows. Planner picks based on initial size.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 49 (lines 961–977) — phase goal, success criteria, plan headings (currently auto-numbered as `45-01..45-03` in roadmap text — these are placeholder slugs; planner generates `49-01..49-03-PLAN.md`)
- `.planning/REQUIREMENTS.md` lines 37–45 (COMPLY-01..09 active) and 129–137 (status table)
- `CLAUDE.md` — "Mandatory Phase Completion Steps" + "Obsidian Vault Integration" + Compliance Freshness rule via memory `feedback_compliance_freshness.md`

### Prior phase context (load-bearing for Phase 49)
- `.planning/phases/48-rich-finding-context/48-CONTEXT.md` — `_build_finding` helper signature + chokepoint pattern; FIPS 203/204/205 literal substring contract that Phase 49 keys off; `tests/test_pqc_terminology_gate.py` as the pytest-CI-gate precedent
- `.planning/phases/46-tls-finding-gaps/46-CONTEXT.md` — risk engine finding branches (lines 343–489 in `risk_engine.py`); chain-verified / cert-defects findings that map to PCI 4.2.1
- `.planning/phases/45-install-day-ux/45-CONTEXT.md` — install-day surrounding patterns

### External standards (cite, do not modify)
- **PCI-DSS 4.0.1** — Payment Card Industry Data Security Standard 4.0.1
  (controls 4.2.1, 4.2.1.1, 6.3.3, 8.3.2). Source:
  <https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf>
- **HIPAA 45 CFR Part 164** — Security and Privacy Standards
  (§164.312(a)(2)(iv), §164.312(e)(1), §164.312(e)(2)(ii)). Source:
  <https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164>
- **NIST FIPS 140-3** — Security Requirements for Cryptographic Modules
  (approved/not-approved algorithm classification). Source:
  <https://csrc.nist.gov/pubs/fips/140-3/final> + SP 800-140 series
- **NIST IR 8547** — Transition to PQC (already on disk per Phase 48 D-06)

### Code under modification
- `quirk/compliance/__init__.py` — **NEW** module; defines `COMPLIANCE_MAP`,
  `UNMAPPED_TITLES`, `STALENESS_THRESHOLD_DAYS`, and the `status_report()`
  function consumed by the CLI subcommand
- `quirk/engine/risk_engine.py` — extend `_build_finding` (Phase 48
  helper) with `compliance` lookup + injection
- `quirk/dashboard/api/schemas.py` — add `compliance: list[ComplianceRef]`
  to finding DTO
- `quirk/reports/html_renderer.py` + `quirk/reports/templates/` —
  Compliance Summary template block
- `quirk/dashboard/api/routes/pdf.py` — confirm PDF path inherits HTML
  template change automatically (Playwright renders the same HTML)
- `run_scan.py` — argparse subcommand refactor (`scan` + `compliance status`)
- **NEW** tests:
  - `tests/test_compliance_schema.py`
  - `tests/test_compliance_title_join.py`
  - `tests/test_compliance_freshness.py`

### Documentation
- `docs/report-interpretation.md` — add a "Compliance Summary" sub-section
  describing how to read the new section. Sync to Obsidian per CLAUDE.md.
- `docs/UAT-SERIES.md` — add UAT-49-01..N covering schema gate, title-join
  gate, staleness gate, CLI subcommand smoke test, and report rendering
  smoke test
- `docs/operators-guide.md` — Phase 50 will document the compliance map
  maintenance process; Phase 49 should add a stub section pointing
  forward to operators-guide.md (Phase 50 RESPONSIBILITY)

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONVENTIONS.md`
- `.planning/codebase/STRUCTURE.md`

### Memory (auto-loaded; flagged here for explicit acknowledgement)
- `feedback_compliance_freshness.md` — version + last_verified + source_url
  + CI staleness check + CLI status command + documented review cadence.
  All five satisfied by COMPLY-06/07/08/09 + D-04 (gates) + D-05 (CLI) +
  Phase 50 operators-guide doc commitment.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_build_finding` helper** (`quirk/engine/risk_engine.py`, Phase 48
  D-02): the chokepoint for finding construction. Phase 49 extends it
  with one additional line: `compliance = COMPLIANCE_MAP.get(title, [])`
  appended to the dict. No new helper required.
- **Pytest-as-CI-gate precedent** (`tests/test_pqc_terminology_gate.py`,
  Phase 48 D-07/08): file-resolution test + invariant test pattern.
  Phase 49 reuses the shape for all three compliance gates.
- **Finding DTO** (`quirk/dashboard/api/schemas.py`): centralized
  Pydantic-ish schema. Adding `compliance: list[ComplianceRef] = []`
  here propagates everywhere without per-route changes.
- **`run_scan:main` entry point**: single argparse `main()` today. Clean
  refactor target — currently no subcommand precedent to break.

### Established Patterns

- **Findings are dicts, not classes**: convention through v4.6. D-02
  preserves this (compliance refs are nested dicts in a list).
- **Wiring problems > greenfield**: Phase 49 is a producer-extension +
  data-table population + renderer-template addition + CLI refactor.
  No new architectural patterns.
- **Mandatory docs + Obsidian sync per phase** (CLAUDE.md): every plan
  must include explicit `docs/UAT-SERIES.md` update + Obsidian phase
  note + `_QUIRK-Hub.md` link refresh tasks.

### Integration Points

- **Risk engine → renderer:** finding dicts now carry `compliance`;
  HTML/PDF templates render the new section.
- **Risk engine → dashboard DTO:** DTO carries `compliance`; future
  BACK-72 dashboard work consumes it without re-implementing lookup.
- **Risk engine → JSON export:** `compliance` propagates as part of
  the finding dict; verify no whitelist/projection drops it.
- **CLI dispatch:** `run_scan.py` becomes a subcommand router. Existing
  `quirk` users with `quirk <args>` continue to work via subcommand
  default-to-scan.

### Areas of Caution

- **`run_scan.py` is large and central** — refactor must preserve every
  existing flag, default, and exit code. Researcher should produce a
  before/after argparse spec for the planner.
- **Finding `title` strings are now load-bearing across phases** —
  D-04's title-join gate is the structural mitigation. Reviewers must
  treat any title rename in `_build_finding` callers as a
  cross-cutting change touching `quirk/compliance/__init__.py`.
- **HTML and PDF render paths must stay in sync** — PDF is rendered from
  HTML via Playwright (per BACK-73 context); the new template block
  must work in both view contexts. Visual regression risk if the
  template uses CSS that PDF rendering doesn't support.

</code_context>

<specifics>
## Specific Ideas

- `STALENESS_THRESHOLD_DAYS = 365` as module-level constant in
  `quirk/compliance/__init__.py` — satisfies COMPLY-08's
  "configurable threshold" by being a named symbol that can be
  monkey-patched in tests or overridden via env var in a future
  enhancement (env-var support is out of scope for v4.6).
- `UNMAPPED_TITLES` as a `frozenset` of finding titles that
  intentionally have no compliance mapping (e.g., observability
  findings, scan-error categories like `D-15` from Phase 41). Each
  entry should carry an inline comment explaining why.
- Phase 50 (Enterprise Documentation) will document the compliance map
  maintenance cadence in `docs/operators-guide.md`. Phase 49 should
  leave a TODO marker in the compliance module's docstring pointing
  forward to that section.

</specifics>

<deferred>
## Deferred Ideas

- **Dashboard Compliance view (BACK-72)** — interactive in-browser
  compliance mapping; out of scope for v4.6 (HTML/PDF-only per
  ROADMAP).
- **Combined Governance + Technical PDF (BACK-73)** — depends on
  BACK-72; deferred to v4.7.
- **Additional frameworks** — NIST CSF, ISO 27001:2022, NSA CNSA 2.0,
  ETSI Quantum-Safe, BSI TR-02102, CMMC 2.0, Common Criteria —
  COMPLY-10/11 already deferred to v4.7 in REQUIREMENTS.md.
- **Structured `category` field on findings** — D-01 alternative;
  rejected for v4.6. Revisit if title strings prove unstable in
  practice (the title-join gate D-04 will surface this signal).
- **Nested-by-framework map shape** — D-01 alternative; rejected for
  v4.6 in favor of flat list. Revisit if rendering by framework
  becomes the dominant traversal pattern (currently the staleness
  walk is at least as common).
- **Lazy / hybrid attachment** — D-02 alternatives; rejected. Revisit
  only if the eager `compliance` field measurably bloats JSON
  exports (unlikely at current finding cardinality).
- **`--format json` for `quirk compliance status`** — Claude's
  discretion; planner may include if trivial, otherwise defer.
- **Env-var override for `STALENESS_THRESHOLD_DAYS`** — out of scope
  for v4.6; module constant is sufficient.

</deferred>

---

*Phase: 49-compliance-mapping*
*Context gathered: 2026-05-05*
