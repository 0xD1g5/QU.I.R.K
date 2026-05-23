---
phase: 96-active-rest-fuzzing
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - quirk/scanner/rest_fuzzer.py
  - run_scan.py
  - quirk/cbom/builder.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
findings:
  critical: 2
  warning: 6
  info: 3
  total: 11
status: issues_found
---

# Phase 96: Code Review Report

**Reviewed:** 2026-05-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the active REST fuzzing implementation — the milestone's sharpest edge (opt-in
outbound traffic). The CONFIRM gate, non-TTY hard abort, exact-literal matching, single
prompt point, scope-gate-before-dispatch, rate limiter, and 5xx cascade pause are all
correctly implemented and well covered by tests. The CBOM skip tuples (REST_FUZZ in both
Pass-2 and Pass-3) and the SCORE_WEIGHTS sum (verified 303.0 / count 41 via `.venv/bin/python`)
are correct, and the invariant test matches.

However, two BLOCKER-class defects undermine the budget hard-ceiling — the single most
important DoS guardrail. The alg-confusion forged-token request and the per-iteration TLS
socket probes both dispatch real network traffic **without consuming budget**, so the
"hard maximum 500" ceiling does not bound the actual number of connections the tool opens.
With `--fuzz-jwt-alg-confusion` plus an HTTPS target, a budget of N can produce up to ~3N
outbound connections. Additional warnings cover the alg-confusion request bypassing the
5xx cascade tracker, the unguarded `_secret_buf` access, and a stale doc comment.

## Critical Issues

### CR-01: Alg-confusion forged-token request bypasses the budget ceiling

**File:** `quirk/scanner/rest_fuzzer.py:636-670`
**Issue:** The normal dispatch increments `budget_used += 1` (line 560), but the
alg-confusion probe block (lines 637-670) issues a second `session.request(**alg_kwargs)`
(line 656) for the SAME loop iteration and **never increments `budget_used`**. Because this
block runs on every iteration where a forged token is available, a run with `--fuzz-budget N`
and `--fuzz-jwt-alg-confusion` against an RS256 target dispatches up to `2N` requests, not `N`.
The module docstring (line 20) and FUZZ-02 spec promise the budget counter bounds dispatched
requests; this path defeats the "hard maximum 500" guarantee that is the core DoS guardrail.
The budget check at line 528 (`if budget_used >= effective_budget: break`) only gates the
top of the loop, so the extra alg-confusion requests are entirely uncounted.
**Fix:**
```python
# Inside the alg-confusion block, before/after dispatch, gate and count it:
if budget_used >= effective_budget:
    break  # do not exceed the ceiling with alg-confusion traffic
limiter.acquire()
try:
    alg_resp = session.request(**alg_kwargs)
    budget_used += 1  # alg-confusion request consumes budget too
    ...
```

### CR-02: Per-iteration TLS downgrade and weak-cipher socket probes are uncounted and unbounded

**File:** `quirk/scanner/rest_fuzzer.py:593-621`
**Issue:** For every HTTPS endpoint iteration, `_probe_tls_downgrade` (up to 2 socket
connections, lines 210-227) and `_probe_cipher_weak` (1 socket connection, lines 253-258)
open raw TLS sockets to `host:port`. These run once per loop iteration, are not gated by the
rate limiter (`limiter.acquire()` only covers the HTTP `session.request`), and do not
increment `budget_used`. Against an HTTPS target with budget N, this opens up to `3N` extra
TCP/TLS connections to the same host beyond the counted HTTP requests — all outside the DoS
guardrails. Worse, they re-probe the identical `host:port` on every iteration, so identical
"tls_downgrade_accepted" / "cipher_weak" findings are appended N times (finding duplication),
inflating `fuzz_finding_count` and the agility ratio. The probes are host/port-scoped, not
URL-scoped, so they gain nothing from per-endpoint repetition.
**Fix:** Hoist the TLS/cipher socket probes out of the per-operation loop and run them once
per unique `host:port` before/after the dispatch loop. Subject each socket connection to
`limiter.acquire()` and count it against the budget (or document a separate, bounded socket
budget). Deduplicate the resulting findings.

## Warnings

### WR-01: Alg-confusion request does not update the 5xx cascade tracker

**File:** `quirk/scanner/rest_fuzzer.py:654-670`
**Issue:** The 5xx cascade pause (the "stop hammering a struggling server" guardrail) only
inspects `resp_status` from the main dispatch (lines 570-578). The alg-confusion request's
response status is never fed into `consecutive_5xx`. A server returning 5xx to forged-token
requests will keep receiving them, defeating the cascade protection on that traffic path.
**Fix:** After the alg-confusion `session.request`, apply the same `if alg_status >= 500: consecutive_5xx += 1 ... break` logic, or fold both request paths through a shared dispatch helper that updates the cascade counter.

### WR-02: Unguarded `_secret_buf` access can raise on malformed credentials

**File:** `quirk/scanner/rest_fuzzer.py:504`
**Issue:** `alg_confusion_bearer = cred_ctx._secret_buf.decode("utf-8")` reaches into a
private field and assumes valid UTF-8. If the bearer secret holds non-UTF-8 bytes, this
raises `UnicodeDecodeError`. It is outside the `try` at line 522, so it propagates uncaught
out of `run_fuzz_scan` (not even captured by the broad handler at 672) and aborts the whole
fuzz phase. `CredentialContext` exposes `auth_headers()`/`bearer_declared_alg()` as the public
API; reaching into `_secret_buf` couples the fuzzer to private internals.
**Fix:** Wrap the decode in try/except (returning/skipping alg-confusion on failure), or add a
public accessor on `CredentialContext` (e.g. `bearer_token()`), and prefer it over `_secret_buf`.

### WR-03: 5xx cascade counter reset on request exception masks a struggling server

**File:** `quirk/scanner/rest_fuzzer.py:561-564`
**Issue:** When `session.request` raises (timeout, connection error), the handler sets
`consecutive_5xx = 0` (line 563). A server that is failing hard — alternating 500s and
connection resets/timeouts — never reaches 3 *consecutive* 5xx because each exception resets
the counter, so the cascade pause never fires despite the server clearly being in distress.
Connection-level failures are at least as strong a "back off" signal as 5xx.
**Fix:** Treat request exceptions as part of the cascade signal (increment a failure counter
rather than resetting), or maintain a combined `consecutive_failures` counter covering both
5xx and exceptions.

### WR-04: `case.as_strategy().example()` may raise per operation, silently losing all subsequent endpoints

**File:** `quirk/scanner/rest_fuzzer.py:535-537`
**Issue:** `op.as_strategy().example()` and `case.as_transport_kwargs(...)` are inside the
loop but there is no per-operation try/except. A single operation whose schema makes
Hypothesis fail to generate an example raises, which is caught only by the function-level
`except Exception` at line 672 — terminating the **entire** loop and dropping every
not-yet-processed operation. One pathological spec path silently kills coverage of all others.
**Fix:** Wrap the per-operation strategy/example/kwargs construction in try/except and
`continue` on failure so one bad operation does not abort the scan.

### WR-05: HTTP-only credential probe emits a finding even when the credential was never sent

**File:** `quirk/scanner/rest_fuzzer.py:626-634`
**Issue:** The `http_creds` HIGH finding fires whenever the URL is `http://` and a `cred_ctx`
is present — regardless of whether credentials are actually attached to the dispatched
request. `as_transport_kwargs` does not inject the QUIRK credential, so the finding asserts
"credentials sent over plaintext" on the basis of mere configuration, not observed behavior.
This can produce false-positive HIGH findings that inflate `fuzz_finding_count` and the
score impact. Also note this finding is appended once per matching iteration with no
host/port dedup (same duplication concern as CR-02).
**Fix:** Only emit `http_creds` when a credential is genuinely placed on the outgoing request
(inspect `kwargs["headers"]`/auth), or downgrade/reword to reflect it is a spec-declared
plaintext endpoint rather than confirmed credential exposure. Deduplicate per host:port.

### WR-06: `target_count` shown in the CONFIRM prompt understates real request volume

**File:** `quirk/scanner/rest_fuzzer.py:458, 168-172`
**Issue:** The prompt tells the operator "up to {budget} active requests to {target_count}
endpoint(s)", where `target_count = len(spec_dict["paths"])`. Given CR-01/CR-02, the actual
outbound connection count can be ~3x the displayed budget, and the gate's stated request
ceiling is not what the code enforces. For a safety-critical informed-consent gate, the
displayed figure must match reality.
**Fix:** After fixing CR-01/CR-02 so all dispatched requests count against `budget`, the
prompt is accurate. Until then, the prompt overstates the safety guarantee.

## Info

### IN-01: Stale SCORE_WEIGHTS sum in module doc comment

**File:** `quirk/intelligence/scoring.py:8`
**Issue:** The comment reads "Their sum is 275.0 BY DESIGN (Phase 83 rebalance)." The actual
sum is 303.0 (count 41), verified via `.venv/bin/python`. The invariant test correctly asserts
303.0, but the inline doc is stale and misleads future contributors.
**Fix:** Update the comment to "Their sum is 303.0 BY DESIGN" and append the Phase 90/94/95/96
deltas (matching the changelog already present in `test_score_weights_invariant.py`).

### IN-02: Misleading test docstring/comment claims `.strip()` is applied

**File:** `tests/test_rest_fuzzer_gate.py:90, 98`
**Issue:** The parametrize comment for `"CONFIRM "` says "strip() is done on answer, not
partial" and the test docstring says "after .strip()", but `confirm_fuzz_gate` deliberately
does NOT strip (rest_fuzzer.py:165-173, `answer == "CONFIRM"`). The test passes only because
`"CONFIRM " != "CONFIRM"`. The comment describes behavior opposite to the implementation and
will mislead anyone reasoning about the gate.
**Fix:** Correct the comment/docstring to state that NO strip is performed and trailing/leading
whitespace is rejected by exact equality.

### IN-03: `base_url` localhost fallback can silently fuzz the wrong host

**File:** `run_scan.py:1449`
**Issue:** `_base_url = f"https://{_fqdns[0]}" if _fqdns else "https://localhost"`. If `--fuzz`
is enabled with an OpenAPI spec but no FQDN target configured, the fuzzer defaults to
`https://localhost`. Combined with `--allow-internal-targets`, this could send active fuzz
traffic to a local service the operator never named. The scope gate still applies, but the
silent localhost default is surprising for an active-traffic feature.
**Fix:** When no FQDN is available for a `--fuzz` run, abort with a clear error ("--fuzz
requires an explicit FQDN target") rather than silently defaulting to localhost.

---

_Reviewed: 2026-05-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
