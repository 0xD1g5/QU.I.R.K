---
phase: 71-protocol-scanner-warnings
verified: 2026-05-15T00:00:00Z
status: passed
score: 19/19
overrides_applied: 0
---

# Phase 71: Protocol Scanner WARNINGs — Verification Report

**Phase Goal:** All five WARNING clusters in the protocol scanner subsystem are resolved — coverage percentages bounded, severity comparisons case-insensitive, subprocess errors logged not swallowed, nmap inputs validated and parsed safely, identity scanner inputs bounded, extras/ThreadPool/dedup issues fixed. Closes audit findings scanners-protocol/WR-01 through WR-14.

**Verified:** 2026-05-15
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement — Success Criteria

| # | ROADMAP Success Criterion | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | `calculate_coverage` returns `[0.0, 1.0]`; severity comparison case-insensitive | VERIFIED | `quirk/discovery/coverage.py:7` `return max(0.0, min(1.0, round(coverage, 2)))` + `:16` `str(f["severity"]).upper()`. `python -c "calculate_coverage(10,5,20)==1.0"` PASS. `python -c "calculate_coverage(-5,10,5)==0.0"` PASS. |
| 2 | Subprocess failures log not swallow; scan continues | VERIFIED | `_LOG.warning` confirmed at `quirk/scanner/ssh_scanner.py:39`, `container_scanner.py:98`, `source_scanner.py:75`. Each has `_LOG = logging.getLogger(__name__)` at module scope. Plan redirected from fingerprint.py to these three sites; redirect documented in audit row WR-03. |
| 3 | nmap extra_args allowlist + defusedxml + default port CSV | VERIFIED | `nmap_provider.py:14` `_SAFE_NMAP_ARG_RE`; `:95` `raise ValueError(f"Unsafe nmap extra arg...")`. `nmap_parser.py:6` `import defusedxml.ElementTree as ET`. Default ports include `5671, 9092, 88, 8443, 5001`. `_SAFE_NMAP_ARG_RE.match('-sV')` PASS; rejects `'; rm -rf /'`. |
| 4 | DNSSEC bound, Kerberos log+nonce, SAML JSON cap | VERIFIED | `dnssec_scanner.py:27` `_DNSKEY_MIN_BYTES` + `:117` `if len(key_bytes) < min_len`. `kerberos_scanner.py:18` `import secrets`, `:90` `secrets.randbits(31)` nonce, `:193` `logger.warning("KDC UDP probe decode failed...")`. `saml_scanner.py:36` `MAX_SAML_JSON_BYTES = 1_048_576` + `:128` gate before parse. |
| 5 | motion_concurrency, tls_scanner dup deleted, target_expander cap+dedup | VERIFIED | `ScanCfg().motion_concurrency == 50` PASS. `quirk/discovery/tls_scanner.py` does NOT exist. `target_expander.py:7` `_MAX_HOSTS_PER_CIDR = 1024`; `:41` `if net.num_addresses > _MAX_HOSTS_PER_CIDR` raises; `:71` `list(dict.fromkeys(targets))`; `:15` `str(ipaddress.ip_address(x))`. No `min(len(tasks), 50)` literals remain. |

**Score:** 5/5 ROADMAP success criteria VERIFIED

---

## Must-Have Truths (Rolled Up Across 5 Plans)

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 71-01 | `calculate_coverage` clamped to `[0.0, 1.0]` | VERIFIED | `coverage.py:7` clamp; python assertions pass |
| 2 | 71-01 | `quantum_readiness_score` severity case-insensitive | VERIFIED | `coverage.py:16` `.upper()` |
| 3 | 71-01 | WR-01 / WR-02 audit rows flipped to Phase 71 closed | VERIFIED | Ledger grep matches both rows |
| 4 | 71-02 | WR-03 bare-except subprocess swallow narrowed + logs | VERIFIED | 3 sites in ssh/container/source scanner; `_LOG.warning` on each. Plan-time target (fingerprint.py) corrected post-investigation per audit ledger row note. |
| 5 | 71-02 | Narrowed handler catches specific subprocess/OS exceptions | VERIFIED | Per ledger row: `(subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError, json.JSONDecodeError)` |
| 6 | 71-02 | WR-03 audit row flipped | VERIFIED | Ledger row reads `Phase 71 \| [x] closed` |
| 7 | 71-03 | nmap extra_args rejected via regex allowlist | VERIFIED | `_SAFE_NMAP_ARG_RE` + ValueError raise |
| 8 | 71-03 | nmap_parser uses defusedxml | VERIFIED | `import defusedxml.ElementTree as ET` |
| 9 | 71-03 | Default port CSV is consulting-grade union | VERIFIED | Fixed set `(22,25,80,88,389,465,587,636,993,995,3389,5671,8080,9092)` + ports_tls union |
| 10 | 71-03 | WR-04 / WR-05 / WR-06 audit rows flipped | VERIFIED | All three closed rows in ledger |
| 11 | 71-04 | DNSSEC `_parse_dnskeys` bounded by algorithm minimum | VERIFIED | `_DNSKEY_MIN_BYTES` constant + length check before subscript |
| 12 | 71-04 | Kerberos `_probe_kdc_udp` decode logs warning | VERIFIED | `logger.warning("KDC UDP probe decode failed...")` line 193 |
| 13 | 71-04 | Kerberos nonce via `secrets` | VERIFIED | `secrets.randbits(31)` at line 90 |
| 14 | 71-04 | SAML enforces 1 MiB JSON cap | VERIFIED | `MAX_SAML_JSON_BYTES = 1_048_576` + gate before json.loads |
| 15 | 71-04 | WR-07 / WR-08 / WR-09 / WR-10 audit rows flipped | VERIFIED | All four closed in ledger |
| 16 | 71-05 | Unified extras messaging across email/broker/container/source | VERIFIED | All 4 files contain `"is not installed — pip install 'quirk[...]'"` |
| 17 | 71-05 | `ScanCfg.motion_concurrency=50` field + wiring | VERIFIED | `ScanCfg().motion_concurrency == 50`; no `min(len(tasks), 50)` literals remain in email/broker |
| 18 | 71-05 | `quirk/discovery/tls_scanner.py` deleted | VERIFIED | File not present; `importlib.util.find_spec` returns None |
| 19 | 71-05 | `target_expander` stable dedup + /22 cap + IP normalization | VERIFIED | `_MAX_HOSTS_PER_CIDR=1024`, `dict.fromkeys`, `str(ipaddress.ip_address(x))` all present |

**Score:** 19/19 must-haves VERIFIED

---

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| PROTO-01 | Coverage clamp + severity case-insensitivity (WR-01, WR-02) | SATISFIED |
| PROTO-02 | Subprocess except narrowing + logging (WR-03) | SATISFIED |
| PROTO-03 | nmap default ports + extra_args allowlist + defusedxml (WR-04/05/06) | SATISFIED |
| PROTO-04 | DNSSEC bound + Kerberos log/nonce + SAML JSON cap (WR-07/08/09/10) | SATISFIED |
| PROTO-05 | Unified extras + motion_concurrency + tls dup delete + expander (WR-11/12/13/14) | SATISFIED |

---

## Audit Ledger Closure

```
grep -cE "scanners-protocol/WR-(0[1-9]|1[0-4]).*Phase 71.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md
```

**Result: 14** — all WR-01..WR-14 rows flipped to `Phase 71 | [x] closed` with rationale references to plans 71-01..71-05 and locked decisions D-01..D-15.

---

## Behavioral Spot-Checks

| # | Behavior | Command | Result | Status |
|---|----------|---------|--------|--------|
| 1 | Coverage clamps high | `python -c "from quirk.discovery.coverage import calculate_coverage; assert calculate_coverage(10,5,20)==1.0"` | exit 0 | PASS |
| 2 | Coverage clamps low | `python -c "...calculate_coverage(-5,10,5)==0.0"` | exit 0 | PASS |
| 3 | nmap arg allowlist | `python -c "from quirk.discovery.nmap_provider import _SAFE_NMAP_ARG_RE; assert _SAFE_NMAP_ARG_RE.match('-sV'); assert not _SAFE_NMAP_ARG_RE.match('; rm -rf /')"` | exit 0 | PASS |
| 4 | motion_concurrency default | `python -c "from quirk.config import ScanCfg; assert ScanCfg(concurrency=10, ports_tls=[443]).motion_concurrency==50"` | exit 0 | PASS |
| 5 | tls dup deleted | `python -c "import importlib.util; assert importlib.util.find_spec('quirk.discovery.tls_scanner') is None"` | exit 0 | PASS |
| 6 | Full quirk/ compile | `python -m compileall quirk/ -q` | exit 0 | PASS |

---

## Phase 71 Test Suite

```
pytest tests/test_coverage_bounds.py tests/test_subprocess_logging.py \
       tests/test_nmap_hardening.py tests/test_identity_scanner_hardening.py \
       tests/test_extras_concurrency_expander.py
```

**Result:** `60 passed, 2 skipped in 0.22s`

Breakdown:
- `test_coverage_bounds.py` — coverage clamp + severity case tests
- `test_subprocess_logging.py` — 3 subprocess-logging tests (timeout / FileNotFoundError / JSONDecodeError)
- `test_nmap_hardening.py` — allowlist + defusedxml + port CSV (incl. XXE block)
- `test_identity_scanner_hardening.py` — DNSSEC bound / Kerberos / SAML cap
- `test_extras_concurrency_expander.py` — extras messaging + motion_concurrency + expander cap/dedup/normalize

Pre-existing failures in unrelated `quirk.intelligence.scoring` modules are out of scope per 71-01 SUMMARY (deferred to a future INTEL-* phase per D-15) and do not gate this verification.

---

## Anti-Patterns / Notable Observations

| File | Observation | Severity | Disposition |
|------|-------------|----------|-------------|
| `quirk/scanner/fingerprint.py` | 7 bare-except sites remain | Info | Intentional per D-08 / D-15 — only the WR-03 site was in scope, and post-investigation that site was actually in ssh/container/source scanners (not fingerprint.py). Audit ledger row WR-03 documents the redirect. To be revisited if a future WARNING re-flags fingerprint.py. |

No BLOCKER-grade or WARNING-grade anti-patterns introduced by this phase. No `TBD` / `FIXME` / `XXX` markers added in modified files.

---

## Plan↔Implementation Divergence (Disclosed)

**71-02 / WR-03 site relocation:** Plan 71-02 frontmatter lists `quirk/scanner/fingerprint.py` as the file modified. During execution, investigation determined the bare-`except Exception` subprocess swallow flagged by WR-03 actually lives in three scanner modules (`ssh_scanner.py::_run_ssh_audit`, `container_scanner.py::scan_container_image`, `source_scanner.py::scan_source_repo`), not in `fingerprint.py`. The fix landed at the correct sites, and the audit ledger row for WR-03 explicitly documents this redirect with full per-file attribution. This is an intentional plan correction during execution and does not affect goal achievement — the bare-except subprocess swallow IS narrowed and logged, which is what WR-03 required.

---

## Gaps Summary

None. All 19 must-haves verified; all 5 ROADMAP success criteria green; all 14 audit ledger rows flipped; all 5 Phase 71 pytest modules pass (60 passed, 2 skipped); `python -m compileall quirk/` exits clean.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
