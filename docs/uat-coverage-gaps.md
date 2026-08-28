# UAT Coverage Gaps (Phases 168 + 169)

Generated from `docs/uat-disposition-ledger.jsonl`. One row per case dispositioned `GAP`.

**Totals (series 1-100, Phase 168's 299-row scope):** PASS 142, FAIL 31, DEFERRED 36, SKIP 36, GAP 54. Total 299.

**Totals (series 101-163, Phase 169's 78-row scope):** PASS 60, FAIL 1, DEFERRED 6, SKIP 8, GAP 3. Total 78.

**Combined totals (series 1-163, full 377-row ledger):** PASS 202, FAIL 32, DEFERRED 42, SKIP 44, GAP 57. Total 377.

Note: `SKIP` here is the document's on-disk checkbox state for both `DEFERRED` and `GAP`
ledger outcomes (the canonical result grammar has no dedicated DEFERRED/GAP checkbox;
`scripts/uat_disposition_apply.py` renders both as a checked SKIP box carrying the
full evidence/need string in parens) — the ledger's `outcome` field is the authoritative
distinction between a verified substitute (`DEFERRED`) and an honest absence of coverage
(`GAP`).

## Series 1-100 GAP Rows (Phase 168 — unchanged)

| Case ID | Series | Bucket | Behavior the case asserts | Coverage that would be needed |
|---|---|---|---|---|
| UAT-5-18 | 5 | C | Storage Profile — Vault Transit Keys | no substitute coverage; needs a Vault Transit unit test for an rsa-1024 key type. tests/test_vault_connector.py::test_transit_key_rsa2048_no_severity and test_transit_key_aes256_no_severity cover the rsa-2048/aes256 classification but HashiCorp Vault Transit does not support an rsa-1024 key type at all -- only rsa-2048/3072/4096 -- so the case's own rsa-1024 weak-plus-quantum-vulnerable dual-flag premise may be untestable against real Vault |
| UAT-5-19 | 5 | C | Storage Profile — PostgreSQL pgcrypto Reachability | no substitute coverage; needs a pgcrypto column-level crypto detector, not yet implemented per BACK-12 named in the case's own Pass Criteria. tests/test_db_connector.py covers connection-level SSL/RDS-encryption detection only, not column-level pgp_sym_encrypt usage |
| UAT-7-01 | 7 | F | Dashboard Loads — No Blank Screen | no substitute coverage; needs a headless-browser render check that the SPA mounts without a blank screen or console errors |
| UAT-7-03 | 7 | F | Executive Page — Score Gauge | no substitute coverage; needs a frontend component test asserting the score gauge renders a 0-100 value with EXCELLENT/GOOD/MODERATE/FAIR/POOR label and confidence badge |
| UAT-7-04 | 7 | F | Executive Page — Severity Chart | no substitute coverage; needs a frontend chart test asserting severity counts render and match findings JSON |
| UAT-7-05 | 7 | F | Executive Page — Score Driver Cards | no substitute coverage; needs a frontend test asserting the 4 driver cards render with subscore values totaling <= 100 |
| UAT-7-06 | 7 | F | Findings Page — Table Renders | no substitute coverage; needs a frontend table test asserting findings rows render with the documented columns and row count parity |
| UAT-7-07 | 7 | F | Findings Page — Sorting | no substitute coverage; needs a frontend interaction test asserting column-header click toggles ascending/descending severity sort |
| UAT-7-08 | 7 | F | Findings Page — Filtering | no substitute coverage; needs a frontend interaction test asserting the severity filter input narrows visible rows |
| UAT-7-09 | 7 | F | Findings Page — Detail Slide-out | no substitute coverage; needs a frontend interaction test asserting row click opens a detail slide-out panel with full finding fields |
| UAT-7-10 | 7 | F | Certificates Page — Inventory Table | no substitute coverage; needs a frontend table test asserting the certificate inventory renders with expiry/self-signed indicators |
| UAT-7-12 | 7 | F | Certificates Page — Expiry Sorting | no substitute coverage; needs a frontend interaction test asserting expiry-column sort ordering on the certificates table |
| UAT-7-14 | 7 | F | CBOM Page — Graph Visualization | no substitute coverage; needs a frontend Cytoscape graph render/interaction test for the CBOM page |
| UAT-7-15 | 7 | F | Roadmap Page — DAG Visualization | no substitute coverage; needs a frontend DAG render test asserting NOW/NEXT/LATER color coding on the roadmap page |
| UAT-7-16 | 7 | F | Roadmap Page — Node Detail Panel | no substitute coverage; needs a frontend interaction test asserting node click opens the roadmap detail panel with Why/owner/deps |
| UAT-7-17 | 7 | F | PDF Export — Generate Report | no substitute coverage; needs a headless-browser test that clicks Export PDF and asserts a valid downloaded PDF |
| UAT-7-20 | 7 | F | Dashboard — SPA Routing | no substitute coverage; needs a frontend SPA routing test asserting a direct navigation to /findings renders without a full reload |
| UAT-7-21 | 7 | F | Dashboard Theme — No Hardcoded Colors | no substitute coverage; needs a frontend style-audit test asserting no hardcoded hex colors on major components |
| UAT-7-22 | 7 | F | Dark/Light Theme Toggle | no substitute coverage; needs a frontend interaction test asserting theme toggle persists via localStorage across reload |
| UAT-7-23 | 7 | F | Sidebar Responsive Collapse | no substitute coverage; needs a frontend responsive-layout test asserting sidebar collapse at the 1024px breakpoint |
| UAT-7-24 | 7 | F | Findings Page — Pagination | no substitute coverage; needs a frontend pagination test asserting 25-row pages and working next/prev controls |
| UAT-7-25 | 7 | F | CBOM Page — Algorithm Search | no substitute coverage; needs a frontend interaction test asserting the CBOM algorithm search box filters rows case-insensitively |
| UAT-7-26 | 7 | F | CBOM Page — Quantum Safety Filter | no substitute coverage; needs a frontend interaction test asserting the quantum-safety dropdown filters the CBOM table |
| UAT-7-27 | 7 | F | CBOM Graph — Node Interaction | no substitute coverage; needs a frontend Cytoscape node-click test asserting the detail panel updates per node type |
| UAT-7-28 | 7 | F | CBOM Graph — Zoom Controls | no substitute coverage; needs a frontend interaction test asserting zoom in/out/fit and scroll-wheel controls on the CBOM graph |
| UAT-7-29 | 7 | F | Roadmap — Node Drag | no substitute coverage; needs a frontend drag-interaction test asserting roadmap node drag keeps edges connected |
| UAT-7-30 | 7 | F | Print View | no substitute coverage; needs a frontend render test asserting the /print route renders a single-column layout with page breaks |
| UAT-7-31 | 7 | F | Dashboard Page Title and Branding | no substitute coverage; needs a frontend render test asserting tab title, wordmark, and favicon branding |
| UAT-7-32 | 7 | F | No JavaScript Console Errors — All Pages | no substitute coverage; needs a full-navigation headless-browser test asserting zero console errors across every dashboard route |
| UAT-7-34 | 7 | F | Identity Page — Protocol Summary Cards (No Scan Data) | no substitute coverage; needs a frontend empty-state test asserting the 3 identity protocol cards render Not Scanned without crashing on an empty identity_findings array |
| UAT-7-37 | 7 | F | Findings Page — Protocol Filter | no substitute coverage; needs a frontend interaction test asserting the Findings-page protocol dropdown narrows rows and combines with the severity filter |
| UAT-7-40 | 7 | F | Hardware Tab — Page Loads with Advisory Banner (HWCOMPAT-07) | no substitute coverage; needs a frontend render test asserting the /hardware advisory banner text and sidebar entry |
| UAT-7-41 | 7 | F | Hardware Tab — Device Table with Tier Badges (HWCOMPAT-07) | no substitute coverage; needs a frontend table test asserting hardware device columns, tier badge colors, and tier-then-vendor sort order |
| UAT-8-04 | 8 | F | Hygiene Subscore — Plaintext Ratio | no substitute coverage; needs a scoring unit test isolating the hygiene subscore specifically, not the overall score, below 25 when plaintext HTTP endpoints exist, proportional to count |
| UAT-8-05 | 8 | F | mTLS Bonus — Identity Trust Subscore | no substitute coverage; needs a scoring unit test isolating the identity_trust subscore increase attributable to mtls_present_count alone, holding all other evidence fixed |
| UAT-9-06 | 9 | F | HTML Report — Visual Quality | no substitute coverage; needs a visual/browser render check of the HTML report dark theme, layout, and mobile responsiveness |
| UAT-11-02 | 11 | C | Multi-Profile Lab Run — Progressive Discovery | no substitute coverage; needs a multi-run progressive-discovery integration test covering score/CBOM growth across successive scans as chaos-lab profiles are added, plus dashboard-reflects-latest-scan-on-refresh -- this is cross-run integration behavior with no single-scan unit-test equivalent |
| UAT-36-04 | 36 | F | Executive summary shows 6 ScoreGauges with Data in Motion last | no substitute coverage; needs a frontend render test asserting exactly 6 ScoreGauge elements with Data in Motion last and an integer value |
| UAT-39-02 | 39 | F | Empty state per section when no DAR data | no substitute coverage; needs a frontend render test asserting the 4 DAR section EmptyStateCards show their scanner-specific locked copy |
| UAT-39-03 | 39 | F | Database table renders with locked columns | no substitute coverage; needs a frontend table test asserting the DatabaseTable's exact 9-column locked set and severity sort |
| UAT-39-04 | 39 | F | Object Storage table renders with locked columns | no substitute coverage; needs a frontend table test asserting the ObjectStorageTable's exact 10-column locked set and em-dash null rendering |
| UAT-39-05 | 39 | F | Kubernetes table renders with locked columns | no substitute coverage; needs a frontend table test asserting the KubernetesTable's exact 8-column locked set and severity sort |
| UAT-39-06 | 39 | F | Vault table renders with locked columns | no substitute coverage; needs a frontend table test asserting the VaultTable's exact 8-column locked set with Seal Type/Auto-Unseal em-dashes |
| UAT-41-03 | 41 | C | lab.sh Profile-Tagged Service Sweep on `down` and `reset` | no substitute coverage; needs a live docker-compose orphan-sweep integration test verifying lab.sh down/reset leave zero quirk-lab containers -- inherently requires running Docker, out of scope per D-01 |
| UAT-47-04 | 47 | C | Wizard Nmap y/N Prompt Appears Once (DISCOVER-01) | no substitute coverage; the interactive nmap y/N wizard prompt this case describes no longer exists in run_scan.py -- it was superseded by the --discovery builtin-or-nmap CLI flag per D-09, Phase 47/121, so there is no prompt-count code path left to unit test |
| UAT-48-02 | 48 | F | HTML All Findings Table Includes Description Column (CONTEXT-02) | no substitute coverage; the only candidate, tests/test_reports_writer.py::test_html_report_has_description_column, is unconditionally skipped per TRIAGE-149 Playwright flakiness, and a skip is not proof of coverage; needs that flake fixed or a non-Playwright equivalent |
| UAT-50-03 | 50 | F | Obsidian vault sync produced both Reference notes with correct frontmatter (DOCS-03) | no substitute coverage; needs a filesystem check of the Obsidian vault Reference notes and _QUIRK-Hub.md wikilinks, which lives outside the repo and is not reachable from pytest |
| UAT-67-04 | 67 | F | ScannerStatusCard renders on Executive page when failures exist (RESUME-02) | frontend component test for ScannerStatusCard needed -- partial_failures render, badge severity, aria-labels; no component or test file exists yet, grep found zero hits; structurally a frontend-only case per 168-07's guard-boundary finding |
| UAT-85-08 | 85 | C | Real dashboard hero screenshot replaces placeholder (LAUNCH-01) | no substitute coverage; needs a real browser screenshot capture of the live dashboard, a release-time manual step with no unit-test equivalent |
| UAT-88-02 | 88 | F | Score Decomposition renders in the HTML report (SCORE-XPARENCY-01 / RENDER-PDF-01) | no test asserts the HTML report actually renders the six-row subscore decomposition table, /25 per row, divide-by-1.5 rollup -- quirk/reports/templates/report.html.j2 lines 409-420 emit exactly this markup, but only data-layer parity in test_score_render_parity.py and markdown presence in test_score_transparency.py are covered by pytest, not the HTML template render output itself |
| UAT-88-03 | 88 | F | Score Decomposition renders in the Playwright PDF (RENDER-PDF-01) | no pytest coverage exists for PDF rendering of the decomposition table at all -- Playwright PDF generation is not exercised by any test; same underlying gap as UAT-88-02 one layer further downstream |
| UAT-89-01-01 | 89 | C | three new weak-TLS profiles start and auto-register (LAB-01/02/04) | no substitute coverage; needs a live docker-compose bring-up plus healthcheck of the postgres-tls/redis-tls/kafka-tls chaos-lab profiles, inherently requiring Docker, out of scope per D-01 |
| UAT-92-01 | 92 | F | Local annotated v5.0.0 tag created at final close-out HEAD (REL-01) | case is a one-time historical release gate for the v5.0.0 tag creation event from Phase 92, already completed per its own Notes field -- tag created locally after operator approval; running its Automated gate today against the current v5.15.0 state naturally fails 2 of 5 checks -- pyproject version now 5.15.0, and the v5.0.0 tag has since been pushed to origin by a later release -- this is expected temporal drift from 15+ subsequent releases, not a live coverage gap, but no substitute test can re-verify a historical one-time event |
| UAT-96-08 | 96 | C | `fuzz-target` chaos profile appears in `./lab.sh profiles` (LAB-01) | no substitute coverage; needs a live docker-compose bring-up of the fuzz-target chaos-lab profile plus live HTTP checks against its openapi.json, jwks.json, and probe endpoints, inherently requiring Docker, out of scope per D-01 |

**54 GAP rows total** (out of 299 in Phase 168's ledger scope).

## Series 101-163 GAP Rows (Phase 169)

| Case ID | Series | Bucket | Behavior the case asserts | Coverage that would be needed |
|---|---|---|---|---|
| UAT-104-04 | 104 | A | Jira SSRF guard — internal URL blocked without `allow_internal` (TICKET-03) | no substitute coverage; the case's own `-k ssrf` filter against `tests/test_ticketing_jira.py` matches 0 of 8 collected tests — none exercise an internal/RFC1918 `jira_url`. `quirk/ticketing/jira.py` wiring confirmed via grep (`validate_external_url` x3, `allow_internal` x1) but that is source inspection, not an executed test; needs a new test constructing a `JiraChannel` with an internal URL and asserting `validate_external_url` raises |
| UAT-134-01 | 134 | C | CBOM Page — Hardware Inventory `[DEVICE]`/`[FIRMWARE]` labels (Manual) | no substitute coverage; the case's core assertion is the React `HardwareInventory` component's two-badge-per-device render and tier-color logic in `src/dashboard/src/pages/cbom.tsx` — zero vitest coverage exists anywhere under `src/dashboard/src/pages/__tests__/` for this component; only a backend data-shape test exists, proving the API payload but not the frontend render; needs a new `HardwareInventory` vitest test |
| UAT-152-01 | 152 | C | `segmented-network` chaos lab profile smoke test (DISC-09) | no substitute coverage; the case's assertion is live network-layer behavior — a real iptables-REJECT gateway producing genuine TCP RST on a dead subnet versus a genuine open TLS port on a live segment — existing nmap tests parse pre-canned text output and cannot substitute for a live-fire network assertion; needs a live Docker run of the `segmented-network` chaos-lab profile |

**3 GAP rows total** (out of 78 in Phase 169's ledger scope).

## Additional Gaps and Guard Limitations Surfaced During the Drain

These findings are not individual `GAP` ledger rows but structural or guard-level
discoveries from Plans 03-08 that Phase 170's traceability work needs to act on:

1. **Anti-fabrication guard defect — `NODE_REF_RE` cannot span a second `::`** (168-06).
   Class-based substitutes had to be cited with the `ClassName*method_name` glob
   workaround instead of the natural `Class::method` pytest node syntax. This is a
   guard bug in `tests/test_uat_disposition_integrity.py`, not a data problem.
2. **Anti-fabrication guard limitation — `NODE_REF_RE` only resolves pytest node IDs**
   (168-07). Real, passing frontend vitest coverage under
   `src/dashboard/src/**/__tests__/*.test.tsx` is structurally ineligible as a DEFERRED
   substitute even when it directly covers the same component. This inflates the GAP
   count: 31 of 168-07's 42 GAPs are series-7 dashboard UI cases that may in fact be
   covered by existing vitest tests the guard cannot currently cite. Highest-value guard
   fix for a future phase.
3. **16 product/documentation FAILs from buckets D+E** (168-05) — dashboard score not
   tracking `--score-profile`, a run-stats key that never disappears when broker
   scanning is disabled, unconditional email-port probing breaking a documented
   empty-state, an undocumented "Hardware" sidebar item breaking the D-11 nav-order
   lock, an unenforced `--fuzz-budget` 500 maximum, a non-hard-aborting non-TTY
   `--fuzz` path, and a raw-URL-disclosure gap in an error message.
4. **`UAT-1-02` FAIL is caused by a stale hardcoded version-substring check inside
   `uat_runner.py` itself** (168-03) — a genuine finding about the runner's own
   staleness, not a product regression. Not fixed (`uat_runner.py` out of scope this
   phase).
5. **Chaos-lab premise findings** (168-06): Vault Transit has no `rsa-1024` key type
   (UAT-5-18 may be untestable as written); pgcrypto column-level detection is
   unimplemented (BACK-12, UAT-5-19); the interactive nmap y/N wizard prompt
   (UAT-47-04) no longer exists in `run_scan.py`, superseded by the `--discovery` flag.
6. **`UAT-48-02`** (168-07) — its only candidate substitute
   (`tests/test_reports_writer.py::test_html_report_has_description_column`) is
   permanently skip-marked (TRIAGE-149) and was correctly rejected as evidence rather
   than accepted as a false-green DEFERRED.
7. **`UAT-88-02`/`UAT-88-03`** (168-08) — the HTML/PDF report's six-row subscore
   decomposition table (`quirk/reports/templates/report.html.j2` lines 409-420) has no
   pytest coverage at the render-output-content level; only data-layer parity
   (`test_score_render_parity.py`) and markdown presence (`test_score_transparency.py`)
   are covered. PDF rendering (Playwright) has zero pytest coverage of this table at
   all.
8. **`UAT-92-01`** (168-08) — a one-time historical release gate for the v5.0.0 tag
   creation event (Phase 92); its automated shell gate now fails against the current
   v5.15.0 state (version string moved on, tag has since been pushed to origin by a
   later release). Expected temporal drift from 15+ subsequent releases, not a live
   product defect, and not re-verifiable by any substitute test since the event it
   checks already happened and is not repeatable.
9. **`UAT-58-01`/`UAT-58-02`** (168-08) — the DEFERRED substitutes
   (`tests/test_api_auth.py`) verify the correct security behavior (401/403, no
   missing-vs-wrong-token oracle leak) but the actual response body is now wrapped in
   the `[QRK-DASHBOARD-00N]` error-code format rather than the case's literal
   `{"detail": "Authentication required"}` / `"Missing CSRF header: X-Quirk-Request"`
   strings — a documentation drift, not a coverage or security gap.
10. **`UAT-104-04`'s SSRF guard is wired but never exercised** (169-03) — Security-relevant.
    `quirk/ticketing/jira.py`'s `validate_external_url`/`allow_internal` wiring is confirmed
    present by source inspection, but the case's own `-k ssrf` filter matches zero of the 8
    tests in `tests/test_ticketing_jira.py`. No test anywhere in `tests/` constructs a
    `JiraChannel` with an internal/RFC1918 URL to prove the guard actually raises. Flagged
    for Phase 170.
11. **`UAT-110-06`'s own worked example is impossible** (169-04) — recorded FAIL, not GAP,
    because the underlying feature was independently confirmed working. The case's literal
    `--stale-days 1` reproduction can never trigger the documented `coverage_warning` line:
    `stale_days=1` excludes any sensor silent more than 1 day, while the default
    2x-expected-cadence overdue threshold is 48h — the two thresholds are mathematically
    incompatible in the case's own worked example. Re-running the identical `quirk sensor
    merge` command with the default `stale_days=30` and a sensor silent 3 days correctly
    printed the WARNING line. This is a defective test case / documentation defect, not a
    `merge_scan()`/`coverage_warning` implementation defect. A defective-worked-example
    finding, not a coverage gap.
12. **Vitest slow leg does not run in CI** (169-02). The new vitest dialect (`VITEST_REF_RE`,
    `_run_vitest_nodes`, `parse_vitest_summary` in `tests/test_uat_disposition_integrity.py`)
    verifies substitute execution locally, but the `Linux Full Suite` job
    (`.github/workflows/python-ci.yml:399`, `pytest -q -m ""`) never installs Node/npm for
    `src/dashboard/`, so `VITEST_TOOLCHAIN_AVAILABLE` is `False` there and vitest substitutes
    are existence-checked only in CI, never executed. This is the same existence-vs-execution
    asymmetry D-05 set out to remove for pytest substitutes, reappearing one layer down at the
    CI layer for vitest substitutes specifically. A `dashboard-quality.yml` workflow already
    exists in this repo and may be the right home for a Node-toolchain slow-leg CI job.
    Flagged for Plans 169-07/169-08.
13. **`scripts/uat_disposition_apply.py`'s `cmd_classify` data-loss bug** (169-01) — the
    `classify` subcommand built its output solely from `in_scope_undispositioned()` and then
    called whole-file `write_ledger()`, so the first `classify` run after raising
    `MAX_SERIES` wiped the ledger from 299 rows to 78 rows (dropping every already-
    dispositioned Phase 168 row). Caught pre-commit during Phase 169 planning and fixed with
    a seed-then-overlay approach. Latent for the entirety of Phase 168 because `classify` had
    only ever run once before, against an empty ledger. A tooling-integrity finding, not a
    product/coverage finding, but load-bearing for trusting the ledger's own history.
14. **377 ledger rows are a strict subset of the document's 647 series-1-163 headings**
    (169-05 independent recount). An independent from-scratch parser confirmed 666 total case
    headings / 666 Result blocks in `docs/UAT-SERIES.md`, of which 647 have series ≤163 and
    zero remain undispositioned. Only 377 of those 647 in-scope cases are tracked by the
    disposition ledger — the remaining 270 were already dispositioned through each phase's own
    original UAT-verification pass (e.g. series 101-163 phases that ran their own
    `/gsd:verify-phase` before Phase 168/169's ledger tooling existed), never through the
    ledger/apply/verify pipeline. This fully accounts for the gap between 169-CONTEXT.md's
    233-case estimate for series 101-163 (155 already dispositioned + 78 remaining) and the
    document's actual 214 series-101-163 headings with series >100 — the CONTEXT figure of
    233 predates a precise document-based recount and should not be treated as ground truth
    going forward; the document itself (666 headings, 0 undispositioned) is.
15. **D-05 second half spent: all 31 series-7 GAP rows re-examined against real vitest
    coverage, zero converted** (169-06). Finding #2 above flagged that `NODE_REF_RE`'s
    pytest-only shape structurally excluded genuine frontend vitest coverage as a DEFERRED
    substitute, inflating the series-7 GAP count by up to 31 cases. 169-02 built the vitest
    dialect (`VITEST_REF_RE`, `find_unresolvable_vitest_refs`, `_run_vitest_nodes`,
    `parse_vitest_summary`); this plan spent it. All 21 `.test.tsx` files under
    `src/dashboard/src/**/__tests__/` were enumerated and every `it()`/`test()` title read
    against each of the 31 cases' "coverage that would be needed" text. None genuinely cover
    the case's specific assertion:
    - `UAT-7-01`, `UAT-7-17`, `UAT-7-32` describe headless-browser/real-PDF/full-navigation
      behavior jsdom cannot structurally exercise — no vitest substitute is possible for
      these regardless of what future tests get written.
    - `UAT-7-03` (`ScoreGauge.test.tsx`) only asserts numeric text and SVG stroke color, never
      the EXCELLENT/GOOD/MODERATE/FAIR/POOR label or confidence badge the case requires.
    - `UAT-7-06` (`findings-columns-memo.test.tsx`) only asserts `columns` is wrapped in
      `useMemo`, not that rows render with the documented columns/row-count parity.
    - `UAT-7-14`/`UAT-7-27` (`cbom-cytoscape-catch.test.tsx`) only assert `console.error`
      logging on `cytoscape.use` failure, never actual graph render or node-click interaction.
    - `UAT-7-22` (`theme-provider.test.tsx`) only asserts the `getStoredTheme` read-side
      allowlist function directly (no toggle click, no rendered toggle button, no reload
      simulation), not the case's click-toggle-then-persist-across-reload workflow.
    - `UAT-7-30` (`print-no-createElement.test.tsx`, `print-pdf-cleanup.test.tsx`) only assert
      the PRINT_CSS JSX-vs-`createElement` implementation detail and the `data-ready` sentinel,
      never single-column layout or page-break rendering.
    - `UAT-7-34` has a same-shaped test (`sensors-loading.test.tsx`) but for a different page
      (Sensors, not Identity) — same component pattern, wrong subject, rejected as a
      filename/pattern-coincidence match per this phase's explicit standard.
    - The remaining 23 cases (`UAT-7-04`, `-05`, `-07`, `-08`, `-09`, `-10`, `-12`, `-15`,
      `-16`, `-20`, `-21`, `-23`, `-24`, `-25`, `-26`, `-28`, `-29`, `-31`, `-37`, `-40`,
      `-41`) have no existing vitest test file that even superficially targets their page or
      interaction — no candidate to evaluate at all.

    All 31 rows stay `GAP`, unchanged, with the reasoning above recorded per-case in the SUMMARY
    (`.planning/phases/169-uat-record-drain-series-100-163-enforcement/169-06-SUMMARY.md`). Per
    this plan's own instruction, "converting 31" was never the target — "every row's disposition
    is true" was, and zero genuine substitutes exist today. Writing the missing vitest tests
    themselves remains out of scope (see "Closing the 54 GAPs by writing the missing tests" in
    169-CONTEXT.md's Deferred Ideas) and is the actual, still-open follow-up work.
