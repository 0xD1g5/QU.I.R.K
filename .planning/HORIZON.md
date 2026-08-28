# HORIZON.md — Multi-Milestone Outlook

**Purpose:** Themes for the next 5–7 milestones — deep enough to anchor backlog grooming and inter-milestone deferrals, shallow enough to revise after each ship. **Plan the next one or two in detail; sketch the rest.**

**Last updated:** 2026-08-26 (post-v5.15 ship — full re-evaluation cadence run, the one owed since 2026-08-11)
**Current state:** The hardware-lifecycle arc is closed. v5.13 (Phases 154–156) built the drift/EOL engine, v5.14 (157–160) closed its fleet-coverage and forecasting gaps, and v5.15 (161–163) drained the last four backlog items — shipping as the first published release since 5.12.0, after v5.13/v5.14's two-component tags silently missed `release.yml`'s glob entirely. **ROADMAP.md's `## Backlog` is now genuinely drained**: nothing remains unpromoted except the parked SaaS block. **v5.16 Review Drain & Gate Integrity is now open** (Phases 164+) — the ops cycle the 2:1 cadence has owed since v5.12, closing the open findings from the 2026-08-24 third-party functional review. See rationale log below. Themes past v5.16 are sketched fresh in this pass (Forward Outlook, revised 2026-08-26). SaaS multi-tenancy stays parked (no business-model signal, unchanged since v5.4).

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
