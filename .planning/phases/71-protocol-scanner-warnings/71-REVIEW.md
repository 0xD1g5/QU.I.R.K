---
phase: 71
status: clean
reviewed: 2026-05-15
fixed-on: 2026-05-15
depth: standard
files_reviewed: 12
files_reviewed_list:
  - quirk/discovery/coverage.py
  - quirk/discovery/nmap_parser.py
  - quirk/discovery/nmap_provider.py
  - quirk/scanner/broker_scanner.py
  - quirk/scanner/container_scanner.py
  - quirk/scanner/dnssec_scanner.py
  - quirk/scanner/email_scanner.py
  - quirk/scanner/kerberos_scanner.py
  - quirk/scanner/saml_scanner.py
  - quirk/scanner/source_scanner.py
  - quirk/scanner/ssh_scanner.py
  - quirk/scanner/target_expander.py
finding_counts:
  critical: 0
  warning: 3
  info: 4
---

# Phase 71: Code Review Report

**Reviewed:** 2026-05-15
**Depth:** standard
**Files Reviewed:** 12 (one deletion verified: `quirk/discovery/tls_scanner.py`)
**Status:** findings

## Summary

The audit-driven fixes mostly land cleanly. `nmap_parser.py` defusedxml swap is complete (no
stdlib `xml.etree` slipping through). The `target_expander.py` rewrite correctly enforces the
/22 cap BEFORE enumeration. `motion_concurrency` plumbing is wired end-to-end including
`run_scan.py:1478/1516/1527` (the cited integration point was actually updated). DNSSEC
`_DNSKEY_MIN_BYTES` table is well-formed and the bounds check fires before any subscript.
Kerberos UDP except chain is appropriately narrowed and `secrets.randbits(31)` replaces
the prior weak RNG.

Three real defects warrant fixing before sign-off:

1. **WR-1 (Warning)** — `_SAFE_NMAP_ARG_RE` uses `re.match` with a trailing `$` anchor; Python
   `$` matches before a trailing `\n`, so tokens like `"--script=foo\n"` pass the allowlist.
2. **WR-2 (Warning)** — `coverage.py::calculate_coverage` clamps to `[0.0, 1.0]` AFTER
   multiplying by 100, collapsing every non-zero coverage (1% – 100%) to exactly `1.0`. This
   is a regression in semantics, not a clamp.
3. **WR-3 (Warning)** — `kerberos_scanner.py::_build_as_req` nonce is only 31 bits
   (`secrets.randbits(31)`). D-09 calls for 32 bits; 31 leaves the high bit always zero and
   halves the nonce space. The CONTEXT comment says "ASN.1 INTEGER ... mask to 31 bits to
   preserve the pre-Phase-71 wire-format range" — that's a self-imposed constraint not
   documented in D-09 and worth a justification or a fix to 32.

The remaining items are info-level: dead `subprocess.CalledProcessError` arms in three narrowed
except tuples (subprocess.run is not invoked with `check=True`), a minor logger-name
inconsistency (`_LOG` vs `logger`) which is acknowledged in CONTEXT, and a couple of
`Exception:` catch-alls in `kerberos_scanner.py` that survived narrowing (out of D-08 scope, so
flagged as info rather than warning).

## Warnings

### WR-1: `_SAFE_NMAP_ARG_RE` allowlist permits trailing newline

**File:** `quirk/discovery/nmap_provider.py:14, 93–95`
**Evidence:**
```python
_SAFE_NMAP_ARG_RE = re.compile(r"^[A-Za-z0-9._:/=,-]+$")
...
if not _SAFE_NMAP_ARG_RE.match(token):
    raise ValueError(f"Unsafe nmap extra arg: {token!r}")
```
**Issue:** Python's `$` in default (non-MULTILINE) mode matches the position before a final
`\n`. Confirmed empirically:
```
>>> re.compile(r"^[A-Za-z0-9._:/=,-]+$").match("abc\n")
<re.Match object; span=(0, 3), match='abc'>   # truthy
```
A token like `"--script=foo\n"` passes the guard. Because the subprocess uses argv (not shell),
this cannot inject a new command, but it (a) defeats the no-whitespace intent of the allowlist
and (b) lets a malformed argument reach nmap with a trailing newline. The Phase 70
`_SAFE_COL_TYPE_RE` pattern this is modeled on uses `fullmatch` for exactly this reason.
**Fix:**
```python
if not _SAFE_NMAP_ARG_RE.fullmatch(token):
    raise ValueError(f"Unsafe nmap extra arg: {token!r}")
```
or swap anchors to `r"\A[A-Za-z0-9._:/=,-]+\Z"`. Add a regression test for `"foo\n"` and
`"foo\r"`.

### WR-2: Coverage clamp collapses 1–100 to 1.0 (semantic regression)

**File:** `quirk/discovery/coverage.py:5–7`
**Evidence:**
```python
coverage = (tls_endpoints / target_count) * 100
# Clamp per audit WR-01 (Phase 71): never report >100% or negative coverage.
return max(0.0, min(1.0, round(coverage, 2)))
```
**Issue:** `coverage` is on a 0–100 scale (note the `* 100`) but the clamp ceiling is `1.0`.
For any input where `tls_endpoints >= 1` and `target_count >= 1`, the return is exactly `1.0`.
The audit row WR-01 calls for "never report >100% or negative" — the previous-untouched math
was percent-scale, so the correct clamp window is `[0.0, 100.0]`, not `[0.0, 1.0]`. D-15
explicitly says "the `*100` percent math is intentionally untouched" — so the clamp is what's
mis-coded, not the formula. This silently breaks any consumer (CBOM coverage subscore,
dashboard widget) that reads this value.
**Fix:**
```python
return max(0.0, min(100.0, round(coverage, 2)))
```
Add tests asserting `calculate_coverage(10, _, 1) == 10.0` and `calculate_coverage(10, _, 11) == 100.0`
to prove the clamp window matches the percent scale. If the intent was actually to return a
0.0–1.0 fraction, then the `* 100` must go AND every downstream consumer must be audited —
that's a Phase 73 INTEL-03 task per D-15 and out of scope here.

### WR-3: Kerberos AS-REQ nonce only 31 bits, contradicting D-09

**File:** `quirk/scanner/kerberos_scanner.py:87–90`
**Evidence:**
```python
# Cryptographic RNG per audit WR-09 (Phase 71): unpredictable 31-bit nonce
# defeats replay-attack precomputation. ASN.1 INTEGER field accepts uint32; we
# mask to 31 bits to preserve the pre-Phase-71 wire-format range.
req_body['nonce'] = secrets.randbits(31)
```
**Issue:** D-09 (locked) prescribes "32-bit nonce" via `secrets.token_bytes(4)` or
`secrets.randbits(32)`. The implementation uses `randbits(31)`, halving the nonce space and
deviating from the locked decision without a CONTEXT amendment. The justification "ASN.1
INTEGER accepts uint32; we mask to 31 bits" conflates ASN.1 INTEGER (which is signed in DER —
hence the historical 31-bit clamp to avoid leading-byte sign issues) with the actual Kerberos
nonce field, which RFC 4120 §5.4.1 specifies as a 32-bit unsigned integer. The DER signed-int
quirk is handled by the pyasn1 encoder via leading-zero byte expansion when the high bit is
set, not by the caller.
**Fix:** Either
```python
req_body['nonce'] = secrets.randbits(32)
```
(canonical) or, if a real wire-format constraint is identified, amend the Phase 71 CONTEXT
with a new D-09a decision documenting it. As-is, the comment is inaccurate and the deviation
from D-09 is unreviewed.

## Info

### IN-1: Dead `subprocess.CalledProcessError` arms in narrowed except tuples

**Files:**
- `quirk/scanner/container_scanner.py:91–97`
- `quirk/scanner/source_scanner.py:68–74`
- `quirk/scanner/ssh_scanner.py:32–38`

**Issue:** All three narrowed except tuples include `subprocess.CalledProcessError`, but the
corresponding `subprocess.run(...)` calls do not pass `check=True`. Without `check=True`,
`subprocess.run` never raises `CalledProcessError`. The exception arm is unreachable.
**Fix:** Drop `subprocess.CalledProcessError` from the tuple, OR set `check=True` if the
intent is to treat non-zero exit as failure (probably not — current code paths parse
stdout regardless). Recommend just dropping the unreachable type.

### IN-2: Logger naming inconsistency (`_LOG` vs `logger`)

**Files:** `container_scanner.py`, `source_scanner.py`, `ssh_scanner.py` use `_LOG = logging.getLogger(__name__)`;
`kerberos_scanner.py`, `dnssec_scanner.py`, `saml_scanner.py` use `logger = ...`. CONTEXT
identifies the project precedent (`logger = ...`, lower-case) at
`quirk/dashboard/api/routes/scan.py:46`.
**Issue:** Mixed naming. Not a bug; this is a style preference but matters for grep-ability.
**Fix:** Pick one convention. Recommend `logger` (project precedent). Defer to a future
sweep if not worth churning these files now.

### IN-3: `kerberos_scanner.py` retains two `except Exception:` arms outside Phase 71 scope

**File:** `quirk/scanner/kerberos_scanner.py:245, 277, 282`
**Issue:** `_probe_ldap_anon` (line 245), the TCP probe wrapper (line 277), and the UDP
fallback wrapper (line 282) still use `except Exception:`. CONTEXT D-08 explicitly scopes
narrowing to WR-03/08/10, so these are correctly *out of scope* for Phase 71 — flagged here
only so they're not forgotten in the Phase 75 (api-cli-core WARNINGs) backlog.

### IN-4: `target_expander.py` exclude-set hostname pathway is silently inconsistent

**File:** `quirk/scanner/target_expander.py:25–31, 56–61`
**Issue:** When `exclude_ips` contains a non-IP string (hostname-like), the code stores
`str(x)` in the exclude set. When `include_ips` contains the same hostname-like string, it
also stores `str(x)`. So a string-vs-string exclude works. But a `cfg.targets.fqdns` entry
(loop at line 34) is NEVER cross-checked against `exclude_set`. So if an operator puts
`"example.com"` in both `fqdns` and `exclude_ips`, the FQDN still scans. Probably WAI per
WR-14's framing (which is about IP type confusion), but worth documenting in the docstring
that exclude only filters expanded CIDR/IP outputs.
**Fix (optional, not required by Phase 71 scope):** Either add the FQDN cross-check or add a
docstring note: `exclude_ips only filters IP-typed targets; use a separate exclude_fqdns to
exclude hostnames`.

---

## Cross-Cutting Notes

- **Out-of-scope leakage:** None detected. No edits to `quirk/scanner/tls_scanner.py`
  (correctly preserved per D-15). No coverage formula numerator/denominator changes (D-15).
- **defusedxml switch completeness:** `nmap_parser.py` imports `defusedxml.ElementTree as ET`
  only; no residual stdlib `xml.etree.ElementTree` import. The `saml_scanner.py` already used
  defusedxml via a separate code path; no change there.
- **Deletion verified:** `quirk/discovery/tls_scanner.py` is gone; the two surviving
  references in tests (`test_credential_leakage.py:25`, `test_extras_concurrency_expander.py:91`)
  are intentional regression guards, not stale imports.
- **SAML byte cap ordering:** `MAX_SAML_JSON_BYTES` check at `saml_scanner.py:128` runs
  BEFORE `json.loads`, correctly bounding parse-time memory. The bytes-vs-str branching is
  defensive (handles both inputs).
- **DNSSEC bounds:** `_DNSKEY_MIN_BYTES` table is checked before any subscript and uses
  `< min_len` (correct — not `<=`, which would reject exactly-min keys). Algorithm-specific
  floors match RFC 6605 §4 / RFC 8080 §3.

---

_Reviewed: 2026-05-15_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---
fixed-on: 2026-05-15

## Fixes Applied

All three Warning findings were fixed on 2026-05-15. Status flipped to `clean`.

- **WR-1 — fullmatch anchor for nmap extra_args validation**
  - Commit: `3e662d5`
  - Files: `quirk/discovery/nmap_provider.py`, `tests/test_nmap_hardening.py`
  - Switched `_SAFE_NMAP_ARG_RE.match(token)` → `.fullmatch(token)` so a
    trailing `\n` can no longer slip past the allowlist. Added a regression
    test for `extra_args=["abc\n-O"]`.

- **WR-2 — coverage clamp corrected to percent scale [0.0, 100.0]**
  - Commit: `1da7ef8`
  - Files: `quirk/discovery/coverage.py`, `tests/test_coverage_bounds.py`,
    `.planning/phases/71-protocol-scanner-warnings/71-CONTEXT.md` (new D-06a),
    `.planning/ROADMAP.md` (Phase 71 success criterion 1).
  - Original `min(1.0, ...)` collapsed every non-zero coverage to `1.0`.
    Spec corrected via new D-06a decision; clamp matches the percent
    semantic D-15 preserves.

- **WR-3 — Kerberos AS-REQ nonce widened to 32 bits per D-09**
  - Commit: `9840862`
  - File: `quirk/scanner/kerberos_scanner.py`
  - Replaced `secrets.randbits(31)` with `secrets.randbits(32)` and rewrote
    the misleading "ASN.1 signed-int" comment to cite RFC 4120 §5.4.1
    directly. D-09 already mandates 32 bits; no CONTEXT amendment needed.

Post-fix verification gate (all green):
- `python -m compileall quirk/` → exit 0
- `pytest tests/test_coverage_bounds.py tests/test_nmap_hardening.py tests/test_subprocess_logging.py tests/test_extras_concurrency_expander.py -x` → 56 passed
- `pytest tests/test_kerberos_scanner.py` → 24 passed, 1 deselected
