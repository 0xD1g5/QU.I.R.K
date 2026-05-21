---
phase: 81-cmvp-attestation-feed
plan: 02
type: execute
status: complete
updated: 2026-05-16
commit: 5ae447a
requirements:
  - CMVP-01
  - CMVP-03
  - CMVP-05
files_added:
  - quirk/compliance/cmvp.py
  - quirk/cli/cmvp_cmd.py
files_modified:
  - run_scan.py
  - quirk/cbom/builder.py
---

# Phase 81 Plan 02: CMVP Module + Refresh/Status CLI + CBOM Coverage Property

CMVP runtime surface landed: offline coverage lookup, NIST refresh CLI with dry-run, and an
additive `quirk:cmvp-coverage` Property attached to CBOM Pass-1 algorithm components without
touching `_fips_status()`. v4.10-D-01 invariant preserved.

## Files Added

- **`quirk/compliance/cmvp.py`** (528 lines) — Public surface:
  `STALENESS_THRESHOLD_DAYS=90`, `is_cmvp_cache_stale()`, `staleness_days()`,
  `coverage_for_algorithm()`, `normalize_for_cmvp_lookup()`, `refresh_cache(dry_run=)`,
  plus `CMVPRefreshNetworkError` / `CMVPRefreshParseError`. Cache is lazy-loaded with
  runtime assertion shape validation. Coverage ordering: FIPS 140-3 first, then
  `module_version` descending lexicographic. Refresh uses `httpx.Client` (sync) + `bs4`
  (lxml parser), atomic tempfile+replace write, 100ms politeness sleep between detail
  pages. The `_FAMILY_MAP` covers AES, RSA, ECDSA, DSA, EdDSA, KAS, SHS, SHA-3, HMAC,
  DRBG, TripleDES, ML-KEM; ChaCha20/sntrup761 explicitly mapped to `None`. Regex
  fallback covers any unmapped `aes-*`, `rsa-*`, `ecdsa-*`, `ecdh-*`, `sha[2|3]-*`,
  `hmac-*`, `ml-(kem|dsa)-*`, `slh-dsa-*`. NO `certified=True` literal anywhere
  (only a docstring comment stating the prohibition — not a real assignment).

- **`quirk/cli/cmvp_cmd.py`** (148 lines) — Mirrors `quirk/cli/qramm_cmd.py`:
  `_resolve_today()` (honours `QUIRK_CI_STALENESS_OVERRIDE_DATE`), `run_cmvp()`
  dispatcher with `_run_refresh` and `_run_status` branches. Refresh translates
  `CMVPRefreshNetworkError` → `CMVP-REFRESH-NETWORK` exit 1, `CMVPRefreshParseError`
  → `CMVP-REFRESH-PARSE` exit 1, empty-result → `CMVP-REFRESH-NO-CHANGES` exit 0.
  Status prints four-column text table OR JSON envelope (schema_version, last_verified,
  source_url, module_count, age_days, days_remaining, threshold_days, status); exits 0
  FRESH / 1 STALE.

## Files Modified

- **`run_scan.py`** — Inside the existing `compliance` argparse group (lines 408-429),
  added a `cmvp` sub-subparser with `refresh` (+ `--dry-run`) and `status` (+ `--format
  text|json`) actions, and a dispatch branch `if comp_args.action == "cmvp": from
  quirk.cli.cmvp_cmd import run_cmvp; run_cmvp(comp_args); return`. No new top-level
  subcommand introduced.

- **`quirk/cbom/builder.py`** — Added `from quirk.compliance.cmvp import
  coverage_for_algorithm` to the import block (line 38) and extended
  `_make_algorithm_component()` to append an additive
  `Property(name="quirk:cmvp-coverage", value=<comma-joined module names>)` ONLY when
  `coverage_for_algorithm(name)` returns ≥1 match. `_fips_status()` is byte-identical
  to its pre-change state (verified via diff). The new Property is alongside, never
  inside, `quirk:fips140-3-status` (D-81-R3 / v4.10-D-01).

## Verification Results

**Smoke tests (executed against committed code):**

```
$ python -c "from quirk.compliance import cmvp; print(cmvp.coverage_for_algorithm('AES-256-GCM')[:1]); print('count:', len(cmvp.coverage_for_algorithm('AES-256-GCM')))"
[{'certificate_number': '4523', 'vendor': 'Amazon Web Services', 'name': 'AWS CloudHSM',
  'module_version': '', 'fips_level': '140-3', 'overall_level': '1',
  'algorithms': ['AES', 'CKG', 'DRBG', 'ECDSA', 'HMAC', 'KAS', 'KBKDF', 'KTS', 'RSA',
                 'SHA-3', 'SHS', 'TripleDES']}]
count: 52
```

→ AES-256-GCM normalizes to family `AES`; 52 of 53 cached modules cover it.

```
$ python -c "from quirk.compliance import cmvp; print(cmvp.staleness_days())"
0
```

→ Cache is fresh (committed today).

**CBOM hook integration test:**

```
AES props: {'quirk:cmvp-coverage': 'AWS CloudHSM, ...', 'quirk:fips140-3-status': 'approved'}
ChaCha props: {'quirk:fips140-3-status': 'approved'}
CBOM hook OK
```

→ AES-256-GCM Component emits BOTH properties; ChaCha20-Poly1305 emits ONLY
`quirk:fips140-3-status` (no `quirk:cmvp-coverage` appended). Correct per behavior spec.

**CLI smoke (against venv python with full deps):**

```
$ python run_scan.py compliance cmvp --help
usage: quirk compliance cmvp [-h] {refresh,status} ...
positional arguments:
  {refresh,status}
    refresh         Refresh CMVP cache from NIST
    status          Print CMVP cache freshness

$ python run_scan.py compliance cmvp status
Last Verified  Modules    Days Remaining   Status
------------------------------------------------------------
2026-05-16     53         90               FRESH
Source: https://csrc.nist.gov/projects/cryptographic-module-validation-program/validated-modules/search

$ python run_scan.py compliance cmvp status --format json | python -m json.tool
{
  "schema_version": "1.0",
  "last_verified": "2026-05-16",
  "source_url": "...",
  "module_count": 53,
  "age_days": 0,
  "days_remaining": 90,
  "threshold_days": 90,
  "status": "FRESH"
}
```

**Refresh dry-run (mocked httpx, no network):**

```
DRY-RUN diff keys: ['added', 'changed', 'removed']
diff: {'added': [], 'removed': [], 'changed': [53 cert numbers...]}
```

→ Dry-run returns the diff dict and writes nothing. (All 53 cached cert numbers show as
"changed" against the mocked fetch — expected, since the mock returns a uniform stub
detail for each cert; live refresh would produce a much smaller diff.)

**Certified-True gate:**

```
$ grep -rnE "['\"]certified['\"][[:space:]]*[:=][[:space:]]*True" quirk/compliance/ quirk/cbom/ | grep -v test
quirk/compliance/cmvp.py:11:v4.10-D-01 (permanent invariant): NEVER emit ``"certified": True`` anywhere in
```

→ Only match is the module docstring stating the prohibition (a string literal inside a
docstring, NOT a dict-key or kwarg `=True` pairing). The Plan 81-04 AST gate walks
`ast.Dict` and call-keyword nodes — docstring contents will not register as violations.

**CBOM regression suite:**

```
$ pytest tests/test_cbom_builder.py tests/test_cbom_builder_algo_hints.py \
    tests/test_cbom_classifier.py tests/test_cbom_coverage.py tests/test_cbom_integration.py
89 passed in 1.96s
```

→ All pre-existing CBOM tests pass. The additive Property does not break any existing
algorithm component test.

## Deviations

- **Plan-noted** (not a deviation): `_make_algorithm_component`'s real signature is
  `(name, bom_ref_key, key_size=None)`, not `(name, nist_level, oid)` as written in the
  plan's `<verify><automated>` smoke block (line 309). The verification was rewritten
  with the correct signature to confirm Property attachment behavior; the underlying
  behavior contract (AES-256-GCM gets `quirk:cmvp-coverage`, ChaCha20 does not) is
  unchanged.

- **Env note** (not a deviation): The system `python` (Homebrew) lacks `pypdf`; the
  project venv (`.venv/bin/python`) has it. All run_scan smoke tests were executed under
  `.venv/bin/python`. The `pypdf` requirement comes from Plan 81-03's parallel-wave
  edits to `quirk/reports/html_renderer.py` (out of scope for Plan 02).

## Deferred Items

None. All Plan 02 surface delivered.

## Commit

```
commit 5ae447a4959169f06533f266dd474ca58de55d1d
feat(81-02): cmvp module + refresh/status CLI + cbom coverage property

 quirk/cbom/builder.py    |  13 +-
 quirk/cli/cmvp_cmd.py    | 148 +++++++++++++
 quirk/compliance/cmvp.py | 528 +++++++++++++++++++++++++++++++++++++++++++++++
 run_scan.py              |  25 +++
 4 files changed, 713 insertions(+), 1 deletion(-)
```

## Self-Check: PASSED

- `quirk/compliance/cmvp.py` exists (528 lines, ≥150 min)
- `quirk/cli/cmvp_cmd.py` exists (148 lines)
- `run_scan.py` modified (cmvp subparser + dispatch added inside compliance group)
- `quirk/cbom/builder.py` modified (additive `quirk:cmvp-coverage` Property,
  `_fips_status()` untouched)
- Commit `5ae447a` present on HEAD with all 4 files
- v4.10-D-01 holds: no `"certified": True` literal in any executable code path
