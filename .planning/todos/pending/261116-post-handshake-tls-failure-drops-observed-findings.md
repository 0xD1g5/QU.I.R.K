---
type: todo
created: 2026-11-16
source: Phase 236-09 code review WR-02 (236-09-REVIEW.md)
priority: medium
area: quirk/scanner/tls_scanner.py, quirk/engine/findings_evaluator.py, quirk/dashboard/api/finding_derivation.py
status: pending
resolves_phase:
owner: "999.132"
---

# A TLS failure after a successful handshake drops real observations on both surfaces

`tls_scanner._scan_one_fallback` fills version and certificate columns from a successful handshake, then a later
capability-enumeration failure sets `scan_error`. Both surfaces now treat the row as a scan error, so true positives observed
in the handshake (legacy version, an expired certificate at CRITICAL) appear on neither surface, and the report's
replacement finding says the handshake was blocked when it succeeded. Parity holds (236-09), but it is parity on less
information.

## Feasibility & Effort

**Feasibility: MEDIUM.** Add one shared predicate, called by both surfaces, that separates post-handshake failures (keep the
observed-field findings) from pre-handshake failures (scan-error branch). **Effort: M.** Moves scores on both surfaces
together; needs new divergence families and a scanner-side marker or a reliable column-based test.
