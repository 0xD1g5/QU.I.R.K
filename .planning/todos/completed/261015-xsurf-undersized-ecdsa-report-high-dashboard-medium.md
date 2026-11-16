---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) D-04; RESEARCH Open Question 6
priority: medium
area: quirk/engine/findings_evaluator.py (ECDSA sites), quirk/dashboard/api/routes/scan.py (Quantum- finding), quirk/dashboard/api/finding_title_bridge.py
status: pending
resolves_phase: 236
owner: "999.132"
---

# Undersized ECDSA key is HIGH in the report and MEDIUM on the dashboard

The report lists `TLS certificate uses undersized ECDSA key` at HIGH (`quirk/engine/findings_evaluator.py:757-764`)
and `TLS certificate uses quantum-vulnerable ECDSA key` at MEDIUM (`:776-783`), split by key size. The dashboard has one
check for every non-RSA public-key algorithm, `Quantum-{vulnerable|at risk} algorithm: {alg}` at MEDIUM regardless of
size (`quirk/dashboard/api/routes/scan.py:346-357`). So an undersized-ECDSA certificate contributes a HIGH to the report's
ceiling count and a MEDIUM to the dashboard's.

This is not caught by the severity gate: `Quantum-` is unbridged (`UNBRIDGED_DASHBOARD_TITLES`) and its literal severity
is MEDIUM, so the D-22 leg (HIGH/CRITICAL unbridged titles only) passes. It is filed here as a known divergence class
rather than a gate entry.

- [ ] Add an undersized-ECDSA branch to the dashboard check (size-gated, HIGH, same title as the report) and bridge it.
- [ ] Add a parity fixture row with a P-192 or similarly undersized ECDSA key.
- [ ] Revisit `UNBRIDGED_DASHBOARD_TITLES["Quantum-"]` wording once the split exists.

## Feasibility & Effort

- **CONFIRMED** by reading both generators at HEAD (citations above); not probed end to end.
- Effort **S-M**. Unknown: the exact size threshold the report uses (read it from `findings_evaluator.py:750-760`
  before copying). No spike needed.

## Resolution (2026-11-16)

Fixed by Phase 236 (XSURF-11): dashboard HIGH "TLS certificate uses undersized ECDSA key" (<256 bits), no Quantum- finding for that row. Commit main 405925d5 (PR #82 merge). Test: ...test_xsurf236_family_headline_parity[ecdsa_192]. Score movement: dashboard drops for ECDSA <256 bits (MEDIUM -> HIGH).
