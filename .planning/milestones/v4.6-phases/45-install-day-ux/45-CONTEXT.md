# Phase 45: Install-Day UX - Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A user running `pip install quirk` (or `pip install quirk[all]`) in a clean venv can execute any subset of scans without ImportError crashes. When a scanner is enabled in config but its optional extra is not installed, QUIRK emits a single visible advisory finding per skipped scanner that names the exact extra to install. `pip install quirk[all]` installs every optional extra except `[identity]` (impacket is excluded to avoid the pyOpenSSL transitive conflict that downgrades the cryptography lib and breaks the TLS scanner).

In scope: pyproject extras restructure, central optional-extra registry + probe, advisory finding type, install-hint message format.
Out of scope: migrating existing scanners away from their per-file `*_AVAILABLE` flags, new scanner coverage, dashboard install UX changes.

</domain>

<decisions>
## Implementation Decisions

### `[all]` meta-extra composition
- **D-01:** `pip install quirk[all]` resolves to the union of `cloud + db + motion + redis + dashboard`. `[identity]` is intentionally excluded — impacket pulls a pyOpenSSL transitive that downgrades the cryptography library and breaks the TLS scanner. This exclusion is a hard constraint, not a preference; planning must include a regression test that asserts `quirk[all]` does not pull impacket.
- **D-02:** Dashboard is included in `[all]` even though it pulls Playwright browser binaries (significantly larger install). The user explicitly chose the one-stop-install ergonomics over install size. Plan must document the size cost in user-facing install docs so consultants are not surprised.

### Advisory finding shape
- **D-03:** Severity is **INFO** (not LOW). This is a coverage signal, not a security finding in the target. Using LOW would inflate finding counts and give the wrong impression in reports.
- **D-04:** New finding category/kind: `coverage_gap` (or equivalent — researcher should propose the exact field name based on existing FindingItem schema). Category lives on the FindingItem so reports can render coverage gaps in their own section, separate from security findings.
- **D-05:** **One INFO finding per skipped-but-enabled scanner** (not aggregated). Per-scanner granularity makes it trivial to track over time which extras a given user installs/uninstalls and to filter in reports.
- **D-06:** Advisory findings are **persisted to the SQLite DB** the same as other findings (consistent with existing report rendering pipeline that pulls from DB).
- **D-07:** Advisory findings have **zero impact on the readiness/intelligence score** — excluded from severity weighting and excluded from the confidence subscore. They are pure information.

### Where the advisory is emitted
- **D-08:** **Centralized pre-scan probe.** A single registry maps each `extra_name → (importable_modules, scanner_label, install_hint)`. At scan start (after config load, before scanner dispatch), the probe walks the registry and, for each extra whose modules cannot be imported, checks whether the corresponding scanner is enabled in config. If enabled-but-unavailable, the probe emits one INFO finding via the standard finding-emit path. Config-disabled scanners stay silent — no advisory for things the user explicitly turned off.
- **D-09:** The advisory message MUST include the literal `pip install quirk[<extra>]` invocation (e.g., `"Kerberos scanning skipped — install quirk[identity] to enable"`). INSTALL-04 acceptance criterion.

### ImportError pattern reuse
- **D-10:** Add a new module `quirk/util/optional_extra.py` housing the `(extra, modules, scanner_name, install_hint)` registry plus the `is_extra_available(name)` and `probe_missing_extras(config)` helpers used by the centralized probe in D-08.
- **D-11:** **No migration of existing scanners.** The 6+ scanners that currently use `try/except ImportError → MODULE_AVAILABLE = False` (e.g., `broker_scanner.py` `SSLYZE_AVAILABLE`, `email_scanner.py`, `aws_connector.py` `BOTO3_AVAILABLE`) keep their existing pattern. Their tests rely on patching those module-level flags and `*Scanner = None` patch points (`broker_scanner.SslyzeScanner`); migrating risks breaking 6 test suites for no functional gain. A future phase may unify if/when needed.

### Claude's Discretion
- Exact field name for the new finding category on the FindingItem schema (`category`, `kind`, `finding_type`, etc. — researcher should match the existing schema's naming convention).
- Exact wording of the per-scanner install-hint strings (must contain `pip install quirk[<extra>]` and a short scanner-name phrase, but the prose is at planner discretion).
- Whether the report renderer's "Coverage Gaps" section is a new template block or a filter on existing finding rendering — researcher reads `quirk/reports/html_renderer.py` and decides.
- Where in the scan lifecycle the probe is invoked from (likely the scan orchestrator, but pinpointing the call site is a planning decision).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — INSTALL-01..04 acceptance language (no ImportError, advisory finding, `[all]` meta-extra, install-time guidance)
- `.planning/ROADMAP.md` § Phase 45 — goal statement, dependencies (Phase 44/v4.5 complete), and the four success criteria that gate verification

### Codebase maps (already exist)
- `.planning/codebase/STRUCTURE.md` — module layout for `quirk/`
- `.planning/codebase/ARCHITECTURE.md` — scanner pipeline + risk engine + DB persistence flow
- `.planning/codebase/CONVENTIONS.md` — coding patterns (PEP 8, minimal diffs, etc.)

### Existing optional-import patterns to study (not migrate)
- `quirk/scanner/broker_scanner.py` — `SSLYZE_AVAILABLE`, `KAFKA_AVAILABLE`, `REDIS_AVAILABLE` flags + `SslyzeScanner = None` patch points
- `quirk/scanner/email_scanner.py` — `SSLYZE_AVAILABLE` pattern with module-level name fallbacks
- `quirk/scanner/aws_connector.py` — `BOTO3_AVAILABLE` flag

### Schema & wiring
- `quirk/models.py` — current `FindingItem` schema (find the right place for the `coverage_gap` category)
- `quirk/db.py` — finding persistence
- `quirk/reports/html_renderer.py` — report rendering for INFO findings + Coverage Gaps section placement
- `quirk/config.py` + `quirk/config_template.yaml` — `enable_*` flags the probe must consult to know which scanners are on
- `pyproject.toml` `[project.optional-dependencies]` — current extras; this is the file where `[all]` is added

### Project rules
- `CLAUDE.md` § Mandatory Phase Completion Steps — Obsidian phase note + UAT-SERIES.md update + sync to vault are required at end of execution
- `CLAUDE.md` § Code Standards — PEP 8, minimal diffs, run `python -m compileall` and tests after changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **FindingItem model** (`quirk/models.py`): already supports `description`, `remediation`, `severity`, and per-research-memory `quantum_risk` fields. Adding a `coverage_gap` category should be additive, not a schema rewrite.
- **DB finding persistence** (`quirk/db.py`): existing INSERT path can take INFO findings without changes — new advisories ride the same code path.
- **Config `enable_*` flags** (`quirk/config.py`, `quirk/config_template.yaml`): the probe consults these to decide whether an unavailable extra warrants an advisory (only emit if scanner is enabled).
- **Existing `*_AVAILABLE` flag pattern** (broker / email / aws): proven idiom; the new helper imitates the same try/except shape but centralized.

### Established Patterns
- **Optional-import idiom:** every scanner that wraps an optional dep does `try: import X / X_AVAILABLE = True; except ImportError: X_AVAILABLE = False` at module top, then guards entry points. The new helper continues this idiom — does not replace it.
- **Severity discipline:** INFO is currently underused. Coverage gaps are the right occupant for INFO so the severity ladder stays meaningful.
- **Test patching shape:** Tests patch `broker_scanner.SSLYZE_AVAILABLE` and `broker_scanner.SslyzeScanner` directly. Honoring this constraint is why D-11 forbids scanner migration in this phase.

### Integration Points
- **Scan orchestrator** — wherever `Engine.run()` (or equivalent) starts a scan, the centralized probe must be invoked before scanner dispatch so the advisory findings are in the DB before the report is rendered.
- **HTML / PDF report renderers** — need a "Coverage Gaps" section (new template block or filtered render) that surfaces INFO `coverage_gap` findings separately from security findings.
- **`pyproject.toml`** — `[all]` is added here; CI / tests must verify `pip install quirk[all]` resolves and that impacket is absent from the resolved environment.

</code_context>

<specifics>
## Specific Ideas

- Advisory message format: `"<Capability> scanning skipped — install quirk[<extra>] to enable"` (e.g., `"Kerberos scanning skipped — install quirk[identity] to enable"`). The `pip install quirk[<extra>]` literal is required; the prose surrounding it is at planner discretion.
- Regression test that asserts `pip install quirk[all]` does NOT pull `impacket` (e.g., parse the resolver output or import-check after install in CI). This is the structural mechanism that prevents the pyOpenSSL conflict from sneaking back in.
- Plan must touch user-facing install docs (`docs/installation.md` or equivalent) to document that `[all]` includes Playwright browser binaries via the `[dashboard]` extra — consultants installing on resource-constrained laptops should know.

</specifics>

<deferred>
## Deferred Ideas

- **Unify scanner optional-import patterns onto the new helper.** Migrating `broker_scanner.SSLYZE_AVAILABLE`, `email_scanner.SSLYZE_AVAILABLE`, `aws_connector.BOTO3_AVAILABLE`, etc. to call `is_extra_available()` would reduce duplication, but it touches 6+ test suites that patch module-level flag names. Defer to a dedicated cleanup phase after v4.6 ships.
- **Confidence-subscore penalty for coverage gaps.** User chose zero score impact in this phase. If consultants later report that scans with missing extras are misleadingly confident, revisit and consider a small confidence-subscore penalty — keep the severity-weighted score untouched.
- **Aggregated single-finding mode for advisories.** If reports become noisy with many `coverage_gap` rows in large enterprise scans, consider a "compact" rendering mode that collapses them. Per-scanner persistence in DB stays; only the rendering changes.
- **`quirk doctor` / dependency-status CLI command.** Surfacing missing extras *before* a scan (e.g., on `quirk init` or via a dedicated subcommand) was discussed as a future ergonomic improvement. Not in scope for Phase 45.

</deferred>

---

*Phase: 45-install-day-ux*
*Context gathered: 2026-05-03*
