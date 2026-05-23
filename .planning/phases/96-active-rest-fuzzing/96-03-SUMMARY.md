---
phase: 96-active-rest-fuzzing
plan: "03"
subsystem: cli + cbom/builder + intelligence/evidence + intelligence/scoring + tests
tags: [rest-fuzzer, cli-flags, cbom-skip, evidence-counter, score-weights, fuzz-01, fuzz-02, fuzz-03, fuzz-04, score-01]
dependency_graph:
  requires: [phase-96-01-gate-layer, phase-96-02-fuzzer-core, phase-94-openapi-scanner, phase-93-ephemeral-creds]
  provides: [--fuzz cli flag, --fuzz-jwt-alg-confusion cli flag, --fuzz-budget cli flag, REST_FUZZ evidence counter, agility_fuzz_crypto_posture_ratio weight, SCORE_WEIGHTS 303.0/41]
  affects: [run_scan.py, quirk/cbom/builder.py, quirk/intelligence/evidence.py, quirk/intelligence/scoring.py, tests/test_score_weights_invariant.py, tests/test_cbom_rest_fuzz_no_tls_component.py]
tech_stack:
  added: []
  patterns: [argparse flags after --inventory-code-signing, _wrapped_phase scan phase, CODE_SIGNING analog for evidence/scoring, dual-invariant sum+count update]
key_files:
  created:
    - tests/test_cbom_rest_fuzz_no_tls_component.py
  modified:
    - run_scan.py
    - quirk/cbom/builder.py
    - quirk/intelligence/evidence.py
    - quirk/intelligence/scoring.py
    - tests/test_score_weights_invariant.py
decisions:
  - "Single gate call: run_fuzz_scan owns confirm_fuzz_gate internally; CLI passes prompt_fn=input + is_tty=sys.stdin.isatty() so user is prompted EXACTLY ONCE (T-96-09 double-prompt resolution)"
  - "spec_dict for fuzz phase re-parsed from cfg.scan.openapi_spec_path via _load_spec_bytes_from_file + _parse_spec_dict (already security-validated by openapi phase)"
  - "base_url derived from cfg.targets.fqdns[0] with https:// prefix; defaults to https://localhost when no fqdns configured"
  - "REST_FUZZ added to BOTH Pass-2 and Pass-3 skip tuples in builder.py to prevent phantom crypto/protocol/tls/* CBOM components"
  - "INFO probe_skipped severity excluded from fuzz_finding_count (T-96-10 score drift prevention)"
  - "SCORE_WEIGHTS sum AND count invariants updated together (299.0->303.0, 40->41) — recurring lesson from Phase 94/95"
metrics:
  duration: "22 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 6
  commits: 2
---

# Phase 96 Plan 03: CLI flags + CBOM skip + evidence/scoring pipeline Summary

--fuzz / --fuzz-jwt-alg-confusion / --fuzz-budget CLI flags with single CONFIRM gate, REST_FUZZ CBOM phantom-component skip, evidence counter for CRITICAL/HIGH fuzz findings feeding agility_signals, and SCORE_WEIGHTS final step 299.0→303.0 / 40→41.

## What Was Built

### Task 1: CLI flags + gated fuzz scan phase in run_scan.py

Three argparse flags added after the `--inventory-code-signing` block:

- `--fuzz` (store_true) — enable active REST crypto-posture fuzzing; references FUZZ-01/02/03
- `--fuzz-jwt-alg-confusion` (store_true) — enable JWT RS256→HS256 alg-confusion probe (FUZZ-04)
- `--fuzz-budget N` (int, default=50) — max requests, hard max 500 (FUZZ-02)

**Missing-extra advisory:** When `--fuzz` is set but `schemathesis` [api] extra is absent, `_emit_missing_extra_advisory("rest_fuzzer", "api", error_endpoints)` is called at startup (after `probe_missing_extras`).

**`_run_fuzz_phase()` gated phase:**

1. Guards: `args.fuzz` must be True, `openapi_endpoints` must be non-empty, `cfg.scan.openapi_spec_path` must be set
2. Derives `base_url` from `cfg.targets.fqdns[0]` (https:// prefix; defaults to `https://localhost`)
3. Re-parses spec via `_load_spec_bytes_from_file` + `_parse_spec_dict` from `openapi_scanner` (spec already security-validated by the openapi phase above)
4. Calls `run_fuzz_scan(spec_dict, base_url, cfg, cred_ctx, budget, prompt_fn=input, is_tty=sys.stdin.isatty(), run_alg_confusion=...)`

**Single CONFIRM gate (T-96-09):** The CLI does NOT call `confirm_fuzz_gate` itself — `run_fuzz_scan` owns the single gate call internally. The CLI passes `prompt_fn=input` and `is_tty=sys.stdin.isatty()` through, so the user is prompted exactly once.

**fuzz_endpoints** are included in the post-phase flush and checkpoint endpoint_count.

**Acceptance verified:**
- `--help` lists `--fuzz`, `--fuzz-jwt-alg-confusion`, `--fuzz-budget N`
- `--fuzz-budget` default is 50
- `python -m compileall run_scan.py` exits 0

### Task 2: REST_FUZZ CBOM skip + evidence counter + agility weight + invariant 303.0/41

**`quirk/cbom/builder.py` — dual skip:**

- **Pass-2** (~line 679): Added `"REST_FUZZ"` to the certificate-component skip tuple (alongside `"CODE_SIGNING"`). Prevents REST_FUZZ endpoints from emitting phantom `cert_bom_ref = f"crypto/certificate/{host}:{port}"` components when they have no X.509 cert metadata.
- **Pass-3** (~line 875): Added `"REST_FUZZ"` to the ProtocolProperties skip tuple. Prevents REST_FUZZ endpoints from falling through to the TLS `else` clause and emitting `crypto/protocol/tls/{host}:{port}` CBOM components.

**`quirk/intelligence/evidence.py`:**

- Added `"REST_FUZZ"` to `_PROTOCOL_KEYS` tuple (after `"CODE_SIGNING"`)
- Added `fuzz_finding_count = 0` counter (near `codesign_weak_algo_count`)
- Added `elif proto == "REST_FUZZ":` branch: increments `fuzz_finding_count` when `severity.upper() in ("CRITICAL", "HIGH")` — INFO `probe_skipped` rows are excluded (T-96-10)
- Added output dict entries `"fuzz_finding_count"` and `"agility_fuzz_crypto_posture_ratio"`

**`quirk/intelligence/scoring.py`:**

- Added `"agility_fuzz_crypto_posture_ratio": 4.0` to `SCORE_WEIGHTS` after the Phase 95 entry
- Appended agility impact tuple: `("Active REST fuzz crypto-posture findings", -_ratio(fuzz_findings, denom) * w["agility_fuzz_crypto_posture_ratio"])` following the Phase 95 codesign append

**`tests/test_score_weights_invariant.py`:**

- Updated sum assertion `299.0 → 303.0` AND count `40 → 41` in the same change
- Added Phase 96 docstring notes recording the `+4.0 / +1` delta for `agility_fuzz_crypto_posture_ratio`

**`tests/test_cbom_rest_fuzz_no_tls_component.py` (new):**

Four tests asserting zero `crypto/protocol/tls/*` CBOM components for REST_FUZZ endpoints with CRITICAL, HIGH, INFO severity, and mixed REST_FUZZ + TLS scenarios.

**Acceptance verified:**
- `grep -c '"REST_FUZZ"' quirk/intelligence/evidence.py` → 2 (in `_PROTOCOL_KEYS` + elif branch)
- `agility_fuzz_crypto_posture_ratio` in SCORE_WEIGHTS == 4.0
- `sum(SCORE_WEIGHTS.values()) == 303.0`, `len(SCORE_WEIGHTS) == 41`
- `"REST_FUZZ"` in both Pass-2 (line 682) and Pass-3 (line 881) skip tuples
- `pytest tests/test_score_weights_invariant.py` → 2 passed
- `pytest tests/test_cbom_rest_fuzz_no_tls_component.py` → 4 passed
- `python -m compileall quirk/cbom/builder.py quirk/intelligence/evidence.py quirk/intelligence/scoring.py` exits 0

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is wired. The fuzz phase returns `[]` when `--fuzz` is absent or no spec is provided (correct guard behavior, not a stub).

## Threat Flags

None — no new network endpoints or auth paths beyond what is covered in the plan's threat model (T-96-09, T-96-10, T-96-SC).

## Self-Check: PASSED

- `run_scan.py`: FOUND (--fuzz, --fuzz-jwt-alg-confusion, --fuzz-budget, _run_fuzz_phase)
- `quirk/cbom/builder.py`: FOUND (REST_FUZZ in both Pass-2 and Pass-3 skip tuples)
- `quirk/intelligence/evidence.py`: FOUND (REST_FUZZ in _PROTOCOL_KEYS, fuzz_finding_count, agility_fuzz_crypto_posture_ratio)
- `quirk/intelligence/scoring.py`: FOUND (agility_fuzz_crypto_posture_ratio=4.0, agility impact append)
- `tests/test_score_weights_invariant.py`: FOUND (303.0, 41)
- `tests/test_cbom_rest_fuzz_no_tls_component.py`: FOUND (4 tests)
- Commit 98a4b60 (Task 1 CLI): FOUND
- Commit c9f49b2 (Task 2 CBOM/evidence/scoring): FOUND
- test_score_weights_invariant.py: 2 passed
- test_cbom_rest_fuzz_no_tls_component.py: 4 passed
- compileall exits 0: CONFIRMED
