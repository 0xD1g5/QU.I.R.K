# Phase 99: Per-Finding Context + Code-Signing Expiry - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the finding list into an advisory document. Every finding in the report
must carry (1) a plain-language quantum-risk "so what" explanation (CTX-01) and
(2) actionable remediation guidance specific to the detected weakness, not
generic PQC boilerplate (CTX-02). Separately, surface code-signing certificate
expiry (`not_after` / expired) as a first-class finding (CTX-03 — the WR-05
carry-over from v5.1, where expiry was computed but never propagated to a
finding).

**In scope:** per-finding risk context + remediation enrichment across all
finding-producing paths; code-signing cert expiry classification → finding;
rendering the new risk context across CLI markdown, HTML, and PDF.

**Out of scope:** new scanner detection capabilities; DOCX export (FMT-03);
PDF layout/branding (FMT-01/02); the executive-narrative sections (shipped in
Phase 98). This phase enriches the *per-finding* layer only.

</domain>

<decisions>
## Implementation Decisions

### CTX-01 — Quantum-risk "so what" source & placement
- **D-01:** Extend the existing `ALGO_IMPACT_MAP` (crypto-class → risk
  label/impact sentence) in `quirk/reports/content_model.py` as the single
  source of per-finding quantum-risk context. Do NOT build a parallel
  finding-type catalog for risk text — reuse the crypto-class keying already
  proven for the exec summary's top-risks (Phase 98 D-02).
- **D-02:** Attach the "so what" to each finding as a **dedicated field**
  (e.g. `quantum_risk`) rather than folding it into the existing `description`.
  Keep technical detail (`description`) and risk framing (`quantum_risk`)
  separate so the renderer can present them distinctly.

### CTX-01 — Render parity
- **D-03:** Render the new quantum-risk field across **all three** report
  surfaces — CLI markdown (`technical.py` findings table), HTML
  (`html_renderer.py` findings section), and PDF. This honors the EXEC-04
  same-story-across-formats contract.

### CTX-02 — Remediation organization
- **D-04:** Introduce a **centralized remediation catalog** keyed by finding
  type / crypto-class (mirroring the `ALGO_IMPACT_MAP` pattern) as the single
  source of remediation text. `_build_finding` call sites reference the catalog
  instead of carrying ad-hoc inline strings. Goal: auditable, consistent,
  specific-to-the-weakness remediation.
- **D-05:** Remediation copy must be specific to the detected weakness — NOT
  generic PQC boilerplate. Re-examine the auto-appended `NIST_IR_8547_DEPRECATION`
  sentence (`_build_finding`, applied to every `quantum_vulnerable=True` finding)
  so the boilerplate does not crowd out or duplicate the weakness-specific
  guidance.

### Coverage scope
- **D-06:** Enrich **all finding-producing paths**, not just those flowing
  through `_build_finding`. Findings from codesign, email, and broker scanners
  (and any DB-sourced findings) must not render with empty or thin context /
  remediation. No finding should reach the report without a quantum-risk "so
  what" and a specific remediation.

### CTX-03 — Code-signing expiry classification
- **D-07:** Add expiry classification to `_classify_codesign_severity` in
  `quirk/scanner/codesign_scanner.py` (today it checks only weak crypto:
  SHA-1 / RSA<2048 / EC<256 and returns `None` for "SAFE" certs, dropping the
  finding). Severity mapping: **expired → HIGH; within 90 days of `not_after`
  → MEDIUM (approaching expiry).**
- **D-08:** Expiry is an **independent reason** that can stack with existing
  weak-crypto reasons. A SAFE-crypto-but-expired cert must now emit a finding
  (it previously returned `None` and was silently dropped).
- **D-09:** Apply expiry classification to **both** codesign source paths —
  `scan_codesign_from_ldap` and `scan_codesign_from_tls_endpoints`. The TLS
  path must read `cert_not_after` reliably; the planner/researcher should
  confirm `not_after` availability on that path.

### Copywriting discipline
- **D-10:** Lock all new author-facing copy (per-finding quantum-risk
  sentences for each crypto class + remediation catalog entries + code-signing
  expiry finding title/description/remediation) in a **UI-SPEC Copywriting
  Contract first**, before planning — mirroring Phase 98. Run `/gsd-ui-phase 99`
  to author and lock the exact strings, then plan against the locked contract.

### Claude's Discretion
- Exact field name for the quantum-risk "so what" (`quantum_risk` is a
  suggestion).
- Catalog data structure (dict-of-tuples vs dataclass) — follow the
  `ALGO_IMPACT_MAP` analog and `PATTERNS.md`.
- How the new field threads through `_dedupe_findings` keying (note: the
  existing dedupe already excludes `recommendation` from the dedup key so
  remediation-text edits don't fragment clusters — preserve that property for
  the new field).
- Markdown/HTML/PDF column-vs-block presentation of the risk text, within the
  locked copy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` §"Per-Finding Context (CTX)" — CTX-01/02/03 wording.
- `.planning/ROADMAP.md` §"Phase 99" — goal + success criteria.

### Finding construction & enrichment
- `quirk/engine/findings_evaluator.py` — `_build_finding` chokepoint (mandatory
  `description` + `recommendation`, `NIST_IR_8547_DEPRECATION` append, compliance
  attach); `_dedupe_findings` keying; `evaluate_*_endpoints` finding sources.
- `quirk/reports/content_model.py` — `ALGO_IMPACT_MAP` (extend per D-01),
  `_classify_finding`, `build_exec_content`; UI-SPEC Copywriting Contract precedent.

### Code-signing expiry (CTX-03 / WR-05)
- `quirk/scanner/codesign_scanner.py` — `_classify_codesign_severity` (add expiry,
  D-07/08), `scan_codesign_from_ldap`, `scan_codesign_from_tls_endpoints`,
  `_parse_codesign_cert` (computes `not_after` / `expired`).
- `.planning/v5.1-MILESTONE-AUDIT.md` (WR-05 entry) and
  `.planning/PROJECT.md` §160 — WR-05 origin and intent.

### Renderers (D-03 parity)
- `quirk/reports/technical.py` — markdown findings table (Description /
  Recommendation columns already present).
- `quirk/reports/html_renderer.py` + `quirk/reports/templates/` — HTML/PDF findings.

### Copywriting precedent
- `.planning/phases/98-executive-narrative-score-transparency/98-UI-SPEC.md` —
  Copywriting Contract pattern to mirror for Phase 99 (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ALGO_IMPACT_MAP` (`content_model.py`): crypto-class → (risk_label,
  impact_sentence). Extend as the single source for per-finding quantum-risk
  context (D-01). `_classify_finding` already maps a finding → crypto-class key.
- `_build_finding` (`findings_evaluator.py`): single chokepoint already
  enforcing non-empty `description` + `recommendation`. Natural injection point
  for catalog-sourced remediation (D-04) and the new `quantum_risk` field.
- `_classify_codesign_severity` (`codesign_scanner.py`): returns
  `(severity, reasons)`; reasons list is the place to append an expiry reason.

### Established Patterns
- Findings are plain `Dict[str, Any]` (not a dataclass). New fields are dict
  keys — renderers read via `f.get(...)`.
- Static copy maps keyed by crypto class, with copy locked in a UI-SPEC
  Copywriting Contract (Phase 98 discipline).
- `_dedupe_findings` deliberately excludes `recommendation` from the dedup key
  so remediation edits don't fragment clusters — apply the same care to any
  new free-text field.

### Integration Points
- Codesign scanners emit `CryptoEndpoint`s (with `severity`, `cert_not_after`),
  which are later evaluated into findings — confirm where codesign endpoints
  become report findings so expiry severity propagates end-to-end.
- Renderer trio (`technical.py` markdown, `html_renderer.py` + templates) is
  where the new `quantum_risk` field surfaces for D-03 parity.

</code_context>

<specifics>
## Specific Ideas

- Mirror Phase 98 exactly on copy discipline: author a 99-UI-SPEC Copywriting
  Contract, then plan against locked strings (D-10).
- Severity thresholds are concrete: expired = HIGH, ≤90 days to `not_after` =
  MEDIUM (D-07).
- "No finding renders with empty/generic context or remediation" is the
  acceptance bar for coverage (D-06).

</specifics>

<deferred>
## Deferred Ideas

- DOCX editable export (FMT-03), PDF branding/layout (FMT-01/02) — separate
  formatting phases in v5.2.
- Net-new scanner detection — out of scope; this phase is report-content only.

None beyond the above — discussion stayed within phase scope.

</deferred>

---

*Phase: 99-per-finding-context-code-signing-expiry*
*Context gathered: 2026-05-24*
