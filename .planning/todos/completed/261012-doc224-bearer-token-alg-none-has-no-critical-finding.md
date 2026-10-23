---
type: todo
created: 2026-10-12
source: Phase 224 gap closure A (docs/report-interpretation.md sections 3.4 and 4)
priority: medium
area: run_scan.py, quirk/intelligence/evidence.py, quirk/engine/findings_evaluator.py, quirk/cbom/classifier.py
status: completed
completed: 2026-10-23
resolves_phase: 230
owner: DETECT-05
---

# A bearer token declaring `alg:none` produces no CRITICAL finding in a scan

`quirk/intelligence/evidence.py:419-420` says of the `BEARER_TOKEN` counter: "alg:none is a separate CRITICAL finding;
this counter tracks quantum-vulnerable conventional algorithms". No such finding exists on the scan path:

- `run_scan.py:4039-4051` turns an authenticated scan's bearer credential into a `BEARER_TOKEN` endpoint with
  `severity="INFO"` and `service_detail="declared_algorithm (unverified)"`, whatever the declared algorithm is.
- `grep -rn "BEARER_TOKEN" quirk/` finds the endpoint only in `evidence.py` and `cbom/builder.py`; `findings_evaluator.py`
  has no bearer-token branch.
- `quirk/cbom/classifier.py:165` maps `"none"` to level 0, but the name `alg:none` is not a table key, so the CBOM
  component classifies as `unknown` (`classify_algorithm("alg:none")` -> `(UNKNOWN, None, None)`).
- Only `quirk analyze-token` flags it: run live 2026-10-12 against an `{"alg":"none"}` token, it printed
  `CRITICAL: alg:none detected` and exited 1.

So a scan given an unsigned bearer token reports nothing above INFO, the scoring counter deliberately skips it
(`evidence.py:423`), and the readiness score is unchanged. The report-interpretation guide no longer claims otherwise
(section 3.4 says `quirk analyze-token` flags it; section 4's CRITICAL examples were changed).

- [x] Decide whether a scan should emit a CRITICAL "Bearer token is unsigned (alg:none)" finding for a declared `none`
      algorithm, as the evidence.py comment assumes.
- [x] If yes: add the branch in `findings_evaluator.py`, a compliance-map entry (`quirk/compliance/__init__.py` has a
      coverage test for titles), and a test; the CRITICAL count then feeds the score ceiling.
- [ ] If no: correct the comment at `evidence.py:419-420`.

## Feasibility & Effort

**CONFIRMED** by reading `run_scan.py:4039-4051` and `evidence.py:418-424`, by `grep -rn BEARER_TOKEN quirk/`, and by
running `quirk analyze-token` with an `alg:none` token (exit 1) in a scratch HOME. Effort **S** for the comment-only
option; **M** for the finding (one evaluator branch, compliance-map and title-bridge entries, a test, golden fixtures
only if a fixture carries a bearer endpoint). Unknown: whether an unsigned token the operator themselves supplied
should be CRITICAL or only advisory, since the scanner never verifies the signature. **Spike**: not needed.

## Resolution (Phase 230, 2026-10-23)

- Decision (D-15): YES, a scan emits the finding. `b8d7541b` adds the shared predicate `quirk/util/jwt_alg.py`, a tri-state `CredentialContext.bearer_alg_state()` and a testable `run_scan._bearer_token_endpoints`; `20372047` adds `evaluate_bearer_token_endpoints` (called from `evaluate_protocol_service_endpoints`, so CLI report and dashboard share it), the `UNMAPPED_TITLES` entry with a justifying comment, and corrects the `evidence.py` comment. An `alg` of `none` (any case) or a missing alg yields one CRITICAL "Bearer token is unsigned (alg:none)".
- Score treatment (D-15): an ORDINARY CRITICAL. It enters the findings list, is counted in the evidence summary's CRITICAL count and feeds `_consequence_ceiling` like any open CRITICAL (the test asserts "1 open CRITICAL finding" in `rating_cap_reason`). No score-exclusion special case; no COMPLIANCE_MAP entry; `bearer_token_weak_alg_count` still excludes none (0 for none/missing, 1 for HS256: no double count); `SCORING_VERSION` stays 3.0; ladder rungs and golden fixtures carry no bearer endpoint, so no regeneration. The raw token never appears in endpoint fields or finding text.
- Proof: `tests/test_bearer_alg_none_finding.py` (13 passed, observed 2026-10-23). Fail-first 12 failed, 1 passed; removing the evaluator term turns 6 red. UAT-230-06.
- The unticked branch ("If no: correct the comment") does not apply; the comment was corrected anyway.
- Follow-up left pending: `261013-doc224-bearer-weak-alg-counter-ignores-classifier` is NOT trivially closable (the counter still counts any non-none declared alg without consulting the classifier).
- 999.125 item 3 fixed; with items 1 and 2 the row closes.
