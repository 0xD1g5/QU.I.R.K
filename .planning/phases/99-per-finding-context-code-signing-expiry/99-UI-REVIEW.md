---
phase: 99
slug: per-finding-context-code-signing-expiry
audited: 2026-05-24
baseline: 99-UI-SPEC.md (locked, approved)
screenshots: not captured (no dev server; static HTML report template — code-only audit)
advisory: true
blocking: false
---

# Phase 99 — UI Review

**Audited:** 2026-05-24
**Baseline:** 99-UI-SPEC.md (locked design contract)
**Screenshots:** Not captured — no dev server running; audit is static-source analysis of HTML template and Python renderer against the locked contract. Visual render is separately queued as human UAT (UAT-99-02).
**Scope:** `quirk/reports/templates/report.html.j2` + `quirk/reports/technical.py`

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All locked strings match spec verbatim; fallback copy correct on both surfaces |
| 2. Visuals | 4/4 | Column placement, block hierarchy, and conditional rendering match spec intent exactly |
| 3. Color | 4/4 | No new color values introduced; CSS variables used exclusively; accent reserved to label only |
| 4. Typography | 4/4 | No new sizes or weights introduced; 13px/12px reuse confirmed; spec contract met |
| 5. Spacing | 3/4 | Implementation correct per CSS Additions Contract (margin-top: 4px); minor spec self-inconsistency noted |
| 6. Experience Design | 4/4 | XSS mitigations present on all 3 quantum_risk render sites; fallback covers absent field on CLI and All Findings; md_cell() escaping applied |

**Overall: 23/24**

---

## Top 3 Priority Fixes

1. **Spec self-inconsistency — Spacing section vs CSS Additions Contract** — No user impact (implementation is correct), but the Spacing narrative table (UI-SPEC.md line 67) documents `.quantum-risk-block` as `padding: 4px 0 0` while the authoritative CSS Additions Contract block (line 247) specifies `margin-top: 4px`. The implementation correctly follows the CSS code block. Fix: update the Spacing narrative table entry to read `margin-top: 4px` for consistency, so the spec is internally coherent before Phase 100 inherits it.

2. **Top Findings quantum_risk block renders no fallback when field absent** — Minimal user impact (Phase 99 guarantees all findings carry `quantum_risk` via `_build_finding`), but the spec's Interaction Contract states "If quantum_risk is absent or empty, the cell renders the fallback copy" without scoping that statement exclusively to the All Findings table. The Top Findings implementation gates on field presence and silently omits the block if absent. This is defensible (the spec template fragment shows the `{% if %}` gate) but creates a silent gap for any legacy finding object that predates Phase 99 enrichment. Advisory fix: add `else` fallback to the Top Findings quantum_risk block, or clarify in the spec that Top Findings intentionally omits the fallback for narrow-table readability.

3. **Pre-existing: `.score-label` font-size is 11px in template (line 74) vs 12px in the Typography scale table** — No Phase 99 regression; this discrepancy predates Phase 99 and lives in the inherited locked scale. Noted here as a minor inherited inconsistency for the Phase 100 PDF branding phase to resolve.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

All locked copy strings verified:

- **Column header:** `<th>Quantum Risk</th>` — exact match to spec §CLI Markdown Findings Table ("Quantum Risk") and §Interaction Contract. Present at `report.html.j2:359` and `technical.py:122`.
- **Inline label:** `"Quantum Risk:"` — rendered via `.quantum-risk-label` span in both the Top Findings block (`report.html.j2:305`) and All Findings cell (`report.html.j2:370`). Matches spec §HTML/CSS Additions Contract template fragments verbatim.
- **Fallback copy:** Template Jinja2 variable at `report.html.j2:357` sets `FALLBACK_QR = "This cryptographic weakness reduces the security margin against quantum-capable adversaries. Migrate to NIST-approved post-quantum algorithms per NIST IR 8547."` — exact match to spec §Copywriting Contract default fallback string.
- **CLI fallback:** `technical.py:13` re-exports `FALLBACK_QUANTUM_RISK` from `content_model.py` as `FALLBACK_QR`; applied at `technical.py:132`. Single source of truth pattern maintained.
- **Empty state:** `"No findings recorded for this scan."` preserved verbatim at `report.html.j2:376` with `color:var(--text-muted)` — matches spec §Empty/Error States.
- No generic labels ("Submit", "OK", "Click Here") present in Phase 99 additions.

WARNING (minor): The spec §Interaction Contract says fallback applies when quantum_risk is "absent or empty" without explicitly scoping this to All Findings only. The Top Findings implementation at `report.html.j2:305` uses `{% if f.get('quantum_risk') %}` with no else branch — meaning fallback text is not shown in Top Findings when the field is absent. This is consistent with the spec's HTML/CSS Additions Contract template fragment (which also shows the `{% if %}` gate) but creates a silent gap for pre-Phase-99 finding objects. Not a defect against the spec code block; flagged as advisory.

### Pillar 2: Visuals (4/4)

- **All Findings table:** 7 columns confirmed at `report.html.j2:359`. Column order: Severity, Title, Host, Port, Description, Recommendation, Quantum Risk — places Quantum Risk as 7th column after Recommendation, matching spec §Interaction Contract primary specification.
- **Top Findings table:** Remains 4 columns (`report.html.j2:294`). Quantum Risk rendered as `.quantum-risk-block` div inside the Description `<td>`, below truncated description text — matching spec §Interaction Contract ("Do NOT add a 5th column... render quantum_risk as a .quantum-risk-block sub-element").
- **Label prefix pattern:** `.quantum-risk-label` span precedes prose text in both surfaces — provides visual anchor and differentiates the risk field from surrounding content without adding a new color.
- **Conditional gating:** Top Findings block only renders when `f.get('quantum_risk')` is truthy — existing findings without the field are not visually disrupted. Correct per spec comment at `report.html.j2:303`.
- **No JavaScript added** — Phase 99 additions are fully static HTML/CSS, consistent with the air-gapped deployment constraint.

### Pillar 3: Color (4/4)

No new color values introduced by Phase 99. All Phase 99 additions use existing CSS variables exclusively:

- `.quantum-risk-block`: `color: var(--text-muted)` (#8888aa) — matches spec color role "Quantum Risk cell prose: --text-muted".
- `.quantum-risk-label`: `color: var(--accent)` (#3b9dff) — matches spec "Accent reserved for: .quantum-risk-label inline tag text only."
- No hardcoded hex values in Phase 99 CSS additions confirmed (grep found no new hex literals beyond the pre-existing `:root` palette).
- Accent discipline maintained: `.quantum-risk-label` is the only Phase 99 element using `--accent`. No accent applied to block container, prose text, or borders.
- Severity badge coloring for code-signing expiry findings uses pre-existing `--high` / `--medium` via the existing `.sev-cell` class — no new severity colors added.

### Pillar 4: Typography (4/4)

Spec contract: "Phase 99 adds zero new font sizes and zero new font weights."

Confirmed:
- `.quantum-risk-block`: `font-size: 13px` — reuses existing table cell size. No new size.
- `.quantum-risk-label`: `font-size: 12px` — reuses existing label/meta size. No new size.
- No `font-weight` property in either Phase 99 CSS rule. Pre-existing font-weight lines (900, bold, 600) are all inherited from Phase 98 and earlier.
- `letter-spacing: 0.06em` on `.quantum-risk-label` matches spec exactly. This is a pre-existing differentiation strategy (same pattern as `.priority-label` at `report.html.j2:168`).

Note (pre-existing, not Phase 99): `.score-label` uses `font-size: 11px` (`report.html.j2:74`) while the spec Typography scale table lists 12px for the label/meta role. This 1px discrepancy predates Phase 99 and is inherited from the locked scale. Not attributable to Phase 99 work.

### Pillar 5: Spacing (3/4)

**Finding: minor internal spec inconsistency, not an implementation defect.**

The UI-SPEC.md §Spacing Scale "Phase 99 net-new spacing" section (line 67) documents:
```
.quantum-risk-block: padding: 4px 0 0 (top gap from description only; border-left provides visual separation)
```

The authoritative §HTML/CSS Additions Contract code block (line 247) specifies:
```css
.quantum-risk-block {
  margin-top: 4px;
  ...
}
```

The implementation at `report.html.j2:173` uses `margin-top: 4px`, matching the CSS Additions Contract (the executor's authoritative source). The implementation is correct. However, the two parts of the spec disagree: the narrative describes `padding` while the code block specifies `margin`. These are not visually equivalent when background color or border is applied to the block — `padding` would push content inside a colored box, `margin` separates the box from the element above it. Since `.quantum-risk-block` has no background color, the visible result is identical in this specific case, but the spec property name is wrong in the narrative section.

**Score rationale:** Implementation passes against the authoritative CSS contract; score deducted one point to flag the spec inconsistency which will need cleanup before Phase 100 inherits the spacing documentation.

All other spacing values match the inherited scale:
- `margin-right: 4px` on `.quantum-risk-label` — matches spec exactly.
- No arbitrary CSS values (no `[Npx]` Tailwind or inline `style=` attributes in Phase 99 additions).
- Inherited pre-existing exceptions (`56px` section margin, `40px` body padding) unchanged.

### Pillar 6: Experience Design (4/4)

**XSS mitigation (T-99-06):** All 3 quantum_risk render sites in `report.html.j2` pass through `| sanitize`:
- `report.html.j2:305` — Top Findings block
- `report.html.j2:370` — All Findings cell
- (Comment at line 356 confirms the FALLBACK_QR set variable is static template content, not user-derived — no sanitize needed there.)

Count confirmed: `grep -Ec 'quantum_risk[^|]*\| sanitize' report.html.j2` → 2 live render sites (both quantum_risk field reads). The third count in SUMMARY.md includes the comment line; the two functional occurrences are both protected.

**Pipe-injection mitigation (T-99-07):** `md_cell(qr)` applied at `technical.py:134`. The `md_cell` wrapper escapes pipe characters that would break the markdown table structure.

**Fallback coverage:**
- CLI markdown: `(f.get("quantum_risk") or FALLBACK_QR)[:120]` at `technical.py:132` — covers absent and empty string.
- HTML All Findings: `f.get('quantum_risk', FALLBACK_QR)[:200]` at `report.html.j2:370` — covers absent field.
- HTML Top Findings: `{% if f.get('quantum_risk') %}` at `report.html.j2:305` — silently omits block when absent (no fallback shown). Acceptable per spec template fragment; see Copywriting finding above.

**No new interactive elements, CTAs, or destructive dialogs** — consistent with spec §Interaction Contract and §Empty/Error States.

**Single source of truth:** `FALLBACK_QR` in `technical.py` is a re-export of `content_model.FALLBACK_QUANTUM_RISK` — no hardcoded duplication of the fallback string across Python modules.

---

## Registry Safety

Registry audit: shadcn initialized (`components.json` present). UI-SPEC.md §Registry Safety table lists zero third-party registry blocks ("Third-party: none — not applicable"). Registry audit skipped — no third-party blocks to inspect.

---

## Files Audited

- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/99-per-finding-context-code-signing-expiry/99-UI-SPEC.md` — design contract (authoritative baseline)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/templates/report.html.j2` — HTML report template (489 lines)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/quirk/reports/technical.py` — CLI markdown renderer (139 lines)
- `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK/.planning/phases/99-per-finding-context-code-signing-expiry/99-03-SUMMARY.md` — plan execution record
