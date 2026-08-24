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
| ☐ | RVW-001 | CRITICAL | Every TLS/certificate and email endpoint is persisted twice | core value path; all inventory counts | The scan pipeline must persist exactly one row per (host, port, protocol) per scan session. Add a regression test asserting `len(motion_findings) == len(set(payloads))` for a single-host scan. | M | Open |
| ☐ | RVW-002 | CRITICAL | Self-signed and untrusted-CA certificate findings are never emitted despite the data being captured | TLS defect detection | The scanner must emit a self-signed finding when `cert_subject == cert_issuer`, and an untrusted-CA finding when `chain_verified` is false. Align `tls-cert-rsa1024` severity with the oracle (HIGH, not CRITICAL) or update the oracle. Gate on the `tls-cert-defects` profile in CI. | M | Open |
| ☐ | RVW-003 | HIGH | One scan fragments into many sessions (17 sessions for 17 ports); Scan History shows phantom scans with contradictory scores | Scan History, Trends, score integrity | All scanners must stamp endpoints with the shared `session_start` value rather than calling `datetime.now()` per endpoint (`tls_scanner.py:367`), restoring STRUCT-01. No endpoint may be persisted with a NULL `scanned_at`. Add a test asserting one scan yields exactly one distinct `scanned_at`. | M | Open |

**Sequencing note:** RVW-003 is likely the cheapest of the three and may share a root cause
with RVW-001 — both concern how endpoints are written. Investigate together before
estimating separately.

---

## Theme 2 — Release & CI Discipline

| ☐ | ID | Sev | Finding | Affects | Remediation | Effort | Status |
|---|----|-----|---------|---------|-------------|--------|--------|
| ☐ | RVW-004 | HIGH | v5.13 and v5.14 declared shipped but never released; v5.14 tag contains `version = "5.12.0"` | release integrity; sensor version reporting | Either publish v5.13/v5.14 properly (bump `pyproject.toml`, run the release workflow) or correct ROADMAP.md to stop claiming they shipped. A milestone must not be markable ✅ shipped without a successful release run. | M | Open |
| ☐ | RVW-005 | HIGH | Three of four CI workflows red on `main`; the last 19 commits have never run CI | entire verification discipline | Restore all four workflows to green and establish that CI runs on every push to `main`. Investigate why no workflow triggered for commits `d3237a7`..`49f9094`. | M | Open |
| ☐ | RVW-006 | HIGH | A sixth CI-gated staleness catalog (CMVP) is undocumented — and is the one currently failing | maintenance runbook | Re-verify the CMVP cache and run `quirk compliance cmvp refresh`. Add CMVP, error-codes, and SNMP-contract catalogs to CLAUDE.md's Staleness Review Cadence so the runbook matches `python-staleness.yml`. | S | Open |
| ☐ | RVW-017 | OBS | `test_schedules_api.py::test_get_schedules_empty` is order-dependent (fails in CI, passes locally) | test reliability | The test must pass under randomised ordering. Isolate the schedule fixture so no row leaks between tests. | S | Open |

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
| ☐ | RVW-008 | MEDIUM | UAT-SERIES.md records no result for 178 of 355 cases (167 also undated) | gating-document integrity | Every UAT case must carry a recorded result or an explicit deferral. Triage the 178; note 75 of the 91 affected requirements already have automated coverage, so most can be closed by reference. | L | Open |
| ☐ | RVW-009 | MEDIUM | v4.7 shipped with no archived ROADMAP or REQUIREMENTS (only dead link of 40) | traceability | Reconstruct v4.7's requirements from `v4.7-phases/` or correct ROADMAP.md's dead link. | S | Open |
| ☐ | RVW-010 | MEDIUM | 15 code-bearing delivered requirements have no test linkage | traceability | Each of the 15 must gain either a test-docstring annotation or a summary `key-files` entry. | M | Open |
| ☐ | RVW-013 | LOW | Version strings stale in README, UAT-SERIES, pyproject; absent from getting-started | user-facing docs | Resolve as part of RVW-004; add getting-started to the version-drift checklist. | S | Open |
| ☐ | RVW-014 | LOW | Four requirement formats and five UAT result formats across the corpus | tooling fragility | Adopt one requirement declaration format and one UAT result format for new documents. Backfilling archives is optional. | M | Open |
| ☐ | RVW-015 | LOW | Archive headers contradict contents (v4.6 "36" vs 22; v5.7 "24" vs 10) | doc accuracy | Correct the two counts; add `**Status:**` headers to the five archives lacking one. | S | Open |
| ☐ | RVW-016 | LOW | Release tag naming inconsistent (`v5.14` vs `v5.12.0`) | tooling | Adopt one tag convention going forward. | S | Open |
| ☐ | RVW-018 | OBS | Planning summaries reference siblings by pre-archive path (16 broken refs) | planning hygiene | Reference phase artifacts by a path that survives archival, or rewrite on archive. | S | Open |
| ☐ | RVW-019 | OBS | GAUGE-01/02/03 have no traceability link (code verified correct) | traceability | Annotate `ScoreGauge.test.tsx` with the GAUGE requirement IDs. | S | Open |

---

## Suggested Sequencing

A recommendation the owner may reject — the reviewer proposes, the owner disposes.

**Milestone A — "Scan Integrity" (blocks release).** RVW-001, RVW-002, RVW-003.
These three are the only findings that corrupt the client-facing deliverable. Until they
are fixed, a consultant hands over doubled inventory rows, phantom scan history, and no
self-signed/untrusted-CA findings. Everything else can wait; these cannot.

**Milestone B — "Release the Backlog."** RVW-004, RVW-005, RVW-006, RVW-013, RVW-017.
Get CI green, get the version bumped, get v5.13/v5.14 either released or un-claimed. This
is mostly small work whose value is that it makes Milestone A's fixes verifiable and
shippable. RVW-006 is a ~15-minute fix that turns two red workflows green.

**Milestone C — "Trustworthy Gates."** RVW-011, RVW-012, RVW-020.
Make the suites pass for real reasons so they stop training people to ignore red.

**Milestone D — "Documentation Drain."** RVW-007 through RVW-019 (docs items).
Genuine debt, no functional urgency. RVW-008 (178 unmarked UAT cases) is the largest item
here and is the most defensible candidate for partial closure by reference to existing
automated coverage.

---

## Not Assessed

Recorded so the plan is not mistaken for full coverage — see the findings report §6.

- Windows platform behaviour and packaging.
- Cloud connector paths (AWS / Azure / GCP KMS) beyond mocks.
- 28 of 29 chaos-lab profiles under live scan.
- The 28 HUMAN-UAT items, which require live external infrastructure.
