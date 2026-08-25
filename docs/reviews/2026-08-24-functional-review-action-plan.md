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
| ☑ | RVW-001 | CRITICAL | Every TLS/certificate and email endpoint is persisted twice — `merge()` at `run_scan.py:3190` re-inserts rows already written by `_flush_stage_endpoints()` | core value path; all inventory counts | The scan pipeline must persist exactly one row per scanned endpoint per scan session. Root cause is a false assumption that `session.merge()` writes the PK back onto the passed object; it does not. See fix options below. Add a regression test asserting a single-host scan yields no two rows differing only in `id`. | S–M | **Done** (`8d3e7f7`) — option A; 3 tests |
| ☐ | RVW-002 | HIGH | The dashboard runs a second finding engine that lacks self-signed and untrusted-CA detection and escalates RSA-1024 to CRITICAL | dashboard `/findings`; operator-vs-client consistency | The dashboard and the report must present the same findings at the same severities. `routes/scan.py` should consume `findings_evaluator` rather than hand-rolling ~20 titles of its own. Add a cross-surface parity test asserting the dashboard and report agree on title and severity for a fixed endpoint set. **Severity revised CRITICAL → HIGH after re-verification: the client deliverable was never affected.** | M | Open |
| ☑ | RVW-003 | HIGH | Scan sessions have no stored identity — `CryptoEndpoint` has no `scan_run_id`, so membership is reconstructed from wall-clock time; one scan renders as several history rows with contradictory scores (92/100/93) | Scan History, Trends, per-session scores | A scan session must be identified by a stored key, not inferred from timestamps. Add `scan_run_id` to `CryptoEndpoint` (the column already exists on `ScanJob` and `ScanCheckpoint`) and group `list_scans()` / trends by it instead of 1-second truncation. No endpoint may persist with a NULL `scanned_at` — those rows are currently invisible to Scan History. Add a test asserting one scan yields exactly one history row. **Fix direction revised after re-verification — see note.** | M | **Done** (`fb23b0d`) — 9 tests |

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
| ☑ | RVW-004 | HIGH | v5.13 and v5.14 declared shipped but never released; v5.14 tag contains `version = "5.12.0"` | release integrity; sensor version reporting | Either publish v5.13/v5.14 properly (bump `pyproject.toml`, run the release workflow) or correct ROADMAP.md to stop claiming they shipped. A milestone must not be markable ✅ shipped without a successful release run. | M | **Done** (`cf08399`, `851328f`) — record corrected; trigger trap fixed |
| ☑ | RVW-005 | HIGH | Three of four CI workflows red on `main`; the last 19 commits have never run CI | entire verification discipline | Restore all four workflows to green and establish that CI runs on every push to `main`. ~~Investigate why no workflow triggered~~ — **root cause found and it is not a trigger fault: there were 32 unpushed commits.** CI's push trigger works; scheduled runs fired throughout. Pushed 2026-08-25; CI runs on every push again. Python CI's two failures were RVW-017 and RVW-006/022, both now fixed. | M | **Root cause resolved** — Release Tag Hygiene still red (RVW-004/016) |
| ☑ | RVW-006 | HIGH | A sixth CI-gated staleness catalog (CMVP) is undocumented — and is the one currently failing | maintenance runbook | Add CMVP, error-codes and SNMP-contract catalogs to CLAUDE.md's Staleness Review Cadence so the runbook matches `python-staleness.yml`. ~~Do NOT run `quirk compliance cmvp refresh` until RVW-022 is fixed~~ — **unblocked**: RVW-022 fixed in `a7cf302` and the refresh has been run safely; cache `last_verified` is current. Catalog documentation in CLAUDE.md still outstanding. | S | **Partly done** — refresh unblocked and run; CLAUDE.md rows still to add |
| ☑ | RVW-022 | HIGH | `quirk compliance cmvp refresh` silently empties the algorithm list of every FIPS 140-3 module (6/6 sampled); `_fetch_cert_detail` looks for `table#fips-algo-table`, absent on 140-3 pages, and returns `[]` instead of raising | compliance attestation; client reports | `_fetch_cert_detail()` must parse FIPS 140-3 certificate pages, and must raise `CMVPRefreshParseError` when the expected structure is absent rather than returning an empty algorithm list. Add a regression test asserting a known 140-3 cert yields a non-empty algorithm list. **Blocks RVW-006.** | M | **Done** (`a7cf302`) — 22 tests; see correction below |
| ☑ | RVW-017 | MEDIUM | Test isolation is illusory — 31 test files share one process-wide in-memory DB via `cache=shared`; `test_get_schedules_empty` fails after `test_otics_cadence_floor.py` writes a schedule | suite reliability; CI trust | The `dashboard_client` fixture must give each test an isolated database, as its docstring already claims. Options: a per-test unique shared-cache name (`file:test_<uuid>:?cache=shared`), or truncate tables in fixture teardown. **Raised OBSERVATION → MEDIUM: the stated cause (random ordering) was wrong — `pytest-randomly` is not installed — and the real cause affects 31 files.** | M | **Done** (`034da44`) — unique-name option; also un-skipped 3 tests |

---

## Theme 3 — Test & Gate Robustness

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-011 | MEDIUM | E2E smoke cannot pass on a developer machine (140s scan vs 120s budget) | developer trust in the suite | `npm run e2e:smoke` must pass on a machine with services listening on common ports — raise the timeout, narrow the scan scope, or pin the port scope for E2E. | S | Open |
| ☐ | RVW-012 | MEDIUM | **291 accessibility violations permanently accepted** across all 11 baselines (286 color-contrast, 3 button-name, 2 scrollable-region-focusable); 0 of 11 routes clean; the gate also breaks on browser upgrades | accessibility; gate value | Triage the accepted set — the 3 `button-name` failures are screen-reader blockers and should be fixed, not baselined. Record impact/WCAG level in the baseline so acceptance is a decision, not an accumulation. Key baselines on something stabler than axe's full CSS-selector path, and pin `@axe-core/puppeteer` exactly rather than `^`. **Raised LOW → MEDIUM: scope was understated (23 → 291).** | M | Open |
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
| ☑ | RVW-013 | LOW | Version strings stale in README, UAT-SERIES, pyproject; absent from getting-started | user-facing docs | Resolve as part of RVW-004; add getting-started to the version-drift checklist. | S | **Resolved by RVW-004** — see note |
| ☐ | RVW-014 | LOW | Four requirement formats and five UAT result formats across the corpus | tooling fragility | Adopt one requirement declaration format and one UAT result format for new documents. Backfilling archives is optional. | M | Open |
| ☐ | RVW-015 | LOW | Five archive documents record no completion status (v4.10, v4.3, v5.1, v5.12, v5.4) | doc accuracy | Add a `**Status:**` header to each. **The numeric-contradiction half of this finding was withdrawn on re-verification — v5.7's header matches its contents exactly and v4.6 is off by one.** | S | Open |
| ☑ | RVW-016 | LOW | Release tag naming inconsistent (`v5.14` vs `v5.12.0`) | tooling | Adopt one tag convention going forward. | S | **Done** (`cf08399`) — same defect as RVW-004, not a separate one |
| ☐ | RVW-018 | OBS | Planning summaries reference siblings by pre-archive path (16 broken refs) | planning hygiene | Reference phase artifacts by a path that survives archival, or rewrite on archive. | S | Open |
| ☐ | RVW-019 | OBS | GAUGE-01/02/03 have no traceability link (code verified correct) | traceability | Annotate `ScoreGauge.test.tsx` with the GAUGE requirement IDs. | S | Open |

---

## Remediation Progress

**Milestone A — Scan Integrity: complete.** Both findings that corrupt the
client-facing deliverable are fixed, tested, and committed.

| ID | Commit | What landed |
|---|---|---|
| RVW-001 | `8d3e7f7` | Option A — `_flush_stage_endpoints` writes the merged PK back onto the caller's object, so the final `db_persist` UPDATEs instead of INSERTing. 3 regression tests. |
| RVW-003 | `fb23b0d` | `CryptoEndpoint.scan_run_id` added via `_ADDITIVE_MIGRATIONS` + explicit index; every write site stamps it; `list_scans`, `compare_scans`, trends and `GET /api/scan/latest?scan_id=` group and resolve on it. Legacy rows keep timestamp grouping. 9 regression tests. |

Backend suite after both: **3499 passed**, with the same 3 failures the pre-fix
baseline produced — `test_cmvp_cache_not_stale` (RVW-006/RVW-022) and two
order-dependent `test_verify_phase_gates` failures (RVW-017). No regressions.

Two notes for whoever picks up the next milestone:

- **RVW-001 option B is now viable.** `scan_run_id` gives the natural key the
  stable component `scanned_at` could not, exactly as the sequencing note
  anticipated. It was not adopted — option A alone makes the tests pass — but
  the blocker is gone if defence in depth is wanted.
- **RVW-017 was observed directly.** The two `test_verify_phase_gates` failures
  pass in isolation and fail in full-suite context, confirming the finding's
  revised root cause (shared process-wide database, not random ordering).

---

### RVW-022 — corrections after implementation

Three claims in the finding did not survive verification against live NIST pages
on 2026-08-25:

| Claim | Reality |
|---|---|
| "absent on 140-3 pages" | The shape varies **per certificate**, not per FIPS level. Certs 4523 and 4884 are both 140-3; only 4523 has `table#fips-algo-table`. |
| "6/6 sampled" | Of six sampled, **three** parsed correctly and three returned `[]`. Across the full curated set the real figure is **11 of 53**. |
| implied single failure mode | There are two page shapes plus a third case — certificates that publish **no** algorithm data at all (cert 5263). Those cannot be fixed by parsing; `refresh` now preserves their last verified list. |

Two things the finding did not mention, both found while diffing the refresh:

- **The old cache was not a faithful scrape.** Certs 4523 and 4884 carried
  byte-identical 12-family lists despite completely different pages, and 30
  modules claimed families NIST does not publish (cert 4339's page lists exactly
  AES, CKG, DRBG, RSA, SHS; the cache also claimed ECDSA and HMAC). The refresh
  therefore *reduces* claimed coverage — which is the correct direction for a
  compliance tool, since over-claiming CMVP coverage is the dangerous error.
- **A spelling split made six modules unmatchable.** The cache held both
  `Triple-DES` and `TripleDES`; `normalize_for_cmvp_lookup()` emits only the
  latter, so the six modules under the other spelling could never match a 3DES
  query. Canonicalised — 3DES coverage went from 7 modules to 18.

### RVW-017 — what it had already cost

Beyond the CI failure, three tests were sitting permanently `xfail` in
`skip_registry.py` with "shared in-memory SQLite cache pollution" recorded as
the cause (`test_dashboard_trends.py` and two in
`test_sensor_push_id_revalidation.py`). With the root cause fixed, all three
markers and registry rows were removed and all three now pass.

---

### RVW-004 / RVW-016 / RVW-013 — one defect, not three

RVW-016's "inconsistent tag naming" **is** RVW-004's "never released".
`release.yml` triggered on `v*.*.*` — three components — so a two-component tag
matched nothing, fired no workflow, and raised no error. Three occurrences:
`v5.9` (already recorded in the hygiene baseline), then `v5.13` and `v5.14`.
`v5.13` was additionally never pushed to origin.

Verified 2026-08-25: PyPI's latest is `5.12.0`; both the `v5.13` and `v5.14` tags
contain `version = "5.12.0"`; the last successful release run was `v5.12.0` on
2026-08-14.

**RVW-013 dissolved on correction.** It flagged `pyproject.toml` and README as
carrying a stale `5.12.0`. Once ROADMAP stopped claiming v5.13/v5.14 shipped,
`5.12.0` is the *correct* value — it is the last released version, and
`docs/release-process.md` makes `pyproject.toml` the single source of truth
(`quirk/__init__.py` derives `__version__` from package metadata). The bump
belongs to the v5.15 release itself. `docs/getting-started.md` carrying no
version string is likewise correct, not a gap — fewer duplicated version
surfaces is the stated design.

Fixed the trap rather than the convention: `push.tags` is now `v[0-9]*`, matching
what `scripts/release_tag_hygiene.py` already treats as release-like, so the two
cannot disagree about what a release tag is. A new test asserts that agreement.

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
shippable. **Correction: RVW-006 is not the quick win this plan originally called it.** Its
prescribed fix would corrupt the CMVP cache (RVW-022), so RVW-022 must land first. The
correct immediate step is investigating why CI has not triggered since 2026-08-19 (RVW-005),
which requires no data changes at all.

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
