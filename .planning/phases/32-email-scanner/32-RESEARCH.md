# Phase 32: Email Scanner - Research

**Researched:** 2026-04-27
**Domain:** Email protocol TLS scanning — SMTP/IMAP/POP3 across 7 ports, sslyze STARTTLS, stdlib fallback, findings composition, chaos lab
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Reuse the existing TLS target list verbatim — every host already passed via `--target` / target file is also probed on the 7 email ports.
- **D-02:** No new CLI flag for email targets. Scanner consumes the same target iterator that `scan_tls_targets` consumes, mirroring the v4.2 dnssec_scanner integration pattern.
- **D-03:** `CONNECTION_REFUSED` per port is non-fatal and silent (logged at DEBUG only) — port 25 egress is commonly blocked on cloud VMs.
- **D-04 (deferred):** MX autodiscovery is not in scope for Phase 32.
- **D-05:** Email scanning runs by default in the `standard` and `deep` profiles only. Excluded from `quick`.
- **D-06:** `quirk/engine/profiles.py:apply_profile()` must flip a config flag (e.g., `cfg.scanners.email_enabled = True`) for `standard` and `deep`. `quick` keeps it False.
- **D-07:** Adding `--include-email` / `--no-email` override flags is Claude's discretion during planning — wire them only if the existing `apply_profile` pattern already exposes scanner-level overrides.
- **D-08:** Fallback triggered when: sslyze raises an uncaught exception; `ServerScanResult.scan_status` is `ERROR_*`; every `ScanCommandAttempt` reports `ERROR_*`.
- **D-09:** Empty/None cipher results without explicit error = "TLS not supported", NOT fallback-triggering.
- **D-10:** Fallback function follows `tls_scanner.py:329 _scan_one_fallback` shape — extract TLS version + cipher + cert via `getpeercert(binary_form=True)` + existing `_pubkey_info()` helper.
- **D-11:** Findings are layered: port-25 endpoint with weak RSA cipher emits BOTH `starttls-downgrade-risk` MEDIUM and `weak-cipher` HIGH.
- **D-12:** Each finding carries its own `finding_id` (currently: distinct `title` + `recommendation` key in `risk_engine.py`). Dashboard de-duplication by title, not by endpoint.
- **D-13:** Non-PFS ECDHE without TLS 1.3 = MEDIUM (per EMAIL-09 verbatim). No reclassification.
- **D-14:** New `labs/email/` directory — matches v4.3 convention.
- **D-15:** Each service (Postfix, Dovecot) gets its own self-signed RSA-2048 cert under `labs/email/certs/`. Do NOT reuse `certs/scenarios/`.
- **D-16:** Cert generation is reproducible via `labs/email/Makefile` `certs` target.
- **D-17:** Compose profile name = `email`. Lives in existing `labs/` compose structure.

### Claude's Discretion

- Exact internal helper organization inside `email_scanner.py` (one function per protocol vs. shared dispatcher).
- Logging verbosity per port-refused / per-fallback event — follow existing scanner logging conventions.
- `pyproject.toml [motion]` extras content for Phase 32 (likely empty or sslyze-only).
- Whether `email_scan_json` payload uses flat or per-port nested JSON structure.
- Whether to add `--include-email` / `--no-email` override flags during planning.

### Deferred Ideas (OUT OF SCOPE)

- MX autodiscovery from a domain (`target_expander.py`, future v4.5).
- Active STARTTLS-stripping detection (agentless scanner constraint — document in finding description).
- Broker scanning (Phase 33), motion subscore wiring (Phase 34), CBOM integration (Phase 35), dashboard motion tab (Phase 36).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRUCT-01 | All new scanners accept `session_start` parameter — no per-scanner `datetime.now()` calls | `dnssec_scanner.py` pattern: `now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)` |
| STRUCT-02 | All new `[motion]` extras group entries declared in `pyproject.toml` at plan time | `[project.optional-dependencies]` table in pyproject.toml; `[motion]` group does not yet exist |
| STRUCT-03 | Each phase plan must include a `pyproject.toml` diff as required deliverable if deps change | Phase 32 adds no new runtime deps (sslyze already optional; stdlib used for fallback) — diff = `[motion]` group declaration |
| EMAIL-00 | SQLite `Scan` model gains `email_scan_json` TEXT NULL column following `kerberos_scan_json`/`dat_scan_json` pattern | Two-part work: add Column to `quirk/models.py`; add `_ensure_email_columns()` migration in `quirk/db.py` |
| EMAIL-01 | Scanner probes SMTP STARTTLS on port 25 and 587 using sslyze `ProtocolWithOpportunisticTlsEnum.SMTP` | API confirmed in existing research doc; same `ServerNetworkConfiguration` as existing `_scan_one_sslyze()` |
| EMAIL-02 | Scanner probes SMTPS implicit TLS on port 465 using existing `_scan_one_sslyze()` path | Direct re-use of existing `tls_scanner.py:scan_one()`; no STARTTLS parameter needed |
| EMAIL-03 | Scanner probes IMAP STARTTLS on port 143 using `ProtocolWithOpportunisticTlsEnum.IMAP` | Same pattern as EMAIL-01 with IMAP enum value |
| EMAIL-04 | Scanner probes IMAPS implicit TLS on port 993 using direct-TLS path | Same as EMAIL-02 for IMAPS |
| EMAIL-05 | Scanner probes POP3 STARTTLS on port 110 using `ProtocolWithOpportunisticTlsEnum.POP3` | Same pattern as EMAIL-01 with POP3 enum value |
| EMAIL-06 | Scanner probes POP3S implicit TLS on port 995 | Same as EMAIL-02 for POP3S |
| EMAIL-07 | Stdlib fallback (`smtplib`/`imaplib`/`poplib`) when sslyze fails; extracts TLS version, cipher, cert via underlying SSLSocket | All five fallback patterns documented in existing research doc; use `_pubkey_info()` from `tls_scanner.py` |
| EMAIL-08 | Port-25 STARTTLS endpoints that successfully negotiate TLS emit a static MEDIUM `starttls-downgrade-risk` finding | New finding in `risk_engine.py` or in `email_scanner.py` findings list; emitted in addition to cipher findings |
| EMAIL-09 | Weak ciphers (`TLS_RSA_WITH_*`, 3DES, RC4) = HIGH; Non-PFS ECDHE without TLS 1.3 = MEDIUM | Compose with existing `_is_weak()` / `_is_pfs()` logic from `tls_scanner.py` |
| EMAIL-10 | `ep.service_detail` format: `"SMTP-STARTTLS:587"`, `"SMTPS:465"`, `"IMAPS:993"`, `"POP3S:995"` etc. | New `EMAIL_PORT_LABELS` map in `email_scanner.py`; set `ep.service_detail` and `ep.protocol` before returning |
| EMAIL-11 | New `email` Docker Compose profile — Postfix + Dovecot (ubuntu:22.04), weak TLS (TLS 1.1 min, RSA non-PFS, RSA-2048 self-signed), ports 30025/30465/30587/30143/30993/30110/30995 | Chaos lab in `labs/email/`; Makefile for cert generation |
| EMAIL-12 | `labs/email/expected_results.md` documents expected findings for chaos lab profile | Template from `labs/vault/expected_results.md` |
</phase_requirements>

---

## Summary

Phase 32 delivers `quirk/scanner/email_scanner.py` — a new scanner module following the canonical 4-function shape established in `tls_scanner.py` and carried forward through every scanner since v3.7. The scanner probes all 7 standard email protocol ports using sslyze's native STARTTLS support (`ProtocolWithOpportunisticTlsEnum.SMTP/IMAP/POP3`) for opportunistic-TLS ports and the existing direct-TLS sslyze path for implicit-TLS ports (465, 993, 995). When sslyze fails, it falls back to the appropriate stdlib module (`smtplib`, `imaplib`, `poplib`) to perform STARTTLS negotiation and extracts TLS version, cipher, and cert from the underlying `ssl.SSLSocket`.

The scanner is integrated in `run_scan.py` after the existing DNSSEC/Kerberos scanners — gated on `cfg.connectors.email_enabled`, which `apply_profile()` sets True for `standard` and `deep` profiles only. Results are stored in a new `email_scan_json` TEXT column on `crypto_endpoints`, following the exact migration pattern used for `kerberos_scan_json` (inspector-first ALTER TABLE). Email-specific findings (`starttls-downgrade-risk` MEDIUM on port 25, `weak-cipher` HIGH for RSA key-exchange suites) are emitted as additional findings alongside the existing TLS findings already produced by `evaluate_endpoints()` in `risk_engine.py`.

The chaos lab is a single Postfix+Dovecot container on `ubuntu:22.04` with deliberately weak TLS (RSA-2048 self-signed cert, non-PFS RSA cipher suites, TLS 1.2 as the practical minimum due to OpenSSL 3.x restrictions on the scanner host). The lab lives in `labs/email/` with a Makefile cert target and uses Docker Compose profile `email` on the port range 30025–30995.

**Primary recommendation:** Implement `email_scanner.py` by lifting the 4-function skeleton from `tls_scanner.py`, parameterizing it with the `EMAIL_PORTS` table, and adding the two email-specific findings as a post-processing step on the returned endpoint list before they are aggregated into `run_scan.py`'s main `endpoints` list.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TLS probe (7 email ports) | Scanner module (`email_scanner.py`) | sslyze / stdlib fallback | All network probing lives in scanner modules; sslyze is the first-choice prober |
| STARTTLS negotiation | sslyze (`ProtocolWithOpportunisticTlsEnum`) | stdlib (`smtplib`/`imaplib`/`poplib`) | sslyze handles the protocol-level EHLO/CAPABILITY/STLS exchange; stdlib is the fallback |
| Result persistence (`email_scan_json`) | `quirk/models.py` + `quirk/db.py` | `run_scan.py` (session.add) | Column declaration in model, migration in db.py, write happens in scanner before `run_scan.py` aggregates |
| Findings (weak-cipher, starttls-downgrade-risk) | `email_scanner.py` | `risk_engine.py` integration | Email-specific findings are best emitted close to the scan result; `evaluate_endpoints()` handles generic TLS findings |
| Profile-gating (`email_enabled`) | `quirk/engine/profiles.py` | `quirk/config.py` (ConnectorsCfg) | Profile logic lives in `apply_profile()`; config carries the flag |
| Chaos lab | `labs/email/` | `quantum-chaos-enterprise-lab/docker-compose.yml` (profile) | Lab files in `labs/email/`; compose profile `email` added to existing compose file |
| Target list reuse | `run_scan.py` | `email_scanner.py` | `run_scan.py` passes the same host list used for TLS; scanner expands to 7 ports internally |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sslyze | optional (already in codebase) | Primary TLS probe — STARTTLS + cipher enumeration | Existing scanner uses it; `ProtocolWithOpportunisticTlsEnum` handles SMTP/IMAP/POP3 natively |
| smtplib | stdlib | SMTP STARTTLS fallback | No dep install; handles EHLO negotiation correctly |
| imaplib | stdlib | IMAP STARTTLS + IMAPS fallback | No dep install; `IMAP4.starttls()` and `IMAP4_SSL` |
| poplib | stdlib | POP3 STARTTLS + POP3S fallback | No dep install; `POP3.stls()` and `POP3_SSL` |
| ssl | stdlib | SSLSocket extraction in fallback | Used in existing `_scan_one_fallback()` |
| cryptography | >=44.0 (pinned) | x509 cert parsing from DER bytes | Already in core deps; `x509.load_der_x509_certificate()` |

[VERIFIED: codebase grep — sslyze used as optional import in tls_scanner.py; cryptography pinned in pyproject.toml]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| concurrent.futures.ThreadPoolExecutor | stdlib | Port-level parallelism | Each (host, port) pair is an independent task; same pattern as `scan_tls_targets` |

### No New Dependencies Required

[VERIFIED: codebase inspection of pyproject.toml]

sslyze is already an optional import in `tls_scanner.py` — the email scanner uses the same soft-import guard pattern. The stdlib fallback uses only `smtplib`, `imaplib`, `poplib`, and `ssl` — all in the Python standard library. Phase 32 adds no new runtime packages. The `[motion]` extras group declared in STRUCT-02 will be an empty group or contain only `sslyze` if the team decides to formalize it as an optional dep.

**pyproject.toml diff (STRUCT-02/STRUCT-03):**
```toml
[project.optional-dependencies]
# ... existing groups ...
motion = [
    # sslyze is used optionally (soft import); no hard dep required for email-only scanning
    # Broker extras (kafka-python, etc.) added in Phase 33
]
```

---

## Architecture Patterns

### System Architecture Diagram

```
run_scan.py:do_scan()
  │
  ├─ [existing] fingerprint → classify hosts
  ├─ [existing] scan_tls_targets(cfg, tls_targets, ...)
  ├─ [existing] scan_ssh_targets / scan_dnssec_targets / scan_kerberos_targets ...
  │
  ├─ [NEW Phase 32] if cfg.connectors.email_enabled:
  │     email_endpoints = scan_email_targets(
  │         hosts=unique_hosts_from_targets,
  │         timeout=cfg.scan.timeout_seconds,
  │         logger=logger,
  │         session_start=session_start,
  │     )
  │
  └─ endpoints = [...all_existing... + email_endpoints]
       │
       └─ evaluate_endpoints(cfg, endpoints)  ← risk_engine.py
            │
            └─ write_reports / db_persist

scan_email_targets(hosts, timeout, logger, session_start)
  │
  for each host × EMAIL_PORTS (7 ports):
  │   scan_one_email(host, port, port_config, timeout, logger, session_start)
  │     │
  │     ├─ _scan_one_sslyze_email(host, port, starttls_enum, timeout, logger)
  │     │   └─ sslyze ServerScanRequest (tls_opportunistic_encryption=starttls_enum or None)
  │     │   └─ Returns CryptoEndpoint or None on failure
  │     │
  │     ├─ if None → _scan_one_fallback_email(host, port, protocol_mode, timeout, logger)
  │     │   └─ smtplib.SMTP / imaplib.IMAP4 / poplib.POP3 + STARTTLS
  │     │   └─ ssl.SSLSocket.version() + cipher() + getpeercert(binary_form=True)
  │     │   └─ _pubkey_info() + x509.load_der_x509_certificate()
  │     │
  │     └─ Sets ep.protocol, ep.service_detail, ep.email_scan_json
  │         + emits email-specific findings list
  │
  └─ Returns List[CryptoEndpoint]  (one per successful port probe)
```

### Recommended Project Structure

```
quirk/scanner/
├── tls_scanner.py        # existing — canonical pattern template
├── dnssec_scanner.py     # existing — session_start pattern template
├── email_scanner.py      # NEW Phase 32
└── ...

quirk/
├── config.py             # add email_enabled field to ConnectorsCfg
├── models.py             # add email_scan_json Column
├── db.py                 # add _ensure_email_columns() + call in init_db()
└── engine/
    └── profiles.py       # add email_enabled flag to apply_profile()

labs/email/
├── Makefile              # certs target + up/down targets
├── Dockerfile            # ubuntu:22.04, Postfix + Dovecot
├── postfix/
│   ├── main.cf
│   └── master.cf
├── dovecot/
│   └── 10-ssl.conf
├── certs/                # generated by Makefile (not committed)
│   ├── generate-email-certs.sh
│   ├── postfix.crt
│   ├── postfix.key
│   ├── dovecot.crt
│   └── dovecot.key
└── expected_results.md

quantum-chaos-enterprise-lab/docker-compose.yml  # add `email` profile services
```

### Pattern 1: 4-Function Scanner Shape

**What:** Every scanner module exposes exactly four functions: `_scan_one_<api>`, `_scan_one_fallback`, `scan_one`, `scan_<surface>_targets`.
**When to use:** Always — this is the project-locked shape.

```python
# Source: quirk/scanner/tls_scanner.py (lines 103, 329, 427, 452)

EMAIL_PORTS = [
    # (port, protocol_label, service_detail_prefix, starttls_enum_or_None)
    (25,  "SMTP-STARTTLS", "SMTP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.SMTP),
    (465, "SMTPS",         "SMTPS",          None),   # implicit TLS
    (587, "SMTP-STARTTLS", "SMTP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.SMTP),
    (143, "IMAP-STARTTLS", "IMAP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.IMAP),
    (993, "IMAPS",         "IMAPS",          None),   # implicit TLS
    (110, "POP3-STARTTLS", "POP3-STARTTLS",  ProtocolWithOpportunisticTlsEnum.POP3),
    (995, "POP3S",         "POP3S",          None),   # implicit TLS
]

def _scan_one_sslyze_email(
    host: str, port: int, starttls_enum, timeout: int, logger=None
) -> Optional[CryptoEndpoint]:
    """Primary path — sslyze with optional STARTTLS param."""
    # starttls_enum is None for implicit TLS ports (465, 993, 995)
    net_cfg = ServerNetworkConfiguration(
        tls_server_name_indication=host,
        tls_opportunistic_encryption=starttls_enum,  # None = direct TLS
        network_timeout=timeout,
    )
    # ... same result parsing as tls_scanner._scan_one_sslyze() ...

def _scan_one_fallback_email(
    host: str, port: int, protocol_label: str, timeout: int, logger=None
) -> CryptoEndpoint:
    """Stdlib fallback when sslyze fails."""
    ep = CryptoEndpoint(host=host, port=port, ...)
    try:
        if protocol_label == "SMTP-STARTTLS":
            tls_ver, cipher, der = _fallback_smtp_starttls(host, port, timeout)
        elif protocol_label == "IMAP-STARTTLS":
            tls_ver, cipher, der = _fallback_imap_starttls(host, port, timeout)
        elif protocol_label == "POP3-STARTTLS":
            tls_ver, cipher, der = _fallback_pop3_starttls(host, port, timeout)
        elif protocol_label == "SMTPS":
            tls_ver, cipher, der = _fallback_implicit_tls(host, port, timeout)
        # ... etc.
        # Extract cert fields using existing _pubkey_info() from tls_scanner.py
    except ConnectionRefusedError:
        ep.tls_blocker_reason = "CONNECTION_REFUSED"  # silent per D-03
    except Exception as e:
        ep.scan_error = str(e)
    return ep

def scan_one_email(
    host: str, port: int, protocol_label: str, starttls_enum, timeout: int,
    logger=None, session_start=None,
) -> CryptoEndpoint:
    """Try sslyze → fallback. Sets ep.protocol, ep.service_detail, ep.scanned_at."""
    ep = _scan_one_sslyze_email(host, port, starttls_enum, timeout, logger)
    if ep is None:
        ep = _scan_one_fallback_email(host, port, protocol_label, timeout, logger)
    ep.protocol = protocol_label
    ep.service_detail = f"{protocol_label}:{port}"
    ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return ep

def scan_email_targets(
    hosts: List[str], timeout: int, logger=None, session_start=None
) -> List[CryptoEndpoint]:
    """Expand hosts × EMAIL_PORTS and probe in parallel."""
    results = []
    tasks = [
        (host, port, label, starttls_enum)
        for host in hosts
        for (port, label, _, starttls_enum) in EMAIL_PORTS
    ]
    with ThreadPoolExecutor(max_workers=min(len(tasks), 50)) as ex:
        futures = {
            ex.submit(scan_one_email, host, port, label, starttls_enum, timeout, logger, session_start): (host, port)
            for host, port, label, starttls_enum in tasks
        }
        for f in as_completed(futures):
            results.append(f.result())
    return results
```

[VERIFIED: tls_scanner.py lines 103, 329, 427, 452 — exact function signatures confirmed by codebase read]

### Pattern 2: session_start Plumbing (STRUCT-01)

**What:** The shared `session_start` datetime flows from `run_scan.py` → scanner → each endpoint's `scanned_at`.
**When to use:** All new scanners — non-negotiable.

```python
# Source: quirk/scanner/dnssec_scanner.py line 188
now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
ep.scanned_at = now
```

[VERIFIED: dnssec_scanner.py line 188 — exact pattern confirmed]

### Pattern 3: DB Migration (EMAIL-00)

**What:** Add new TEXT NULL column via inspector-first ALTER TABLE migration.
**When to use:** Every new `*_scan_json` column.

```python
# Source: quirk/db.py lines 42-63 (_ensure_identity_columns pattern)

_EMAIL_COLUMNS = ["email_scan_json"]

def _ensure_email_columns(engine) -> None:
    """Add v4.4 email scanner column (email_scan_json TEXT) if absent (idempotent)."""
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _EMAIL_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()

# In init_db(): call after existing _ensure_v43_columns()
_ensure_email_columns(engine)
```

[VERIFIED: quirk/db.py lines 42-63, 87-128 — pattern confirmed by codebase read]

### Pattern 4: Profile-Gating

**What:** Scanner flags live on `cfg.connectors` (not `cfg.scanners` as CONTEXT.md notes — see below). Profile sets flag for standard/deep, leaves False for quick.
**When to use:** Every scanner that should be profile-aware.

```python
# Source: quirk/engine/profiles.py + quirk/config.py

# In ConnectorsCfg (quirk/config.py):
enable_email: bool = False

# In apply_profile (quirk/engine/profiles.py):
if p in ("standard", "deep"):
    if getattr(cfg.connectors, "enable_email", None) is None:
        cfg.connectors.enable_email = True
# quick: leave enable_email = False

# In run_scan.py (after DNSSEC/Kerberos blocks):
if cfg.connectors.enable_email:
    email_endpoints = scan_email_targets(
        hosts=[h for h, _ in targets],  # unique hosts from tls_targets
        timeout=cfg.scan.timeout_seconds,
        logger=logger,
        session_start=session_start,
    )
```

**Important correction from CONTEXT.md:** D-06 mentions `cfg.scanners.email_enabled` but the codebase uses `cfg.connectors.*` for all scanner flags (confirmed: `enable_dnssec`, `enable_kerberos`, `enable_saml` all live in `ConnectorsCfg`). The planner MUST use `cfg.connectors.enable_email`.

[VERIFIED: quirk/config.py lines 62-69 — `enable_dnssec` etc. are in ConnectorsCfg]

### Pattern 5: Findings Emission (EMAIL-08 / EMAIL-09)

**What:** Email-specific findings (STARTTLS downgrade risk, weak cipher) are new finding types not yet in `risk_engine.py`. They should be emitted inside `email_scanner.py` as a separate findings list attached to each endpoint, OR added as new cases in `evaluate_endpoints()`.

**Recommended approach:** Add new `evaluate_email_endpoints()` function in `risk_engine.py` (or inline in `email_scanner.py` then merge). The `_dedupe_findings()` key is `(host, port, title, recommendation)` — two different titles = two separate findings per endpoint.

```python
# New finding shape for EMAIL-08:
{
    "severity": "MEDIUM",
    "host": host,
    "port": 25,
    "title": "STARTTLS downgrade risk on SMTP",
    "recommendation": (
        "STARTTLS (opportunistic TLS) is susceptible to stripping attacks that "
        "cannot be detected by an agentless scanner. An attacker in-path can "
        "suppress the STARTTLS capability advertisement, forcing plaintext delivery. "
        "Enforce MTA-STS (RFC 8461) or DANE (RFC 7672) to prevent stripping."
    ),
}

# New finding shape for EMAIL-09 (weak RSA key exchange):
{
    "severity": "HIGH",
    "host": host,
    "port": port,
    "title": "Weak cipher suite on email TLS endpoint",
    "recommendation": (
        "TLS_RSA_WITH_* suites use RSA key exchange (no forward secrecy) and are "
        "quantum-vulnerable. Disable non-PFS suites and require ECDHE or TLS 1.3 "
        "cipher suites across all email protocol ports."
    ),
}

# EMAIL-09 MEDIUM (non-PFS ECDHE without TLS 1.3):
{
    "severity": "MEDIUM",
    "host": host,
    "port": port,
    "title": "Non-PFS cipher suite on email TLS endpoint",
    "recommendation": (
        "ECDHE without TLS 1.3 provides forward secrecy but remains quantum-vulnerable "
        "via Shor's algorithm. Prefer TLS 1.3 AEAD suites (AES-GCM, ChaCha20-Poly1305) "
        "and plan migration to post-quantum key encapsulation."
    ),
}
```

[VERIFIED: risk_engine.py lines 165-191 — `_dedupe_findings()` key and finding dict shape confirmed]

### Anti-Patterns to Avoid

- **`cfg.scanners.email_enabled`:** The CONTEXT.md uses this shorthand, but the real config namespace is `cfg.connectors`. Do not create a `cfg.scanners` namespace — it doesn't exist in `quirk/config.py`.
- **Calling `datetime.now()` inside the scanner:** All timestamps must use the shared `session_start` parameter (STRUCT-01/ISSUE-3 pattern).
- **Reusing `certs/scenarios/` CA for the chaos lab:** Keep `labs/email/certs/` decoupled (D-15).
- **Running `enumerate_tls_capabilities()` in the email fallback:** The `_scan_one_fallback` in `tls_scanner.py` calls `enumerate_tls_capabilities()` after handshake. For the email scanner fallback this adds scan time and the function is designed for direct-TLS. Skip it for the email fallback — record what the single handshake returns.
- **Emitting `starttls-downgrade-risk` on port 587:** The requirement (EMAIL-08) specifies port 25 only. Port 587 uses mandatory STARTTLS (MSA) which is a different risk profile. The finding is port-25-specific.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SMTP STARTTLS negotiation | Custom socket SMTP state machine | `smtplib.SMTP + starttls()` | stdlib handles 250-STARTTLS advertisement, EHLO, capability parsing |
| IMAP STARTTLS negotiation | Custom socket IMAP state machine | `imaplib.IMAP4 + starttls()` | stdlib handles CAPABILITY response, STARTTLS command |
| POP3 STARTTLS negotiation | Custom socket POP3 state machine | `poplib.POP3 + stls()` | stdlib handles CAPA response, STLS command |
| Full TLS cipher enumeration | Custom cipher enumeration loop | sslyze `ScanCommand.TLS_1_*_CIPHER_SUITES` | sslyze probes all versions; `enumerate_tls_capabilities()` exists for fallback but is not needed for email fallback |
| Cert field extraction | Custom ASN.1 DER parser | `x509.load_der_x509_certificate()` + `_pubkey_info()` (tls_scanner.py) | All helpers already exist and are tested |
| Deduplicated findings | Custom finding registry | `_dedupe_findings()` in `risk_engine.py` | Existing function; layered findings (D-11) survive dedup because titles differ |

---

## Runtime State Inventory

> Phase 32 is a greenfield scanner addition — no rename/refactor. Omitting this section.

---

## Common Pitfalls

### Pitfall 1: `cfg.scanners` vs `cfg.connectors`

**What goes wrong:** CONTEXT.md D-06 says "`cfg.scanners.email_enabled`" but no such namespace exists. The code uses `cfg.connectors.enable_email`.
**Why it happens:** The CONTEXT.md was written at a higher level of abstraction.
**How to avoid:** Check `quirk/config.py` — all scanner enable flags (`enable_dnssec`, `enable_kerberos`, etc.) live in `ConnectorsCfg`.
**Warning signs:** `AttributeError: 'AppConfig' object has no attribute 'scanners'` at runtime.

### Pitfall 2: smtplib socket access after STARTTLS

**What goes wrong:** After `smtp.starttls()`, attempting to access `smtp.sock` or `smtp.sock.getpeercert()` raises `AttributeError` on some Python versions / OS combinations.
**Why it happens:** `smtplib` wraps the socket in-place as an `ssl.SSLSocket`, but the attribute name can differ.
**How to avoid:** Use `smtp.sock` as primary; fall back to `smtp.file._sock` if `smtp.sock` is not the SSLSocket. Always check `isinstance(smtp.sock, ssl.SSLSocket)`.
**Warning signs:** `AttributeError: '_io.BufferedIOBase' object has no attribute 'version'`.

### Pitfall 3: OpenSSL 3.x rejects TLS 1.0/1.1 probes

**What goes wrong:** The chaos lab Postfix/Dovecot container is configured with `ssl_protocols = !SSLv2 !SSLv3` (allowing TLS 1.0/1.1), but the scanner host's OpenSSL 3.x refuses to negotiate these versions. sslyze returns empty cipher suites for TLS 1.0/1.1 — not an error, just no results.
**Why it happens:** OpenSSL 3.0+ disables TLS 1.0/1.1 at the library level. Both client and server must support the version.
**How to avoid:** Per STATE.md: "target RSA key-exchange and weak cipher as primary detectable findings at TLS 1.2". The chaos lab cert uses RSA-2048 (quantum-vulnerable) and non-PFS RSA cipher suites (`AES128-SHA`, `AES256-SHA`) which ARE detectable at TLS 1.2. Do not assert TLS 1.1 findings in `expected_results.md`.
**Warning signs:** sslyze returns completed status but `tls_1_1_cipher_suites.result.accepted_cipher_suites` is empty even with a TLS-1.1-enabled server.

### Pitfall 4: Port 25 blocked on cloud VM

**What goes wrong:** `ConnectionRefusedError` or `socket.timeout` on port 25 during CI or cloud-hosted tests.
**Why it happens:** Most cloud providers (AWS, GCP, Azure) block outbound TCP port 25 by default.
**How to avoid:** Per D-03: `ConnectionRefusedError` on any email port is non-fatal and logged at DEBUG only. Wrap the sslyze call AND the fallback in try/except; set `ep.tls_blocker_reason = "CONNECTION_REFUSED"` and return without error. Do NOT raise.
**Warning signs:** Test suite failures on CI when run against external hosts.

### Pitfall 5: Duplicate findings for the same endpoint

**What goes wrong:** Port 25 endpoint gets three findings: STARTTLS downgrade risk (MEDIUM) + weak cipher (HIGH) + the generic "Legacy TLS cipher suites accepted" (LOW) from `evaluate_endpoints()`.
**Why it happens:** `evaluate_endpoints()` in `risk_engine.py` already emits findings for any endpoint with `protocol="SMTP-STARTTLS"` and `tls_weak_ciphers_present=True` (via the `tls_legacy_suites_present` check).
**How to avoid:** The `_dedupe_findings()` function deduplicates by `(host, port, title, recommendation)` — different titles survive. This is correct behavior per D-11 (layered findings). Document in `expected_results.md` that multiple findings on the same port are expected and intentional.
**Warning signs:** Dashboard showing 4+ findings per email port instead of 2-3.

### Pitfall 6: email_scan_json shape inconsistency

**What goes wrong:** Planner decides on per-port nested structure; later dashboard query (Phase 36 DASH-02) expects flat structure or vice versa.
**Why it happens:** Shape is Claude's discretion (CONTEXT.md) but Phase 36 depends on it.
**How to avoid:** Use a per-port nested structure: `{ "25": {...endpoint_data}, "587": {...}, ... }` keyed by port number. This is the cleanest shape for the Phase 36 per-port table view (DASH-02). Write the JSON to the endpoint whose port is the lowest-numbered successful port, or attach it to all endpoints from the same host (duplicated).
**Recommended shape:**
```json
{
  "host": "mail.example.com",
  "scanned_at": "2026-04-27T12:00:00Z",
  "ports": {
    "25": {"protocol": "SMTP-STARTTLS", "tls_version": "TLSv1.2", "cipher": "AES256-SHA", ...},
    "465": {"protocol": "SMTPS", "tls_version": "TLSv1.3", ...},
    "587": {"error": "CONNECTION_REFUSED"},
    "143": {...},
    "993": {...},
    "110": {...},
    "995": {...}
  }
}
```

---

## Code Examples

Verified patterns from official sources (codebase):

### sslyze STARTTLS scan call (EMAIL-01 / EMAIL-03 / EMAIL-05)

```python
# Source: quirk/scanner/tls_scanner.py lines 135-155 + existing research doc
from sslyze import (
    Scanner as SslyzeScanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ServerNetworkConfiguration,
    ProtocolWithOpportunisticTlsEnum,
    ScanCommand,
    ServerScanStatusEnum,
)

scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(hostname=host, port=port),
    network_configuration=ServerNetworkConfiguration(
        tls_server_name_indication=host,
        tls_opportunistic_encryption=ProtocolWithOpportunisticTlsEnum.SMTP,  # or IMAP, POP3
        network_timeout=timeout,
    ),
    scan_commands={
        ScanCommand.CERTIFICATE_INFO,
        ScanCommand.TLS_1_2_CIPHER_SUITES,
        ScanCommand.TLS_1_3_CIPHER_SUITES,
        # ... etc.
    },
)
```

[VERIFIED: tls_scanner.py lines 135-155; ProtocolWithOpportunisticTlsEnum API confirmed in existing email-tls-research.md]

### smtplib STARTTLS fallback

```python
# Source: quirk/.planning/research/email-tls-research.md section 2
import smtplib, ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def _fallback_smtp_starttls(host: str, port: int, timeout: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ctx)
        smtp.ehlo()
        ssock = smtp.sock  # ssl.SSLSocket after STARTTLS
        tls_version = ssock.version()
        cipher = ssock.cipher()
        der = ssock.getpeercert(binary_form=True)
    return tls_version, cipher[0] if cipher else None, der
```

[VERIFIED: existing email-tls-research.md section 2 — cross-referenced with stdlib smtplib docs]

### DB migration (EMAIL-00)

```python
# Source: quirk/db.py lines 42-63 (exact pattern from _ensure_identity_columns)
_EMAIL_COLUMNS = ["email_scan_json"]

def _ensure_email_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _EMAIL_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

[VERIFIED: quirk/db.py lines 42-63]

### Chaos lab Postfix main.cf (TLS weak config for EMAIL-11)

```ini
# Source: quirk/.planning/research/email-tls-research.md section 4
# Allows TLS 1.2 (1.0/1.1 excluded by OpenSSL 3.x on scanner host anyway)
smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1
smtp_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1

# RSA key exchange (no PFS — quantum-vulnerable) — detectable at TLS 1.2
smtpd_tls_mandatory_ciphers = medium
smtpd_tls_mandatory_exclude_ciphers = aNULL, eNULL, EXPORT, DES, MD5, PSK, SRP, CAMELLIA, ECDHE, EDH
smtpd_tls_ciphers = medium

# STARTTLS on port 25
smtpd_tls_security_level = may
smtpd_use_tls = yes
smtpd_tls_cert_file = /etc/postfix/certs/postfix.crt
smtpd_tls_key_file = /etc/postfix/certs/postfix.key
```

[ASSUMED — specific Postfix directive values for excluding ECDHE while keeping RSA-only suites at TLS 1.2 require lab testing to confirm they produce the expected weak-cipher scan results.]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| sslyze CLI subprocess | sslyze Python API (`ServerScanRequest`) | sslyze v5.x | Direct Python integration; no subprocess overhead |
| Separate SMTP/IMAP/POP3 scan tools | sslyze `ProtocolWithOpportunisticTlsEnum` | sslyze v3+ | Single library handles all three STARTTLS protocols |
| TLS 1.0/1.1 as detectable weakness | TLS 1.0/1.1 disabled by OpenSSL 3.x on modern hosts | OpenSSL 3.0 (2021) | Chaos lab must use RSA key-exchange at TLS 1.2 as the primary weak finding |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Postfix `main.cf` directive `smtpd_tls_mandatory_exclude_ciphers = ... ECDHE ...` produces RSA-only suites at TLS 1.2 in the chaos lab | Code Examples (chaos lab Postfix config) | Chaos lab may not produce the expected `weak-cipher` HIGH finding; `expected_results.md` would need correction |
| A2 | `smtp.sock` on Python 3.11+ after `smtplib.SMTP.starttls()` is always an `ssl.SSLSocket` with working `.version()`, `.cipher()`, `.getpeercert(binary_form=True)` | Code Examples (smtplib fallback) | Fallback may fail silently on specific OS/Python combinations; test needed |
| A3 | sslyze `ProtocolWithOpportunisticTlsEnum` values for SMTP, IMAP, POP3 are accessible without a separate extras install | Standard Stack | If sslyze is not installed and the STARTTLS probe path is reached, it falls back to stdlib — correct behavior; no runtime failure |

---

## Open Questions

1. **`email_scan_json` attachment point**
   - What we know: `kerberos_scan_json` is written to the first endpoint for a target (kerberos_scanner.py line 319). Email has 7 endpoints per host.
   - What's unclear: Should `email_scan_json` be a summary JSON attached to all 7 endpoints (duplicated), or only to one "summary" endpoint per host?
   - Recommendation: Attach the per-host summary JSON to every email endpoint for that host. This simplifies Phase 36 dashboard queries — any email endpoint can be joined to get the full port summary.

2. **`--include-email` / `--no-email` CLI flags (D-07, Claude's Discretion)**
   - What we know: `apply_profile()` handles scanner enable/disable via config flags. No existing scanner has per-scanner CLI override flags.
   - What's unclear: Whether the planner should add CLI flags or rely entirely on profile-based gating.
   - Recommendation: Skip the CLI flags for Phase 32 — profile gating (`standard`/`deep`) covers the primary use case. Adding `--no-email` can be a quick add-on in Phase 37 if needed.

3. **findings from `evaluate_endpoints()` vs `email_scanner.py`**
   - What we know: `evaluate_endpoints()` already produces generic TLS findings for any endpoint. Email-specific findings (EMAIL-08, EMAIL-09) need to fire in addition.
   - What's unclear: Whether to add email logic into `risk_engine.py:evaluate_endpoints()` (touching shared code) or emit findings inside `email_scanner.py` (scanner-local).
   - Recommendation: Add `evaluate_email_endpoints()` in `risk_engine.py` parallel to the existing logic. Call it from `run_scan.py` after collecting `email_endpoints`. This keeps scanner modules free of finding logic (separation of concerns).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | email_scanner.py | ✓ | 3.14.4 | — |
| smtplib (stdlib) | EMAIL-07 fallback | ✓ | stdlib | — |
| imaplib (stdlib) | EMAIL-07 fallback | ✓ | stdlib | — |
| poplib (stdlib) | EMAIL-07 fallback | ✓ | stdlib | — |
| sslyze | EMAIL-01..06 primary | Not installed | — | stdlib fallback (all paths work) |
| Docker | EMAIL-11 chaos lab | ✓ (assumed from other labs in use) | — | Skip lab testing |
| openssl CLI | labs/email/Makefile certs target | ✓ (assumed on macOS dev) | OpenSSL 3.x | — |

[VERIFIED: Python version via `python3 --version`; sslyze absence confirmed via pip show and venv check]
[ASSUMED: Docker availability — other labs are already present; openssl CLI on macOS dev machine]

**sslyze note:** sslyze is an optional import in `tls_scanner.py` (soft-import with `SSLYZE_AVAILABLE` guard). It is NOT in `pyproject.toml` core dependencies. Phase 32 must maintain the same optional-import pattern. If sslyze is not installed, ALL email port probes use the stdlib fallback path. This is correct behavior.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python 3 stdlib test runner) |
| Config file | None — discovered via project root |
| Quick run command | `python3 -m pytest tests/test_email_scanner.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

[VERIFIED: `python3 -m pytest --collect-only` collects 504 tests; pytest works from project root]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EMAIL-00 | `email_scan_json` column present in schema after `init_db()` | unit | `pytest tests/test_email_scanner.py::test_email_scan_json_column_exists -x` | ❌ Wave 0 |
| EMAIL-01 | Port 25 sslyze STARTTLS returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_smtp_starttls_sslyze -x` | ❌ Wave 0 |
| EMAIL-02 | Port 465 implicit TLS returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_smtps_sslyze -x` | ❌ Wave 0 |
| EMAIL-03 | Port 143 IMAP STARTTLS returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_imap_starttls_sslyze -x` | ❌ Wave 0 |
| EMAIL-04 | Port 993 IMAPS returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_imaps_sslyze -x` | ❌ Wave 0 |
| EMAIL-05 | Port 110 POP3 STARTTLS returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_pop3_starttls_sslyze -x` | ❌ Wave 0 |
| EMAIL-06 | Port 995 POP3S returns populated CryptoEndpoint | unit (mocked sslyze) | `pytest tests/test_email_scanner.py::test_scan_one_pop3s_sslyze -x` | ❌ Wave 0 |
| EMAIL-07 | stdlib fallback returns TLS version + cipher + cert when sslyze fails | unit (mocked smtplib/imaplib/poplib) | `pytest tests/test_email_scanner.py::test_fallback_smtp -x` | ❌ Wave 0 |
| EMAIL-08 | Port 25 STARTTLS endpoint emits `starttls-downgrade-risk` MEDIUM finding | unit | `pytest tests/test_email_scanner.py::test_starttls_downgrade_finding_port25 -x` | ❌ Wave 0 |
| EMAIL-09 | RSA key-exchange cipher emits HIGH finding; non-PFS ECDHE emits MEDIUM | unit | `pytest tests/test_email_scanner.py::test_weak_cipher_finding_rsa -x` | ❌ Wave 0 |
| EMAIL-01 | CONNECTION_REFUSED on port 25 does not crash scan | unit | `pytest tests/test_email_scanner.py::test_connection_refused_non_fatal -x` | ❌ Wave 0 |
| EMAIL-10 | `ep.service_detail` format matches `"SMTP-STARTTLS:587"` etc. | unit | `pytest tests/test_email_scanner.py::test_service_detail_labels -x` | ❌ Wave 0 |
| STRUCT-01 | `scan_email_targets` accepts `session_start` parameter; no internal `datetime.now()` | unit | `pytest tests/test_email_scanner.py::test_session_start_propagation -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_email_scanner.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work` (existing 4 failures are pre-existing version/packaging; acceptable)

### Test Fixture Pattern (from existing test_sslyze_integration.py and test_dnssec_scanner.py)

Tests MUST mock network calls — no live network required.

```python
# Pattern from tests/test_sslyze_integration.py + tests/test_dnssec_scanner.py

from unittest.mock import patch, MagicMock
from quirk.scanner.email_scanner import scan_email_targets, scan_one_email

def _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES256-SHA"):
    """Build a mock sslyze ServerScanResult with completed status."""
    result = MagicMock()
    result.scan_status = ServerScanStatusEnum.COMPLETED
    # ... populate cipher suites, cert_info, etc.
    return result

@patch("quirk.scanner.email_scanner.SslyzeScanner")
def test_scan_one_smtp_starttls_sslyze(mock_scanner_cls):
    mock_scanner = MagicMock()
    mock_scanner.get_results.return_value = [_make_mock_sslyze_result()]
    mock_scanner_cls.return_value = mock_scanner
    ep = scan_one_email("mail.example.com", 25, "SMTP-STARTTLS",
                        ProtocolWithOpportunisticTlsEnum.SMTP, timeout=5)
    assert ep.protocol == "SMTP-STARTTLS"
    assert ep.service_detail == "SMTP-STARTTLS:25"
    assert ep.tls_version == "TLSv1.2"
```

### Wave 0 Gaps

- [ ] `tests/test_email_scanner.py` — covers EMAIL-00 through EMAIL-12 and STRUCT-01
- [ ] `quirk/scanner/email_scanner.py` — the module under test (must exist before tests run)
- [ ] No new fixtures needed in `tests/conftest.py` — mock pattern is self-contained

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Scanner is agentless, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Read-only scanner |
| V5 Input Validation | Yes | Host/port inputs validated via existing `_SAFE_COL_RE` for column names; hosts come from user config (trusted) |
| V6 Cryptography | No | Scanner reports others' crypto — does not implement it |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via column names in migration | Tampering | `_SAFE_COL_RE` allowlist in `quirk/db.py` — already applied |
| Cert data trust (attacker controls target server) | Spoofing | `ssl.CERT_NONE` — scanner intentionally accepts all certs to enumerate them; this is correct scanner behavior |
| Port 25 timeout causing full scan hang | Denial of Service | `cfg.scan.timeout_seconds` applied per-connection; ThreadPoolExecutor isolates per-port futures |

---

## Sources

### Primary (HIGH confidence)

- `quirk/scanner/tls_scanner.py` — canonical 4-function shape; `_pubkey_info()`, `_scan_one_sslyze()`, `_scan_one_fallback()`, `scan_tls_targets()` confirmed by direct read
- `quirk/scanner/dnssec_scanner.py` — `session_start` plumbing pattern confirmed (line 188)
- `quirk/scanner/kerberos_scanner.py` — `kerberos_scan_json` attachment pattern confirmed (lines 294, 319, 329)
- `quirk/db.py` — migration pattern confirmed (lines 42-128)
- `quirk/models.py` — `CryptoEndpoint` column declarations confirmed (lines 67-80)
- `quirk/config.py` — `ConnectorsCfg` fields confirmed (lines 44-100); `enable_dnssec` pattern confirmed
- `quirk/engine/profiles.py` — `apply_profile()` structure confirmed; no existing scanner-level boolean flags set here yet
- `quirk/engine/risk_engine.py` — finding dict shape, `_dedupe_findings()` key, `evaluate_endpoints()` flow confirmed
- `quirk/pyproject.toml` — `[project.optional-dependencies]` table structure confirmed; `[motion]` group absent
- `run_scan.py` — integration call site patterns (lines 395, 628, 656); `session_start` flow confirmed
- `.planning/research/email-tls-research.md` — sslyze STARTTLS API, stdlib fallback patterns, port conventions, chaos lab rationale, Postfix/Dovecot config — verified HIGH confidence per existing research doc

### Secondary (MEDIUM confidence)

- `.planning/STATE.md` — OpenSSL 3.x TLS 1.1 caveat documented as milestone-level decision
- `labs/vault/expected_results.md` — `expected_results.md` format template
- `quantum-chaos-enterprise-lab/docker-compose.yml` — profile naming convention (`vault`, `storage`, `kerberos`, `dnssec`)

### Tertiary (LOW confidence)

- Specific Postfix `smtpd_tls_mandatory_exclude_ciphers` directive values for RSA-only at TLS 1.2 — needs lab testing to confirm

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries verified in codebase (sslyze optional import confirmed, stdlib always available)
- Architecture: HIGH — 4-function pattern, DB migration pattern, profile gating pattern all confirmed by direct code read
- Pitfalls: HIGH — `cfg.scanners` vs `cfg.connectors` verified by code; OpenSSL TLS 1.1 caveat from STATE.md; smtplib socket access from research doc
- Chaos lab Postfix config: MEDIUM/LOW — directive values are assumed until lab-tested

**Research date:** 2026-04-27
**Valid until:** 2026-07-27 (stable Python stdlib patterns; sslyze API stable on 5.x)

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- If detection logic changes, update `labs/*/expected_results.md` accordingly.
- Phase completion requires: Obsidian phase note, UAT-SERIES.md update, Obsidian sync, commit.
- Test runner: `python3 -m pytest tests/` from project root.
