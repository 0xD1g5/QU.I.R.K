# Phase 115: Live-UAT Stabilization + Lab Testability - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — grey areas proposed in batch tables, all accepted

<domain>
## Phase Boundary

Root-cause and eliminate the four defects surfaced by the v5.4 distributed live-UAT
(backlog 999.86–89) so `lab.sh distributed e2e` is re-runnable without
`docker compose down -v`, and make the Phase 111 per-segment filter exercisable
end-to-end by adding a weak-crypto target to a non-default segment of the
distributed chaos lab (999.85).

**Delivers (STAB-01..04, LAB-01):**
- **STAB-01** — `quirk console enroll` / `quirk sensor enroll` are idempotent for
  already-provisioned entities (no error, no duplicate rows) → lab re-runnable
  without teardown.
- **STAB-02** — `cmvp_cache.json` ships inside the installed wheel (declared as
  package data) → no "CMVP cache unavailable" warning on merge in a non-source-tree
  install.
- **STAB-03** — `quirk scheduler` no longer passes unsupported `--target` /
  `--output` to `run_scan`; scheduled scans exit 0; locked by a regression test in
  the same class as the fixed `sensor` / `_run_local_scan` bug.
- **STAB-04** — Phantom `email_scanner` / `broker_scanner` rows with
  `scanned_at=None` / port 0 are root-caused and eliminated **at the source**, so
  merged console output contains no phantom endpoints.
- **LAB-01** — The distributed chaos lab gains a weak-TLS target on `segment-b`
  reachable only by sensor-b; `lab.sh distributed`, the `expected_results_*.md`
  oracle, and the chaos-lab README are all updated in the same change (CLAUDE.md
  no-drift rule).

**Locked constraints (milestone-level, carried from v5.5):** single-tenant only ·
additive schema only · no new heavy infra · OS-agnostic sensor↔console wire
contract unchanged · CLAUDE.md chaos-lab no-drift rule applies to LAB-01.

</domain>

<decisions>
## Implementation Decisions

### Enroll idempotency (STAB-01)
- **D-01:** Re-enrolling an already-provisioned sensor/console is an **idempotent
  success** — it prints an "already enrolled" notice and exits 0 **without minting
  a new token**. No token churn on re-run. (Accepted Area 1 Q1.)
- **D-02:** Detection is a **pre-check by `sensor_id`** before insert, with the
  existing `IntegrityError` rollback retained as a backstop (covers the
  pre-check/insert race). Mirror this in both `console_cmd._cmd_enroll` and
  `sensor_cmd` enroll. (Accepted Area 1 Q2.)
- **D-03:** An explicit `--rotate` / `--force` re-mint path is **deferred** (out of
  scope this phase). (Accepted Area 1 Q3.)

### Phantom-row root cause (STAB-04)
- **D-04:** Eliminate the vacuous `scanned_at=None` / port-0 `email_scanner` /
  `broker_scanner` rows **at the source** — stop the scanner/builder Pass-1 from
  emitting empty endpoint rows — rather than filtering them downstream. (Accepted
  Area 2 Q1; matches the success-criterion wording "eliminated at the source".)
  Investigate builder Pass-1 (see prior note: 5 profiles emit zero CBOM algo
  components — database/registry/source/ssh-weak/storage-s3 vacuously pass the
  classifier gate).
- **D-05:** Add a **regression test** asserting merged console output contains no
  endpoint with `scanned_at` null or port 0. (Accepted Area 2 Q2.)

### Scheduler fix (STAB-03) + CMVP packaging (STAB-02)
- **D-06:** `scheduler_cmd` **drops the unsupported `--target` / `--output`**
  arguments to the `python -m run_scan` subprocess. `run_scan.py`'s top-level
  parser accepts `--config` (and `--profile`) but NOT `--target` / `--output`;
  drive target + output directory via `--config` (cfg target + `cfg.output.directory`,
  the SENSOR-05 Fix-1 anchoring already present). Do **not** widen `run_scan.py`'s
  arg surface. (Accepted Area 3 Q1.)
- **D-07:** Lock STAB-03 with a regression test in the **same test class** as the
  fixed `sensor` / `_run_local_scan --output` bug (asserts the scheduler cmd list
  contains no `--target` / `--output` and scheduled run exits 0).
- **D-08:** Ship `cmvp_cache.json` by declaring `quirk/compliance/*.json` (or the
  specific file) under **`[tool.setuptools.package-data]`** in `pyproject.toml`.
  Prefer `importlib.resources` for the load path if the current loader uses a
  source-tree-relative path. (Accepted Area 3 Q2.)

### Weak-crypto lab target (LAB-01)
- **D-09:** Add a **weak-TLS target** (TLS 1.0/1.1 + RC4/export ciphers) to the
  **`segment-b`** network of `docker-compose.distributed.yml`, reachable **only by
  sensor-b** (preserves the existing segment isolation; sensor-a does not see it).
  (Accepted Area 4 Q1+Q2.)
- **D-10:** **Reuse the existing chaos-lab weak-TLS image/pattern** — the main
  `docker-compose.yml` already defines a "LEGACY TLS (TLS 1.0/1.1 + weak-ish
  ciphers)" service (~L14); model the distributed target on it rather than building
  a new custom image. (Accepted Area 4 Q3.)
- **D-11:** Per the CLAUDE.md no-drift rule, the **same change** updates
  `lab.sh` (distributed profile/services if affected), the
  `expected_results_distributed.md` oracle (new weak-TLS findings + per-segment
  score), and the chaos-lab `README.md`.

### Claude's Discretion
- Exact "already enrolled" message strings and whether the pre-check emits to
  stdout vs stderr (follow existing T-109 fixed-string conventions, exit 0).
- The precise builder/scanner location of the phantom-row emission (Pass-1
  investigation result) and the cleanest source-level fix.
- The exact weak-TLS service image/tag, container name, and port for the
  distributed lab target, and the resulting oracle finding rows.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Defect surfaces
- `quirk/cli/console_cmd.py` — `_cmd_enroll` (L136): atomic sensors + sensor_tokens
  insert, IntegrityError rollback. Add idempotent pre-check (STAB-01).
- `quirk/cli/sensor_cmd.py` — sensor enroll path; mirror idempotency.
- `quirk/cli/scheduler_cmd.py` — the `python -m run_scan` subprocess builder (~L150);
  remove `--target` / `--output` (STAB-03). `run_scan.py` top-level argparser
  (~L590) confirms only `--config`/`--profile` are accepted.
- `quirk/compliance/cmvp.py` + `quirk/compliance/cmvp_cache.json` — packaging target
  (STAB-02); `pyproject.toml` `[tool.setuptools.package-data]` (~L127).
- Phantom rows (STAB-04): `quirk/scanner/email_scanner.py`,
  `quirk/scanner/broker_scanner.py`, and the merge/CBOM builder Pass-1 — the
  email/broker scanners are NOT in the scanner registry, so the vacuous rows
  originate in builder/emission, not registration.

### Lab (LAB-01 — no-drift rule)
- `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` — segment-a
  (10.10.0.0/24) / segment-b (10.20.0.0/24) topology; add weak-TLS target on
  segment-b.
- `quantum-chaos-enterprise-lab/docker-compose.yml` (~L14) — existing LEGACY TLS
  service to model the distributed weak-TLS target on.
- `quantum-chaos-enterprise-lab/lab.sh` — distributed profile + ALL_PROFILES list.
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` — oracle.
- `quantum-chaos-enterprise-lab/README.md` — chaos-lab README.

### Requirements
- `.planning/REQUIREMENTS.md` §STAB / §LAB — STAB-01..04, LAB-01.

### Prior context
- `.planning/STATE.md` Deferred Items + memory backlog 999.85–89 (the v4 live-UAT
  defects this phase closes).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_default_db_path()` + `QUIRK_DB_PATH` resolution (enroll path already uses it).
- Existing IntegrityError rollback + fixed-string error pattern in `_cmd_enroll`.
- `cfg.output.directory` anchoring (SENSOR-05 Fix-1) — the scheduler already
  computes `output_dir` from config; the `--output` arg is redundant with it.
- The main compose LEGACY TLS service — weak-TLS image/cipher config to reuse.

### Established Patterns
- T-109 fixed-string audit / never-stringify-exception conventions on the CLI.
- CLAUDE.md chaos-lab no-drift rule: lab.sh + README + expected_results in one change.
- Regression tests co-located with the originally-fixed bug's test class.

### Integration Points
- Enroll pre-check before the two-row insert in both console + sensor enroll.
- scheduler_cmd subprocess arg list (drop two args).
- pyproject package-data + cmvp load path.
- builder/scanner Pass-1 emission (phantom rows).
- distributed compose + lab.sh + oracle + README (weak-TLS target).

</code_context>

<specifics>
## Specific Ideas

- STAB-03 regression test belongs in the SAME test class as the prior
  `sensor` / `_run_local_scan --output` fix (v5.4 live-UAT follow-up).
- STAB-04 regression: merged console output has zero endpoints with `scanned_at`
  null or port 0.
- LAB-01 must keep `lab.sh distributed e2e` green and exercise the Phase 111
  per-segment filter end-to-end (the previously-blocked Test 7).

</specifics>

<deferred>
## Deferred Ideas

- `--rotate` / `--force` explicit token re-mint on enroll — deferred (D-03).
- Widening `run_scan.py` to accept `--target` / `--output` — rejected (D-06);
  the scheduler conforms to run_scan's existing surface instead.
- Weak-SSH distributed target / segment-a placement — not chosen (D-09 picks
  weak-TLS on segment-b).

</deferred>

---

*Phase: 115-live-uat-stabilization-lab-testability*
*Context gathered: 2026-05-27 via smart discuss (autonomous)*
