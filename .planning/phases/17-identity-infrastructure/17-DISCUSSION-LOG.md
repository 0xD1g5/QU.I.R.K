# Phase 17: Identity Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-08
**Phase:** 17-identity-infrastructure
**Mode:** discuss
**Areas discussed:** Migration guard approach, Config template section, Kerberos target field shape

---

## Gray Areas Identified

From codebase analysis:

| Area | Why it's a gray area | Resolution |
|------|---------------------|------------|
| Migration guard approach | No existing ALTER TABLE migration pattern in codebase; `init_db()` only calls `create_all()`. Three valid options: inspector-first, try/except OperationalError, raw SQL IF NOT EXISTS | Inspector-first (SQLAlchemy `inspect()`) |
| Config template section | Identity is a new capability tier; question of inline-with-connectors vs separate subsection vs commented-out defaults | Separate commented subsection, fully commented out by default |
| Kerberos target field shape | KDC hostnames vs SAML metadata URLs vs DNSSEC domain names are different target types; question of overlap with main scan targets | Follow existing `x_targets: list` pattern in ConnectorsCfg; no overlap with main targets |

---

## User Context

User noted that the identity infrastructure domain is outside their strong area, and requested
recommendations based on what is practical for both small organizations and large enterprises.
All recommendations were accepted without correction.

---

## Decisions Made

### Migration Guard Approach → SQLAlchemy inspector-first

**Question:** How to implement idempotent ALTER TABLE ADD COLUMN in db.py startup?

**Options presented:**
- SQLAlchemy inspector-first (`sa_inspect(engine).get_columns(table)` → ALTER if missing)
- try/except OperationalError (optimistic, catch "duplicate column name")
- Raw SQL `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (SQLite 3.37+ native)

**Selected:** SQLAlchemy inspector-first

**Rationale:** Avoids catching exceptions for control flow; idiomatic SQLAlchemy; testable
(can prove existing column causes no error); scales to future column additions.

---

### Config Template → Separate commented identity subsection

**Question:** How should identity fields appear in quirk init output?

**Options presented:**
- Inline with existing connectors block (like enable_aws, enable_jwt)
- Separate `# -- Identity connectors (optional) ---` subsection, commented out by default
- Active false/empty defaults like existing connectors

**Selected:** Separate commented subsection, fully commented out

**Rationale:** Identity scanning is a specialized capability tier; consultants doing basic
TLS/SSH scans shouldn't need to read past identity settings; commented-out default
signals "opt-in advanced scanning."

---

### Target Field Shape → Follow existing x_targets: list pattern

**Question:** Should Kerberos/SAML/DNSSEC targets overlap with main scan targets or stay in ConnectorsCfg?

**Options presented:**
- Stay in ConnectorsCfg as separate `kerberos_targets`, `saml_targets`, `dnssec_targets: list`
- Overlap with main targets (include_ips / fqdns for Kerberos; fqdns for DNSSEC)

**Selected:** Separate lists in ConnectorsCfg following existing pattern

**Rationale:** Main targets are for network sweeps (TLS/SSH); identity targeting is explicit
and protocol-specific. KDC probes, SAML metadata fetches, and DNSSEC queries are not
sweep operations. Matches jwt_targets/container_targets/source_targets pattern exactly.

---

## No Corrections

All recommendations accepted — user deferred to Claude's judgment on identity infrastructure
patterns.
