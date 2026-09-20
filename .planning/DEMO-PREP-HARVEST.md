---
project: QU.I.R.K.
type: compilation
status: active
compiled: 2026-09-20
covers: demo-prep 2026-09-14 → 2026-09-18, and the v5.24 position it interrupted
demo_outcome: delivered 2026-09-18, went well
sources: .planning/.continue-here.md (2026-09-16), .planning/ROADMAP.md, .planning/STATE.md, .planning/HORIZON.md, PRs #19-#32, .planning/todos/pending/
---

# Demo-Prep Harvest and Milestone Position

The 2026-09-18 demo is delivered. This file compiles two things the demo pushed aside:
**what demo prep uncovered** (§2–§6) and **where v5.24 actually stands** (§1), so the next
session resumes from a single inventory instead of reconstructing it from six planning files
and three open PRs.

Demo prep was never a GSD phase. It ran 2026-09-14 → 2026-09-18 as three strands — getting
Phase 209 merged, preparing the demo, and an operator-requested doc reconciliation — and
produced **11 merged PRs, 3 still open**, plus a large set of findings that were recorded but
not acted on because the demo date was fixed.

---

## 0. Act on these first

Two are new to this compilation; the rest are the highest-cost items already recorded.

| | Item | Why now |
|---|---|---|
| **0.1** | **`phase-206-dashboard-ui-coverage` exists only on one machine.** | See §1.2. 24 commits, never pushed; its phase artifacts are gitignored, so they are not in git at all. A lost laptop loses 5 of 13 plans of work with no remote copy. **Push the branch today.** |
| **0.2** | **PR #31 → then retarget #32.** | #32 is stacked on #31's branch. GitHub does not always auto-retarget when the base survives a merge, so #32 must be pointed at `main` by hand after #31 lands. Between them they carry ~9 real defects. |
| **0.3** | **CLI vs dashboard score divergence.** | §4. Two client-deliverable PDFs, 15/100 and 19/100, one click apart on the same screen. The only item here that can reach a client. |
| **0.4** | **PR #30 — merge or close.** | §6. Pure judgment, no work. It has been the sole open thread since 2026-09-16. |
| **0.5** | **The arm64 lab blocker is recorded nowhere on `main`.** | §5.1. `docs/demo-runbook-2026-09-18.md` does not mention it. It will be rediscovered the hard way by the next person on Apple Silicon. |

---

## 1. Where v5.24 stands — the position demo prep interrupted

**Milestone:** v5.24 *UAT Coverage Drain* — `status: executing`.
**Goal:** turn the release-gate document from a record of *what was checked* into a record of
*what is covered*, and make the gap worklist derive itself so it cannot silently accumulate
again.

### 1.1 Phase ledger

| Phase | Title | State |
|---|---|---|
| 203 | Catalog Freshness Drain | ✅ complete |
| 204 | Worklist Truth & Derivation | ✅ complete |
| 205 | Guard Integrity | ✅ complete |
| **206** | **Dashboard UI Coverage Drain** | **⏸ PAUSED at 5 of 13 plans** |
| 207 | Browser-Only Coverage Verdict | ▫ not started |
| 208 | Security, Report Coverage & Doc Debt | ▫ not started |
| 209 | Deliverable Reachability | ✅ complete, merged (PR #19) |

Four of seven done. **206 is the resume point**; 207 and 208 then close the milestone, followed
by the audit.

### 1.2 Phase 206 — the pause, and the risk in it

Paused **2026-09-13 by operator decision** for the demo, explicitly *not* abandoned. Resume with
`/gsd-autonomous --from 206 --to 206`. Tracked at P2 as **999.114** in `HORIZON.md`; the full
pause record is in `STATE.md` § "Phase 206 PAUSE RECORD".

- **Done:** 206-01 / 02 / 03 / 05 / 06 — 8 UAT cases dispositioned, vitest 404 → 414 passing.
- **Remaining:** 206-04 / 07 / 08 / 09 / 10 / 11 / 12 / 13.
- **By design, no disposition has been flipped in `docs/UAT-SERIES.md`** — all three coupled doc
  artifacts are fenced into 206-13, which runs last.
- Enforced by `tests/test_paused_phase_resume_gate.py` (RESUME-01/02/03), which fails if the
  ROADMAP box is checked while STATE.md still holds the pause record, or if v5.24 is archived
  while any phase is unchecked.

> **⚠ The 24 commits are local-only.** `git ls-remote --heads origin` returns no
> `phase-206-dashboard-ui-coverage`. The ROADMAP already warns *"do not `git clean` that
> branch"* because the phase artifacts are gitignored and live on disk only — but the branch
> itself was never pushed either, so there is no remote copy of any of it. This is the single
> largest recoverable risk in the project right now and it costs one `git push` to close.

### 1.3 Standing constraints still in force

Carried unchanged through demo prep. None were discharged.

- All mutating GSD `state.*` / `roadmap.*` / `phase.complete` / `milestone.complete` verbs
  remain **UNSAFE on this machine** (CLAUDE.md §TOOL-05) — a semantic defect class producing
  well-formed but *wrong* values that both textual corruption signatures read as clean. Every
  phase and milestone close is hand-written under the pre-image + signature-diff protocol.
- `requirements mark-complete` over-flips multi-phase requirements — hand-flip and verify.
- **Never bump a `last_verified` date without re-verifying against the `source_url`.** A
  recorded deferral is honest; a bumped date fabricates an attestation.
- **Recompute, never transcribe, any count from this milestone** —
  `.venv/bin/python -m scripts.uat_corpus reconcile` before citing a number in any phase,
  review, or close. A frozen literal count in the milestone block is the exact defect
  COV-01/COV-02 exist to prevent.
- Any `src/dashboard/*.tsx` change needs `npm run build` + `npm run lint` in `src/dashboard/`
  before it counts as complete — FastAPI serves pre-built statics.

### 1.4 Date-gated catalogs that trip next

From `STATE.md` § D-07. The one that matters in this window:

| Catalog | `last_verified` | Threshold | Trips |
|---|---|---|---|
| `quirk/scanner/hw_cve.py` | 2026-09-13 | 30 days | **2026-10-13** |
| `quirk/qramm/model_meta.py` | 2026-08-11 | 90 | 2026-11-09 |
| `quirk/compliance/cmvp.py` | 2026-08-25 | 90 | 2026-11-23 — **never run `quirk compliance cmvp refresh`** (RVW-022) |
| `quirk/scanner/snmp_meta.py`, `pqc_deadlines.py` | 2026-09-02 | 90 | 2026-12-01 |

`hw_cve` trips in three weeks. Worth doing inside this milestone rather than meeting it red.

---

## 2. Defects found and fixed — merged

All on `main`. Listed because the *pattern* matters more than the individual fixes (§6).

| PR | Defect |
|---|---|
| #20 | **"Stabilize scan reliability — scan error rate is 90.5%"** reported a closed-port sweep as scanner unreliability. It was 335 of 370 probed ports being closed on an 11-port sweep. Wording fixed; **the metric was deliberately not changed** — `scan_error_rate` is a scoring input, and the counterfactual at the true 1.1% moves the estate from 15 to 18. Changing a displayed sentence and changing a scored quantity are different risk classes four days out. |
| #21 | **Report downloads served a different scan than the dashboard displayed.** Wrong output directory, HTTP 200 on every format. |
| #22 | **The sensor image silently produced no PDF** for any containerised scan. `render_pdf_report()` caught the error, returned `False`, scan exited 0 with eleven artifacts and no warning. Fixed in the `sensor.Dockerfile` — not in the running container — so the shipped image is repaired for everyone. |
| #24 | `scripts/validate-fresh-install.sh` — nine outcome-asserting checks, built entirely on "assert the artifact, not the exit code". |
| #25 | Disk check: wrong wording (read as RAM), a guessed threshold, and it read one mount. **Operator caught this**; the misleading message turned out to hide three separate bugs. |
| #26 | venv reuse mis-filed as a doc divergence. **Operator caught this too.** |
| #27 | Linux had no Docker install path documented; lab disk requirement never stated. |
| #28 / #29 | Doc reconciliation — four mechanical drifts, then a falsified dependency claim, 5 undocumented env vars, lab addressing. |

Earlier in the same window, from the 2026-09-14 session:

- **The rollup equation did not divide.** `76 / 1.25 = 61, capped to 15` printed `= 15` on a
  client-facing scorecard, across **five** render sites — not the four a hand-derived list had
  claimed. Fixed once, in one shared helper.
- **The crown-jewel ring rendered black** and had since Phase 195, behind green API, green unit
  tests and a correct bundle. Cytoscape draws to `<canvas>` with its own parser and cannot read
  the modern space-separated `hsl()` syntax `--accent`'s raw components produce.
- **The Exposure Map drew 1225 edges where 19 existed**, 32% of them an endpoint joined to
  itself. Diagnosed as a rendering artifact, not the data.
- A SAML **encryption** certificate was titled "signing".

---

## 3. Defects found, fixes still open — PRs #31 and #32

These are the largest unlanded finding set. Both opened 2026-09-17, both `mergeable_state:
unstable`, and **#32 is stacked on #31's branch**.

### 3.1 PR #31 — `sslyze` was never a declared dependency

`sslyze` drives the primary TLS scanner and is the **only** engine for the email and broker TLS
probes. It appeared nowhere in `pyproject.toml` — not in core, not in any extras group
(`email = []` was literally empty). A clean `pip install quirk-scanner`, with or without extras,
never installed it.

Nothing failed loudly because every consumer guards the import: `tls_scanner.py` degraded
silently to the stdlib fallback, so **the flagship scanner shipped in its reduced mode with no
error**. Verified: across an 82-package resolution, `quirk-scanner` is the only package that
requires it — there was no transitive path. It worked only where sslyze happened to already be
present. Surfaced by an operator hitting the rejection banner on a fresh Ubuntu install.

Falsified alongside it:

- The error hint told operators to run `pip install 'quirk[motion]'` — **wrong package name**
  *and* an extras group that never contained sslyze. The suggested command could not fix the
  failure it was printed for.
- `test_extras_concurrency_expander.py` asserted the literal `"is not installed — pip install
  'quirk["`, **pinning that false hint in place for ~9 milestones.** Hardcoding the bracket is
  what let a broken hint pass CI.
- Regenerating the `operators-guide.md` extras table from `pyproject.toml` found **all four rows
  drifted** — `[cloud]` claimed 3 packages against an actual 7, and named `google-cloud-kms`,
  which is not there at all.
- UAT-32-04 staged the email stdlib fallback by *uninstalling sslyze* — a premise
  `run_scan.py:3869-3872` makes unreachable, since the email phase is then skipped entirely and
  the fallback is never called. **The live procedure could not have passed as written.** It was
  dispositioned PASS on three unit tests that are correct but cannot observe the phase-level
  skip they stood in for.

### 3.2 PR #32 — connector field reference + 9 multihost hosts + 5 bug fixes

Started as "write down what to type in each connector's fields" and turned up five defects.

**The trap it documents:** 16 of 25 connectors take **detail fields** that do *not* read the
main target list. Leave them blank and the connector probes nothing, **the scan still succeeds**,
and the tab renders empty with no error. An operator hit exactly this — Identity and Data at
Rest both blank after a clean multihost scan.

| Defect | Detail |
|---|---|
| **The `kerberos` profile could never provision — on any platform.** | Three stacked defects, each hiding the next: Debian's packaged `smb.conf` sets `server role = standalone server` and `samba-tool domain provision` reads it first and aborts; bookworm split the AD schema into an uninstalled `samba-ad-provision`; and provisioning sets NT ACLs via an xattr overlayfs does not support. |
| **The JWT connector could not scan any private or loopback target.** | `_fetch_jwks` runs `validate_external_url()` but neither it nor its two callers accepted `allow_internal`, and `run_scan.py` never passed one — so RFC1918 and loopback were rejected regardless of `security.allow_internal_targets`. **The chaos lab's own documented `jwt` profile had never been scannable.** Measured 0 → 4 endpoints. |
| `jwt_targets` documented as `.../token` | The connector builds JWKS paths by concatenation, so it requested `/token/.well-known/jwks.json`. Measured: `/token` → 0 endpoints, base URL → 1. |
| `mysql_targets` unset in the multihost config | Although `mh-db-hr` was already a container and already in `targets.cidrs` — the same "`enable_*` alone probes nothing" trap the file's own `pg_targets` comment records, pointed at the other engine. |
| Five operators-guide scanner-matrix rows carried `(no dedicated doc yet)` | All five now link to the new reference. |

Also adds 9 connector-coverage hosts to the multihost profile (Samba AD DC, Vault, four JWT
variants, Postfix, Dovecot), taking it **33 → 42 containers**, each verified against the live
subnet rather than assumed. Because `mh-kdc` publishes no ports, **multihost Kerberos works on
macOS where the standalone profile structurally cannot** (it would collide with the KDC macOS
runs on `:88`).

Limitations recorded rather than smoothed over: `mh-prober` installs `.[all]`, which excludes
`[identity]`, so **the prober cannot scan Kerberos**; the UDP AS-REQ probe times out and falls
back to TCP, leaving UDP enctype enumeration unexercised; Postfix's RSA-only ciphers do not
negotiate under the stdlib fallback. DNSSEC, S/MIME and AD CS hosts were deliberately deferred
rather than half-landed.

---

## 4. The open architectural defect

**Two client-deliverable PDFs, different headline scores, one click apart.**

Tracked at `.planning/todos/pending/cli-dashboard-score-divergence-same-scan.md`; read the
**ESCALATION 2026-09-16** section before touching either reporting surface.

| Artifact | Score | CRITICALs |
|---|---|---|
| `report-{stamp}.pdf` — one of the five Phase 209 downloads | **15 / 100** | 5 |
| Export PDF — immediately adjacent button | **19 / 100** | 7 |

Reproduced on scan stamp `20260916-145333`, a single clean 18s run with 12 minutes between runs,
so this is **not** the `SESSION_BRACKET` merge. Root cause is architectural:
`quirk/engine/findings_evaluator.py` has **zero** SAML/Kerberos/DNSSEC rules while
`quirk/dashboard/api/routes/scan.py` has all three, and the dashboard emits the SAML finding
twice.

**Why it escalated:** the recorded mitigation was *"do not put the two surfaces side by side"* —
written when one score lived in a terminal and the other in a browser. **Phase 209 put both on
the same page**, as adjacent download buttons. An operator can now follow the mitigation exactly
and still hand a client two PDFs with different headline scores.

**The near-miss that makes it easy to misread:** 76 appears in both surfaces meaning different
things — the report's *pre-cap* value (`76 ÷ 1.25 = 61`) and the dashboard's *post-cap computed*
value. Under pressure that reads as agreement.

Related open scoring items: **999.111** (drawer vs roadmap disagree on score-lift across
`scan_run_id`), **999.112** (LIFT-05's four-surface numeric equality holds only for unmodified
templates), and the P2b xfail (more healthy endpoints raise the score with weakness counts held
constant — open by design, do not promote).

---

## 5. Environment and infrastructure

### 5.1 arm64 — recorded nowhere on `main`

`kenchan0130/simplesamlphp:1.19.7`, the `mh-saml-idp` host at `10.80.0.41`, publishes a
**single-architecture `linux/amd64` manifest**. Verified against the Docker Hub registry API on
2026-09-15: no arm64 variant exists under that tag. Every other multihost image is multi-arch,
including `osixia/openldap:1.5.0`; `mh-prober` builds from source.

On an arm64 guest the container will not start. The fix is `docker run --privileged --rm
tonistiigi/binfmt --install amd64` plus `platform: linux/amd64` on that one service — **not**
Docker Desktop's Rosetta, which does not exist in a native Linux guest.

`docs/demo-runbook-2026-09-18.md` does not mention any of this. Full detail and two alternative
routes are in `.planning/DEMO-COMMANDS.md` §2. **This belongs in `docs/chaos-lab.md`** so the
next person on Apple Silicon does not rediscover it.

### 5.2 Still open

- **VM disk — task 16, blocked.** 4GB free; the lab needs ~25GB (images ~20GB, the multihost
  prober alone 3.5GB). Grow the volume to 40GB. The failure mode is a confusing mid-pull layer
  error, not a clear out-of-space message. **PR #32 takes the lab 33 → 42 containers, so this
  gets worse, not better.**
- **`lab.sh up` silently reuses a stale prober image** — tracked at
  `.planning/todos/pending/lab-sh-up-silently-reuses-stale-prober-image.md`. It passes no
  `--build`. A stale image reproduced **91/100** under superseded scoring v2 where the same
  evidence scores 15/100 under v3 — exit 0, full artifact set, no warning. The mitigation is
  still a remembered command, not a mechanism.
- **BACK-51 gate false positive** — the only red on `main`. Keys on (ID, title) and scrapes a
  narrative prose line from the archived `v5.23-ROADMAP.md`, extracting the bare word "Phases"
  as the title. BACK-51 is closed at `HORIZON.md:49`. Not a required check; verified identical
  on every PR merged during demo prep.
- **Brand inconsistency.** `favicon.svg` uses `#3B9DFF` (hue ~210); the dashboard CSS
  `--accent` is `#399797` (hue 180). Two hue families shipping together, and neither clears
  3.5:1 on white. Cosmetic, but it is a one-commit fix whenever the identity work is picked up.

---

## 6. Method findings — the most reusable output

Demo prep's durable product is not the fixes. It is a set of failure shapes that recurred often
enough to be treated as laws.

**Exit code is not evidence.** Three defects found in one day all exited 0 — a stale prober
reporting a confident 91/100; download routes serving the wrong directory with HTTP 200 on every
format; a scan writing eleven artifacts with no PDF and no warning. Each was a confident success
hiding a wrong outcome. Same shape as the crown-jewel ring that rendered black for months while
API, tests and bundle were all green.
→ *Assert the observable outcome: a launched browser, `%PDF` magic bytes, an HTTP 200 carrying a
non-empty body of the right type.* `scripts/validate-fresh-install.sh` is built entirely on this.

**A count produced by the audited tool is not a measurement.** The doc audit produced **six**
findings that dissolved under a second method — including "76 undocumented config fields", which
was purely an extractor artifact, plus `5.5.7` (an OID fragment), `5.3.1` (a section number), and
`quirk hardware`, whose hits were *negative* references saying the command does not exist.
→ *Re-derive every count with an independent method before recording it. Disagreement between the
two IS the finding.* All six were recorded rather than discarded, so the next audit does not
re-find and re-disprove them.

**A self-check that exercises only the skip path proves nothing.**
`validate-fresh-install.sh --self-check` passed while skipping all nine checks.
→ *Mutation-test the guard: break the thing it watches and confirm it goes red.* Done for the
install harness and the master-guide fence tracker — breaking the tracker kills 4 of 11 tests,
restoring brings all 11 back.

**Verification commands that lie.** `$?` through a pipe captured `tail`; a lingering `cd`
produced 127; and **zsh does not word-split unquoted parameters**, so `pytest $sel` passed 53
paths as a single argument and ran **zero** tests while printing `2 warnings in 0.00s`.
→ *Use `${=sel}`; confirm an `N passed` count, never the mere absence of errors.*

**A hand-derived list of sites is not a safeguard.** The rollup "4 render sites" list was wrong —
there were 5. Fifth naming of this lesson in the project; the direct rationale for COV-01/COV-02.
→ *Enumerate from the import graph or the AST at run time.*

**A deferral's premise can expire without anyone revisiting the decision.** Phase 195 deferred
crown jewels because the then-cross-scan map appeared to need persistence. The map became
scan-scoped and that premise lapsed silently. Phase 209 did the same thing to the score-divergence
mitigation (§4).
→ *When a design changes, re-read what was deferred because of the old design.*

**Two of the best findings came from the operator, not the tooling** — the disk message that read
as RAM (which hid three separate bugs) and the venv mis-categorisation.

---

## 7. Hygiene — task 17, deferred until after the demo

Small, mechanical, and now unblocked.

- `STATE.md` `completed_phases: 3` vs ROADMAP's **4** checked boxes (203, 204, 205, 209).
- **ROADMAP Progress table is badly stale** — rows 203/204/205 read `0/? Not started` and 209
  reads `6/8 In progress`, when all four are complete. Verified 2026-09-20; still wrong.
- Retire the superseded 2026-09-14 handoff files. `HANDOFF.json`'s
  `demo_walkthrough_confirmed` block is superseded by `docs/demo-runbook-2026-09-18.md`.
- Confirm-or-close todo **999.113** — recorded CLOSED 2026-09-13 in `HORIZON.md` but still
  carried at P1; looks fixed-but-never-retired.
- Decide **BACK-51** (§5.2).
- **Retire or fold `.planning/DEMO-RUNBOOK.md` and `.planning/DEMO-COMMANDS.md`.** Both were
  written 2026-09-15 against the pre-#30 state and are superseded by
  `docs/demo-runbook-2026-09-18.md` — except for the arm64 section (§5.1), which exists in no
  other file and should move to `docs/chaos-lab.md` before either is deleted.

**21 pending todos** in `.planning/todos/pending/`. The ones demo prep touched or raised:
`cli-dashboard-score-divergence-same-scan` (escalated, §4),
`lab-sh-up-silently-reuses-stale-prober-image` (§5.2),
`saml-one-certificate-counted-twice-c-and-d` (options C+D, operator-scheduled after the next
milestone), `exposure-map-spider-web-is-an-artifact-not-the-data` (items 1–3 done, item 4 open),
`r5-ladder-fixture-is-not-the-measurement-it-claims`,
`readiness-score-denominator-is-probe-count-not-assessable-endpoints`, and
`backlog-gate-false-positive-on-archived-roadmap-prose`.

---

## 8. Awaiting an operator decision, not work

- **PR #30** — the generated master guide (`scripts/build_master_guide.py`,
  `docs/quirk-master-guide.md`, 6,513 lines, 11 tests proven non-vacuous by mutation). Read it
  and merge or close; the five sources stay canonical either way. If merged, the natural
  follow-up is a CI freshness gate asserting the committed master byte-matches a fresh
  generate, matching the four existing generator-drift gates.
- **Task 15** — send the `validate-fresh-install.sh` SUMMARY table from the VM, specifically
  checks 4 (Playwright), 7 (PDF) and 8 (downloads). *Asked twice, never received.* "No doc
  divergences" is not the same as "all checks passed."
- **SAML options C and D** — operator-scheduled for after the next milestone. Option B (titles
  only, zero score impact) shipped before the demo; C and D move the emitted score and the
  ladder fixtures.

---

## 9. Suggested order

1. **Push `phase-206-dashboard-ui-coverage`.** One command, closes the only unrecoverable risk.
2. **Merge #31, retarget #32 to `main`, merge.** Largest landed-value-per-effort, and #32 grows
   the lab, which interacts with the disk item below.
3. **Grow the VM volume to 40GB** before running the 42-container lab.
4. **Task 17 hygiene**, including moving the arm64 note into `docs/chaos-lab.md`.
5. **Decide PR #30.**
6. **Resume Phase 206** — `/gsd-autonomous --from 206 --to 206`, 8 plans remaining.
7. Phases 207 and 208, then the v5.24 audit and close.
8. **Schedule the score-divergence work as its own phase.** It is architectural, it now reaches
   client deliverables, and it is the one item here that should not ride along with something
   else.

`hw_cve.py`'s 30-day staleness gate trips **2026-10-13** — fold it into whichever phase is
running then, rather than meeting it red.
