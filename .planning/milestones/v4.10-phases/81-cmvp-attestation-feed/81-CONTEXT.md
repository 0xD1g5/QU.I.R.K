# Phase 81: CMVP Attestation Feed - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can display which NIST CMVP-validated modules cover each discovered algorithm —
as an informational coverage list in the CBOM and HTML/PDF compliance section — with an
offline-capable bundled snapshot, a 90-day staleness CI gate, and a CLI refresh command.

**The system NEVER emits `certified: true` from algorithm-name matching alone.** v4.10-D-01
is a permanent locked invariant; CMVP-07 is its CI enforcement.

Wave A — parallel with Phases 78, 79, 80, 82.

</domain>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 81 (5 success criteria)
- `.planning/REQUIREMENTS.md` — CMVP-01 … CMVP-07 verbatim
- `quirk/qramm/model_meta.py` — staleness pattern (90-day cadence, `STALENESS_THRESHOLD_DAYS = 90`)
- `quirk/compliance/__init__.py` — existing compliance module + 365-day cadence
- `.github/workflows/python-staleness.yml` — existing CI staleness workflow (Phase 81 extends this)
- `quirk/errors.py` — error code registry for refresh CLI failures
- `quirk/cli.py` or `quirk/cli/__init__.py` — CLI dispatch for `quirk compliance cmvp refresh`
- `quirk/reports/executive.py` + `quirk/reports/technical.py` + `report.html.j2` — coverage column injection sites
- `quirk/cbom/builder.py` — Pass-1 algorithm component compliance metadata
- `pyproject.toml` — new dep `beautifulsoup4>=4.13.0`

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — Bundled cache scope
- **Consultant-relevant top-50:** OpenSSL FIPS modules (3.x family), Microsoft CNG/CAPI Kernel + User-mode, Linux kernel crypto API, cloud KMS HSMs (AWS CloudHSM, Azure Dedicated HSM, GCP Cloud HSM), common library FIPS providers (Bouncy Castle FIPS, libsodium FIPS, mbedTLS FIPS). Targets maximum value for the consultant use case.

### Area 2 — Refresh CLI behavior
- **`quirk compliance cmvp refresh`:** writes the cache by default. `--dry-run` previews changes without writing.
- **Failure mode:** network failure or parse failure → exit 1 with cause+remediation message using `quirk/errors.py` registry (Phase 68 pattern). New error codes: `CMVP-REFRESH-NETWORK`, `CMVP-REFRESH-PARSE`, `CMVP-REFRESH-NO-CHANGES` (info-level, exit 0).
- **Offline-capable:** if no network, scan proceeds against the bundled `cmvp_cache.json` snapshot — never blocks on refresh.

### Area 3 — Report UX
- **'CMVP Coverage' column in the algorithm table** — matches ROADMAP success criterion #3 verbatim. Each algorithm row lists module names from `cmvp_cache.json` that cover it. Empty matches render as `"Not in CMVP catalog"`.
- Inline column placement (not separate section) — readability for consultant deliverable.

### Area 4 — Staleness CI gate
- **Hard fail at 91 days** — exactly matches existing QRAMM 90-day pattern in `quirk/qramm/model_meta.py`.
- CI fail message format: `CMVP cache STALE: last_verified=YYYY-MM-DD ({N} days old). Re-verify against {source_url}, then run \`quirk compliance cmvp refresh\` and commit with message "chore: re-verify CMVP catalog (YYYY-MM-DD)"`.
- Extends `.github/workflows/python-staleness.yml` (Phase 51 origin); same monthly cron schedule.

### Cross-cutting (locked by milestone memory)
- **v4.10-D-01 (permanent):** NO code path in `quirk/compliance/cmvp.py` or `quirk/cbom/` emits `certified: true` from algorithm-name matching. CMVP module emits ONLY `fips_140_3_coverage` informational lists (module names covering an algorithm). Active certification of an algorithm requires the specific module + the specific environment — algorithm-name matching alone is insufficient and legally meaningful.
- **CMVP-07 (CI permanent test):** `tests/test_cmvp_no_certified_true.py` asserts no code path emits `certified: true` for any algorithm. Cannot be removed without explicit documented rationale (locked invariant).
- Cache schema: `{"last_verified": "YYYY-MM-DD", "source_url": "https://csrc.nist.gov/...", "modules": [{"name": ..., "vendor": ..., "module_version": ..., "certificate_number": ..., "algorithms": [...], "fips_level": "140-3"}], ...}`.
- New dep `beautifulsoup4>=4.13.0` in `[project] dependencies` (used only by refresh CLI; lxml parser already present per Phase 19 SAML).
- Refresh CLI fetches https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search
- Cache file: `quirk/compliance/cmvp_cache.json` (in-tree, version-controlled).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/qramm/model_meta.py::STALENESS_THRESHOLD_DAYS = 90` — staleness pattern (clone)
- `quirk/compliance/__init__.py` — existing compliance module home
- `quirk/errors.py` (Phase 68) — error code registry for refresh CLI
- `.github/workflows/python-staleness.yml` — CI staleness workflow (extend)

### Established Patterns
- Staleness CI gate = `assert (date.today() - last_verified).days <= 90` + clear remediation message
- CLI dispatch lives in `quirk/cli.py` or `quirk/cli/__init__.py` with subcommand registration
- Compliance helpers live under `quirk/compliance/`
- HTML/PDF report tables already extend gracefully via `quirk/reports/executive.py` + `report.html.j2`
- CBOM Pass-1 already accepts auxiliary compliance metadata (per Phase 22-23 SAML/Kerberos pattern)

### Integration Points
- `quirk/compliance/cmvp.py` — NEW module (refresh logic + cache lookup + coverage query)
- `quirk/compliance/cmvp_cache.json` — NEW bundled cache (committed)
- `quirk/cli/compliance.py` or `quirk/cli.py` — register `compliance cmvp refresh` subcommand
- `quirk/cbom/builder.py` — extend Pass-1 algorithm components with `fips_140_3_coverage` informational property
- `quirk/reports/executive.py` + `technical.py` — add CMVP Coverage column to algorithm tables
- `quirk/reports/templates/report.html.j2` — Jinja column with `| sanitize` filter (Phase 78 chokepoint)
- `pyproject.toml` — `beautifulsoup4>=4.13.0` in `[project] dependencies`
- `.github/workflows/python-staleness.yml` — extend with `tests/test_cmvp_freshness.py` invocation
- `tests/test_cmvp_freshness.py` — NEW staleness CI gate (90-day)
- `tests/test_cmvp_no_certified_true.py` — NEW permanent invariant test (v4.10-D-01 / CMVP-07)
- `tests/test_cmvp_refresh.py` — NEW refresh CLI tests (mock httpx + beautifulsoup4 parsing)
- `tests/test_cmvp_coverage_query.py` — NEW coverage lookup tests (algorithm → module list)
- `tests/test_cmvp_report_column.py` — NEW HTML/PDF column rendering test

</code_context>

<specifics>
## Specific Ideas

- Cache schema must include `source_url` field so the staleness gate message can cite it programmatically.
- The 50-module curation list should be committed as a CSV or YAML alongside `cmvp_cache.json` so future operators can re-run the refresh and see what was selected.
- `quirk compliance cmvp status` — read-only CLI that prints current `last_verified` + staleness days + source URL (mirrors `quirk compliance status` from Phase 51).
- Per-algorithm coverage query returns `list[ModuleName]` ordered by (a) fips_level (140-3 first), (b) most-recently-validated.

</specifics>

<deferred>
## Deferred Ideas

- Active CMVP API integration (not yet exposed by NIST) — out of scope
- CAVP (algorithm-level) validation — separate program from CMVP; out of scope
- Multi-language compliance bundles (FedRAMP, Common Criteria) — out of scope

</deferred>
