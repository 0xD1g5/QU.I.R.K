# HORIZON.md — Multi-Milestone Outlook

**Purpose:** Themes for the next 5–7 milestones — deep enough to anchor backlog grooming and inter-milestone deferrals, shallow enough to revise after each ship. **Plan the next one or two in detail; sketch the rest.**

**Last updated:** 2026-05-23 (post-v5.1 ship)
**Current state:** v5.1 Authenticated Scanning + API Surface Depth SHIPPED 2026-05-23 — ephemeral credential model, OpenAPI/bearer analysis, LDAP/TLS-EKU code-signing inventory, and gated active REST fuzzing all live; `SCORE_WEIGHTS` at 303.0/41. The detection surface is now deep and broad across six scanner families. **Next milestone (v5.2) scoped below — the deliverable (report) layer is the chosen anchor.** The forward outlook has been re-prioritized through a product lens: for a consulting tool, the report a client receives *is* the product, and no milestone has yet owned the output layer.

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

QRAMM (Quantum Readiness Assessment & Maturity Model) — 120-question maturity assessment with evidence bridge from live scans, compliance framework coverage view, combined governance+technical PDF export, quarterly CI staleness gate. 6 phases (51–56) + Phase 56.1. Audit: `.planning/v4.7-MILESTONE-AUDIT.md`.

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

# Forward Outlook — Re-prioritized 2026-05-23 (product lens)

**Framing:** v4.x–v5.1 built a deep, broad *detection* engine across six scanner families (TLS, SSH, identity, data-at-rest, data-in-motion, API/auth) plus governance (QRAMM) and a public distribution. **What has never had a dedicated milestone is the output layer** — the report the consultant hands the client. For a consulting-grade tool, that report *is* the product; better detection only creates value if it's communicated defensibly. The forward outlook is therefore re-ordered: **deliverable first, adoption second, scale-out last.**

The 2:1 capability/ops cadence still holds: v5.0 (ops) → v5.1 (capability) → **v5.2 (deliverable/capability) → v5.3 (adoption/ops) → v5.4 (stabilization + scale validation).**

## v5.2 — Consulting-Grade Reporting *(NEXT — user-anchored North Star)*

The deliverable layer. Make the document a consultant hands a CISO genuinely client-ready: narrative executive summary, defensible per-finding context, a first-class prioritized remediation roadmap, and consistent, well-formatted PDF/HTML/CLI output. This is the highest-leverage milestone because it monetizes every detection investment already shipped and is the literal moment-of-truth of an engagement.

| Backlog | Item | Why it matters |
|---|---|---|
| 999.72 | Rich per-finding context — quantum-risk explanation, "so what," remediation guidance | Turns a finding list into an advisory document a non-cryptographer can act on |
| 999.56 | Score-transparency executive reports — show how the readiness number is built | Defensibility: the client must trust *and understand* the score |
| 999.82 | Executive-summary score↔severity consistency | Correctness: exec summary must not contradict the detail tables (latent inconsistency) |
| 999.2 | PDF report formatting / professional layout / branding | Presentation quality is the credibility signal for a paid deliverable |
| WR-05 (v5.1) | Surface code-signing cert expiry as a finding | Report-content gap — folds naturally into the finding-quality theme |

**Anchor / North Star:** the **narrative executive report** — a CISO-readable document that leads with the readiness story, not a raw finding dump.
**Why now:** explicit user priority; compounds all prior detection work; closes the gap between "we detect everything" and "we communicate it like consultants."
**Risk:** scope creep into endless visual polish. Mitigation: anchor on the executive narrative + remediation roadmap as the must-ship core; treat branding/theming as nice-to-have.
**Tax to fold in:** WR-02/03/04/06 cleanup as a small dedicated phase.

## v5.3 — Adoption & Integration Surface *(was Candidate B)*

Make QU.I.R.K. load-bearing inside someone else's workflow. First-party integrations over capability breadth.

| Theme | Items | Note |
|---|---|---|
| Notification fan-out | Slack / email / webhook from scheduled-scan drift events | **Start here — drift events are already emitted but never delivered (half-built; lowest-risk, highest-signal)** |
| SIEM / observability export | Splunk HEC, Elastic, generic syslog/CEF | Surface findings into existing security stacks |
| Ticketing integration | Jira / ServiceNow auto-ticket per finding with QRAMM evidence | Closes the remediation loop |
| Dashboard team auth | API key / token-based single-tenant dashboard auth | Team sharing without SaaS multi-tenancy |

**Why now:** v4.10 shipped distribution; reporting (v5.2) makes the deliverable excellent; v5.3 makes it *flow into* the customer's existing tooling. Lower technical risk than capability work, higher adoption signal.
**Risk:** without a North Star it sprawls into a grab-bag. Mitigation: finish notification fan-out first as the anchor, then add one export + one ticketing integration.

## v5.4 — Stabilization + Distributed/SaaS Validation *(was the v5.2 sketch)*

Breather cycle: docs (999.58 comprehensive architecture document, 999.59 operators-guide all-settings coverage), residual tech-debt sweep, dependency hygiene. **Commit to distributed/multi-tenant infrastructure (999.22 multi-node agent/console split, SaaS multi-tenancy) only if v5.3 adoption surfaces a real multi-segment customer ask.** If adoption stays single-host single-tenant, this milestone stays a stabilization cycle and the SaaS bet defers again.

| Backlog | Item |
|---|---|
| 999.58 | Comprehensive architecture document |
| 999.59 | Operators-guide all-configurations-and-settings coverage |
| 999.22 | Distributed multi-node scanner architecture (agent/console split) — *gated on adoption signal* |
| — | SaaS-mode dashboard: auth, multi-tenancy, per-tenant isolation — *gated on adoption signal* |

---

## Items Pulled Forward (rationale log)

Track here when the horizon shifts so future-you can see why:

| Item | From | To | Rationale | Date |
|---|---|---|---|---|
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
