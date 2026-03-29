# Phase 1: Foundation Fixes - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix what is broken, make the codebase correct and consistent, rename to QU.I.R.K., and replace
the banner-only SSH scanner and basic TLS scanner with deep-enumeration implementations
(ssh-audit and sslyze). No new scan surfaces (Phase 3), no CBOM (Phase 2), no UI (Phase 5).

</domain>

<decisions>
## Implementation Decisions

### sslyze Integration (SCAN-01)
- **D-01:** Use sslyze as the primary TLS scanner. If sslyze fails to scan a target (error,
  timeout, connection refused), fall back to the existing `ssl`+`cryptography` scanner to
  preserve data for that endpoint. Two code paths — sslyze primary, existing as fallback.
- **D-02:** The existing `tls_scanner.py` is NOT deleted — it becomes the fallback. The new
  sslyze path is the first branch; the existing code is the else/except branch.
- **D-03:** sslyze results map to existing `CryptoEndpoint` fields where possible (cert, cipher,
  tls_version). New sslyze-only data (cipher suite list, chain depth, protocol version matrix)
  goes into `tls_capabilities_json` — check if this field exists, if not add it additively.

### ssh-audit Integration (SCAN-02)
- **D-04:** Run ssh-audit as a subprocess (`ssh-audit --json`), parse JSON output.
  Library import is not used — subprocess is more stable.
- **D-05:** Store the full ssh-audit JSON output in a single new column `ssh_audit_json TEXT`
  on `CryptoEndpoint`. One additive schema change. No typed columns for individual
  algorithm categories (avoids rigid schema, stays additive-only).
- **D-06:** The MVP banner-grab in `tls_version` field is replaced — `tls_version` is no longer
  misused for SSH data. Use the existing `cipher_suite = "SSH"` marker to identify SSH endpoints.

### SSH Scanner Threading (CORE-04)
- **D-07:** Replace the sequential loop in `scan_ssh_targets()` with `ThreadPoolExecutor`.
  Use the same concurrency patterns already established in the TLS scanner (check `run_scan.py`
  for the existing thread pool configuration and match it).

### Scoring Consolidation (CORE-01)
- **D-08:** `intelligence/scoring.py` → `compute_readiness_score(evidence)` is the single
  authoritative scoring path. It is already used by `scorecard.py` and tested.
- **D-09:** Remove the `assessment.readiness_score.compute_readiness_score()` call from
  `writer.py` (currently the "legacy but still supported" path at line ~586). This removes
  the `assessment.readiness_score` block from scan output JSON. Clean break — no shim.
- **D-10:** Replace `_score_from_evidence()` in `writer.py` with a call to
  `intelligence.scoring.compute_readiness_score(evidence)`. The inline function is deleted.
- **D-11:** `assessment/readiness_score.py` becomes dead code after D-09. Delete the file
  and its imports from writer.py.

### cert_pubkey_alg Field Fix (CORE-02)
- **D-12:** Fix `_extract_cert_key_type()` in `writer.py`. The function checks wrong attribute
  names (`cert_key_type`, `cert_pubkey_type`, `cert_public_key_type`, `cert_key_algo`,
  `cert_pubkey_algo`). The actual field on `CryptoEndpoint` is `cert_pubkey_alg`. Replace
  the probe list with just `cert_pubkey_alg` as the first (and primary) check.

### Rename: QU.I.R.K. (CORE-03)
- **D-13:** Full package rename — `qcscan/` directory renamed to `quirk/`. All Python imports
  updated from `from qcscan.xxx` → `from quirk.xxx`. All references in `run_scan.py` and
  test files updated. This is a sed sweep across all `.py` files.
- **D-14:** `setup.py` / `pyproject.toml` package name updated to `quirk`.
- **D-15:** CLI entry point renamed: `run_scan.py` becomes the `quirk` command entry point
  (or a thin `quirk.py` wrapper). `quirk --help`, `quirk scan`, etc.
- **D-16:** All user-facing strings updated: `PLATFORM_VERSION` stays at `"3.9"` version number
  but product name in report headers → `"QU.I.R.K."`. Config file keys that say `qcscan`
  → `quirk`. Markdown report headers updated.
- **D-17:** The one remaining Python-file `QuRisk` reference in `validate.py` is updated.

### Claude's Discretion
- Exact sslyze `ScanCommand` set (which commands to run per target)
- sslyze async vs synchronous scan execution model
- ThreadPoolExecutor pool size for SSH scanner (infer from existing TLS pool config)
- How to handle ssh-audit not installed (clear error message + install instructions)
- How to handle sslyze not installed (graceful fallback to existing scanner, warning logged)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing scanner code
- `qcscan/scanner/tls_scanner.py` — Current TLS scanner (becomes fallback); understand field population
- `qcscan/scanner/ssh_scanner.py` — Current SSH scanner (replace with threaded + ssh-audit)
- `qcscan/models.py` — `CryptoEndpoint` SQLAlchemy model; field names are canonical (cert_pubkey_alg)
- `qcscan/reports/writer.py` — Three scoring calls, `_extract_cert_key_type()` bug, field mapping

### Scoring systems (all three must be understood before consolidating)
- `qcscan/intelligence/scoring.py` — Authoritative scoring model (survives)
- `qcscan/assessment/readiness_score.py` — Legacy model (deleted after D-09/D-11)
- `qcscan/reports/scorecard.py` — Already uses intelligence/scoring.py correctly (reference for correct usage)

### Schema and persistence
- `qcscan/models.py` — SQLAlchemy model; new columns must be additive (no breaking changes)

### Tests
- `tests/test_intelligence_scoring.py` — Must pass after consolidation
- `tests/test_intelligence_confidence.py` — Must pass after consolidation

### Requirements
- `.planning/REQUIREMENTS.md` §CORE-01…CORE-04, SCAN-01…SCAN-02
- `.planning/ROADMAP.md` §Phase 1 — Success criteria are the acceptance gates

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `qcscan/intelligence/evidence.py` — `build_evidence_summary()` already produces the evidence dict that `intelligence/scoring.py` consumes. Don't rebuild this.
- `qcscan/intelligence/confidence.py` — `compute_confidence()` already uses evidence model. Stays as-is.
- `qcscan/reports/scorecard.py` — Correct integration example of intelligence/scoring.py + confidence. Use as reference for writer.py consolidation.
- `run_scan.py` `_get_scan_int()` — Existing thread pool concurrency configuration. SSH scanner should use same pattern.

### Established Patterns
- Thread pool: TLS scanner already uses `ThreadPoolExecutor`. SSH scanner sequential loop is the outlier — match TLS pattern.
- Error classification: `_categorize_tls_error()` in tls_scanner.py classifies errors into typed strings. sslyze errors should get the same treatment.
- Evidence model: `_normalize_evidence()` in writer.py is the bridge between raw endpoints+findings and the scoring input. This is the integration point for new ssh-audit data.

### Integration Points
- `writer.py` `generate_report()` is the main orchestration function — scoring consolidation changes happen here
- `writer.py` `_normalize_evidence()` — where ssh_audit_json fields get parsed into evidence counts (if needed for scoring)
- `qcscan/models.py` `CryptoEndpoint` — where `ssh_audit_json` TEXT column gets added
- `run_scan.py` — where `scan_ssh_targets()` is called; threading changes transparent to caller

</code_context>

<specifics>
## Specific Ideas

- sslyze should be treated as "not installed is okay" — log a warning and fall back to existing scanner silently. Don't require sslyze at install time (yet — Phase 7 can make it a required dep).
- ssh-audit similarly: if not installed, SSH endpoints fall back to banner-grab with a warning. Don't hard-require it.
- The rename is a mechanical sweep. The key risk is missing a reference — run `grep -r "qcscan" .` after the rename to catch stragglers.
- `quirk` should be the CLI command name. Users will type `quirk scan 192.168.1.0/24`, `quirk --help`, etc.

</specifics>

<deferred>
## Deferred Ideas

- sslyze ROBOT/DROWN/HEARTBLEED vulnerability checks — new scan surface, Phase 3 scope
- ssh-audit remediation suggestions in the report — Phase 6 (documentation/reporting)
- Making sslyze/ssh-audit hard requirements with version pinning — Phase 7 (packaging)
- `quirk serve` (dashboard command) — Phase 5
- pip install quirk distribution — Phase 7

</deferred>

---

*Phase: 01-foundation-fixes*
*Context gathered: 2026-03-28*
