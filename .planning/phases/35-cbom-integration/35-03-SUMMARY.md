---
phase: 35-cbom-integration
plan: 03
subsystem: cbom
type: execute
wave: 3
status: complete
tags: [cbom, golden-snapshot, motion, email, broker, fixtures, integration-test]
requires:
  - quirk/cbom/builder.py (Pass 2 + Pass 3 plaintext-broker skip from Plan 02)
  - tests/test_cbom_motion_endpoints.py (RED→GREEN contract from Plans 01/02)
provides:
  - tests/fixtures/cbom/expected_email_cbom.json
  - tests/fixtures/cbom/expected_broker_cbom.json
  - tests/fixtures/cbom/README.md
  - tests/test_cbom_motion_golden.py
affects: []
tech-stack:
  added: []
  patterns:
    - lab-driven-golden-snapshot
    - structural-not-byte-for-byte-diff
    - env-var-gated-regen
    - synthesized-endpoint-tests
key-files:
  created:
    - tests/fixtures/cbom/expected_email_cbom.json
    - tests/fixtures/cbom/expected_broker_cbom.json
    - tests/fixtures/cbom/README.md
    - tests/test_cbom_motion_golden.py
  modified: []
decisions:
  - D-04-applied: structural snapshot (bom_ref + asset_type + protocol + named cipher suites) — strip metadata.timestamp, serial_number, cert validity dates
  - regen path is REGEN_CBOM_FIXTURES=1 env-gated test (skipped by default) — no production code involvement
  - email lab: 7 endpoints / 6 distinct labels (SMTP-STARTTLS shared by ports 30025+30587)
  - broker lab: 6 endpoints / 3 TLS + 3 plaintext — plaintext rows carry None on cert + cipher fields to mirror real broker_scanner output
requirements-completed:
  - CBOM-01
  - CBOM-02
  - CBOM-03
  - CBOM-04
metrics:
  duration_seconds: 240
  completed: 2026-04-28
  tasks_completed: 1
  files_changed: 4
  tests_added: 9  # 1 regen (skipped) + 2 snapshot + 6 structural-invariant
---

# Phase 35 Plan 03: Lab-Driven Golden CBOM Verification Summary

Lab-driven golden CBOM verification (D-04) with two committed structural
JSON snapshots, a regeneration recipe, and an integration test asserting
CBOM-01..CBOM-04 invariants. Snapshots are built from hand-constructed
`CryptoEndpoint` lists that mirror `labs/email/expected_results.md` and
`labs/broker/expected_results.md` verbatim — same labels, same ports,
same cipher suites — so the suite runs without Docker while still anchored
to the real chaos-lab port maps.

## What Was Built

### `tests/test_cbom_motion_golden.py` (383 lines)

Single test module with three layers:

1. **Endpoint generators** — `_build_email_lab_endpoints()` returns 7 email
   endpoints (Postfix RSA-ARIA at TLS 1.2, Dovecot RSA-ChaCha at TLS 1.3);
   `_build_broker_lab_endpoints()` returns 3 TLS + 3 plaintext broker
   endpoints. Plaintext rows carry `None` for cert + cipher + tls_version
   to mirror the real `broker_scanner` shape.
2. **Normalizer** — `_normalize_bom_for_snapshot(bom)` strips volatile
   fields (timestamps, UUIDs, serial numbers, cert validity dates) and
   keeps `{bom_ref, name, type, asset_type, protocol_type, protocol_version,
   cipher_suite_names}` per component, sorted by `bom_ref`. Diff-stable
   across runs and minor `cyclonedx-python-lib` bumps.
3. **Tests** — 9 cases:
   - `test_generate_fixtures` (skipped unless `REGEN_CBOM_FIXTURES=1`)
   - `test_email_cbom_matches_snapshot` / `test_broker_cbom_matches_snapshot`
   - `test_email_snapshot_has_seven_protocol_components` (CBOM-01)
   - `test_broker_snapshot_has_three_tls_protocol_components` (CBOM-02)
   - `test_no_certificate_components_for_plaintext_brokers` (CBOM-03 — both
     live build + snapshot mirror)
   - `test_no_tls_protocol_components_for_plaintext_brokers` (CBOM-03)
   - `test_amqps_azure_servicebus_protocol_component_present` (D-03 — slash
     never escapes into bom_ref values)
   - `test_kafka_tls_rsa_cipher_decomposes_to_quantum_vulnerable` (CBOM-04)

### `tests/fixtures/cbom/expected_email_cbom.json` (198 lines)

Structural snapshot for the email lab — 7 TLS protocol components keyed
by `crypto/protocol/tls/localhost:{30025,30465,30587,30143,30993,30110,30995}`,
2 cert components (one per cert subject host), and the shared algorithm
registry (RSA-2048, AES-256-GCM, ChaCha20-Poly1305, SHA-384, etc.).

### `tests/fixtures/cbom/expected_broker_cbom.json` (105 lines)

Structural snapshot for the broker lab — exactly 3 TLS protocol components
(`localhost:25671`, `:26380`, `:29093`), 3 cert components (TLS rows only),
and zero refs containing `:29092`, `:25672`, or `:26379`. Locks the
plaintext-skip behavior from Plan 02 against future regression.

### `tests/fixtures/cbom/README.md` (56 lines)

Source of truth, snapshot scope (structural — not byte-for-byte),
regeneration command, and explicit "when not to regenerate" guidance.

## Test Evidence

```
$ python -m pytest tests/test_cbom_motion_golden.py \
                   tests/test_cbom_motion_endpoints.py \
                   tests/test_cbom_builder.py \
                   tests/test_cbom_classifier.py \
                   tests/test_cbom_writer.py \
                   tests/test_cbom_integration.py -v
======================== 101 passed, 1 skipped in 0.30s ========================
```

The 1 skipped test is `test_generate_fixtures` (gated by
`REGEN_CBOM_FIXTURES=1`), as designed.

### Acceptance criteria verification

| Criterion | Result |
|---|---|
| `expected_email_cbom.json` exists and is valid JSON | PASS |
| `expected_broker_cbom.json` exists and is valid JSON | PASS |
| Email snapshot contains exactly 7 `crypto/protocol/tls/...` refs | PASS (7) |
| Broker snapshot contains exactly 3 `crypto/protocol/tls/...` refs (TLS-only ports) | PASS (`:25671`, `:26380`, `:29093`) |
| Broker snapshot has zero `crypto/certificate/localhost:{29092,25672,26379}` refs | PASS |
| All assertion tests in `test_cbom_motion_golden.py` PASS | PASS (9/9, 1 skipped by env-var design) |
| No regressions in `test_cbom_motion_endpoints.py` / `test_cbom_builder.py` | PASS (19/19 + 28/28) |
| `tests/fixtures/cbom/README.md` references `REGEN_CBOM_FIXTURES` | PASS |
| `python -m compileall quirk tests` clean | PASS |

## Deviations from Plan

None - plan executed exactly as written.

The `<action>` block specified the exact helper names, the env-var-gated
regen path, and the 5+ assertion tests. Implementation followed verbatim;
the only minor planner-discretion choice was naming the load helper
`_load_snapshot(name)` (used by 4 tests) rather than inlining the
`json.loads(Path(...).read_text())` call, for readability.

**Total deviations:** 0. **Impact:** None — every fixture path, env-var
name, and assertion shape matches the plan body 1:1.

## Authentication Gates

None.

## Decisions Made

- **D-04 normalization scope:** kept `{bom_ref, name, type, asset_type,
  protocol_type, protocol_version, cipher_suite_names}` per component
  (sorted by `bom_ref`). Stripped `metadata.timestamp`, `serial_number`,
  `version`, cert validity dates. This is structural enough to catch
  builder layout changes (Pass-N skip-list rename, cipher decomposition
  drift, scanner label rename) but volatile-free — the snapshot does not
  drift on rerun.
- **Plaintext broker shape:** plaintext rows carry `None` on cert + cipher
  + tls_version, exactly as `broker_scanner.py` emits. This makes the
  Pass-2 falsy-cert guard AND the Pass-3 explicit skip-list both
  exercised in the same fixture — defense-in-depth from Plan 02 is
  validated end-to-end.
- **Two-layer assertions:** the snapshot tests guard the *output shape*
  (high-level diff); the structural-invariant tests guard the *behavior*
  (no plaintext leaks, AMQPS/Azure-ServiceBus slash-handling, RSA quantum
  classification). A regression in either layer fails loudly with a
  pointer to the regen recipe.

## Verification

- [x] `python -m compileall quirk tests` — clean (no syntax errors)
- [x] `python -m pytest tests/test_cbom_motion_golden.py -v` — **8 passed,
      1 skipped** (regen)
- [x] `python -m pytest tests/test_cbom_motion_golden.py tests/test_cbom_motion_endpoints.py tests/test_cbom_builder.py tests/test_cbom_classifier.py tests/test_cbom_writer.py tests/test_cbom_integration.py -v` — **101 passed, 1 skipped**
- [x] No production code modified (`quirk/cbom/builder.py`,
      `quirk/cbom/classifier.py` untouched)
- [x] `tests/fixtures/cbom/expected_email_cbom.json` valid JSON, 7 TLS proto refs
- [x] `tests/fixtures/cbom/expected_broker_cbom.json` valid JSON, 3 TLS proto refs, 0 plaintext leaks
- [x] `tests/fixtures/cbom/README.md` documents the `REGEN_CBOM_FIXTURES=1` recipe
- [x] Test file: 383 lines (>= 120 min_lines)

## Commits

- `7329e4b` — test(35-03): add lab-driven golden CBOM fixtures + structural test

## Self-Check: PASSED

Verified files:
- FOUND: tests/test_cbom_motion_golden.py
- FOUND: tests/fixtures/cbom/expected_email_cbom.json
- FOUND: tests/fixtures/cbom/expected_broker_cbom.json
- FOUND: tests/fixtures/cbom/README.md
- FOUND commit: 7329e4b

## Next

Ready for Plan 35-04 (final phase plan — REQUIREMENTS.md amendments per
D-01/D-02, UAT-SERIES.md updates per D-07, Obsidian phase-note finalization
per D-08).
