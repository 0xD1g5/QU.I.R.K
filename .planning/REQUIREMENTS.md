# Requirements: QU.I.R.K. — Milestone v5.23 Deliverable Experience

**Defined:** 2026-09-11
**Core Value:** Complete, defensible cryptographic inventory with CBOM deliverable and
quantum-readiness score — handed to a client in under two hours. This milestone makes the
deliverable itself — the report a consultant hands the client — customizable, credible in its
forward-looking framing, and narratively explorable.

**Research basis:** `.planning/research/SUMMARY.md` (committed `41af634c`) — STACK, FEATURES,
ARCHITECTURE, PITFALLS. Zero new runtime dependencies required for this scope.

## v1 Requirements

### Wave A Drain (TRIAGE — continues v5.20's TRIAGE numbering)

Gating correctness drain, sequenced first so scoring-adjacent defects don't compound with the
new score-lift math.

- [ ] **TRIAGE-10**: Fractional scores survive the trend/merge paths end-to-end —
      `quirk/intelligence/trends.py` / sensor `merge.py` int-coercion of score fields fixed
      (recorded in `188-05-SUMMARY.md` at the scoring-v2 boundary), with regression coverage
      proving a fractional score round-trips unchanged
- [ ] **TRIAGE-11**: A CI regression test exercises the connectors + advanced overlays
      **combined** on one scan submission (job YAML + effective-config preview both asserted) —
      the v5.22 milestone-audit deferred tech-debt item

### Report Branding & Templates (RPT — 999.105 Tier 1 + profiles + Tier 2 spike)

- [ ] **RPT-01**: Operator can set client branding (logo, client/engagement identity, cover
      details) in config, rendered consistently on every report surface that supports it
      (CLI/HTML+PDF/DOCX; CLI carries the identity fields it can honestly render)
- [ ] **RPT-02**: Operator can override report templates from a local template directory,
      rendered through a sandboxed Jinja2 environment (`SandboxedEnvironment`) with the existing
      autoescape discipline preserved on the same Environment instance — SSTI containment is a
      go/no-go gate inside this phase, not a follow-up
- [ ] **RPT-03**: Branding/template path fields are containment-guarded (path-traversal) and
      dashboard-excluded via a **named, tested guard** — not tribal-knowledge absence (the
      `assessment.logo_path` lesson, `schemas.py:991`)
- [ ] **RPT-04**: Operator can save and select named report profiles ("house styles") bundling
      branding + template settings for reuse across engagements
- [ ] **RPT-05**: Section-composition spike delivers a written go/no-go + honest sizing for
      999.105 Tier 2 — resolves how the zero-CRITICAL congruence guard (`writer.py:307,:927`)
      and the presence-based parity test suite would be redesigned; decision doc only, no
      implementation

### Score-Lift Roadmap Re-frame (LIFT — 999.101 + BACK-51)

- [ ] **LIFT-01**: Every remediation roadmap item carries a score-lift computed by real
      delta-scoring against `compute_readiness_score()` as a pure function over synthetic
      evidence — never a heuristic mapping
- [ ] **LIFT-02**: The aggregate projected score is its own independent rescore call — never a
      sum of per-item lifts (the 25-point subscore clamp in `_apply_weighted_impacts` makes
      lifts non-additive; a summed aggregate overstates)
- [ ] **LIFT-03**: Projected/simulated scores never persist into or feed any real score
      surface — machine-enforced by a new forward-projection firewall guard test
      (ADVISORY-02-style, mirroring `test_remediation_advisory_guard.py`'s pattern)
- [ ] **LIFT-04**: One roadmap categorization system feeds all surfaces — the
      `build_phased_roadmap()` / `categorize_waves()` duality (BACK-51) is unified so
      NOW/NEXT/LATER assignments agree across CLI/HTML/DOCX/dashboard for the same scan
- [ ] **LIFT-05**: Score-lift renders on the dashboard roadmap surface (including the
      `routes/scan.py`-side wiring it requires), consistent with the report surfaces

### Finding Storyline Drawer (STORY — 999.102, unblocked: 999.98 shipped v5.21 Phase 191)

- [ ] **STORY-01**: Operator can open a per-finding storyline drawer from the dashboard
      findings table, with narrative sourced from the existing Phase-99 catalogs
      (`ALGO_IMPACT_MAP` / `REMEDIATION_CATALOG`) — no forked fourth narrative generator
- [ ] **STORY-02**: The drawer shows the finding's score-lift attribution, consuming LIFT-01's
      per-item number (sequenced after the LIFT phase)

## v2 Requirements

Deferred, tracked in HORIZON.md's Open-Item Ledger.

### Reporting Engine

- **RPT-F-01**: 999.105 Tier 2 — section-composition profiles (executive-only / technical
  variants); gated on RPT-05's spike verdict
- **RPT-F-02**: 999.105 Tier 3 — full custom-template engine incl. DOCX templating
  (`docxtpl`); requires its own threat-model milestone (SSTI/RCE class, CVE-2025-27516
  precedent)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Tier 2 section-composition implementation | Spike-gated (RPT-05); breaks the congruence guard + 8 parity test files if done naively |
| Tier 3 full template engine / `docxtpl` | Operator-authored Jinja in-process is an RCE-class trust boundary; milestone-sized threat-model decision on its own |
| Dashboard-uploadable template dirs / logo paths | Path-traversal surface; local-CLI-config-only until a containment review (RPT-03 guards the exclusion) |
| Score-lift feeding the real score (either direction) | LIFT-03 firewall; the ADVISORY-01 precedent extended to forward projection |
| Heuristic score-lift estimates | The named anti-feature from FEATURES.md — "gimmicky roadmap" failure mode; real delta-scoring only |
| v5.24 UAT Coverage Drain scope | Committed as the NEXT milestone (HORIZON rationale log 2026-09-11), not folded in here |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TRIAGE-10 | — | Pending |
| TRIAGE-11 | — | Pending |
| RPT-01 | — | Pending |
| RPT-02 | — | Pending |
| RPT-03 | — | Pending |
| RPT-04 | — | Pending |
| RPT-05 | — | Pending |
| LIFT-01 | — | Pending |
| LIFT-02 | — | Pending |
| LIFT-03 | — | Pending |
| LIFT-04 | — | Pending |
| LIFT-05 | — | Pending |
| STORY-01 | — | Pending |
| STORY-02 | — | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 14 ⚠️ (expected — roadmap not yet created)

---
*Requirements defined: 2026-09-11*
*Last updated: 2026-09-11 after initial definition (milestone v5.23 open)*
