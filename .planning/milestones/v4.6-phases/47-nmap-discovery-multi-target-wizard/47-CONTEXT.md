# Phase 47: Nmap Discovery + Multi-Target Wizard — Context

**Gathered:** 2026-05-03
**Status:** Ready for planning

<domain>
## Phase Boundary

A consultant running QUIRK can supply many targets at once — comma-separated hosts, an `@targets-file`, or an IPv4 CIDR range — and optionally pre-discover open ports with nmap before scanning. This unlocks real enterprise 50-host+ engagements without manual port enumeration. Bundled into the same phase: bumping `cyclonedx-python-lib[validation]` → `[json-validation]` so the CBOM JSON QUIRK actually emits is schema-validated at write time.

In scope:
- Multi-target ingestion (CSV, `@file`, CIDR) in `quirk/interactive.py` and via `--targets-file <path>` CLI flag.
- Wiring `quirk/discovery/nmap_provider.py` (already exists) to be invoked from the wizard with a global y/N toggle.
- Probe-budget guard (`targets × ports > 10,000`) with TTY-aware confirmation.
- Coverage-gap INFO finding when `nmap` binary is absent (reuses Phase 45 registry pattern).
- `cyclonedx-python-lib[json-validation]` swap + post-write JSON-schema validation in `quirk/cbom/writer.py` with soft-fail WARN finding.
- Coverage-gap INFO when CBOM-validation deps are missing.

Out of scope:
- Exclude-list (`!host`) syntax — captured as MULTI-06 for a future phase.
- IPv6 CIDR expansion — stdlib `ipaddress` supports it but acceptance criteria name IPv4 only; defer.
- nmap discovery for non-TLS scanners (motion, broker, etc.) — Phase 47 wires nmap into the TLS-host workflow only.
- Migrating existing scanners' `*_AVAILABLE` flag pattern (per Phase 45 D-11).

</domain>

<decisions>
## Implementation Decisions

### Target ingestion semantics
- **D-01:** **One smart wizard prompt, syntax-routed.** `quirk/interactive.py` asks once: "Targets (CSV, @file, or CIDR)". Parser routes per-token: starts with `@` → file load; contains `/` → CIDR expand via stdlib `ipaddress`; contains `,` → split CSV; else → single host. Mixed CSV like `host1,10.0.0.0/24,@extras.txt` is allowed; each token is routed individually.
- **D-02:** **Targets file grammar is permissive.** Each non-blank, non-`#`-prefixed line is one token, routed the same way as wizard input (host / IP / CIDR allowed). No nested `@file` references.
- **D-03:** **CLI `--targets-file` replaces config targets.** When `--targets-file` is given, `config.targets.fqdns` and `config.targets.cidrs` are ignored entirely. Unix tradition (CLI > config > defaults), keeps bulk-scan invocations predictable.
- **D-04:** **CIDR expansion at config-load / argument-parse time** (not at scan-dispatch). The expanded host list feeds the same downstream pipeline that today receives `TargetsCfg.fqdns` — minimizing diff blast radius. Existing `TargetsCfg.cidrs` field stays the source of truth at the model layer; expansion happens before scanner dispatch.
- **D-05:** **Malformed input is a hard error**, not a silent skip. Bad CIDR → `ValueError` from `ipaddress.ip_network` is caught and re-raised as a clear "invalid target: <token>" message. Missing `@file` → `FileNotFoundError` similarly surfaced. Acceptance criterion #5.

### Nmap UX & defaults
- **D-06:** **One global y/N nmap prompt** in the wizard, applied to all targets. Per-target overrides live only in `config.yaml` for power users. Asking 50+ prompts is unusable.
- **D-07:** **Hard-coded `--max-parallelism 100`** in `nmap_provider._default_nmap_args`. Roadmap success criterion #4 names it explicitly (macOS socket-exhaustion guard); not configurable in this phase.
- **D-08:** **When `nmap` binary is absent, emit Phase 45-style coverage_gap INFO finding + fall back to `CONSULTING_TLS_PORTS`.** Extends the optional-extra registry pattern (`quirk/util/optional_extra.py`) to handle binary deps too — researcher should propose whether this is a new helper (`probe_missing_binaries`) or an extension of `probe_missing_extras`. The 17-port consulting list already in `quirk/interactive.py` is the fallback port set. One INFO finding per scan.
- **D-09:** **Non-interactive mode skips the prompt** and uses `config.discovery.enable_nmap` (default false). The wizard prompt only fires when stdin is a TTY.

### Probe-budget guard
- **D-10:** **TTY-aware probe-budget guard.** If `targets × ports > 10,000` and stdout is a TTY, print the projection and require interactive y/N confirmation before nmap fires. In non-TTY (CI, scripted runs), print the warning to stderr and auto-proceed. Uses `sys.stdout.isatty()`.
- **D-11:** **Probe math uses the resolved post-config port list** — the actual workload that will be sent to nmap (wizard ports merged with config defaults), after CIDR expansion of targets. The warning matches reality.
- **D-12:** **Threshold stays at 10,000** — locked by roadmap success criterion #5. Not configurable in this phase.

### CBOM JSON validation
- **D-13:** **Replace `cyclonedx-python-lib[validation]` with `[json-validation]`** in `pyproject.toml`. QUIRK only emits CBOM as JSON via `quirk/cbom/writer.py`; the XML extra is dead weight. Pin window stays `>=11.7.0,<12`.
- **D-14:** **Validation runs after write in `quirk/cbom/writer.py`.** The generated JSON file is loaded back and validated against the cyclonedx JSON schema before the writer returns the path. The file is NOT deleted on failure — user output is preserved.
- **D-15:** **Validation failure is soft-fail.** On schema violation, emit a `coverage_gap`-category WARN finding (`"CBOM JSON failed schema validation: <error summary>"`) and continue. A renderer/schema-drift bug should not kill a 90-minute scan.
- **D-16:** **Missing json-validation deps → Phase 45 coverage_gap INFO finding + skip validation.** Add an entry (e.g., `cbom-validation` → `(jsonschema, py-serializable, ...)` — researcher confirms exact module list from cyclonedx-python-lib's `[json-validation]` extra) to the optional-extra registry. CBOM still gets written, just unvalidated.

### Claude's Discretion
- Exact name and shape of the binary-probe helper in `optional_extra.py` (extend `probe_missing_extras` vs new `probe_missing_binaries`).
- Exact wording of all advisory finding messages — must contain the actionable hint (`pip install quirk[cbom]`, `install nmap`) but prose is at planner discretion.
- Where in the scan orchestrator the probe-budget guard is invoked (likely just before `run_nmap_discovery` is called).
- Whether to introduce a new `quirk/util/targets.py` for the CSV/`@file`/CIDR parser or co-locate in `interactive.py` — researcher should weigh reuse needs (CLI `--targets-file` will need the same parser).
- Exact CycloneDX JSON schema version to validate against (likely whatever `cyclonedx-python-lib` ships).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` § DISCOVER-01..04, MULTI-01..05 — acceptance language for nmap toggle, missing-binary fallback, max-parallelism, probe-budget warning, CSV/@file/CIDR ingestion, malformed-input error
- `.planning/ROADMAP.md` § Phase 47 — goal, dependencies (Phase 45), and the five success criteria that gate verification

### Codebase maps
- `.planning/codebase/STRUCTURE.md` — `quirk/` module layout
- `.planning/codebase/ARCHITECTURE.md` — scanner pipeline, CBOM build/write flow
- `.planning/codebase/CONVENTIONS.md` — PEP 8, minimal diffs

### Existing code to extend (not rewrite)
- `quirk/discovery/nmap_provider.py` — `run_nmap_discovery()` and `_default_nmap_args()` already exist; add the `--max-parallelism 100` arg here if not already present
- `quirk/discovery/nmap_parser.py` — `parse_nmap_xml()` and `NmapOpenPort` dataclass exist
- `quirk/interactive.py` — `_prompt`, `_prompt_int`, `CONSULTING_TLS_PORTS` (17 ports — fallback set when nmap absent)
- `quirk/config.py` § `TargetsCfg` — `fqdns`, `cidrs`, `include_ips`, `exclude_ips` all exist
- `quirk/util/optional_extra.py` — Phase 45 registry; extend for cbom-validation entry and (TBD) binary probes
- `quirk/cbom/writer.py` — where post-write JSON validation hooks in
- `pyproject.toml` `[project.optional-dependencies]` — current `cyclonedx-python-lib[validation]>=11.7.0,<12` line to replace

### Prior phase context
- `.planning/phases/45-install-day-ux/45-CONTEXT.md` — D-03..D-09 establish the coverage_gap INFO finding pattern Phase 47 reuses (D-08, D-15, D-16); D-10 establishes `optional_extra.py` location

### Project rules
- `CLAUDE.md` § Mandatory Phase Completion Steps — Obsidian phase note + UAT-SERIES.md update + sync to vault required at end of execution
- `CLAUDE.md` § Code Standards — PEP 8, minimal diffs, run `python -m compileall` and tests after changes
- `CLAUDE.md` § Chaos Lab Maintenance — Phase 47 does not touch chaos lab profiles, but if scope grows to add a discovery-test profile, `lab.sh` + README + expected-results must update in the same change

</canonical_refs>

<code_context>
## Existing Code Insights

### What's already built
- **Nmap subprocess wrapper:** `quirk/discovery/nmap_provider.py:run_nmap_discovery()` exists with sane defaults (`-sT -n -Pn --open`, conservative retry/timeout). Phase 47 adds `--max-parallelism 100` to the default args and wires invocation from the wizard.
- **Nmap XML parser:** `quirk/discovery/nmap_parser.parse_nmap_xml()` returns `List[NmapOpenPort]`.
- **CIDR field at model layer:** `TargetsCfg.cidrs: List[str]` already exists. Expansion to host list is what's missing.
- **Wizard prompt idioms:** `_prompt(text, default)` and `_prompt_int(text, default, minv, maxv)` in `quirk/interactive.py` — reuse, do not invent.
- **Fallback port set:** `CONSULTING_TLS_PORTS` (17 ports) in `quirk/interactive.py` is the curated consulting list — use as the no-nmap fallback per D-08.
- **Optional-extra registry:** `quirk/util/optional_extra.py` from Phase 45 with `probe_missing_extras(config)` returning INFO findings — extend for `cbom-validation` and (TBD) binary probes.
- **CBOM writer:** `quirk/cbom/writer.py` is where post-write validation hooks in.

### What needs to be added
- Target-input parser (CSV / `@file` / CIDR routing) — likely a new `quirk/util/targets.py` so both wizard and CLI `--targets-file` share it.
- `--targets-file <path>` CLI flag in the entrypoint (`quirk/cli/__init__.py` or wherever argparse lives — researcher confirms).
- TTY-aware probe-budget confirm helper (likely co-located with the target parser).
- `cyclonedx-python-lib[json-validation]` swap in `pyproject.toml`.
- JSON-schema validation call in `cbom/writer.py` + WARN-finding emit path on failure.
- New registry entry for `cbom-validation` (and possibly a binary-probe helper for `nmap`).

</code_context>

<deferred>
## Deferred Ideas

None raised in this discussion. (Roadmap already lists `MULTI-06` exclude-list syntax and `DOCS-05` `quirk doctor` as out-of-scope for v4.6.)

</deferred>
