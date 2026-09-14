# HORIZON.md — Multi-Milestone Outlook

**Purpose:** Themes for the next 5–7 milestones — deep enough to anchor backlog grooming and inter-milestone deferrals, shallow enough to revise after each ship. **Plan the next one or two in detail; sketch the rest.**

**Last updated:** 2026-09-13 (v5.24 boundary pass — **v5.24 UAT Coverage Drain OPENED**, Phases 203–208, honouring the commitment made at the v5.23 boundary. Live re-derivation corrected the worklist's own headline number: 70 GAP-annotated cases across 878, not the 57 the worklist claims for series 1–163, with 25 accumulated in series 164–202 it has never absorbed. 999.110 and 999.107 considered and deliberately deferred with reasons recorded in the rationale log.)
**Current state:** The hardware-lifecycle arc is closed. v5.13 (Phases 154–156) built the drift/EOL engine, v5.14 (157–160) closed its fleet-coverage and forecasting gaps, and v5.15 (161–163) drained the last four backlog items — shipping as the first published release since 5.12.0, after v5.13/v5.14's two-component tags silently missed `release.yml`'s glob entirely. **ROADMAP.md's `## Backlog` is now genuinely drained**: nothing remains unpromoted except the parked SaaS block. **v5.16 Review Drain & Gate Integrity is now open** (Phases 164+) — the ops cycle the 2:1 cadence has owed since v5.12, closing the open findings from the 2026-08-24 third-party functional review. See rationale log below. Themes past v5.16 are sketched fresh in this pass (Forward Outlook, revised 2026-08-26). SaaS multi-tenancy stays parked (no business-model signal, unchanged since v5.4).

---

## Open-Item Ledger — canonical as of 2026-09-11 (v5.23 boundary pass)

**This section is the single source of truth for open items.** The archived roadmaps' `## Backlog`
tables and the `.planning/backlog/999.*` directories are historical archives only — the
reconciliation audit (`.planning/reports/backlog-reconciliation-2026-09-07.md`) classified all 92
BACK-* IDs with per-item evidence: ~92% shipped/obsolete, the residue below. An item leaves this
table only by shipping (cite the phase) or by a recorded obsolescence decision. The planned
**derived gate** (todo `backlog-reconciliation-and-derived-gate.md`, step 3) will enforce that no
BACK-*/999.* ID is neither closed-with-evidence nor listed here; it must key on **title+ID**
(BACK-68 names two unrelated items) and count requirement-section-heading citations as closure.

| Item | Priority | What it is | Source / notes |
|---|---|---|---|
| **999.115** | **P1** | **RESOLVED 2026-09-14** on branch `scoring-999.115-model-fix` (tag `pre-999.115-scoring-model` marks the pre-change state; `main` untouched throughout). **Six model changes, chosen by measurement against an operator-set calibration ladder rather than by argument** — `58f58a13` P8 undetermined key types, `1b1e114d` P5c driver/headline agreement, `d92e928b` C the absolute consequence ceiling (COMPRESSED, never clamped), `523dd818` the PQC ceiling + prevalence curve D + removal of `agility_high_impact_ratio`, `c47aa6c1` the compression-range fix below, `e63fe1e9` `SCORING_VERSION` 2.0 -> 3.0. **Ladder 5/5 against blind-set targets:** R1 100 EXCELLENT / R2 78 GOOD / R3 46 FAIR / R4 24 POOR / R5 (the 31-host estate) 87 -> **18**, against this row's own <40 target, later tightened to <30. Every capped score discloses what capped it and its uncapped value via `rating_cap_reason`. Phase 184.4 D-03 superseded (operator-approved), rationale preserved at `.planning/decisions/999.115-severity-caps-the-number-supersedes-184.4-D-03.md`. **Seven properties promoted xfail->green** in `tests/test_score_properties.py` (P1, P4, P7a, P7b, ladder R2/R3/R4). **The prior's B+C call was half right:** C (absolute severity) landed and is load-bearing; B (start-at-zero) was never needed once C existed; D shipped as a supporting curve rather than as the fallback. **Two findings worth carrying forward.** (1) *Compression is not clamping, and it is not piecewise either.* A hard `min(score, ceiling)` made the score INERT on capped estates (remediation lift +0, all three profiles collapsed to one number); compressing only ABOVE the ceiling then put a 13-point CLIFF exactly at it, so every estate computing 85-100 scored below one computing 84 — a live P1 violation caught by `test_identity_surface::test_weak_kerberos_lowers_score`, which a prior session had listed as a stale pin to repair. It was not stale. Both defects were found by measurement, neither by inspection. (2) **P2b is NOT closed** and is the last open property — observing more healthy endpoints still dilutes the score (computed 71 -> 74 -> 78 -> 82 with every weakness count held identical), a denominator problem in `assessable_endpoint_count` that the ceiling MASKS in the emitted number but does not fix. Filed at `.planning/todos/pending/p2b-healthy-endpoints-dilute-the-readiness-score.md`. **Standing caveat: four of the ladder's five rungs are synthetic** — the SHAPE (consequence must be absolute) is well evidenced, the CONSTANTS are a first fit; add real-scan rungs before treating the thresholds as settled. Original description follows. **The readiness score's USABLE RANGE is ~85-100, so real-world badness is compressed into the top 15 points and reads as a B+.** Successor to 999.113, which is CLOSED and was necessary but NOT sufficient. **Measured 2026-09-13 against the fixed scorer:** a PERFECT estate scores **100**; a MAXIMALLY BROKEN estate — every ratio driven to 1.0, i.e. every endpoint plaintext, every cert expired, every protocol UNKNOWN — scores **19**. So the floor IS reachable in principle. But no real estate drives ratios near 1.0: the 31-host purpose-built vulnerable lab runs 0.26 plaintext, 0.29 expired certs, 0.42 legacy TLS, and lands at **87/FAIR**. **The model reserves ~80% of its scale for estates that cannot exist.** Root cause is the transfer function, not the range: `penalty = ratio x weight` is LINEAR, so it treats 30%-of-certs-expired as exactly six times worse than 5%. No consultant reads it that way — 5% expired is hygiene drift, 30% is an organisation that has lost control of its PKI. Alarm is steeply non-linear in prevalence; the scorer models it as a straight line through the origin. **Second, independent gap: the model has no concept of CONSEQUENCE, only PREVALENCE.** Nothing distinguishes 5 CRITICALs in a 17-host estate from 5 CRITICALs in a 500-host estate. `cap_band_for_severity()` already compensates for exactly this — but only on the BAND, capping at FAIR with no ladder, which is why the product's strongest possible statement about a catastrophic estate is the incoherent "87 — FAIR". **Four candidate shapes, to be chosen by MEASUREMENT against the calibration ladder, not by argument:** (A) larger weights — right diagnosis, blunt instrument, punishes ordinary estates alongside catastrophic ones and collides domains at 0; (B) start-at-zero / earn-points — removes the structural "innocent until proven guilty" default that produced BOTH 999.95 and 999.113, and is far cheaper than it first appears because **every ratio already computed has a complement** (`plaintext_http/assessable` implies "endpoints using TLS"; `expired/certs_observed` implies "certs valid") — no new detection needed, only counting the good side of predicates already evaluated; (C) an absolute severity term, `min(prevalence_score, severity_ceiling)`, extending `cap_band_for_severity`'s existing reasoning from the band to the number; (D) a non-linear ratio->penalty curve — the minimal targeted fix, keeps every existing structure. Prior: **B + C**, with D as the fallback if B proves too large to land safely. | **Filed 2026-09-13** by the operator during the demo-readiness pivot, from the observation that decides it: *"most people will see 87 and say not bad."* The requirement is not "is the arithmetic defensible" but **"does the number carry the meaning"** — a 0-100 scale arrives pre-loaded with school-grade semantics that no band label or findings table overrides. **Do NOT pick a model in the abstract.** The P1-P6 property suite + calibration ladder (operator-set bottom rung: the multihost estate must score **below 40**) is the instrument that makes this an experiment rather than a debate — score every reference estate under A/B/C/D and read off which puts a catastrophic estate below 40 **without** flattening ordinary estates into the same bucket. That second half is the trap: any of the four can reach 40 if pushed hard enough, only some preserve the difference between *mediocre* and *dangerous*. **This is the third instance of one defect class** (999.95 zero-evidence domains at 25/25 -> 999.113 real-evidence domains at 25/25 -> 999.115 realistic badness compressed at the top), each found by accident rather than by a test, because all ~3,200 lines of existing scoring tests assert mechanism, bounds, and rendering — never meaning. `test_score_always_bounded_1000_iterations` is passed perfectly by a function returning the constant 91. Effort **L**: needs its own phase and a written decision doc in the shape of `.planning/decisions/999.113-denominator-semantics.md`. Measurement reproduction and the four options in full: this row plus that decision doc. |
| **999.113** | **P1** | **CLOSED 2026-09-13** (`0b0ed1c7` fix, `a49c7dd6`/`9fadfaa2` red-proof pair, `e0aec9e3` CHANGELOG) — every ratio now divides by the population its own numerator is drawn from: certificate ratios over `certs_observed`, endpoint ratios over `assessable_endpoint_count`, high-impact findings over the **non-INFO** finding count. Decision recorded at `.planning/decisions/999.113-denominator-semantics.md` (D1-D5 + D1(d)). Measured on the 31-host estate: score **91 -> 87**, Identity **25/25 -> 19/25**, top drivers now legible (legacy TLS -6, expired certs -4, high-impact findings -4, plaintext HTTP -3, self-signed -2) where previously all were sub-1-point rounding noise. Zero domains floored at 0/25 on two healthy fixtures. Blast radius exactly 2 tests. Red-proof `tests/test_score_denominator_999_113.py` pins that two evidence dicts differing ONLY in `totals.endpoints` now score identically. **D1(d) is the part worth remembering:** `agility_high_impact_ratio` was initially and wrongly excluded from scope as "the one site that was always correct" — it divided 19 high-impact findings by 398 TOTAL findings, 330 of them INFO, registering a catastrophic estate as 4.8%. Found by arithmetic during implementation, not by inspection. **NOT SUFFICIENT — see 999.115**, which carries the remaining calibration gap (87 against a <40 target) and is the third instance of this same defect class. Original description follows. **PRODUCT DEFECT — readiness-score ratio penalties divide by the PROBE count, so the score is blind to real weaknesses.** Every subscore penalty in `quirk/intelligence/scoring.py` is `-_ratio(count, denom) * weight` with `denom = totals.endpoints` (line 227) — the number of host x port probes, NOT live or assessable endpoints. `assessable_endpoint_count` is computed four lines away (line 390) and used ONLY for the `endpoints_assessed` predicate, never as a denominator, despite `_endpoints_assessed`'s own docstring instructing callers to prefer it over `totals.endpoints`. Certificate ratios are affected too: they divide certificate counts by the probe count rather than by `certs_observed`. Two consequences, both measured: **(1) a deeper port scan scores BETTER than a shallow one on identical infrastructure** (89 at 2 ports / `endpoints=54` vs 91 at 10 ports / `endpoints=219`); **(2) adding real, correctly-detected vulnerabilities does not move the score at all.** | **Found 2026-09-13** while building the `multihost` chaos-lab profile (999.110 thin slice) and trying to drive a demo score DOWN honestly. Five successive rounds on a purpose-built vulnerable estate took findings from 1 CRITICAL / 3 HIGH to **5 CRITICAL / 14 HIGH / 33 MEDIUM** across **31 vulnerable hosts** and left **every subscore byte-identical** and the score pinned at **91/100**. Decisive case: `certificate_observations` = `{certs_observed: 17, expired_count: 5}` — **29% of the estate's certificates expired — and Identity scored a perfect 25/25**, because `identity_expired_ratio` (weight 14.0) computes `-(5/370)*14 = -0.19` and rounds away; over `certs_observed` it would be `-(5/17)*14 = -4.1` and Identity would fall to ~19. **The scanner detects and severity-rates everything correctly — only the SCORE is blind.** THIS IS THE SIBLING OF 999.95 (the only other P1 in this ledger, *"Readiness score awards full 25/25 to domains with zero evidence"*, CLOSED 2026-09-08 by Phase 188 SCORE-06): 188 fixed *no* evidence scoring 25/25; this is *real* evidence scoring 25/25. **SCORE-06's fix was incomplete.** Full arithmetic, the five-round table and reproduction steps: `.planning/todos/pending/readiness-score-denominator-is-probe-count-not-assessable-endpoints.md`; measurements also recorded in `quantum-chaos-enterprise-lab/expected_results_v4.md` §`## Profile: multihost`. Effort **M, not S** — changing `denom` moves every score the product has ever emitted, so it needs a written denominator-semantics decision, golden-fixture regeneration (CBOM fixtures + `score-strings.json` are generator-drift-gated), a red-proof that a known scan moves in the predicted direction, and a check on `_apply_weighted_impacts`' 25-point clamp saturating more often. **Deliberately NOT patched to flatter or deflate a demo.** Filed 2026-09-13. |
| **999.114** | **P2** | **Phase 206 (Dashboard UI Coverage Drain) is PAUSED at 5 of 13 plans, mid-milestone — NOT abandoned.** Resume with `/gsd-autonomous --from 206 --to 206`. Work is committed on branch `phase-206-dashboard-ui-coverage` (24 commits ahead of `main`); phase artifacts are gitignored and exist on disk only, so **do not `git clean` that branch**. Done: 206-01 (enabling), 02 (Executive), 03 (Findings A), 05 (Certificates+Identity), 06 (CBOM table) — 8 UAT cases dispositioned, vitest 404 → 414 passing, every red-proof mutation reverted byte-identical. Remaining: 206-04/07/08/09/10/11/12/13. **Invariant: no disposition has been flipped in `docs/UAT-SERIES.md`** — all three coupled doc artifacts are fenced into 206-13, which runs last, because a disposition must never be flipped before the test it cites exists and has been red-proved. Verify that fence still holds before resuming. | **Paused 2026-09-13** by operator decision to free the week before a 2026-09-18 client demo; Phase 206 delivers no demo-visible value. Filed here because the operator's stated concern — *"I need a way to ensure we come back to phase 206"* — is historically justified: `BACK-A11Y-01` sat invisible ~3 months after a v5.0 archive, `BACK-89` drifted P2→P1 invisible for 3.5 months, and v5.24 itself slipped three consecutive boundaries. **A prose note is not the guarantee — `tests/test_paused_phase_resume_gate.py` is** (RESUME-01/02/03, all three red-proved on creation): it fails if Phase 206's ROADMAP box is checked while STATE.md still holds its pause record, and — the load-bearing one — if v5.24 is archived while ANY phase remains unchecked. Rides the `Linux Full Suite` CI job. Full pause record in `.planning/STATE.md` § "Phase 206 PAUSE RECORD". |
| 999.108 | **P1** | **CLOSED 2026-09-11 (`cfdd5438`, session quick task)** — 9 tests pinned to an all-available probe map + E2E scan-flow switched to the quick profile; gate untouched; proven both directions under a sslyze-off simulation (9 fail pre-fix, 14 pass post-fix). Original: `main` CI red since 2026-09-10 (v5.21 archive commit onward): Phase 193's submit-time connector-availability 422 gate regressed 9 pre-existing job-submission tests (CI lacks sslyze; email/broker auto-enabled by preset fail closed) + cascades into both Dashboard Quality E2E legs (`POST /api/jobs` 422 → `GET /api/scan/latest` 404). Fix = update the 9 tests to explicitly disable email/broker (or `_all_available_probe_map` monkeypatch pattern), never loosen the gate. Effort S, feasibility CONFIRMED. | Filed 2026-09-11 from `.planning/debug/github-release-notes-and-ci-failures.md`; full node list + fix shape in `.planning/backlog/999.108-main-ci-red-connector-gate-test-regressions/IDEA.md`. Same investigation's BACK-* ledger drift already CLOSED 2026-09-11 (`c2d4ee81`); chaos-lab timeout leg is the known Docker-health environmental class |
| 999.109 | P2 | Every GitHub release body is static Windows-sensor boilerplate (`release.yml:303-348` hardcoded `body:`, unparameterized since ~Phase 118; v5.18.0/v5.19.0/v5.21.0 confirmed byte-identical via `gh release view`). Fix = extract the matching `## [x.y.z]` section from `CHANGELOG.md` and prepend to the (still-accurate) unsigned-binary notice; optional one-time `gh release edit` backfill. NO test tags — validates only on the next real release. Effort S, feasibility CONFIRMED. | Filed 2026-09-11 from `.planning/debug/github-release-notes-and-ci-failures.md`; details in `.planning/backlog/999.109-release-body-static-boilerplate/IDEA.md` |
| 999.111 | P2 | **Drawer vs roadmap disagree on score-lift when endpoints don't share a `scan_run_id` (v5.23 audit INT-01, blocker).** `lift_context_for_scan` (`quirk/dashboard/api/routes/scan.py:1268-1351`) filters `CryptoEndpoint.scan_run_id ==` strictly and returns `{}` when falsy; `get_latest_scan` (`:1703-1762`) resolves the latest scan via a `SESSION_BRACKET` time window **with explicit fallbacks for legacy (`scan_run_id IS NULL`) and distributed-sensor rows** — a materially different endpoint set. So for those deployments the roadmap page shows a real `score_lift` while the storyline drawer shows `None` **for the same finding**, violating v5.23's own "same story, same finding" principle on the shipped distributed console/sensor topology (`docs/operators-guide.md` §8.1). **Mitigating:** the failure is MISSING, never WRONG, information — the drawer renders honest absence, not a divergent number. Pinned by a characterization test (`tests/test_dashboard_finding_storyline.py:742`) and documented at both call sites. **Fix shape:** resolve both call sites' endpoint set through ONE shared helper. Not done in-phase because `get_latest_scan`'s window/fallback tree is exercised by multiple pinned tests — needs its own phase and verification, not a post-review patch. | Filed 2026-09-12 at the v5.23 close; operator accepted the milestone with this open (audit `gaps_found`). Full evidence in `.planning/v5.23-MILESTONE-AUDIT.md` gaps.integration INT-01. |
| 999.112 | P3 | **LIFT-05's four-surface numeric-equality guarantee silently holds only for UNMODIFIED report templates (v5.23 audit INT-03, newly found by the audit).** RPT-02's operator template override is a **full-file** override — `quirk/reports/html_renderer.py:1005-1016` puts the operator's `FileSystemLoader` first in a `ChoiceLoader` — so a same-named operator template can omit the roadmap/lift block entirely. Nothing validates that an overridden template still contains it: `content_model._check_congruence` compares severity bands and CRITICAL counts only and has no notion of roadmap-section presence. DOCX is unaffected (no override path; RPT-02/03 scope it to HTML). This is a working-as-designed consequence of two independently-correct features meeting — Phase 200's full override and Phase 201's equality claim — not a wiring bug. Neither phase's scope contained the other, which is why only a cross-phase audit surfaced it. **Fix shape:** a one-line precondition note in `docs/report-interpretation.md`, or a template-presence linter that warns when an overridden template drops a section the parity tests assert. | Filed 2026-09-12 at the v5.23 close. Evidence in `.planning/v5.23-MILESTONE-AUDIT.md` tech_debt, phase 200. |
| 999.110 | P2 | **Multi-host chaos-lab topology — independent hosts, not services-by-port.** The lab's 90 services across 30 profiles nearly all publish onto the Docker host, so a scan sees ONE IP with many open ports. Give logical hosts their own addresses so scanning walks real hosts, findings group per host, and a host can carry Crown Jewels for the Exposure Map visual. **Feasibility CONFIRMED, effort M — the mechanism already runs in-repo:** the `segmented-network` profile (Phase 152 / DISC-09 / DISC-10, `docker-compose.yml:1443-1457`) already does custom bridge networks with static `ipv4_address` (`segnet-gateway` at `10.70.0.2`); `grep -c ipv4_address` → 5, all in that one profile. This is generalisation, not invention. Mandatory companion work per CLAUDE.md §Chaos Lab Maintenance: `lab.sh` `ALL_PROFILES` + chaos-lab `README.md` + every affected `expected_results_*.md` oracle, same change — the oracles gaining per-host expectations is a real share of the effort. | Filed 2026-09-12 on operator request (scanning coverage + per-host finding attribution + demo value when explaining the platform); full writeup incl. unknowns and plan sketch in `.planning/backlog/999.110-multi-host-lab-topology/IDEA.md`. **Filed at P2, not P3, because it is the ENABLER for 999.107** — see that row. |
| 999.107 | P2 (v2) | Operator-declared reachability + crown-jewel declaration for the Quantum Exposure Map — new persistence + validated CRUD endpoint + declaration UX (the Tier B of Phase 195) | Deferred 2026-09-09 by the MAP-01 spike go/no-go gate (`195-SPIKE-DECISION.md`): ~2-plan effort with no re-validated need beyond the discuss-time leaning, and no live `upstream_mitigated`/reachability data exists to exercise it today. Phase 195 shipped Tier A (key-reuse + upstream_mitigated bridge edges, zero-inference). Build when a client engagement actually needs operator-declared attack paths. **UPDATE 2026-09-12: the gate's blocker is addressable without waiting for a client engagement.** This row's deferral reason is a DATA problem, not an effort problem, and new item **999.110** (multi-host lab topology) is exactly what produces that missing data — it would also convert the 2 standing Phase 195 UAT GAPs (crown-jewel badge, hardware-bridge edge styling, both recorded in `195-06-SUMMARY.md` as unexercisable for lack of live data) into real cases, which is in-scope interest for the committed **v5.24 UAT Coverage Drain**. Re-read this row's go/no-go alongside 999.110 at the next PM review rather than treating "needs a client engagement" as still-binding. |
| 999.106 | P3 (someday/maybe) | Operator-settable SSH port list (`ports_ssh`) — real backend capability: config field + scanner targeting support; today SSH targets derive solely from protocol-classified open ports | Filed 2026-09-09 during Phase 194 discuss: operator chose to DROP ports_ssh from the PARITY-04 Advanced section (no CLI counterpart = not parity) and park the build-it option here. Cross-referenced from `194-PARITY-AUDIT.md`'s "Intentional gaps" §1 (2026-09-09) — `ports_ssh` is not a `config.py` field at all today; building it for real is exactly this ledger item. |
| 999.95 | P1 | Readiness score awards full 25/25 to domains with zero evidence | **CLOSED 2026-09-08 (Phase 188, SCORE-06)** — exclude-and-rescale over assessed domains; see `.planning/milestones/v5.20-REQUIREMENTS.md` |
| 999.92 | P2 | Frontend `ScoreGauge.tsx` band thresholds unconverged with `severity_bands.py` | **CLOSED 2026-09-08 (Phase 188, SCORE-07)** — single-producer bands with drift-guard test; completes v5.19 SCORE-05's frontend half |
| todo: dashboard-cert-view-phantom-tls-rows | high | Failed TLS handshakes rendered as phantom certificate rows | **CLOSED 2026-09-09 (Phase 194, DASH-09)** — `_is_real_cert_endpoint()` shared filter + honest empty states; todo moved to `todos/completed/` |
| 999.96 | P2 | Connectors unreachable from dashboard; every skip silent | **CLOSED 2026-09-09 (Phases 192+193)** — observability half via OBS-01/02 (ScanPhaseRecord + Scan Coverage disclosure); feature half via PARITY-02/03 (all 25 connectors dashboard-reachable) |
| **999.104** | P2 | CLI config ↔ dashboard parity — counted field universe is 121 operator-settable fields (not the ~138 PM-era estimate), of which 35 covered + 6 covered-indirectly + 15 intentional-gap + 65 not-yet-covered per the audit; structural parent of 999.96's feature half | Filed 2026-09-08 by PM at v5.21 boundary; tiered shape + feasibility in `.planning/backlog/999.104-cli-config-dashboard-parity/IDEA.md`. **Audited 2026-09-09** by Phase 194 plan 08: `.planning/phases/194-advanced-scan-fields-executive-verdict-phantom-cert-fix/194-PARITY-AUDIT.md`. Tier roll-up: **Tier 1 (visibility) CLOSED**; **Tier 2 (connector parity) CLOSED** (closed 2026-09-10 by Phase 197) — 25/25 `enable_*` flags dispositioned (unchanged) plus 37/37 credential/endpoint/target sub-fields now dashboard-settable via the widened connectors delta overlay (`quirk.dashboard.api.schemas.validate_connectors_overlay` / `_CONNECTOR_DETAIL_KEY_TYPES`), enforced in lockstep at submit, job-YAML merge, and Effective Config preview; see `197-01-SUMMARY.md` (backend widening + lockstep proof), `197-02-SUMMARY.md` (dashboard rendering, 37/37 fields), and `197-03-SUMMARY.md` (PARITY-07 no-leak regression proof + D-14 job-YAML success-criterion-4 proof). The archived `194-PARITY-AUDIT.md` point-in-time record is left unmodified (D-15) — this row is the record of the closure; **Tier 3 (scan-behavior parity) CLOSED** (closed 2026-09-10 by Phase 198) — the Advanced panel's `scan.*`/`timeouts.*`/`retry.*` surface grew from 7 of 30 fields (plus 1 covered-indirectly) to the full 27-field `AdvancedScanFields` shared model (11 new per-scanner timeouts at 1-600s, 2 retry backoff fields with a base<=max validator, 5 concurrency knobs, `tls_designated_ports`), enforced in lockstep at submit and Effective Config preview via the same shared-model/overlay mechanism Tier 2 used — zero `config_preview.py` changes were needed (D-10 confirmed); see `198-01-SUMMARY.md` (backend 27-field extension + overlay mapping), `198-02-SUMMARY.md` (AdvancedPanel.tsx rendering, TS/Pydantic lockstep), and `198-04-SUMMARY.md` (docs, UAT Series 198, operator walkthrough). Two findings recorded here: **(D-02)** REQUIREMENTS.md's PARITY-09 text said "four concurrency knobs"; a live read of `quirk/config.py`'s `ScanCfg` and `194-PARITY-AUDIT.md` both independently enumerate FIVE (`scan.concurrency`, `fingerprint_concurrency`, `tls_concurrency`, `ssh_concurrency`, `motion_concurrency`) — all five shipped, the requirement text was stale, not the model's scope. **(D-04)** three intentional gaps remain unrendered by design: `scan.openapi_spec_path` (path-traversal surface, same class as `assessment.logo_path`), `scan.hardware_history_retention_days`, `scan.hardware_drift_event_retention_days` (install-scoped engagement-history policy, not per-scan behavior) — recorded in `docs/configuration.md`, never rendered, never added to the schema. **GATE-04** (the standing backlog-reconciliation gate, shipped Phase 189) was re-verified this phase and its D-13 U+2011 escaping fix (100 occurrences across 8 files) retired the last standing local-only RED, landing an EMPTY full-suite failing-node baseline — see `198-03-SUMMARY.md`. **Tier 4 (config-file parity) remains explicitly OUT of milestone scope**, per this row's own v5.21 rationale — no server-side `config.yaml` write surface was touched. This row IS now fully closed across tiers 1-3; tier 4 stays a named, future-milestone item. |
| 999.100 | P2 | Executive Verdict layer | **CLOSED 2026-09-09 (Phase 194, VERDICT-01)** — cherry-pick `f05e7dc7` only, default-on, consumes `rating`/`rating_cap_reason` from API |
| 999.105 | P3 | Customizable reporting engine — operator-controlled composition/templates/branding on top of the existing `ReportContent` → three-renderer split | Filed 2026-09-08 by PM during Phase 191; three-tier shape + feasibility in `.planning/backlog/999.105-customizable-reporting-engine/IDEA.md`; interacts with BACK-51 and 999.101/102. **Tier 1 (template/branding overrides, floor) CLOSED** — shipped 2026-09-11 by Phase 200 (RPT-01 through RPT-04): sandboxed Jinja2 env + `ChoiceLoader` operator template-dir override with GO-verdict SSTI containment (200-01), full-fidelity branding on HTML/PDF and DOCX (200-03), and named report profiles with save/list/select + explicit-config-always-wins precedence (200-05); see `200-01-SUMMARY.md`, `200-03-SUMMARY.md`, `200-05-SUMMARY.md`. **Tier 2 (section-composition profiles) verdict: NO-GO** for the next open slot, decided 2026-09-11 by Phase 200 plan 06 (RPT-05) — full evidence, redesign shape, and sizing in `.planning/backlog/999.105-customizable-reporting-engine/TIER2-GO-NO-GO.md` (local copy, untracked). Two invariants block a naive Tier 2: the **congruence** guard (`content_model.py::_check_congruence`, NOT the ROADMAP-cited `writer.py:307`/`:927` shorthand, which are severity-bucketing/console-count sites, not the raising guard) runs upstream of any renderer on the full, unfiltered severity counts and cannot see which sections a profile will omit; and nine presence-based **parity** test files (`test_cross_surface_parity.py`, `test_report_render_parity.py`, `test_key_reuse_render_parity.py`, `test_quantum_risk_render_parity.py`, `test_report_coverage_parity.py`, `test_score_render_parity.py`, `test_score_parity.py`, `test_finding_engine_parity.py`, `test_cli_dashboard_discovery_parity.py`) assert section presence unconditionally and would need a profile x renderer x section matrix redesign. Sizing floor: **~15-16 plans** (4-plan section-registry refactor + 1 guard-redesign spike + 1-2 guard implementation plans + 9-file, or 1+9-file, parity matrix redesign) — does not fit the already-committed v5.24 UAT Coverage Drain slot; this document does not claim it. Conditions to revisit: a completed guard-redesign spike, a milestone boundary with room for a ~15-16 plan capability item, and a shared-fixture-vs-per-file decision for the parity matrix made up front. |
| 999.98 | P2 | Persist cert SPKI fingerprint per endpoint | **CLOSED 2026-09-08 (Phase 191, SPKI-01/02)** — every scan path incl. sensor merge; key-reuse clusters on all report surfaces |
| 999.99 | P2 | Quantum Exposure Map (attack-path view) | **CLOSED 2026-09-10 (Phase 195, MAP-01/02/03)** — Tier A shipped (zero-fabrication map + score firewall); Tier B deferred by spike → 999.107 (own row above) |
| 999.101 / BACK-07 | P3 | Migration Roadmap NOW/NEXT/LATER re-frame with score-lift | Same item filed twice, 4 months apart |
| 999.102 / BACK-88-drawer | P3 | Finding storyline drawer (Obsidian Pro design remnant) | Same item filed twice |
| 999.91 | P2 | Modbus Step 4 gate unsatisfiable — fingerprinting never activates end-to-end | **CLOSED 2026-09-08 (Phase 190, TRIAGE-07)** — fixed by 141-08/141-11, independently confirmed at `PROJECT.md:677`; fresh live re-verification (not a restatement) in `190-EVIDENCE.md` Leg 2 matches the 2026-08-03 oracle exactly. See `.planning/backlog/999.91-modbus-step4-gate-unsatisfiable/IDEA.md`'s closure annotation and `docs/UAT-SERIES.md` UAT-190-05. |
| 999.103 | P3 | Broker `port_overrides` additive design surfaces pre-existing Kafka/Redis scanner-logic noise (bare-TCP-connect false positives on foreign-family ports; Redis TLS probe exception-swallowing; Kafka sslyze cross-probe out-detecting Redis's own weak-cipher probe; native Kafka TLS/mTLS port 29093 never yielding a genuine finding) | Filed 2026-09-08 (Phase 190, TRIAGE-06 closure); full detail in `190-EVIDENCE.md`'s "Divergences" section and `docs/chaos-lab.md` §3.19's live-run-divergences note. Not a TRIAGE-06 blocker — real findings at operator-declared ports are demonstrated live. |
| 999.93 | P2 | `docs/chaos-lab.md` example config fails verbatim | **CLOSED 2026-09-08 (Phase 189, TRIAGE-03)** — example loads verbatim, executable docs-example gate added; repro artifacts may still sit untracked at repo root (housekeeping only) |
| 999.97 | P3 | Scan-config port fields lack int coercion on YAML load — quoted ports silently no-op | **CLOSED 2026-09-08 (v5.20 Phase 189, QRK-CONFIG-001/002)** — port coercion covered dataclass-wide, cited at `.planning/milestones/v5.20-REQUIREMENTS.md:44`; row corrected 2026-09-11 (v5.23 boundary pass — was still listed open here) |
| BACK-68 (broker sense) | P3 | Broker scanner ports hardcoded (Kafka 9092/9093); lab maps 29092/25671/26380 — cited in v5.20-REQUIREMENTS.md Correctness Drain and v5.22-REQUIREMENTS.md Standing Drain / Out of Scope sections, still open | v5.0 roadmap; distinct from shipped QRAMM BACK-68 |
| BACK-01 | P3 | Dashboard UI for per-algorithm threshold overrides | v4.x era; re-triage before building |
| BACK-03 | P3 | Severity heatmap visualization | v4.x era; re-triage before building |
| BACK-08 | P3 | Narrative onboarding/training guide | Possibly obsolete — docs/ is now deep |
| BACK-51 | P3 | migration_planner dual categorization — one targeted check needed (v5.22-REQUIREMENTS.md carried it in its Out of Scope table; folded into v5.23 LIFT-04) | **CLOSED** — resolved 2026-09-11 by Phase 201 plan 03 (LIFT-04) as a recorded decision, not an accident. `build_phased_roadmap()` (`quirk/intelligence/roadmap.py:99`) is now THE single categorization system feeding every surface, including the console's "Migration Waves" table. `categorize_waves()` (formerly `quirk/reports/writer.py:293-314`, severity-bucketed NOW/NEXT/LATER, console-only) was **deleted outright — no adapter, no deprecated stub kept** — because an unused severity-bucketed categorizer sitting alongside the canonical one would itself have remained the second system this row exists to close. The console table's second column changed meaning as a direct consequence: it now counts roadmap **items** per NOW/NEXT/LATER phase (re-derived from `build_phased_roadmap()`'s own `roadmap_raw` items via a tolerant phase-then-timeframe lookup) rather than raw **findings** bucketed by severity, and was honestly renamed from "Findings" to "Items" to make that change legible on sight. Bucket labels (NOW/NEXT/LATER) and timeframes (0-30/31-90/90+ days) are unchanged. 8 test files' `categorize_waves` patch decorators were removed in the same change (`tests/test_reports_writer.py`, `tests/test_cmvp_report_column.py`, `tests/test_cbom_vex.py`, `tests/test_report_template_sandbox.py`, `tests/test_report_injection_hardening.py`, `tests/test_report_branding_cli.py`, `tests/test_burndown_writer_load.py`, `tests/test_cbom_integration.py`), each individually re-verified green. A new standing regression guard, `tests/test_roadmap_categorization_unification.py`, machine-asserts CLI markdown / HTML / DOCX / dashboard all derive the same NOW/NEXT/LATER assignment from the one system and that `categorize_waves` no longer exists. See `201-03-SUMMARY.md` for the live RED-verification transcript (an injected stub `categorize_waves` was correctly flagged as a BACK-51 violation, then reverted with a confirmed-empty `git diff quirk/`) and the full task-by-task evidence. |
| todo: gsd-phase-complete-premature-completion | high | SEMANTIC toolchain class — `phase.complete` unsafe on this machine | `.planning/todos/pending/` |
| todo: gsd-state-planned-phase-misleading-empty-updated | medium | `updated: []` returned while frontmatter drifts | `.planning/todos/pending/` |
| todo: gsd-state-bold-field-search-unscoped-latent | medium | Dormant bold-branch scoping risk, deliberately unfixed with stated reason | `.planning/todos/pending/` |
| todo: backlog-reconciliation-and-derived-gate | high | **CLOSED** — steps 1–2 executed 2026-09-07 (this ledger); step 3's derived gate shipped Phase 189 (TRIAGE-09), re-verified green end-to-end by Phase 198 GATE-04 with an EMPTY full-suite failing-node baseline; todo moved to `todos/completed/`, dropped from STATE.md's v5.22 deferred table; row corrected 2026-09-11 (v5.23 boundary pass) | `.planning/todos/completed/` |

### Resolved by Phase 189

| Item | Verdict | Evidence |
|---|---|---|
| BACK-59 | KEEP — port 22 in `docs/sample-config.yaml:10`'s `ports_tls` is deliberate, not vestigial | Live-confirmed 2026-09-08: a TLS ClientHello against a real SSH listener (local sshd, 127.0.0.1:22) raises `ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]`, which `quirk/scanner/tls_scanner.py::_categorize_tls_error` (line 71-74) maps to `NOT_TLS_ON_PORT`, surfaced live via `quirk.scanner.tls_scanner.scan_one()` as `tls_blocker_reason="NOT_TLS_ON_PORT"` / `scan_error="NOT_TLS_ON_PORT: SSLError: ..."` — a real, operator-visible endpoint signal, not a swallowed exception. Mechanism half machine-checked in `tests/test_tls_error_categorization.py`. Rationale recorded inline in `docs/sample-config.yaml` above the `ports_tls` line. The lab's own `ssh-alt` container (2222) was unreachable at decision time (no chaos-lab containers running); the local-sshd fallback tier named in the plan was used instead. |

### Drained by Phase 189 review fix (WR-05 enumeration widening, recorded 2026-09-08)

The WR-05 review fix widened gate enumeration from `*-ROADMAP.md` only to the tracked
`*-REQUIREMENTS.md` and phase-doc corpus. The widened scan surfaced exactly 2 new id::title
keys — both prose citations of the already-shipped BACK-89 (executive-summary
score-vs-severity consistency, closed/superseded by Phase 184.4), keyed by their nearest
preceding headings as synthetic titles:

| Cited as | Where | Verdict / evidence |
|---|---|---|
| BACK-89 under heading "Enumeration Drift (the shared defect class)" | `v5.19-REQUIREMENTS.md` SCORE-04 closure narrative ("This supersedes BACK-89") | SHIPPED/SUPERSEDED — Phase 184.4 severity floor; `.planning/backlog/999.82-executive-summary-score-vs-severity-consistency/RESOLVED.md` |
| BACK-89 under heading "Observable Truths" | `v5.19-phases/184.4-rating-band-severity-floor/184.4-VERIFICATION.md` (truth row 6: "BACK-89 is closed by reference") | SHIPPED — same item, same closure evidence as above |

### Bulk-closed by Phase 189 (TRIAGE-09 gate drain, recorded 2026-09-08)

The TRIAGE-09 derived gate's first honest run against the full on-disk corpus found 97
BACK-*/999.* id::title keys neither closed-with-evidence by the gate's own scan
(`- [x]` lines / heading citations only) nor ledgered here -- even though the 2026-09-07
reconciliation audit (`.planning/reports/backlog-reconciliation-2026-09-07.md`) had
already independently verified nearly all of them SHIPPED by direct source-code
existence checks, a closure form the gate structurally cannot see (it never reads the
codebase, only planning-doc text). This table records that verdict here so the gate
passes for the honest reason -- ledger membership -- rather than by narrowing the gate.

| Backlog dir ID | Mirrors | Verdict / evidence |
|---|---|---|
| 999.1 | BACK-04 | SHIPPED — src/dashboard/src/components/theme-provider.tsx |
| 999.2 | BACK-05 | SHIPPED — print.tsx cover section + v5.2 Consulting-Grade Reporting milestone |
| 999.5 | BACK-09 | SHIPPED — closed via v5.1-REQUIREMENTS.md heading "Active REST Fuzzing (BACK-09)" |
| 999.6 | BACK-10 | SHIPPED — closed via v5.1-REQUIREMENTS.md heading "OpenAPI / Swagger Spec Analysis (BACK-10)" |
| 999.7 | BACK-11 | SHIPPED — closed via v5.1-REQUIREMENTS.md heading "Bearer Token Analysis (BACK-11)" |
| 999.8 | BACK-12 | SHIPPED — quirk/scanner/db_connector.py; aws_connector.py:86 _scan_rds_encryption (DB-03) |
| 999.9 | BACK-13 | SHIPPED — azure_connector.py:154 _scan_blob_encryption (STOR-02); gcp_connector.py:376 GCS CMEK |
| 999.10 | BACK-14 | SHIPPED — quirk/scanner/gcp_connector.py |
| 999.11 | BACK-15 | SHIPPED — quirk/scanner/k8s_connector.py; aws_connector.py:143 _scan_eks_encryption (K8S-01) |
| 999.12 | BACK-16 | SHIPPED — quirk/scanner/email_scanner.py + postfix-email compose service |
| 999.13 | BACK-17 | SHIPPED — quirk/scanner/broker_scanner.py |
| 999.14 | BACK-18 | SHIPPED — quirk/scanner/kerberos_scanner.py |
| 999.15 | BACK-19 | SHIPPED — quirk/scanner/saml_scanner.py |
| 999.16 | BACK-20 | SHIPPED — closed via v4.6-REQUIREMENTS.md heading "Compliance Mapping (BACK-20)" |
| 999.17 | BACK-21 | SHIPPED — trend analysis / dashboard delta reporting shipped (v4.8 Phase 64) |
| 999.18 | BACK-22 | SHIPPED — quirk/scanner/dnssec_scanner.py |
| 999.19 | BACK-23 | SHIPPED — quirk/scanner/vault_connector.py |
| 999.20 | BACK-24 | SHIPPED — closed via v5.1-REQUIREMENTS.md heading "Code-Signing Certificate Inventory (BACK-24)" |
| 999.21 | BACK-25 | SHIPPED — scheduled scans (v4.8 Phase 63) |
| 999.23 | BACK-27 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-01 |
| 999.24 | BACK-28 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-02 |
| 999.25 | BACK-30 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-06 |
| 999.26 | BACK-29 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-03 |
| 999.27 | BACK-33 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] (TLS port defaults); re-verified live by Phase 189-02 (TRIAGE-05) |
| 999.28 | BACK-34 | SHIPPED — SSH port prompt added to interactive mode (v4.1 era) |
| 999.29 | BACK-32 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-05 |
| 999.30 | BACK-35 | SHIPPED — tls_enum_mode surfaced in interactive mode (v4.1 era) |
| 999.31 | BACK-31 | SHIPPED — data_classification/data_types consolidation (v4.1 era interactive-mode cleanup) |
| 999.32 | BACK-36 | SHIPPED — interactive prompts reordered, targets first (v4.1 era) |
| 999.33 | BACK-37 | SHIPPED — quirk/connectors/ legacy directory removed |
| 999.34 | BACK-38 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] INTER-04 |
| 999.35 | BACK-39 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] (enable_windows_adcs removed); re-verified live by Phase 184.2 |
| 999.36 | BACK-40 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] CLI-01 |
| 999.37 | BACK-41 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] CLI-02 |
| 999.38 | BACK-42 | SHIPPED — quirk/assessment/ reduced to migration_advisor+operator_context; intelligence/scoring.py authoritative (Phase 83 CLEAN-01) |
| 999.39 | BACK-43 | SHIPPED — scoring calibration profile fix (v4.1 era cleanup) |
| 999.40 | BACK-44 | SHIPPED — validate.py/write_reports() artifact contract fixed (v4.1 era cleanup) |
| 999.41 | BACK-45 | SHIPPED — cfg.scan mutation guarded with try/finally (v4.1 era cleanup) |
| 999.42 | BACK-46 | SHIPPED — migration_advisor.py dead string patterns removed (v4.1 era cleanup) |
| 999.43 | BACK-47 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] CLI-03 |
| 999.44 | BACK-48 | SHIPPED — closed via v4.1-REQUIREMENTS.md [x] CLI-04 |
| 999.45 | BACK-49 | SHIPPED — quirk/engine/rules.py empty reserved file removed |
| 999.46 | BACK-50 | SHIPPED — dead helpers in writer.py / orphaned scorecard.py removed |
| 999.47 | BACK-51 | CLOSED 2026-09-11 by Phase 201 plan 03 (LIFT-04) — see the BACK-51 row above and `201-03-SUMMARY.md` for the deletion decision and evidence |
| 999.48 | BACK-52 | SHIPPED — dead intelligence modules (driver_text, schema dataclasses, calibration) removed |
| 999.49 | BACK-53 | SHIPPED — data/qcscan-legacy.sqlite removed |
| 999.50 | BACK-54 | OBSOLETE — premise gone: tqdm now genuinely wired, run_scan.py:1614 use_tqdm=bool(args.progress) |
| 999.51 | BACK-55 | SHIPPED — internal D-reference ticket comments cleaned from source |
| 999.52 | BACK-56 | SHIPPED — datetime.utcnow() deprecation fixed |
| 999.53 | BACK-57 | SHIPPED — tests/test_interactive_mode.py, test_validate.py, 6x test_run_scan_* |
| 999.54 | BACK-58 | SHIPPED — closed via v4.8-REQUIREMENTS.md [x] DEBT-02 (JWT scanner verify=False documented) |
| 999.55 | BACK-59 | RESOLVED by Phase 189 — see "Resolved by Phase 189" subsection above (KEEP verdict) |
| 999.56 | BACK-63 | SHIPPED — score transparency in executive reports (v4.7/v5.2 reporting work) |
| 999.57 | BACK-64 | SHIPPED — closed via v5.1-REQUIREMENTS.md heading "Authenticated Scanning — Credential Model (BACK-64)" |
| 999.60 | BACK-67 | SHIPPED — defusedxml.lxml -> hardened lxml XXE migration (v5.0 Stabilization milestone) |
| 999.61 | BACK-68 | SHIPPED (QRAMM sense only) — quirk/qramm/ data model + backend API; the still-open broker-ports BACK-68 stays in the main ledger table above |
| 999.62 | BACK-69 | SHIPPED — pages/qramm-assessment.tsx, qramm-profile.tsx, components/qramm/QuestionCard.tsx |
| 999.63 | BACK-70 | SHIPPED — components/qramm/ScorecardTab.tsx |
| 999.64 | BACK-71 | SHIPPED — quirk/qramm/evidence_bridge.py |
| 999.65 | BACK-72 | SHIPPED — quirk/qramm/compliance_map.py + components/qramm/ComplianceMapTab.tsx |
| 999.66 | BACK-73 | SHIPPED — print.tsx:275 Compliance Framework Coverage section (combined PDF export) |
| 999.67 | BACK-74 | SHIPPED — closed via v4.6-REQUIREMENTS.md heading "TLS Finding Gaps (BACK-74)" |
| 999.68 | BACK-75 | SHIPPED — closed via v4.6-REQUIREMENTS.md heading "Nmap Port Discovery (BACK-75)" |
| 999.72 | BACK-79 | SHIPPED — closed via v4.6-REQUIREMENTS.md heading "Rich Finding Context (BACK-79)" |
| 999.79 | BACK-86 | SHIPPED — dashboard-initiated scan configuration/launch/reporting (v4.8 Phase 65) |
| 999.80 | BACK-87 | SHIPPED — closed via v4.8-REQUIREMENTS.md [x] DEBT-02 (lab.sh PROFILE_ARGS CLI precedence) |
| 999.94 | -- | SHIPPED — Phase 185-03 tooltip contrast fix + WCAG guard test |

| BACK item (no surviving 999.* stub in this drain) | Verdict / evidence |
|---|---|
| BACK-02 | SHIPPED — src/dashboard/src/components/ScanSelector.tsx (+tests) |
| BACK-06 | SUPERSEDED — cbom.tsx:266 colors nodes by quantum_safety (QS_NODE_COLOR), a deliberate different encoding |
| BACK-26 | SHIPPED — Distributed On-Prem Scanner Architecture (v5.4 milestone, 7 phases) |
| BACK-80 | SHIPPED — docker-compose.yml postgres-tls profile (Phase 89 / LAB-01) |
| BACK-81 | SHIPPED — oqs-nginx profile + quirk/scanner/pqc_probe.py |
| BACK-82 | SHIPPED — postfix-email service with weak-TLS certs |
| BACK-83 | SHIPPED — grpc-tls profile |
| BACK-84 | SHIPPED — kafka-tls profile |
| BACK-90 | SHIPPED (both senses) — chaos lab config-drift bugs: v5.5-phases/999.83-.../999.83-01..05-SUMMARY.md; RELENG UAT automation shipped in v5.5+ CI workflows |


**Completeness patch (2026-09-07, same day):** a PM spot-question ("are items marked months ago
forgotten?") caught four v5.16-era carried-forward rows and one standing worklist that the initial
ledger missed — verified still-open via `v5.17-REQUIREMENTS.md:271` (recorded there as deferred,
absent from v5.19's requirement set):

| Item | Priority | What it is | Source / notes |
|---|---|---|---|
| Unanchored vitest `-t` substring matching | P3 | Cross-test bleed risk when substitutes run batched | Phase 169 review WARNING; carried since v5.16 |
| `cmd_classify` never prunes orphaned ledger rows | P3 | Latent; data-loss half fixed in 169-01 | Phase 169 review WARNING; carried since v5.16 |
| Vitest `-m slow` leg doesn't execute in CI | P3 | `Linux Full Suite` installs no Node; vitest substitutes existence-checked only | Phase 169; `docs/uat-coverage-gaps.md` tracks it; `dashboard-quality.yml` may be the home |
| Persist the literal scan target at start | P3 | Record user intent rather than reconstructing; not a bug fix | Phase 171 D-02 alternative |
| **`docs/uat-coverage-gaps.md` worklist** | P2 (aggregate) | **PROMOTED 2026-09-13 into milestone v5.24 UAT Coverage Drain (Phases 203–208, 15 requirements)** — the drain this row has been asking for since 2026-09-07. **The row's own "57+" figure was wrong and the promotion is what caught it:** a live parse of `docs/UAT-SERIES.md` at the v5.24 boundary found **70** GAP-annotated cases across **878**, of which only **45** are series ≤163 — the worklist file is scoped to series 1–163 and has never absorbed the **25** that accumulated in series 164–202 (≈1.4 per phase). The 57-vs-45 disagreement between the ledger's `outcome` field and the document's own annotations is itself now a requirement (**COV-03**), sequenced ahead of the generator work because the generator cannot be written until it is decided which source it reads. Original: the UAT coverage GAPs, milestone-sized test-writing effort; still ACCUMULATING — Phase 184 added item 16. | Phases 168/169; the file is its own worklist — this row exists so the ledger points at it. Promotion recorded in the rationale log below (2026-09-13) and in `.planning/REQUIREMENTS.md`. This row leaves the ledger when v5.24 closes and COV-01/COV-02 make the worklist a derived, gated artifact rather than a hand-maintained snapshot. |
| Phase 158 human-UAT (2 visual scenarios) + UAT-143-03 Windows Authenticode cert | P3 / blocked | Standing carry-forward, opportunistic-only / blocked on procuring a production signing certificate | Also listed in PROJECT.md "Standing carry-forward" — mirrored here for one-stop visibility |

**Watch item (rescued from STATE.md's pre-v5.20 Current Position, where it lived only in narrative):**
CISA/NIST CBOM minimum-elements guidance is due ≈**2026-12-19** under EO 14412's 180-day tasking — a
schema-risk event for the CBOM. Not scoped anywhere; SURF-01's VEX surface was built to absorb a
schema shift. Re-check at every milestone boundary until the guidance lands.

**Still parked:** SaaS multi-tenancy (no business-model signal, unchanged since v5.4).

---

## The Primetime Bar

QU.I.R.K. is "primetime" when a consultant or enterprise security team can:

1. **Install it cleanly** — `pip install quirk-scanner` works on a fresh venv. ✅ v4.10
2. **Trust the findings** — every detected weakness is real, every missed weakness is intentional. ✅ v4.6 closed TLS gaps; v4.7 Phase 52 closed FIPS/SOC2/ISO 27001 evidence gaps; v4.9 Audit Depth closed 169 audit findings with a CI invariant.
3. **Trust the score** — single authoritative number; same in CLI report, JSON, dashboard, PDF. ✅ v4.1 + v4.7 Phase 52.
4. **Self-onboard** — operator can run a full engagement from `docs/operators-guide.md` alone. ✅ v4.6 shipped the guide; v4.7 Phase 52 added `quirk doctor`; v4.10 added `docs/getting-started.md` 3-step quickstart + Homebrew tap.
5. **Run on a cadence** — scheduled scans + diff against last run, surfaced in dashboard. ✅ v4.8 (Phase 63 scheduled scans, Phase 64 trend analysis, Phase 65 dashboard-initiated scan).

**All five gates have shipped.** The "primetime cutover" goal originally pinned to v4.8 is now in the rear-view. Post-primetime work shifts from "make it deployable" to "make it adopted / extended / load-bearing."

---

## v4.7 — Governance & Compliance Platform — SHIPPED 2026-05-08

QRAMM (Quantum Readiness Assessment & Maturity Model) — 120-question maturity assessment with evidence bridge from live scans, compliance framework coverage view, combined governance+technical PDF export, quarterly CI staleness gate. 6 phases (51–56) + Phase 56.1. Audit: `.planning/milestones/v4.7-MILESTONE-AUDIT.md`.

## v4.8 — Pre-Primetime Hardening + Operating Model — SHIPPED 2026-05-14

13 phases (57–68) including 64.1 audit-residual-blockers insert. Wave A (57–62) closed 15 gating BLOCKERs from the 2026-05-08 audit (scanner security, dashboard API hardening, credential leakage sweep, score correctness, CBOM sanitization, React hook cancellation). Wave B (63–68) shipped the operating model: scheduled scanning, trend analysis, dashboard-initiated scans + history/compare, resumable scans, operator error-message UX. Scope expanded from a small trust/polish wave to 13 phases because of audit-finding density — rationale logged below.

## v4.9 — Audit Depth — SHIPPED 2026-05-15

10 phases (69–77) + 69.1. Systematically closed all 169 findings from the 2026-05-08 audit ledger and locked the invariant via the `tests/test_audit_ledger_zero_open.py` CI gate. Sets the precedent that audit findings get an explicit zero-open invariant rather than informally tracked. Audit: `.planning/milestones/v4.9-MILESTONE-AUDIT.md`.

## v4.10 — Launch Readiness — SHIPPED 2026-05-21

8 phases (78–85), 52/52 requirements. HTML/PDF injection hardening, S/MIME LDAP discovery scanner, Windows AD CS scanner, CMVP attestation feed, chaos lab fidelity, integration gate, **release engineering** (Trusted Publishers OIDC + Sigstore + towncrier + multi-arch GHCR + Homebrew tap formula), public-launch polish (README marketing, sample CBOM fixtures, upgrade guide). Distribution name finalized as `quirk-scanner` after a late PEP 541 rejection of `qu-i-r-k` (v4.10-D-06). Audit: `.planning/v4.10-MILESTONE-AUDIT.md`.

**Post-ship cleanup (2026-05-22):** doc-sweep for the distribution name, lazy-import fix for `pypdf` in the always-imported report chain, install-error test catch-up to Phase 75 + Phase 81 contracts. CI now fully green on `main`.

---

## v5.0 — Stabilization + Tech Debt Sweep — SHIPPED 2026-05-22

6 phases (87–92), 16 plans. The "breathe" milestone after four heavy capability cycles: Node 20→24 CI bump, `defusedxml`→hardened-lxml XXE migration, single canonical scoring engine with six subscores surfaced against budget, five zero-algo CBOM profiles fixed (closed Phase 42 OBS-1), five new weak-TLS chaos profiles + identity evidence, the OQS-nginx `X25519MLKEM768` PQC-hybrid scoring-ceiling target, dead-code sweep, and the v5.0.0 release. Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`.

## v5.1 — Authenticated Scanning + API Surface Depth — SHIPPED 2026-05-23

4 phases (93–96), 16 plans. An optional ephemeral credential model (`CredentialContext`, in-memory-only, never persisted) unlocking deeper findings across the API surface, plus: `analyze-token` JWT classifier, `$ref`-SSRF-hardened OpenAPI scanner, LDAP `userCertificate` + TLS-EKU code-signing inventory with cross-source CBOM dedup, and `CONFIRM`-gated/non-TTY-aborted active REST fuzzing (alg-confusion + crypto-posture probes) under an unbypassable budget ceiling. `[api]` extras excluded from `[all]` with a CI guard; `SCORE_WEIGHTS` walked 283.0 → 303.0/41 via the existing `agility_signals` subscore. Audit: `.planning/v5.1-MILESTONE-AUDIT.md`.

**Carried tech debt → v5.2 scoping:** WR-05 (code-signing cert expiry computed but not surfaced as a finding — *report-content-adjacent, fold into reporting milestone*), WR-03 (5xx cascade counter resets on connection-exception), WR-02/04/06 (design-judgment follow-ups: env-var all-caps contract, per-call str copies, `_append_query_param` overwrite, sentinel test pre-scrubbed assertions, scheduler `.yml` heuristic). 6 environment/TTY-gated human-UAT items deferred, all non-blocking.

---

# Shipped Since — v5.2 through v5.11 (recaps)

*The 2026-05-23 product-lens framing that opened this section is preserved in the rationale log below; the milestones it prioritized have all shipped.*

<details>
<summary>Original 2026-05-23 framing</summary>

**Framing:** v4.x–v5.1 built a deep, broad *detection* engine across six scanner families (TLS, SSH, identity, data-at-rest, data-in-motion, API/auth) plus governance (QRAMM) and a public distribution. **What has never had a dedicated milestone is the output layer** — the report the consultant hands the client. For a consulting-grade tool, that report *is* the product; better detection only creates value if it's communicated defensibly. The forward outlook is therefore re-ordered: **deliverable first, adoption second, scale-out last.**

The 2:1 capability/ops cadence held through v5.3: v5.0 (ops) → v5.1 (capability) → v5.2 (deliverable) → v5.3 (adoption/ops). **v5.4 breaks the breather rhythm deliberately** — distributed on-prem scanning is a capability cliff for the ICP (segmented enterprise networks), and v5.3 closed low-debt, so the breather defers; stabilization items fold into v5.4's tail instead. v5.0 (ops) → v5.1 (capability) → v5.2 (deliverable) → v5.3 (adoption/ops) → **v5.4 (distributed architecture — capability)**.

</details>
## v5.2 — Consulting-Grade Reporting — SHIPPED 2026-05-24

4 phases (97–100), 12 plans, 13/13 requirements. One shared content model feeding CLI/HTML/PDF/DOCX,
narrative executive report, per-finding context, prioritized remediation roadmap. Details:
`.planning/milestones/v5.2-MILESTONE-AUDIT.md`.

## v5.3 — Adoption & Integration Surface — SHIPPED 2026-05-25

5 phases (101–105), 20 plans, 21/21. Notification fan-out + SIEM CEF + Jira/ServiceNow ticketing on
one shared SSRF-safe/secret-scrubbing layer, plus dashboard token auth. Details:
`.planning/milestones/v5.3-MILESTONE-AUDIT.md`.

## v5.4 — Distributed On-Prem Scanner Architecture — SHIPPED 2026-05-26

7 phases (106–112), 20 plans, 33 requirements, 0 blockers. Sensor/console split: scan-per-segment →
outbound push → merge → one CBOM + one score, no inbound access to any segment. Details:
`.planning/milestones/v5.4-MILESTONE-AUDIT.md`.

## v5.5 — Distributed Hardening + Stabilization — SHIPPED 2026-05-27

4 phases (113–116), 11 plans, 13/13. Per-sensor opaque tokens + revocation, failure-isolated
auto-merge, live-UAT stabilization sweep (999.85–89), Windows packaging spike (GO-conditional).
Details: `.planning/milestones/v5.5-ROADMAP.md`.

## v5.6 — Distributed Completion + Public Launch — SHIPPED 2026-06-12

6 phases (117–122), 20 plans, 21/21. Production Windows frozen sensor, public-repo cutover
(3-pass gitleaks-clean history rewrite + branch protection), port-scope discovery control.

## v5.7 — Hardening + Hardware Compatibility & Lifecycle Remediation — SHIPPED 2026-06-14

7 phases (123–129), 24 plans, 24/24. Wave A drained the 18 deferred v5.6 audit rows (SSRF cluster,
scoring correctness, posture defaults, distributed edges); Wave B shipped the HWCOMPAT-01..06 arc —
agentless hardware fingerprinting, 8-vendor PQC compatibility matrix, CNSA 2.0 tiers, crypto-bridge
detection, CBOM Pass 4 FIRMWARE components.

## v5.8 — Audit Closeout + SNMP Fingerprinting — SHIPPED 2026-06-18

5 phases (130–134), 21 plans. Audit ledger closeout + SNMP `[hw]` extras + CBOM DEVICE hierarchy.

## v5.9 — Documentation Audit & Living Docs System — SHIPPED 2026-07-30

4 phases (135–138) + 138.1/138.2, 10 plans, 16/16. Established the `CLAUDE.md` Per-Phase
Documentation Checklist and Milestone-Boundary Doc Review Template as structural anti-drift
enforcement, after doc staleness accumulated silently across v5.4–v5.8.

## v5.10 — Hardware Lifecycle Depth — SHIPPED 2026-08-03

5 phases (139–143), 36 plans, 23/23. SNMPv3 auth+priv, SNMP-confirmed `upstream_mitigated` bridge
promotion, OT/ICS (Modbus + BACnet) fingerprinting with safety guardrails, advisory-only firmware
CVE correlation, and a dashboard/security tail (scan-date badge, trusted-targets allowlist, Windows
Authenticode signing CI). Details: `.planning/milestones/v5.10-MILESTONE-AUDIT.md`.

## v5.11 — Discovery at Scale + Backlog Drain — SHIPPED 2026-08-11

4 phases (144–147), 16 plans, 11/11, audit `passed`. Chunked, partial-result-tolerant nmap discovery
reachable end-to-end from the dashboard for >1024-host ranges (both hard-reject gates relaxed in the
same phase as the chunking that replaces them), TCP liveness pre-pass with privilege-fallback
detection, per-batch progress + batch-scaled timeouts, CLI/dashboard call-site parity,
undetermined-host disclosure — plus a full drain of the v5.8/v5.10 debt tail. Details:
`.planning/milestones/v5.11-MILESTONE-AUDIT.md`.

---

# Forward Outlook — Re-prioritized 2026-08-11 (integrity lens)

**Framing shift.** v4.x–v5.11 built a deep detection engine, a consulting-grade deliverable, a
distributed architecture, a public distribution, and a hardware-lifecycle advisory layer. The
capability surface is broad and the backlog is nearly drained. What v5.11 exposed is a different
class of problem: **the project's own signals stopped being trustworthy in places, and nothing
caught it.**

Evidence from the v5.11 cycle, all found within one milestone:

- The **release pipeline produced no Windows build for three consecutive milestones** and nobody
  noticed. `v5.10.0` was tagged locally and never pushed; `v5.9` is a two-component tag that never
  matched `release.yml`'s `v*.*.*` glob. The last release run before `v5.11.0` was `v5.8.0`.
- The **Windows signing self-test could never pass** — it verifies a self-signed cert with
  `signtool verify /pa`, which requires a trusted root. Added 2026-08-02 (Phase 143), first executed
  2026-08-11, failed immediately, and took the Windows asset down with it.
- **Three of four phases shipped missing a completion artifact** — Phase 145 had no VERIFICATION.md,
  Phase 147's VALIDATION.md never left draft, Phase 144 had no UAT series entry. All three were
  caught only at milestone-audit time.
- A **deferred item's rationale went stale within a day** of being written and would have survived
  indefinitely, because re-triage reads verdicts rather than re-deriving evidence.
- **~102 test failures have been red since roughly Phase 97** — about fifty phases — long enough to
  be treated as scenery rather than signal.

For a tool whose stated bar is *"every detected weakness is real, every missed weakness is
intentional"* (Primetime gate 2), having its own verification and release signals silently
no-op is the same failure class it exists to find in customer estates. That makes integrity the
highest-leverage next theme — not because capability work is exhausted, but because the confidence
attached to *all* prior capability work is currently unverified.

**Cadence check:** the 2:1 capability/ops ratio is overdue for an ops cycle. The last true ops
milestone was **v5.0 (2026-05-22)** — eleven milestones back. v5.7's Wave A was a targeted audit
drain, not a systems-integrity pass.

## v5.12 — Release & Verification Integrity — SHIPPED 2026-08-14

6 phases (148–153), 36 plans. Release pipeline repair + Windows asset backfill, test-suite triage
and a green CI-gated baseline, phase-completion artifact gates (`scripts/verify_phase_gates.py` +
pre-commit hook), DISC-09 empirical closure, and a real tag cut. Details:
`.planning/milestones/v5.12-MILESTONE-AUDIT.md`.

## v5.13 / v5.14 / v5.15 — the Hardware Lifecycle arc — SHIPPED 2026-08-15 / 08-19 / 08-26

The "continuous hardware lifecycle monitoring" theme deferred since v5.10 took three milestones
rather than the sketched one. Research resolved its flagged 3x sizing uncertainty toward the
smaller estimate — a scheduling/diffing/reporting layer over existing `HardwareDevice` data, not a
new scanner surface — but the tail was longer than the core. See recaps in ROADMAP.md.

---

# Forward Outlook — Re-evaluated 2026-08-26 (post-arc)

**Framing.** For the first time since roughly v5.9, there is no obvious next thing. The backlog is
drained, the hardware-lifecycle arc is closed, the release pipeline is repaired and proven, and all
five Primetime gates remain met. That is a good problem, but it means the next two or three
milestones have to be *chosen* rather than inherited.

The 2026-08-24 third-party functional review is the one large body of live, externally-sourced
evidence available, and it is not yet drained — which makes v5.16 an easy call. What follows it is
a genuine open question, sketched below rather than committed.

## v5.16 — Review Drain & Gate Integrity — SHIPPED 2026-08-28 *(Phases 164–171)*

**Anchor / North Star:** **QUIRK's own gating documents deserve the standard QUIRK applies to
customer estates.** The tool's stated bar is "every detected weakness is real, every missed weakness
is intentional." A release-gate document with no recorded result for 325 of 628 cases, and an
accessibility baseline that permanently accepts 291 violations including three screen-reader
blockers, does not meet that bar.

| Source | Item | Why it matters |
|---|---|---|
| RVW-021 | `quirk scan --targets` doesn't exist, yet the dashboard empty state instructs it | It is the literal first thing a new user is told to type, and it tracebacks |
| RVW-012 | 291 baselined a11y violations, 0 of 11 routes clean, 3 screen-reader blockers accepted | Baselining a blocker converts a decision into an accumulation |
| RVW-008 | 325 of 628 UAT cases carry no result | The document calls itself the release gate |
| RVW-011, RVW-020 | E2E smoke can't pass locally; `uat_runner.py` parses XML with stdlib ElementTree | A gate that can't pass trains people to ignore red; XXE-by-default in a security product |
| RVW-007/009/010/014/015/018/019 | Changelog, archive, traceability and format debt | Genuine debt, no functional urgency — the tail, not the anchor |

**Why now:** drain-before-net-new (standing PM preference) applies directly, and the 2:1
capability/ops ratio is owed — v5.13/v5.14/v5.15 were all capability or capability-drain cycles and
the last true ops milestone was v5.12 on 2026-08-14. The findings are also *pre-scoped*: the
reviewer wrote remediation text in requirement phrasing, so promotion cost is near zero.

**Risk:** same as v5.12's — an integrity milestone has no user-visible feature and is easy to defer
again. Mitigation is the same too: lead with RVW-021, which is a concrete first-run bug, and treat
RVW-008's drain as the tail rather than the opening act.

### Outcome (2026-08-28)

All 8 phases, all 24 requirements complete. The anchor held: the UAT corpus went from 325
unrecorded cases to **zero undispositioned across all 666**, guarded by a standing
`tests/test_uat_zero_undispositioned_gate.py` that was proven load-bearing by mutating a scratch
corpus and confirming it names the offending case.

**The real deliverable is the honest record, not the green gates:** 32 recorded FAIL dispositions — **18 of them genuine product defects**, 13 chaos-lab-down artifacts from a sweep that was required not to start the lab, and 1 spurious (its observed output matched the expectation) — plus 57 honest coverage GAPs and
57 honest coverage GAPs, each naming what would be needed. A corpus reading 100% PASS would have
been worth nothing.

One CRITICAL security finding surfaced mid-milestone and was fixed: **CR-01**, an evidence-newline
injection in `scripts/uat_disposition_apply.py` that could splice a fabricated, fully-`[x] PASS`
UAT case into the document past all three guards at once (the zero-undispositioned gate saw a
PASS, heading/result parity was preserved, and the fabricated ID was novel). Root cause was a
`[^)]*` annotation group matching newlines. Fixed in two layers with 8 regression tests that fail
against the pre-fix code.

**Recurring lesson worth carrying:** the 2026-08-24 review's *symptoms* were reliable but its
*counts* failed re-measurement every single time — 5→3 duplicate IDs, 4→2 genuinely-missing tests,
16→230 stale references. Separately, **enumeration loses entries and derivation does not**: three
successive hand-written slug lists each silently omitted work, and a filesystem-derived index
closed it in one pass.

### Carried forward from v5.16 — deferred, not dropped

Recorded here rather than in `ROADMAP.md`'s Backlog because archived roadmaps swallow backlog
items — `BACK-A11Y-01` was invisible for three months that way (see the note at `ROADMAP.md:120`).

| Item | Origin | Notes |
|---|---|---|
| **GATE-03's fork-safety gate is an allowlist, not a sweep** | v5.16 milestone audit (2026-08-28) | `tests/test_cli_helper_usage.py::_COVERED_FILES` names 11 files, but **18 files carry 38 call sites** matching the gate's own criterion (`cwd=` present, or `close_fds=False` absent). Worst: `test_errors_cmd.py` (8), `test_chaos_lab_idempotency.py` (6), `test_install_errors.py` (4). Latent and order-dependent — the suite passes with zero fatal signals today — but the gate's docstring claims protection "regardless of which subset of tests is run", which it cannot deliver from a hand-maintained list. This is the same enumeration-vs-derivation failure Phase 170 hit three times. **Needs a scoped phase:** convert `_find_offenders` to a repo-wide walk, decide whether the 38 sites migrate to `run_fork_safe` or just gain the kwargs, and grandfather explicitly rather than silently. |
| Unanchored vitest `-t` substring matching | Phase 169 code review (WARNING) | Risks cross-test bleed when substitutes run batched. Latent, not exploited. |
| `cmd_classify` never prunes orphaned ledger rows | Phase 169 code review (WARNING) | Latent; the data-loss half of this function was already fixed in 169-01. |
| Vitest `-m slow` leg doesn't execute in CI | Phase 169 (169-02) | `Linux Full Suite` never installs Node, so vitest substitutes are existence-checked only there. `dashboard-quality.yml` may be the right home. |
| Stale local editable install | Phase 170/171 suite runs | `__editable__.quirk-4.0.0.pth` claims v4.0.0 (project is at 5.15.0), breaking pip's build-backend and causing 3 environmental `test_extras_install_matrix` failures. Local-only; CI installs fresh. Fix is `pip install -e . --no-deps` — a toolchain change, user's call. |
| Persist the literal scan target at start | Phase 171 (D-02 alternative) | Would record user intent rather than reconstructing it. Not a bug fix — derivation already repairs existing runs. |
| Close the 57 UAT coverage GAPs | Phases 168/169 | Writing the missing tests. Its own milestone-sized effort; `docs/uat-coverage-gaps.md` is the worklist. |
| Action the 18 genuine product FAILs (of 32 FAIL rows; 13 are lab-down artifacts, 1 spurious — re-measured 2026-08-28) | Phases 168/169 | Enumerated with command/expected/observed evidence in the 168-03/04/05 and 169-04 SUMMARYs. |

## Beyond v5.16 — three candidates, none committed *(sketch)*

No candidate here is a commitment. Each needs a shaping conversation, and at least one needs a
research pass before it can be sized.

**Candidate A — Migration Execution.** QUIRK detects, scores, and produces a prioritized
remediation roadmap — then stops. The consultant hands over a document and the client executes it
somewhere else entirely. Closing that loop (tracking remediation items to completion across
re-scans, showing movement against the roadmap rather than only against the score) is the most
natural extension of the *consulting* value proposition, and it compounds every detection
capability shipped since v3.9. **Open question:** is this a QUIRK feature or a Jira/ServiceNow
integration deepening on top of the Phase 101–105 ticketing surface already shipped? The answer
changes its size by 3x, exactly like the hardware-monitoring question did at v5.10.

**Candidate B — Detection breadth, re-opened.** Nothing has been added to the scanner surface since
v5.10's OT/ICS work. The standing Out-of-Scope list has three entries worth re-testing rather than
re-inheriting: Windows AD CS live connector (stub still present), S/MIME message-content scanning,
and passive network capture. All three were deferred for reasons that may or may not still hold.
**Open question:** is there a real engagement asking for any of them, or is this breadth for its own
sake? Do not open this without a demand signal.

**Candidate C — Another ops cycle.** Explicitly listed so it isn't forgotten: if the v5.16 drain
surfaces evidence density the way the 2026-05-08 audit did for v4.8 (44 blockers → a 13-phase
milestone), the correct response is to let v5.17 absorb the overflow rather than force a capability
pivot. v4.8 and v4.9 are the precedent.

**Still parked:** SaaS multi-tenancy. Unchanged since v5.4 — the gate is a business-model signal,
and none has appeared. Note that Candidate A does *not* require it; cross-tenant PQC trend
aggregation does, which is why that item stays rejected.

---

## Items Pulled Forward (rationale log)

Track here when the horizon shifts so future-you can see why:

| Item | From | To | Rationale | Date |
|---|---|---|---|---|
| **v5.24 opened as UAT Coverage Drain — the committed pick, honoured rather than re-litigated** | The `docs/uat-coverage-gaps.md` worklist row (P2 aggregate) had been ledgered since 2026-09-07 and deferred at three consecutive boundaries | v5.24 = 6 phases (203–208), 15 requirements: catalog freshness drain (STALE-01/02), worklist truth & derivation (COV-03/01/02/09), guard integrity (GUARD-01/02), the 28 jsdom-tractable dashboard cases (COV-04), the 3 browser-only cases (COV-05), and security/report coverage + carried doc debt (COV-06/07/08, DOC-01/02) | PM review with the user as PM (2026-09-13, post-v5.23 close). **This boundary's job was to honour a prior commitment, not re-open the question** — v5.24 was committed as UAT Coverage Drain at the v5.23 boundary specifically so it could not slip a fourth time, and the operator confirmed the theme unchanged. Cadence supports it: v5.20 correctness → v5.21 capability → v5.22 capability tail → v5.23 capability means an ops/integrity cycle is owed, and drain-before-net-new applies directly. **Every count was re-derived at the boundary rather than inherited, and the inherited one was wrong:** the worklist claims 57 GAPs for series 1–163, but a live parse of `docs/UAT-SERIES.md` finds **70 GAP-annotated cases across 878**, of which only **45** are series ≤163 — the other **25 accumulated in series 164–202 and the worklist has never seen them**, accruing at ~1.4 per phase. That 57-vs-45 disagreement between the ledger's `outcome` field and the document's own annotations became **COV-03**, sequenced ahead of COV-01/COV-02, because a worklist generator cannot be written until it is decided which source it reads. **Catalog re-verification was folded in as the OPENING phase, not a tail** — operator's explicit choice: `tests/test_hardware_staleness.py` is RED on `main` at 91/90 days and `hw_cve.py`'s 30-day cadence trips ≈2026-10-02 mid-milestone; a red staleness gate is a poor backdrop for a coverage-integrity milestone. Research deliberately **skipped** — the evidence is entirely in-repo and already enumerated per-case; the one genuinely external question (Playwright scope, Node-in-CI) is scoped inside COV-05/GUARD-02 as in-phase work. **Precondition cleared before any artifact was written:** v5.23's 155 commits were sitting unmerged in stacked PRs #12 → #13, with #13 based on the stack branch rather than `main` — retargeted and merged (`623fa502`, `5f625595`), so this milestone's phase-complete evidence is branch-honest from the start. Explicitly NOT opened, each by its own standing gate: **999.110** multi-host lab topology (considered seriously as a GAP-enabler — it would convert the 2 unexercisable Phase 195 UAT GAPs into live-data cases — and set aside to keep the drain's anchor sharp; re-read next boundary alongside 999.107), **999.107** Exposure Map Tier B (gated on 999.110's data), **999.111** v5.23's accepted blocker (needs its own phase — `get_latest_scan`'s window/fallback tree is pinned by multiple tests), **999.109** static release bodies (validates only on a real release, wants a release-carrying milestone), **999.105 Tier 2** (NO-GO, ~15–16 plans), Tier 4 config-file parity, detection breadth (no demand signal). CBOM minimum-elements watch item re-checked 2026-09-13: nothing landed (due ≈2026-12-19). SaaS still parked. | 2026-09-13 |
| v5.23 = Deliverable Experience (capability); **v5.24 committed as UAT Coverage Drain** | Open-Item Ledger residue: P3 UX set (999.105/999.101/999.102, BACK-51) + P2 phase-sized drain items + the accumulating uat-coverage-gaps worklist | v5.23 = Wave A drain (trends.py/merge.py int-coerced score fields from 188-05; combined connectors+advanced overlay CI regression test from v5.22 tech debt) gating 999.105 Tier 1 (customizable reporting engine) + 999.101 (NOW/NEXT/LATER score-lift re-frame) + 999.102 (finding storyline drawer) + BACK-51 opportunistic fold-in; **v5.24 = UAT Coverage Drain**, committed at this boundary so it cannot slip a fourth time | PM review with the user as PM (2026-09-11, post-v5.22 close); user's own leaning independently matched the ledger-derived pick ("the last two milestones have been prepping for a solid reporting makeover"). Rationale: for a consulting tool the report IS the product (this file's own 2026-05-23 framing) and the deliverable layer has had no dedicated pass since v5.2 (~20 milestones) while detection grew enormously; 999.101/999.102 are each double-filed months apart — the ledger signaling genuine want; 999.105's IDEA.md interaction note treats all three + BACK-51 as one surface. Cadence in balance (v5.19 ops → v5.20 correctness → v5.21 capability → v5.22 capability tail) — either direction defensible, so the demand signal decided it. UAT coverage drain explicitly sequenced NEXT rather than deferred-again: it has been "important, not urgent" for three boundaries and the worklist is still accumulating (Phase 184 added item 16) — the BACK-89 invisibility pathology in slow motion. Explicitly NOT opened, all by their own standing gates: 999.107 Exposure Map Tier B (needs a client engagement), Candidate B detection breadth (needs a demand signal), Tier 4 config-file parity (needs its own threat-model decision), CBOM minimum-elements pre-work (guidance not landed, due ≈2026-12-19, re-checked this boundary). Two stale ledger rows corrected with evidence (999.97; backlog-reconciliation todo). SaaS still parked — no business-model signal. | 2026-09-11 |
| v5.21 = capability cycle: Dashboard Parity & Exposure Capability | v5.20's own key-context note ("v5.21 should lean capability") + Open-Item Ledger residue | v5.21 = 999.104 (NEW, PM-filed: CLI config ↔ dashboard parity, tiers 1–3 of 4 — the scan form exposes 6 knobs vs a then-estimated ~138-field YAML surface, later audited at 194-08 to 121 real operator-settable fields) + 999.96 observability half + phantom-cert-rows todo + 999.100 Executive Verdict + the full 999.98→999.99 Exposure Map arc | PM review with the user as PM (2026-09-08, post-v5.20 close). Cadence: v5.19 (ops) → v5.20 (correctness) were back-to-back inward cycles, so capability is owed and no drain-before-net-new tension exists — the drainable residue is P3s and toolchain todos, all deliberately deferred and ledgered. The PM's own ask (config parity) turned out to be the structural parent of 999.96's feature half, so the two merged (999.104 tier 2 = 999.96 feature half; observability half stays its own requirement). Tier 4 (server-side config.yaml editing) explicitly OUT — a new security surface deserving its own threat-model decision, not a rider. Exposure Map arc included despite being milestone-sized on its own — explicit PM decision "big but worth it"; expect 6–8 phases. Version v5.21, not v6.0 — big scope alone doesn't warrant a major bump. Excluded and still ledgered: P3 UX set (999.101/102, BACK-01/03/08), 999.103, trends.py int-coercion, GSD tooling todos, UAT coverage-gaps worklist. SaaS still parked — no business-model signal. CBOM minimum-elements watch item re-checked: nothing landed (due ≈2026-12-19). | 2026-09-08 |
| Backlog reconciliation executed; HORIZON becomes the canonical open-item ledger | 92 BACK-* IDs across archived roadmaps read as drained (zero `[ ]` anywhere) while 37 were ledger-invisible; BACK-89 precedent: invisible 3.5 months, drifted P2→P1 | Open-Item Ledger section added above; `.planning/reports/backlog-reconciliation-2026-09-07.md` holds per-item evidence for all 92 | PM directive at the post-v5.19 boundary (2026-09-07): compare backlog to shipped reality and to HORIZON before scoping the next milestone, then switch tracking to the preferred file. Audit re-derived rather than trusted the todo's counts and found them 20 over (its grep missed requirement-section-heading promotion, the dominant closure path). Result: ~92% of the archived backlog is closed with evidence paths; the open residue is 6-7 BACK items, 999.91-999.102, and 5 pending todos — all now in the ledger. The derived gate (todo step 3) is a candidate phase for the next milestone; it must key on title+ID (BACK-68 collision) and honor heading-citation closure. | 2026-09-07 |
| v5.19 = ops drain of v5.18's carried items | Candidate A spent by v5.18; B still gated on a demand signal; C available | v5.19 = Drain — GSD tooling defect, a11y baseline environment mismatch, GATE-03 fork-safety allowlist, DEFER-172-01, TRIAGE-176-01/02 | PM review with the user as PM (2026-09-03, post-v5.18 close). **Candidate A is spent** — Migration Execution shipped as v5.18.0, closing the detect→score→roadmap→execute loop. **Candidate B excluded again by its own gate:** no demand signal for AD CS live / S/MIME content / passive capture; deferred three times now on the same basis, and HORIZON's own instruction is "do not open this without a demand signal". **The 2:1 ratio permits an ops cycle here** — v5.18 was the capability milestone that v5.17's forward caveat demanded, so one ops cycle after one capability cycle is in balance; this is not a fourth consecutive inward turn. **Evidence density does NOT justify a v4.8-scale drain** (v5.18 closed 16/16 with 0 blockers and ~5 carried items, nowhere near 44), so this is scoped small — 4-5 phases, not 13. **Every item was re-measured at the boundary rather than inherited:** GATE-03's drift has GROWN since HORIZON recorded it (recorded as 11 files / 18 / 38 sites; measured 2026-09-03 as 14 allowlisted, 21 unlisted files, 35 direct `subprocess.*` call sites), and **DEFER-172-01 is an accumulator, not a static failure** — it absorbed a NEW skip during v5.18 (`test_closure_burndown.py:296`, Phase 180) without anyone noticing, because the node was already red. That is the same pathology that made Phase 180's genuine second failure hard to distinguish. Three of the five items (GATE-03, DEFER-172-01, a11y baselines) are one defect class: **a hand-maintained enumeration that has drifted from the criterion it claims to enforce** — the remedy in each case is derivation or a guard against the enumeration's own criterion, following Phase 178's derived-table precedent. **The GSD tooling item is included deliberately** despite being an upstream package: it silently corrupted STATE.md nine times across Phases 179-181, and STATE.md is the file every future session treats as project history. Bug A root-caused and patched locally; Bug B (frontmatter reconstruction dropping `stopped_at` and `progress:`) reproduced and unpatched. SaaS still parked — no business-model signal. | 2026-09-03 |
| v5.18 = Candidate A (Migration Execution) as capability anchor, with the release-toolchain repair folded in as a gating Wave A | HORIZON sketched Candidate A as "the most natural extension of the consulting value proposition" but explicitly unshaped, with a 3x sizing question unanswered | v5.18 = Migration Execution (closing the detect→score→roadmap→**execute** loop) preceded by a gating wave that repairs the editable install, bumps the version, and cuts the first release since 5.15.0 | PM review with the user as PM (2026-09-01, post-v5.17 close). **The v5.17 entry's own forward caveat is binding and was honoured:** "this is the third consecutive inward-facing cycle and breaks the 2:1 capability/ops ratio — v5.18 should be a capability milestone unless evidence density again says otherwise." Evidence density did not say otherwise — v5.17 closed 16/16 with only 2 backlogged defects (TRIAGE-176-01/02), nothing near the 44-blocker density that justified v4.8. Candidate B excluded again by its own gate: no demand signal for AD CS live / S/MIME content / passive capture. A fourth ops cycle considered and rejected for the same reason. **The release wave is not scope creep — it is the boundary condition nobody had surfaced:** `pyproject.toml` still reads `5.15.0`, so v5.16 AND v5.17 are both unreleased and two milestones of user-visible fixes are invisible. The blocker is small and mechanical (a stale `__editable__.quirk-4.0.0.pth` breaking the `pip install -e . --no-deps` a version bump requires), and `release.yml` now fires on `v[0-9]*`, so a wrong tag would cut a real bad release rather than silently no-op. Folding it in as a gating Wave A follows the v5.7 and v4.8 precedent rather than deferring a third time. **Shaping question deliberately NOT answered at the boundary** — the user chose a research pass, which is what this file recommended ("opening it unshaped would repeat the v5.10 hardware-monitoring sizing error"). **Research outcome (same day): the 3x premise did not survive.** The ratio is 4-5x, and the two readings are not two sizes of one feature — ticketing readback delegates item identity to the client's tracker, which is the entire problem the native reading must solve, so it yields zero reusable infrastructure and "cheap version first" costs the real version in full on top. A third option the sketch never named — closure tracked against roadmap items, whose titles are a closed, non-interpolated, already-used-as-merge-key list — is the actual foundation. Research also surfaced **two live defects that became prerequisites**, both independently verified before scoping: `compute_trend_report` is structurally dead (delta keys on `(host, port, protocol, severity)` and filters `severity is not None`, but severity is populated only by the three cloud connectors — 10,069 live endpoint rows, 0 non-NULL, so every scan reports 0 new / 0 resolved), and the ticketing fingerprint `SHA256(host:port::title)` interpolates 22 titles including `f"Certificate expiring in {days_to_expiry} day(s)"`, so cert-expiry findings mint a fresh Jira ticket daily despite a docstring claiming stability across re-scans. Structure approved as 5 phases (177–181). **ADVISORY-01 decided at the boundary rather than mid-phase:** closure state never feeds the readiness score, extending the machine-enforced `test_cve_score_guard.py` firewall rather than amending it. Ticketing readback explicitly out of scope (bi-directional sync presumes a continuously-running control plane — that is the parked SaaS block, not an episodic consulting tool). **Also corrected at this boundary** (milestone-boundary doc review): vault `Roadmap.md` and `Requirements.md` were stale/orphaned and `_QUIRK-Hub.md` still showed v5.16 and v5.17 as IN PROGRESS while repeating three claims plan 176-08 had superseded. SaaS still parked; Candidate A explicitly does not require it. | 2026-09-01 |
| v5.17 = Candidate C (another ops cycle), not A or B | HORIZON sketch listed three candidates, none committed | Defect drain of v5.16's own output | Candidate C set an explicit bar: absorb the overflow if the drain surfaced v4.8-like evidence density (44 blockers → 13 phases). The drain produced ~89 evidence-backed items. Candidate B was excluded by its own gate — no demand signal. Candidate A (Migration Execution) remains the strongest strategic move but still has an unresolved shaping question (QUIRK feature vs Jira/ServiceNow deepening) that changes its size 3x; opening it unshaped would repeat the v5.10 hardware-monitoring sizing error. Standing drain-before-net-new preference also applies. **Caveat recorded:** this is the third consecutive inward-facing cycle and breaks the 2:1 capability/ops ratio — v5.18 should be a capability milestone unless evidence density again says otherwise. | 2026-08-28 |
| v5.16 opened as Review Drain & Gate Integrity (ops cycle); HORIZON re-sketched with three uncommitted candidates past it | HORIZON had **no** theme sketched past v5.15, and had explicitly owed a full re-evaluation cadence run since 2026-08-11 | v5.16 = the 11 open + 3 partial findings from the 2026-08-24 third-party functional review, led by RVW-021 (first-run command doesn't exist), RVW-012 (291 baselined a11y violations incl. 3 screen-reader blockers), RVW-011/020 (gate robustness), with RVW-008's full 325-case UAT drain as the tail; Beyond-v5.16 sketched as three explicit candidates (Migration Execution / Detection breadth / another ops cycle) | PM review with the user as PM (2026-08-26, post-v5.15 ship). This is the first boundary where **`ROADMAP.md`'s Backlog is genuinely empty** — the hardware-lifecycle arc closed with v5.15 and nothing remains unpromoted except the parked SaaS block, so the usual drain-before-net-new answer had no items to point at. The live evidence pointed instead: an independent 2026-08-24 functional review left 11 fully-open and 3 partial findings, all pre-scoped with remediation text written in requirement phrasing. Cadence agreed: v5.13/v5.14/v5.15 were all capability or capability-drain, and the last true ops milestone was v5.12 (2026-08-14), so the 2:1 ratio was owed. Two findings are user-facing correctness rather than hygiene — RVW-021 means the dashboard's own empty state instructs a nonexistent command that tracebacks, and RVW-012 baselines three screen-reader blockers as accepted — which answers the standing objection that ops milestones have no demonstrable deliverable. Options considered: (1) drain the review — chosen; (2) net-new capability — rejected, no theme was ready and inventing one under time pressure risks a worse pick, the same reasoning that produced v5.15; (3) split gates-now/docs-later across v5.16+v5.17 — rejected by the user in favour of one milestone with a full RVW-008 drain. Sizing verified rather than inherited: the review's "353 of 601" measured as 325 unmarked of 628 headings, with 3 duplicate IDs not 5 — and the 636-vs-628 mismatch between `**Result:**` blocks and `### UAT-` headings is itself RVW-014 evidence, which is why format unification is sequenced *before* the drain. Explicitly excluded: RVW-002's wholesale `findings_evaluator` merge (TLS cert findings already converged with a parity test; the rest is a design-judgment refactor). SaaS still parked. Also corrected at this boundary: the `test_verify_phase_gates` pair recorded as a "cheap reproducer for RVW-017" is neither — RVW-017 was fixed in `034da44` and Phase 162 established the failures as macOS-only subprocess SIGSEGV, with Linux CI green. Same record-drift class the v5.11 review flagged. | 2026-08-26 |
| v5.15 opened as Lifecycle Tail Drain (small, backlog-only) | HORIZON had no sketch past v5.13/v5.14 — "Beyond v5.13" only listed parked SaaS | v5.15 = 3 phases (161–163) draining HWLC-14, HWLC-19 (vendor-trend surfacing), HWLC-20 (check-in scheduling), DISC-08 (checkpoint granularity); no net-new capability | PM review with the user as PM (2026-08-19, post-v5.14 ship). HORIZON's last two sketched anchors both shipped (Release Integrity → v5.12; Continuous Hardware Lifecycle Monitoring → split across v5.13/v5.14), leaving no next theme. Rather than force a premature net-new capability pick, PM review confirmed the backlog itself as the answer: v5.14's Active-requirements carry-forward list already named 4 small, well-scoped items (all additive extensions of already-shipped subsystems — Phase 101 fan-out, Phase 63 scheduler, Phase 144 checkpointing, Phase 160's dormant API), none individually milestone-sized but collectively closing out the HWLC arc cleanly. Drain-before-net-new (standing PM preference) applies directly. Options considered: (1) drain the tail — chosen; (2) pick a new capability area — rejected, no HORIZON theme was ready and inventing one under time pressure risks a worse pick than researching properly next cycle; (3) another stabilization/ops cycle — rejected, v5.12 (3 milestones back) already covered the ops cadence and nothing has surfaced comparable evidence density since. HORIZON explicitly flagged as needing a full re-evaluation cadence run at the *next* boundary (after v5.15 ships), since this file has had no fresh theme-sketching pass since 2026-08-11. SaaS still parked. | 2026-08-19 |
| v5.12 shaped as Release & Verification Integrity (ops cycle); continuous hardware lifecycle monitoring pushed to v5.13 | Backlog theme "Hardware Compatibility & Lifecycle (v5.11+)" implied continuous monitoring was next up | v5.12 = integrity/ops (release pipeline repair, test-suite stabilization, phase-artifact enforcement, DISC-09 empirical closure); v5.13 = continuous monitoring as capability anchor | PM review with the user as PM (2026-08-11, post-v5.11 ship). Three factors converged. (1) **Cadence:** the 2:1 capability/ops ratio is badly overdue — last true ops milestone was v5.0 on 2026-05-22, eleven milestones back. (2) **Evidence density:** the v5.11 cycle surfaced five independent measurement failures — a release pipeline that produced no Windows build for three milestones (v5.9's tag never matched the `v*.*.*` glob, v5.10.0 was never pushed), a signing self-test that could never pass and had never run, three of four phases shipping without a completion artifact, a deferred-item rationale that decayed within a day, and ~102 tests red since ~Phase 97. (3) **Compounding:** these hide each other — a saturated test signal cannot flag a regression, a silent release pipeline cannot flag a missing artifact. Drain-before-net-new (standing PM preference) applies with unusual force here because the debt is in the *verification layer itself*, so every future milestone's "green" is currently unproven. Continuous monitoring stays deferred one more slot for the same reason it was deferred at v5.10: it needs a research pass to determine whether it is a new scanner surface or a scheduling/diffing layer, and that answer changes its size by 3x. SaaS still parked. Also noted: two backlog rows (OT/ICS resume-checkpoint gap, BACnet CVE key coverage) were already closed by v5.11 Phase 147 as DRAIN-01/DRAIN-02 but never struck from the backlog — same record-drift class as the findings above. | 2026-08-11 |
| v5.10 opened as Hardware Lifecycle Depth (SNMPv3, SNMP-confirmed bridge, OT/ICS, firmware CVE correlation) | Backlog theme "Hardware Compatibility & Lifecycle Remediation (v5.10+)" — 5 items, one (continuous monitoring) least-scoped | v5.10 = 4 of the 5 tagged items (SNMPv3, upstream_mitigated confirmation, OT/ICS fingerprinting, firmware CVE correlation) + a folded-in Dashboard/UX tail (scan-date badge, trusted-targets allowlist, Authenticode signing); continuous monitoring deferred to v5.11+ | PM review with the user as PM (2026-07-30, post-v5.9 ship). Drain-before-net-new (standing PM preference): this backlog theme was explicitly tagged "v5.10+" when v5.8 shipped SNMP fingerprinting, so it's the clearest unbuilt, already-scoped theme rather than net-new scope. Continuous hardware lifecycle monitoring excluded from the multiSelect as the least-scoped item, needing its own research pass before it can be sized. Dashboard/UX tail (3 small items) folded in as a stabilization tail per the v4.8/v5.4 pattern rather than left to age further in the backlog. Research (4 parallel agents) confirmed all four capability items are additive extensions of existing patterns (no new architecture), with two dominant risk themes flagged for same-phase mitigation: false assurance in a consulting deliverable (over-eager bridge promotion, unqualified CVE claims) and OT/ICS probe safety (fragile production control systems). SaaS still parked. | 2026-07-30 |
| v5.7 opened as Hardening + Hardware Compatibility & Lifecycle Remediation | v5.7 sketched as pure HWCOMPAT capability anchor | v5.7 = Wave A hardening drain (18 audit rows + Dashboard Quality green-up) hard-gating Wave B HWCOMPAT-01..06 | PM review with the user as PM (2026-06-12, post-v5.6 ship). Drain-before-net-new (standing PM preference): v5.6 deferred 18 audit rows — dominated by the SSRF/`url_allowlist.py` cluster the 2026-05-27 audit flagged as 5-of-7 criticals — and the repo is now PUBLIC, making both the SSRF surface and the red Dashboard Quality badge world-visible. Folding the drain into v5.7 as a gating Wave A (v4.8 pattern) beats deferring again (debt compounds publicly) and beats a pure-hardening milestone (HWCOMPAT was already slotted as the v5.7 anchor on 2026-05-27 and the 2:1 cadence permits capability work). SaaS still parked. | 2026-06-12 |
| v5.6 opened as Distributed Completion + Public Launch (Windows full build + public-repo cutover) | v5.6 candidates: Windows full build, public-repo cutover, HWCOMPAT | v5.6 = WINBUILD (production --onedir Windows sensor: build/smoke → packaging+Scheduled-Task+E2E+release → 3 phases) + PUBREPO (secret sweep → public + required check); HWCOMPAT → v5.7 | PM review with the user as PM (2026-05-27, post-v5.5 ship). Drain carry-forward before net-new (standing PM preference): the Windows full build and public-repo cutover were both explicit v5.5-seeded carry-forward; HWCOMPAT is net-new. Windows full build gated on the v5.5 WINPKG-01 spike GO — confirmed-conditional by the live windows-latest CI build triggered on the v5.5.0 push. Scope locked: --onedir (not --onefile, per spike), zip+PowerShell Scheduled-Task (not MSI/NSIS), publish unsigned to GitHub Releases (Authenticode deferred), pre-public git-history secret sweep before cutover. Research skipped — Windows freezing was already the v5.5 spike. HWCOMPAT remains the v5.7 capability anchor; SaaS still parked. | 2026-05-27 |
| v5.5 opened as Distributed Hardening + Stabilization; Windows packaging cut to spike-only; public-repo cutover deferred | v5.5 sketched as a pure live-UAT bug-sweep | v5.5 = 4 phases (113–116): per-sensor auth (TD-1) + auto-merge (106 D-06) + STAB sweep (999.85–89) + Windows SPIKE | PM review with the user as PM (2026-05-26, post-v5.4 ship). The owed 2:1 breather, expanded from bug-sweep to *hardening* because the carry-forward items (per-sensor auth, auto-merge) were ready and reuse fresh v5.4 primitives. Windows packaging held to a spike (not full build) to cap the documented balloon risk → full build conditional on the spike → v5.6. Public-repo cutover kept OUT (repo stays private; `windows-sensor-smoke` non-blocking) — deferred to the launch decision. Per-sensor auth promoted to core. SaaS still parked. Research skipped (internal hardening; the one unknown — Windows freezing — is the spike itself). | 2026-05-26 |
| Distributed on-prem scanner (999.22) decoupled from SaaS + promoted to v5.4 anchor | v5.4 = stabilization breather; 999.22 + SaaS both gated on adoption signal | v5.4 = Distributed On-Prem Scanner Architecture (anchor); SaaS stays parked | PM review with the user as PM (2026-05-25, post-v5.3 ship). 999.22 (on-prem, single-tenant, agent/console) was conflated with SaaS multi-tenancy under one "wait for multi-segment demand" gate — but they're different problems: distributed on-prem is a network-topology/engagement-completeness necessity (segmented enterprise nets a single host can't reach), SaaS is a business-model bet. The user surfaced a concrete multi-segment on-prem need → the gate's condition is met. Groundwork is freshest now (v5.3 just built the console-side auth + outbound-push primitives). v5.3 closed low-debt → low cost to defer the breather; 999.58 arch doc folds in as Phase 1. SaaS stays parked (no business-model signal). v5.3 live-delivery human-UAT items parked (no test environment) — explicitly NOT a v5.4 entry condition. | 2026-05-25 |
| Forward outlook re-prioritized: Reporting promoted to NEXT (v5.2) | v5.0/v5.1 candidate sketches A/B/C; Distributed/SaaS at v5.2 | v5.2 Consulting-Grade Reporting → v5.3 Adoption → v5.4 Stabilization+SaaS-validation | v5.0 (stabilization) and v5.1 (auth/API capability) both shipped, consuming candidates A and C. Product-lens review (with the user as PM): for a consulting tool the *report is the product*, and no milestone has owned the output layer despite a now-deep detection engine. Reporting compounds all prior detection work and is the engagement moment-of-truth → promoted to NEXT. Adoption/integration (old Candidate B) follows. Distributed/SaaS pushed one more slot, still gated on a real adoption signal. | 2026-05-23 |
| v5.1 candidate A (Authenticated Scanning) collapsed to shipped recap | sketch | one-paragraph recap | Shipped 2026-05-23 as Phases 93–96; details in v5.1-MILESTONE-AUDIT.md. | 2026-05-23 |
| v5.0 candidate C (Stabilization) collapsed to shipped recap | sketch | one-paragraph recap | Shipped 2026-05-22 as Phases 87–92; details in v5.0-MILESTONE-AUDIT.md. | 2026-05-23 |
| v4.7–v4.10 collapsed to shipped recap | "in progress" + "primetime cutover" + "API depth" sections | one-paragraph audit references each | All four milestones closed since last HORIZON revision; details now live in respective `MILESTONE-AUDIT.md` files. HORIZON is for what's *ahead*, not a log of what shipped. | 2026-05-22 |
| Primetime bar reframed as ✅✅✅✅✅ | gates 1–5 partial | all 5 met | v4.8's "primetime cutover" goal landed as planned (Phase 63 scheduled, 64 trend, 65 dashboard-initiated). v4.10 added the public-distribution layer (PyPI/GHCR/Homebrew/Sigstore) that closed gate 1 cleanly. The mental model shifts from "make it deployable" to "make it adopted." | 2026-05-22 |
| v5.0 reshape: 3 candidate themes vs. 1 default | "slot open — QRAMM pulled into v4.7" | 3 explicit candidates A/B/C with trade-offs | The old "TBD after v4.9" placeholder is no longer load-bearing; v4.9 and v4.10 both shipped. v5.0 needs a concrete shaping conversation, not a placeholder. | 2026-05-22 |
| Distributed/SaaS pushed from v5.1 sketch to v5.2 sketch | v5.1 anchor theme | v5.2, pending adoption validation | Original v5.1 sketch assumed the next milestone after primetime cutover should be platform-scale work. Post-ship reality: no adoption signal yet that justifies committing to multi-tenant infrastructure. Defer one slot; let v5.0/v5.1 surface whether multi-segment is a real ask. | 2026-05-22 |
| Phase 64.1 (Audit Residual Blockers) | unplanned | v4.8 bridge between 64 and 65 | 19 BLOCKERs from 2026-05-08 audit were untriaged after Wave A. 5 of these directly undermined Phase 64 UAT (trend session window) or Phase 65 foundations (non-transactional migrations). Inserted 64.1 to triage all open findings and fix the foundation-touching subset before any operating-model features extended those code paths. Remaining 14 absorbed by v4.9 audit-depth ledger. | 2026-05-10 |
| v4.8 scope expansion: Wave A/B split (audit-driven) | HORIZON v4.8 sketch (trust & polish) | full 13-phase Wave A+B | HORIZON v4.8 sketch listed a small trust/polish wave. The 2026-05-08 pre-v4.8 audit revealed 44 BLOCKERs / 96 WARNINGs across 116 files — a primetime cutover was not defensible without addressing the critical security/correctness findings first. Wave A absorbed the 15 gating blockers; Wave B absorbed the HORIZON operating-model anchor items (scheduled scans, trend analysis, dashboard-initiated scan). Scope expanded from ~5 phases to 13; justified by audit finding density. v4.9 inherited the remaining 121 open findings (92 WARNINGs + 29 INFOs + 13 deferred BLOCKERs). | 2026-05-14 |
| QRAMM (BACK-68 → BACK-73) — Governance & Compliance Platform | v5.0 | v4.7 | Evidence bridge compounded v4.6 compliance mapping; COMPLY-10/11/DOCS-05 deferrals created a natural anchor for Phase 52; pulling forward eliminated a capability cliff before v5.x distributed work. | 2026-05-05 |

(Older rationale entries from v4.6 era retained in git history — see commit `a6b9820` and prior.)

---

## Re-evaluation Cadence

After every milestone closes, before opening the next:

1. Does the next-up theme still make sense given what just shipped?
2. Did this milestone surface anything that should jump the queue?
3. Is the 2:1 capability/ops ratio still holding (one ops-depth milestone per two capability-breadth milestones)?
4. Has the primetime bar moved? Did this ship advance gates 1–5, or expand them?

**Revise this file at every milestone wrap.** Pulled-forward / pushed-back decisions go in the rationale log above so the reasoning isn't lost.

---

## What This Document Is Not

- **Not a commitment.** Themes survive; details rarely do. Phase decomposition happens at `/gsd-new-milestone` time, not here.
- **Not a backlog replacement.** ROADMAP.md `## Backlog` is still the source of truth for individual items; this is the *grouping* layer above it.
- **Not exhaustive.** New backlog items will arrive between now and v5.2. The horizon should absorb them, not be invalidated by them.
