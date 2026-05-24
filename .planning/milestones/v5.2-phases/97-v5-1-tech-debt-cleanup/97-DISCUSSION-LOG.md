# Phase 97: v5.1 Tech-Debt Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-23
**Phase:** 97-v5.1 Tech-Debt Cleanup
**Areas discussed:** TD-01 scope, WR-02 env-var contract, WR-03 str-copy, WR-04 query-param overwrite, TD-02 cascade counter

> The user requested likelihood-weighted recommendations before answering. Claude
> assessed each finding by trigger-likelihood × client/operator-visible impact;
> the user then locked all recommendations.

---

## TD-01 Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Just the 3 named (WR-02/03/04) | Stick to requirement prose; leave WR-05/WR-06 deferred | |
| Add WR-06 (scheduler heuristic) | Include the brittle .yml-extension reject | |
| Add WR-05 + WR-06 | Close all five deferred 93-REVIEW items | ✓ |

**User's choice:** Add WR-05 + WR-06 (full deferred set in scope)
**Notes:** All five 93-REVIEW design-judgment items (WR-02..06) are in scope.

---

## WR-02 — Env-var all-caps contract

| Option | Description | Selected |
|--------|-------------|----------|
| Enforce all-caps | Add `ref.isupper() and ref in os.environ` | |
| Correct the docstring | Keep behavior, reword docstring to "any name in environment" | ✓ |
| Enforce + warn | Require all-caps and warn on non-all-caps env collision | |

**User's choice:** Correct the docstring (likelihood-weighted recommendation)
**Notes:** Low trigger likelihood; enforcing all-caps would reject legitimate
lowercase env-var names — friction disproportionate to a theoretical collision.

---

## WR-03 — Per-call str-copy proliferation

| Option | Description | Selected |
|--------|-------------|----------|
| Materialize once at boundary | Build header/query dict once, pass it down | |
| Document + bound under D-05 | Keep per-call decode, document accepted proliferation | ✓ |

**User's choice:** Document + bound under D-05 (likelihood-weighted recommendation)
**Notes:** High run-frequency but already-accepted bounded impact under v5.1 D-05;
the refactor touches JWT-scanner call sites for marginal gain — regression risk
disproportionate to a cleanup phase.

---

## WR-04 — `_append_query_param` overwrite

| Option | Description | Selected |
|--------|-------------|----------|
| Reject pre-existing param | Raise/skip if target URL already carries the param | ✓ |
| Document replace-is-intended | Keep overwrite, add comment + scrubbed debug log | |
| Append rather than replace | Add value alongside existing (undefined server semantics) | |

**User's choice:** Reject pre-existing param (likelihood-weighted recommendation)
**Notes:** Low trigger but trivial fix; removes silent operator-surprise data loss.

---

## TD-02 — REST fuzzer 5xx cascade counter

| Option | Description | Selected |
|--------|-------------|----------|
| Combined failure counter | Exceptions + 5xx share one counter/threshold; reset only on success | ✓ |
| Separate exception threshold | Track exceptions in their own counter with its own limit | |

**User's choice:** Combined failure counter (matches 96-REVIEW prescribed fix)
**Notes:** Timeout-only servers now trip the back-off; rejected separate threshold
to avoid a second tunable constant in a cleanup phase.

---

## Claude's Discretion

- Exact wording of corrected docstrings, comments, and log messages.
- Whether the combined counter is renamed (`consecutive_failures`) or the existing
  `consecutive_5xx` variable's semantics are broadened.
- Which leak-test surface (WR-05) is routed through the real write/scrub path.

## Deferred Ideas

- IN-01 — centralize `_KEY_PARAM_NAMES` redaction set everywhere.
- IN-02 — raise on multiple `--auth-*` flags instead of hardcoded precedence.
- Fuller leak-suite rebuild beyond the ≥1 real-path surface (WR-05).
