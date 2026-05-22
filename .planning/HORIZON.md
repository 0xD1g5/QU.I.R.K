# HORIZON.md — Multi-Milestone Outlook

**Purpose:** Themes for the next 5–7 milestones — deep enough to anchor backlog grooming and inter-milestone deferrals, shallow enough to revise after each ship. **Plan the next one or two in detail; sketch the rest.**

**Last updated:** 2026-05-22 (post-v4.10 ship)
**Current state:** v4.10 Launch Readiness SHIPPED 2026-05-21 — public-registry release pipeline live (PyPI `quirk-scanner`, GHCR multi-arch image, Sigstore attestations, Homebrew tap formula). v4.7 through v4.10 all closed since the last HORIZON revision. Next milestone (v5.0) unscoped — candidate themes below.

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

## v5.0 — *(unscoped — candidate themes for shaping)*

The primetime bar is met. v5.0 is the first milestone of a post-launch phase — themes available depend on which value lever to push next. Three credible candidates, picked in detail at `/gsd-new-milestone` time:

### Candidate A — Authenticated Scanning + API Surface Depth *(was the v4.9 sketch theme)*

Closes the passive-only-API gap and adds an optional credential model that unlocks deeper findings across multiple scanners.

| Backlog | Item |
|---|---|
| BACK-64 | Authenticated scan mode (credential model + security review gate) — foundational |
| BACK-09 | Active REST API fuzzing for crypto posture |
| BACK-10 | OpenAPI / Swagger spec analysis |
| BACK-11 | Bearer token interception and analysis |
| BACK-24 | Code signing certificate inventory |

**Why now:** post-launch users want deeper findings the unauthenticated path can't reach. Credential storage is a platform concern — design once, every scanner adopts uniformly.
**Risk:** introduces a security-sensitive subsystem (credentials at rest, scoped use); needs a security review gate baked into the milestone.

### Candidate B — Adoption & Integration Surface

Lean into v4.10's public-launch foundation and make QU.I.R.K. load-bearing in a customer workflow. First-party integrations rather than capability breadth.

| Theme | Items |
|---|---|
| SIEM / observability export | Splunk HEC, Elastic, generic syslog/CEF — surface findings into existing security stacks |
| Ticketing integration | Jira / ServiceNow auto-ticket creation per finding with QRAMM evidence |
| Notification fan-out | Slack/email/webhook from scheduled-scan drift events (currently emitted but not delivered) |
| API key / token-based dashboard auth | Lets the dashboard be shared across a team (single-tenant) without SaaS multi-tenancy |
| Public-launch follow-through | Asciinema demo, homebrew tap bootstrap, Path C deferrals (BACK-89/90 release-UAT-automation) |

**Why now:** v4.10 shipped the distribution; v5.0 makes the distributed product *useful in someone else's workflow*. Lower technical risk than authenticated scanning; higher adoption signal.
**Risk:** without a primary anchor item it can sprawl into a polish-grab-bag — needs one clear North Star integration.

### Candidate C — Stabilization + Tech Debt Sweep *(was v5.2 sketch)*

A deliberate non-feature milestone after four heavy capability milestones. Pulls v5.2 forward to give the codebase a rest cycle before the next big capability push.

| Bundle | Items |
|---|---|
| Chaos lab targets | BACK-80 postgres-tls + redis-tls, BACK-81 OQS-nginx PQC-hybrid (the scoring-ceiling target!), BACK-82 SMTP/STARTTLS, BACK-83 gRPC TLS, BACK-84 Kafka TLS |
| Identity lab gap | BACK-78 identity scoring evidence keys (Kerberos KDC, SAML SP, DNSSEC zone) |
| Code cleanup | BACK-49–57 dead code, deprecation, version drift |
| Bookkeeping | BACK-62 Nyquist VALIDATION.md updates |
| Dependency hygiene | BACK-67 `defusedxml.lxml` → `lxml` with manual XXE controls; Node.js 20 → 24 in release-container action versions |
| v4.10 residuals | Phase 42 OBS-1 CBOM Pass-1 fix (5 profiles emit zero algo components), BACK-63 score transparency, BACK-58 JWT `verify=False` docs |

**Why now:** four milestones at the rate of one every 4–7 days is unsustainable; this is the "breathe" cycle. The OQS-nginx target is the only chaos lab profile that scores *above* "good classical TLS" — anchors the scoring ceiling in a demoable artifact.
**Risk:** doesn't move adoption forward — could feel like marking time if user feedback is asking for capability.

---

## v5.1 — *(sketch, shape after v5.0 close)*

Whichever candidate above is *not* chosen for v5.0 is the leading sketch for v5.1. The 2:1 capability-to-ops ratio holds either way — if v5.0 is capability (A) or adoption (B), then v5.1 should be the other side of the pair, with the stabilization sweep (C) following.

---

## v5.2 — *(sketch — Distributed Architecture & SaaS, pending validation)*

Was originally v5.1 (Distributed Architecture & SaaS Foundation). Pushed back because v5.0/v5.1 should validate adoption signal *before* committing to multi-tenant infrastructure. If post-launch adoption stays single-host single-tenant, this milestone gets de-prioritized in favor of more capability work. If multi-segment scanning shows up as a real customer ask, this becomes the next big bet.

| Backlog | Item |
|---|---|
| BACK-26 | Distributed multi-node scanner architecture (agent/console split) |
| BACK-86 (slice 3) | SaaS-mode dashboard — auth, multi-tenancy, per-tenant data isolation |
| — | Per-segment topology view in dashboard |
| — | Agent auth tokens + console registration |

---

## Items Pulled Forward (rationale log)

Track here when the horizon shifts so future-you can see why:

| Item | From | To | Rationale | Date |
|---|---|---|---|---|
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
