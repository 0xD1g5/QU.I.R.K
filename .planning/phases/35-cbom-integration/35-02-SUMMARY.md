---
phase: 35-cbom-integration
plan: 02
subsystem: cbom
type: tdd
wave: 2
status: complete
tags: [cbom, tdd, green-phase, motion, broker, plaintext, builder]
requires:
  - tests/test_cbom_motion_endpoints.py
provides:
  - quirk/cbom/builder.py (Pass 2 + Pass 3 skip plaintext brokers)
affects:
  - CBOM output for KAFKA-PLAIN / AMQP-PLAIN / REDIS-PLAIN endpoints
tech-stack:
  added: []
  patterns:
    - explicit-skip-tuple
    - defense-in-depth-cert-guard
key-files:
  created:
    - .planning/phases/35-cbom-integration/35-02-SUMMARY.md
  modified:
    - quirk/cbom/builder.py
decisions:
  - D-01-applied: grouped insertion at end of each tuple with v4.4-motion comment line
  - D-02-applied: Pass 1 untouched (default branch already correct via falsy cipher/cert guards)
metrics:
  duration_seconds: 90
  completed: 2026-04-28
  tasks_completed: 1
  files_changed: 1
  tests_added: 0
  tests_flipped_to_green: 3
---

# Phase 35 Plan 02: CBOM Plaintext-Broker Skip GREEN Summary

GREEN-phase production change for Phase 35: extends the Pass 2 cert-skip tuple
and Pass 3 protocol-skip tuple in `quirk/cbom/builder.py` with the three v4.4
motion plaintext broker labels — `KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN` —
closing the Pass 3 ghost-protocol-component leak locked by Plan 01. This is
the only production code change in Phase 35.

## What Was Built

Two tuple-line additions in `quirk/cbom/builder.py` (6 lines added, 2 lines
modified — `git diff --stat`: `1 file changed, 6 insertions(+), 2 deletions(-)`).

### Pass 2 — Cert components (line 436)

Appended grouping at end of skip tuple:

```python
# v4.4 motion plaintext brokers — no TLS cert (Phase 35 / CBOM-03)
"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"
```

Hardens an already-correct behavior — the existing `if not ep.cert_pubkey_alg:
continue` guard at line 442 was already short-circuiting plaintext brokers
(per Plan 01 deviation analysis). The explicit skip is now defense-in-depth.

### Pass 3 — Protocol components (line 519)

Appended same grouping at end of skip tuple:

```python
# v4.4 motion plaintext brokers — no TLS protocol component (Phase 35 / CBOM-03)
"KAFKA-PLAIN", "AMQP-PLAIN", "REDIS-PLAIN"
```

This is the actual leak fix — Pass 3 had no falsy guard, so its default-TLS
branch was unconditionally emitting `crypto/protocol/tls/{host}:{port}` bom_refs
for plaintext brokers despite their having no cipher suite, no TLS version,
and no cert. The skip tuple addition stops the leak.

## Test Evidence

```
$ python -m pytest tests/test_cbom_motion_endpoints.py -v
============================== 19 passed in 0.18s ==============================

$ python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py \
                   tests/test_cbom_writer.py tests/test_cbom_integration.py
============================== 74 passed in 0.33s ==============================
```

| Coverage | Tests | Plan 01 RED | Plan 02 GREEN |
|---|---|---|---|
| CBOM-01 — email TLS labels emit protocol + cert | 6 | PASS | PASS |
| CBOM-02 — broker TLS labels (incl. AMQPS/Azure-ServiceBus) | 4 | PASS | PASS |
| CBOM-03 — plaintext skipped from cert pass | 3 | PASS (incidental) | PASS (explicit + guard) |
| CBOM-03 — plaintext skipped from protocol pass | 3 | **FAIL (RED)** | **PASS (GREEN)** |
| CBOM-04 — cipher-suite quantum-safety verifications | 3 | PASS | PASS |
| **TOTAL** | **19** | **16/3** | **19/0** |

Grep verification on the modified file:

```
$ grep -c '"KAFKA-PLAIN"' quirk/cbom/builder.py    → 2
$ grep -c '"AMQP-PLAIN"'  quirk/cbom/builder.py    → 2
$ grep -c '"REDIS-PLAIN"' quirk/cbom/builder.py    → 2
```

## Deviations from Plan

### Predicted RED split was 6 fails, observed (carried from Plan 01) was 3 fails

**Found during:** Plan 01 verification (already documented in `35-01-SUMMARY.md`
§Deviations) — surfaces here because Plan 02's frontmatter
(`must_haves.truths[2]`) and `<objective>` text both predicted "6 RED tests
turn GREEN".

**Issue:** Plan 02 was authored expecting all 6 plaintext-broker tests
(3 cert-pass + 3 protocol-pass) to be RED before this plan landed. In reality,
the 3 cert-pass tests were already PASSING in Plan 01 because
`quirk/cbom/builder.py` Pass 2 has a pre-existing `if not ep.cert_pubkey_alg:
continue` falsy guard at line 442 that incidentally skips plaintext brokers
(whose `cert_pubkey_alg` is `None`). The actual RED count entering Plan 02
was therefore **3** (Pass 3 protocol leaks only), not 6.

**Plan-text vs plan-intent:** the literal "flip 6 RED to GREEN" wording is
stale, but the plan's **intent** — "extend both skip tuples with the 3
plaintext labels per D-01 / CBOM-03" — is correct and unchanged. The
Pass 2 edit hardens an already-correct behavior to defense-in-depth; the
Pass 3 edit closes the genuine leak. Both edits are still required by the
contract Plan 01 locked, and both edits are the exact lines the plan body
prescribes.

**Action taken:** Implemented the plan's `<action>` block verbatim (both
Pass 2 and Pass 3 tuple expansions, identical comment-grouped insertion).
Did **not** widen scope. Did **not** modify any test. The GREEN criterion
is satisfied: 19/19 in `test_cbom_motion_endpoints.py`, 0 regressions in
the four existing CBOM test files (74/74).

**Files modified:** `quirk/cbom/builder.py` only.
**Commit:** `b76c818`

## Authentication Gates

None.

## Decisions Made

- Honored D-01: grouped insertion at the *end* of each tuple with a single
  comment line ("v4.4 motion plaintext brokers — ... Phase 35 / CBOM-03"),
  preserving git-blame clarity and signaling co-locality of the three labels.
- Honored D-02: Pass 1 untouched. The default-TLS algorithm-registration
  branch in Pass 1 already short-circuits on `cipher_suite=None` /
  `cert_pubkey_alg=None`, so plaintext brokers register zero algorithms there.
  No defensive scope creep (DEF-35-A explicitly deferred per plan).
- Kept the Pass 2 explicit skip even though the falsy guard already covers
  plaintext brokers — defense-in-depth and matches the plan's must_haves.

## Verification

- [x] `python -m compileall quirk/cbom/builder.py` — clean (no syntax errors)
- [x] `python -m pytest tests/test_cbom_motion_endpoints.py -v` — **19 passed, 0 failed**
- [x] `python -m pytest tests/test_cbom_builder.py tests/test_cbom_classifier.py tests/test_cbom_writer.py tests/test_cbom_integration.py` — **74 passed, 0 failed**
- [x] `grep -c '"KAFKA-PLAIN"' quirk/cbom/builder.py` → **2**
- [x] `grep -c '"AMQP-PLAIN"'  quirk/cbom/builder.py` → **2**
- [x] `grep -c '"REDIS-PLAIN"' quirk/cbom/builder.py` → **2**
- [x] `git diff --stat quirk/cbom/builder.py` (pre-commit) → 6 insertions, 2 deletions (tuple-close paren lines retouched)
- [x] No test file modified
- [x] No classifier file modified
- [x] No Pass 1 modification

## Commits

- `b76c818` — feat(35-02): skip plaintext brokers in CBOM Pass 2 + Pass 3

## Self-Check: PASSED

Verified files:
- FOUND: quirk/cbom/builder.py (modified)
- FOUND: .planning/phases/35-cbom-integration/35-02-SUMMARY.md
- FOUND commit: b76c818

## TDD Gate Compliance

RED gate: `test(35-01): add RED ...` commit `d99ddd2` (Plan 01).
GREEN gate: `feat(35-02): skip plaintext brokers ...` commit `b76c818` (this plan).
REFACTOR gate: not needed — change is a 2-line tuple expansion with no
duplication / cleanup opportunity. Phase 35 production code change is
COMPLETE after this plan; remaining Phase 35 plans are verification,
snapshot, and docs only.
