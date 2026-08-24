# QU.I.R.K. — Third-Party Functional Review: Findings

**Review date:** 2026-08-24
**Reviewed commit:** `49f9094` (product code); review deliverables committed separately
**Reviewed version:** v5.15 Lifecycle Tail Drain (in progress); v5.14 declared shipped
**Charter:** `docs/superpowers/specs/2026-08-24-third-party-functional-review-design.md`
**Mandate:** Findings only. No defect was fixed as part of this engagement.

---

## 1. Executive Summary

QU.I.R.K. is a mature, heavily-instrumented codebase. 3,487 backend tests pass, the
frontend suites are green, the committed dashboard bundle is byte-identical to a fresh
build, and **every one of the 444 delivered requirements is implemented** — the review
found no requirement that was claimed complete but absent from the code.

The defects that matter are not missing features. They are **defects in how scan results
are stored and surfaced**, and a **release and verification-discipline gap** in which the
last two milestones were declared shipped without being released, and the most recent 19
commits have never run CI.

| Severity | Count |
|---|---|
| CRITICAL | 1 |
| HIGH | 5 |
| MEDIUM | 6 |
| LOW | 5 |
| OBSERVATION | 4 |

**The single CRITICAL finding is in the core value path** — every scanned endpoint is
persisted twice, inflating the certificate inventory, the Data-in-Motion table, and the
endpoint count on the consultant's deliverable. It traces to a false assumption at
`run_scan.py:3190` about what `session.merge()` returns, and the fix is small.

The next tier concerns **two surfaces disagreeing with each other**: the dashboard runs a
second, independent finding engine that lacks the self-signed and untrusted-CA detections
the report engine has, and scan sessions fragment so that one scan appears as several with
contradictory scores.

### Verdict

The product does substantially what its documents say it does, and its **client-facing
report deliverable is materially correct** — a live scan of the chaos lab's certificate
defect ports produced exactly the findings and severities the project's own oracle
specifies, in the CLI output, the findings JSON, the HTML report and the DOCX.

The problems a consultant would actually hit are: **doubled rows** in the certificate and
Data-in-Motion inventories, a scan history showing **phantom scans with contradictory
scores**, and a **dashboard that reports a different security picture from the report**.
The first two undermine the "complete, defensible cryptographic inventory" claim; the third
undermines trust in the operator's primary working surface. All three should be fixed
before the next release, and none is a large piece of work.

---

## 2. What Works — Reported As Prominently As What Does Not

A review that lists only problems would misrepresent this codebase.

- **Zero stale evidence.** Across 809 file references and 126 named test files in plan
  summaries, **no test file claimed by a completed phase is missing**. In a codebase with
  161 phases of churn this is a genuinely strong result, and it was the finding class the
  charter expected to be worst.
- **Zero unimplemented requirements.** All 444 delivered requirements trace to code.
  The only three with no traceability link (GAUGE-01/02/03) were verified line-by-line and
  are fully built and tested.
- **Backend suite: 3,487 passed / 1 genuine failure** (the CMVP staleness gate, which is
  *supposed* to fail — see RVW-005). Two further local failures were environmental
  (`git init` SIGSEGV on this machine) and are not product defects.
- **Frontend: all green.** ESLint clean including the project-specific
  `check-cancelled-guards.sh` hook gate; 141/141 vitest tests pass.
- **Committed bundle is fresh.** A clean `npm run build` reproduced byte-identical
  content-hashed assets — the E2E suite and this review both exercised the genuinely
  shipped frontend. The repo has a dedicated `check-bundle-freshness.sh` CI gate for this.
- **Chaos-lab drift is structurally impossible.** `lab.sh` *derives* its profile list from
  `docker-compose.yml` via `_derive_all_profiles()` rather than duplicating it. All 29
  profiles resolve correctly and **all 29 have oracle coverage**. This is a stronger
  guarantee than the manual sync CLAUDE.md's maintenance rule describes.
- **Five of six staleness catalogs are within cadence**, and the CI gate that enforces
  them is working — it is currently, correctly, red.
- **Security controls are live and well-messaged.** The CSRF guard rejected an unheadered
  POST with `[QRK-DASHBOARD-002] Missing CSRF header ... Fix: Add header X-Quirk-Request: 1`
  — an error carrying both a code and the remedy.
- **Honest score presentation.** The dashboard renders a red "Very Low Confidence" badge
  beside a 93/EXCELLENT score rather than presenting the number unqualified.
- **Advisory firewalls hold.** Hardware and vendor-trend sections each carry explicit
  "does not affect the readiness score" captions, as their requirements specify.

---

## 3. Method and Evidence Model

Verdicts are stamped with the evidence tier they rest on, so any individual call can be
challenged on its evidence rather than its conclusion.

| Tier | Source | Coverage of 444 delivered reqs |
|---|---|---|
| A | `SUMMARY.md` frontmatter (`requirements-completed` + `key-files`) | 89 (23%) |
| B | `docs/UAT-SERIES.md` case linkage | 183 (46%) |
| C | ROADMAP phase mapping | 379 (96%) |
| D | Requirement ID annotated in `tests/` module docstrings | 306 (78%) |

**Traceability matrix — delivered requirements:**

| Verdict | Count | % |
|---|---|---|
| Names existing test file(s) | 348 | 78% |
| Roadmap phase mapping only | 38 | 9% |
| UAT case recorded PASS, no test named | 28 | 6% |
| UAT case exists, result never recorded | 27 | 6% |
| No evidence at any tier | 3 | 1% |
| **Stale evidence** | **0** | **0%** |

Full matrix: 554 requirement IDs across 27 documents (444 delivered, 108 deliberately
out-of-scope, 2 open).

---

## 4. Findings

### RVW-001 — CRITICAL — Every scanned endpoint is persisted twice

**Affects:** core value path; inflates all inventory counts.

**Documented claim** — `.planning/PROJECT.md` core value: *"Produce a complete, defensible
cryptographic inventory with a CBOM deliverable and quantum-readiness score that a
consultant can hand to a client in under two hours."*

**What the code does:** every Data-in-Motion and Certificate endpoint is written to
`crypto_endpoints` twice. The scanner emits the correct count; the persistence path
doubles it.

**Evidence chain (single scan, single host, `port_scope=top1000`):**

```
scan run.log        : "Email scan: 7 endpoints from 1 hosts"      <- correct
sqlite crypto_endpoints, latest session:
  port 25 -> 2, 110 -> 2, 143 -> 2, 465 -> 2, 587 -> 2, 993 -> 2, 995 -> 2
GET /api/scan/latest: motion_findings = 14 rows, 7 distinct payloads (each x2)
                      certificates    =  6 rows, 3 distinct payloads (each x2)
dashboard /motion   : 14 rows rendered; /certificates: 6 rows rendered
meta.total_endpoints: 58 (inflated)
```

Independently reproduced against the `tls-cert-defects` chaos-lab profile: 4 findings from
2 distinct, 8 certificates from 4 distinct — all exactly doubled. Not a loopback artifact.

**Ruling out an intentional dual-probe.** The endpoint model carries a `sni_used` column,
which raises the possibility that the scanner probes each target twice by design (with and
without SNI) and persists both. It does not: `include_sni` is a single config value and
`scan_one` is submitted once per `(host, port)` at `tls_scanner.py:552`. Verified at the
database layer against genuinely open ports serving real certificates — the two rows differ
in **`id` and nothing else**:

```
port 13444: id=2 protocol=TLS tls=TLSv1.3 subj=CN=expired.chaos.local
            id=4 protocol=TLS tls=TLSv1.3 subj=CN=expired.chaos.local
            DIFFERING COLUMNS: ['id']
```

Same protocol, TLS version, certificate subject, and `scanned_at`. These are not two
observations; they are one observation stored twice.

**Root cause — a false assumption in code written to prevent this exact defect.**
Endpoints are written twice:

1. `_flush_stage_endpoints()` (`run_scan.py:243`) persists each stage's endpoints
   immediately after that stage completes — Phase 67 / **RESUME-01**, so a crash mid-scan
   does not lose completed stages. Called from 8 stages (inventory, TLS, SSH,
   JWT/container/source/openapi/fuzz, identity, data-at-rest, broker+email).
2. The final `db_persist` block (`run_scan.py:3190`) writes every endpoint again, using
   `merge()` rather than `add()`. Its own comment states the intent:

   > *"CR-03: use merge() instead of add() so that detached resumed endpoints (which
   > already have a PK from a prior flush) are UPDATE'd rather than INSERT'd, avoiding
   > IntegrityError on resume."*

**The parenthetical is false.** `session.merge()` returns a *new* persistent instance and
never writes the primary key back onto the object passed to it. The in-memory endpoints
therefore still carry `id = None` at the final persist, SQLAlchemy treats them as new
objects, and inserts a second row.

Reproduced in isolation with no scanner involved:

```
before flush     : ep.id = None
after stage-flush: ep.id = None    <- PK not written back to the caller's object
rows in DB for one endpoint scanned once: 2
```

**Corroboration from the defect's distribution.** CBOM components and hardware devices are
**not** duplicated — and that set is precisely the set of stages that do *not* call
`_flush_stage_endpoints`. The duplication appears in exactly the stages that flush, which
is what distinguishes a named cause from a coincidence.

**Scope of impact — what is and is not affected.** The duplication is at the *endpoint row*
level, so it inflates the certificate inventory, the Data-in-Motion table, and
`total_endpoints`. The **findings list is not affected**: `_dedupe_findings()`
(`findings_evaluator.py`) keys on `(host, port, title, recommendation)` and collapses the
duplicates. A CLI scan of two lab ports produced 7 findings, all distinct. The defect
therefore corrupts *inventory counts*, not *finding counts* — an important distinction for
anyone assessing blast radius.

**Interaction with RVW-003:** any fix must not dedupe on `scanned_at`, because that column
is currently unreliable for the separate reason described in RVW-003.

**Verdict:** CONFIRMED — a defect, not a designed behaviour. Evidence tier: direct
execution + isolated reproduction + source inspection.

---

### RVW-002 — HIGH — The dashboard runs a second, divergent finding engine

**Affects:** dashboard `/findings`; operator-vs-client consistency.
**Severity revised down from CRITICAL after re-verification — see note below.**

**What is actually true.** QU.I.R.K. contains **two independent finding generators**:

| | Report path | Dashboard path |
|---|---|---|
| Code | `quirk/engine/findings_evaluator.py` | `quirk/dashboard/api/routes/scan.py` |
| Consumers | CLI, findings JSON, HTML, DOCX, PDF | `GET /api/scan/latest` → dashboard UI |
| Self-signed detection | ✅ yes (`:636`) | ❌ absent |
| Untrusted-CA detection | ✅ yes (`:654`) | ❌ absent |
| RSA-1024 severity | HIGH — "TLS certificate uses undersized RSA key" | **CRITICAL** — "Weak RSA key: 1024 bits" (`:216`) |

`routes/scan.py` never imports `findings_evaluator`; it hand-rolls roughly twenty finding
titles of its own.

**The client-facing deliverable is correct.** A live CLI scan of the lab's self-signed
(13445) and untrusted-CA (13446) ports produces exactly what the oracle specifies:

```
findings-20260824-195344.json
   port=13445 sev=HIGH     TLS certificate is self-signed
   port=13446 sev=MEDIUM   TLS certificate issued by untrusted CA
```

Both titles also appear in `report-*.html` and `technical-findings-*.md`. The chaos-lab
oracle for `tls-cert-defects` is **satisfied** by the report path.

**What the operator sees instead.** The same two ports scanned through the dashboard yield
no self-signed and no untrusted-CA finding, and the RSA-1024 defect is escalated to
CRITICAL where the engine and the oracle both say HIGH. A consultant triaging in the
dashboard sees a materially different security picture from the report they hand the client.

**Second-order consequence — compliance mapping silently misses.**
`quirk/compliance/__init__.py:152-153` maps controls by the **engine's** finding titles:

```python
"TLS certificate is self-signed":            [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
"TLS certificate issued by untrusted CA":    [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
```

The dashboard's titles (`"Weak RSA key: 1024 bits"`, …) are not keys in that map, so
dashboard-surfaced findings cannot carry PCI/SOC 2/ISO annotations even where the
equivalent engine finding would.

**Verdict:** CONFIRMED as a surface divergence between two finding engines — **not**, as
this finding originally claimed, a failure to detect the defects.

> **Correction.** This finding was first written as *"two of four documented certificate-defect
> classes are never reported"* at CRITICAL severity, on evidence drawn solely from
> `GET /api/scan/latest`. That tested one of two surfaces. The engine emits both findings
> correctly at the oracle's exact severities — verified by unit-invoking
> `evaluate_endpoints()` on the observed certificate values and by a full CLI scan
> producing HTML, DOCX and PDF. The defect is real but narrower, and the client deliverable
> was never affected. Severity revised CRITICAL → HIGH.

---

### RVW-003 — HIGH — Scan sessions fragment: one scan becomes many, with contradictory scores

**Affects:** Scan History, Trends, score integrity. **Regression of declared requirement
STRUCT-01.**

**Documented claim** — `.planning/milestones/v4.4-REQUIREMENTS.md`, STRUCT-01: *"All new
scanners accept a `session_start` parameter (shared `datetime` from `run_scan.py`) — no
per-scanner `datetime.now()` calls (ISSUE-3 elimination pattern)."*

**What the code does** — `quirk/scanner/tls_scanner.py:367` constructs each endpoint with:

```python
scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
```

a per-endpoint `datetime.now()` call, which is exactly what STRUCT-01 forbids.

**Observed consequence.** Two submitted scans produced **24 distinct scan sessions**:

```
None                        -> 3 endpoints     <- NULL scanned_at
2026-08-24 19:16:59.449047  -> 2 endpoints
2026-08-24 19:16:59.449071  -> 2 endpoints
... 17 sessions differing only in MICROSECONDS ...
2026-08-24 19:19:31.890970  -> 14 endpoints
```

17 sessions × 2 endpoints = 34 = exactly the `total_endpoints` of the common-scope scan,
which scans `CONSULTING_TLS_PORTS` — **17 ports**. The scanner is creating one scan session
per port. One session has `scanned_at = NULL`.

**User-visible damage**, confirmed in the browser:

- **Scan History** lists 6 scans for 2 real ones, with contradictory scores: 92, 100, 93,
  93, 92, 93. Each fragment is scored against only its own 2 endpoints.
- **Trends** compares two fragments and renders the meaningless `Score Delta 100 → —
  First scan`.

A consultant reviewing scan history sees scans they never ran and scores that disagree.

**Verdict:** CONFIRMED. Evidence tier: direct execution + source inspection.

---

### RVW-004 — HIGH — v5.13 and v5.14 were declared shipped but never released

**Affects:** release integrity; distributed sensor version reporting.

**Documented claim** — `.planning/ROADMAP.md:30-31` marks both milestones ✅ shipped
(2026-08-15 and 2026-08-19).

**What is actually true:**

```
$ gh release list           -> latest published release is v5.12.0 (2026-08-14)
$ git tag                   -> v5.13 and v5.14 exist
$ gh run list --workflow=release.yml
                            -> NO release-workflow run for v5.13 or v5.14
$ git show v5.14:pyproject.toml | grep ^version
                            -> version = "5.12.0"
$ .venv/bin/quirk --version -> QU.I.R.K. v5.12.0
```

The v5.14 **release tag itself contains `version = "5.12.0"`**. Two milestones were tagged
and declared shipped with no version bump, no release workflow run, and no published
release.

**This is not merely cosmetic.** `quirk/cli/sensor_cmd.py:282` transmits
`quirk.__version__` as `sensor_version` in distributed sensor push payloads. The console's
version-skew handling — requirement CONSOLE-05, *"extra='ignore' + version-skew graceful"* —
therefore receives a version string two releases behind reality from every v5.13/v5.14
sensor.

**The project's own gate already detects this and has been ignored.** The Release Tag
Hygiene workflow is red as of 2026-08-24T09:36:51Z with
`release_tag_hygiene: 1 flagged tag(s): ['v5.14']`. The script's own docstring records
that this has happened three times before: *"three milestones (v5.9, v5.10.0, v5.11.0's
Windows asset)"*.

**Verdict:** CONFIRMED. Evidence tier: direct execution.

---

### RVW-005 — HIGH — Three of four CI workflows are red on `main`, and the last 19 commits have never run CI

**Affects:** the entire verification discipline.

**What is actually true** (as of 2026-08-24):

| Workflow | State | Cause |
|---|---|---|
| Python Staleness Gate | ❌ red | CMVP cache 100 days old (threshold 90) |
| Python CI | ❌ red | same CMVP failure + `test_schedules_api.py::test_get_schedules_empty` |
| Release Tag Hygiene | ❌ red | `v5.14` flagged (RVW-004) |
| Dashboard Quality | ✅ green | last run 2026-08-19 |

**No workflow has run on the current HEAD.** The newest CI run of any workflow is on
`c776add` (2026-08-19T10:18Z). Commits `d3237a7` through `49f9094` — **19 commits dated
2026-08-19/20, comprising the entire Phase 161 / v5.15 work** — have zero CI runs.

The CMVP failure reproduces locally: `tests/test_cmvp_freshness.py::test_cmvp_cache_not_stale`
is 1 of only 3 failures in the full 3,490-test run, and the only genuine one.

**Verdict:** CONFIRMED. Evidence tier: direct execution.

---

### RVW-006 — HIGH — A sixth CI-gated staleness catalog is undocumented, and it is the one that is stale

**Affects:** maintenance runbook completeness.

`CLAUDE.md` § "Staleness Review Cadence" documents five catalogs and gives a remediation
procedure for each. `.github/workflows/python-staleness.yml:29-36` actually gates **seven**
test files, including `tests/test_cmvp_freshness.py`.

The CMVP cache (`quirk/compliance/cmvp_cache.json`, `last_verified: 2026-05-16`, 90-day
threshold) is **100 days old and failing CI today** — and it is precisely the catalog
CLAUDE.md never mentions. `grep -ci cmvp CLAUDE.md` returns 0.

The documented runbook therefore does not cover the catalog that is actually broken. Also
undocumented: `test_error_codes_freshness.py`, `test_snmp_scanner_contract.py`.

**All five documented catalogs are within cadence:**

| Catalog | Threshold | last_verified | Age |
|---|---|---|---|
| `qramm/model_meta.py` | 90d | 2026-08-11 | 13d |
| `compliance/__init__.py` | 365d | 2026-05-05 | 111d |
| `scanner/hw_cve.py` | 30d | 2026-08-02 | 22d |
| `scanner/bacnet_vendors.py` | 365d | 2026-08-11 | 13d |
| `scanner/hardware_eol.py` | 365d | 2026-08-14 | 10d |

**Verdict:** CONFIRMED.

---

### RVW-007 — MEDIUM — `CHANGELOG.md` is stale by six milestones

The newest entry is `[5.8.0] — 2026-06-16`. Milestones v5.9 through v5.14 are undocumented
in a public repository. The file carries a `<!-- towncrier release notes start -->` marker,
but `changelog.d/` contains only `README.md` — no pending fragments explain the gap.

---

### RVW-008 — MEDIUM — The UAT gating document records no result for half its cases

`docs/UAT-SERIES.md` contains 355 UAT cases linked to a requirement:

| Result | Count |
|---|---|
| PASS | 174 |
| **UNMARKED** (checkbox present, nothing ticked) | **178** |
| SKIP | 1 |
| Unparseable prose | 2 |

167 of the 178 unmarked cases also have an empty `**Date:**` field, indicating they were
never executed rather than executed-but-unrecorded. 12 cases are typed HUMAN-UAT.

**Important qualification:** an unmarked UAT case does not mean the capability is untested.
Of the 91 delivered requirements whose UAT cases never record a PASS, **75 still carry
automated test evidence**, leaving 16 with neither. This finding concerns the integrity of
the gating document, not test coverage.

---

### RVW-009 — MEDIUM — `v4.7` was shipped without archived planning artifacts

`.planning/ROADMAP.md:12` marks v4.7 Governance & Compliance ✅ shipped (2026-05-08) and
links to `.planning/milestones/v4.7-ROADMAP.md`. Neither that file nor a
`v4.7-REQUIREMENTS.md` exists.

Of the 40 milestone files referenced by ROADMAP.md, **v4.7-ROADMAP.md is the only dead
link**. Only `v4.7-phases/` survives (phases 51–56.1 — the QRAMM subsystem). v4.7's
requirements are absent from the declared inventory and traceable only through phase
artifacts.

---

### RVW-010 — MEDIUM — 15 code-bearing delivered requirements have no test linkage

AUTH-05, DASHQ-01, DASHQ-02, DEBT-02, DEBT-04, DEP-01, GAP-01, GAP-02, QRAMM-08, QRAMM-09,
QRAMM-11, STRUCT-02, TAIL-04, UAT-02, UAT-03.

Not evidence of defect — evidence that nothing mechanically ties them to a test. A further
20 `PHASE-ONLY` requirements are documentation or process requirements (architecture-document
contents, CLAUDE.md templates, user guides) that are correctly verified by artifact
inspection rather than by test.

---

### RVW-011 — MEDIUM — The E2E smoke test cannot pass on a developer machine

`src/dashboard/tests/e2e/run-e2e.mjs` hardcodes `SCAN_TIMEOUT_MS = 120_000`. Measured scan
duration with the harness's default `port_scope=top1000` against loopback on this machine:
**140 seconds** (TLS ~85s, SSH ~50s). The documented command `npm run e2e:smoke` fails,
twice reproduced, with `scan-timeout`.

This is a test-robustness defect, **not a product defect**. A CI ubuntu runner has almost
nothing listening on localhost, so the TLS and SSH stages find no open ports and finish in
seconds. Any developer machine with real services listening blows the budget. A suite that
is red for reasons unrelated to correctness trains people to ignore it.

---

### RVW-012 — LOW — The a11y gate is red locally on a selector change, not an accessibility change

`npm run a11y:check` exits 1 on `/data-at-rest`. The cause is not a new violation: the
baseline records the table wrapper `div` as the violating node while the current DOM
reports `th:nth-child(9)` in the same table. `run-a11y.mjs:176` keys each violation on
axe's full CSS-selector path, so an ancestor class change invalidates the key.

Two facts point in opposite directions and both matter: the gate firing is a false
positive, **and** the underlying 23-element `color-contrast` violation on `/data-at-rest`
is real, permanently baselined, and therefore invisible to the gate by design.

---

### RVW-013 — LOW — Version strings are stale in three user-facing files

`README.md:7` (`v5.12.0`), `docs/UAT-SERIES.md` (`**Version:** 5.12.0`), and
`pyproject.toml:7` (`5.12.0`) all trail the v5.14 shipped claim.
`docs/getting-started.md` carries **no version string at all**, though CLAUDE.md's
milestone-boundary checklist requires one. UAT-SERIES.md's header is internally
contradictory: `**Version:** 5.12.0` beside a `**Last Updated:**` line describing v5.14
Phase 160 work.

---

### RVW-014 — LOW — Requirements are declared in four incompatible formats

Across 26 archive documents: checkbox (23 files), markdown table (v3.9, 36 reqs),
bold-list (v4.4), and bold-header-with-checkmark (v5.8, 22 reqs). Any tool that reads
requirements must implement all four or silently lose whole milestones. This review's own
parser initially lost 51 requirements to a related issue.

Related: `docs/UAT-SERIES.md` uses **five** different result-line formats within a single
document.

---

### RVW-015 — LOW — Archive header counts contradict file contents

`v4.6-REQUIREMENTS.md` declares *"All 36 v4.6 requirements implemented and verified"* but
the file declares 22 IDs. `v5.7-REQUIREMENTS.md` declares *"All 24 requirements VALIDATED"*
against 10 declared IDs. Five archive files carry no `**Status:**` header at all (v4.10,
v4.3, v5.1, v5.12, v5.4).

---

### RVW-016 — LOW — Release tag naming is inconsistent

`v5.9`, `v5.13`, `v5.14` omit the patch component; `v5.12.0`, `v5.11.0`, `v5.10.0` include
it. This complicates any automated tag-to-version comparison.

---

### RVW-017 — OBSERVATION — `test_schedules_api.py::test_get_schedules_empty` is order-dependent

Fails in CI (`assert data["schedules"] == []` received a populated list) but **passes
locally** under `-p no:randomly`. The signature of a test-isolation leak that only
surfaces under a particular ordering.

---

### RVW-018 — OBSERVATION — Planning summaries cross-reference siblings by pre-archive path

16 Tier-A file references point at `.planning/phases/...` paths that break when a milestone
is archived and its phase directory moves to `.planning/milestones/<version>-phases/`.
Links to code and tests do not rot; only self-referential planning links do.

---

### RVW-019 — OBSERVATION — GAUGE-01/02/03 have no traceability link of any kind

The string `GAUGE-0` appears nowhere in the repository outside its own requirements file.
All three were verified implemented and tested by direct inspection
(`ScoreGauge.tsx:7,16,23`; `executive.tsx:338-343,353`; `__tests__/ScoreGauge.test.tsx`).
Traceability debt, not capability debt.

---

### RVW-021 — MEDIUM — The documented `quirk scan --targets` command does not exist

**Affects:** first-run experience; six UAT case definitions.

There is no `scan` subcommand and no `--targets` flag. Targets come from `config.yaml`
(or `--targets-file`). Both documented forms fail:

```
$ quirk scan --targets 1.2.3.4
quirk: error: unrecognized arguments: scan

$ quirk --targets 127.0.0.1
FileNotFoundError: Targets file not found: 127.0.0.1
```

The second is worse than a usage error: argparse prefix-matches `--targets` to
`--targets-file`, so the value is treated as a **path**, and the failure surfaces as an
**uncaught traceback** rather than a clean message. The project has an error-code
convention (`QRK-DASHBOARD-002`, `QRK-INSTALL-NNN`) and requirement UX-02 covers exactly
this class of failure.

**The dashboard instructs users to run the non-existent command.**
`src/dashboard/src/pages/findings.tsx:119` renders the empty state:

> *"No findings recorded in this scan — run a scan first: `quirk scan --target <host>`.
> Results will appear here automatically."*

A new user following the product's own on-screen instruction gets an argparse error.

Also affected: `docs/chaos-lab.md:676`, and **six UAT step definitions** in
`docs/UAT-SERIES.md` (lines 8315–8317, 9071, …) whose steps are written as
`quirk scan --targets …`. Those cases cannot have been executed as written — which
corroborates RVW-008: UAT-67-01, whose step is `quirk scan --targets 127.0.0.1 &`, is one
of the 178 cases with no recorded result.

---

### RVW-020 — OBSERVATION — `uat_runner.py` parses XML with stdlib `ElementTree`

`xml.etree.ElementTree` is vulnerable to XXE and billion-laughs attacks by default. The
parsed input is self-generated, so exposure is low, but `defusedxml` is the safer default
for a security-tooling product.

---

## 5. The 28 HUMAN-UAT Items

`docs/UAT-SERIES.md` marks 28 items as requiring human execution; 12 are linked to a
requirement and appear in the traceability matrix. These are outside any automated harness
and remain unverified by this review:

UAT-101-02 (Slack live delivery, NOTIFY-03) · UAT-101-03 (Email live delivery, NOTIFY-04) ·
UAT-101-04 (Webhook live delivery + failure isolation, NOTIFY-05/07) · UAT-102-02
(`quirk token generate` live round-trip, AUTH-01) · UAT-102-05 (Browser login flow, AUTH-03) ·
UAT-102-06 (Mid-session 401 returns to login, AUTH-03) · UAT-102-07 (Auth-disabled
passthrough, AUTH-03) · UAT-103-02 (syslog UDP/TCP delivery + CEF mapping, SIEM-01/02) ·
UAT-103-04 (After-scan export, SIEM-01/02) · UAT-104-02 (live Jira issue creation + dedup,
TICKET-01/03) · UAT-105-02 (live ServiceNow incident, TICKET-02) · UAT-118-03 (live
windows-sensor-e2e CI green run, WINBUILD-04).

Each requires live external infrastructure (Slack workspace, SMTP relay, webhook endpoint,
Jira/ServiceNow tenant, Windows CI).

---

## 6. Limitations

1. **Single commit, single platform.** Reviewed at `49f9094` on macOS/darwin. Windows
   behaviour — which has its own documented packaging gotchas — was not assessed.
2. **Cloud connectors not credentialed.** AWS, Azure, and GCP KMS paths were verified only
   to the extent their tests and mocks allow.
3. **One chaos-lab profile exercised live.** `tls-cert-defects` was brought up and scanned
   against its oracle, through **both** the dashboard API and the CLI/report path. Its
   oracle is satisfied by the report path. The other 28 profiles were verified only for
   derivation correctness and oracle coverage, not live scanner behaviour — and, given
   RVW-002, any future profile check must exercise the report path, not only the dashboard.
4. **PHASE-ONLY sampling.** The characterisation of older untraced requirements rests on a
   stratified sample, not a census.
5. **Two local test failures were environmental** (`git init` SIGSEGV) and are excluded from
   the findings as not attributable to the product.
6. **Evidence tiering involves reviewer judgment.** Every verdict states its tier so it can
   be independently challenged.

---

## 7. Reviewer's Note on Method

Four defects in this review's own analysis tooling were found and corrected during
validation, each of which would have produced **false findings against the project**:

1. Inheriting a milestone's SHIPPED header marked deliberately out-of-scope items as
   delivered (104 rows; would have produced 7 false contradiction findings).
2. Rigid UAT result-triple matching discarded genuine dated PASS records (PASS corrected
   116 → 174).
3. Tier-D evidence was mis-ranked as incidental string matches when it is in fact a
   maintained docstring convention (PROVEN corrected 67 → 348).
4. A 6-character requirement-prefix cap silently dropped 51 real requirements
   (`CONSOLE-*`, `RELEASE-*`, `HWCOMPAT-*`, …).

Two false "stale catalog" flags were also caught and discarded. These are recorded because
an audit that trusts its own tooling produces confident, wrong findings — and because the
corrected figures in this report are materially more favourable to the project than the
uncorrected ones would have been.

**A fifth correction came from challenge rather than self-review.** RVW-001 was originally
supported only by comparing the API projection of each row, which omits fields such as
`sni_used`. On that evidence a deliberate dual-probe design — one pass with SNI, one
without — would have been indistinguishable from a defect, and the finding as first written
did not rule it out. Re-checking at the database layer against genuinely open ports showed
the rows differ in `id` alone, and following that through produced the root cause now
recorded in RVW-001. The finding survived, and became considerably more actionable.

The methodological point generalises: *"duplicate rows"* is precisely the shape an
intentional dual-observation design would take. A reviewer who reports that shape without
eliminating the benign explanation is guessing. This report's findings should be read as
falsifiable claims, and challenged the same way.

**A sixth correction, from the same challenge applied to RVW-002 — and this one changed the
finding.** RVW-002 originally claimed, at CRITICAL severity, that *"two of four documented
certificate-defect classes are never reported."* That rested entirely on
`GET /api/scan/latest`. Re-verification showed:

- `findings_evaluator.py:636,654` implements both detections correctly;
- unit-invoking `evaluate_endpoints()` on the exact observed certificate values emits
  `HIGH — TLS certificate is self-signed` and `MEDIUM — TLS certificate issued by untrusted
  CA`, matching the oracle's severities precisely;
- a full CLI scan of the lab ports put both findings in the findings JSON, the HTML report
  and the technical-findings markdown.

**The chaos-lab oracle is satisfied by the report path.** What is actually wrong is
narrower and, in its own way, more interesting: the dashboard runs a *second* finding
engine that lacks those branches. The client deliverable was never affected. Severity
revised CRITICAL → HIGH and the finding rewritten.

Both corrections ran the same direction — the original claim was too harsh, and closer
verification was more favourable to the project. That asymmetry is worth stating plainly: a
reviewer's first pass is biased toward the surface they happened to test, and for this
product the dashboard API is a partial view of the system, not a proxy for it.
