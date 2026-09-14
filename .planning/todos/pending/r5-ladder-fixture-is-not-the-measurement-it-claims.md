# The R5 calibration rung documents itself as measured, but four of its fields were never measured

**Filed:** 2026-09-14 (demo-prep task 3 groundwork)
**Priority:** P2 — the ladder's verdict is unaffected today, the fidelity claim is not
**Status:** open

## Claim vs. reality

`tests/test_score_properties.py::_multihost_evidence()` describes itself as "the recorded 31-host
deliberately-vulnerable chaos-lab estate (`multihost` profile, **measured 2026-09-13**)", and is
rung **R5** of the calibration ladder — the one rung billed as non-synthetic. Duplicated verbatim in
`tests/test_score_denominator_999_113.py`.

Measured the same estate 2026-09-14 (`findings-20260914-142606.json` /
`intelligence-20260914-142606.json`) and compared field by field:

| Field | R5 fixture | Lab actually emits |
|---|---|---|
| `finding_severity_counts` | 5 / 14 / 33 / 16 / 330 | 5 / 14 / 33 / 16 / **332** (INFO) |
| `certificate_observations` | 17 observed, 5 expired | ✅ identical |
| `assessable_endpoint_count` | 38 | ✅ 38 |
| `plaintext_http_count` | 6 | **10** |
| `http_on_tls_port_count` | 3 | **0** |
| `cert_key_type_counts` | `{RSA: 0, ECDSA: 0}` | **`{RSA: 18, ECDSA: 1}`** |
| `pqc_hybrid_endpoint_count` | *absent* | **21** |

Severity counts and certificate observations match exactly, so the fixture **is** derived from a
real run. But `{RSA: 0, ECDSA: 0}` alongside 17 observed certificates is not a measurement — it is
an omission. And the absent `pqc_hybrid_endpoint_count` denies R5 the `+8` PQC-hybrid credit the
real estate earns, which is a material input to its score.

## Why it doesn't break anything today

`MULTIHOST_CALIBRATION_CEILING = 30`. The fixture scores **18**; the real measured evidence scores
**15**. Both are under the ceiling, so `test_ladder_is_monotonic` and the ceiling assertion hold
either way, and the full scoring surface is green (439 passed / 3 xfailed, selected via
`grep -rln "quirk.intelligence.scoring" tests/`).

## Why it still matters

The ladder's authority rests on being "an independent instrument rather than a description of the
current model" — the bands were set blind, and R5 is the rung that anchors the bottom in reality. A
rung that is partly hand-filled is partly a description of the model after all. The 3-point gap
between fixture and reality is small now; nothing keeps it small.

## Proposed work (this is the "sixth non-synthetic rung" from the demo-prep handoff)

1. Add **R6** as the fully measured 2026-09-14 evidence — copy `evidence_summary` verbatim from
   `intelligence-20260914-142606.json`, no hand-editing of any field.
2. Keep R5 as-is with its comment corrected to say which fields were not captured, OR re-derive it
   from the same measured source. **Do not silently overwrite R5** — the operator-set band on it was
   set against its current numbers, and 999.113 D5 forbids moving a target to fit.
3. Whichever is chosen, update **both** copies (`test_score_properties.py` and
   `test_score_denominator_999_113.py`) — the fixture is duplicated deliberately, with a comment
   saying "if you change one, change both, and re-measure".

## Standing lesson

Third instance in this project of a hand-maintained record drifting from the source it claims to
describe. The fixture's own docstring is what made it credible; the docstring was not the
measurement. Re-derive from `intelligence-*.json` at write time rather than transcribing.
