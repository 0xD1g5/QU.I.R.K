---
phase: 79-smime-ldap-discovery-scanner
plan: 04
subsystem: tests / phase-closure
tags: [smime, tests, ast-gate, privacy-invariant, phase-closure, v4.10]
requires: [79-01, 79-02, 79-03]
provides:
  - "tests/test_smime_scanner.py — 6 unit tests against mocked ldap3 + 3 DER fixtures"
  - "tests/test_smime_no_envelope_leak.py — 2 SMIME-04 privacy invariant tests"
  - "tests/test_smime_ast_gate.py — 3 SMIME-08 AST gate tests (real-target + positive + negative self-tests)"
  - "tests/fixtures/smime/{alice,bob,carol}.der — byte-identical copies of chaos lab fixtures"
  - "docs/UAT-SERIES.md — 3 new UAT-79-* test cases (SMIME-01/02/05/06, SMIME-04, SMIME-08)"
  - "Obsidian phase note at 20_Dev-Work/QUIRK/Phases/Phase-79-SMIME-LDAP-Discovery-Scanner.md"
affects:
  - tests/
  - docs/UAT-SERIES.md
key_files:
  created:
    - tests/test_smime_scanner.py
    - tests/test_smime_no_envelope_leak.py
    - tests/test_smime_ast_gate.py
    - tests/fixtures/smime/alice.der
    - tests/fixtures/smime/bob.der
    - tests/fixtures/smime/carol.der
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-79-SMIME-LDAP-Discovery-Scanner.md
  modified:
    - docs/UAT-SERIES.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md
requirements:
  - SMIME-04
  - SMIME-08
decisions:
  - "Patch `LDAP3_AVAILABLE` flag in tests alongside `_bind_and_search` so the suite runs without the optional `[identity]` extra installed in CI's base Python env"
  - "AST gate forbidden set: {imaplib, poplib, smtplib, email} + ImportFrom prefix `email.` — catches all four IMAP/SMTP/POP/envelope import shapes"
  - "Test serialiser walks public string fields of CryptoEndpoint (host, port, protocol, service_detail, severity, cert_pubkey_alg, cert_sig_alg, scan_error, smime_scan_json) — single source for the sentinel-absence assertion"
metrics:
  duration: ~18 min
  tasks: 5
  tests_added: 11
  fixtures_added: 3
  files_created: 7
  files_modified: 2
  completed: 2026-05-16
---

# Phase 79 Plan 04: Tests + AST Gate + Phase Closure — Summary

Closed Phase 79 by locking the SMIME scanner contract behind 11 pytest
tests (6 unit + 2 privacy invariant + 3 AST gate), copying the chaos-lab
DER fixtures into the test tree so unit tests stay hermetic, and
executing the CLAUDE.md mandatory phase closure (UAT-SERIES.md update +
Obsidian phase note).

## What Was Built

### 1. `tests/test_smime_scanner.py` (6 tests, all green)

Patches both `quirk.scanner.smime_scanner.LDAP3_AVAILABLE` and
`_bind_and_search` so unit tests run with no `ldap3` dependency
installed (the `[identity]` extra is not in the base CI env). Builds
synthetic `searchResEntry` dicts whose `raw_attributes` carry one of
the three DER fixtures, then asserts the Phase 79-02 contract:

| Fixture | Key | Sig | Expected | Asserted |
|---|---|---|---|---|
| `alice.der` | RSA-1024 | SHA-1 | HIGH + 2 reasons | `severity="HIGH"`, `reasons ⊇ {weak-signing-alg, weak-rsa-key}` |
| `bob.der`   | RSA-1024 | SHA-256 | HIGH + 1 reason | `severity="HIGH"`, `weak-rsa-key ∈ reasons`, `weak-signing-alg ∉ reasons` |
| `carol.der` | RSA-2048 | SHA-256 | SAFE | 0 endpoints |

Plus three additional tests:
- `test_three_fixtures_together_produce_two_high_findings` — end-to-end
  multi-entry assertion (`{alice, bob} → HIGH`, `carol → suppressed`).
- `test_user_certificate_attribute_also_picked_up` — SMIME-01 both-attr
  contract via `userCertificate` (not just `userSMIMECertificate`).
- `test_no_entries_yields_no_endpoints` — empty paged-search → no crash.

Every emitted `CryptoEndpoint` is verified to carry `protocol="SMIME"`
and a populated `smime_scan_json` (which JSON-parses cleanly).

### 2. `tests/test_smime_no_envelope_leak.py` (SMIME-04, 2 tests)

Privacy invariant. Builds a `SimpleNamespace` target carrying four
sentinel IMAP-style envelope fields:

```python
SimpleNamespace(
    host="ldap.example.com",
    port=389,
    realm="QUIRK.LAB",
    to="SENTINEL_TO_FIELD",
    from_="SENTINEL_FROM_FIELD",
    subject="SENTINEL_SUBJECT_FIELD",
    message_id="SENTINEL_MESSAGEID_FIELD",
)
```

Runs the scanner end-to-end with both `carol.der` (SAFE → zero
endpoints) AND `alice.der` (HIGH → endpoint with populated
`smime_scan_json`), then walks every public string field of every
returned endpoint and asserts NONE of the sentinel strings surface.
The HIGH path also asserts the JSON blob parses and the sentinels are
not present in the parsed structure either.

### 3. `tests/test_smime_ast_gate.py` (SMIME-08, 3 tests)

AST gate cloning the structural shape of
`tests/test_scan_error_gate.py`:

```python
FORBIDDEN_MODULES = {"imaplib", "poplib", "smtplib", "email"}
FORBIDDEN_FROM_PREFIXES = ("email.",)
```

Walks `ast.parse(quirk/scanner/smime_scanner.py)`, collects every
`ast.Import` / `ast.ImportFrom` matching the forbidden set, and fails
with a path+import list when any are found. Plus:

- **Positive self-test** — synthetic source with all 4 plain forbidden
  imports + 2 `from email.* import` shapes; gate must produce exactly 6
  violations.
- **Negative self-test** — synthetic clean source mirroring the real
  module's legitimate `ldap3` / `cryptography` / `quirk.*` imports;
  gate must produce zero violations.

### 4. DER fixtures (`tests/fixtures/smime/`)

Three files copied byte-identical from
`quantum-chaos-enterprise-lab/smime/certs/`:

```
tests/fixtures/smime/alice.der  618 B  RSA-1024 SHA-1     HIGH
tests/fixtures/smime/bob.der    614 B  RSA-1024 SHA-256   HIGH
tests/fixtures/smime/carol.der  879 B  RSA-2048 SHA-256   SAFE
```

Same regen source as the chaos lab — both test suite and lab oracle
agree on the cryptographic surface.

### 5. `docs/UAT-SERIES.md` (3 new test cases)

Appended a new "Phase 79 — S/MIME LDAP Discovery Scanner" section after
the Phase 78 block, with three UAT cases:

- **UAT-79-01** — Run `smime` chaos lab profile end-to-end (SMIME-01/02/05/06)
- **UAT-79-02** — Verify SMIME-04 privacy invariant (envelope-leak test)
- **UAT-79-03** — Verify SMIME-08 AST gate (drift prevention)

`**Last Updated:**` bumped to 2026-05-16.

### 6. Obsidian phase note

Written directly to vault filesystem (file > shell-arg limit, so
Obsidian CLI `content=` is unsafe):

```
/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-79-SMIME-LDAP-Discovery-Scanner.md
```

Frontmatter `status: complete`, Goal verbatim from ROADMAP, Requirements
Covered (SMIME-01..08), Success Criteria (the five ROADMAP truths),
What Was Built (one subsection per plan 79-01..79-04 sourced from the
four SUMMARY.md files), Notes (Phase 83 invariant red + LDAPS deferral),
Related wikilinks.

## AST gate forbidden-import set

| Module / prefix | Why forbidden |
|---|---|
| `imaplib` | IMAP envelope access (the canonical "we touched mailbox content" signal) |
| `poplib` | POP3 envelope access |
| `smtplib` | SMTP envelope access |
| `email` | top-level stdlib email envelope package |
| `email.*` (ImportFrom prefix) | `email.message`, `email.header`, `email.parser`, etc. |

Current `quirk/scanner/smime_scanner.py` violations: **0**.

## Verification

```
$ pytest tests/test_smime_scanner.py tests/test_smime_no_envelope_leak.py \
         tests/test_smime_ast_gate.py -x -v
======================== 11 passed in 0.10s ========================

$ python -m compileall quirk/ tests/
# exit 0, no errors
```

Full-suite sweep confirmed `tests/test_score_weights_invariant.py`
remains the documented expected red (count drift 29→32, sum drift
261.0→267.0) — Phase 83 CLEAN-01 owns the consolidated bump after
Phase 80 also lands its weight (D-79-R3). Pre-existing 13 collection
errors caused by multiple stray `quirk.db` files in the workspace
(`/quirk.db`, `/output/quirk.db`, `/quirk-output/quirk.db`,
`/.planning/quirk.db`, `/data/quirk.db`) are out-of-scope —
they preceded Plan 79-04 and are unrelated to SMIME work.

## Commits

| # | SHA | Subject |
|---|---|---|
| 1 | `__CODE_SHA__` | `feat(79-04): smime unit tests + privacy invariant + ast gate (SMIME-04, SMIME-08)` |
| 2 | `__UAT_SHA__`  | `docs(phase-79): update UAT-SERIES.md` |

(SHAs filled in post-commit; this file is amended into commit #1.)

## Deviations from Plan

### Auto-fixed

**1. [Rule 3 — blocking] Test suite requires LDAP3_AVAILABLE patch**
- **Found during:** Task 1 first pytest run
- **Issue:** The base CI/dev Python env does NOT have the `[identity]`
  extra installed; `import ldap3` fails inside the scanner module so
  `LDAP3_AVAILABLE` is False at import time. The scanner short-circuits
  with `return []` before reaching `_bind_and_search`, defeating every
  patched test.
- **Fix:** Added `patch.object(smime_scanner, "LDAP3_AVAILABLE", True)`
  alongside the `_bind_and_search` patch in every helper. Pure test-side
  fix; the scanner's runtime guard is unchanged.
- **Files modified:** `tests/test_smime_scanner.py`, `tests/test_smime_no_envelope_leak.py`
- **Commit:** code/test commit

### Out of scope (logged, NOT fixed)

**Pre-existing test-collection errors from multiple stray DB files**
- 13 test files raise `ValueError: Multiple QU.I.R.K. DBs found` at
  collection time. The cause is stale `quirk.db` files at five paths
  in the workspace, all predating Plan 79-04. Per scope boundary, not
  fixed in this plan.

## Self-Check

- `tests/test_smime_scanner.py` — FOUND, 6 tests, all PASS ✓
- `tests/test_smime_no_envelope_leak.py` — FOUND, 2 tests, all PASS ✓
- `tests/test_smime_ast_gate.py` — FOUND, 3 tests, all PASS ✓
- `tests/fixtures/smime/alice.der` (618 B) — FOUND ✓
- `tests/fixtures/smime/bob.der` (614 B) — FOUND ✓
- `tests/fixtures/smime/carol.der` (879 B) — FOUND ✓
- `docs/UAT-SERIES.md` — contains `UAT-79-01..03` rows; `**Last Updated:** 2026-05-16` ✓
- Obsidian vault note — FOUND at expected path ✓
- `python -m compileall quirk/ tests/` — exit 0 ✓
- Phase 79 expected red `test_score_weights_invariant` confirmed; Phase 83 owns bump ✓

## Self-Check: PASSED
