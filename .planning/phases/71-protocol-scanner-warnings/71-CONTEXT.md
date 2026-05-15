# Phase 71: Protocol Scanner WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 14 WARNING-severity audit findings in the protocol-scanner subsystem from the 2026-05-08 audit ledger (`scanners-protocol/WR-01..WR-14`). Internal-contract changes only — no new scan capabilities, no schema changes, no new pip dependencies (defusedxml is already core).

**In scope (mapped to PROTO-NN requirements):**

- **PROTO-01** — `quirk/discovery/coverage.py::calculate_coverage` clamps return to `[0.0, 1.0]`; `quantum_readiness_score` severity comparison normalized case-insensitively (closes WR-01, WR-02)
- **PROTO-02** — Bare `except Exception` swallowing subprocess errors replaced with specific exception handling + stderr logging (closes WR-03)
- **PROTO-03** — `quirk/discovery/nmap_provider.py` default port CSV corrected; `extra_args` validated against character allowlist; `nmap_parser` switched from stdlib `xml.etree.ElementTree` to `defusedxml.ElementTree` to eliminate XXE / billion-laughs surface (closes WR-04, WR-05, WR-06)
- **PROTO-04** — DNSSEC `_parse_dnskeys` `key_bytes` subscript bounded; Kerberos `_probe_kdc_udp` decode errors logged; Kerberos `_build_as_req` nonce uses `secrets.token_bytes`; SAML `_classify_target` JSON parse has byte-size cap (closes WR-07, WR-08, WR-09, WR-10)
- **PROTO-05** — Optional-extras messaging consistent across email/broker/container/source scanners; email/broker `ThreadPoolExecutor max_workers` configurable via new `ScanCfg.motion_concurrency` field; `quirk/discovery/tls_scanner.py` dead duplicate deleted; `target_expander.expand_targets()` dedup stable, CIDR expansion bounded, type confusion resolved (closes WR-11, WR-12, WR-13, WR-14)

**Out of scope (deferred to other phases or explicitly do-not-touch):**

- Cloud-scanner WARNINGs (Phase 72) — `scanners-cloud/WR-01..WR-24`
- CBOM/intelligence/reports WARNINGs (Phase 73) — `cbom-intel-reports/WR-*`
- QRAMM + compliance WARNINGs (Phase 74) — `qramm-compliance/WR-*`
- API/CLI core WARNINGs (Phase 75) — `api-cli-core/WR-*`
- React frontend WARNINGs (Phase 76) — `react-frontend/WR-*`
- All BLOCKER-severity rows (already closed in Phase 69 / Phase 70)
- Any code path not explicitly named in WR-01..WR-14 (see D-08 do-not-touch list below)

</domain>

<decisions>
## Implementation Decisions

### CIDR expansion bound (PROTO-05 / WR-14)

- **D-01 (locked):** `quirk/scanner/target_expander.py::expand_targets()` enforces a `/22` hard cap (1024 hosts) per CIDR. If `ipaddress.ip_network(cidr, strict=False).num_addresses > 1024`, raise `ValueError(f"CIDR {cidr} expands to {n} hosts; refusing to scan more than 1024 hosts per CIDR (split it or use --include-ips)")`. Validate BEFORE iterating `.hosts()` so a misconfigured `/8` doesn't burn memory before failing. Choice rationale: 1024 hosts × ~7 default ports = ~7K endpoint tuples — comfortably within scanner concurrency budgets — while making misconfiguration fail loudly.
- **D-01a (Claude's discretion):** Whether to bound the *aggregate* across all CIDRs (sum across `cfg.targets.cidrs`) or only per-CIDR — researcher to confirm whether any caller already pre-validates. Default to per-CIDR (simpler, matches the audit row's framing).

### ThreadPool concurrency knob (PROTO-05 / WR-12)

- **D-02 (locked):** Add a single `motion_concurrency: int = 50` field to `ScanCfg` (in `quirk/config.py:63`), positioned alongside `tls_concurrency`, `ssh_concurrency`, `fingerprint_concurrency`. Replace all four hardcoded `min(len(tasks), 50)` literals — `quirk/scanner/email_scanner.py:532`, `quirk/scanner/broker_scanner.py:475`, `:574`, `:801` — with `min(len(tasks), cfg.scan.motion_concurrency)`. Default `50` preserves current behavior (no behavior change, just config surface). Naming chosen because email + broker were grouped under the "motion" subsystem in Phase 36/37 (CBOM motion subscore, `[motion]` meta-extra).
- **D-02a (Claude's discretion):** Whether to add a wizard prompt or CLI flag for `motion_concurrency` — defer; the field is YAML-configurable on day one, wizard exposure can come later if operators ask.

### nmap default port CSV (PROTO-03 / WR-04)

- **D-03 (locked):** `quirk/discovery/nmap_provider.py:54` default port set becomes the broadest "consulting-grade" union: composed from `cfg.scan.ports_tls` (canonical TLS ports — currently `443, 8443, 9443, 10443, 5001`) plus `22` (SSH), `80, 8080` (HTTP), `25, 465, 587, 993, 995` (motion email), `88` (Kerberos), `389, 636` (LDAP/LDAPS), `3389` (RDP), `5671` (AMQPS), `9092` (Kafka). The TLS half stays composed from `cfg.scan.ports_tls` so when that list changes the nmap default tracks it; the rest is a fixed constant in `nmap_provider.py`. Port 5001 is preserved (Phase 47 consulting set inherits it).
- **D-03a (Claude's discretion):** Exact representation — single sorted CSV vs. list-then-join — pick whatever fits the existing `_default_nmap_args` style. Researcher to verify final port numbers (e.g., Kafka SSL port 9092 vs. 9094, AMQPS 5671 vs 5672) against project precedent.

### nmap extra_args allowlist (PROTO-03 / WR-05)

- **D-04 (locked):** `quirk/discovery/nmap_provider.py::run_nmap_discovery` validates each token of `extra_args` against the regex `^[A-Za-z0-9._:/=,-]+$` before passing to subprocess. Any token that fails the regex raises `ValueError(f"Unsafe nmap extra arg: {token!r}")` immediately. No quoting / escaping — fail loud. Mirrors the Phase 70 `_SAFE_COL_TYPE_RE` defense-in-depth pattern: it never *should* be reached because all current callers build `extra_args` from validated cfg, but the guard catches future code paths.
- **D-04a (Claude's discretion):** Researcher to confirm whether `extra_args` is `List[str]` or a single shell string today; if string, split on whitespace before regex check (or reject any whitespace).

### nmap XML parser switch (PROTO-03 / WR-06)

- **D-05 (locked):** `quirk/discovery/nmap_parser.py` switches from `xml.etree.ElementTree as ET` to `import defusedxml.ElementTree as ET`. defusedxml is already a core dependency (`pyproject.toml:29` — `defusedxml>=0.7.1`); the switch is a one-line import change that defuses XXE, billion-laughs, and external-DTD surfaces with no runtime config needed (defusedxml's defaults already forbid all dangerous constructs). No need for `forbid_dtd=True` flag — defusedxml.ElementTree has it on by default.

### Coverage clamp (PROTO-01 / WR-01)

- **D-06 (locked):** `quirk/discovery/coverage.py::calculate_coverage` returns `max(0.0, min(1.0, coverage))` at the final return statement. Clamp only — do NOT change the underlying numerator/denominator math (that's a Phase 73 INTEL-03 concern per D-08). Add an inline comment citing WR-01.

### Severity comparison normalization (PROTO-01 / WR-02)

- **D-07 (locked):** `quantum_readiness_score` (researcher to locate exact module — likely `quirk/intelligence/score.py` or similar) severity comparison uses `.upper()` for both LHS and RHS before comparison: `if str(severity).upper() in ("CRITICAL", "HIGH"):` (or analogous). Do NOT use `.casefold()` — project precedent (Phase 60, Phase 64.1, audit ledger row text) uses uppercase severity literals throughout.

### Bare except narrowing (PROTO-02 + PROTO-04)

- **D-08 (locked):** Only narrow the bare `except` clauses that WR-03, WR-08, WR-10 specifically point at:
  - **WR-03** — protocol-scanner subprocess `except Exception` (researcher locates exact site; likely `quirk/scanner/fingerprint.py` or another scanner that shells out)
  - **WR-08** — `quirk/scanner/kerberos_scanner.py::_probe_kdc_udp` decode `except`
  - **WR-10** — `quirk/scanner/saml_scanner.py::_classify_target` JSON parse (size cap applies here too)

  Any *other* broad `except Exception:` in scanner code stays for Phase 75 (api-cli-core WARNINGs) or its own follow-up. Mirrors Phase 70 D-07 boundary: one row, one fix, one commit.

### Kerberos nonce RNG (PROTO-04 / WR-09)

- **D-09 (locked):** `quirk/scanner/kerberos_scanner.py::_build_as_req` nonce switches from whatever non-cryptographic source it currently uses (likely `random.randint(...)`) to `int.from_bytes(secrets.token_bytes(4), "big")` for a 32-bit nonce, or `secrets.randbits(32)` if Python's stdlib makes it cleaner. Researcher to pick the form that fits the existing call site idiom; both produce cryptographically strong nonces.

### SAML JSON byte cap (PROTO-04 / WR-10)

- **D-10 (locked):** `quirk/scanner/saml_scanner.py::_classify_target` enforces a `MAX_SAML_JSON_BYTES = 1_048_576` (1 MiB) cap before `json.loads(...)`. If `len(payload) > MAX_SAML_JSON_BYTES`, log a WARNING and return the same fallback path as a parse failure. 1 MiB is generous for SAML metadata (typical IdP metadata is ~50 KiB) but bounds memory exposure from a malicious endpoint serving multi-GB JSON.

### DNSSEC key_bytes subscript bound (PROTO-04 / WR-07)

- **D-11 (locked):** `quirk/scanner/dnssec_scanner.py::_parse_dnskeys` validates `len(key_bytes) >= expected_min_length` for the algorithm before any `key_bytes[i]` subscript. Researcher to enumerate the algorithm-specific minimums (RSA / ECDSA / Ed25519 / Ed448) from RFC 4034 / RFC 6605 / RFC 8080. On a too-short key, log a WARNING and skip the record (do not raise — DNSSEC scans should degrade gracefully on malformed records, not abort).

### Optional-extras messaging consistency (PROTO-05 / WR-11)

- **D-12 (locked):** Standardize the optional-dep import-error message format across `email_scanner.py`, `broker_scanner.py`, `container_scanner.py`, `source_scanner.py` to match the established Phase 41 / Phase 45 idiom (project precedent: `RuntimeError("X is not installed — pip install quirk[Y] to enable Z scanning")`). Researcher to verify the exact format from one of those phases' SUMMARY.md files; planner unifies all four sites in a single commit.

### discovery/tls_scanner.py deletion (PROTO-05 / WR-13)

- **D-13 (locked):** Delete `quirk/discovery/tls_scanner.py` outright. Confirmed dead duplicate of `quirk/scanner/tls_scanner.py`. Researcher must grep for any imports of `quirk.discovery.tls_scanner` across the codebase BEFORE deletion; if any are found, either redirect them to `quirk.scanner.tls_scanner` first (own commit) or surface the conflict for human resolution.

### target_expander dedup stability + type confusion (PROTO-05 / WR-14)

- **D-14 (locked):** `expand_targets()` returns a **stable-deduplicated** list (preserve first-seen order; use a `dict` or `seen: set` accumulator, not `list(set(...))` which loses order). Type-confusion fix: normalize all IP comparisons to `str(ipaddress.ip_address(x))` so `cfg.targets.exclude_ips` works whether entries are `str` or `ipaddress.IPv4Address` instances. Same normalization for `include_ips`.

### Phase-71 do-not-touch list

- **D-15 (locked):** Explicitly out of scope for Phase 71:
  - Other bare `except` clauses outside the WR-03/08/10 sites (deferred to Phase 75)
  - Any change to `quirk/scanner/tls_scanner.py` — no WR row points at it; incidental edits would expand the change surface without audit justification
  - Email/broker `ThreadPoolExecutor` lifecycle restructuring — only swap the literal 50 for the new ScanCfg knob; no per-host parallelism model changes
  - Coverage formula numerator/denominator — only clamp the return value (formula belongs to Phase 73 INTEL-03)

</decisions>

<canonical_refs>
## Canonical References (downstream agents MUST read)

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — audit ledger; rows `scanners-protocol/WR-01..WR-14` are the source of truth for what to fix and what evidence to record. Rows must be flipped to `Phase 71 | [x] closed` with per-row evidence (mirrors Phase 70 / Phase 69 pattern).
- `.planning/REQUIREMENTS.md` lines 26–30 — `PROTO-01..PROTO-05` requirement statements; one-to-many mapping to WR rows (defined in each requirement's `closes` clause).
- `.planning/ROADMAP.md` Phase 71 section (line ~1493) — Goal + 5 Success Criteria — these are gating, not aspirational.
- `.planning/phases/70-deferred-blockers-api-qramm-model/70-CONTEXT.md` — Phase 70 precedent for the audit-row-flip pattern, the `_SAFE_COL_TYPE_RE` defense-in-depth allowlist style (D-04 mirrors it), and the do-not-touch boundary discipline (D-08, D-15 mirror Phase 70 D-07).
- `.planning/phases/69-deferred-blockers-scanner-cloud/` — Phase 69 SUMMARY.md files for the established WR-row evidence format and BLOCKER-closure commit-message style.
- `quirk/discovery/coverage.py` — `calculate_coverage` clamp site (PROTO-01).
- `quirk/discovery/nmap_provider.py` line 54 — current default port CSV (PROTO-03).
- `quirk/discovery/nmap_parser.py` — XML parser to switch to defusedxml (PROTO-03).
- `quirk/scanner/dnssec_scanner.py`, `kerberos_scanner.py`, `saml_scanner.py` — PROTO-04 fix sites.
- `quirk/scanner/email_scanner.py:532`, `quirk/scanner/broker_scanner.py:{475,574,801}` — hardcoded `max_workers=50` sites (PROTO-05).
- `quirk/scanner/target_expander.py` — `expand_targets()` rewrite (PROTO-05 / WR-14).
- `quirk/discovery/tls_scanner.py` — DELETE candidate (PROTO-05 / WR-13).
- `quirk/config.py:63` — `ScanCfg` class; new `motion_concurrency: int = 50` field (PROTO-05 / WR-12).
- `pyproject.toml:29` — confirms `defusedxml>=0.7.1` is already a core dep, no install changes needed.

</canonical_refs>

<code_context>
## Reusable Assets / Patterns (from codebase scout)

- **`_SAFE_COL_TYPE_RE` defense-in-depth pattern** (Phase 70, `quirk/db.py:34`) — module-level regex constant + early `if not RE.match(x): raise ValueError(...)` guard. D-04 (nmap extra_args allowlist) follows this shape directly.
- **SQLAlchemy connect-event listener idiom** (Phase 70, `quirk/db.py`) — irrelevant here, but the *pattern of registering a single module-level enforcement hook* is analogous to how the new `target_expander` bound is enforced (one validation site for many call sites).
- **Existing per-subsystem concurrency naming** (`quirk/config.py:63`) — `tls_concurrency=150`, `ssh_concurrency=100`, `fingerprint_concurrency=200`. New `motion_concurrency=50` slots in alongside.
- **Existing logger.warning idiom** (`quirk/dashboard/api/routes/scan.py:46` post-Phase 70, `quirk/dashboard/api/routes/qramm.py`) — `logger = logging.getLogger(__name__)` at module scope, `logger.warning("X failed for %r: %s", target, e)`. Use this format for all new WARNING logs in PROTO-02, PROTO-04 narrowing.
- **Existing optional-extras error format** (Phase 41 / Phase 45 precedent) — `RuntimeError("X is not installed — pip install quirk[Y] to enable Z")`. Researcher to copy verbatim from one of those phases' SUMMARY.md.
- **Phase 47 consulting port set** — somewhere in the codebase Phase 47 added a "consulting-grade" port set; researcher should locate it as a sanity check on the D-03 union (the new nmap default may already overlap with that constant — if so, reuse).

</code_context>

<test_strategy>
## Test Approach (high-level — planner refines)

- **One test module per PROTO requirement** (5 modules) — mirrors Phase 70 plan-per-requirement granularity. Each module covers all WR rows under that requirement.
- **RED-then-GREEN per fix** — every guard / clamp / narrowing gets at least one test that proves the failing input is now handled. For the nmap allowlist (D-04), include a parametrized table of malicious tokens (`; rm -rf /`, `$(whoami)`, backtick injection, etc.).
- **Defense-in-depth tests** for D-04 + D-01 should assert the `ValueError` message format so future regressions on the user-facing error are caught.
- **Audit ledger flip** verified by integration: a test or a docs-update commit that asserts all 14 WR-NN rows show `Phase 71 | [x] closed` in `AUDIT-TASKS.md` (Phase 70 precedent — see `tests/test_db_migrations.py` audit-row assertions).
- **No new UAT-NN-NN cases needed** — these are internal contracts, no user-visible CLI/output change. Follow Phase 70 wrap pattern: prepend a "Phase 71 wrap" note to `docs/UAT-SERIES.md` `Last Updated:` preamble describing the contract changes.

</test_strategy>

<deferred>
## Deferred Ideas (noted, not in scope)

- **Wizard prompt for `motion_concurrency`** (D-02a) — defer until operators ask; YAML config covers day-one needs.
- **Aggregate CIDR bound across `cfg.targets.cidrs`** (D-01a) — defer to a follow-up phase if operators ever hit it; per-CIDR bound covers the audit row's framing.
- **Refactoring email/broker `ThreadPoolExecutor` lifecycle** (D-15 explicit non-goal) — if a future scaling pass calls for it, that's its own phase.
- **Coverage formula correctness review** — Phase 73 INTEL-03 already covers some of this; if more is needed, capture as a future INTEL-* requirement.

</deferred>
