# Requirements: QU.I.R.K. — v5.2 Consulting-Grade Reporting

**Defined:** 2026-05-23
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

**Milestone framing:** v4.x–v5.1 built a deep, broad *detection* engine across six scanner families. v5.2 is the first milestone to own the *output layer* — the artifact the consultant hands the client. For a consulting tool the report IS the product; better detection only creates value if communicated defensibly. Anchor: the narrative executive report.

## v1 Requirements

Requirements for this milestone. Each maps to exactly one roadmap phase.

### Executive Narrative Report (EXEC)

- [ ] **EXEC-01**: Reader sees an executive summary that opens with a plain-language readiness narrative (overall posture + what it means) before any finding tables
- [ ] **EXEC-02**: Executive summary surfaces the top prioritized risks framed by business impact, not as raw finding rows
- [ ] **EXEC-03**: Report includes a prioritized remediation roadmap section — ordered actions with rationale and relative effort/impact
- [ ] **EXEC-04**: The executive narrative renders with consistent content across CLI markdown, HTML, and PDF (format-appropriate, same story)

### Per-Finding Context (CTX)

- [ ] **CTX-01**: Each finding carries a plain-language quantum-risk "so what" explanation (why it matters for PQC)
- [ ] **CTX-02**: Each finding carries actionable remediation guidance specific to the detected weakness
- [ ] **CTX-03**: Code-signing certificate expiry (not_after / expired) is surfaced as a finding [WR-05 carry-over from v5.1]

### Score Transparency & Consistency (TRANS)

- [ ] **TRANS-01**: Reports show the six-pillar subscore decomposition against budget that feeds the overall readiness number
- [ ] **TRANS-02**: Reports explain how the overall score is computed (subscore weighting + ÷1.5 rollup) so the number is defensible to a client
- [ ] **TRANS-03**: The executive summary's headline score and severity language are consistent with the detailed findings tables — no contradiction [999.82]

### Professional Formatting & Editable Delivery (FMT)

- [ ] **FMT-01**: The PDF report uses a professional client-ready layout (cover with a configurable logo region, sectioning, consistent typography/branding)
- [ ] **FMT-02**: Report tables/headings render cleanly in PDF with no overflow, truncation, or broken pagination
- [ ] **FMT-03**: The report can be exported as an editable document (DOCX, opens in Word/Google Docs) that preserves sections and tables, so a consultant can insert a logo and edit content before producing the final client deliverable

### v5.1 Tech-Debt Cleanup (TD)

- [x] **TD-01**: Credential env-var contract + CredentialContext per-call str-copy / `_append_query_param` overwrite behaviors corrected [WR-02/04/06]
- [x] **TD-02**: The 5xx cascade counter correctly trips on connection-exception failures (timeout-only servers no longer escape the cascade pause) [WR-03]

## Future Requirements

Deferred beyond v5.2. Tracked but not in this roadmap.

### Reporting (future)

- **REPORT-F1**: Customizable report templates / white-labeling per consulting firm
- **REPORT-F2**: Diff/delta narrative report comparing two scan sessions in prose
- **REPORT-F3**: Per-asset / per-segment report sectioning for large multi-target engagements

## Out of Scope

Explicitly excluded for v5.2 to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New scanner / detection capability | v5.2 is the output layer; detection surface is frozen for this milestone |
| Interactive / live dashboard report builder | Reports are generated artifacts (CLI/HTML/PDF); interactive authoring is a separate concern |
| Multi-tenant / hosted report storage | SaaS milestone (deferred to v5.4+, gated on adoption signal) |
| Net-new branding/design system | Reuse existing visual identity; v5.2 polish is layout/typography, not a rebrand |

## Traceability

Which phases cover which requirements. Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXEC-01 | Phase 98 | Pending |
| EXEC-02 | Phase 98 | Pending |
| EXEC-03 | Phase 98 | Pending |
| EXEC-04 | Phase 98 | Pending |
| CTX-01 | Phase 99 | Pending |
| CTX-02 | Phase 99 | Pending |
| CTX-03 | Phase 99 | Pending |
| TRANS-01 | Phase 98 | Pending |
| TRANS-02 | Phase 98 | Pending |
| TRANS-03 | Phase 98 | Pending |
| FMT-01 | Phase 100 | Pending |
| FMT-02 | Phase 100 | Pending |
| FMT-03 | Phase 100 | Pending |
| TD-01 | Phase 97 | Complete |
| TD-02 | Phase 97 | Complete |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-23*
*Last updated: 2026-05-23 — FMT-03 (DOCX editable export) added; FMT-01 extended to include configurable logo region; coverage bumped to 15/15*
