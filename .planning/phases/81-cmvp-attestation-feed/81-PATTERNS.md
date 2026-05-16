# Phase 81: CMVP Attestation Feed — Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 14 surfaces
**Analogs found:** 14 / 14

## File Classification

| Surface | Role | Data Flow | Closest Analog | Match |
|---------|------|-----------|----------------|-------|
| `quirk/compliance/cmvp.py` | module/service | request-response + cache lookup | `quirk/qramm/model_meta.py` + `quirk/compliance/__init__.py` | role-match |
| `quirk/compliance/cmvp_cache.json` | data asset | static read | `quirk/qramm/model_meta.py::QRAMM_MODEL` (in-code dict) | partial (no JSON precedent — committed JSON is new) |
| `quirk/compliance/cmvp_curation.csv` | data asset | static read | none — new pattern | none |
| CLI `compliance cmvp refresh` / `status` | CLI subcommand | request-response | `run_scan.py:408-429` + `run_scan.py:449-455` | exact (two-level subcommand) |
| `quirk/errors.py` CMVP-* entries | registry extension | static | `quirk/errors.py:163-167` (CBOM-001 block) | exact |
| `quirk/cbom/builder.py` Pass-1 prop | builder/transform | batch-emit | `quirk/cbom/builder.py:295-319` (`_make_algorithm_component`) | exact (same function extended) |
| `quirk/reports/executive.py` + `technical.py` column | reporter | template | `quirk/reports/templates/report.html.j2:304-323` (Endpoint Inventory table) | partial (no algorithm table exists yet) |
| `report.html.j2` CMVP column | template | jinja render | `report.html.j2:307` (table thead pattern) + `:316` (`\| sanitize` filter) | exact |
| `pyproject.toml` bs4 dep | config | static | `pyproject.toml:31` (`nh3>=0.2.17`) | exact |
| `.github/workflows/python-staleness.yml` | CI config | request-response | `.github/workflows/python-staleness.yml:28-33` | exact (extend list) |
| `tests/test_cmvp_freshness.py` | test | static | `tests/test_qramm_staleness.py:41-59` + `tests/test_compliance_freshness.py` | exact |
| `tests/test_cmvp_no_certified_true.py` | test (AST gate) | static | `tests/test_smime_ast_gate.py:28-46` | exact (AST walker pattern) |
| `tests/test_cmvp_refresh.py` | test | mock I/O | `tests/test_jwt_scanner.py:50-67` (httpx mock pattern) | role-match |
| `tests/test_cmvp_coverage_query.py` | test | static | `tests/test_qramm_compliance_map.py` + dict-lookup style | role-match |
| `tests/test_cmvp_report_column.py` | test | template render | `tests/test_report_injection_hardening.py:30-60` | exact |

## Pattern Assignments

### `quirk/compliance/cmvp.py` (NEW module)

**Analog A:** `quirk/qramm/model_meta.py` (staleness math)
**Analog B:** `quirk/compliance/__init__.py:252-283` (`status_report()` printer)

**Top-of-file constants** — copy verbatim shape from `quirk/qramm/model_meta.py:17-25`:
```python
from __future__ import annotations
import datetime

STALENESS_THRESHOLD_DAYS: int = 90  # mirror QRAMM (also 90)

CMVP_CACHE_META = {
    "schema_version": "1.0",
    "last_verified": "2026-05-16",
    "source_url": "https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search",
}
```

**Staleness helper** — clone `quirk/qramm/model_meta.py:28-45` (`is_qramm_model_stale`) verbatim signature:
```python
def is_cmvp_cache_stale(today: datetime.date | None = None) -> bool:
    reference = today or datetime.date.today()
    last_verified = datetime.date.fromisoformat(_load_cache()["last_verified"])
    age = (reference - last_verified).days
    return age > STALENESS_THRESHOLD_DAYS
```

**Coverage query** — new function, lookup-by-algorithm-name:
```python
def coverage_for_algorithm(algo_name: str) -> list[dict]:
    """Return list of CMVP modules covering algo_name, ordered by
    (fips_level=='140-3' first, then most-recent validation date).
    NEVER returns {'certified': True} — only informational module names.
    Empty list = "Not in CMVP catalog"."""
    cache = _load_cache()
    matches = [m for m in cache["modules"] if algo_name in m.get("algorithms", [])]
    return sorted(matches, key=lambda m: (m.get("fips_level") != "140-3", m.get("certificate_date", "")), reverse=False)
```

**Refresh function** — fetch + bs4-parse + dry-run support:
```python
def refresh_cache(dry_run: bool = False) -> dict:
    """Fetch CMVP search page, parse top-50 curated modules, write cache.
    Raises with CMVP-REFRESH-NETWORK on httpx failure;
    CMVP-REFRESH-PARSE on bs4 selector miss."""
    # httpx.Client (sync) — mirror jwt_scanner pattern; NOT async
    # beautifulsoup4 parses validated-modules table
    # write cmvp_cache.json atomically; respect dry_run flag
```

**Diff vs. analog:** model_meta stores the entire dict in-source; CMVP stores the dict in a versioned JSON file with same key shape (`last_verified`, `source_url`, plus `modules`). The cache file is read at import time into a module-level cached dict.

---

### `quirk/compliance/cmvp_cache.json` (NEW bundled snapshot)

**Schema** — locked by CONTEXT.md Area Cross-cutting:
```json
{
  "schema_version": "1.0",
  "last_verified": "2026-05-16",
  "source_url": "https://csrc.nist.gov/...",
  "modules": [
    {"name": "OpenSSL FIPS Provider", "vendor": "OpenSSL Project",
     "module_version": "3.0", "certificate_number": "4282",
     "algorithms": ["AES-256-GCM", "SHA-256", ...],
     "fips_level": "140-3"}
  ]
}
```

**Top-50 curation** per CONTEXT Area 1: OpenSSL FIPS 3.x family, Microsoft CNG/CAPI Kernel + User-mode, Linux kernel crypto API, AWS CloudHSM, Azure Dedicated HSM, GCP Cloud HSM, Bouncy Castle FIPS, libsodium FIPS, mbedTLS FIPS.

**Drift flag:** No existing committed JSON data file under `quirk/compliance/` — `__init__.py` is currently the only file. Confirmed package (has `__init__.py`).

---

### `quirk/compliance/cmvp_curation.csv` (NEW curated module list)

**Analog:** none — net-new artifact. Use simple CSV: `module_name,vendor,certificate_number,reason_selected`. Lives alongside `cmvp_cache.json` so operators can re-run refresh and audit selection.

---

### CLI `quirk compliance cmvp refresh` / `quirk compliance cmvp status`

**Analog:** `run_scan.py:408-429` (existing `quirk compliance status`)

**Pattern to extend** — `run_scan.py:408-429` already implements the `compliance` two-level dispatcher. Phase 81 ADDS a `cmvp` sub-subcommand to `comp_sub`:

```python
# After the existing status_parser block (run_scan.py:415-424):
cmvp_parser = comp_sub.add_parser("cmvp", help="Inspect / refresh CMVP attestation cache")
cmvp_sub = cmvp_parser.add_subparsers(dest="cmvp_action", required=True)

cmvp_refresh = cmvp_sub.add_parser("refresh", help="Refresh CMVP cache from NIST")
cmvp_refresh.add_argument("--dry-run", action="store_true",
                          help="Preview changes without writing the cache")

cmvp_status = cmvp_sub.add_parser("status", help="Print CMVP cache freshness")
cmvp_status.add_argument("--format", choices=["text", "json"], default="text")
```

**Dispatch** — extend the `if comp_args.action == "status"` branch at line 426:
```python
if comp_args.action == "cmvp":
    from quirk.cli.cmvp_cmd import run_cmvp
    run_cmvp(comp_args)
    return
```

**New module:** `quirk/cli/cmvp_cmd.py` — mirror `quirk/cli/qramm_cmd.py` (84 lines, full file as analog). The status function clones `run_qramm_status()` at lines 44-65: print four-column table, exit 0 (FRESH) / 1 (STALE), honor `QUIRK_CI_STALENESS_OVERRIDE_DATE` per `_resolve_today()` at lines 24-41.

**Drift flag (confirmed):** `quirk compliance status` already exists (Phase 49 D-05). The `compliance` argparse group exists at `run_scan.py:408-429`. Phase 81 only adds the `cmvp` child subparser — does NOT register a new top-level group.

---

### `quirk/errors.py` — CMVP-* entries

**Analog:** `quirk/errors.py:163-167` (CBOM-001 single-entry block) + the INSTALL/SCHED blocks for multi-entry domain shape.

**What to copy** — insert a new domain block after CBOM-001 (around line 168), preserving the `ErrorEntry(code=..., cause=..., fix=...)` shape:
```python
# --- CMVP domain (Phase 81) ---
"CMVP-REFRESH-NETWORK": ErrorEntry(
    code="CMVP-REFRESH-NETWORK",
    cause="Could not fetch CMVP search page (network error).",
    fix="Verify connectivity to csrc.nist.gov; retry `quirk compliance cmvp refresh`. Offline scans still use the bundled cache.",
),
"CMVP-REFRESH-PARSE": ErrorEntry(
    code="CMVP-REFRESH-PARSE",
    cause="CMVP search page HTML did not match expected selectors.",
    fix="NIST page structure may have changed. File an issue and pin to the bundled cache until parser updated.",
),
"CMVP-REFRESH-NO-CHANGES": ErrorEntry(
    code="CMVP-REFRESH-NO-CHANGES",
    cause="CMVP cache already current; no modules changed.",
    fix="No action needed. Bump `last_verified` only if re-verifying without content change.",
),
"CMVP-STALE": ErrorEntry(
    code="CMVP-STALE",
    cause="CMVP cache is older than 90 days.",
    fix="Run `quirk compliance cmvp refresh` and commit with message `chore: re-verify CMVP catalog (YYYY-MM-DD)`.",
),
```

**Adapt:** entries follow `INSTALL-009` precedent (line 62-66) — staleness errors point at remediation runbook, not a traceback.

---

### `quirk/cbom/builder.py` Pass-1 `fips_140_3_coverage` extension

**Analog:** `quirk/cbom/builder.py:295-319` (`_make_algorithm_component`)

**Existing `_fips_status` at line 281-292** explicitly reserves `"certified"` for "a future phase with CMVP attestation" — that future phase IS Phase 81. **DO NOT** change `_fips_status` to return `"certified"` — v4.10-D-01 forbids it. Instead, attach `fips_140_3_coverage` as a SEPARATE `Property` alongside the existing `quirk:fips140-3-status` property at line 318:

```python
# Inside _make_algorithm_component, after line 318:
from quirk.compliance.cmvp import coverage_for_algorithm

properties = [Property(name="quirk:fips140-3-status", value=_fips_status(nist_level))]
coverage = coverage_for_algorithm(name)
if coverage:
    module_names = ", ".join(m["name"] for m in coverage)
    properties.append(Property(name="quirk:cmvp-coverage", value=module_names))
# pass properties=properties to Component(...)
```

**Critical:** NEVER emit `certified: true` or any boolean attestation. The property value is an informational comma-separated string of module names — pure metadata, never a certification claim.

**Adapt vs. analog:** mirrors how Phase 79 SMIME / Phase 80 ADCS attach scanner-derived metadata as extra `Property` rows (single-line additive — no schema migration).

---

### Report CMVP Coverage column (HTML + technical/executive)

**Analog A (template thead pattern):** `quirk/reports/templates/report.html.j2:307` (Endpoint Inventory `<thead>`)
**Analog B (sanitize chokepoint, Phase 78):** `report.html.j2:316` — every scanner-controlled cell wraps with `{{ value | sanitize }}`. See also the comment at line 176: *"Phase 78 / HARDEN-02..03: every scanner-controlled cell piped through | sanitize."*

**No existing algorithm table** — `report.html.j2` currently has Endpoint Inventory but NOT a per-algorithm summary. Phase 81 introduces the algorithm table.

**Pattern to apply** — new `<section>` mirroring lines 304-323:
```jinja
<h2>Algorithm Inventory (FIPS 140-3 Coverage)</h2>
{% if algorithms %}
<table>
  <thead><tr><th>Algorithm</th><th>NIST Level</th><th>FIPS Status</th><th>CMVP Coverage</th></tr></thead>
  <tbody>
  {% for a in algorithms %}
  <tr>
    <td>{{ a.name | sanitize }}</td>
    <td>{{ a.nist_level }}</td>
    <td>{{ a.fips_status | sanitize }}</td>
    <td>{{ a.cmvp_coverage | sanitize if a.cmvp_coverage else 'Not in CMVP catalog' }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% endif %}
```

**Sanitize chokepoint** — every scanner-controlled cell (algorithm name, status, coverage list) MUST pipe through `| sanitize`. The literal string `"Not in CMVP catalog"` is template-static and not sanitized.

**Renderer wiring:** `quirk/reports/html_renderer.py` (or `writer.py`) must pass a new `algorithms` template context derived from the CBOM Pass-1 algo_registry. `executive.py` and `technical.py` are markdown reports — add a new "CMVP Coverage" column to the algorithm table there as well.

---

### `pyproject.toml` — `beautifulsoup4>=4.13.0`

**Analog:** `pyproject.toml:31` (`"nh3>=0.2.17",` — Phase 78 single-line core dep addition).

**Insert** — single line into `[project] dependencies` at line 11-32. Order doesn't matter; group near `lxml>=6.0` at line 28 (related HTML/XML parsing):
```toml
    "beautifulsoup4>=4.13.0",
```

**Note:** `lxml>=6.0` is already core (line 28, Phase 19 SAML); bs4 will use the `lxml` parser, no separate parser dep needed.

---

### `.github/workflows/python-staleness.yml` — add CMVP freshness gate

**Analog:** `.github/workflows/python-staleness.yml:28-33` (existing pytest invocation block)

**Extend** — add `tests/test_cmvp_freshness.py` to the existing pytest list:
```yaml
- name: Run staleness gates
  run: |
    pytest \
      tests/test_qramm_staleness.py \
      tests/test_compliance_freshness.py \
      tests/test_error_codes_freshness.py \
      tests/test_cmvp_freshness.py \
      -v
```

**No schedule change** — Monday 09:00 UTC cron at line 5-6 already runs weekly.

---

### `tests/test_cmvp_freshness.py` (NEW staleness CI gate)

**Analog A:** `tests/test_qramm_staleness.py:41-59` (`test_qramm_model_not_stale`)
**Analog B:** `tests/test_compliance_freshness.py` (entire file, 27 lines)

**Clone shape** — exact mirror of `test_qramm_model_not_stale` at lines 41-59, swapping `QRAMM_MODEL` → cache load, `qramm/model_meta.py` → `quirk/compliance/cmvp_cache.json`. Honor `QUIRK_CI_STALENESS_OVERRIDE_DATE` env var per lines 47-52 so CI can simulate stale state. Failure message format per CONTEXT Area 4: `CMVP cache STALE: last_verified=YYYY-MM-DD ({N} days old). Re-verify against {source_url}, then run \`quirk compliance cmvp refresh\` and commit with message "chore: re-verify CMVP catalog (YYYY-MM-DD)"`.

**Also include:** `test_cmvp_staleness_override_fresh` + `test_cmvp_staleness_override_stale` mirroring `test_qramm_staleness.py:62-81`.

---

### `tests/test_cmvp_no_certified_true.py` (NEW permanent invariant — v4.10-D-01 / CMVP-07)

**Analog:** `tests/test_smime_ast_gate.py:28-46` (AST walker pattern); `tests/test_adcs_ast_gate.py` (same shape).

**Pattern** — AST-walk `quirk/compliance/cmvp.py`, `quirk/cbom/builder.py`, and `quirk/cbom/classifier.py` for any `ast.Constant(value=True)` paired with key/attr name `certified`, or any `ast.Dict` whose key `"certified"` maps to `True`. Fail if found.

```python
# Mirror tests/test_smime_ast_gate.py:28-46 (_collect_violations) but target:
FORBIDDEN_KEYS = {"certified"}
TARGETS = [
    PROJECT_ROOT / "quirk" / "compliance" / "cmvp.py",
    PROJECT_ROOT / "quirk" / "cbom" / "builder.py",
    PROJECT_ROOT / "quirk" / "cbom" / "classifier.py",
]

def _collect_violations(tree):
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if (isinstance(k, ast.Constant) and k.value in FORBIDDEN_KEYS
                    and isinstance(v, ast.Constant) and v.value is True):
                    violations.append(f"line {k.lineno}: '{k.value}': True")
        # also check keyword=Constant(True) on calls with name 'certified'
    return violations
```

**Self-tests** — clone the synthetic-positive/synthetic-negative pattern at `test_smime_ast_gate.py:71-120`. Permanent invariant — cannot be removed without explicit documented v4.10-D-01 rationale.

---

### `tests/test_cmvp_refresh.py` (NEW refresh CLI unit tests)

**Analog:** `tests/test_jwt_scanner.py:50-67` (`patch("quirk.scanner.jwt_scanner.httpx")` mock pattern)

**Pattern** — mock `httpx.Client` (sync, since refresh is a one-shot CLI call, not async) and pre-canned HTML response; verify:
- Happy-path: bs4 parses → cache written → exit 0
- Network failure (`httpx.ConnectError`): exit 1 with `CMVP-REFRESH-NETWORK` in stderr
- Parse failure (malformed HTML): exit 1 with `CMVP-REFRESH-PARSE` in stderr
- `--dry-run`: no file write, prints diff summary

```python
from unittest.mock import patch, MagicMock
with patch("quirk.compliance.cmvp.httpx") as mock_httpx:
    mock_resp = MagicMock(text="<html>...</html>", status_code=200)
    mock_httpx.Client.return_value.__enter__.return_value.get.return_value = mock_resp
    # call refresh_cache(dry_run=False); assert cache shape
```

---

### `tests/test_cmvp_coverage_query.py` (NEW coverage lookup tests)

**Analog:** `tests/test_qramm_compliance_map.py` (dict-lookup style) + any `quirk/compliance/__init__.py::status_report` test.

**Pattern** — direct function calls into `coverage_for_algorithm(name)` with a fixture cache; assert:
- Known algorithm (e.g. `"AES-256-GCM"`) returns ≥1 module
- Unknown algorithm returns `[]`
- Ordering: FIPS 140-3 modules appear before 140-2; within tier, most-recent-validated first
- Return type is `list[dict]` — never raises on missing keys

---

### `tests/test_cmvp_report_column.py` (NEW HTML/PDF column rendering test)

**Analog:** `tests/test_report_injection_hardening.py:30-60` (end-to-end render fixture)

**Pattern** — build SimpleNamespace cfg per `_make_cfg` at lines 31-44, synthesize a `CryptoEndpoint` with a known FIPS-covered algorithm (e.g. AES-256-GCM via OpenSSL FIPS Provider), invoke `write_reports`, glob the HTML output, and assert:
- "Algorithm Inventory" heading present
- "CMVP Coverage" column header present
- Known module name (e.g. "OpenSSL FIPS Provider") in correct row
- Unmapped algorithm row renders `"Not in CMVP catalog"`
- XSS payload in algorithm name is escaped/stripped (sanitize chokepoint regression)

PDF assertions guarded by `pytest.importorskip("playwright.sync_api")` per the analog's pattern at line 13.

---

## Shared Patterns

### Staleness math
**Source:** `quirk/qramm/model_meta.py:28-45` (`is_qramm_model_stale`)
**Apply to:** `quirk/compliance/cmvp.py::is_cmvp_cache_stale`
**Boundary:** `age > STALENESS_THRESHOLD_DAYS` — strict greater-than, so exactly 90 days is NOT stale (matches QRAMM).

### Staleness override env var
**Source:** `quirk/cli/qramm_cmd.py:24-41` (`_resolve_today`)
**Apply to:** `quirk/cli/cmvp_cmd.py` — honor `QUIRK_CI_STALENESS_OVERRIDE_DATE` with the same try/except → fallback to `datetime.date.today()` shape.

### CLI two-level subcommand dispatch
**Source:** `run_scan.py:408-429` (`compliance` group) + `run_scan.py:449-455` (`qramm` group)
**Apply to:** new `compliance cmvp refresh` / `compliance cmvp status` — extend the EXISTING `compliance` block, do not create a new top-level group.

### Error code registry extension
**Source:** `quirk/errors.py:20-221` (single dict, alphabetical-by-domain blocks)
**Apply to:** insert CMVP-* block after CBOM-001 at line 167.

### Sanitize chokepoint (Phase 78 HARDEN-02/03)
**Source:** `report.html.j2:176` (comment) + `:183,184,185,...` (every scanner-controlled cell)
**Apply to:** every cell in the new Algorithm Inventory table — wrap with `| sanitize`.

### AST CI gate
**Source:** `tests/test_smime_ast_gate.py:28-89` (full pattern: `_collect_violations` + main test + self-tests)
**Apply to:** `tests/test_cmvp_no_certified_true.py` — different forbidden pattern (`{"certified": True}`), same scaffold.

### httpx mocking in unit tests
**Source:** `tests/test_jwt_scanner.py:50-67`
**Apply to:** `tests/test_cmvp_refresh.py` — same `patch("...httpx")` shape.

---

## Drift / Mismatch Flags

1. **CONFIRMED:** `quirk/compliance/` is a package — `__init__.py` exists. Cache file `cmvp_cache.json` can land alongside it.
2. **CONFIRMED:** `quirk compliance status` already exists (Phase 49 D-05 at `run_scan.py:408-429`). Phase 81 adds the `cmvp` SUB-subcommand to the existing `compliance` argparse group — does NOT register a new top-level group.
3. **CONFIRMED:** CLI entrypoint is `run_scan.py` (not `quirk/cli.py` or `quirk/__main__.py`). All test smoke fixtures invoke `python run_scan.py compliance cmvp …`. CONTEXT.md's reference to `quirk/cli.py` is incorrect — use `run_scan.py` + `quirk/cli/cmvp_cmd.py` (mirror `quirk/cli/qramm_cmd.py`).
4. **CONFIRMED:** No existing algorithm table in `report.html.j2` — Phase 81 introduces it. The "Endpoint Inventory" table at lines 304-323 is the closest pattern; clone its shape (thead/tbody + `| sanitize` cells) for the new Algorithm Inventory section.
5. **CONFIRMED:** `_fips_status` at `quirk/cbom/builder.py:281-292` documents `"certified"` as reserved for "a future phase with CMVP attestation" — that future phase is Phase 81, but per v4.10-D-01 we explicitly **do not** activate the `certified` tier. We attach CMVP coverage as a SEPARATE `Property(name="quirk:cmvp-coverage", value=<module names>)` and leave `_fips_status` untouched.
6. **CONFIRMED:** `lxml>=6.0` already in core deps (pyproject.toml:28) — bs4 will use lxml parser, no extra dep beyond `beautifulsoup4` itself.
7. **CONFIRMED:** Staleness CI workflow at `.github/workflows/python-staleness.yml:28-33` invokes pytest with a fixed list — Phase 81 appends `tests/test_cmvp_freshness.py` to that list, no new job needed.
8. **NEW PATTERN:** `quirk/compliance/cmvp_cache.json` is the first committed JSON data file in `quirk/compliance/`. There is no precedent; the closest pattern is `quirk/qramm/model_meta.py::QRAMM_MODEL` (in-source dict). Justify the divergence: the CMVP cache is large (~50 modules × algorithm lists) and would clutter a `.py` file; JSON keeps refresh idempotent and diff-readable.

## Metadata

**Analog search scope:** `quirk/`, `tests/`, `.github/workflows/`, `pyproject.toml`, `run_scan.py`
**Files scanned:** ~25
**Pattern extraction date:** 2026-05-16
