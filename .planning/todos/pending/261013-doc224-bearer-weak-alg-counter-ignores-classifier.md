---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §3 Agility table)
priority: medium
area: quirk/intelligence/evidence.py (bearer_token_weak_alg_count)
status: pending
resolves_phase: null
owner: "999.131"
---

# Bearer-token "weak algorithm" counter counts every declared alg, including quantum-safe ML-DSA

`quirk/intelligence/evidence.py:423-424` increments `bearer_token_weak_alg_count` for any `cert_pubkey_alg` other
than `none`. The comment at `:419-420` assumes every declared alg is quantum-vulnerable, but a token declaring
`ML-DSA-65` (classified quantum-safe by `quirk/cbom/classifier.py`) still lowers the Agility score. Probe
`gc3-r3-f1-*`: an ML-DSA-65 bearer token increments the counter.

When fixed, update docs/report-interpretation.md §3 Agility table, "Bearer token weak algorithm" row.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `evidence.py:423-424` (`if _bt_alg and _bt_alg.lower() != "none"`).
- Fix: gate the increment on `classify_algorithm(alg)` quantum level 0 (quantum-vulnerable).
- Unknown: classifier spelling for JOSE alg names (`ML-DSA-65` vs `MLDSA65`); add a test for both.

## Phase 230 disposition (2026-10-23)

Left pending, owner unchanged. Plan 230-04 corrected the `evidence.py` comment and the none/missing exclusions but found
this NOT trivially closable: `bearer_token_weak_alg_count` still counts any non-"none" declared alg without consulting
the classifier, so an ML-DSA bearer is still counted as weak. Fixing it moves the Agility score and is a scoring-model
change, not a DETECT-05 follow-through.
