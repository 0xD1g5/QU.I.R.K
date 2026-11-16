---
phase: 236-score-divergence-closure
plan: 08
subsystem: docs / UAT / vault / closure / CI observation
tags: [d-14, d-15, d-16, d-17, d-18, citruth-03, closure-pending]
requires: [236-01, 236-02, 236-03, 236-04, 236-05, 236-06, 236-07]
provides:
  - "Docs, Series 236 UAT, regenerated guides and vault sync for XSURF-09..14"
  - "Phase 240 hand-off phrase list (D-17) and score-movement note (D-18)"
  - "Staged post-merge closure (LEDGER row 261115-phase236-post-merge-closure)"
affects: [240]
key-files:
  modified:
    - docs/report-interpretation.md
    - docs/operators-guide.md
    - docs/quirk-master-guide.md
    - docs/UAT-SERIES.md
    - docs/uat-coverage-gaps.md
    - docs/doc-claim-ledger.jsonl
    - quantum-chaos-enterprise-lab/expected_results_v3.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - tests/test_score_attribution.py
    - tests/test_finding_derivation_minimal_import.py
    - .planning/LEDGER.md
    - .planning/todos/pending/261108-headline-score-divergence.md
requirements: [XSURF-09, XSURF-10, XSURF-11, XSURF-12, XSURF-13, XSURF-14]
requirements-completed: []
decisions:
  - "Closure pending merge: fixes are only on v529-open, so no requirement, todo or LEDGER status flipped (LEDGER rule 3, T-236-15)"
  - "UAT-228-01 repointed from the retired AST gate node to the behaviour gate node"
metrics:
  tasks: 3
completed: 2026-11-16
---

# Phase 236 Plan 08: Docs, UAT, vault, closure hand-off and CI Summary

Docs, UAT and the vault now describe the closed score divergences, Phase 240 has its exact phrase list, and the requirement/todo/LEDGER closure is staged for the post-merge commit because the fixes are not on main.

## Commits

| Commit | What |
|---|---|
| 2825c61a | docs: report-interpretation, operators guide, Series 236 UAT (6 cases), regenerated master guide and uat-coverage-gaps, doc-claim anchor repair, v3/v4 oracle notes |
| 7a843d3f | docs: 261108 todo `owner: "999.132"` |
| 76e37517 | docs: LEDGER row `261115-phase236-post-merge-closure` (Open 298 -> 299) |
| c81eeb61 | fix: subprocess spawns in two phase 236 tests routed through the fork-safe contract (see Deviations) |
| (metadata) | this SUMMARY, STATE.md, ROADMAP plan list |

## Docs, oracles, UAT, vault

- `docs/report-interpretation.md`: new HIGH rows "Only legacy TLS versions offered (no TLS 1.2+)" and "Weak TLS cipher suites accepted", narrowed LOW "Legacy TLS versions allowed (TLS 1.0/1.1)", and a rewritten dashboard-parity paragraph (two-tier legacy, ECDSA HIGH, container rows on the Findings page, remaining Kerberos/DNSSEC/HTTP-mTLS-pair differences, drift score on the Trends recipe).
- `docs/operators-guide.md`: the same scanner signals under the TLS scanner section. `docs/quirk-master-guide.md` regenerated with `scripts.build_master_guide` (never hand-edited).
- `docs/doc-claim-ledger.jsonl`: DCL-REPORTINT-0459 anchor and claim repaired to the new table row, evidence line numbers refreshed (`findings_evaluator.py:705/707/710`). `tests/test_doc_claim_ledger_gate.py` 71 passed after every doc edit.
- UAT: Series 236, six cases, all PASS on cited nodes (legacy tiers, weak cipher HIGH, ECDSA HIGH, container findings, drift equals Trends, dispositioned remainder). Header `**Last Updated:**` bumped. `docs/uat-coverage-gaps.md` regenerated. `docs/uat-disposition-ledger.jsonl` needed no row: it has no row for any 235.x or 228 case (the corpus tooling does not require one per case). Gates: doc-claim ledger, zero-undispositioned, disposition-integrity, coverage-gaps freshness, worklist reconciliation, master-guide freshness, score-strings freshness, series format: 163 passed.
- UAT-228-01 cited `tests/test_finding_title_bridge.py::test_bridged_pair_severities_match_or_are_dispositioned`, which plan 236-01 retired. `test_substitute_nodes_resolve` caught it; the citation now points at `tests/test_severity_divergence_behaviour.py::test_every_residual_is_dispositioned` and the Notes say so. The Result checkbox is unchanged.
- Oracles checked, outcome:
  - `quantum-chaos-enterprise-lab/expected_results_v4.md` and `_v3.md`: container sections gained a note that the findings now reach the dashboard (live counts not re-measured). Line ~669 "Legacy TLS versions present -9" and ~817 prose unchanged: that driver counts endpoints accepting TLS 1.0/1.1 (`legacy_tls_count`), and no lab profile has a max-legacy host (236-07).
  - `labs/email/expected_results.md`, `labs/broker/expected_results.md`: unchanged. The generic HIGH "Weak TLS cipher suites accepted" fires only for `protocol == "TLS"` rows (`runs_tls_certificate_checks`, exact match), so SMTPS/IMAPS/KAFKA-TLS/AMQPS/REDIS-TLS rows keep only their own "Weak cipher suite on email/broker TLS endpoint" HIGH. "HIGH = 6" (broker) and "HIGH = 3" (email) therefore stand. This is code-derived, not re-measured on a live lab run.
  - `scripts/gen_multihost_oracle_table.py:58` and `lab.sh`: untouched (no profile change); the title map still only names the cipher-suite title.
- Vault: `scripts.sync_vault_guides --write` then `--check` exit 0 (all in-sync); `UAT-Series.md` synced with the frontmatter recipe (and `--check` still in-sync afterwards); phase note `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-236-Score-Divergence-Closure.md` written. Its status is `active`, not the plan's `complete`: the phase is unmerged and unverified.
- `git diff --name-only -- README.md CHANGELOG.md changelog.d` prints nothing (D-17, D-18).

## Phase 240 hand-off (D-17)

Greps run at execution time against current files.

REMOVE (fixed by Phase 236):
- `README.md:161` "Known defects, scores": remove "the legacy TLS version finding, weak cipher suites, undersized ECDSA certificate keys, end-of-life crypto libraries in container images" and "and the drift notification".
- `README.md:119` (Quantum-readiness score bullet): remove "and the scheduled-scan drift notification can show a different score than the dashboard's Trends page".
- `CHANGELOG.md:180-188` (5.28.0 "Known defects", released section, historical): the legacy TLS, weak cipher, undersized ECDSA and container clauses (lines 180-184) and "the drift notification's score, which can disagree with the Trends page" (line 188) are what 5.29.0's text withdraws. A released section is not rewritten; Phase 240 states the withdrawal in the 5.29.0 section.
- `CHANGELOG.md:130-131` (5.28.2 "carried from 5.28.0 that still apply", released): the generic "can still differ" bullet stays historical.

KEEP (not fixed, dispositioned D-19):
- "Kerberos weak-encryption and DNSSEC findings" (`README.md:161`, `CHANGELOG.md:185`), plus "some other report-only high or critical findings" where it names remaining cases.
- "TLS-designated ports" (`README.md:161`, `CHANGELOG.md:187-188`): deferred todo `261015-xsurf-default-report-deriver-drops-tls-designated-ports`.
- "other findings may also differ" (`README.md:161`, `CHANGELOG.md:189`): KEPT. Plan 236-02's operator decision kept the census extra "Unencrypted HTTP service" (HTTP row beside an MTLS_REQUIRED sibling) dispositioned, which keeps the clause under D-17.

Tests to re-point in the same Phase 240 change: `tests/test_changelog_5280_section.py` `_DIVERGENCE_PHRASES` (still has "Quantum-": "undersized ECDSA", which must go when the README wording goes) and `_TODO_DIVERGENCE_PHRASES` (the container-EOL and "Slack drift score vs Trends" entries).

## Score movement (D-18)

SCORING_VERSION stays "4.0"; no changelog.d fragment exists.
- Report scores drop for endpoints with no TLS 1.2+ (TLS 1.0/1.1-only and SSLv2/SSLv3-only), and for endpoints accepting RC4/3DES/NULL/EXPORT/MD5 suites or SSLv2/SSLv3 (new HIGH "Weak TLS cipher suites accepted"). Report scores are otherwise unchanged; TLS 1.0/1.1 alongside TLS 1.2+ is still LOW.
- Dashboard scores drop for ECDSA keys under 256 bits (MEDIUM -> HIGH), for end-of-life OpenSSL / outdated Python `cryptography` in container images (new findings; Pass A replay 42 -> 27), for SSLv2/SSLv3-max endpoints (new HIGH), and rise by a small LOW for legacy offered alongside TLS 1.2+.
- The Slack/notify drift score now follows the Trends page recipe, so drift notifications can differ from before for the same data.
- Pinned per-family headlines (report == dashboard): legacy_max_tls10 62, weak_cipher 63, ecdsa_192 63, container_openssl_111 63, container_openssl_102 31. Live: core 28/28/28, core+registry+dnssec 27/27/27.
- Residual dispositioned differences (score-moving, dashboard-only): Kerberos weak etype, DNSSEC NONE, HTTP beside an mTLS-required sibling.

## Closure pending merge (D-14, LEDGER rule 3)

`git merge-base --is-ancestor <sha> main` is false for every fix commit (checked: 2d8d2d35, 6c4f24d1, 8a414dca, 7ed02587, b4a425a5, 5d18efab; v529-open was never pushed before this plan). So there is no requirement flip, no todo move and no DONE row. The staged edits live in `236-evidence/closure-pending.md` (gitignored phase dir) and are reproduced here so they survive. Owner: LEDGER row `261115-phase236-post-merge-closure` (OPEN, P1, scoring, Source = this SUMMARY).

Fix commits (replace with post-merge main shas when applying): XSURF-09: 2d8d2d35, 045bd805, 6a751dff. XSURF-10/11: 6c4f24d1. XSURF-12: 8a414dca, bd2d6c6a. XSURF-13: 759ee1b7, e63b4b5f, 5d18efab, 7ed02587, b4a425a5. XSURF-14: 03c59e25 (Pass A replay e621fa68, 2dd285fc).

Apply as ONE commit after the merge:
1. `.planning/REQUIREMENTS.md`: XSURF-09..14 `[ ]` -> `[x]` (lines ~30-41) and Pending -> Complete in the six traceability rows (~122-127); verify by hand (mark-complete over-flips).
2. `git mv` from `.planning/todos/pending/` to `.planning/todos/completed/`, each with a `## Resolution` (fix commits, test nodes, score movement from the section above): `261015-xsurf-legacy-tls-severity-diverges-dashboard-vs-report.md` (XSURF-09), `261015-xsurf-weak-cipher-suites-dashboard-high-has-no-report-counterpart.md` (XSURF-10), `261015-xsurf-undersized-ecdsa-report-high-dashboard-medium.md` (XSURF-11), `261015-xsurf-container-library-eol-findings-are-report-only.md` (XSURF-12), `261015-xsurf-dashboard-and-report-pipelines-still-diverge-gate-blind.md` (XSURF-13), `261108-headline-score-divergence.md` (XSURF-14).
3. `.planning/LEDGER.md`: the six matching rows Open -> Closed, DONE, Evidence `main <sha> -- <resolution one-liner and score movement>`, path updated to `todos/completed/`; then set `261115-phase236-post-merge-closure` DONE and fix the section counts.

The three remaining dispositioned divergences (Kerberos, DNSSEC, HTTP+mTLS pair) keep their own todos and LEDGER rows (owner 999.132).

## Test results

- Full suite (`pytest -q -m ""`, foreground-equivalent, basetemp `/Volumes/Digs-1TB/pytest-236-full`) at 76e37517: 9193 passed, 43 skipped, 71 xfailed, 5 xpassed, 1 failed in 915s. The one failure was `tests/test_cli_helper_usage.py::test_no_direct_crash_exposed_subprocess_spawn_in_covered_files`, caused by this phase (two spawn sites, below), fixed in c81eeb61 and re-run green with the two touched files (27 passed). A full-suite re-run after the fix was not repeated; the fix touches only those two test files.

## Deviations from Plan

**1. [Rule 1 - Bug] Fork-safety gate failed on two phase 236 tests.** `tests/test_finding_derivation_minimal_import.py:45` (236-03) used `cwd=` and `tests/test_score_attribution.py:109` (236-01) lacked `close_fds=False`. Fix: the first now uses `tests.cli_helpers.run_fork_safe` with the repo root on PYTHONPATH, the second adds `close_fds=False`. Commit c81eeb61.

**2. [Rule 1 - Bug] UAT-228-01 cited a retired test node** (see above). Citation repointed, Result unchanged. Commit 2825c61a.

**3. Phase note status** is `active`, not `complete` as the plan text said, because the phase is unmerged and unverified.

## CI State (CITRUTH-03)

Recorded after the push in `236-evidence/branch-ci.json` (verbatim `branch_ci_state.py --compare-main` output), copied by the verifier into `236-VERIFICATION.md` as the `ci:` block. This SUMMARY is committed before the observation so HEAD does not move afterwards; the exit code, `head_sha` and run ids are in the orchestrator report and in that JSON. The phase-close commit must sit directly on `head_sha`. Python 3.11 in CI versus local 3.14: a CI-only failure would suggest a 3.12+ API or a locally installed extra.

## Known Stubs

None.

## Threat Flags

None. No embargoed text used; README, CHANGELOG and changelog.d untouched.

## Self-Check

See the orchestrator report; commits 2825c61a, 7a843d3f, 76e37517 and c81eeb61 exist on v529-open.
