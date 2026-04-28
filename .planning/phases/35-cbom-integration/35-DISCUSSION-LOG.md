# Phase 35: CBOM Integration — Discussion Log

**Discussed:** 2026-04-28
**Format:** Per-area Q&A trail. Human reference only — downstream agents read CONTEXT.md.

---

## Areas Selected by User

All four presented gray areas:
1. Plaintext skip-list naming
2. STARTTLS variant coverage
3. Cloud broker label handling
4. Verification approach for SC-1/SC-2

---

## Area 1: Plaintext skip-list naming

**Context surfaced:** REQUIREMENTS CBOM-03 specifies skip values `"AMQP"` / `"KAFKA-PLAIN"` / `"REDIS-PLAIN"`, but `quirk/scanner/broker_scanner.py:472` actually emits `"AMQP-PLAIN"`.

**Question asked:** How should we resolve the AMQP vs AMQP-PLAIN mismatch?

**Options presented:**
1. Use `AMQP-PLAIN`, update REQUIREMENTS (Recommended)
2. Add both names defensively
3. Rename scanner to emit `AMQP`

**User clarification request:** "what is the difference?" — Claude expanded each option with concrete code-change scope and ripple analysis.

**User selection:** Option 1 — Use `AMQP-PLAIN`, update REQUIREMENTS.

**Decision:** D-01 (CONTEXT.md).

---

## Area 2: STARTTLS variant coverage

**Context surfaced:** CBOM-01 enumerates `SMTP-STARTTLS`, `SMTPS`, `IMAPS`, `POP3S` (4 labels), but `quirk/scanner/email_scanner.py:74-87` emits 6 labels including `IMAP-STARTTLS` and `POP3-STARTTLS`.

**Question asked:** How should we handle IMAP-STARTTLS and POP3-STARTTLS?

**Options presented:**
1. Treat all 6 email labels uniformly (Recommended)
2. Only the 4 listed in CBOM-01
3. Skip-list IMAP-STARTTLS / POP3-STARTTLS

**User selection:** Option 1 — All 6 uniform.

**Decision:** D-02 (CONTEXT.md).

---

## Area 3: Cloud broker label handling

**Context surfaced:** Broker scanner emits `AMQPS/Azure-ServiceBus` (with slash) for Azure Service Bus endpoints. Slash could affect any consumer that splits bom_refs on `/`.

**Question asked:** How should the AMQPS/Azure-ServiceBus label flow through the CBOM?

**Options presented:**
1. Fall through as standard TLS (Recommended)
2. Normalize to AMQPS in CBOM only
3. Rename scanner to AMQPS-AZURE

**User clarification request:** "what are the ramifications - can you provide scenarios" — Claude provided 5 concrete scenarios covering compliance scripts, scan-diff churn, CBOM viewers, downstream Phase 36 dashboard, and bom_ref parsing safety.

**User selection:** Option 1 — Fall through unchanged.

**Decision:** D-03 (CONTEXT.md).

---

## Area 4: Verification approach for SC-1 / SC-2

**Question asked:** How should SC-1 and SC-2 be verified (CBOM contains email + broker components)?

**Options presented:**
1. Synthesized endpoints + builder assertions (Recommended)
2. Golden CBOM snapshot from chaos labs
3. Both — unit + integration
4. Defer integration to Phase 37 gap closure

**User selection:** Option 2 — Golden CBOM snapshot from chaos labs.

**Decision:** D-04 (CONTEXT.md). Phase 35 takes Docker dependency (already established by Phases 32/33).

---

## Claude's Discretion (no user question asked)

- Quantum-safety classification verification approach (D-05) — captured as "verify, don't redefine" pattern; planner picks specific cipher suites to assert against.
- Doc updates and Obsidian sync (D-06, D-07, D-08) — mandatory per CLAUDE.md / user-feedback memory; no user question needed.

---

## Deferred Ideas

- DEF-35-A: Defensive skip-list entries for suffixless `AMQP` / `KAFKA` / `REDIS` labels.
- DEF-35-B: Renaming `AMQPS/Azure-ServiceBus` to slash-free form if a downstream consumer breaks.
