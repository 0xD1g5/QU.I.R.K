---
type: todo
created: 2026-10-12
source: Phase 224 gap closure A (docs/report-interpretation.md sections 3.4 and 4)
priority: medium
area: run_scan.py, quirk/intelligence/evidence.py, quirk/engine/findings_evaluator.py, quirk/cbom/classifier.py
status: pending
resolves_phase: null
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

- [ ] Decide whether a scan should emit a CRITICAL "Bearer token is unsigned (alg:none)" finding for a declared `none`
      algorithm, as the evidence.py comment assumes.
- [ ] If yes: add the branch in `findings_evaluator.py`, a compliance-map entry (`quirk/compliance/__init__.py` has a
      coverage test for titles), and a test; the CRITICAL count then feeds the score ceiling.
- [ ] If no: correct the comment at `evidence.py:419-420`.

## Feasibility & Effort

**CONFIRMED** by reading `run_scan.py:4039-4051` and `evidence.py:418-424`, by `grep -rn BEARER_TOKEN quirk/`, and by
running `quirk analyze-token` with an `alg:none` token (exit 1) in a scratch HOME. Effort **S** for the comment-only
option; **M** for the finding (one evaluator branch, compliance-map and title-bridge entries, a test, golden fixtures
only if a fixture carries a bearer endpoint). Unknown: whether an unsigned token the operator themselves supplied
should be CRITICAL or only advisory, since the scanner never verifies the signature. **Spike**: not needed.
