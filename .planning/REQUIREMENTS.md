# Requirements: QU.I.R.K. — Milestone v5.21 Dashboard Parity & Exposure Capability

**Defined:** 2026-09-08
**Core Value:** Complete, defensible cryptographic inventory with CBOM deliverable and
quantum-readiness score — handed to a client in under two hours. This milestone makes the
dashboard a full, trustworthy operating surface and adds the first genuinely new detection
capability since OT/ICS.

Sources: PM-approved scope from the 2026-09-08 boundary review (`PROJECT.md` §Current Milestone),
backlog items 999.104 / 999.96 / 999.98 / 999.99 / 999.100 + the phantom-cert todo, and
`.planning/research/SUMMARY.md` (4-file research pass, confidence HIGH).

## v1 Requirements

### Config Parity (999.104, tiers 1–3)

- [x] **PARITY-01**: Operator can view the effective config a scan will run with (resolved
      `QuirkCfg`) from the dashboard, via a new auth-gated `GET /api/config/effective` that
      actively redacts credential fields (the existing 1-field unauthenticated `/api/config` is
      not a usable seed — research-verified).
- [x] **PARITY-02**: Operator can enable/disable any of the 25 connectors at scan-submit time,
      with each toggle gated on a run-time availability probe covering BOTH
      `optional_extra.REGISTRY` and the per-scanner `*_AVAILABLE` flags — a connector whose
      extra isn't installed is shown unavailable-with-reason, never offered as a silent no-op.
      Config flows through the existing `_write_job_config()` YAML-overlay path (never a
      `ScanJob` blob column) to preserve `_user_set_fields` semantics.
- [x] **PARITY-03**: Operator can supply connector credentials at scan-submit time through an
      in-memory-only path — credentials never land in `ScanJob`, the job `config.yaml`, or any
      log (extends the Phase 59 `safe_str` no-log gate to the new request fields).
- [x] **PARITY-04**: Operator can set advanced scan-behavior fields (TLS port lists (SSH list dropped per Phase 194 D-18/999.106 — not a CLI field),
      `tls_enum_mode`, discovery options, timeouts/retry) in a collapsed "advanced" section of
      the scan form, composing with (not fighting) vertical presets under a single recorded
      precedence rule.

### Skip Observability (999.96, observability half)

- [x] **OBS-01**: Every scanner phase that does not run has a structured skip record persisted
      to the database per scan (not only the filesystem `run-stats-*.json`), with
      distinguishable reasons: disabled-by-config, missing-extra, no-eligible-targets,
      missing-credentials, failed.
- [x] **OBS-02**: Operator can see which scanner phases ran / were skipped and why, on the
      dashboard scan surfaces and in the CLI/HTML/DOCX report coverage disclosure — a scan that
      assessed nothing in a domain says so, never renders as silently empty.

### Key Identity (999.98)

- [x] **SPKI-01**: Every TLS endpoint's certificate SPKI SHA-256 fingerprint is persisted on
      `CryptoEndpoint` — including endpoints arriving via the sensor push/merge path
      (`PushEnvelope` + `merge/scan.py` projection updated in the same plan, with a round-trip
      sensor-push integration test; v5.8 B-01 recurrence guard).
- [x] **SPKI-02**: Operator can see key-reuse — endpoints sharing the same public key —
      derived by query (no denormalized boolean), framed as remediation leverage ("one re-key
      closes N findings").

### Executive Verdict (999.100)

- [x] **VERDICT-01**: Consultant sees the Executive Verdict layer on the dashboard by default
      (no flag gate), landed by cherry-picking only commit `f05e7dc7` from `origin/UX-Updates`
      (never a branch merge — the branch is 7 months stale) and rewired to consume
      `rating`/`rating_cap_reason` from the API instead of re-deriving score bands client-side.

### Certificate View Integrity (phantom-cert todo; continues existing DASH numbering)

- [x] **DASH-09**: Dashboard certificate inventory and `/print` PDF render only real
      certificates — failed TLS handshakes (no `cert_subject`, or `scan_error` set) are
      excluded via a shared filter helper, and an honest "no certificates discovered" empty
      state appears when nothing real was found.

### Quantum Exposure Map (999.99)

- [x] **MAP-01**: The Exposure Map's reachability data-source decision (operator-declared vs
      inferred vs deferred) is resolved by a dedicated spike and recorded as a decision before
      any rendering implementation is planned — a hard go/no-go gate.
- [x] **MAP-02**: Consultant can view a quantum-exposure attack-path map built ONLY from
      verified relationships (key-reuse clusters from SPKI-02, operator-declared crown jewels,
      confirmed hardware crypto-bridge chains) — zero inferred edges, with an explicit "no path
      data available" state instead of a fabricated chain.
- [x] **MAP-03**: Exposure Map data never feeds the quantum-readiness score — machine-enforced
      by a `test_exposure_map_score_guard.py` firewall test (ADVISORY-01 /
      `test_cve_score_guard.py` pattern) written in the same phase the feature is built.

## v2 Requirements

Deferred, tracked in `HORIZON.md`'s Open-Item Ledger:

- **PARITY-T4**: Dashboard load/edit/save of the persistent `config.yaml` (tier 4) — needs its
  own threat model first.
- **MAP-ELK**: `cytoscape-elk` layout upgrade — only if dagre proves visually inadequate
  against real exposure data.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Tier 4 server-side `config.yaml` editing | New security surface (auth, path containment, YAML injection) — explicit PM decision, deferred with its own threat-model gate |
| Inferred (nmap/heuristic) attack-path edges | Credibility risk in a client deliverable — fabricated chains are the 999.95 failure class in graph form; anti-feature per research |
| Flat 138-field 1:1 config form | Operator-hostile; tiered disclosure is the industry pattern (Nessus/Qualys precedent) |
| Wholesale `origin/UX-Updates` merge | Branch diverged 2026-02-18; a merge deletes ~7 months of main (817 files, −143K lines) |
| Denormalized "key reused" boolean column | Drifts from truth; `GROUP BY cert_spki_sha256` derivation instead |
| P3 UX set (999.101/999.102/BACK-01/03/08), 999.103, trends.py int-coercion, GSD tooling todos, UAT coverage-gaps worklist | Deliberately deferred at boundary; visible in HORIZON's Open-Item Ledger |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PARITY-01 | 192 | Complete (2026-09-09) |
| PARITY-02 | 193 | Complete |
| PARITY-03 | 193 | Complete |
| PARITY-04 | 194 | Complete (2026-09-09) |
| OBS-01 | 192 | Complete (2026-09-09) |
| OBS-02 | 192 | Complete (2026-09-09) |
| SPKI-01 | 191 | Complete |
| SPKI-02 | 191 | Complete |
| VERDICT-01 | 194 | Complete (2026-09-09) |
| DASH-09 | 194 | Complete |
| MAP-01 | 195 | Complete (2026-09-10) |
| MAP-02 | 195 | Complete (2026-09-10) |
| MAP-03 | 195 | Complete |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 13 (Phase 191: SPKI-01/02; Phase 192: PARITY-01, OBS-01/02; Phase 193: PARITY-02/03; Phase 194: PARITY-04, VERDICT-01, DASH-09; Phase 195: MAP-01/02/03)
- Unmapped: 0

---
*Requirements defined: 2026-09-08*
*Last updated: 2026-09-10 after 195-06 operator walkthrough approval (MAP-01, MAP-02 flipped Complete)*
