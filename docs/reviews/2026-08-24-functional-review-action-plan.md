# QU.I.R.K. — Functional Review Action Plan

**Source:** `docs/reviews/2026-08-24-functional-review-findings.md`
**Review date:** 2026-08-24 · **Reviewed commit:** `49f9094`
**Status legend:** ☐ Open · ◐ In progress · ☑ Done · ⊘ Won't fix (record why)

Remediation text is written in requirement phrasing so rows can be promoted into
`.planning/REQUIREMENTS.md` as a milestone requirement set without rewriting.

Effort: **S** ≤ half a day · **M** 1–3 days · **L** > 3 days.

---

## Theme 1 — Scan Pipeline Correctness (blocks the core deliverable)

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-001 | CRITICAL | Every TLS/certificate and email endpoint is persisted twice — `merge()` at `run_scan.py:3190` re-inserts rows already written by `_flush_stage_endpoints()` | core value path; all inventory counts | The scan pipeline must persist exactly one row per scanned endpoint per scan session. Root cause is a false assumption that `session.merge()` writes the PK back onto the passed object; it does not. See fix options below. Add a regression test asserting a single-host scan yields no two rows differing only in `id`. | S–M | Open |
| ☐ | RVW-002 | HIGH | The dashboard runs a second finding engine that lacks self-signed and untrusted-CA detection and escalates RSA-1024 to CRITICAL | dashboard `/findings`; operator-vs-client consistency | The dashboard and the report must present the same findings at the same severities. `routes/scan.py` should consume `findings_evaluator` rather than hand-rolling ~20 titles of its own. Add a cross-surface parity test asserting the dashboard and report agree on title and severity for a fixed endpoint set. **Severity revised CRITICAL → HIGH after re-verification: the client deliverable was never affected.** | M | Open |
| ☐ | RVW-003 | HIGH | Scan sessions have no stored identity — `CryptoEndpoint` has no `scan_run_id`, so membership is reconstructed from wall-clock time; one scan renders as several history rows with contradictory scores (92/100/93) | Scan History, Trends, per-session scores | A scan session must be identified by a stored key, not inferred from timestamps. Add `scan_run_id` to `CryptoEndpoint` (the column already exists on `ScanJob` and `ScanCheckpoint`) and group `list_scans()` / trends by it instead of 1-second truncation. No endpoint may persist with a NULL `scanned_at` — those rows are currently invisible to Scan History. Add a test asserting one scan yields exactly one history row. **Fix direction revised after re-verification — see note.** | M | Open |

### RVW-001 — fix options

The two writes are `_flush_stage_endpoints()` (`run_scan.py:243`, Phase 67 / RESUME-01,
called from 8 stages) and the final `db_persist` block (`run_scan.py:3190`). The second was
written to be an UPDATE — its comment says so — but `session.merge()` returns a *new*
persistent instance and never sets the PK on the object passed in, so the endpoints reach
the final persist with `id = None` and are INSERTed again.

| Option | Change | Trade-off |
|---|---|---|
| **A — write the PK back** (recommended) | In `_flush_stage_endpoints`, capture `merged = session.merge(ep)` and assign `ep.id = merged.id` after `commit()`. | Smallest diff; makes the existing `merge()` comment true rather than aspirational. Must run inside the session, before it closes. |
| **B — database constraint** | Add a uniqueness constraint on the endpoint's natural key and let the second write collide harmlessly. | Defence in depth, but needs a migration, and the natural key must **not** include `scanned_at` until RVW-003 is fixed. |
| **C — skip the redundant write** | Track which stages already flushed and exclude them from the final persist. | Most bookkeeping; risks losing rows if a stage flush silently fails — note `_flush_stage_endpoints` swallows all exceptions by design. |

**Sequencing note:** fix **RVW-003 before** adopting option B, since `scanned_at` is
currently unreliable as part of any natural key. RVW-001 and RVW-003 both concern how
endpoints are written and are best investigated in one sitting, but they are independent
defects with independent fixes — RVW-001 is a persistence-identity bug, RVW-003 is a
session-identity bug.

### RVW-003 — revised fix direction

The original remediation ("stamp endpoints with the shared `session_start` instead of
`datetime.now()`") treated the symptom. Re-verification showed:

- The **read** path already documents and works around the per-endpoint timestamps —
  `list_scans()` truncates to one second on purpose. The workaround fails only because a
  single scan's *stages* span multiple seconds, which no amount of truncation can group.
- STRUCT-01 does **not** apply: it is scoped to scanners new in v4.4, and every such
  scanner complies. `tls`/`ssh`/`jwt` are v3.9-era and were never in scope.

So the fix is not to change how timestamps are produced but to stop using them as identity.
`ScanJob` and `ScanCheckpoint` already carry `scan_run_id`; `CryptoEndpoint` does not. Adding
it (additive migration, matching the project's existing `_ADDITIVE_MIGRATIONS` convention)
and grouping on it makes both Scan History and Trends correct by construction, and removes
the 1-second heuristic entirely.

This also makes RVW-001 option B viable: `scan_run_id` gives the natural key a stable
component that `scanned_at` cannot provide.

---

## Theme 2 — Release & CI Discipline

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-004 | HIGH | v5.13 and v5.14 declared shipped but never released; v5.14 tag contains `version = "5.12.0"` | release integrity; sensor version reporting | Either publish v5.13/v5.14 properly (bump `pyproject.toml`, run the release workflow) or correct ROADMAP.md to stop claiming they shipped. A milestone must not be markable ✅ shipped without a successful release run. | M | Open |
| ☐ | RVW-005 | HIGH | Three of four CI workflows red on `main`; the last 19 commits have never run CI | entire verification discipline | Restore all four workflows to green and establish that CI runs on every push to `main`. Investigate why no workflow triggered for commits `d3237a7`..`49f9094`. | M | Open |
| ☐ | RVW-006 | HIGH | A sixth CI-gated staleness catalog (CMVP) is undocumented — and is the one currently failing | maintenance runbook | Re-verify the CMVP cache and run `quirk compliance cmvp refresh`. Add CMVP, error-codes, and SNMP-contract catalogs to CLAUDE.md's Staleness Review Cadence so the runbook matches `python-staleness.yml`. | S | Open |
| ☐ | RVW-017 | MEDIUM | Test isolation is illusory — 31 test files share one process-wide in-memory DB via `cache=shared`; `test_get_schedules_empty` fails after `test_otics_cadence_floor.py` writes a schedule | suite reliability; CI trust | The `dashboard_client` fixture must give each test an isolated database, as its docstring already claims. Options: a per-test unique shared-cache name (`file:test_<uuid>:?cache=shared`), or truncate tables in fixture teardown. **Raised OBSERVATION → MEDIUM: the stated cause (random ordering) was wrong — `pytest-randomly` is not installed — and the real cause affects 31 files.** | M | Open |

---

## Theme 3 — Test & Gate Robustness

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-011 | MEDIUM | E2E smoke cannot pass on a developer machine (140s scan vs 120s budget) | developer trust in the suite | `npm run e2e:smoke` must pass on a machine with services listening on common ports — raise the timeout, narrow the scan scope, or pin the port scope for E2E. | S | Open |
| ☐ | RVW-012 | LOW | a11y gate red on a CSS-selector change, not an accessibility change; the real 23-element contrast violation is permanently baselined and invisible | a11y gate value | Key a11y baselines on something stabler than the full CSS-selector path. Separately, decide whether the baselined `/data-at-rest` `color-contrast` violation is accepted or should be fixed — currently it can never fire. | M | Open |
| ☐ | RVW-020 | OBS | `uat_runner.py` parses XML with stdlib `ElementTree` (XXE/billion-laughs by default) | tooling hygiene | Use `defusedxml` for XML parsing in a security-tooling product. | S | Open |

---

## Theme 4 — Documentation & Traceability

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-007 | MEDIUM | `CHANGELOG.md` stale by six milestones (v5.9–v5.14) | public repo users | The changelog must document every shipped milestone. Backfill v5.9–v5.14. | M | Open |
| ☐ | RVW-008 | MEDIUM | UAT gating doc records no outcome for **353 of 601 cases (59%)**; only 31 carry an explicit disposition; 5 duplicate case IDs | gating-document integrity | Every UAT case must carry a recorded result or an explicit deferral. 31 already do (the UAT-33-03 pattern — deferral plus a named substitute test — is the model to follow). Resolve the 5 duplicate IDs. **Counts corrected upward after re-verification (was "178 of 355").** | L | Open |
| ☐ | RVW-009 | MEDIUM | v4.7 shipped with no archived ROADMAP or REQUIREMENTS (only dead link of 40) | traceability | Reconstruct v4.7's requirements from `v4.7-phases/` or correct ROADMAP.md's dead link. | S | Open |
| ☐ | RVW-010 | LOW | **Four** delivered requirements have no discoverable test: DEBT-02, GAP-02, QRAMM-08, QRAMM-09 | test coverage | Write a test for each: `lab.sh` PROFILE_ARGS precedence, the re-enabled SAML scan-window test, the 120-question/4-tab assessment page, and the Org Profile multiplier. Separately, annotate the 5 requirements that have tests but no linkage (AUTH-05, DEBT-04, GAP-01, QRAMM-11, TAIL-04). **Revised 15 → 4 after re-verification; 6 of the original 15 are not code requirements.** | S | Open |
| ☐ | RVW-021 | MEDIUM | `quirk scan --targets` does not exist — no `scan` subcommand, no `--targets` flag; `--targets` prefix-matches `--targets-file` and raises an uncaught FileNotFoundError | first-run experience; 6 UAT step definitions | The dashboard empty state (`findings.tsx:119`) must instruct a command that exists. Correct `docs/chaos-lab.md:676` and the six UAT steps in `docs/UAT-SERIES.md`. An unparseable target argument must fail with a coded error, not a traceback (requirement UX-02). | S | Open |
| ☐ | RVW-013 | LOW | Version strings stale in README, UAT-SERIES, pyproject; absent from getting-started | user-facing docs | Resolve as part of RVW-004; add getting-started to the version-drift checklist. | S | Open |
| ☐ | RVW-014 | LOW | Four requirement formats and five UAT result formats across the corpus | tooling fragility | Adopt one requirement declaration format and one UAT result format for new documents. Backfilling archives is optional. | M | Open |
| ☐ | RVW-015 | LOW | Archive headers contradict contents (v4.6 "36" vs 22; v5.7 "24" vs 10) | doc accuracy | Correct the two counts; add `**Status:**` headers to the five archives lacking one. | S | Open |
| ☐ | RVW-016 | LOW | Release tag naming inconsistent (`v5.14` vs `v5.12.0`) | tooling | Adopt one tag convention going forward. | S | Open |
| ☐ | RVW-018 | OBS | Planning summaries reference siblings by pre-archive path (16 broken refs) | planning hygiene | Reference phase artifacts by a path that survives archival, or rewrite on archive. | S | Open |
| ☐ | RVW-019 | OBS | GAUGE-01/02/03 have no traceability link (code verified correct) | traceability | Annotate `ScoreGauge.test.tsx` with the GAUGE requirement IDs. | S | Open |

---

## Suggested Sequencing

A recommendation the owner may reject — the reviewer proposes, the owner disposes.

**Milestone A — "Scan Integrity" (blocks release).** RVW-001, RVW-003, then RVW-002.
RVW-001 and RVW-003 are the two findings that corrupt the client-facing deliverable —
doubled inventory rows and phantom scan history. RVW-002 does not affect the client
deliverable (the report is correct) but does mean the operator's primary surface disagrees
with it, so it belongs in the same milestone at lower priority.

Re-verification moved RVW-002 out of the "corrupts the deliverable" category. If capacity
is tight, RVW-001 and RVW-003 are the two that genuinely gate a release.

**Milestone B — "Release the Backlog."** RVW-004, RVW-005, RVW-006, RVW-013, RVW-017.
Get CI green, get the version bumped, get v5.13/v5.14 either released or un-claimed. This
is mostly small work whose value is that it makes Milestone A's fixes verifiable and
shippable. RVW-006 is a ~15-minute fix that turns two red workflows green.

**Milestone C — "Trustworthy Gates."** RVW-011, RVW-012, RVW-020.
Make the suites pass for real reasons so they stop training people to ignore red.

**Milestone D — "Documentation Drain."** RVW-007 through RVW-019 (docs items).
Genuine debt, no functional urgency. RVW-008 (**353 unrecorded UAT cases**, corrected
upward from 178) is by far the largest item here. Partial closure by reference to existing
automated coverage is still the pragmatic route, but note the caveat added during
re-verification: requirement-ID annotation is an unreliable proxy for coverage in both
directions, so each closure needs a named test, not an inferred one. The project's own
UAT-33-03 pattern — an explicit deferral naming the substitute test — is the model.

---

## Not Assessed

Recorded so the plan is not mistaken for full coverage — see the findings report §6.

- Windows platform behaviour and packaging.
- Cloud connector paths (AWS / Azure / GCP KMS) beyond mocks.
- 28 of 29 chaos-lab profiles under live scan.
- The 28 HUMAN-UAT items, which require live external infrastructure.
