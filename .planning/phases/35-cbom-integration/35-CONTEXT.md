# Phase 35: CBOM Integration — Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the email + broker TLS endpoints (already produced by Phases 32 and 33) into the CycloneDX CBOM pipeline so they appear correctly across Pass 1 (algorithm components), Pass 2 (certificate components), and Pass 3 (protocol components). Plaintext-only broker endpoints must be skipped to prevent hollow `CertificateProperties` entries. Scope is **CBOM wiring only** — no scanner changes, no risk-engine work, no dashboard.

**The elegance:** `quirk/cbom/builder.py` uses a "default = TLS" fall-through in Pass 3. Email TLS labels (`SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S`) and broker TLS labels (`AMQPS`, `AMQPS/Azure-ServiceBus`, `KAFKA-TLS`, `REDIS-TLS`) flow through automatically because they are not in any skip list and not handled as a special case. The only required code change is **adding plaintext-only labels to Pass 2 and Pass 3 skip lists**.

**In scope:**
- Add `KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN` to Pass 2 + Pass 3 skip lists in `quirk/cbom/builder.py` (CBOM-03).
- Verify quantum-safety classification of `TLS_RSA_WITH_*`, `ECDHE`, and TLS 1.3 AEAD ciphers via existing `QUANTUM_SAFETY_MAP` (CBOM-04).
- Update `.planning/REQUIREMENTS.md` CBOM-01 + CBOM-03 wording to reflect actual emitted labels.
- Golden CBOM snapshot tests against `labs/email/` and `labs/broker/` chaos lab scans.

**Out of scope (other phases):**
- Dashboard `/motion` tab + 6th subscore line + `MotionFinding` API schema → **Phase 36**.
- Nyquist VALIDATION.md across all v4.4 phases + version bump to 4.4.0 → **Phase 37**.
- Any changes to scanners, finding IDs, or chaos lab fixtures (Phases 32 + 33 territory).

</domain>

<decisions>
## Implementation Decisions

### Plaintext skip-list naming (CBOM-03)
- **D-01:** Skip lists use the **actual emitted labels**: `KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`. Code is ground truth; `REQUIREMENTS.md` CBOM-03 wording is amended to match (it currently says `"AMQP"` / `"KAFKA-PLAIN"` / `"REDIS-PLAIN"` — only AMQP needs the suffix correction). Both Pass 2 (line ~436) and Pass 3 (line ~517) skip-list tuples in `quirk/cbom/builder.py` get the three additions. **Do not** rename scanner-emitted labels — that's Phase 33's territory and would ripple through finding IDs, lab expected_results, and tests.

### STARTTLS variant coverage (CBOM-01)
- **D-02:** All **six** email TLS labels (`SMTP-STARTTLS`, `SMTPS`, `IMAP-STARTTLS`, `IMAPS`, `POP3-STARTTLS`, `POP3S`) flow uniformly through Pass 1 + Pass 2 + Pass 3 via the builder's default-TLS branch. No code change in builder. CBOM-01 wording in REQUIREMENTS.md is updated to enumerate all six (currently lists only four). Test fixtures cover all six labels.

### Cloud broker label handling
- **D-03:** `AMQPS/Azure-ServiceBus` (with slash) flows through the default-TLS branch unchanged. **No normalization, no special-case** in builder. Rationale: the slash never escapes into bom_ref strings (bom_refs are `crypto/protocol/tls/{host}:{port}` — slashes are in the prefix, not the value), so no consumer parsing is broken. Preserving the cloud-vs-self-hosted distinction is consulting-grade value: compliance scripts can `jq`-filter for "Azure brokers", annual scan diffs stay stable, and Phase 36 dashboard naturally renders cloud as a distinct row.

### Verification approach (SC-1, SC-2)
- **D-04:** **Golden CBOM snapshot** verification driven by chaos labs. Test plan:
  1. `docker compose --profile email up` → run scan → write generated CBOM → diff against `labs/email/expected_cbom.json` (committed golden file).
  2. `docker compose --profile broker up` → same flow → diff against `labs/broker/expected_cbom.json`.
  3. Snapshots assert key invariants: algorithm components present for each email/broker TLS label, no certificate components for plaintext labels, `TLS_RSA_WITH_*` cipher suites flagged `quantum-vulnerable`.
- Phase 35 inherits Docker dependency that Phases 32 and 33 already established — no new infrastructure cost.
- Synthesized-endpoint unit tests (mirroring Phase 34's style) supplement the golden snapshots for fast feedback during development; planner decides the split.

### Quantum-safety classification (CBOM-04)
- **D-05:** `QUANTUM_SAFETY_MAP` in `quirk/cbom/classifier.py` already handles cipher suites for these endpoints. **Verify, don't redefine.** A unit test asserts the classification for a representative set: `TLS_RSA_WITH_AES_128_CBC_SHA` → `quantum-vulnerable` (HIGH), `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384` → `quantum-vulnerable` (MEDIUM), `TLS_AES_256_GCM_SHA384` (TLS 1.3 AEAD) → `quantum-unknown` (LOW). If any is missing or mis-classified, that's a separate spike — file a backlog ticket rather than expanding scope.

### Documentation updates (mandatory per CLAUDE.md)
- **D-06:** `.planning/REQUIREMENTS.md` edits (CBOM-01 enumeration, CBOM-03 AMQP→AMQP-PLAIN) are part of this phase, not deferred.
- **D-07:** `docs/UAT-SERIES.md` gains UAT-35-01 (golden email CBOM matches snapshot), UAT-35-02 (golden broker CBOM matches snapshot), UAT-35-03 (no hollow cert components for plaintext brokers).
- **D-08:** Obsidian phase note created at start, updated per wave, finalized on completion at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-35-CBOM-Integration.md`. UAT-Series synced to vault after final commit.

### Claude's Discretion
- Whether the new skip-list strings are inserted alphabetically or grouped together (planner decides for readability).
- Exact split between unit tests (`tests/cbom/test_motion_endpoints.py`) and integration golden snapshots — both styles are required by D-04, but the file naming and test count are planner-discretion.
- Whether the golden CBOM JSONs include full timestamps (volatile) or are normalized before diff. Planner picks based on existing test patterns in `tests/cbom/`.
- Whether to create `expected_cbom.json` next to existing `labs/email/expected_results.md` or in a parallel `tests/fixtures/cbom/` directory.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (locked)
- `.planning/REQUIREMENTS.md` §"CBOM integration" — CBOM-01, CBOM-02, CBOM-03, CBOM-04 are LOCKED on intent. Wording for CBOM-01 (enumerate all 6 email labels) and CBOM-03 (`"AMQP"` → `"AMQP-PLAIN"`) is amended in this phase per D-01 and D-02.
- `.planning/ROADMAP.md` Phase 35 entry — CBOM Integration goal + 4 success criteria.

### Builder pipeline (read before modifying skip lists)
- `quirk/cbom/builder.py` (entire file). Specifically:
  - **Pass 1** (~lines 340–410): algorithm component registration. Already ep.protocol-aware. Email + broker TLS labels flow through automatically because they fall into the default branch (no special-case needed).
  - **Pass 2** (~line 436): certificate component skip list. **Add** `KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`.
  - **Pass 3** (~line 517): protocol component skip list. **Add** the same three labels. The default branch (~line 525) handles all TLS endpoints — no other change needed.

### Classifier quantum mapping (verify, don't redefine)
- `quirk/cbom/classifier.py`:
  - `QuantumSafety` enum + `quantum_safety_label()` (~lines 24–44).
  - The cipher-suite-to-NIST-level lookup tables (~lines 150–185) — confirm coverage for `TLS_RSA_WITH_*`, `TLS_ECDHE_*`, and TLS 1.3 AEAD families per CBOM-04.

### Scanner-emitted protocol labels (ground truth — do not modify)
- `quirk/scanner/email_scanner.py` (~lines 74–87): authoritative list of the 6 email TLS labels.
- `quirk/scanner/broker_scanner.py` (lines 173, 390, 472, 512, 515, 611, 625, 674): authoritative list of broker TLS + plaintext labels.

### Test patterns
- `tests/cbom/` (entire directory) — existing CBOM test conventions for builder + classifier. Planner reads to choose file naming + test split between unit and golden snapshot.
- `tests/intelligence/test_motion_subscore.py` (Phase 34 output) — synthesized-endpoint test pattern to mirror.

### Chaos labs (golden snapshot source)
- `labs/email/expected_results.md` + `docker-compose` `email` profile — source for `expected_cbom.json` golden snapshot.
- `labs/broker/expected_results.md` + `docker-compose` `broker` profile — source for the broker golden snapshot.

### Carry-forward decisions (from Phases 32, 33, 34)
- Phase 32 emits 6 email TLS labels (no plaintext-only label — port 25 always gets `SMTP-STARTTLS` regardless of STARTTLS success). Therefore **no email plaintext skip-list entries needed**.
- Phase 33 emits broker labels with `-TLS` / `-PLAIN` suffix convention. Phase 35 honors this convention rather than renaming.
- Phase 34 established the "verify, don't redefine" pattern for existing maps (`QUANTUM_SAFETY_MAP` here mirrors `_as_int(evidence.get(...))` legacy-compat pattern there).

### Downstream consumers (informational; not modified in Phase 35)
- Phase 36 will read the CBOM components surfaced here to render the dashboard `/motion` tab. Stable component names and preserved cloud-vs-self-hosted distinction (D-03) are inputs to Phase 36's UI.

</canonical_refs>

<deferred>
## Deferred Ideas

- **DEF-35-A:** Defensive skip-list entries for `AMQP` / `KAFKA` / `REDIS` (no suffix) — only useful if a future scanner change drops the `-PLAIN` suffix. Captured as a "future-proofing" backlog item rather than carried in Phase 35.
- **DEF-35-B:** Renaming `AMQPS/Azure-ServiceBus` to `AMQPS-AZURE` (slash-free) — only worth doing if a downstream consumer is shown to actually break. Revisit if Phase 36 or a CBOM viewer reports issues.

</deferred>

[Roadmap](../../ROADMAP.md)
