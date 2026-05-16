# Phase 71: Protocol Scanner WARNINGs — Discussion Log

**Discussion date:** 2026-05-15
**Mode:** default (no flags)
**Outcome:** CONTEXT.md written with 15 locked decisions across 4 user-confirmed gray-area clusters

This log is for human reference (audit / retrospective). Downstream agents (researcher, planner, executor) consume only `71-CONTEXT.md`.

---

## Pre-discussion analysis

Phase 71 closes 14 WARNING-severity audit findings in the protocol-scanner subsystem (`scanners-protocol/WR-01..WR-14`), mapped to 5 PROTO-NN requirements. Like Phase 70, it is a fixed-scope, audit-driven phase — most decisions are pre-determined by the audit row text. The discussion focused only on choices where the user's call meaningfully changes the result.

**Pre-decided (skipped to avoid re-asking):**
- Phase boundary, requirement set, success criteria — already locked in ROADMAP.md / REQUIREMENTS.md
- Audit-row-flip evidence pattern — Phase 69 / 70 precedent
- defusedxml dependency — already core (`pyproject.toml:29`)
- Logger format — Phase 70 / qramm.py / scan.py established `logger.warning("X failed for %r: %s", ...)` idiom
- ScanCfg field-naming convention — `<subsystem>_concurrency` per Phase 41
- Internal-contract style with no new UAT-NN-NN cases — Phase 70 wrap-note pattern

**Identified gray areas (presented to user):**
1. CIDR expansion bound (PROTO-05 / WR-14) — magnitude + failure mode
2. ThreadPool max_workers ScanCfg knob (PROTO-05 / WR-12) — naming + default + scope
3. nmap default port CSV (PROTO-03 / WR-04) — port set composition
4. Do-not-touch list (scope discipline) — explicit non-goals to prevent diff sprawl

---

## Discussion turn

### Q1 — CIDR expansion bound

**Options presented:**
- /22 hard cap, raise (Recommended)
- /16 hard cap, raise
- /22 soft cap, log + truncate
- Configurable via ScanCfg.max_cidr_hosts

**User selection:** /22 hard cap, raise (Recommended)

**Captured as:** D-01

### Q2 — ThreadPool concurrency knob

**Options presented:**
- motion_concurrency=50 (Recommended)
- email_concurrency=50, broker_concurrency=50
- motion_concurrency=100

**User selection:** motion_concurrency=50 (Recommended)

**Captured as:** D-02

### Q3 — nmap default port CSV

**Options presented:**
- Mirror ports_tls + SSH + key web (Recommended)
- Add motion + identity + RDP
- Use nmap --top-ports 100
- Reuse Phase 47 consulting set verbatim

**User selection:** Add motion + identity + RDP

**Captured as:** D-03 — broadest consulting-grade union: ports_tls + 22 (SSH) + 80/8080 (HTTP) + 25/465/587/993/995 (motion email) + 88 (Kerberos) + 389/636 (LDAP/LDAPS) + 3389 (RDP) + 5671 (AMQPS) + 9092 (Kafka). User picked the broader set over the recommended composable-base — accepted on the rationale that consulting-grade discovery benefits from wider port surface even at the cost of slower nmap runs.

### Q4 — Do-not-touch list

**Options presented (multi-select):**
- Other bare except clauses outside the WR rows (Recommended)
- tls_scanner.py refactor / additions (Recommended)
- Email/broker connection-pool refactor
- Coverage formula changes

**User selection:** Other bare except clauses outside the WR rows (Recommended), tls_scanner.py refactor / additions (Recommended)

**Captured as:** D-08 (bare except scope), D-15 (full do-not-touch list). The two unchecked options (email/broker pool refactor, coverage formula) were folded into D-15 as Claude's discretion — implied by the audit-driven "fix only what the row says" discipline of this phase.

---

## Deferred ideas raised in discussion

- **Wizard prompt for motion_concurrency** — D-02a, captured in CONTEXT deferred section
- **Aggregate CIDR bound across all `cfg.targets.cidrs`** — D-01a, captured in CONTEXT deferred section

---

## Notes on discussion process

- All 4 questions presented in a single batched AskUserQuestion call (one per gray area). User answered all four; no follow-up questions needed.
- No scope creep raised by user — Phase 71's tight audit-row framing makes it self-limiting.
- Codebase scout (~5% context) located all key sites before question generation: `target_expander.py:expand_targets`, `email_scanner.py:532`, `broker_scanner.py:475/574/801`, `nmap_provider.py:54`, `nmap_parser.py`, `coverage.py`, `config.py:63 ScanCfg`. This enabled concrete option text (file:line citations in each option's description) instead of abstract framing.
