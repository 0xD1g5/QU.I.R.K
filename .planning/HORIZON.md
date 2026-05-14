# HORIZON.md — Multi-Milestone Outlook

**Purpose:** Themes for the next 5–7 milestones — deep enough to anchor backlog grooming and inter-milestone deferrals, shallow enough to revise after each ship. **Plan the next one or two in detail; sketch the rest.**

**Last updated:** 2026-05-05 (post-v4.6 ship)
**Current state:** v4.6 Enterprise Readiness shipped 2026-05-05 — install-day UX, TLS finding gaps, multi-target ingestion, rich finding context, compliance mapping, enterprise docs. v4.7 Governance & Compliance Platform in progress (Phase 51 discussion/planning).

---

## The Primetime Bar

QU.I.R.K. is "primetime" when a consultant or enterprise security team can:

1. **Install it cleanly** — `pip install quirk` works on a fresh venv. ✅ v4.6
2. **Trust the findings** — every detected weakness is real, every missed weakness is intentional. 🟡 v4.6 closed TLS gaps; v4.7 Phase 52 closes FIPS/SOC2/ISO 27001 compliance evidence gaps.
3. **Trust the score** — single authoritative number; same in CLI report, JSON, dashboard, PDF. 🟡 v4.1 + v4.7 Phase 52 close the loop.
4. **Self-onboard** — operator can run a full engagement from `docs/operators-guide.md` alone. 🟡 v4.6 shipped the guide; v4.7 Phase 52 adds `quirk doctor`.
5. **Run on a cadence** — scheduled scans + diff against last run, surfaced in dashboard. ❌ v4.8.

**The primetime cutover is the v4.8 ship.** Everything before is gating; everything after is depth.

---

## v4.7 — Governance & Compliance Platform (in progress — plan locked)

**Status:** Phase 51 in discussion/planning. **Do not add items mid-flight.** New governance work goes to v4.8+.

**Theme:** Transform QU.I.R.K. from a technical scanner into a governance + technical deliverable. The centerpiece is **QRAMM** (Quantum Readiness Assessment & Maturity Model) — a 120-question interactive maturity assessment that sits on top of the scanner data and produces a consultant-grade scorecard. Phase 52 absorbs the three v4.6 trust/polish deferrals (COMPLY-10, COMPLY-11, DOCS-05) as a parallel track.

**Phases (6 total, critical path: 51 → 53 → 54 → 55 → 56; Phase 52 parallel with 51)**

| Phase | Name | Focus |
|---|---|---|
| 51 | QRAMM Core Infrastructure | SQLite tables, FastAPI CRUD, 120-question catalog (4 dims × 3 practices × 10 Qs), weakest-link scoring engine, `datetime.utcnow` fix |
| 52 | Compliance Uplift & Health Check | SOC2 + ISO 27001 mappings (COMPLY-11), FIPS 140-3 CBOM annotations (COMPLY-10), `quirk doctor` health CLI (DOCS-05), 4 tech debt items |
| 53 | QRAMM Evidence Bridge | Auto-populate ~30 QRAMM questions from live scan data via SESSION_BRACKET; suggested answers + human confirmation workflow |
| 54 | QRAMM Assessment UI & Scorecard | Org Profile wizard, 120-question dimension tabs, radar chart scorecard, real-time answer persistence |
| 55 | QRAMM Compliance Mapping View | 8-framework coverage table (NIST PQC, NSM-10, CNSA 2.0, ISO 27001, ETSI, PCI-DSS, CC, BSI TR-02102) |
| 56 | PDF Export & Staleness Enforcement | Combined governance + technical PDF with QRAMM section, quarterly CI staleness gate |

**What QRAMM is:** 4 dimensions × 3 practice areas × 10 questions each. Dimension score = minimum of its 3 practice scores (weakest-link rule). Profile multiplier (0.8–1.5×) adjusts for org size, sector, and regulatory obligations.

**Done when:** a consultant can run a scan, step through the 120-question wizard (with evidence pre-filled from the scan), and export a single PDF containing both the technical findings and the QRAMM scorecard with compliance framework coverage.

---

## v4.8 — Operating Model + Residual Trust (primetime cutover)

**Theme:** QU.I.R.K. transitions from a one-shot audit tool into a tool that runs on a schedule, diffs against last time, and can be driven from the dashboard by users who never open a terminal. **This is the milestone after which a customer can deploy and forget.** Also catches residual trust/polish items that surfaced after v4.7's plan locked.

**Anchor items — Operating model**

| Backlog | Item | Why this milestone |
|---|---|---|
| BACK-25 | Scheduled / continuous scanning mode | Operating model enterprise security teams actually use |
| BACK-21 | Trend analysis across scan sessions | The analytical layer beneath scheduled scans — score change, new/resolved findings |
| BACK-86 (slice 1) | Dashboard-initiated scan: configure + launch + live status | Non-CLI users get a way in; standalone single-tenant only |
| BACK-86 (slice 2) | Dashboard scan history + clone/compare | Pairs with BACK-21 to make trends visible |
| (new) | **Resumable / partial-failure scans** | Real estates always have unreachable hosts; one timeout shouldn't poison the run |
| (new) | **Operator error-message pass** | Every error path emits an actionable next step (extras, perms, network, config) |

**Anchor items — Residual trust / polish (COMPLY-10/11 and DOCS-05 moved to v4.7 Phase 52)**

| Backlog | Item | Origin |
|---|---|---|
| Phase 42 OBS-1 | **CBOM Pass-1 fix** — 5 profiles (database, registry, source, ssh-weak, storage-s3) emit zero algo components | Surfaced in v4.5 audit; not in v4.7 plan |
| BACK-40/41/42/44 | **Verify-still-landed audit** — `quirk init` template, `quirk scan` doc, dual scoring, version disagreements | Memory-flagged for verification; not in v4.7 plan |
| BACK-63 | **Score transparency in exec reports** | Methodology section + score-driver narrative |
| BACK-58 | **Document JWT `verify=False` behavior** | Trivial credibility item |
| BACK-87 | **`lab.sh` PROFILE_ARGS precedence fix** | Chaos lab harness bug; opportunistic ops wave fit |

**Pulled forward from v5.x to compress time-to-primetime:**

- BACK-86 dashboard-launched scans was originally v4.9-shaped — pulling slice 1 forward because the primetime bar requires non-CLI access. SaaS multi-tenancy stays in v5.1.
- Resumable-scan and error-message work were implicit Polish backlog items — promoting to first-class because partial-failure handling is what separates "demoable" from "deployable."

**Out-of-scope:** API breadth, auth scanning, distributed sensors, QRAMM (now v4.7).

**Done when:** a customer can configure a weekly scan from the dashboard, get a Slack/email/diff artifact when posture drifts, and never SSH into the QUIRK host.

---

## v4.9 — API Surface Depth & Authenticated Scanning

**Theme:** First post-primetime capability milestone. Closes the passive-only API gap and introduces the optional credential model that unlocks deeper authenticated findings across multiple scanners.

**Anchor items**

| Backlog | Item |
|---|---|
| BACK-64 | **Authenticated scan mode** (credential model + security review gate) — foundational; everything below depends on it |
| BACK-09 | Active REST API fuzzing for crypto posture |
| BACK-10 | OpenAPI / Swagger spec analysis |
| BACK-11 | Bearer token interception and analysis |
| BACK-24 | Code signing certificate inventory |

**Why BACK-64 first:** credential storage is a platform concern; design once, all scanners adopt uniformly. Kerberos (LDAP bind), SSH (key-based login), and JWT/API (OAuth client creds) all benefit.

**Done when:** a customer with a service account can run an authenticated scan and see findings invisible to the unauthenticated path.

---

## v5.0 — *(slot open — QRAMM pulled into v4.7)*

**Theme:** TBD. QRAMM Governance Integration (originally planned here as BACK-68 → BACK-73) was pulled forward into v4.7 because the evidence bridge compounds the value of the enterprise docs and compliance mapping already shipped in v4.6. This slot will be shaped after v4.9 ships and the post-API-depth backlog is visible.

**Candidates at shaping time:** extended audit trail / SIEM export, advanced QRAMM iteration (custom frameworks, maturity benchmarking), or first-party integrations (Jira, ServiceNow, Slack) depending on enterprise adoption signals.

**Done when:** shaped at v4.9 wrap.

---

## v5.1 — Distributed Architecture & SaaS Foundation

**Theme:** QU.I.R.K. graduates from single-host tool to platform. Multi-segment scanning + multi-tenant dashboard. v2-scale capability promised in BACK-26.

**Anchor items**

| Backlog | Item |
|---|---|
| BACK-26 | Distributed multi-node scanner architecture (agent/console split) |
| BACK-86 (slice 3) | SaaS-mode dashboard — auth, multi-tenancy, per-tenant data isolation |
| (new) | Per-segment topology view in dashboard |
| (new) | Agent auth tokens + console registration |

**Dependencies:** v4.8 must be solid — scheduled scans + dashboard-launch are the substrate this milestone extends.

**Risk:** large-scope; may need to split into v5.1a (distributed) + v5.1b (SaaS) once detailed planning starts.

---

## v5.2 — Chaos Lab Coverage + Tech Debt Sweep

**Theme:** Bundled debt phase between capability cycles. Closes the lab-shaped backlog and accumulated cleanup items in one focused milestone instead of scattering them as tax across feature milestones.

**Anchor items**

| Bundle | Items |
|---|---|
| Chaos lab targets | BACK-80 postgres-tls + redis-tls, BACK-81 OQS-nginx PQC-hybrid (the scoring-ceiling target!), BACK-82 SMTP/STARTTLS, BACK-83 gRPC TLS, BACK-84 Kafka TLS |
| Identity lab gap | BACK-78 identity scoring evidence keys (Kerberos KDC, SAML SP, DNSSEC zone) |
| Code cleanup | BACK-49–57 dead code, deprecation, version drift |
| Bookkeeping | BACK-62 Nyquist VALIDATION.md updates |
| Dependency hygiene | BACK-67 `defusedxml.lxml` → `lxml` with manual XXE controls |

**Why a sweep:** GSD's per-phase overhead means 10 trivial PRs cost more than one bundled phase. Memory's "lab-shaped, batch don't expand" guidance applies.

**The OQS-nginx target (BACK-81) is the strategic centerpiece** — it's the only chaos lab target that scores *above* "good classical TLS" in the readiness model, which grounds the scoring ceiling in a concrete demoable artifact.

---

## Items Pulled Forward (rationale log)

Track here when the horizon shifts so future-you can see why:

| Item | From | To | Rationale | Date |
|---|---|---|---|---|
| Phase 64.1 (Audit Residual Blockers) | unplanned | v4.8 bridge between 64 and 65 | 19 BLOCKERs from 2026-05-08 audit were untriaged after Wave A. 5 of these directly undermine Phase 64 UAT (trend session window) or Phase 65 foundations (non-transactional migrations). Inserting 64.1 to triage all open findings and fix the foundation-touching subset before any operating-model features extend those code paths. Remaining 14 deferred to v4.9. | 2026-05-10 |
| v4.8 scope expansion: Wave A/B split (audit-driven) | HORIZON v4.8 sketch (trust & polish) | full 13-phase Wave A+B | HORIZON v4.8 sketch listed a small trust/polish wave. The 2026-05-08 pre-v4.8 audit revealed 44 BLOCKERs / 96 WARNINGs across 116 files — a primetime cutover was not defensible without addressing the critical security/correctness findings first. Wave A absorbed the 15 gating blockers; Wave B absorbed the HORIZON operating-model anchor items (scheduled scans, trend analysis, dashboard-initiated scan). Scope expanded from ~5 phases to 13; justified by audit finding density. v4.9 now owns the remaining 121 open findings (92 WARNINGs + 29 INFOs + 13 deferred BLOCKERs). | 2026-05-14 |
| BACK-86 slice 1 (dashboard-launched scan) | v4.9-shaped | v4.8 | Primetime bar requires non-CLI access | 2026-05-05 |
| BACK-25 + BACK-21 (scheduled + trend) | implicit | v4.8 explicit | "Run on a cadence" is gate 5 of primetime | 2026-05-05 |
| BACK-58 (document JWT verify=False) | misc | v4.8 | v4.7 plan already locked — defer one milestone | 2026-05-05 |
| BACK-63 (score transparency) | unscheduled | v4.8 | v4.7 plan already locked — defer one milestone | 2026-05-05 |
| BACK-87 (lab.sh PROFILE_ARGS) | misc | v4.8 opportunistic | v4.7 plan already locked; chaos lab harness bug fits any ops wave | 2026-05-05 |
| BACK-40/41/42/44 verify-still-landed | v4.7 (briefly) | v4.8 | v4.7 plan didn't include them; bundle with operating-model trust polish | 2026-05-05 |
| Phase 42 OBS-1 CBOM Pass-1 fix | v4.7 (briefly) | v4.8 | v4.7 plan didn't include it; primary residual CBOM correctness bug | 2026-05-05 |
| QRAMM (BACK-68 → BACK-73) — Governance & Compliance Platform | v5.0 | v4.7 | Evidence bridge compounds v4.6 compliance mapping; COMPLY-10/11/DOCS-05 deferrals create a natural anchor for Phase 52; pulling forward eliminates a capability cliff before v5.x distributed work | 2026-05-05 |
| COMPLY-10, COMPLY-11, DOCS-05 (Trust & Polish) | v4.7 standalone | v4.7 Phase 52 | Absorbed into v4.7 as Phase 52 parallel track; same milestone, not a separate one | 2026-05-05 |

---

## Re-evaluation Cadence

After every milestone closes, before opening the next:

1. Does the next-up theme still make sense given what just shipped?
2. Did this milestone surface anything that should jump the queue?
3. Is the 2:1 operational/capability ratio still holding (one ops-depth milestone per two capability-breadth milestones)?
4. Has the primetime bar moved? Did this ship advance gates 1–5, or expand them?

**Revise this file at every milestone wrap.** Pulled-forward / pushed-back decisions go in the rationale log above so the reasoning isn't lost.

---

## What This Document Is Not

- **Not a commitment.** Themes survive; details rarely do. Phase decomposition happens at `/gsd-new-milestone` time, not here.
- **Not a backlog replacement.** ROADMAP.md `## Backlog` is still the source of truth for individual items; this is the *grouping* layer above it.
- **Not exhaustive.** New backlog items will arrive between now and v5.2. The horizon should absorb them, not be invalidated by them.
