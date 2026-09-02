# Requirements: v5.18 — Migration Execution

**Milestone:** v5.18 Migration Execution
**Opened:** 2026-09-01
**Source:** HORIZON.md Candidate A, shaped by two research passes on 2026-09-01
(`.planning/research/v5.18-domain.md`, `.planning/research/v5.18-sizing.md`) rather than opened on
the unshaped sketch.

> [!important] The sketch's premise did not survive research
> HORIZON framed this as a 3x sizing question — "QUIRK feature or Jira/ServiceNow deepening?"
> Re-measurement found the ratio is **4-5x**, and more importantly that the two readings are **not
> two sizes of one feature**: ticketing readback delegates item identity to the client's tracker,
> which is the entire problem the native reading must solve. It yields **zero** reusable
> infrastructure. A third option the sketch never named — closure tracked against roadmap items,
> whose titles are a closed, non-interpolated, already-used-as-merge-key list — is the actual
> foundation, and is folded in below.

> [!warning] Two live defects were found while sizing, and both are prerequisites
> `compute_trend_report` keys its new/resolved delta on `(host, port, protocol, severity)` and
> filters `severity is not None` on both sides — but severity is populated only by the three cloud
> connectors. Verified against the live DB: **10,069 endpoint rows, 0 non-NULL severity**, so every
> scan reports **0 new / 0 resolved**. Separately, the ticketing fingerprint
> `SHA256(host:port::title)` — whose docstring claims stability across re-scans — interpolates 22
> titles, including `f"Certificate expiring in {days_to_expiry} day(s)"`, so **cert-expiry findings
> mint a fresh Jira ticket every day**. Neither is optional: remediation tracking is impossible on
> an identity key that decays daily.

---

## Standing constraint (applies to every requirement below)

- [ ] **ADVISORY-01**: Remediation/closure state is **advisory-only and never feeds the
  quantum-readiness score.** Decided at the milestone boundary (2026-09-01), not deferred to phase
  CONTEXT. `tests/test_cve_score_guard.py` machine-enforces this firewall and was extended by name
  in Phases 142/155/157; this milestone extends it again rather than amending it. A re-scan that
  genuinely finds an endpoint fixed already moves the score through normal detection — no second
  path into the score is created, so tracking state cannot inflate a client deliverable.

## Release Toolchain Repair (Phase 177) — gating Wave A

Two milestones of user-visible fixes are unreleased. Nothing else in v5.18 ships to a user until
this does.

- [ ] **RELEASE-01**: The local editable install works — `pip install -e . --no-deps` succeeds and
  `tests/test_extras_install_matrix` stops failing environmentally. The stale
  `__editable__.quirk-4.0.0.pth` claims v4.0.0 against a 5.15.0 project and breaks pip's
  build-backend.
  *Evidence: 3 environmental failures in the v5.16 and v5.17 close baselines; carried in HORIZON
  since 2026-08-28.*

- [ ] **RELEASE-02**: A real release ships covering v5.16 **and** v5.17. Version bumped in
  `pyproject.toml` with the editable reinstall done (a bump alone fails `tests/test_version.py`),
  three-component tag, `release.yml` fires. Both prior milestones were archived untagged precisely
  because a wrong tag now cuts a real bad release rather than silently no-opping.

- [ ] **RELEASE-03**: Version-facing surfaces reflect what shipped — `README.md` badge and
  "What's New" (currently stops at v5.15, so two milestones are invisible), `docs/getting-started.md`,
  `docs/UAT-SERIES.md` header and UAT-1-02 criteria, `CHANGELOG.md`.
  *Evidence: milestone-boundary doc review 2026-09-01, Domain 1 — no drift, but no coverage either.*

## Finding Identity Repair (Phase 178) — gating Wave B

The foundation both readings need. Remediation tracking on a decaying key is worse than none.

- [ ] **IDENT-01**: A finding's identity is stable across re-scans. The 22 `title=f"..."`
  interpolations are normalized out of the fingerprint input (the normalizer already exists —
  `TITLE_PREFIX_ALIASES`, `quirk/compliance/__init__.py:105-122` — but is not applied to it), with a
  regression test proving a cert-expiry finding keeps one fingerprint across a simulated day
  boundary. Fixes the live daily-Jira-ticket defect.

- [ ] **IDENT-02**: `compute_trend_report` either reports real movement or honestly reports that it
  cannot. Removing `severity` from the delta key is the likely fix, but note severity-in-key is
  deliberate (`trends.py:206-208`) — a HIGH→MEDIUM partial remediation currently reads as 1 closed +
  1 new. Whichever way it resolves, a test must prove the function is non-vacuous against seeded
  two-scan data; the current implementation passes its tests while being structurally incapable of
  ever returning a non-empty delta.

- [ ] **IDENT-03**: The two disagreeing findings-derivation paths are reconciled or explicitly
  bounded. `quirk/engine/findings_evaluator.py` and the five `_derive_*_findings` functions in
  `quirk/dashboard/api/routes/scan.py` independently produce findings with their own f-string
  titles. Persisting only one guarantees the dashboard and reports disagree about what is resolved.
  Scope may be "prove they agree on identity" rather than "merge them" — merging is a design-judgment
  refactor explicitly excluded from v5.16 as RVW-002.

## Remediation Item Model (Phase 179)

- [ ] **REMED-01**: Remediation items have a stable ID decoupled from their title, joined to the
  finding fingerprints that constitute them. Today `quirk/intelligence/roadmap.py` generates
  aggregate, template-titled candidates from evidence counters and never persists them: fixing 1 of
  8 plaintext endpoints closes nothing, fixing the 8th makes the item silently vanish with no
  closure record, and rewording a title silently re-keys its history. Progress must be expressible
  as "6 of 8 verified closed", not a boolean.

- [ ] **REMED-02**: Closure is refused across incomparable scopes. A persisted **scope signature**
  (port scope, profile, optional extras present, credential presence, sensor set) is recorded per
  scan, and closure computation hard-refuses when signatures differ. Without this, a re-engagement
  run with `--profile quick` would auto-generate an attestation claiming dozens of false closures.
  Positive probe health is required, not "the scan exited 0" — the TRIAGE-176-03 shape, where
  `ssh-audit` silently degraded to banner grabs for the life of the integration.

- [ ] **REMED-03**: `not_observed` is a first-class third state alongside open and closed. Re-scan
  entity resolution is explicitly **not** attempted — `(host, port)` breaks on DHCP, hostname-vs-IP,
  VIPs, and container churn — so operator-supplied aliases carry that burden, with the human in the
  loop. "9 closed, 4 open, 12 not observed" is defensible; "21 closed" is a liability.

## Closure Verification (Phase 180)

- [ ] **CLOSE-01**: Closure is **machine-observed, never human-asserted**, under a two-sided
  condition: detected by a previous scan AND verified absent by the current one. Never mark closed
  if the scanner did not recheck that specific item. Unanimous across Tenable, Qualys, and Orca;
  Qualys's explicit "does not mark a QID closed if the scanner did not recheck it" is the guardrail
  being copied.

- [ ] **CLOSE-02**: `resurfaced` is modelled explicitly. Every comparable tool has this state;
  without it a regression reads as a new finding and the burndown counts the same item closing
  twice.

- [ ] **CLOSE-03**: Burndown is **relative to a named target date**, not a single scalar. EO 14412
  (2026-06-22) deadlines PQC key establishment at **2030-12-31** and digital signatures at
  **2031-12-31** *separately*, so one readiness number is under-specified against the mandate.
  Deadlines live in a `last_verified` staleness-gated catalog with `source_url` and a CI gate — the
  90-day QRAMM/CMVP cadence is the precedent, and EO 14412 plus OMB M-26-15 invalidated the prior
  consensus inside a 3-day window.
  > **Verification debt, carried honestly:** the research pass got **HTTP 403** fetching the NSA
  > CNSA 2.0 PDF. That date table is MEDIUM confidence from concurring secondary sources and
  > **must be manually re-verified against the primary source before shipping.**

## Surfacing (Phase 181)

- [ ] **SURF-01**: Closure state is emitted as **CycloneDX VEX** in the CBOM.
  `ImpactAnalysisState` (`resolved` / `not_affected` / `in_triage` / …) and
  `VulnerabilityAnalysis(state, justification, responses, detail, first_issued, last_updated)` are
  confirmed present in the installed `cyclonedx-python-lib` 11.7.0 — **zero new dependencies**.
  QUIRK's builder currently emits no `vulnerabilities` array, so this is new surface.
  `protected_at_perimeter` maps cleanly onto the existing `upstream_mitigated`.
  *Explicitly deferred:* CDXA `declarations` (signed attestations) has no model module in 11.7.0.

- [ ] **SURF-02**: Burndown appears in the CLI, HTML, and DOCX reports, advisory-only per
  ADVISORY-01, with byte-identical captions across surfaces (the Phase 161 HWLC-19 pattern).

- [ ] **SURF-03**: Burndown appears on the dashboard, reusing the existing advisory-surface firewall
  tuple rather than adding a parallel guard.

## Out of scope (v5.18)

- **Jira/ServiceNow status readback (the old Reading 2).** Bi-directional sync presumes a
  continuously-running control plane — that is the parked SaaS block, not an episodic consulting
  tool. Push-only is the right architecture to keep and harden. Genuinely additive scope, not a
  discount; revisit on demand signal.
- **Signed attestations (CDXA declarations)** — no model module in the installed lib.
- **Entity resolution across re-scans** — deliberately replaced by operator aliases + `not_observed`.
- **Merging the two findings-derivation paths** — RVW-002's design-judgment refactor, excluded
  since v5.16.
- **SaaS multi-tenancy** — still parked. Candidate A explicitly does not require it.

## Watch item (not a requirement)

**CISA/NIST CBOM minimum-elements guidance is due ≈2026-12-19** under EO 14412's 180-day tasking —
a direct schema-risk event for QUIRK's flagship artifact, landing inside this milestone's window.
Not scoped, but SURF-01's VEX surface should be built so a schema shift is absorbable.

## Traceability

| Requirement | Phase | Status |
|---|---|---|
| ADVISORY-01 | All (standing) | Pending |
| RELEASE-01 | Phase 177 | Partial (177-01 done; 177-03 pending) |
| RELEASE-02 | Phase 177 | Pending |
| RELEASE-03 | Phase 177 | Pending |
| IDENT-01 | Phase 178 | Pending |
| IDENT-02 | Phase 178 | Pending |
| IDENT-03 | Phase 178 | Pending |
| REMED-01 | Phase 179 | Pending |
| REMED-02 | Phase 179 | Pending |
| REMED-03 | Phase 179 | Pending |
| CLOSE-01 | Phase 180 | Pending |
| CLOSE-02 | Phase 180 | Pending |
| CLOSE-03 | Phase 180 | Pending |
| SURF-01 | Phase 181 | Pending |
| SURF-02 | Phase 181 | Pending |
| SURF-03 | Phase 181 | Pending |
