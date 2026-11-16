---
phase: 236-score-divergence-closure
plan: 07
subsystem: cross-surface parity tests / live evidence
tags: [XSURF-14, XSURF-09, XSURF-10, XSURF-11, XSURF-12]
requires: [236-01, 236-03, 236-06]
provides:
  - "Five isolated per-family headline parity runs (report == /api/scan/latest == pinned literal)"
  - "Live three-number equality on two fresh lab scans, with attribution clean"
affects: [236-08]
key-files:
  modified:
    - tests/test_cross_surface_parity.py
  created:
    - .planning/phases/236-score-divergence-closure/236-evidence/live-core.txt
    - .planning/phases/236-score-divergence-closure/236-evidence/live-core-registry-dnssec.txt
decisions:
  - "Pins are measured, not derived (D-13)"
metrics:
  tasks: 2
---

# Phase 236 Plan 07: Per-family headline parity and live legs Summary

CI now pins report == dashboard headline per fixed family, and two fresh live lab scans show intel == html == dashboard with no ATTRIBUTED line.

## Task 1: CI parity runs (commit 03c59e25)

`test_xsurf236_family_headline_parity` (legacy_max_tls10, weak_cipher, ecdsa_192, container_openssl_111) and
`test_xsurf236_container_critical_headline_parity` (container_openssl_102). Each seeds its FAMILY_ROWS plus two
healthy TLS rows, isolated run id `_XSURF236_*_RUN_ID`. Measured pins (score, CRITICAL, HIGH):

| family | score | CRIT | HIGH |
|---|---|---|---|
| legacy_max_tls10 | 62 | 0 | 1 |
| weak_cipher | 63 | 0 | 1 |
| ecdsa_192 | 63 | 0 | 1 |
| container_openssl_111 | 63 | 0 | 1 |
| container_openssl_102 | 31 | 1 | 0 |

Test file: 12 passed (5 new, `-k xsurf236` collects 5). `grep -c _XSURF236_` = 12. `_xsurf04_seed_scan_run` unchanged.
Mutation spot-check: dashboard undersized-ECDSA branch severity HIGH -> MEDIUM made
`test_xsurf236_family_headline_parity[ecdsa_192]` fail (1 failed, 4 passed); reverted, `git status quirk/` clean.
compileall exits 0.

## Task 2: Live legs (evidence, not a CI gate)

Fresh scans, serving a sqlite `.backup` snapshot on 127.0.0.1:8612 (worked; no IPv6 fallback needed).

| leg | dashboard | html | intel | SCORE-STRICT | SCORE-PARITY | ATTRIBUTED |
|---|---|---|---|---|---|---|
| core | 28 | 28 | 28 | PASS | equal | none |
| core + registry + dnssec | 27 | 27 | 27 | PASS | equal | none |

Core: 1 CRITICAL (expired cert) + 1 HIGH (self-signed) on both surfaces; vacuous for the four fixed conditions
(RESEARCH Pitfall 7). Wider leg: container EOL live (OpenSSL 1.0.x CRITICAL x2, 1.1.x HIGH x2, cryptography 2.9.2
HIGH x2) plus DNSSEC; the CRITICAL ceiling (27) masks HIGH-driven differences there, so per-family CI runs are the
HIGH-sensitive proof (dashboard HIGH 11 vs report HIGH 5 reflects the dispositioned DNSSEC/identity differences).

Fixture-only: weak generic-TLS ciphers, undersized ECDSA and legacy-max TLS exist in no lab profile; proven by CI
fixtures only. Lab down and no server left after each leg; canonical `./quirk-output/quirk.db` never opened.

## Deviations from Plan

XSURF-04 seeder deliberately not extended (SAML CRITICAL ceiling masks HIGHs); D-13's "extend
test_xsurf04_three_number_cross_surface_equality" is met by sibling isolated runs in the same file.
Leg 1 used `PROFILE_ARGS="--profile core"` because lab `.env` sets PROFILE_ARGS and an empty value falls back to it;
no compose service carries a `core` profile, so the unprofiled default set ran. Wider leg also set `dnssec_targets`
weak/unsigned/broken.chaos.local with resolver 127.0.0.1:15353 (broken zone not asserted).

## Open verification gaps

None for the plan criteria. No live leg isolates legacy-max TLS (tls-legacy offers more than TLS 1.0 only).

## Self-Check: PASSED
Commit 03c59e25 present; evidence files present under 236-evidence/.

## Orchestrator correction

Orchestrator correction (2026-11-16, re-derived from /Volumes/Digs-1TB/pytest-236-evidence/core-registry-dnssec/latest.json):
the scored dashboard `findings` list is CRITICAL 3 / HIGH 8 (Certificate expired; 2x EOL OpenSSL 1.0.x; 2x EOL
OpenSSL 1.1.x; 2x Severely outdated Python cryptography 2.9.2; TLS certificate is self-signed; 3x "DNSSEC: NONE").
Against the report (CRITICAL 3 / HIGH 5) the multiset difference is exactly 3x "DNSSEC: NONE" (dashboard_only),
the D-19 dispositioned key. The "HIGH 11" above also counted the separate identity_findings / dar_findings panels,
which are not in the scored findings set. No undispositioned live divergence.
