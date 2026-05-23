---
phase: 96
slug: active-rest-fuzzing
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-23
---

# Phase 96 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, root pytest.ini) |
| **Config file** | `pytest.ini` (root) |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_rest_fuzzer_gate.py tests/test_rest_fuzzer_probes.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~60 seconds (quick) / several minutes (full) |

Wave 0 dependency: `.venv/bin/pip install -e ".[api]"` installs schemathesis + transitive
hypothesis (Plan 01 Task 1). Until installed, rest_fuzzer probe tests cannot import schemathesis.

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds (quick)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 96-01-01 | 01 | 1 | FUZZ-02 (PKG guard) | T-96-SC | schemathesis resolvable in [api], absent from [all] | unit | `.venv/bin/python -m pytest tests/test_install_all_excludes_schemathesis.py -x -q` | ✅ (extend) | ⬜ pending |
| 96-01-02 | 01 | 1 | FUZZ-03 | T-96-01 | Non-TTY hard-abort: mocked session.request.call_count == 0 | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_gate.py::test_non_tty_hard_abort_zero_requests -x -q` | ❌ W0 | ⬜ pending |
| 96-01-02 | 01 | 1 | FUZZ-03 | T-96-03 | TTY gate requires literal "CONFIRM"; other input aborts | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_gate.py::test_confirm_required_exact_string -x -q` | ❌ W0 | ⬜ pending |
| 96-01-02 | 01 | 1 | FUZZ-02 | T-96-02 | Budget > 500 raises ValueError; default 50; cannot bypass | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_gate.py::test_budget_hard_ceiling -x -q` | ❌ W0 | ⬜ pending |
| 96-02-01 | 02 | 2 | FUZZ-01 | — | as_transport_kwargs dict unpacked into session.request; GET-only | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py::test_dispatch_uses_as_transport_kwargs -x -q` | ❌ W0 | ⬜ pending |
| 96-02-01 | 02 | 2 | FUZZ-02 | T-96-04 | Out-of-scope URL rejected; budget not consumed | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py::test_scope_gate_rejects_does_not_consume_budget -x -q` | ❌ W0 | ⬜ pending |
| 96-02-01 | 02 | 2 | FUZZ-02 | T-96-05 | Budget caps dispatch; TokenBucket acquired; 3x5xx pauses | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py -x -q -k "budget or rate or cascade"` | ❌ W0 | ⬜ pending |
| 96-02-01 | 02 | 2 | FUZZ-01 | T-96-06 | HSTS/TLS probes emit HIGH REST_FUZZ findings | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py -x -q -k "hsts or tls"` | ❌ W0 | ⬜ pending |
| 96-02-02 | 02 | 2 | FUZZ-04 | T-96-07 | RS256→HS256 forge returns bytes; non-RS256 → None | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py -x -q -k "alg_confusion or forge"` | ❌ W0 | ⬜ pending |
| 96-02-02 | 02 | 2 | FUZZ-04 | T-96-08 | No public key → INFO probe_skipped, no forged request; no jku follow | unit | `.venv/bin/python -m pytest tests/test_rest_fuzzer_probes.py::test_alg_confusion_no_public_key_skips_info -x -q` | ❌ W0 | ⬜ pending |
| 96-03-01 | 03 | 3 | FUZZ-01/02/03 | T-96-09 | --fuzz / --fuzz-jwt-alg-confusion / --fuzz-budget flags + single CONFIRM prompt | smoke | `.venv/bin/python run_scan.py --help \| grep -E -- "--fuzz-jwt-alg-confusion\|--fuzz-budget\|--fuzz"` | ✅ (modify) | ⬜ pending |
| 96-03-02 | 03 | 3 | SCORE-01 | T-96-10 | SCORE_WEIGHTS sum 303.0 AND count 41 (both invariants) | unit | `.venv/bin/python -m pytest tests/test_score_weights_invariant.py -x -q` | ✅ (update) | ⬜ pending |
| 96-04-01 | 04 | 3 | LAB-01 | T-96-11 | fuzz-target compose profile + weak service (no HSTS) | smoke | `cd quantum-chaos-enterprise-lab && grep -q 'fuzz-target' docker-compose.yml && python -m compileall fuzz-target/main.py` | ❌ W0 | ⬜ pending |
| 96-04-02 | 04 | 3 | LAB-01 | T-96-12 | Oracle + README document fuzz-target | smoke | `cd quantum-chaos-enterprise-lab && grep -q '## Profile: fuzz-target' expected_results_v4.md && grep -q 'fuzz-target' README.md` | ❌ W0 | ⬜ pending |
| 96-05-01 | 05 | 4 | FUZZ-01..04 | T-96-14 | docs document flags, guardrails, non-TTY abort, fuzz-target | smoke | `grep -q -- '--fuzz-jwt-alg-confusion' docs/configuration.md && grep -q 'fuzz-target' docs/chaos-lab.md` | ✅ (modify) | ⬜ pending |
| 96-05-02 | 05 | 4 | LAB-01/SCORE-01 | T-96-SC | UAT-96 series + vault sync + Phase-96 note | smoke | `grep -q "UAT Series 96" docs/UAT-SERIES.md && test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-96-Active-REST-Fuzzing.md"` | ✅ (modify) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `.venv/bin/pip install -e ".[api]"` — installs schemathesis + hypothesis (Plan 01 Task 1)
- [ ] `tests/test_rest_fuzzer_gate.py` — gate + budget unit tests, zero-requests assertion (Plan 01 Task 2, test-first)
- [ ] `quirk/scanner/rest_fuzzer.py` — module stub with confirm_fuzz_gate + _resolve_budget + constants (Plan 01 Task 2)
- [ ] `tests/test_rest_fuzzer_probes.py` — dispatch-integration + probe + alg-confusion tests (Plan 02)

The CONFIRM gate + non-TTY hard-abort tests (96-01-02) are written and passing BEFORE any
request-dispatch code exists (Plan 02), per the CONTEXT.md test-first mandate.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live fuzz run against the fuzz-target chaos lab profile produces >= 2 crypto-posture findings (incl. CRITICAL alg-confusion) | FUZZ-01/04, LAB-01 | Requires Docker + running lab service on port 20100 and an interactive TTY to type CONFIRM | `PROFILE_ARGS="--profile fuzz-target" ./lab.sh up`; then `quirk scan --targets http://localhost:20100 --fuzz --fuzz-jwt-alg-confusion --openapi-spec http://localhost:20100/openapi.json --allow-internal-targets` (run from repo root); type CONFIRM at the prompt; expect HSTS-missing + http-creds + alg-confusion findings |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s (quick)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-23
