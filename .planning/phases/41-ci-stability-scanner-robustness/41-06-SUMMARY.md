---
phase: 41-ci-stability-scanner-robustness
plan: 06
subsystem: docs+chaos-lab
tags: [docs, configuration, audit, lab-sh, profile-sweep, ROBUST-04, D-10, D-18]

requires:
  - phase: 41-ci-stability-scanner-robustness
    plan: 02
    provides: TimeoutsCfg/RetryCfg dataclass field set + deprecation aliases
  - phase: 41-ci-stability-scanner-robustness
    plan: 03
    provides: scanners read from canonical cfg.scan.timeouts.* slots
provides:
  - "docs/configuration.md §'Timeout & Retry Policy (v4.5+)' — full sub-table + deprecation + D-10 upper-bound formula"
  - "docs/timeout-retry-audit.md — ROBUST-04 audit table mapping every scanner to its canonical timeout/retry slot"
  - "lab.sh down + reset arms sweep profile-tagged services via --profile \"*\" --remove-orphans"
affects: [41-07]

tech-stack:
  added: []
  patterns:
    - "Markdown audit-table doc citing canonical dataclass field as source-of-truth"
    - "docker compose --profile \"*\" + --remove-orphans for full profile-sweep on stop"

key-files:
  created:
    - docs/timeout-retry-audit.md
  modified:
    - docs/configuration.md
    - quantum-chaos-enterprise-lab/lab.sh

key-decisions:
  - "Audit doc placed under docs/ (not .planning/) — it's consultant-facing reference, not internal planning"
  - "Worked example in upper-bound formula uses single-host (~36s) and 100-host TLS+SSH (~27 min) cases — covers the two consultant FAQs"
  - "Retry policy presented as uniform across scanners; per-scanner retry override is a deferred capability, not a v4.5 promise"
  - "lab.sh reset arm extension applied alongside the down-arm fix — same intent, trivially safe (RESEARCH Open Question 4)"

patterns-established:
  - "Scanner audit doc as canonical Phase-N reference: one row per scanner, citing cfg.scan.timeouts.<slot> directly"
  - "Profile-sweep idiom for docker-compose lab teardown: --profile \"*\" --remove-orphans"

requirements-completed: [ROBUST-04]
requirements-progress: [ROBUST-02]

duration: ~10 min
completed: 2026-04-29
---

# Phase 41 Plan 06: Documentation + lab.sh Profile-Sweep Summary

**Consultant-facing timeout/retry documentation landed (configuration.md sub-table reference + D-10 upper-bound formula + ROBUST-04 audit doc), and the Phase 40 carry-over `lab.sh` profile-sweep gap is closed on both `down` and `reset` arms.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 2
- **Files created:** 1
- **Files modified:** 2

## Accomplishments

- `docs/configuration.md` gained a new **Timeout & Retry Policy (v4.5+)** section between the Scan Block and Targets Block. Documents:
  - All 14 `[scan.timeouts]` slots with type, default, and which scanner consumes them (default=5, fingerprint=4, tls=6, ssh=6, jwt=10, container=120, source=300, dnssec=10, saml=10, kerberos=10, vault=10, db_connect=5, broker=10, email=10).
  - All 3 `[scan.retry]` slots (retry_count=0, backoff_base_seconds=1.0, backoff_max_seconds=5.0).
  - Deprecation table for the four legacy flat fields (`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`, `ssh_timeout_seconds`) → canonical sub-table slots, with explicit `DeprecationWarning` notice.
  - **D-10 upper-bound formula** as a fenced code block plus a worked single-host example (~36s) and a 100-host TLS+SSH worst-case example (~1610s) — the two cases consultants ask about.
  - Full YAML snippet showing both sub-tables in use.
- `docs/timeout-retry-audit.md` created — ROBUST-04 audit doc. Markdown table covering 16 scanner rows (fingerprint, tls, ssh, jwt, container, source, dnssec, saml, kerberos, vault, db_pg, db_mysql, broker_kafka, broker_rabbitmq, broker_redis, email), each citing `cfg.scan.timeouts.<slot>` as canonical source. Closing notes explain default fallback, shared-slot scanners (db, broker), retry uniformity, and the post-Phase-41 source-of-truth chain.
- `quantum-chaos-enterprise-lab/lab.sh` `down` arm now runs `compose --profile "*" down --remove-orphans` (was: `compose down`). `reset` arm now runs `compose --profile "*" down -v --remove-orphans` (was: `compose down -v`) before `compose up -d`. Profile-tagged services (identity, broker, database, vault, email, …) are now swept on every teardown regardless of which profiles were active at startup.

## Task Commits

1. **Task 1: docs/configuration.md + docs/timeout-retry-audit.md** — `cbfa7db` (docs)
2. **Task 2: lab.sh down + reset profile-sweep fix (D-18 + extension)** — `357344a` (fix)

## Files Created/Modified

- `docs/configuration.md` — Inserted ~125-line "Timeout & Retry Policy (v4.5+)" section before Targets Block. No existing content removed; legacy flat-field documentation in the Scan Block left intact (still accurate as long as deprecation warnings are surfaced).
- `docs/timeout-retry-audit.md` — New file. Frontmatter-light heading + audit table + notes section. 16 scanner rows, all sourced from `cfg.scan.timeouts.*`.
- `quantum-chaos-enterprise-lab/lab.sh` — Two-line change: `down` and `reset` arms updated to `--profile "*" ... --remove-orphans`. The `compose()` helper at line 49 is unchanged; `${PROFILE_ARGS}` slot in front of the user args means `--profile "*"` composes cleanly even if `PROFILE_ARGS` is set.

## Decisions Made

- **Audit doc location:** placed under `docs/` (alongside `configuration.md`) rather than `.planning/`. ROBUST-04 calls it consultant-facing — the planning tree is internal-only. Cross-linked from `configuration.md`'s new section.
- **Worked-example pair (single-host + 100-host):** consultants typically ask "how long for one box?" (smoke test) and "how long for /24?" (engagement scoping). Two examples cover both without bloating the section.
- **Retry policy framed as uniform:** per-scanner retry-count overrides were considered; the current `RetryCfg` shape is global. Documenting per-scanner overrides as a v4.5 capability would be misleading since the loader doesn't accept them. Audit doc explicitly notes this as a deferred capability.
- **lab.sh reset-arm extension:** Plan 06 originally only listed D-18 (down arm). RESEARCH Open Question 4 flagged the reset arm as having the same gap with the same fix. Applied both in a single commit — trivially safe and avoids a follow-up commit on a one-line change.

## Deviations from Plan

None. Both tasks executed exactly as specified. The reset-arm extension was already documented in the plan (`must_haves.truths` line: "lab.sh reset arm uses `compose --profile "*" down -v --remove-orphans` (D-18 extension per RESEARCH Open Question 4)"), so it's not a deviation — it's part of the specified scope.

## Issues Encountered

None.

## Threat Flags

None. Documentation change + lab.sh teardown behavior change. No new network surface, no auth path, no trust-boundary change. The `--profile "*"` flag is a wildcard match against locally-defined compose profiles; it does not increase the lab's external attack surface.

## CLAUDE.md Chaos-Lab Maintenance Check

Per the project rule: any change to lab.sh that adds, removes, renames, or reconfigures a Compose profile (or its ports/services) must update `ALL_PROFILES`, the chaos-lab `README.md`, and the `expected_results_*.md` oracle in the same change. **This plan's lab.sh change does not touch profiles, ports, or services** — it only changes how teardown sweeps containers. ALL_PROFILES, README.md, and expected_results files remain accurate as written. No additional sync work required.

## Next Phase Readiness

- Plan 07 (final wave — UAT verification + roadmap close-out) can run UAT-41-03 (`./lab.sh up && ./lab.sh down && docker ps -a | grep quirk-lab` returns no rows) against the fixed lab.sh.
- Phase 41 documentation deliverables are now complete; consultants can reference `docs/configuration.md` §"Timeout & Retry Policy" and `docs/timeout-retry-audit.md` for client deliverables.
- `requirements-progress: [ROBUST-02]` — ROBUST-02 (canonical TimeoutsCfg/RetryCfg) is implementation-complete in Plan 02 and now docs-complete here; Plan 07's verification pass will close it.

## Self-Check: PASSED

Files verified present:
- `docs/configuration.md` — modified (`grep -q "scan.timeouts"` ✓, `grep -q "scan.retry"` ✓, `grep -q "scan_upper_bound"` ✓, `grep -q "safety_margin"` ✓, `grep -q "DeprecationWarning"` ✓)
- `docs/timeout-retry-audit.md` — new (`grep -q "tls_seconds"` ✓, `grep -q "broker_seconds"` ✓, 17 `cfg.scan.timeouts` references ≥ 14 ✓, 18 table rows ≥ 16 ✓)
- `quantum-chaos-enterprise-lab/lab.sh` — modified (`bash -n` exit 0 ✓, `--profile "*" down --remove-orphans` present ✓, `--profile "*" down -v --remove-orphans` present ✓, old `compose down` / `compose down -v` arms gone ✓)

Commits verified in `git log`:
- `cbfa7db` — Task 1
- `357344a` — Task 2

Acceptance criteria all green:
- Task 1: scan.timeouts ✓, scan.retry ✓, scan_upper_bound ✓, safety_margin ✓, DeprecationWarning ✓, ≥14 cfg.scan.timeouts citations ✓, ≥16 table rows ✓.
- Task 2: bash -n ✓, both new arms present ✓, both old arms absent ✓.
- Smoke: `./lab.sh status` exits 0 against an empty lab ✓.

---
*Phase: 41-ci-stability-scanner-robustness*
*Plan: 06*
*Completed: 2026-04-29*
