---
phase: 48-rich-finding-context
type: context
status: active
source: /gsd-discuss-phase 48
updated: 2026-05-04
milestone: v4.6 Enterprise Readiness
requirements: [CONTEXT-01, CONTEXT-02, CONTEXT-03, CONTEXT-04]
---

# Phase 48 — Rich Finding Context — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Every finding emitted by QUIRK carries a non-empty plain-English `description`
of the cryptographic risk and, where quantum-relevant, a `recommendation` that
names the appropriate FIPS 203/204/205 algorithm using FIPS designations only —
plus a NIST IR 8547 deprecation deadline (RSA/ECC deprecated 2030, disallowed
2035). All "Kyber"/"Dilithium"/"when standards are adopted" terminology is
purged from QUIRK source files and project docs, and a CI grep gate fails the
build if any of those strings reappear in the two locked source paths.

**Key insight:** This is mostly a **schema + content + enforcement problem**,
not greenfield. Findings today are dicts with only `severity`, `host`, `port`,
`title`, `recommendation` constructed in ~14 places inside
`quirk/engine/risk_engine.py:343–489`. CONTEXT-01 requires adding a new
`description` key — every producer must populate it, every consumer (HTML/PDF
renderer, dashboard DTO, JSON exports) must render it. Real stale-terminology
hits in source are narrow: `risk_engine.py:447`, `docs/report-interpretation.md`,
`docs/quirk-overview.md`. Everything under `quirk-output/` is generated and
self-heals after a fresh scan.

**In scope (from ROADMAP.md):**
- `description` field added to every finding (1–3 sentences plain English)
- `recommendation` text rewritten to use FIPS designations only
- NIST IR 8547 deprecation deadline cited on every quantum-vulnerable finding
- Stale PQC terminology purged from QUIRK source + project docs
- CI grep gate over the two locked source files
- Renderer (HTML/PDF/dashboard DTO/JSON exports) updated to display `description`
- Docs sync (`docs/report-interpretation.md`, `docs/quirk-overview.md`) +
  Obsidian phase note + UAT-SERIES.md update per CLAUDE.md mandate

**Out of scope:**
- `see_also` URL field — deferred to v4.7 (CONTEXT-05)
- Compliance framework mappings — Phase 49
- Structured `deprecation: {deprecated_year, disallowed_year}` field — D-05
  rejected for v4.6
- Purge of `quirk-output/` artifacts — regenerate on next scan
- Purge of `.planning/` historical record — preserves project history

</domain>

<decisions>
## Implementation Decisions

### Finding schema shape

- **D-01 — Add `description` field, keep `recommendation`.** Findings gain a
  new `description` key (1–3 sentences explaining the cryptographic risk in
  plain English) alongside the existing `title` and `recommendation` keys.
  `recommendation` is **not** renamed to `remediation` — semantics are clean
  enough as-is and renaming ripples through every consumer.

  *Why:* Matches success criterion #1's wording verbatim ("non-empty
  `description` field"). Clean separation: risk explanation vs. fix
  guidance. Minimum-viable contract change.

  *How to apply:* Researcher should map every consumer of finding dicts
  (HTML/PDF renderer, dashboard DTO at `quirk/dashboard/api/schemas.py`,
  JSON export path). Planner splits into one task per consumer plus one
  task for the producer-side helper.

- **D-02 — Helper builder + unit test enforces non-emptiness.** Centralize
  finding construction through a `_build_finding(...)` helper in
  `quirk/engine/risk_engine.py` that requires `description` as a required
  positional arg. Add a unit test that runs the engine over a fixture set
  and asserts every emitted finding has a non-empty `description` (and a
  non-empty `recommendation` for quantum-vulnerable findings).

  *Why:* Enforcement at construction time is unmissable. A helper can also
  inject the canonical NIST IR 8547 deprecation phrase (D-06) automatically
  for quantum-vulnerable findings. No new model classes or runtime
  validators required.

  *How to apply:* Helper signature should require `description` + `title`
  + `severity` + `host` + `port` + `recommendation` and accept an optional
  `quantum_vulnerable: bool` flag that triggers the NIST IR 8547
  constant injection.

### PQC terminology purge

- **D-03 — Purge scope: source code + project docs.** Targets:
  `quirk/**/*.py`, `docs/**/*.md`, and any HTML/Jinja templates under
  `quirk/` (none expected, but verify). Excludes `quirk-output/`
  (artifacts regenerate) and `.planning/` (historical record). Tests
  + chaos lab `expected_results_*.md` files are also out of scope —
  test fixtures intentionally exercise legacy terminology semantics.

  *Why:* Fixes the truth at the source; artifacts self-heal on next scan.
  Strict-interpretation alternative would leave `docs/quirk-overview.md`
  stale (client-facing drift). Broader alternative pulls in test fixtures
  unnecessarily.

  *How to apply:* Researcher enumerates source-tree occurrences (current
  count: 1 in `risk_engine.py:447`, plus the two doc files). Planner adds
  a single task that does the substitution per D-04 across the in-scope set.

- **D-04 — Replacement string: FIPS standard number always.** Canonical
  forms:
  - Key exchange: `ML-KEM (FIPS 203)`
  - Signatures: `ML-DSA (FIPS 204)` or `SLH-DSA (FIPS 205)` as appropriate
  - **Never:** "Kyber", "Dilithium", "CRYSTALS-Kyber", "CRYSTALS-Dilithium",
    "when standards are adopted"

  *Why:* Maximum regulatory traceability. The literal "FIPS 203/204/205"
  strings on disk become a stable anchor for Phase 49 (Compliance Mapping).
  Pentest deliverables read more authoritatively to compliance auditors.

  *How to apply:* Use these strings consistently across `risk_engine.py`,
  `docs/report-interpretation.md`, `docs/quirk-overview.md`, and any
  rendered finding text.

### Deprecation deadline format

- **D-05 — Prose embedded in `description`/`recommendation` (no new
  field).** NIST IR 8547 deprecation deadlines are written into existing
  fields as natural-language prose. No `deprecation` structured field is
  added in v4.6.

  *Why:* Smallest diff that still satisfies success criterion #3. No
  new model fields, no consumer updates beyond the text itself.
  Structured representation can be added in a future phase without
  breaking the v4.6 contract if filtering/sorting needs emerge.

- **D-06 — Single canonical deprecation phrase via constant.** Define
  `NIST_IR_8547_DEPRECATION` as a module-level constant in
  `quirk/engine/risk_engine.py`:

  ```python
  NIST_IR_8547_DEPRECATION = (
      "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and "
      "disallowed after 2035."
  )
  ```

  The `_build_finding` helper appends this constant to the
  `recommendation` (or `description`, planner's choice — see below) of
  every finding flagged `quantum_vulnerable=True`.

  *Why:* CI grep gate has one canonical string to check; updating the
  phrase when NIST revises requires touching exactly one symbol; per-
  finding drift impossible.

  *How to apply:* Planner decides whether the constant is appended to
  `description` or `recommendation` — recommend `recommendation`
  (because the deadline is part of the migration story, not the risk
  description). Researcher should verify no consumer truncates
  `recommendation` strings.

### CI grep gate

- **D-07 — Gate scope: two named files (resolved paths).** The CI grep
  gate scans exactly:
  - `quirk/engine/risk_engine.py`
  - `quirk/dashboard/api/routes/scan.py`  *(real path; ROADMAP says
    `routes/scan.py` — resolve to the dashboard API location)*

  *Why:* Matches success criterion #4 verbatim with the real path
  resolved. Tight, predictable, no false positives on legitimate new
  code under `quirk/**`. The narrow gate is sufficient because
  `_build_finding` (D-02) is the chokepoint that prevents drift in
  `risk_engine.py`, and `routes/scan.py` is small enough to audit.

- **D-08 — Gate rigor: case-insensitive substring, no exemptions.**
  Pattern (literal, no word boundaries):

  ```bash
  grep -i -E 'kyber|dilithium|when standards are adopted' \
    quirk/engine/risk_engine.py \
    quirk/dashboard/api/routes/scan.py
  ```

  Any match — including in comments, docstrings, or string literals —
  fails the build.

  *Why:* Simplest, most predictable, trivially auditable. No AST-aware
  tooling required. Because the gate scope is narrow (D-07), the lack
  of exemptions doesn't cause false positives in legitimate
  educational/historical comments — those live in tests and docs which
  are not gated.

  *How to apply:* Add a `make` or `pytest` target invoked by CI that
  exits non-zero on any match. Place near existing CI checks (planner
  to identify location).

### Claude's Discretion

- Exact prose wording of `description` strings (per finding type) — content
  decision; user did not specify per-finding language.
- Whether the NIST IR 8547 constant is appended to `description` or
  `recommendation` (D-06) — recommendation made above; planner finalizes.
- File-system layout for the CI gate (`scripts/ci_pqc_terminology_gate.sh`
  vs. inline `Makefile` target vs. pytest test) — planner picks based on
  existing CI conventions in the repo.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 48 (lines 947–959) — phase goal + success criteria
- `.planning/REQUIREMENTS.md` lines 30–33, 78, 125–128, 142 — CONTEXT-01..04
  active + CONTEXT-05 deferred-to-v4.7
- `CLAUDE.md` — "Mandatory Phase Completion Steps" + Obsidian sync rules

### External standards (cite, do not modify)
- **NIST FIPS 203** — Module-Lattice-Based Key-Encapsulation Mechanism
  Standard (ML-KEM). Source: <https://csrc.nist.gov/pubs/fips/203/final>
- **NIST FIPS 204** — Module-Lattice-Based Digital Signature Standard
  (ML-DSA). Source: <https://csrc.nist.gov/pubs/fips/204/final>
- **NIST FIPS 205** — Stateless Hash-Based Digital Signature Standard
  (SLH-DSA). Source: <https://csrc.nist.gov/pubs/fips/205/final>
- **NIST IR 8547** — Transition to Post-Quantum Cryptographic Standards
  (deprecation 2030 / disallowed 2035). Source:
  <https://csrc.nist.gov/pubs/ir/8547/ipd>

### Code under modification
- `quirk/engine/risk_engine.py` (629 lines) — finding construction site;
  lines 343–489 contain all five TLS/SSH/CONTAINER finding branches.
  Stale terminology at line 447. Add `_build_finding` helper +
  `NIST_IR_8547_DEPRECATION` constant here.
- `quirk/dashboard/api/routes/scan.py` — second file gated by CI grep.
  Verify it constructs no findings directly; should be free of stale
  terminology already.
- `quirk/dashboard/api/schemas.py` — dashboard DTO; add `description`
  field to finding schema.
- HTML/PDF renderer (researcher to locate — likely
  `quirk/reports/` or `quirk/renderer/`) — display `description` above
  `recommendation` per D-01.
- JSON export path (researcher to locate) — pass `description` through.

### Documentation
- `docs/report-interpretation.md` — contains stale "Kyber"/"Dilithium";
  rewrite per D-04. Sync to Obsidian per CLAUDE.md.
- `docs/quirk-overview.md` — contains stale terminology; rewrite per D-04.
- `docs/UAT-SERIES.md` — update per CLAUDE.md mandatory step #2 (new test
  cases for `description` field non-empty + FIPS terminology).

### Prior phase context
- `.planning/phases/46-tls-finding-gaps/46-CONTEXT.md` — TLS finding
  branches and risk engine layout; recently expanded.
- `.planning/phases/45-install-day-ux/45-CONTEXT.md` — install-day UX
  decisions (no overlap with Phase 48 content but locks the surrounding
  v4.6 patterns).

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONVENTIONS.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **Risk engine finding-dict pattern** (`risk_engine.py:343–489`): every
  TLS/SSH/CONTAINER finding is a `dict` with the same five keys. The
  centralized construction site is the right place for the
  `_build_finding` helper — no other module emits findings.
- **`_evaluate_container_package`** (`risk_engine.py:486`): existing helper
  function pattern; emulate its signature/return-type style for
  `_build_finding`.
- **Dashboard DTO** (`quirk/dashboard/api/schemas.py`): centralized
  Pydantic-ish schemas — adding `description: str` here propagates to
  every consumer without a per-route change.

### Established Patterns

- **Findings are dicts, not classes**: convention through v4.6. D-01
  preserves this. Promotion to typed model can happen later without
  blocking this phase.
- **Wiring problems > greenfield**: Phase 46's central insight — the
  scaffolding usually exists; the bug is in field assignment or
  consumer wiring. Phase 48 follows the same shape: `description` field
  is one schema addition + N consumer updates, not a new architecture.
- **Mandatory docs + Obsidian sync per phase** (CLAUDE.md): every phase
  ends with `docs/UAT-SERIES.md` update, Obsidian phase note, and
  `_QUIRK-Hub.md` link refresh. Plan must include explicit tasks.

### Integration Points

- **Risk engine → renderer:** finding dicts flow into HTML/PDF rendering.
  New `description` key must be picked up by the renderer template.
- **Risk engine → dashboard DTO:** dashboard reads finding dicts from
  the scan result and serializes via `schemas.py`. Add field there.
- **Risk engine → JSON export:** export path serializes finding dicts
  directly; once `description` is in the dict it flows through, but
  verify no whitelist/projection drops it.
- **CI gate → Makefile/pytest:** new gate target slots into existing CI
  conventions. Planner identifies hook point.

</code_context>

<specifics>
## Specific Ideas

- Single `NIST_IR_8547_DEPRECATION` constant — exact text proposed:
  > "Per NIST IR 8547, RSA and ECC are deprecated after 2030 and
  > disallowed after 2035."
  Planner may polish wording but the structure (one sentence, cites
  NIST IR 8547 by name, both years present) is locked.
- Phase 49 (Compliance Mapping) will key off the literal `FIPS 203`,
  `FIPS 204`, `FIPS 205` substrings written here. Don't break the
  consistency — D-04 is contractually visible to the next phase.

</specifics>

<deferred>
## Deferred Ideas

- **Structured `deprecation: {deprecated_year, disallowed_year, source}`
  field** — rejected for v4.6 (D-05 took prose route). Revisit if a
  filter/sort UX need emerges (e.g., dashboard "show findings disallowed
  within 5 years").
- **Word-boundary regex CI gate** — rejected for v4.6 (D-08 took
  substring route). Revisit only if false positives appear in practice.
- **Comment/docstring exemption for educational PQC history** — rejected
  for v4.6. Revisit if educational comments become valuable inside the
  two gated files (none today).
- **Purge of test fixtures + chaos lab `expected_results_*.md`** —
  intentionally out of scope; fixtures may exercise legacy semantics on
  purpose. Revisit if/when CI flags drift.
- **`see_also` URL field per finding** — already deferred to v4.7
  (CONTEXT-05 in REQUIREMENTS.md).

</deferred>

---

*Phase: 48-rich-finding-context*
*Context gathered: 2026-05-04*
