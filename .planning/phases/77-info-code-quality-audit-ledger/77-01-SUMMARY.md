---
phase: 77-info-code-quality-audit-ledger
plan: 01
subsystem: scanners-protocol
tags: [INFO-01, IN-01, IN-02, IN-03, IN-04, IN-05, IN-06, weak_crypto, migration_advisor, ipaddress, dnssec, saml, kerberos, fingerprint, tls_capabilities]
one_liner: "Closed INFO-01 (scanners-protocol/IN-01..06) — TLS probe rationale comment, DNSSEC Reserved alg 9/11, SAML SHA1 word-boundary, fingerprint Host header, weak_crypto helper consolidation, kerberos ipaddress refactor. Row flips deferred to PLAN 77-05."
requires:
  - .planning/phases/73-intel-cipher-classifier-debt/  # quirk.util.weak_crypto module home
  - .planning/phases/74-warning-code-quality/          # quirk.assessment.migration_advisor._matches helper
requirements: [INFO-01]
provides:
  - quirk/util/weak_crypto.py::is_pfs_cipher (D-05)
  - quirk/util/weak_crypto.py::is_weak_cipher_classification (D-05)
  - quirk/scanner/dnssec_scanner.py::DNSSEC_ALG_MAP[9] = ("Reserved", "HIGH") (D-02)
  - quirk/scanner/dnssec_scanner.py::DNSSEC_ALG_MAP[11] = ("Reserved", "HIGH") (D-02)
affects:
  - quirk/scanner/broker_scanner.py    # D-05 dedup, now imports from weak_crypto
  - quirk/scanner/email_scanner.py     # D-05 dedup, now imports from weak_crypto
  - quirk/scanner/tls_scanner.py       # D-05 dedup, now imports from weak_crypto
  - quirk/scanner/saml_scanner.py      # D-03 SHA1 detection now word-boundary via _matches
  - quirk/scanner/fingerprint.py       # D-04 Host header uses target hostname
  - quirk/scanner/kerberos_scanner.py  # D-06 ipaddress-based IPv4/IPv6 detection
  - quirk/scanner/tls_capabilities.py  # D-01 probe-rationale comment
  - quirk/scanner/dnssec_scanner.py    # D-02 Reserved alg map entries
  - quirk/util/weak_crypto.py          # D-05 new public helpers
tech_stack:
  added: []
  patterns: [word-boundary-regex, ipaddress-stdlib-strict-parser, public-helper-consolidation]
key_files:
  created:
    - tests/test_tls_capabilities_comment.py
    - tests/test_dnssec_scanner_reserved_algs.py
    - tests/test_saml_scanner_sha1_word_boundary.py
    - tests/test_fingerprint_host_header.py
    - tests/test_weak_crypto_pfs_weak_helpers.py
    - tests/test_kerberos_scanner_realm_ipaddress.py
    - .planning/phases/77-info-code-quality-audit-ledger/deferred-items.md
    - .planning/phases/77-info-code-quality-audit-ledger/77-01-SUMMARY.md
  modified:
    - quirk/scanner/tls_capabilities.py
    - quirk/scanner/dnssec_scanner.py
    - quirk/scanner/saml_scanner.py
    - quirk/scanner/fingerprint.py
    - quirk/scanner/kerberos_scanner.py
    - quirk/scanner/broker_scanner.py
    - quirk/scanner/email_scanner.py
    - quirk/scanner/tls_scanner.py
    - quirk/util/weak_crypto.py
    - tests/test_dnssec_scanner.py
decisions:
  - "D-01 / IN-01: 3-line `# WHY:` comment block immediately above _try_handshake body (line ~52) — phrase `legacy-server posture` plus citation `closes scanners-protocol/IN-01`. (Cite for 77-05: tls_capabilities.py:52-55.)"
  - "D-02 / IN-02: DNSSEC_ALG_MAP gained `9: ('Reserved', 'HIGH')` and `11: ('Reserved', 'HIGH')` per IANA / RFC 8624. RESEARCH C-9 adjudication applied — CONTEXT identification of alg 9 as RSASHA1-NSEC3-SHA1 was incorrect (that's alg 7, already present). Existing DNSSEC-02 coverage test broadened from 12→14 expected keys. (Cite for 77-05: dnssec_scanner.py:51, 53.)"
  - "D-03 / IN-03: SAML _is_sha1_uri delegates to `quirk.assessment.migration_advisor._matches('SHA1', uri)` — Phase 74 word-boundary helper. CANONICAL_ALG_SYNONYMS['SHA1'] covers both `SHA1` and `SHA-1` synonyms. `SHA1024` no longer mis-detected. (Cite for 77-05: saml_scanner.py imports _matches at line 43, _is_sha1_uri body at line ~190.)"
  - "D-04 / IN-04: fingerprint._http_probe_plain HTTP/1.0 request now sends `Host: {host}` (target hostname) instead of literal `Host: localhost`. Encoded ASCII-safe via .encode('ascii', errors='replace'). (Cite for 77-05: fingerprint.py:111-117.)"
  - "D-05 / IN-05: Two new public helpers in `quirk/util/weak_crypto.py` — `is_pfs_cipher` (ECDHE/DHE token detection) and `is_weak_cipher_classification` (RC4/3DES/CBC3/NULL/EXPORT/MD5 6-token set). Local `_is_pfs` / `_is_weak` deleted from broker_scanner.py (was at 115/120), email_scanner.py (was at 103/108), tls_scanner.py (was at 248/254). All 6 call sites rerouted. RESEARCH D-05 home decision (weak_crypto.py, Phase 73) honored. (Cite for 77-05: weak_crypto.py:72-105.)"
  - "D-06 / IN-06: kerberos_scanner._derive_realm replaced `len(parts)==4 and all(p.isdigit())` heuristic with `ipaddress.ip_address(stripped)` strict parser inside try/except ValueError (RESEARCH Pattern 4). Now correctly classifies IPv6 (`::1`) and rejects all-numeric non-IP labels. (Cite for 77-05: kerberos_scanner.py:18, 51-71.)"
metrics:
  duration_seconds: 410
  completed_date: "2026-05-15"
  source_files_modified: 9
  test_files_created: 6
  tests_added: 21
  scanner_callsites_rerouted: 6
  audit_row_flips: 0  # deferred to PLAN 77-05 (LEDGER-01 consolidator)
---

# Phase 77 Plan 01: INFO-01 — Protocol Scanner INFOs Summary

## One-Liner

Closed six protocol-scanner INFO findings (scanners-protocol/IN-01..06) via
surgical edits: a probe-rationale comment, two DNSSEC Reserved algorithm
entries, a word-boundary SHA1 check, a target-hostname Host header, a
centralized PFS/weak cipher helper pair (Phase 73 weak_crypto extension),
and an ipaddress-based IPv4/IPv6 detector. No new pip deps. 21 tests added
RED→GREEN. Audit-row flips deferred to PLAN 77-05.

## What Changed

### D-01 — `quirk/scanner/tls_capabilities.py::_try_handshake` (IN-01)

Inserted a 3-line `# WHY:` comment block between the docstring and the first
statement of `_try_handshake`. Phrase `legacy-server posture` makes the
probe rationale grep-able; cites audit row `scanners-protocol/IN-01`.
RESEARCH C-8 adjudication applied: there is no single "downgrade site" — the
function probes deprecated TLS bands as inventory.

### D-02 — `quirk/scanner/dnssec_scanner.py::DNSSEC_ALG_MAP` (IN-02)

Added `9: ("Reserved", "HIGH")` and `11: ("Reserved", "HIGH")` per IANA DNS
Security Algorithm Numbers registry / RFC 8624. RESEARCH C-9 adjudication
applied: CONTEXT D-02 had mis-identified alg 9 as RSASHA1-NSEC3-SHA1 (that's
alg 7, already present). The map now covers the Reserved range that previously
fell through to UNKNOWN classification — defense-in-depth restored. Existing
DNSSEC-02 coverage test updated from 12→14 expected keys.

### D-03 — `quirk/scanner/saml_scanner.py::_is_sha1_uri` (IN-03)

Replaced `any(ind in uri.lower() for ind in SHA1_INDICATORS)` substring scan
with `_matches('SHA1', uri)` — the Phase 74 word-boundary regex helper. The
helper's `CANONICAL_ALG_SYNONYMS['SHA1'] = {'SHA1', 'SHA-1'}` covers both
spellings, and `\b` boundary rejection eliminates the `SHA1024`/`SHA1_INTERNAL`
false-positive class. RESEARCH D-03 Discretion path taken (`_matches` over
`is_weak_cipher`).

### D-04 — `quirk/scanner/fingerprint.py::_http_probe_plain` (IN-04)

Replaced hard-coded `Host: localhost` in the HTTP/1.0 request with
`Host: {host}` substituted from the function's own `host` parameter. Encoded
ASCII-safe. Mock-socket test asserts both presence of `Host: example.org`
and absence of `Host: localhost`.

### D-05 — `quirk/util/weak_crypto.py` + 3 scanner refactors (IN-05)

Added two module-level public helpers next to the existing Phase 73 surface:

- `is_pfs_cipher(cipher)` — ECDHE / DHE token detection
- `is_weak_cipher_classification(cipher)` — 6-token weak set (RC4, 3DES,
  CBC3, NULL, EXPORT, MD5). Kept distinct from `is_weak_cipher` (broader
  intelligence-layer surface) per docstring guard.

Deleted local `_is_pfs` / `_is_weak` inner/outer functions from:
- `quirk/scanner/broker_scanner.py` (was at lines 115, 120)
- `quirk/scanner/email_scanner.py` (was at lines 103, 108)
- `quirk/scanner/tls_scanner.py` (was at lines 248, 254 — inner)

All 6 call sites rerouted to the centralized helpers. Cipher-classification
semantics preserved exactly (same 6-token set, same uppercase substring check
for the weak helper; same `ECDHE`/`DHE` presence for the PFS helper).

### D-06 — `quirk/scanner/kerberos_scanner.py::_derive_realm` (IN-06)

Replaced the dotted-quad `len(parts)==4 and all(p.isdigit())` heuristic with
RESEARCH Pattern 4:

```python
try:
    ipaddress.ip_address(stripped)
    return stripped.upper()
except ValueError:
    pass
```

Strict stdlib parser. Now correctly classifies IPv6 literals (e.g. `::1`) and
rejects all-numeric non-IP tokens (`1.2.3` falls through to the
last-two-labels branch). `import ipaddress` added at module top.

## Citations for PLAN 77-05 (audit-row flips)

| Audit row | Decision | Code citation |
| --- | --- | --- |
| `scanners-protocol/IN-01` | D-01 | `quirk/scanner/tls_capabilities.py:52-55` (3-line `# WHY:` block) |
| `scanners-protocol/IN-02` | D-02 | `quirk/scanner/dnssec_scanner.py:51, 53` (`9:` + `11:` Reserved entries) |
| `scanners-protocol/IN-03` | D-03 | `quirk/scanner/saml_scanner.py:43` (import `_matches`) + `_is_sha1_uri` body |
| `scanners-protocol/IN-04` | D-04 | `quirk/scanner/fingerprint.py:111-117` (`Host: {host}` substitution) |
| `scanners-protocol/IN-05` | D-05 | `quirk/util/weak_crypto.py:72-105` (helpers); imports in `broker_scanner.py`, `email_scanner.py`, `tls_scanner.py` |
| `scanners-protocol/IN-06` | D-06 | `quirk/scanner/kerberos_scanner.py:18` (import) + `:51-71` (try/except body) |

## RESEARCH Adjudications Applied

- **C-8** (D-01 site is `_try_handshake`, not a "downgrade site"): comment
  placed above function body at line ~52, phrase `legacy-server posture`
  baked into the rationale.
- **C-9** (D-02 alg numbers wrong per IANA): plan-text retained the CONTEXT
  wording but the actual code change matches IANA (entries 9 and 11 as
  `Reserved`). Existing DNSSEC-02 test broadened 12→14.
- **D-03 Discretion / A5**: chose Phase 74 `_matches` over Phase 73
  `is_weak_cipher` because the substring-vs-word-boundary axis is exactly
  what `_matches` solves; `is_weak_cipher` would have re-introduced the
  substring bug.
- **D-05 Discretion**: chose `quirk/util/weak_crypto.py` (Phase 73) as the
  consolidation home over a new `tls_cipher_classify.py`, matching
  RESEARCH recommendation.
- **Pattern 4** (D-06): adopted the canonical `ipaddress.ip_address` strict
  try/except form verbatim.

## Verification

- `python -m compileall quirk/scanner quirk/util` → exit 0
- `pytest tests/test_tls_capabilities_comment.py tests/test_dnssec_scanner_reserved_algs.py tests/test_saml_scanner_sha1_word_boundary.py tests/test_fingerprint_host_header.py tests/test_weak_crypto_pfs_weak_helpers.py tests/test_kerberos_scanner_realm_ipaddress.py` → 21 passed
- Regression band (broker_kafka, broker_redis, email_scanner, email_findings, tls_scanner_chain_verified, saml_scanner, fingerprint_socket_cleanup, kerberos_scanner, dnssec_scanner) → 134 passed, 2 skipped, 3 deselected
- No new pip dependency introduced (D-32 honored)
- 0 audit row flips (consolidated by PLAN 77-05 per plan design)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Tracked file `tls_capabilities.py` had mixed CRLF/LF line endings; an
intermediate normalization to pure CRLF produced a 141-line diff masking the
3-line change.**
- **Found during:** Task 2 staging
- **Issue:** Initial Edit operations converted CRLF lines to LF, then a
  whole-file normalization to pure CRLF re-touched every line.
- **Fix:** Reset the file to HEAD, then applied the D-01 comment insertion
  via a byte-level surgical `replace` that preserved the original mixed
  line endings exactly. Final staged diff is the intended 3 inserted lines.
- **Files modified:** `quirk/scanner/tls_capabilities.py`
- **Commit:** `e4e176b`

### Regression-sweep adjustments

**2. [Rule 1 — Test data] `tests/test_dnssec_scanner.py::test_algorithm_map_has_all_twelve_entries`
expected exactly 12 keys; D-02 added 2 more.**
- **Found during:** Task 3 regression sweep
- **Issue:** Pre-existing coverage test enumerated `{1,3,5,6,7,8,10,12,13,14,15,16}`;
  the D-02 fix legitimately added `9, 11` to the map.
- **Fix:** Broadened the expected set to 14 keys including Reserved 9/11.
  Test name kept (compatibility); docstring annotated with Phase 77 D-02
  context.
- **Files modified:** `tests/test_dnssec_scanner.py`
- **Commit:** `fdf1666`

## Deferred Issues

See `.planning/phases/77-info-code-quality-audit-ledger/deferred-items.md`:

- `tests/test_broker_scanner_rabbitmq.py` — 2 pre-existing failures
  (`KeyError: rabbitmq_version`), confirmed via `git stash` to NOT be
  caused by INFO-01 changes.
- `tests/test_tls_scanner_resource_cleanup.py` — 2 pre-existing failures
  (`AttributeError: SslyzeScanner`), confirmed pre-existing.

## Commits

| Commit | Title |
| --- | --- |
| `db20755` | `test(77-01): add failing tests for INFO-01 (D-01..D-06)` |
| `e4e176b` | `feat(77-01): close INFO-01 (D-01..D-06) — protocol scanner INFOs` |
| `fdf1666` | `fix(77-01): update test_algorithm_map_has_all_twelve_entries to include Reserved 9/11` |

## Self-Check: PASSED

- File `quirk/util/weak_crypto.py` contains `def is_pfs_cipher` → FOUND
- File `quirk/util/weak_crypto.py` contains `def is_weak_cipher_classification` → FOUND
- File `quirk/scanner/dnssec_scanner.py` contains `9:` `Reserved` → FOUND
- File `quirk/scanner/dnssec_scanner.py` contains `11:` `Reserved` → FOUND
- File `quirk/scanner/tls_capabilities.py` contains `legacy-server posture` → FOUND
- File `quirk/scanner/saml_scanner.py` contains `from quirk.assessment.migration_advisor import _matches` → FOUND
- File `quirk/scanner/fingerprint.py` contains `Host: {host}` → FOUND, `Host: localhost` → ABSENT
- File `quirk/scanner/kerberos_scanner.py` contains `ipaddress.ip_address` → FOUND
- Commit `db20755` → FOUND in git log
- Commit `e4e176b` → FOUND in git log
- Commit `fdf1666` → FOUND in git log
