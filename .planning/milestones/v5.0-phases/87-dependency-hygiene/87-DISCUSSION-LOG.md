# Phase 87: Dependency Hygiene - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 87-dependency-hygiene
**Areas discussed:** Node bump scope, xml_safe.py shape, XXE test as CI gate, Node 24 verification, WR-06 audit traceability, nmap_parser migration API, xml_safe API surface, plan execution order

---

## Node Bump Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | node-version 20→24 only, keep setup-node@v4 (dashboard-quality.yml only) | ✓ |
| Broader | Also bump setup-node@v4→v6 + audit third-party actions' bundled Node | |

**User's choice:** Minimal
**Notes:** Research confirmed @v4 already supports Node 24; smallest diff clears the deadline with lowest churn risk.

---

## xml_safe.py Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Factory function | make_safe_parser() returns a fresh hardened lxml parser per call (thread-safe) | ✓ |
| Shared module constant | Single _SAFE_XML_PARSER reused everywhere (risks concurrency bug) | |
| Thread-local parser | One parser per thread via threading.local() | |

**User's choice:** Factory function
**Notes:** lxml parsers aren't thread-safe; SSH/SAML scanners run threaded — factory is safe by construction.

---

## XXE Test as CI Gate

| Option | Description | Selected |
|--------|-------------|----------|
| Permanent CI invariant | Billion-laughs/XXE pytest wired as a forward-locking gate (matches AST/staleness-gate culture) | ✓ |
| One-off pytest | Cover it in the suite, no special invariant framing | |

**User's choice:** Permanent CI invariant
**Notes:** Prevents silent regression if an unsafe parser is re-introduced.

---

## Node 24 Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Real GHA run on a branch | Push change so dashboard-quality runs on Node 24 and goes green | ✓ |
| Local validation only | Validate dashboard build/tests locally on Node 24, trust the workflow | |

**User's choice:** Real GHA run on a branch
**Notes:** Success criterion #1 is "CI green on Node 24"; only a real run proves the runtime upgrade. Research explicitly flagged this.

---

## WR-06 Audit Traceability

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve + re-point | Update WR-06 comment to cite xml_safe chokepoint; assert WR-06 stays mitigated + ledger gate green | ✓ |
| Just migrate, no ledger fuss | Swap parser; assume new hardened parser inherently satisfies WR-06 | |

**User's choice:** Preserve + re-point
**Notes:** nmap_parser's defusedxml is a documented mitigation for audit WR-06; the repo enforces a zero-open-ledger CI gate. Controlled mitigation swap avoids silently reopening a finding.

---

## nmap_parser Migration API

| Option | Description | Selected |
|--------|-------------|----------|
| lxml.etree compat | Use lxml.etree with factory parser; keep ET-style navigation (findall/get) | ✓ |
| Full rewrite to lxml idioms | Rewrite parsing with lxml-native xpath etc. | |

**User's choice:** lxml.etree compat
**Notes:** Smallest behavioral change; re-test against existing nmap XML fixtures.

---

## xml_safe API Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Factory + parse helper | make_safe_parser() plus a thin parse_safely(source) convenience | ✓ |
| Factory only | Expose just make_safe_parser(); callers pass it themselves | |

**User's choice:** Factory + parse helper
**Notes:** Single obvious entry point; callers can't forget to pass the parser.

---

## Plan Execution Order

| Option | Description | Selected |
|--------|-------------|----------|
| Parallel-safe, atomic commits | Disjoint files (yaml vs python); independent commits; CI fail in one never blocks the other | ✓ |
| Sequential (Node first) | Force Node bump first, then lxml, strict order | |

**User's choice:** Parallel-safe, atomic commits
**Notes:** Matches the roadmap rationale for the two-plan split.

---

## Claude's Discretion

- Exact test file name/location for the XXE invariant (follow existing `tests/` naming).
- Whether `parse_safely` wraps `fromstring` + `parse` or just one, based on actual call-site needs.

## Deferred Ideas

None — discussion stayed within phase scope. (setup-node major bump and third-party action Node audits explicitly scoped OUT.)
