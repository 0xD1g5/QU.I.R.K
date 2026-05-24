# Roadmap: QU.I.R.K. — Quantum Infrastructure Readiness Kit

## Milestones

- ✅ **v3.9 Gap Closure** — Phases 1–11, 40 plans (shipped 2026-04-04) → `.planning/milestones/v3.9-ROADMAP.md`
- ✅ **v4.1 Foundation Polish** — Phases 12–16, 17 plans (shipped 2026-04-08) → `.planning/milestones/v4.1-ROADMAP.md`
- ✅ **v4.2 Identity Crypto** — Phases 17–24, 14 plans (shipped 2026-04-24) → `.planning/milestones/v4.2-ROADMAP.md`
- ✅ **v4.3 Data at Rest** — Phases 25–31, 24 plans (shipped 2026-04-26) → `.planning/milestones/v4.3-ROADMAP.md`
- ✅ **v4.4 Data in Motion** — Phases 32–37, 33 plans (shipped 2026-04-29) → `.planning/milestones/v4.4-ROADMAP.md`
- ✅ **v4.5 Reliability & Gap Closure** — Phases 38–44, 40 plans (shipped 2026-05-03) → `.planning/milestones/v4.5-ROADMAP.md`
- ✅ **v4.6 Enterprise Readiness** — Phases 45–50, 24 plans (shipped 2026-05-05) → `.planning/milestones/v4.6-ROADMAP.md`
- ✅ **v4.7 Governance & Compliance** — Phases 51–56 (shipped 2026-05-08) → `.planning/milestones/v4.7-ROADMAP.md`
- ✅ **v4.8 Pre-Primetime** — Phases 57–68, 53 plans (shipped 2026-05-14) → `.planning/milestones/v4.8-ROADMAP.md`
- ✅ **v4.9 Audit Depth** — Phases 69–77, 38 plans (shipped 2026-05-15) → `.planning/milestones/v4.9-ROADMAP.md`
- ✅ **v4.10 Launch Readiness** — Phases 78–85, 31 plans (shipped 2026-05-21) → `.planning/milestones/v4.10-ROADMAP.md`
- ✅ **v4.10.1 Scoring Correctness Hotfix** — Phase 86, 3 plans (shipped 2026-05-22) → `.planning/milestones/v4.10.1-ROADMAP.md`
- ✅ **v5.0 Stabilization + Tech Debt Sweep** — Phases 87–92, 16 plans (shipped 2026-05-22) → `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v5.1 Authenticated Scanning + API Surface Depth** — Phases 93–96, 16 plans (shipped 2026-05-23) → `.planning/milestones/v5.1-ROADMAP.md`
- 🔄 **v5.2 Consulting-Grade Reporting** — Phases 97–100 (in progress)

---

<details>
<summary>✅ v3.9–v5.1 (Phases 1–96) — SHIPPED</summary>

All completed milestone roadmaps are archived in `.planning/milestones/`. Next milestone continues from Phase 97.

</details>

---

## v5.2 Consulting-Grade Reporting

**Goal:** Make the artifact a consultant hands a client genuinely client-ready — a narrative, defensible, professionally-formatted deliverable — rather than a raw finding dump.

**Phases:**

- [x] **Phase 97: v5.1 Tech-Debt Cleanup** — Close carried WR-02/03/04/06 items before report work begins (completed 2026-05-23)
- [ ] **Phase 98: Executive Narrative + Score Transparency** — The anchor: narrative exec summary, prioritized remediation roadmap, subscore decomposition, consistency fix; all three render surfaces
- [ ] **Phase 99: Per-Finding Context + Code-Signing Expiry** — Enrich every finding with a quantum-risk "so what" + actionable remediation; surface code-signing cert expiry as a finding
- [ ] **Phase 100: Professional & Editable Report Delivery** — Client-ready PDF cover/layout/typography, clean table pagination, and DOCX editable export so a consultant can finalize before client delivery

## Phase Details

### Phase 97: v5.1 Tech-Debt Cleanup
**Goal**: The v5.1 carry-over design-judgment issues are corrected so the codebase entering the report milestone is sound
**Depends on**: Nothing (first v5.2 phase; orthogonal to report changes)
**Requirements**: TD-01, TD-02
**Success Criteria** (what must be TRUE):
  1. The credential env-var contract is documented accurately (no unenforced all-caps claim) and CredentialContext per-call str-copy behavior is documented under D-05 — a developer reading the code sees unambiguous, safe credential handling; the JWT pre-existing-param overwrite and scheduler auth-reject gaps are closed
  2. The 5xx cascade counter trips correctly on connection-exception failures (timeout-only servers no longer escape the cascade pause) — a scan against an unresponsive host observes the back-off pause activate
**Plans**: 4 plans

Plans:
- [x] 97-01-PLAN.md — credentials.py doc-only corrections (D-01 env-var docstring + D-02 str-copy proliferation comments)
- [x] 97-02-PLAN.md — rest_fuzzer combined failure-cascade counter (D-06 / TD-02) + regression test
- [x] 97-03-PLAN.md — JWT pre-existing-param reject (D-03) + scheduler parse-based fail-closed auth-reject (D-05), both with tests
- [x] 97-04-PLAN.md — leak-test real-path routing + PDF coverage-gap annotation (D-04) + mandatory docs/UAT/Obsidian sync

### Phase 98: Executive Narrative + Score Transparency
**Goal**: A consultant running any output surface (CLI, HTML, PDF) receives a CISO-readable executive report that leads with the readiness story, shows a prioritized remediation roadmap, and surfaces the full subscore decomposition — all three surfaces carry identical content
**Depends on**: Phase 97
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, TRANS-01, TRANS-02, TRANS-03
**Success Criteria** (what must be TRUE):
  1. The executive section of a generated report opens with a plain-language narrative (overall posture + what it means for the organisation) before any finding table appears
  2. The report's top-risks section presents the highest-priority findings framed by business impact — a non-cryptographer can read it and understand what to fix first and why
  3. The report contains a prioritized remediation roadmap section: ordered actions with rationale and relative effort/impact, not a raw severity list
  4. The six-pillar subscore decomposition (each subscore against its /25 budget) and the ÷1.5 rollup formula are visible in the report — a client asking "how did you get 72?" receives a complete answer in the document itself
  5. The executive summary's headline score and severity language match the detail findings tables — no contradiction between "GOOD" in the exec summary and "7 CRITICAL" in the body
  6. Running `quirk report`, opening the HTML in a browser, and exporting the PDF all produce the same narrative sections and score story — format-appropriate rendering, identical content
**Plans**: 3 plans

Plans:
- [ ] 98-01-PLAN.md — shared ExecContent content model, D-02/D-05 static maps, D-04 within-bucket ordering, D-06 congruence guard + unit tests
- [ ] 98-02-PLAN.md — writer seam + build-time guard; CLI + HTML/template narrative, top-risks, rollup formula, effort/impact roadmap labels (D-03/D-07) + ordering tests
- [ ] 98-03-PLAN.md — cross-surface parity test (EXEC-04/D-03a) + UAT-SERIES.md update and Obsidian sync
**UI hint**: yes

### Phase 99: Per-Finding Context + Code-Signing Expiry
**Goal**: Every finding in the report carries a quantum-risk explanation and actionable remediation guidance, turning the finding list into an advisory document; code-signing certificate expiry is surfaced as a first-class finding
**Depends on**: Phase 97
**Requirements**: CTX-01, CTX-02, CTX-03
**Success Criteria** (what must be TRUE):
  1. Each finding row or block displays a plain-language "so what" explanation — a CISO reading the report understands why the detected weakness matters for post-quantum readiness without needing to look anything up
  2. Each finding carries actionable remediation guidance specific to the detected weakness (not generic PQC boilerplate) — a practitioner can follow the guidance to address the finding
  3. A code-signing certificate that is expired or approaching expiry appears as a finding in the report with severity-appropriate classification — a consultant scanning a host with an expired code-signing cert sees it called out explicitly
**Plans**: TBD

### Phase 100: Professional & Editable Report Delivery
**Goal**: The exported PDF presents as a client-ready deliverable — professionally laid out with a cover page, clean section hierarchy, consistent typography, and no rendering defects — and the consultant can also export a DOCX that preserves sections and tables for final editing before client handoff
**Depends on**: Phase 98, Phase 99
**Requirements**: FMT-01, FMT-02, FMT-03
**Success Criteria** (what must be TRUE):
  1. The PDF opens with a branded cover page (including a configurable logo region) and contains clearly delineated sections (executive summary, findings, remediation roadmap, score breakdown) — a consultant can hand the file to a CISO without visual apology
  2. Tables and headings in the PDF render without text overflow, truncation, or broken pagination — every row is fully readable and no section boundary splits a table mid-row
  3. Running `quirk report --format docx` (or equivalent export path) produces a DOCX file that opens in Word and Google Docs with sections, headings, and tables intact — a consultant can insert a logo and edit narrative text without reconstructing the document structure
**Architecture note (for planner)**: The DOCX exporter must derive from the SAME report content model that drives CLI/HTML/PDF — the same `IntelligenceReport` / finding dict that Phase 98 establishes — so it inherits EXEC-04 and TRANS-03 consistency guarantees rather than being a hand-built parallel document. The PDF is the "as-scanned" immutable artifact; the DOCX is the "pre-delivery editable" artifact the consultant finalizes. Both are generated from one content pipeline, not two.
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 97. v5.1 Tech-Debt Cleanup | 4/4 | Complete    | 2026-05-23 |
| 98. Executive Narrative + Score Transparency | 0/3 | Planned | - |
| 99. Per-Finding Context + Code-Signing Expiry | 0/TBD | Not started | - |
| 100. Professional & Editable Report Delivery | 0/TBD | Not started | - |
