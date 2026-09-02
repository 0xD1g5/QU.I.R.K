---
phase: 179-remediation-item-model
plan: 04
subsystem: database
tags: [sqlalchemy, sqlite, scope-signature, probe-health, ast-guard, tdd]

# Dependency graph
requires:
  - phase: 179-01
    provides: "ScanScopeSignature table (scan_run_id unique-indexed NOT NULL, digest NOT NULL, discrete columns + probe_health_json)"
  - phase: 179-03
    provides: "remediation_persist phase in run_scan.py's main(), the call site this plan's scope_signature phase is inserted directly after"
provides:
  - "build_scope_signature(cfg, session) / compute_signature_digest(sig) — six discrete scope fields + a deterministic SHA256 digest"
  - "assess_probe_health(cfg, endpoints, run_stats) / _FAMILY_SPEC — 13 probe families with positively-asserted health (healthy | unhealthy | no_targets | not_run)"
  - "persist_scope_signature(db_path, scan_run_id, cfg, endpoints, run_stats) — writes/updates one scan_scope_signatures row at scan completion"
  - "run_scan.py's main() populates the scope-signature table in a dedicated scope_signature phase between remediation_persist and reporting"
affects: ["180-closure-computation"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Protocol-set membership for every probe family (13/13) — no evidence-column-only membership fallback was needed anywhere, including the three families (email, broker, database) whose CryptoEndpoint.protocol values fan out across multiple literals; the enumerable sets were verified against live scanner source and the discretion is recorded in _FamilySpec's docstring"
    - "database family borrows tls_version as its positive-evidence field (no dedicated *_scan_json column exists for db) — the only family that deviates from the evidence-json-column convention, documented inline"
    - "Digest excludes probe_health_json by construction — a fixed 6-field payload tuple, not the full signature dict — so health variance across otherwise-identical scans never makes them incomparable"
    - "Idempotent upsert via unique-index lookup-then-update (mirrors remediation_persist's --resume-scan-id handling), not INSERT-and-catch-IntegrityError"

key-files:
  created:
    - quirk/intelligence/scope_signature.py
    - tests/test_scan_scope_signature.py
  modified:
    - run_scan.py

key-decisions:
  - "All 13 probe families use protocol-SET membership, not the evidence-column-only fallback the plan's action text anticipated for 'families not distinguishable by protocol.' Measured against live scanner source: email's 7 EMAIL_PORTS protocol labels and broker's 5 protocol labels are both fully enumerable frozensets, and database's POSTGRESQL/MYSQL labels are equally clean. The fallback path was never needed; this is recorded as Claude's Discretion in _FamilySpec's docstring rather than silently deviating from the plan's suggested design."
  - "database has no *_scan_json evidence column at all (verified: not in the CryptoEndpoint evidence-column list). tls_version is used instead — a Postgres/MySQL TLS handshake writes directly onto the shared TLS fields, not a JSON blob. Documented inline in _FAMILY_SPEC's leading comment."
  - "persist_scope_signature is fully exception-guarded (try/except returning None + logger.exception), mirroring persist_remediation_snapshot's advisory-bookkeeping-must-never-fail-a-scan contract, even though the plan's <action> text didn't explicitly mandate it — this is the established pattern for every 179-series bookkeeping phase inserted into run_scan.py's main() and is the safer default for a phase that only records evidence, never gates the scan."
  - "Three per-task commits share one file (quirk/intelligence/scope_signature.py) built incrementally — each task's commit stages exactly that task's additions (build_scope_signature/digest, then _FAMILY_SPEC/assess_probe_health, then persist_scope_signature + run_scan.py wiring), verified independently green before each commit, rather than one combined commit for the whole plan."

requirements-completed: []  # REMED-02 spans 01/04/05/06. Not marked complete per plan instructions.

# Metrics
duration: ~55min
completed: 2026-09-02
---

# Phase 179 Plan 04: Scan Scope Signature + Probe Health Summary

**`persist_scope_signature()` writes one `scan_scope_signatures` row per `scan_run_id` at scan completion — six discrete scope fields (port scope, profile, extras present, credentials present, sensor set) plus a deterministic SHA256 digest, together with a per-family probe-health map derived from positive evidence (never `scan_error IS NULL`) — so Phase 180 can hard-refuse closure across incomparable scans.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-02
- **Tasks:** 3/3 completed
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `build_scope_signature(cfg, session)` returns six discrete fields (`signature_version`, `port_scope`, `profile`, `extras_present`, `credentials_present`, `sensor_set`); `compute_signature_digest(sig)` produces a stable 64-char SHA256 hex digest over exactly those six fields, mirroring `compute_fingerprint`'s canonicalisation shape (`json.dumps(sort_keys=True, separators=(",", ":"))`)
- Digest-sensitivity matrix proven: changing profile, port scope, extras present, credentials present, or sensor set each independently changes the digest; two independently-built identical signatures produce the same digest; `probe_health_json` is explicitly excluded from the digest payload and proven insensitive by a dedicated test
- `credentials_present` stores credential KIND labels only (`broker`, `snmp_v3`, `postgres`, `mysql`, `aws`, `azure`, `gcp`) — never a username, password, env-var name, profile name, subscription id, or project id; a dedicated test plants secret-looking values into the config and asserts they never appear anywhere in the built signature
- `assess_probe_health(cfg, endpoints, run_stats)` and `_FAMILY_SPEC` cover 13 probe families (`tls`, `ssh`, `jwt`, `container`, `source`, `database`, `dnssec`, `saml`, `kerberos`, `smime`, `codesign`, `email`, `broker`), deriving `healthy | unhealthy | no_targets | not_run` in the exact order the plan specifies — family disabled → `not_run`; timing key absent → `not_run`; evidence present → `healthy`; zero matching endpoints → `no_targets`; otherwise → `unhealthy`
- **The degraded-probe guard** (`test_probe_health_positive_assertion`): 3 SSH endpoints, `enable_ssh` implicitly on (always-on family), `ssh_scanning` timing key present, every endpoint has `ssh_audit_json is None` AND `scan_error is None` — exactly TRIAGE-176-03's shape. Recorded `unhealthy`, not `healthy`. Proven RED first against a temporary naive `scan_error is None`-based stub (see below)
- `no_targets` is proven distinguishable from `unhealthy` (timing key present, zero matching endpoints); the Phase 173 stale-timing-key precedent is proven not to upgrade a family to `healthy` on its own; non-deep TLS (`tls_enum_mode != "deep"`) is proven `not_run`, not `unhealthy`
- `scan_error is None`, `returncode == 0`, and `exit_code` are grep-confirmed absent from the module as health signals
- `persist_scope_signature()` writes one row per `scan_run_id` at scan **completion**, wired into `run_scan.py` strictly between Plan 03's `remediation_persist` block and the `reporting` block (`git diff --stat run_scan.py` = 18 lines, under the 25-line budget); idempotent under `--resume-scan-id` (lookup-then-update on the unique index, never a duplicate insert); a round-trip test recomputes the digest from the read-back discrete columns and confirms it matches the stored digest
- `quirk/cli/console_cmd.py` and `quirk/intelligence/roadmap.py` verified byte-unchanged (`git diff` both empty)
- Sensor-origin limitation (179-CONTEXT.md § Sensor-Origin Coverage) recorded directly in `persist_scope_signature`'s docstring: no `scan_run_id` is synthesized for sensor-pushed envelopes; sensor-origin findings have no signature coverage and are excluded from closure by user decision

## Task Commits

Each task was committed atomically:

1. **Task 1: build_scope_signature and the digest** - `70f975cf` (feat, tdd)
2. **Task 2: assess_probe_health — positive assertion per family** - `594a1d85` (feat, tdd)
3. **Task 3: Persist the signature at scan completion** - `ae287554` (feat)

_Note: Tasks 1 and 2 are `tdd="true"`. Tests were written alongside the implementation and run to confirm the correct shape for each `<behavior>` bullet before each task's single commit, matching the plan's task-level `type="auto" tdd="true"` grouping (no separate test/feat commits required within one task) — the same convention 179-03 established. Task 2's mandatory negative control (see below) was additionally run for real, as a genuine RED reproduction of TRIAGE-176-03, before the real implementation was confirmed and committed._

## Files Created/Modified

- `quirk/intelligence/scope_signature.py` (new) — `SCOPE_SIGNATURE_VERSION`, `build_scope_signature()`, `compute_signature_digest()`, `_has_evidence()`, `_FamilySpec`, `_FAMILY_SPEC` (13 families), `assess_probe_health()`, `persist_scope_signature()`. No literal `"scoring"` anywhere in the file (grep-clean); no `scan_error is None` / `returncode == 0` / `exit_code` used as a health signal (grep-clean)
- `tests/test_scan_scope_signature.py` (new) — 35 tests: the required digest-stability + sensitivity matrix, the never-stores-credential-values guard, the 13-family `_FAMILY_SPEC` coverage guard, `test_probe_health_positive_assertion` (the degraded-probe guard, named exactly as `179-VALIDATION.md` references), the positive control, the `scan_error`-alone-never-healthy guard, `no_targets` vs `unhealthy`, family-disabled/timing-absent → `not_run`, the stale-timing-key guard, empty-JSON-container non-evidence cases, non-deep-TLS → `not_run`, the exit-status/`scan_error` grep guard, the round-trip digest-consistency test, the idempotency test, the skip-without-scan_run_id/db_path test, the docstring content guard, and the `remediation_persist < scope_signature < "reporting"` call-site ordering guard
- `run_scan.py` — one new `with _phase_timer(run_stats, "scope_signature")` block inserted between Plan 03's `remediation_persist` block and `proto_counts = Counter(...)` / the `reporting` block; lazy import of `persist_scope_signature` inside the block; skips via `mark_skipped()` when `scan_run_id` or `cfg.output.db_path` is falsy, so no phantom `timings_sec` key is written

## Decisions Made

- **All 13 families use protocol-set membership; the evidence-column-only fallback the plan anticipated was never needed.** The plan's `<action>` text hedged that "families whose endpoints are not distinguishable by protocol" might need membership defined purely by evidence-column non-NULL-ness with `endpoints_seen` sourced from the timing key. Measured against the live scanner source: `email_scanner.py`'s `EMAIL_PORTS` table has exactly 7 enumerable protocol labels (`SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S`), `broker_scanner.py` has exactly 5 (`KAFKA-TLS`, `KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-TLS`, `REDIS-PLAIN`, excluding `ADVISORY` rows which are not probe attempts), and `db_connector.py` has exactly 2 (`POSTGRESQL`, `MYSQL`). All three are cleanly enumerable frozensets — the fallback was designed for a case that didn't materialize once the source was actually read. This is recorded as Claude's Discretion in `_FamilySpec`'s docstring rather than silently choosing one path without explanation.
- **`database` has no dedicated evidence-JSON column, unlike every other family.** `tls_version` is used as its positive-evidence field instead, because Postgres/MySQL TLS handshake results are written directly onto the shared TLS fields (not a JSON blob) — the only family where this deviation from the "one `*_scan_json` column per family" convention was necessary. Documented in `_FAMILY_SPEC`'s leading comment.
- **`persist_scope_signature` is fully exception-guarded**, returning `None` and logging on any failure — matching `persist_remediation_snapshot`'s "advisory bookkeeping must never fail the scan it attaches to" contract from Plan 03, even though this plan's `<action>` text didn't explicitly restate that requirement. This keeps the two Phase-179 scan-time bookkeeping phases behaviorally consistent.
- **Three task-boundary commits share one incrementally-built file.** Rather than one combined commit for the whole plan (or three commits each rewriting the full file), each commit stages exactly the additions specified by that task — `build_scope_signature`/`compute_signature_digest` first, then `_FAMILY_SPEC`/`assess_probe_health`, then `persist_scope_signature` plus the `run_scan.py` wiring — with the test suite re-verified green at each boundary before committing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test fixture for `Sensor` rows was initially missing required NOT NULL columns**
- **Found during:** Task 1, first test run of `test_build_scope_signature_sensor_set_reads_enrolled_fleet`
- **Issue:** `Sensor` requires `segment` (`nullable=False`), `enrolled_at` (`nullable=False`), and `expected_cadence_minutes` (`nullable=False`); the initial test only set `sensor_id`, producing three sequential `IntegrityError`s.
- **Fix:** Populated all four required fields on the two test `Sensor` rows.
- **Files modified:** `tests/test_scan_scope_signature.py`
- **Commit:** `70f975cf`

**Total deviations:** 1 auto-fixed (Rule 1, a test-fixture correctness fix found during the same task's own test run — no implementation-logic bugs, no scope creep).
**Impact on plan:** Zero impact on shipped behavior.

## Negative Control — Recorded RED Output (Task 2, mandatory per plan)

A temporary naive `assess_probe_health` stub was swapped into `quirk/intelligence/scope_signature.py`, using `scan_error is None` as its (wrong) health signal instead of the family evidence column:

```python
def assess_probe_health(cfg, endpoints, run_stats):
    """TEMP NAIVE STUB for negative-control RED evidence (Phase 179 Plan 04)."""
    endpoint_list = list(endpoints)
    timings = ((run_stats or {}).get("timings_sec") or {})
    result = {}
    for family, spec in _FAMILY_SPEC.items():
        if spec.timing_key not in timings:
            result[family] = {"status": "not_run", ...}
            continue
        seen = [e for e in endpoint_list if getattr(e, "protocol", None) in spec.protocols]
        ok = all(getattr(e, "scan_error", None) is None for e in seen)  # WRONG signal
        status = "healthy" if ok and seen else ("no_targets" if not seen else "unhealthy")
        result[family] = {"status": status, ...}
    return result
```

Running `test_probe_health_positive_assertion` against this stub (3 SSH endpoints, `ssh_audit_json=None`, `scan_error=None`, `ssh_scanning` timing key present) produced:

```
F
=================================== FAILURES ===================================
_____________________ test_probe_health_positive_assertion _____________________
    health = assess_probe_health(cfg, endpoints, run_stats)

>   assert health["ssh"]["status"] == "unhealthy"
E   AssertionError: assert 'healthy' == 'unhealthy'
E
E     - unhealthy
E     ? --
E     + healthy

tests/test_scan_scope_signature.py:276: AssertionError
=========================== short test summary info ============================
FAILED tests/test_scan_scope_signature.py::test_probe_health_positive_assertion
1 failed in 0.20s
```

This is the exact TRIAGE-176-03 failure mode reproduced: a naive `scan_error IS NULL`-based check reports `healthy` for a probe that silently degraded and produced no evidence. The stub was then reverted via a scripted exact-file restore (`cp` from a pre-mutation backup, not a manual re-type), and `git status --short` was confirmed to show the file as identical to its Task-1-committed state before Task 2's real implementation was verified and committed. The guard was re-run afterward against the real `assess_probe_health` and passed green (see Self-Check below).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `quirk/intelligence/scope_signature.py` is ready for Phase 180's closure computation: `persist_scope_signature()` writes exactly one row per `scan_run_id`, columns and digest mutually consistent (round-trip proven), with `probe_health_json` available for 180 to read and reason about per-family before deciding whether to attempt closure at all
- A MISSING signature row means NOT-COMPARABLE — stated explicitly in `persist_scope_signature`'s docstring — so Phase 180 must treat absence as a hard refusal condition, never as comparable-by-default
- The sensor-origin exclusion is recorded in the code that owns it; Plan 05 still needs to surface it in operator-facing docs per 179-CONTEXT.md's explicit requirement
- No blockers. `quirk/intelligence/roadmap.py` and `quirk/cli/console_cmd.py` remain byte-unchanged; `tests/test_cve_score_guard.py` and `quirk/intelligence/scoring.py` remain byte-unchanged; REMED-02 is NOT marked complete (it spans plans 01/04/05/06)

---
*Phase: 179-remediation-item-model*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: quirk/intelligence/scope_signature.py
- FOUND: tests/test_scan_scope_signature.py
- FOUND: 70f975cf (git log)
- FOUND: 594a1d85 (git log)
- FOUND: ae287554 (git log)
- Verified: `.venv/bin/pytest tests/test_scan_scope_signature.py tests/test_remediation_persist.py tests/test_remediation_item_model.py tests/test_remediation_advisory_guard.py tests/test_cve_score_guard.py tests/test_run_scan_init_db_scope.py tests/skip_registry.py -q` → 83 passed
- Verified: `git diff quirk/cli/console_cmd.py quirk/intelligence/roadmap.py` → empty (byte-unchanged)
- Verified: `git diff --stat run_scan.py` (this plan's contribution) → 18 insertions, under the 25-line budget
- Verified: `grep -n "scoring" quirk/intelligence/scope_signature.py` → no matches
- Verified: `grep -nE "scan_error is None|returncode == 0|exit_code" quirk/intelligence/scope_signature.py` → no matches
- Verified: `.venv/bin/python -c "from quirk.intelligence.scope_signature import _FAMILY_SPEC as F; assert 'ssh' in F and 'broker' in F and len(F) >= 13"` → exits 0 (13 families)
