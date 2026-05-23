# Phase 97: v5.1 Tech-Debt Cleanup - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Correct the v5.1 carry-over design-judgment items so the codebase entering the
v5.2 reporting milestone is sound. Two requirements:

- **TD-01** — Credential handling: env-var contract (WR-02), per-call str-copy
  proliferation (WR-03), `_append_query_param` overwrite (WR-04), sentinel leak
  tests (WR-05), and scheduler auth-reject heuristic (WR-06). All from
  `93-credential-infrastructure/93-REVIEW.md`.
- **TD-02** — REST fuzzer 5xx cascade counter trips on connection-exception
  failures (timeout-only servers no longer escape the cascade pause). From
  `96-active-rest-fuzzing/96-REVIEW.md` WR-03.

**Scope-anchor note:** This phase is orthogonal to report-content work
(v5.2-D-01). No executive-narrative, scoring, or render-surface changes here.

**Numbering caveat for downstream agents:** `REQUIREMENTS.md` tags TD-01 as
`[WR-02/04/06]`, but the authoritative findings are **WR-02 through WR-06 in
`93-REVIEW.md`** (not 94-REVIEW). Trust the file paths in Canonical References
below, not the bracket digits.

</domain>

<decisions>
## Implementation Decisions

All five TD-01 sub-items were scoped IN (user chose "Add WR-05 + WR-06" — the
full deferred set). Fix-directions below were locked on a **likelihood-weighted**
basis: in a cleanup phase, prefer the lowest-regression fix that removes the
silent/misleading behavior over the heavier refactor, especially for
low-trigger findings.

### TD-01 — Credential handling (`93-REVIEW.md`)

- **D-01 (WR-02 — env-var all-caps mismatch): Correct the docstring, do NOT
  enforce `isupper()`.** `from_cli` (quirk/auth/credentials.py:115-186) accepts
  any name present in `os.environ`; the docstring (lines ~129) wrongly says
  "all-caps". Reword the docstring to "any name present in the environment is
  read and deleted." Rationale: low trigger likelihood (needs a lowercase ref
  colliding with a real env var), and enforcing all-caps would reject legitimate
  lowercase env-var names some shops use — friction disproportionate to a
  theoretical collision. Zero behavior change.

- **D-02 (WR-03 — per-call str-copy): Document + bound under D-05, do NOT
  refactor to materialize-once.** `as_headers()`/`query_param()`
  (credentials.py:53-77) re-decode the secret to a new immortal `str` every
  call. v5.1's **D-05 already accepts** best-effort zeroization / str-copy
  proliferation. Add an explicit comment documenting the accepted proliferation
  and noting the call-count bound (once per endpoint per scan), rather than
  threading a pre-built dict through the JWT-scanner call sites. Rationale: the
  "real fix" touches multiple call sites for a gap D-05 already owns —
  regression risk disproportionate to a cleanup phase; high run-frequency but
  bounded, already-accepted impact.

- **D-03 (WR-04 — `_append_query_param` overwrite): Reject pre-existing param.**
  `quirk/scanner/jwt_scanner.py:41-51` does `existing[param]=[value]`, silently
  dropping an operator-probed `?api_key=...` already on the target URL. Change
  to detect a pre-existing same-named param and reject/skip that target with a
  clear (scrubbed) message. Rationale: low trigger likelihood but the fix is
  trivial and eliminates silent operator-surprise data loss — clean win.

- **D-04 (WR-05 — sentinel leak tests assert on pre-scrubbed data): Route ≥1
  surface through the real write/scrub path.** `tests/test_credential_leakage.py`
  (`:303-356`, `:145-158`) re-asserts data the test itself already scrubbed via
  `safe_str`, so it cannot catch a regression in the real PDF renderer or an
  unscrubbed write path. For at least one surface, inject the sentinel through
  the *actual* scanner/scrub path (e.g. construct a `CryptoEndpoint` whose
  `scan_error` is set by the real exception handler). Mark the PDF assertion
  explicitly as a documented coverage gap, not coverage. Rationale: low trigger
  but it's a test-honesty / security-control-honesty item — the leak suite's
  "11 surfaces" claim currently overstates what is mechanically verified.

- **D-05 (WR-06 — scheduler `.yml` extension heuristic): Parse any existing
  file; do NOT gate on file extension.** `quirk/cli/schedule_cmd.py:24-46`
  (`_config_has_authenticated_mode`, line 33) returns `False` for any config
  path not ending `.yml`/`.yaml`, so an auth config at an unconventional path
  bypasses the D-11 "credentials must never persist in scheduled scans" reject.
  Attempt the YAML parse for any existing file and reject on
  parse-as-dict-with-auth-flag. Consider rejecting when the config cannot be
  definitively classified as non-authenticated. Rationale: low trigger but high
  stakes — a security control silently not engaging is exactly the kind of item
  to close before client-facing artifact work.

### TD-02 — REST fuzzer cascade counter (`96-REVIEW.md` WR-03)

- **D-06: Combined `consecutive_failures` counter covering both 5xx and
  connection exceptions; reset only on a genuine success.**
  `quirk/scanner/rest_fuzzer.py:601-618` currently sets `consecutive_5xx = 0` on
  request exception (line 603), so a server failing via timeouts/connection
  resets never reaches 3 *consecutive* 5xx and the cascade pause never fires.
  Treat request exceptions as part of the cascade signal — increment the same
  counter against the same `_CONSECUTIVE_5XX_LIMIT` threshold rather than
  resetting, and reset only on a real success response. Connection-level
  failures are at least as strong a "back off" signal as 5xx. Rejected the
  separate-exception-threshold option (adds a second tunable constant + surface
  for a cleanup phase). **Note:** the alg-confusion path at lines ~674-678 also
  feeds the cascade tracker (WR-01, already fixed) — keep that consistent with
  the combined-counter semantics.

### Claude's Discretion
- Exact wording of corrected docstrings, comments, log messages.
- Whether the combined counter is renamed (`consecutive_failures`) or the
  existing `consecutive_5xx` is kept and its semantics broadened — planner/
  executor's call, as long as exceptions now count toward the pause.
- Which specific leak-test surface (WR-05) is routed through the real path —
  pick the highest-value one (PDF render or scan-error JSON).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source review findings (authoritative scope + fix options)
- `.planning/milestones/v5.1-phases/93-credential-infrastructure/93-REVIEW.md` §WR-02..WR-06 — the five credential design-judgment findings (TD-01), each with file:line and the either/or fix the human just decided. **This is the source of truth for TD-01 — NOT 94-REVIEW.**
- `.planning/milestones/v5.1-phases/96-active-rest-fuzzing/96-REVIEW.md` §WR-03 (lines 111-121) — the cascade-counter finding (TD-02) with file:line.
- `.planning/v5.1-MILESTONE-AUDIT.md` (lines 14, 16) — records these as deferred design-judgment follow-ups for v5.2.

### Requirements & decisions
- `.planning/REQUIREMENTS.md` — TD-01 (line 39), TD-02 (line 40); coverage rows lines 82-83.
- `.planning/STATE.md` §Accumulated Context — v5.2-D-01 (phase 97 first, orthogonal to report work); pending-todo note to read v5.1-MILESTONE-AUDIT.md at plan time.
- v5.1 locked decision **D-05** (best-effort zeroization / str-copy accepted) and **D-11** (credentials must never persist in scheduled scans) — referenced throughout 93-REVIEW; these constrain D-02 and D-05 above.

### Target source files
- `quirk/auth/credentials.py:53-77` (`as_headers`/`query_param`), `:115-186` (`from_cli`) — WR-02, WR-03.
- `quirk/scanner/jwt_scanner.py:41-51` (`_append_query_param`) — WR-04.
- `tests/test_credential_leakage.py:303-356`, `:145-158` — WR-05.
- `quirk/cli/schedule_cmd.py:24-46` (`_config_has_authenticated_mode`, line 33) — WR-06.
- `quirk/scanner/rest_fuzzer.py:493`, `:601-618`, `:674-678` (cascade tracker) — TD-02.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `safe_str` / `safe_exc.py` redaction helpers — already used across credential
  paths; reuse for any new reject/log messages (WR-03/04/06) so secrets stay
  scrubbed. WR-05's real-path test should exercise these, not bypass them.
- `_KEY_PARAM_NAMES` constant (added in 93 remediation, commit 624f55a) — the
  canonical set of key-bearing query-param names; reference it rather than
  re-listing param names (relates to IN-01).
- `validate_external_url` (rest_fuzzer scope gate) — unaffected, but confirms
  the dispatch loop already has structured pre-dispatch guards to model after.

### Established Patterns
- **best-effort zeroization (D-05):** `bytearray` secret buffer, `close()` zeros
  in place, str only at injection boundary. D-02 above explicitly keeps this
  stance rather than upgrading it.
- **fail-closed security controls (D-11):** scheduler must reject authenticated
  configs; D-05/WR-06 fix strengthens this from an extension heuristic to a
  parse-based check.
- **per-operation try/except + `continue`** already added in the fuzz loop
  (rest_fuzzer.py:571, 96-REVIEW WR-04) — TD-02's exception handling lives in the
  same loop; keep the cascade increment consistent with that structure.

### Integration Points
- The cascade counter (TD-02) interacts with two increment sites: the main
  dispatch path (line ~611) and the alg-confusion path (line ~676). Both must
  use the combined-failure semantics so the pause fires consistently.
- WR-04 reject path connects `jwt_scanner._append_query_param` to its caller's
  target-list iteration — rejecting one target must not abort the others.

</code_context>

<specifics>
## Specific Ideas

- All fix-directions were chosen on a **likelihood-weighted** rubric the user
  articulated: recommend by how likely each finding is to actually produce a
  wrong/surprising result a client or operator sees — not by how often the code
  path runs. This is why two high-frequency-but-low-impact items (WR-02, WR-03)
  resolved to "document/correct" while two low-frequency-but-control-honesty
  items (WR-05, WR-06) were scoped in and fixed properly.

</specifics>

<deferred>
## Deferred Ideas

- **IN-01** (93-REVIEW): centralize `_query_param` redaction names into one
  `_KEY_PARAM_NAMES` constant referenced everywhere. Partial constant exists;
  full centralization not in TD-01 scope — note for a future hardening pass.
- **IN-02** (93-REVIEW): `from_cli` silently resolves multiple `--auth-*` flags
  by hardcoded precedence instead of raising. Not in TD-01 prose — deferred.
- WR-05's "11 surfaces" coverage claim: only ≥1 surface is being routed through
  the real path this phase; the remaining sentinel tests stay as documented
  coverage gaps. A fuller leak-suite rebuild is out of scope.

### Reviewed Todos (not folded)
- STATE.md pending todos for Phases 98/99/100 — belong to their own phases; not
  relevant to this cleanup phase.

</deferred>

---

*Phase: 97-v5.1 Tech-Debt Cleanup*
*Context gathered: 2026-05-23*
