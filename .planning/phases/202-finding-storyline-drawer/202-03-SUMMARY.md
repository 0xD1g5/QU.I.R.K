---
phase: 202-finding-storyline-drawer
plan: 03
subsystem: dashboard-api
tags: [fastapi, pydantic, storyline, findings, catalog, disambiguation]
dependency-graph:
  requires: ["202-01 (title-bridge ledger, not consumed directly)", "202-02 (locked TS FindingStoryline contract this model mirrors)"]
  provides: ["FindingStoryline (Python)", "findings_for_endpoint", "finding_by_id_and_title", "GET /api/findings/{id}/storyline"]
  affects: [202-04, 202-05]
tech-stack:
  added: []
  patterns: ["single-endpoint finding derivation shared between the list route and the per-finding route (no duplicated branch logic)"]
key-files:
  created:
    - quirk/dashboard/api/routes/storyline.py
    - tests/test_dashboard_finding_storyline.py
  modified:
    - quirk/dashboard/api/schemas.py
    - quirk/dashboard/api/routes/scan.py
    - quirk/dashboard/api/app.py
    - tests/test_finding_title_bridge.py
    - .planning/phases/202-finding-storyline-drawer/202-VALIDATION.md
decisions:
  - "narrative = f'{risk_label} — {impact_sentence}' (ALGO_IMPACT_MAP indices 0+1), mirroring the executive report's markdown join at quirk/reports/executive.py:432, minus the markdown emphasis since this is a plain-text API field"
  - "quantum_impact = ALGO_IMPACT_MAP[key][2] verbatim, mirroring findings_evaluator._build_finding's own quantum_risk composition (findings_evaluator.py:122-125)"
  - "remediation_guidance = REMEDIATION_CATALOG[key] verbatim, mirroring findings_evaluator._build_finding's own recommendation composition when a catalog entry exists (findings_evaluator.py:115-116); the NIST_IR_8547_DEPRECATION fallback boilerplate branch is NOT mirrored — that branch exists only for the no-catalog-match case, which this route leaves as honest None per D-07 rather than authoring text"
  - "the KERBEROS/SAML/DNSSEC identity-protocol skip and the severity sort both stay in _derive_findings as loop-level (whole-list) concerns; only the nine per-endpoint branches moved into findings_for_endpoint"
metrics:
  duration: "~55 min"
  completed: 2026-09-12
---

# Phase 202 Plan 03: Storyline Endpoint Summary

Shipped `GET /api/findings/{finding_id}/storyline` — an auth-gated, read-only route keyed by
`(CryptoEndpoint.id, title)` per D-06, returning a Pydantic `FindingStoryline` model that mirrors
202-02's locked 10-field TS contract, with its narrative section assembled server-side from the
existing Phase-99 `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` catalogs and nothing else.

## What Shipped, Per Task

**Task 1 — schema + shared per-endpoint lookup.** Added `FindingStoryline` to `schemas.py`,
docstring citing the `FindingItem` "DO NOT UNIFY" comment and the `RoadmapNode.score_lift`
`None`-never-`0` contract it inherits. Extracted `findings_for_endpoint(ep) -> list[FindingItem]`
from `_derive_findings`' per-endpoint loop body — the nine branch conditions (HTTP, legacy TLS,
weak ciphers, cert-expired, cert-expiring, undersized-RSA, self-signed, untrusted-CA, quantum-
vulnerable-non-RSA) now live in exactly one place, verified by `grep -c "title="` against the
extracted body: each of the nine sites appears exactly once. `_derive_findings` now only retains
the two genuinely loop-level (whole-endpoint-list) concerns: the KERBEROS/SAML/DNSSEC
identity-protocol skip (a cross-endpoint filter, not a per-endpoint rule) and the final
CRITICAL>HIGH>MEDIUM>LOW>INFO severity sort (a property of the assembled list). Added
`finding_by_id_and_title(db, endpoint_id, title)`, an exact-string-match resolver returning
`(ep, finding)` / `(ep, None)` / `(None, None)` so the route can distinguish "no such endpoint"
from "no such title on this endpoint."

**Task 2 — the route.** `quirk/dashboard/api/routes/storyline.py`: `APIRouter(dependencies=
[Depends(require_auth)])`, the same construction `connectors.py` (Phase 193) uses. `title` is a
required, length-bounded (`max_length=512`) query parameter; FastAPI's own `int` path coercion and
`Query(...)` give 422 for free on a non-numeric `finding_id` or an omitted `title` — no hand-rolled
validator that could echo the value back. Two distinct fixed 404 details separate "no such
endpoint" from "endpoint exists, title doesn't match." A generic exception handler (both around
the lookup and around narrative assembly) returns the fixed `"Storyline lookup failed"` 500 detail
via `logger.exception` server-side, never the exception's own text. Registered in `app.py` beside
the fifteen sibling `include_router` calls.

**Task 3 — tests.** `tests/test_dashboard_finding_storyline.py`, 13 tests, all green.

## Catalog-Tuple-Index → Response-Field Mapping (D-05)

`ALGO_IMPACT_MAP[key]` is a 3-tuple `(risk_label, impact_sentence, quantum_risk_sentence)`
(`quirk/reports/content_model.py:230-232`). Two existing composition sites in the report engine
compose these indices into text; the route mirrors the appropriate one for each response field:

| Response field | Source | Mirrors | Composition |
|---|---|---|---|
| `narrative` | `ALGO_IMPACT_MAP[key][0]` + `[1]` | `quirk/reports/executive.py:432` (executive markdown risk list) | `f"{risk_label} — {impact_sentence}"` — same join, markdown `**bold**` dropped since this is a plain-text API field, not rendered markdown |
| `quantum_impact` | `ALGO_IMPACT_MAP[key][2]` | `quirk/engine/findings_evaluator.py:122-125` (`_build_finding`'s own `quantum_risk` field) | verbatim, no transformation |
| `remediation_guidance` | `REMEDIATION_CATALOG[key]` | `quirk/engine/findings_evaluator.py:115-116` (`_build_finding`'s own `recommendation` field, catalog-match branch) | verbatim, no transformation |

The `_build_finding` fallback branch that appends `NIST_IR_8547_DEPRECATION` boilerplate
(`findings_evaluator.py:117-119`) is deliberately NOT mirrored: that branch exists only when there
is NO catalog match, which this route leaves as honest `None` per D-07 rather than authoring new
text. Mirroring it would mean writing new narrative content in the dashboard layer — exactly what
D-05 prohibits.

`_classify_finding` is called with exactly the three keys `FindingItem` actually carries a
counterpart for (`severity`, `title`, `description`) — it also reads `category`/`check_id`, which
`FindingItem` has no equivalent field for, noted in-line in `storyline.py`.

## Disambiguation Proof (D-06)

`test_disambiguation_same_endpoint_id_different_title_different_storyline` seeds ONE
`CryptoEndpoint` with `cert_pubkey_alg="RSA"`, `cert_pubkey_size=1024` (fires the undersized-RSA
branch, HIGH, RSA keyword -> narrative populated) AND `cert_issuer == cert_subject` (fires the
self-signed branch, HIGH, no keyword -> narrative absent per D-07). Both branches are independent
top-level `if`s in `findings_for_endpoint` (not mutually exclusive with the RSA branch), so both
findings share the same `CryptoEndpoint.id`. Requesting `(same id, "TLS certificate uses
undersized RSA key")` vs. `(same id, "TLS certificate is self-signed")` returns two genuinely
different response bodies — one with a real catalog narrative, one with honest absence — proving
the route resolves the requested title's OWN finding rather than "the first finding for this id."
This was chosen deliberately over pairing two narrative-absent findings (e.g. legacy-TLS +
self-signed), which would have produced two byte-identical response bodies differing in nothing
the test could assert on — that pairing was rejected during authoring precisely because it "cannot
fail," per the plan's own guidance.

## Finding Classes: Narrative vs. Absence

Of the nine `findings_for_endpoint` classes, only the undersized-RSA class (`ALGO_IMPACT_MAP["RSA"]`
keyword match) is exercised as narrative-present in this plan's tests — it is the one class research
already flagged (202-01) as byte-identical between dashboard and CLI vocabularies. Per D-07, the
majority of classes (plaintext HTTP, legacy TLS, weak ciphers, cert-expired, cert-expiring,
self-signed, untrusted-CA) carry no `_ALGO_KEYWORDS` hit in their title/description and resolve to
A5 absence — confirmed live for plaintext-HTTP and self-signed in this plan's tests. The
quantum-vulnerable-non-RSA class (`Quantum-{label} algorithm: {alg}`) was not directly exercised
here; its title embeds the raw algorithm name (e.g. "ECDSA", "DSA", "DH"), all of which ARE
`_ALGO_KEYWORDS` entries, so it is expected to hit the catalog — left for 202-05's fuller
reachability work rather than duplicated here, since this plan's job was proving the mechanism
works, not enumerating every class exhaustively.

## 404 / 422 / 500 Handling

- **422:** omitted `title` (FastAPI `Query(...)` required-ness), non-numeric `finding_id` (FastAPI
  path `int` coercion), `title` over 512 chars (`max_length=512`). None hand-validated.
- **404:** `"Finding not found"` (no such `CryptoEndpoint.id`) vs. `"Finding not found for the
  given title"` (endpoint exists, no matching finding) — two distinct fixed strings, neither ever
  contains the submitted `finding_id` or `title`, asserted by test.
- **500:** `finding_by_id_and_title` patched to raise `RuntimeError("/Users/someone/secret/path.db
  exploded")`; response asserts the exact fixed detail `"Storyline lookup failed"` and the absence
  of `Traceback`, `/Users/`, and the injected path fragment anywhere in the response body.

## RED/GREEN Transcript (Task 3)

Since Tasks 1-2 already implemented the route ahead of Task 3's test authoring (a natural
consequence of this plan's task ordering — schema/lookup, then route, then tests), a literal
"write tests against a not-yet-existing route" RED was not available. To honor the `tdd="true"`
requirement honestly, a genuine RED was manually demonstrated instead: the narrative-composition
`if` block inside `get_finding_storyline` was temporarily replaced with `if False:` (disabling
narrative/quantum_impact/remediation_guidance population entirely), the suite was re-run, and
exactly the two tests that assert non-null catalog output failed on the precise assertions this
task requires:

```
FAILED tests/test_dashboard_finding_storyline.py::test_disambiguation_same_endpoint_id_different_title_different_storyline - assert None is not None
FAILED tests/test_dashboard_finding_storyline.py::test_narrative_present_undersized_rsa_matches_catalog_verbatim - AssertionError: assert None == 'Harvest-now-decrypt-later exposure — adversaries may already be archiving encrypted traffic for future decryption.'
2 failed, 11 passed
```

The file was then restored byte-identically (`cp` from a pre-edit backup) and re-run GREEN:

```
13 passed
```

`git status --short quirk/dashboard/api/routes/storyline.py` showed no diff after restoration —
the RED probe left no trace.

## Verification

- `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py` → 13 passed
- `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py tests/test_dashboard_api.py tests/test_finding_engine_parity.py` → 76 passed
- `.venv/bin/python -m pytest -q tests/test_dashboard_api.py tests/test_finding_engine_parity.py tests/test_dashboard_finding_segment_field.py tests/test_dashboard_empty_state_contract.py` → 69 passed (Task 1's pre-task baseline, unchanged)
- `.venv/bin/python -m compileall -q quirk` → exits 0
- `grep -n "require_auth" quirk/dashboard/api/routes/storyline.py` → router-level dependency present, no per-endpoint auth
- `grep -n "str(exc)\|{title}\|format(title" quirk/dashboard/api/routes/storyline.py` → no matches
- `git status --short quirk/reports/content_model.py quirk/engine/findings_evaluator.py` → clean (zero catalog edits)
- Full-suite (`.venv/bin/python -m pytest -q -m ""`) → 3 failed / 4984 passed / 42 skipped / 72 xfailed /
  5 xpassed (see "Full-Suite Failing-Node SET" above for the two-run comparison)

## Deviations from Plan

**1. [Rule 1 - Bug] Retargeted 202-01's title-bridge extractor at `findings_for_endpoint`.**
- **Found during:** the full-suite run required by this plan's own verification step.
- **Issue:** Task 1's extraction of the nine per-endpoint branches out of `_derive_findings` into
  `findings_for_endpoint` silently broke `tests/test_finding_title_bridge.py` (202-01), which sliced
  `_derive_findings`' source body via `_slice_function(source, "_derive_findings")` to regenerate its
  title-emission-site occurrence set at test-run time. With the sites moved, that extractor found 0
  sites instead of 9, cascading into a second failure in the reachability census (which also sliced
  `_derive_findings` to read `severity=` literals).
- **Fix:** retargeted both `_slice_function(source, "_derive_findings")` call sites in
  `tests/test_finding_title_bridge.py` at `"findings_for_endpoint"`, where the title=/severity= sites
  now live. No change to the ledger's dispositioned data (`DASHBOARD_TITLE_BRIDGE`,
  `UNBRIDGED_DASHBOARD_TITLES`, `BRIDGE_REACHABILITY`) — only to where the run-time source scan looks.
- **Files modified:** `tests/test_finding_title_bridge.py`
- **Commit:** `350fe0fa`

No other Rule 1/2/3/4 fixes were required beyond the plan's own explicitly-anticipated need to
derive a narrative-composition mapping from two separate report-engine sites (documented above).

## Full-Suite Failing-Node SET (before vs. after this plan's changes)

Run 1 (`.venv/bin/python -m pytest -q -m ""`, before the fix above) — **5 failed**, 4982 passed:
```
FAILED tests/test_errors_cmd.py::test_lookup_single_known_returns_zero
FAILED tests/test_finding_title_bridge.py::test_dashboard_extractor_finds_plausible_number_of_sites
FAILED tests/test_finding_title_bridge.py::test_bridge_reachability_matches_recomputed_classification
FAILED tests/test_hardware_staleness.py::test_hardware_matrix_not_stale
FAILED tests/test_uat_disposition_integrity.py::test_non_vacuity_skipped_substitute_is_flagged
```

Run 2 (after the extractor retarget) — **3 failed**, 4984 passed:
```
FAILED tests/test_errors_cmd.py::test_lookup_single_known_returns_zero
FAILED tests/test_hardware_staleness.py::test_hardware_matrix_not_stale
FAILED tests/test_uat_disposition_integrity.py::test_non_vacuity_skipped_substitute_is_flagged
```

The two `test_finding_title_bridge.py` failures are gone. The remaining three are pre-existing and
unrelated to any file this plan touches:
- `test_hardware_staleness.py::test_hardware_matrix_not_stale` — the documented, operator-deferred
  91-day calendar-time staleness trip named in this plan's own `<CRITICAL_OVERRIDES>`.
- `test_errors_cmd.py::test_lookup_single_known_returns_zero` and
  `test_uat_disposition_integrity.py::test_non_vacuity_skipped_substitute_is_flagged` — both fail on
  environment-dependent output-parsing assertions (ANSI-colored terminal output; a pytest `-r`
  skipped-report line format) in files this plan never touched
  (`quirk/errors.py`/`run_scan.py errors`, and pytest's own summary formatting). Verified
  independently via targeted single-test runs before and confirmed present in both full-suite runs
  above — not introduced by this plan.

Net: this plan's failing-node SET is `{test_hardware_staleness, test_errors_cmd,
test_uat_disposition_integrity}`, a superset of the documented one-node inherited baseline by two
nodes that predate and are unrelated to this plan's changes.

## Known Stubs

None. The route has no mock data path — every response is computed from the resolved `FindingItem`
and the real catalog dicts. The six `theme_*`/`finding_position` fields are `None` by design per
this plan's explicit scope boundary (202-05 fills them), not a stub — asserted present-and-null by
a dedicated test.

## Threat Flags

None beyond what the plan's own `<threat_model>` already covers (T-202-07 through T-202-12, T-202-SC).
No new trust boundary, auth path, or schema change beyond the one new read-only GET route the threat
model was authored against.

## Self-Check: PASSED

- FOUND: `quirk/dashboard/api/routes/storyline.py`
- FOUND: `tests/test_dashboard_finding_storyline.py`
- FOUND: `quirk/dashboard/api/schemas.py`, `quirk/dashboard/api/routes/scan.py`, `quirk/dashboard/api/app.py` (modified)
- FOUND: `tests/test_finding_title_bridge.py` (modified — Rule 1 fix)
- FOUND commit `8223d08b` (feat: FindingStoryline schema + shared per-endpoint finding lookup)
- FOUND commit `09056453` (feat: storyline route with catalog-sourced narrative)
- FOUND commit `4be7fc80` (test: disambiguation, narrative presence/absence, auth, 422, fixed 500)
- FOUND commit `e3445cda` (docs: flip 202-03-T1/T2/T3 validation rows to green)
- FOUND commit `350fe0fa` (fix: retarget 202-01's title-bridge extractor)
- `.venv/bin/python -m pytest -q tests/test_dashboard_finding_storyline.py` → 13 passed
- `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py` → 13 passed
- `.venv/bin/python -m compileall -q quirk` → exits 0
- `.venv/bin/python -m pytest -q -m ""` → 3 failed / 4984 passed (all 3 pre-existing/unrelated)

## Confirmation of Override 1

No mutating GSD verb was invoked (`phase.complete`, `milestone.complete`, `requirements
mark-complete`, any `state.*`/`roadmap.*` write verb). `.planning/STATE.md`, `.planning/ROADMAP.md`,
and `.planning/REQUIREMENTS.md` were not touched by this plan. All git operations used plain
`git add` / `git commit` (the gitignored-but-already-tracked `202-VALIDATION.md` staged cleanly
with plain `git add` despite the "ignored paths" hint, per the documented repo gotcha — no `-f`
was actually required this time, confirmed via `git status --short` before committing).
