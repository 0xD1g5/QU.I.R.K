# Phase 17: Identity Infrastructure - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Add structural scaffolding for three new identity scanners: schema columns, config flags and
target fields, and optional dependency group declaration. No scanner logic, CBOM integration,
or UI work this phase — pure plumbing that phases 18–20 build upon.

</domain>

<decisions>
## Implementation Decisions

### Schema Migration Guard
- **D-01:** Use SQLAlchemy inspector-first pattern for idempotent column additions. After
  `Base.metadata.create_all(engine)`, call a helper that checks
  `sa_inspect(engine).get_columns("scan_results")` and only runs `ALTER TABLE ... ADD COLUMN`
  if the column name is absent. This avoids catching exceptions for control flow and is
  explicitly testable (prove an existing column causes no error).
- **D-02:** Add three nullable Text columns to `ScanResult`: `kerberos_scan_json`,
  `saml_scan_json`, `dnssec_scan_json` — matching the existing `ssh_audit_json`,
  `jwt_scan_json`, `container_scan_json` pattern in `quirk/models.py`.
- **D-03:** The migration helper lives in `db.py` and is called from `init_db()` after
  `create_all()` — no separate migration file or Alembic dependency.

### ConnectorsCfg Fields
- **D-04:** Add `enable_kerberos`, `enable_saml`, `enable_dnssec` boolean flags to
  `ConnectorsCfg` with `= False` defaults — matching `enable_jwt: bool = False` pattern.
- **D-05:** Add separate target list fields: `kerberos_targets: list`, `saml_targets: list`,
  `dnssec_targets: list` — all untyped `list` with `field(default_factory=list)`, matching
  `jwt_targets`, `container_targets`, `source_targets` exactly.
  - `kerberos_targets` — KDC hostnames/IPs (explicit, not CIDR sweeps)
  - `saml_targets` — metadata URLs (`https://idp.example.com/metadata.xml`)
  - `dnssec_targets` — domain names (`example.com`) for DNSKEY queries
- **D-06:** Identity fields do NOT overlap with main scan targets (`include_ips`, `fqdns`,
  `cidrs`) — identity scanning is explicit opt-in targeting, not a network sweep.

### pyproject.toml [identity] Extras Group
- **D-07:** Add `[identity]` optional extras group after the existing `[dashboard]` group.
  Exact packages and version pins per REQUIREMENTS.md INFRA-03:
  `impacket>=0.13.0,<0.14`, `dnspython[dnssec]>=2.8.0`, `lxml>=6.0`,
  `defusedxml>=0.7.1`, `signxml>=4.4.0`.
- **D-08:** `impacket` must NOT enter core dependencies — it stays in `[identity]` only due
  to pyOpenSSL transitive conflict risk with the core cryptography stack.

### Config Template
- **D-09:** Add a new `# -- Identity connectors (optional) ---` subsection at the end of
  `quirk/config_template.yaml`, after the existing connectors block. The entire section is
  commented out by default — consultants uncomment only the protocol they need. Each target
  field gets a descriptive inline comment explaining the expected value format.

### Claude's Discretion
- Exact helper function signature and naming in `db.py`
- Whether the migration helper is private (`_ensure_columns`) or named per column
- Inline comment verbosity in `config_template.yaml` identity section

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Schema and database
- `quirk/db.py` — `init_db()` function; migration helper added here after `create_all()`
- `quirk/models.py` — `ScanResult` model; existing `*_json = Column(Text, nullable=True)` pattern to follow

### Config infrastructure
- `quirk/config.py` — `ConnectorsCfg` dataclass; `enable_X` flag + `x_targets: list` pattern
- `quirk/config_template.yaml` — existing connectors block format; identity section added at end

### Dependency management
- `pyproject.toml` — existing `[dashboard]` optional extras group; `[identity]` group follows same format

### Requirements (phase scope)
- `.planning/REQUIREMENTS.md` §INFRA-01, INFRA-02, INFRA-03 — full requirement text including exact package versions and success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/models.py` `ScanResult`: Existing `*_scan_json = Column(Text, nullable=True)` columns for ssh_audit, jwt, container, source — new identity columns follow this exact pattern
- `quirk/config.py` `ConnectorsCfg`: Dataclass with `enable_X: bool = False` flags and `x_targets: list = field(default_factory=list)` — identity fields replicate this exactly
- `quirk/db.py` `init_db()`: Startup hook; migration guard is added here after `Base.metadata.create_all(engine)`

### Established Patterns
- Optional dependencies use `[extras-group]` in pyproject.toml; `dashboard` group is the only existing example
- `ConnectorsCfg` uses Python dataclasses with `field(default_factory=list)` for list fields
- Config template uses `# -- Section name ---` subsection headers with inline comments
- No Alembic — schema evolution via raw `ALTER TABLE` executed during `init_db()`

### Integration Points
- `init_db()` in `db.py` is the single startup hook — migration guard attaches here
- `config.py` `AppConfig.from_dict()` at line ~131 unpacks `ConnectorsCfg` from raw YAML — new fields must have Python defaults (won't be in old config.yaml files)
- `config_template.yaml` is bundled in `quirk/` package data; changes appear in `quirk init` output
- Phases 18–20 will import `enable_kerberos`, `enable_saml`, `enable_dnssec` flags from config and read `kerberos_scan_json` etc. from `ScanResult`

</code_context>

<specifics>
## Specific Ideas

- Inspector-first migration pattern recommended over try/except OperationalError — avoids
  using exceptions for control flow; SQLAlchemy `inspect()` is idiomatic for column introspection
- Identity config section should be **fully commented out by default** in the template,
  not just set to `false` — signals to consultants this is optional advanced scanning
- `kerberos_targets`, `saml_targets`, `dnssec_targets` must all have `field(default_factory=list)`
  defaults so loading a v4.1 config.yaml without these fields does not raise a TypeError

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 17-identity-infrastructure*
*Context gathered: 2026-04-08*
