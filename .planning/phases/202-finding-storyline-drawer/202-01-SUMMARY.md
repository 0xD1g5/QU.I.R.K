---
phase: 202-finding-storyline-drawer
plan: 01
subsystem: dashboard-cli-bridge
tags: [findings, remediation, title-bridge, gate]
dependency-graph:
  requires: []
  provides: [finding_title_bridge.canonical_cli_title, finding_title_bridge.DASHBOARD_TITLE_BRIDGE,
             finding_title_bridge.UNBRIDGED_DASHBOARD_TITLES, finding_title_bridge.BRIDGE_REACHABILITY]
  affects: [202-02, 202-03, 202-05]
tech-stack:
  added: []
  patterns: ["run-time source-scan gate (regenerates occurrence sets from installed source, no hand-written lists)"]
key-files:
  created:
    - quirk/dashboard/api/finding_title_bridge.py
    - tests/test_finding_title_bridge.py
  modified:
    - .planning/phases/202-finding-storyline-drawer/202-VALIDATION.md
decisions:
  - "Weak-cipher-suites and Quantum-{label}-algorithm dashboard classes are confirmed UNBRIDGED (different firing fields / no 1:1 CLI granularity), falsifying research's implicit 'divergent but translatable' framing for those two classes"
  - "catchall-only reachability class is real (undersized RSA key) and per D-09 must be rendered, not suppressed to A1 — flagged for 202-03/202-05"
metrics:
  duration: "~35 min"
  completed: 2026-09-12
---

# Phase 202 Plan 01: Finding-Title Bridge Summary

Built `quirk/dashboard/api/finding_title_bridge.py` — the pure-data translation layer from the
dashboard's finding-title vocabulary to the CLI pipeline's canonical titles, the only vocabulary
`RemediationItemFingerprint` rows are ever written from — plus a run-time source-scan gate
(`tests/test_finding_title_bridge.py`) that regenerates both vocabularies' occurrence sets from
installed source on every run, so this ledger cannot silently go stale the way five prior
hand-maintained-list "safeguards" in this repo have (per CLAUDE.md).

## Per-Class Verification Table

Both generators' actual `if`/`elif` conditions and endpoint fields were read directly (not
title-name similarity). All 9 `_derive_findings()` emission sites (`quirk/dashboard/api/routes/scan.py:137-329`)
plus the identity-findings family are accounted for:

| # | Dashboard title (site) | Dashboard firing condition | Candidate CLI title (site) | CLI firing condition | Verdict |
|---|---|---|---|---|---|
| 1 | `Unencrypted HTTP service` (scan.py:137-151) | `ep.protocol.upper() == "HTTP"` | `Plaintext HTTP service detected` (findings_evaluator.py:537-549) | `proto == "HTTP"` | **bridged** — same field, same comparison |
| 2 | `Legacy TLS version: {v}` (scan.py:154-168) | `ep.tls_version in ("TLSv1","TLSv1.1","TLS 1.0","TLS 1.1")` | `Legacy TLS versions allowed (TLS 1.0/1.1)` (findings_evaluator.py:551-565, via `_has_legacy_tls_versions`) | `ep.tls_version in {"TLSv1","TLSv1.1"}` OR intersection with `tls_supported_versions` | **bridged** — same primary field (`tls_version`); CLI condition is a superset (also reads `tls_supported_versions`), dashboard also matches spaced forms. Overlapping, not byte-identical, but same concept and same field |
| 3 | `Weak cipher suites enabled` (scan.py:171-185) | `ep.tls_weak_ciphers_present` | `Legacy TLS cipher suites accepted` (findings_evaluator.py:568-584) | `ep.tls_legacy_suites_present` | **unbridged (confirmed)** — two DISTINCT, independently-populated boolean columns (`quirk/models.py:45-46`; `quirk/scanner/tls_scanner.py:323-324` sets both from different capability checks in the same scan). They can and do disagree on a given endpoint |
| 4 | `Certificate expired` (scan.py:188-207) | `days_to_expiry < 0` (from `cert_not_after`) | `TLS certificate expired` (findings_evaluator.py:586-608) | `na < now_naive` (same field) | **bridged** — same field, same comparison direction |
| 5 | `Certificate expiring in {n} day(s)` (scan.py:208-222) | `0 <= days_to_expiry < 30` | `TLS certificate expiring within 30 days` (findings_evaluator.py:609-624) | `now_naive <= na < now_naive + 30d` | **bridged** — same field, same 30-day window |
| 6 | `TLS certificate uses undersized RSA key` (scan.py:230-255) | `cert_pubkey_alg.upper().startswith("RSA") and cert_pubkey_size < 2048` | same title (findings_evaluator.py:676-697) | `cert_pubkey_alg.upper() == "RSA" and cert_pubkey_size < 2048` | **identity** — byte-identical title; near-identical condition (`startswith` vs exact `==`, immaterial in practice) |
| 7 | `TLS certificate is self-signed` (scan.py:263-286) | `issuer and subject and issuer == subject` | same title (findings_evaluator.py:634-652) | byte-identical condition | **identity** |
| 8 | `TLS certificate issued by untrusted CA` (scan.py:287-307) | `issuer and subject and issuer != subject and _chain_verified(ep) is False` | same title (findings_evaluator.py:653-671) | byte-identical condition | **identity** |
| 9 | `Quantum-{label} algorithm: {alg}` (scan.py:309-331) | `cert_pubkey_alg` truthy, NOT startswith `"RSA"` — covers EVERY non-RSA alg the CBOM classifier scores Vulnerable/At-Risk (DSA, DH, Ed25519, ECDSA of any size), ONE title regardless of size | ECDSA-specific sites only (findings_evaluator.py:716-753) | `cert_pubkey_alg.upper() == "ECDSA"`, split into TWO size-gated titles the dashboard does not distinguish; no site at all for DSA/DH/Ed25519 | **unbridged (confirmed)** — no 1:1 CLI equivalent at any granularity, even restricted to the ECDSA subset |
| — | KERBEROS/SAML/DNSSEC identity family (appended separately at scan.py:1641 from `_derive_identity_findings()`, `id=None`) | n/a — out of `_derive_findings()` scope entirely | n/a | n/a | **unbridged** (out of gate scope by construction — no CLI identity-protocol titles exist in `findings_evaluator.py`) |

## Agreement / Disagreement with RESEARCH's Count

`202-RESEARCH.md` reported "~5 of 9 TLS classes diverge, 3 match verbatim" with MEDIUM confidence
and explicitly flagged that the 1:1 per-condition correspondence (its Assumption A4) was "not
verified by running both."

**Verified independently, condition-by-condition:**
- **3 match verbatim** (rows 6-8 above: undersized-RSA, self-signed, untrusted-CA) — **agrees**
  with research's count.
- Of the remaining 6 "diverging" titles, only **4 are safely bridgeable** (rows 1, 2, 4, 5: HTTP,
  legacy-TLS-version, cert-expired, cert-expiring) because their firing conditions genuinely align
  on the same endpoint field.
- **The other 2 are NOT bridgeable at all** (rows 3, 9: weak-cipher-suites, quantum-algorithm) —
  their firing conditions read **different fields** (`tls_weak_ciphers_present` vs
  `tls_legacy_suites_present`) or cover **structurally different sets of algorithms/granularity**
  (dashboard's one non-RSA branch vs CLI's ECDSA-only, size-split branches).

**Disagreement:** research's framing implicitly treats all "~5 diverging" classes as translatable
(just with different wording); this re-verification found that **2 of those 5 diverge on
condition, not just wording**, and must be dispositioned `unbridged` rather than translated. This
confirms — rather than falsifies — the plan's own "suspect unbridged" hypothesis for exactly those
two rows. A confidently wrong bridge for either would have attributed one condition's theme (and
lift) to a genuinely different condition (T-202-01).

Final ledger: `DASHBOARD_TITLE_BRIDGE` has 7 entries (4 differently-worded-but-bridged + 3
identity self-maps), `UNBRIDGED_DASHBOARD_TITLES` has 2 entries.

## Gate: RED Demonstrations

Both RED demonstrations were performed manually against the real files, with the suite run before
and after, and `git status --short` confirmed clean afterward.

**RED 1 — deleted the `"Certificate expired"` ledger entry** from `DASHBOARD_TITLE_BRIDGE`:

```
E   AssertionError: scan.py line 199: dashboard title/prefix 'Certificate expired' has NO
    disposition -- add an entry to DASHBOARD_TITLE_BRIDGE or UNBRIDGED_DASHBOARD_TITLES in
    quirk/dashboard/api/finding_title_bridge.py
FAILED tests/test_finding_title_bridge.py::test_every_dashboard_emission_site_is_dispositioned
FAILED tests/test_finding_title_bridge.py::test_bridge_reachability_covers_every_bridge_value_no_gaps_no_extras
2 failed, 11 passed
```

Named the exact source line (199) and the fix. The reachability test also correctly cascaded-failed
(a stale `BRIDGE_REACHABILITY` entry pointing at a now-undefined bridge value). Restored via
backup; re-ran suite: `13 passed`. `git status --short` showed only the two new plan files
untracked — clean.

**RED 2 — injected a fake `title="Bogus new finding"` line inside `_derive_findings`** (via a dead
`if False:` branch, at line 137):

```
E   AssertionError: scan.py line 137: dashboard title/prefix 'Bogus new finding' has NO disposition
    -- add an entry to DASHBOARD_TITLE_BRIDGE or UNBRIDGED_DASHBOARD_TITLES in
    quirk/dashboard/api/finding_title_bridge.py
FAILED tests/test_finding_title_bridge.py::test_every_dashboard_emission_site_is_dispositioned
1 failed, 12 passed
```

Named the exact injected line number (137). Restored `scan.py` from backup; re-ran suite:
`13 passed`. `git status --short` showed only the two new plan files untracked — clean.

Minimum-count vacuous-pass guards are present (`>= 9` dashboard sites, `>= 10` CLI sites) and pass
against the real files (9 and ~13 respectively, confirmed by the extractor tests).

## Reachability Census (Task 3, D-08/D-09)

Recomputed at test-run time from `REMEDIATION_CONSTITUENCY` + each dashboard site's literal
`severity=` — never asserted against a hand-written string:

| CLI title | Constituency | Dashboard severity | Reachability |
|---|---|---|---|
| `Plaintext HTTP service detected` | in `plaintext-http-exposure` fingerprint tuple | HIGH | **specific** |
| `Legacy TLS versions allowed (TLS 1.0/1.1)` | in `legacy-tls-versions` fingerprint tuple | HIGH | **specific** |
| `TLS certificate expired` | in `expired-certificates` fingerprint tuple | CRITICAL | **specific** |
| `TLS certificate expiring within 30 days` | in `near-expiry-certificates` fingerprint tuple | HIGH | **specific** |
| `TLS certificate is self-signed` | in `self-signed-certificates` fingerprint tuple | HIGH | **specific** |
| `TLS certificate uses undersized RSA key` | in NO fingerprint tuple | HIGH | **catchall-only** |
| `TLS certificate issued by untrusted CA` | in NO fingerprint tuple | MEDIUM (below HIGH/CRITICAL) | **unreachable** |

All three reachability classes (`specific`, `catchall-only`, `unreachable`) are represented — the
census is not vacuous.

**Flagged open question (not decided here, per D-08/D-09):** `TLS certificate uses undersized RSA
key` is `catchall-only` — its ONLY theme is the `high-impact-findings` severity catch-all. Per D-09
(operator-confirmed 2026-09-12), plan 202-03/202-05 should **render** the catch-all theme for this
class rather than suppress it to absence case A1 — suppressing it would assert a FALSE absence for
a finding that genuinely has a real lift via the catch-all. This is exactly D-09's own worked
example, reproduced independently here from the data rather than assumed from the CONTEXT text.
202-05 consumes `BRIDGE_REACHABILITY` directly for this branch.

## Deviations from Plan

None beyond the two RED-demonstration probe edits (temporary, reverted, confirmed clean via
`git status --short`) and one test-authoring correction: an initial identity-family scoping test
asserted `"Kerberos"/"SAML"/"DNSSEC"` did not appear anywhere in `_derive_findings`' sliced body,
but `_derive_findings` legitimately references those three literals once, in its own skip-guard
(`if proto in {"KERBEROS", "SAML", "DNSSEC"}: continue`) — not a title-emission site. Rule 1 (bug
in my own new test, not in production code): narrowed the assertion to check only the extracted
`title=` sites' resolved prefixes, not the raw source text, which is what the test actually needed
to prove.

## Known Stubs

None. No hardcoded empty values, no placeholder UI text — this plan ships a pure data module and
its test gate, no rendering surface.

## Threat Flags

None. No new network endpoints, auth paths, file-access patterns, or schema changes — matches the
plan's own threat model (pure in-process module; test reads its own two known source files).

## Self-Check: PASSED

- FOUND: `quirk/dashboard/api/finding_title_bridge.py`
- FOUND: `tests/test_finding_title_bridge.py`
- FOUND commit `4b3ec456` (feat: bridge ledger)
- FOUND commit `3bd096f7` (test: gate + reachability census)
- FOUND commit `bbab3157` (docs: VALIDATION.md rows flipped)
- `.venv/bin/python -m pytest -q tests/test_finding_title_bridge.py` → 13 passed
- `.venv/bin/python -m compileall -q quirk` → exits 0
- `git status --short` → clean (only this SUMMARY.md pending, to be committed next)
