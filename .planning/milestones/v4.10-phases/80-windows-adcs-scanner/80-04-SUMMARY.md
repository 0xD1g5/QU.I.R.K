---
phase: 80-windows-adcs-scanner
plan: 04
type: execute
status: complete
subsystem: identity / tests / phase-closure
tags: [adcs, ldap, tests, ast-gate, extras-matrix, phase-closure]
dependency_graph:
  requires: [80-01, 80-02, 80-03]
  provides: [adcs-test-coverage, adcs-09-static-gate, adcs-09-runtime-gate, adcs-07-ci-matrix, phase-80-closure]
  affects: [tests/, docs/UAT-SERIES.md, Obsidian vault]
tech_stack:
  added: []
  patterns: [mocked-ldap3 contract test, sentinel-monkeypatched CSR builder, AST CI gate (D-80-R4), pip --dry-run --report JSON parse]
key_files:
  created:
    - tests/test_adcs_scanner.py
    - tests/test_adcs_no_writes.py
    - tests/test_adcs_ast_gate.py
    - tests/test_extras_install_matrix.py
    - tests/fixtures/adcs/ca-weak.der
    - tests/fixtures/adcs/templates.json
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-80-Windows-AD-CS-Scanner.md
  modified:
    - docs/UAT-SERIES.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
decisions:
  - "Injected stub ldap3 module (SimpleNamespace with SUBTREE/ANONYMOUS/SIMPLE/ALL constants + core.exceptions.LDAPBindError) into the scanner namespace via patch.object — base CI Python env has no ldap3 installed, but the scanner references ldap3.SUBTREE inside scan_adcs_targets so a bare LDAP3_AVAILABLE=True patch is insufficient."
  - "AST gate flags .add/.modify/.delete/.modify_dn ONLY on Call nodes whose .func is an ast.Attribute (i.e., method-call sites), not on bare attribute reads — avoids tripping on legitimate non-call attribute access patterns while still catching every ldap3 write surface."
  - "Extras matrix uses `pip install --dry-run --report` JSON parser pattern (inherited from tests/test_install_all_excludes_impacket.py); helper `_resolved_packages(extras)` returns {name_lower: version} for floor-version assertion."
metrics:
  duration_minutes: ~25
  tasks_complete: 6
  files_touched: 8
  completed: 2026-05-16
requirements:
  - ADCS-04
  - ADCS-07
  - ADCS-09
---

# Phase 80 Plan 04: Tests + AST gate + extras matrix + phase closure Summary

Locked Phase 80 with four pytest files (11 tests total — 8 fast + 3 slow-marked), six fixture artifacts, the UAT-SERIES update + vault sync, and the Obsidian phase note. All ADCS-* requirements now closed; Phase 80 ships.

## What Was Built

### `tests/test_adcs_scanner.py` (3 tests)

Mocked-`ldap3` contract tests. Patches `adcs_scanner._bind_and_query` to return a `MagicMock` connection whose `.extend.standard.paged_search` yields the CA list on its first call and the template list on its second call (via `side_effect=[iter(...), iter(...)]`).

- `test_full_chaos_lab_contract_against_mocked_ldap` — feeds 1 CA entry (weak DER) + 3 template entries (BadTemplate-ESC1, BadTemplate-ESC4, SafeTemplate); asserts exactly 6 findings per target: 1 HIGH `weak-signing-alg` CA (RSA-1024 SHA-1, `cert_pubkey_alg="RSA"`, `cert_pubkey_size=1024`, `adcs_scan_json` populated with `ca_cn="QuirkLabCA"` + `reasons=["weak-signing-alg", "weak-rsa-key"]`), 1 HIGH ESC1 (`esc1-` in `service_detail`, `template_cn="BadTemplate-ESC1"`), 0 from `SafeTemplate`, 0 misconfig from `BadTemplate-ESC4` (D-80-R8 — surfaces only as coverage-gap), 4 LOW coverage-gap (`ESC4`/`ESC5`/`ESC7`/`ESC8`). Every emitted endpoint carries `protocol="ADCS"` and a populated `adcs_scan_json`.
- `test_bind_failure_emits_adcs_unreachable_no_propagation` (ADCS-04 SC#2) — patches `_bind_and_query` to raise a stand-in `LDAPBindError`; asserts exactly 1 LOW finding with `service_detail.startswith("adcs-unreachable|")` + `scan_error_category="exception"` + non-empty `scan_error`; no exception propagates.
- `test_safe_only_input_yields_just_coverage_gaps` — target with no CA cert and only `SafeTemplate` emits exactly 4 coverage-gap LOWs.

**ldap3 stub strategy:** the test injects a `SimpleNamespace` `ldap3` module (with `SUBTREE`, `ALL`, `SIMPLE`, `ANONYMOUS` constants and `core.exceptions.LDAPBindError` exception class) via `patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True)`. Necessary because `quirk/scanner/adcs_scanner.py` references `ldap3.SUBTREE` inside `scan_adcs_targets` (not just at import time) — `LDAP3_AVAILABLE=True` alone leaves `ldap3` unbound when the real module isn't installed in the test env.

### `tests/test_adcs_no_writes.py` (2 tests)

ADCS-09 runtime arm.

- `test_scanner_never_calls_ldap_write_methods` — runs a full scan against the chaos lab fixtures, then asserts the MagicMock connection's `.add`/`.modify`/`.delete`/`.modify_dn` were each `assert_not_called()`. Sanity-asserts the scan actually emitted findings to avoid vacuous pass.
- `test_scanner_never_instantiates_csr_builder` — `monkeypatch`'s `cryptography.x509.CertificateSigningRequestBuilder` with a sentinel that raises `AssertionError("ADCS-09 violation: ...")`. Runs a full scan. If any code path constructs a CSR builder (including future drift adding `if foo: CertificateSigningRequestBuilder(...)` behind a flag), the AssertionError surfaces and pytest fails. Catches dynamic / late-imported / `getattr`-obfuscated drift the AST gate would miss.

### `tests/test_adcs_ast_gate.py` (3 tests)

D-80-R4 AST CI gate. Forbidden sets:

- **`FORBIDDEN_IMPORT_MODULES = {"certipy", "certipy_ad", "impacket.ldap.ldapasn1_modify"}`** — plus any module name starting with `"certipy"` (catches `certipy.X` submodule imports).
- **`FORBIDDEN_FROM_NAMES = {("cryptography.x509", "CertificateSigningRequestBuilder")}`** — name-level check; catches the targeted CSR-builder import even when the parent module is otherwise allowed.
- **`FORBIDDEN_LDAP_METHODS = {"add", "modify", "delete", "modify_dn"}`** — detected on `ast.Call` nodes whose `.func` is an `ast.Attribute` (i.e., method-call sites). Avoids tripping on bare attribute reads.

Three tests: real-module gate over `quirk/scanner/adcs_scanner.py` (clean), positive self-test asserting synthetic source containing every forbidden shape produces ≥8 violations spanning all three categories, negative self-test asserting clean ldap3 read-only source produces zero violations.

### `tests/test_extras_install_matrix.py` (3 slow-marked tests)

ADCS-07. Helper `_resolved_packages(extras, tmp_path) -> dict[str, str]` runs `pip install --dry-run --ignore-installed --report` for `quirk[<extras>]`, parses the report JSON, returns `{name_lower: version}`. `_version_ge_44(ver)` does a strict `>=44` leading-component check (robust to `44.0`, `44.0.1`, `45.0b1`, etc.).

- `test_adcs_extras_resolves_ldap3_cryptography44_no_impacket` — `quirk[adcs]`: ldap3 present, cryptography>=44.0, impacket absent.
- `test_all_extras_resolves_cryptography44_no_impacket` — `quirk[all]`: cryptography>=44.0, impacket absent (Phase 45 / D-01 invariant preserved), ldap3 surfaces (proves `quirk[adcs]` is in `[all]`).
- `test_adcs_plus_identity_keeps_cryptography44_floor` — `quirk[adcs,identity]`: cryptography>=44.0 floor holds even with impacket allowed via `[identity]`. Canary for any future impacket release silently downgrading the pin.

### Fixtures

- `tests/fixtures/adcs/ca-weak.der` — 630-byte byte-identical copy of `quantum-chaos-enterprise-lab/adcs/certs/ca-weak.der` (RSA-1024, SHA-1 self-signed, 100-year validity, `CN=QUIRK-Lab-CA`). Single regen source per Phase 79 precedent.
- `tests/fixtures/adcs/templates.json` — 3 canned `searchResEntry` dicts matching the `raw_attributes`-keyed contract that `paged_search(generator=True)` yields. BadTemplate-ESC1 (`msPKI-Certificate-Name-Flag=1`, `msPKI-RA-Signature=0`, EKU=client-auth), BadTemplate-ESC4 (`msPKI-Certificate-Name-Flag=0`, `msPKI-RA-Signature=1`, `nTSecurityDescriptor=<bytes-sentinel>`), SafeTemplate (`msPKI-Enrollment-Flag=0`, EKU=email-protection only).

### Documentation / phase closure

- `docs/UAT-SERIES.md` — added 5 new rows (UAT-80-01 chaos lab e2e, UAT-80-02 read-only runtime invariant, UAT-80-03 AST gate, UAT-80-04 extras matrix, UAT-80-05 ADCS-UNREACH behavior). `**Last Updated:** 2026-05-16` prepended with the Phase 80 wrap clause.
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — synced from `docs/UAT-SERIES.md` via the printf+cat+cp pattern (file is too large for `obsidian CLI content=`).
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-80-Windows-AD-CS-Scanner.md` — Obsidian phase note created via the Write tool (NOT `obsidian CLI`); frontmatter `status: complete`, Goal verbatim from ROADMAP §Phase 80, all 9 ADCS-* requirements covered, 5 success criteria, per-plan "What Was Built" subsections, Notes (intentional red, coverage-gaps by design D-80-R8, schema-load branch D-80-R7, privacy/safety defence in depth), Related wikilinks.

## Verification Performed

- `python -m pytest tests/test_adcs_scanner.py tests/test_adcs_no_writes.py tests/test_adcs_ast_gate.py -x -v` → **8 passed** in 0.14s.
- `python -m pytest tests/test_extras_install_matrix.py -x -v -m slow` → **3 passed** in 12.22s.
- `python -m compileall quirk/ tests/ run_scan.py` → clean (compiled new test files; no syntax errors).
- Full-suite baseline check: ran `pytest tests/ --continue-on-collection-errors --ignore=tests/test_score_weights_invariant.py --deselect ...slow tests` BEFORE staging vs AFTER staging — 120 failures / 1506 passed pre-stage vs 120 failures / 1514 passed post-stage. **+8 new passing tests, zero new failures.** The 120 pre-existing failures + 31 collection errors are out of scope (Plan 80-02 SUMMARY already documents them) and unrelated to Phase 80 work.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking dep] `ldap3` not installed in the base CI Python env.**

- **Found during:** First run of `test_adcs_scanner.py`. The scanner's `try: import ldap3` falls through to `LDAP3_AVAILABLE=False`, so simply patching `LDAP3_AVAILABLE=True` is insufficient — `scan_adcs_targets` references `ldap3.SUBTREE` inside `paged_search` calls, and `ldap3` is unbound in the module namespace.
- **Fix:** Added a `_fake_ldap3_module()` helper that returns a `SimpleNamespace` carrying `SUBTREE`/`ALL`/`SIMPLE`/`ANONYMOUS` constants and `core.exceptions.LDAPBindError`; injected into the scanner via `patch.object(adcs_scanner, "ldap3", _fake_ldap3_module(), create=True)`. Mirrors the smime_scanner test's `LDAP3_AVAILABLE=True` patch but extended to cover the `ldap3` module reference itself.
- **Files modified:** `tests/test_adcs_scanner.py`, `tests/test_adcs_no_writes.py` (same fix applied for the runtime invariant tests).
- **Tracked:** No commit-level deviation — fix is local to the new test files.

### Out-of-scope Issues (deferred — NOT fixed)

- 31 collection errors + 120 test failures in `tests/test_dashboard_scan_history.py`, `tests/test_jobs_api.py`, `tests/test_qramm_*`, etc. → `ValueError: Multiple QU.I.R.K. DBs found ...`. These exist in baseline before Plan 80-04 changes (verified via `git stash` baseline comparison). Plan 80-02 SUMMARY already noted similar pre-existing failures. Out of scope per SCOPE BOUNDARY.

No architectural deviations (no Rule 4 events).

## Known Stubs

None.

## Threat Flags

None — Plan 80-04 introduces tests + docs only; no new attack surface.

## Known Red (Intentional)

`tests/test_score_weights_invariant.py` — sum drifted 261.0 → 275.0 over Phase 79+80 (count 29 → 36). Phase 83 CLEAN-01 owns the consolidated bump per D-80-R5. Do NOT touch.

## Commits

- **`a0f02ed`** — `feat(80-04): adcs unit tests + write-safety invariant + ast gate + extras matrix` — staged: `tests/test_adcs_scanner.py`, `tests/test_adcs_no_writes.py`, `tests/test_adcs_ast_gate.py`, `tests/test_extras_install_matrix.py`, `tests/fixtures/adcs/ca-weak.der`, `tests/fixtures/adcs/templates.json` (explicit paths; no `-A`). 6 files / 752 insertions.
- **`6e453b4`** — `docs(phase-80): update UAT-SERIES.md` — staged via `gsd-tools.cjs commit` with explicit `--files docs/UAT-SERIES.md`.

## Self-Check

- **Files created (FOUND):**
  - `tests/test_adcs_scanner.py` (203 LOC, 3 tests)
  - `tests/test_adcs_no_writes.py` (130 LOC, 2 tests)
  - `tests/test_adcs_ast_gate.py` (146 LOC, 3 tests)
  - `tests/test_extras_install_matrix.py` (147 LOC, 3 slow-marked tests)
  - `tests/fixtures/adcs/ca-weak.der` (630 bytes, byte-identical to chaos lab)
  - `tests/fixtures/adcs/templates.json` (3 entries)
  - `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-80-Windows-AD-CS-Scanner.md` (Obsidian phase note, status: complete)
- **Files modified (FOUND):**
  - `docs/UAT-SERIES.md` (UAT-80-01..05 appended; Last Updated bumped with Phase 80 wrap clause)
  - `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` (synced via printf+cat+cp)
- **Commits (FOUND in git log):** `a0f02ed`, `6e453b4`
- **Test counts:** 8 fast tests pass + 3 slow-marked tests pass = 11 new green
- **Expected red preserved:** `tests/test_score_weights_invariant.py` still red (Phase 83 owns)
- **No architectural deviations**

## Self-Check: PASSED
