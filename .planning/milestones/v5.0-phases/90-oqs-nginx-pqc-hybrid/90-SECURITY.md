---
phase: 90
phase_name: oqs-nginx-pqc-hybrid
type: security
status: secured
asvs_level: 1
block_on: high
threats_total: 9
threats_closed: 9
threats_open: 0
register_authored_at_plan_time: true
audited: 2026-05-22
---

# Phase 90 — Security Threat Verification

**Audit date:** 2026-05-22
**ASVS Level:** 1 · **Block on:** high
**Auditor disposition:** SECURED — all 9 threats CLOSED (register authored at plan time; verify-mitigations mode)

## Accepted Risks Log

The following threats were explicitly accepted at plan time. Recording them here satisfies the `accept` disposition requirement.

| Threat ID | Category | Accepted Risk | Rationale |
|-----------|----------|---------------|-----------|
| T-90-02 | Information Disclosure | Loopback-bound chaos-lab port (oqs-nginx on 127.0.0.1:39444) reachable without authentication | Lab is a local chaos sandbox; loopback bind is the existing lab-wide isolation control. Live scans require explicit `--allow-internal-targets` opt-in, placing responsibility on the operator. No production data is exposed. |
| T-90-08 | Information Disclosure | Demo scan output in `expected_results_v4.md` and `docs/UAT-SERIES.md` documents local lab target oracle numbers | Documents a loopback lab target only (127.0.0.1:39444). No production data, credentials, or private key material appears in the oracle. |
| T-90-SC (Plans 01–04) | Tampering / Supply Chain | No new pip/npm/cargo packages introduced | v5.0 stabilization principle. PQC probe uses system `openssl` binary plus stdlib `subprocess` only. No `[ASSUMED]` or `[SUS]` packages. |

## Threat Verification Record

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-90-01 | Tampering / Supply Chain | mitigate | CLOSED | `quantum-chaos-enterprise-lab/docker-compose.yml:1232` — image line is `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870`; no `:latest` tag present |
| T-90-02 | Information Disclosure | accept | CLOSED | Recorded in accepted risks log above |
| T-90-03 | Tampering / Elevation | mitigate | CLOSED | `quirk/scanner/pqc_probe.py:116-132` — `cmd` is a Python list literal; both `subprocess.run` calls use `shell=False` explicitly (lines 64, 131); host validated by `_validate_host()` at line 102 (empty + shell metachar rejection via `_SHELL_METACHAR_RE` at line 31); port coerced via `int(port)` at line 106 |
| T-90-04 | Denial of Service | mitigate | CLOSED | `quirk/scanner/pqc_probe.py:124-148` — `subprocess.run(..., timeout=timeout, ...)` with default `timeout=8`; `stdin=subprocess.DEVNULL`; `except subprocess.TimeoutExpired` at line 136 catches the hung-handshake case and returns `detected=False` without re-raising |
| T-90-05 | Repudiation / Info Accuracy | mitigate | CLOSED | `quirk/scanner/pqc_probe.py:49-71` (`host_supports_mlkem` capability gate) + `run_scan.py:1117-1165` (`_run_pqc_phase`): line 1142 branches on `not capability_ok`; advisory path at lines 1147-1164 sets `protocol="ADVISORY"`, `scan_error_category="coverage_gap"`, and includes the human-readable message "PQC-hybrid detection requires host OpenSSL >= 3.5 / OQS-compiled tooling" — a non-detection is never silently scored as full detection |
| T-90-06 | Tampering | mitigate | CLOSED | `quirk/intelligence/scoring.py:210` — `pqc_hybrid_count = max(0, _as_int(evidence.get("pqc_hybrid_endpoint_count", 0)))` — non-int coerced by `_as_int`, negative clamped by `max(0, ...)`, missing key defaults to `0`; no exception path |
| T-90-07 | Elevation (score inflation) | mitigate | CLOSED | `quirk/intelligence/scoring.py:58` — `"agility_pqc_hybrid_bonus": 8.0` is a single entry appended to `agility_impacts` at line 221; `_apply_weighted_impacts(score_cap=25.0)` at line 223 enforces the /25 ceiling; `tests/test_score_weights_invariant.py:22,36` asserts `sum == 283.0` and `len == 37` — forward-locks the weight set |
| T-90-08 | Information Disclosure | accept | CLOSED | Recorded in accepted risks log above |
| T-90-09 | Repudiation | mitigate | CLOSED | `tests/test_pqc_discriminator.py` (248 lines, 9 tests) — negative arm (mocked classical output → `detected=False`) always runs; positive live arm skips cleanly when lab profile is down; human-verified live run documented in `90-04-SUMMARY.md` with actual agility values (PQC=25, classical=17) |
| T-90-SC (Plans 01–04) | Tampering / Supply Chain | accept | CLOSED | Recorded in accepted risks log above; verified: no new entries in `requirements.txt` or `package.json` introduced by Phase 90 |

## Unregistered Flags

None. No threat flags were raised in any of the four SUMMARY.md `## Threat Surface Scan` sections that lack a mapping to the threat register.

## Audit Trail

| Date | Event |
|------|-------|
| 2026-05-22 | Initial verification (State B, from PLAN threat models + SUMMARY flags). gsd-security-auditor in verify-mitigations mode. 9/9 CLOSED, 0 open. ASVS L1, block on high → SECURED. |
