# Phase 32: Email Scanner - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/scanner/email_scanner.py` | scanner module | request-response | `quirk/scanner/tls_scanner.py` | exact |
| `quirk/db.py` | migration helper | CRUD | `quirk/db.py:_ensure_identity_columns()` | exact (same file) |
| `quirk/models.py` | model column add | CRUD | `quirk/models.py` lines 67-80 (v4.2/v4.3 blocks) | exact (same file) |
| `quirk/config.py` | config flag | config | `quirk/config.py` lines 63-66 (`enable_kerberos` etc.) | exact (same file) |
| `quirk/engine/profiles.py` | profile toggle | config | `quirk/engine/profiles.py:apply_profile()` — existing `tls_enum_mode` branch | role-match |
| `quirk/engine/risk_engine.py` | findings emitter | request-response | `quirk/engine/risk_engine.py:evaluate_endpoints()` lines 246-365 | role-match |
| `run_scan.py` | integration call site | request-response | `run_scan.py` lines 624-696 (DNSSEC/Kerberos blocks) | exact |
| `tests/test_email_scanner.py` | test | test | `tests/test_dnssec_scanner.py` | exact |
| `labs/email/` (whole directory) | chaos lab | event-driven | `quantum-chaos-enterprise-lab/docker-compose.yml` vault/kerberos profiles + `labs/vault/expected_results.md` | role-match |

---

## Pattern Assignments

### `quirk/scanner/email_scanner.py` (scanner module, request-response)

**Analog:** `quirk/scanner/tls_scanner.py`

**Imports pattern** (tls_scanner.py lines 1-32):
```python
import json
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Optional

import smtplib
import imaplib
import poplib

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger

# sslyze optional import (copy guard verbatim from tls_scanner.py lines 19-35)
try:
    from sslyze import (
        Scanner as SslyzeScanner,
        ServerScanRequest,
        ServerNetworkLocation,
        ScanCommand,
        ServerNetworkConfiguration,
        ScanCommandAttemptStatusEnum,
        ServerScanStatusEnum,
        ProtocolWithOpportunisticTlsEnum,
    )
    import sslyze as _sslyze_module
    SSLYZE_AVAILABLE = True
except ImportError:
    SSLYZE_AVAILABLE = False

_sslyze_warned = False
```

**Port table (new — no direct analog; use this shape):**
```python
# (port, protocol_label, service_detail_prefix, starttls_enum_or_None)
EMAIL_PORTS = [
    (25,  "SMTP-STARTTLS", "SMTP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.SMTP if SSLYZE_AVAILABLE else None),
    (465, "SMTPS",         "SMTPS",          None),   # implicit TLS
    (587, "SMTP-STARTTLS", "SMTP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.SMTP if SSLYZE_AVAILABLE else None),
    (143, "IMAP-STARTTLS", "IMAP-STARTTLS",  ProtocolWithOpportunisticTlsEnum.IMAP if SSLYZE_AVAILABLE else None),
    (993, "IMAPS",         "IMAPS",          None),   # implicit TLS
    (110, "POP3-STARTTLS", "POP3-STARTTLS",  ProtocolWithOpportunisticTlsEnum.POP3 if SSLYZE_AVAILABLE else None),
    (995, "POP3S",         "POP3S",          None),   # implicit TLS
]
```

**`_pubkey_info()` reuse** (tls_scanner.py lines 38-47 — import, do NOT copy):
```python
# Import from tls_scanner to avoid duplication (D-10 explicitly calls for reuse)
from quirk.scanner.tls_scanner import _pubkey_info, _extract_sans
```

**`_scan_one_sslyze_email()` — sslyze primary path** (modeled after tls_scanner.py lines 103-322):
```python
def _scan_one_sslyze_email(
    host: str,
    port: int,
    starttls_enum,          # ProtocolWithOpportunisticTlsEnum or None (implicit TLS)
    timeout: int,
    logger: Optional[Logger] = None,
) -> Optional[CryptoEndpoint]:
    """Primary TLS probe via sslyze. Returns None to trigger fallback on any failure."""
    global _sslyze_warned
    if not SSLYZE_AVAILABLE:
        if not _sslyze_warned:
            if logger:
                logger.v("sslyze not installed — email scanner using stdlib fallback")
            _sslyze_warned = True
        return None
    try:
        net_cfg = ServerNetworkConfiguration(
            tls_server_name_indication=host,
            tls_opportunistic_encryption=starttls_enum,   # None = direct TLS
            network_timeout=timeout,
        )
        scan_request = ServerScanRequest(
            server_location=ServerNetworkLocation(hostname=host, port=port),
            network_configuration=net_cfg,
            scan_commands={
                ScanCommand.CERTIFICATE_INFO,
                ScanCommand.TLS_1_2_CIPHER_SUITES,
                ScanCommand.TLS_1_3_CIPHER_SUITES,
            },
        )
        scanner = SslyzeScanner(per_server_concurrent_connections_limit=2)
        scanner.queue_scans([scan_request])
        results = list(scanner.get_results())
        if not results:
            return None
        server_result = results[0]
        if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
            if logger:
                logger.v(f"sslyze ERROR for {host}:{port} — using fallback")
            return None
        # ... parse cert_info, cipher_suites (copy pattern from tls_scanner.py lines 178-317)
        # Set ep.tls_weak_ciphers_present, ep.tls_pfs_supported, ep.cipher_suite, ep.tls_version
        return ep
    except ConnectionRefusedError:
        return None   # D-03: CONNECTION_REFUSED is non-fatal and silent
    except Exception as e:
        if logger:
            logger.v(f"sslyze exception for {host}:{port}: {e} — using fallback")
        return None
```

**`_scan_one_fallback_email()` — stdlib fallback** (modeled after tls_scanner.py lines 329-420):
```python
def _scan_one_fallback_email(
    host: str,
    port: int,
    protocol_label: str,
    timeout: int,
    logger: Optional[Logger] = None,
) -> CryptoEndpoint:
    """Stdlib fallback (smtplib/imaplib/poplib). Sets ep fields from SSLSocket."""
    ep = CryptoEndpoint(host=host, port=port, protocol=protocol_label)
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        if protocol_label == "SMTP-STARTTLS":
            tls_version, cipher_name, der = _fallback_smtp_starttls(host, port, timeout, ctx)
        elif protocol_label == "IMAP-STARTTLS":
            tls_version, cipher_name, der = _fallback_imap_starttls(host, port, timeout, ctx)
        elif protocol_label == "POP3-STARTTLS":
            tls_version, cipher_name, der = _fallback_pop3_starttls(host, port, timeout, ctx)
        else:
            # Implicit TLS (SMTPS 465, IMAPS 993, POP3S 995)
            tls_version, cipher_name, der = _fallback_implicit_tls(host, port, timeout, ctx)
        ep.tls_version = tls_version
        ep.cipher_suite = cipher_name
        if der:
            cert = x509.load_der_x509_certificate(der, default_backend())
            ep.cert_subject = cert.subject.rfc4514_string()
            ep.cert_issuer = cert.issuer.rfc4514_string()
            ep.cert_sans = _extract_sans(cert)
            ep.cert_sig_alg = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else "unknown"
            alg, size = _pubkey_info(cert.public_key())
            ep.cert_pubkey_alg = alg
            ep.cert_pubkey_size = size
    except ConnectionRefusedError:
        ep.tls_blocker_reason = "CONNECTION_REFUSED"   # D-03: silent at DEBUG
        if logger:
            logger.debug(f"Email port {port} CONNECTION_REFUSED on {host}")
    except Exception as e:
        ep.scan_error = str(e)
        if logger:
            logger.v(f"Email fallback error {host}:{port}: {e}")
    return ep
```

**`scan_one_email()` — orchestrator** (modeled after tls_scanner.py lines 427-449):
```python
def scan_one_email(
    host: str,
    port: int,
    protocol_label: str,
    starttls_enum,
    timeout: int,
    logger: Optional[Logger] = None,
    session_start=None,
) -> CryptoEndpoint:
    """Try sslyze → fallback. Sets ep.protocol, ep.service_detail, ep.scanned_at."""
    ep = _scan_one_sslyze_email(host, port, starttls_enum, timeout, logger)
    if ep is None:
        ep = _scan_one_fallback_email(host, port, protocol_label, timeout, logger)
    ep.protocol = protocol_label
    ep.service_detail = f"{protocol_label}:{port}"
    # STRUCT-01: shared session_start, no datetime.now() inside scanner
    ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return ep
```

**`scan_email_targets()` — parallel driver** (modeled after tls_scanner.py lines 452-478):
```python
def scan_email_targets(
    hosts: List[str],
    timeout: int,
    logger: Optional[Logger] = None,
    session_start=None,
) -> List[CryptoEndpoint]:
    """Expand hosts × EMAIL_PORTS and probe in parallel via ThreadPoolExecutor."""
    results: List[CryptoEndpoint] = []
    tasks = [
        (host, port, label, starttls_enum)
        for host in hosts
        for (port, label, _, starttls_enum) in EMAIL_PORTS
    ]
    if not tasks:
        return results
    if logger:
        logger.stamp(f"Starting email TLS scans: {len(tasks)} tasks ({len(hosts)} hosts × 7 ports)")
    with ThreadPoolExecutor(max_workers=min(len(tasks), 50)) as ex:
        futures = {
            ex.submit(scan_one_email, host, port, label, starttls_enum, timeout, logger, session_start): (host, port)
            for host, port, label, starttls_enum in tasks
        }
        for f in as_completed(futures):
            ep = f.result()
            if ep is not None:
                results.append(ep)
    if logger:
        ok = len([e for e in results if not getattr(e, "scan_error", None) and not getattr(e, "tls_blocker_reason", None)])
        logger.stamp(f"Email scans complete: {ok}/{len(results)} successful")
    return results
```

---

### `quirk/db.py` — `_ensure_email_columns()` (migration helper, CRUD)

**Analog:** `quirk/db.py:_ensure_identity_columns()` lines 42-63 and `_ensure_v43_columns()` lines 87-106

**Exact pattern to copy** (db.py lines 42-63 with adapted names):
```python
_EMAIL_COLUMNS = ["email_scan_json"]


def _ensure_email_columns(engine) -> None:
    """Add v4.4 email scanner column (email_scan_json TEXT) if absent (idempotent).

    Uses SQLAlchemy inspector to check existing columns before ALTER TABLE.
    Called from init_db() after _ensure_v43_columns().
    """
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _EMAIL_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

**Call site in `init_db()`** (db.py lines 126-128, append after last existing call):
```python
# existing calls already in init_db():
_ensure_identity_columns(engine)   # v4.2
_ensure_gcp_columns(engine)        # v4.3
_ensure_v43_columns(engine)        # v4.3
_ensure_email_columns(engine)      # v4.4 Phase 32  ← ADD THIS LINE
```

---

### `quirk/models.py` — `email_scan_json` column add (model, CRUD)

**Analog:** `quirk/models.py` lines 64-80 (v4.2 identity fields block)

**Exact pattern to follow** (models.py lines 67-69):
```python
kerberos_scan_json = Column(Text, nullable=True)  # Full Kerberos scan JSON
saml_scan_json = Column(Text, nullable=True)       # Full SAML scan JSON
dnssec_scan_json = Column(Text, nullable=True)     # Full DNSSEC scan JSON
```

**New block to add** (append after line 80, following the v4.3 DAR block at lines 78-80):
```python
    # ==========================
    # v4.4 Data in Motion fields
    # ==========================
    email_scan_json = Column(Text, nullable=True)  # Per-host email port scan summary JSON (Phase 32)
```

---

### `quirk/config.py` — `ConnectorsCfg.enable_email` flag (config)

**Analog:** `quirk/config.py` lines 63-65 (`enable_kerberos`, `enable_saml`, `enable_dnssec`)

**Exact pattern** (config.py lines 63-65):
```python
    enable_kerberos: bool = False
    enable_saml: bool = False
    enable_dnssec: bool = False
```

**New line to add** (append at the bottom of `ConnectorsCfg`, after line 99 `vault_tls_verify`):
```python
    # Email scanner enable flag (v4.4, Phase 32)
    enable_email: bool = False
```

**CRITICAL:** The config attribute is `cfg.connectors.enable_email` (NOT `cfg.scanners.email_enabled` — that namespace does not exist).

---

### `quirk/engine/profiles.py` — profile toggle for email (config, profile-gating)

**Analog:** `quirk/engine/profiles.py:apply_profile()` — existing `tls_enum_mode` conditional branches at lines 87-116

**Pattern for scanner-level boolean gating** (profiles.py lines 75-116 structure):
```python
# In apply_profile(), at the end of each profile branch:

if p == "quick":
    # ... existing quick settings ...
    # Email scanner stays disabled for quick (D-05)
    # cfg.connectors.enable_email remains False (default)
    pass

elif p == "deep":
    # ... existing deep settings ...
    # Enable email scanner for deep profile (D-05/D-06)
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_email"):
        if not cfg.connectors.enable_email:   # only set if user hasn't already set it
            cfg.connectors.enable_email = True

else:  # standard
    # ... existing standard settings ...
    # Enable email scanner for standard profile (D-05/D-06)
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_email"):
        if not cfg.connectors.enable_email:
            cfg.connectors.enable_email = True
```

**Note:** `profiles.py` currently sets only `scan.*` fields. The `cfg.connectors.*` mutation is new for Phase 32. Use `hasattr` guards (same defensive style as existing `getattr(scan, field, None)` pattern throughout the file).

---

### `quirk/engine/risk_engine.py` — `evaluate_email_endpoints()` (findings emitter)

**Analog:** `quirk/engine/risk_engine.py:evaluate_endpoints()` lines 246-365

**Finding dict shape** (from risk_engine.py lines 263-282 — copy this exact structure):
```python
findings.append({
    "severity": "MEDIUM",      # or "HIGH"
    "host": host,
    "port": port,
    "title": "...",
    "recommendation": "...",
})
```

**New function to add** (parallel to `evaluate_endpoints()`):
```python
def evaluate_email_endpoints(endpoints) -> List[Dict[str, Any]]:
    """Emit email-specific findings (EMAIL-08, EMAIL-09) for email scanner endpoints.

    Called from run_scan.py after scan_email_targets() completes.
    _dedupe_findings() is called in evaluate_endpoints(); these findings are
    merged into the main findings list before that call.
    """
    findings: List[Dict[str, Any]] = []

    for e in endpoints:
        host = getattr(e, "host", "")
        port = int(getattr(e, "port", 0))
        protocol = getattr(e, "protocol", "")
        cipher = getattr(e, "cipher_suite", "") or ""
        tls_version = getattr(e, "tls_version", "") or ""
        pfs = getattr(e, "tls_pfs_supported", None)

        # EMAIL-08: STARTTLS downgrade risk — port 25 ONLY, not port 587
        if port == 25 and protocol == "SMTP-STARTTLS" and tls_version:
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "STARTTLS downgrade risk on SMTP",
                "recommendation": (
                    "STARTTLS (opportunistic TLS) is susceptible to stripping attacks that "
                    "cannot be detected by an agentless scanner. An attacker in-path can "
                    "suppress the STARTTLS capability advertisement, forcing plaintext delivery. "
                    "Enforce MTA-STS (RFC 8461) or DANE (RFC 7672) to prevent stripping."
                ),
            })

        # EMAIL-09: Weak RSA key exchange (no PFS) = HIGH
        upper_cipher = cipher.upper()
        is_rsa_kex = (
            upper_cipher.startswith("TLS_RSA_WITH_")
            or ("AES128-SHA" in upper_cipher or "AES256-SHA" in upper_cipher)
            or any(m in upper_cipher for m in ("3DES", "RC4"))
        ) and "ECDHE" not in upper_cipher and "DHE" not in upper_cipher

        if is_rsa_kex and tls_version:
            findings.append({
                "severity": "HIGH",
                "host": host,
                "port": port,
                "title": "Weak cipher suite on email TLS endpoint",
                "recommendation": (
                    "TLS_RSA_WITH_* suites use RSA key exchange (no forward secrecy) and are "
                    "quantum-vulnerable. Disable non-PFS suites and require ECDHE or TLS 1.3 "
                    "cipher suites across all email protocol ports."
                ),
            })

        # EMAIL-09: Non-PFS ECDHE without TLS 1.3 = MEDIUM
        elif pfs is False and tls_version and tls_version != "TLSv1.3":
            findings.append({
                "severity": "MEDIUM",
                "host": host,
                "port": port,
                "title": "Non-PFS cipher suite on email TLS endpoint",
                "recommendation": (
                    "ECDHE without TLS 1.3 provides forward secrecy but remains quantum-vulnerable "
                    "via Shor's algorithm. Prefer TLS 1.3 AEAD suites (AES-GCM, ChaCha20-Poly1305) "
                    "and plan migration to post-quantum key encapsulation."
                ),
            })

    return findings
```

**`_dedupe_findings()` key reminder** (risk_engine.py lines 165-191): key is `(host, port, title, recommendation)`. Layered findings (D-11) survive dedup because `title` values differ.

---

### `run_scan.py` — email scan integration block (integration call site)

**Analog:** `run_scan.py` lines 624-663 (DNSSEC + Kerberos blocks)

**Exact pattern to mirror** (run_scan.py lines 624-635 — DNSSEC block):
```python
    # ── DNSSEC scanning ─────────────────────────────────────
    dnssec_endpoints = []
    with _phase_timer(run_stats, "dnssec_scanning"):
        if cfg.connectors.enable_dnssec and cfg.connectors.dnssec_targets:
            dnssec_endpoints = scan_dnssec_targets(
                targets=cfg.connectors.dnssec_targets,
                timeout=getattr(cfg.connectors, "dnssec_timeout", 10),
                logger=logger,
                session_start=session_start,
            )
            logger.info("DNSSEC scan: %d endpoints from %d targets",
                        len(dnssec_endpoints), len(cfg.connectors.dnssec_targets))
```

**New block for email** (insert after the Vault block, before the `endpoints = (...)` aggregation at line 689):
```python
    # ── Email TLS scanning (Phase 32) ────────────────────────
    email_endpoints = []
    with _phase_timer(run_stats, "email_scanning"):
        if cfg.connectors.enable_email:
            from quirk.scanner.email_scanner import scan_email_targets
            # Derive unique host list from existing tls_targets (D-01/D-02)
            email_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if email_hosts:
                email_endpoints = scan_email_targets(
                    hosts=email_hosts,
                    timeout=cfg.scan.timeout_seconds,
                    logger=logger,
                    session_start=session_start,
                )
                logger.info("Email scan: %d endpoints from %d hosts",
                            len(email_endpoints), len(email_hosts))
```

**Import at top of run_scan.py** (follow pattern of line 24 `from quirk.scanner.dnssec_scanner import scan_dnssec_targets` — OR use lazy import inside the block as Kerberos does at line 655):
```python
from quirk.scanner.email_scanner import scan_email_targets  # add to top-level imports
```

**Aggregation line update** (run_scan.py line 689-696 — add `email_endpoints`):
```python
    endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
                 + jwt_endpoints + container_endpoints + source_endpoints
                 + aws_endpoints + azure_endpoints + gcp_endpoints
                 + db_endpoints
                 + s3_endpoints + blob_endpoints + gcs_storage_endpoints
                 + k8s_endpoints
                 + dnssec_endpoints + saml_endpoints + kerberos_endpoints
                 + vault_endpoints
                 + email_endpoints)   # ← add this
```

**`evaluate_email_endpoints()` call** (after collecting email_endpoints, before the main `findings = evaluate_endpoints(cfg, endpoints)` call):
```python
    # Email-specific findings (EMAIL-08/EMAIL-09) merged before dedup
    from quirk.engine.risk_engine import evaluate_email_endpoints
    email_findings = evaluate_email_endpoints(email_endpoints)
    # email_findings are merged into the main findings list in evaluate_endpoints
    # via the shared _dedupe_findings() call — or passed separately; see risk_engine pattern
```

---

### `tests/test_email_scanner.py` (test, request-response)

**Analog:** `tests/test_dnssec_scanner.py`

**Test file structure** (test_dnssec_scanner.py lines 1-16):
```python
"""Tests for email scanner (EMAIL-00 through EMAIL-12, STRUCT-01).

Tests mock network calls — no live network required.
Scanner module: quirk/scanner/email_scanner.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from quirk.scanner.email_scanner import (
    scan_email_targets,
    scan_one_email,
    EMAIL_PORTS,
)
```

**Mock helper pattern** (test_dnssec_scanner.py lines 23-57 — adapted for sslyze):
```python
def _make_mock_sslyze_result(tls_version="TLSv1.2", cipher="AES256-SHA", completed=True):
    """Build a mock sslyze ServerScanResult."""
    result = MagicMock()
    result.scan_status = ServerScanStatusEnum.COMPLETED if completed else ServerScanStatusEnum.ERROR_NO_CONNECTIVITY
    # Cipher suite mock
    suite = MagicMock()
    suite.cipher_suite.name = cipher
    attempt = MagicMock()
    attempt.status = ScanCommandAttemptStatusEnum.COMPLETED
    attempt.result.accepted_cipher_suites = [suite]
    result.scan_result.tls_1_2_cipher_suites = attempt
    return result
```

**CONNECTION_REFUSED non-fatal test pattern** (test_dnssec_scanner.py lines 142-165 structure):
```python
def test_connection_refused_non_fatal():
    """D-03/EMAIL-01: ConnectionRefusedError on any port must not raise."""
    with patch("quirk.scanner.email_scanner._scan_one_sslyze_email", return_value=None):
        with patch("quirk.scanner.email_scanner._scan_one_fallback_email") as mock_fb:
            mock_ep = MagicMock()
            mock_ep.tls_blocker_reason = "CONNECTION_REFUSED"
            mock_ep.scan_error = None
            mock_fb.return_value = mock_ep
            result = scan_one_email("mail.example.com", 25, "SMTP-STARTTLS", None, timeout=5)
            assert result is not None   # must not raise
```

**session_start propagation test** (STRUCT-01):
```python
from datetime import datetime, timezone

def test_session_start_propagation():
    """STRUCT-01: scan_email_targets must accept session_start; ep.scanned_at must equal it."""
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    with patch("quirk.scanner.email_scanner.scan_one_email") as mock_one:
        mock_ep = MagicMock()
        mock_ep.scan_error = None
        mock_ep.tls_blocker_reason = None
        mock_one.return_value = mock_ep
        scan_email_targets(["mail.example.com"], timeout=5, session_start=fixed_time)
        # session_start must be forwarded — check it was passed to scan_one_email
        call_kwargs = mock_one.call_args_list[0]
        assert fixed_time in call_kwargs.args or call_kwargs.kwargs.get("session_start") == fixed_time
```

---

### `labs/email/` — chaos lab directory (chaos lab)

**Analog:** `quantum-chaos-enterprise-lab/docker-compose.yml` vault profile (lines 720-756) + `labs/vault/expected_results.md`

**docker-compose.yml service block pattern** (lines 725-756):
```yaml
  # ── Email Chaos Lab (profile: email) ─────────────────────
  # Postfix + Dovecot with weak RSA-2048 TLS (non-PFS, TLS 1.2)
  # Ports: 30025/30465/30587 (SMTP), 30143/30993 (IMAP), 30110/30995 (POP3)
  postfix-email:
    build:
      context: ../labs/email
      dockerfile: Dockerfile
    profiles: ["email"]
    ports:
      - "30025:25"
      - "30465:465"
      - "30587:587"
    volumes:
      - ../labs/email/certs/postfix.crt:/etc/postfix/certs/postfix.crt:ro
      - ../labs/email/certs/postfix.key:/etc/postfix/certs/postfix.key:ro
      - ../labs/email/postfix/main.cf:/etc/postfix/main.cf:ro
    healthcheck:
      test: ["CMD-SHELL", "postfix status || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 20s

  dovecot-email:
    build:
      context: ../labs/email
      dockerfile: Dockerfile
    profiles: ["email"]
    ports:
      - "30143:143"
      - "30993:993"
      - "30110:110"
      - "30995:995"
    volumes:
      - ../labs/email/certs/dovecot.crt:/etc/dovecot/private/dovecot.crt:ro
      - ../labs/email/certs/dovecot.key:/etc/dovecot/private/dovecot.key:ro
    healthcheck:
      test: ["CMD-SHELL", "dovecot status || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 20s
```

**`labs/email/expected_results.md` structure** (copy from `labs/vault/expected_results.md` — lines 1-71):
```markdown
# Phase 32 — Email Scanner Expected Results

**Lab:** Postfix + Dovecot (Docker Compose profile `email`)
**Phase:** 32 — Email TLS Scanner
**Requirements:** EMAIL-01 through EMAIL-12

## Lab Setup

Boot the dedicated email chaos profile:
...
## Expected Scan Output

| port | protocol | tls_version | cipher_suite | finding | severity |
|------|----------|-------------|--------------|---------|----------|
| 30025 | SMTP-STARTTLS | TLSv1.2 | AES256-SHA | starttls-downgrade-risk + weak-cipher | MEDIUM + HIGH |
| 30465 | SMTPS | TLSv1.2 | AES256-SHA | weak-cipher | HIGH |
...
```

**`labs/email/Makefile` cert target** (D-16 — no existing analog; use this shape):
```makefile
.PHONY: certs clean

CERTS_DIR := certs

certs:
	mkdir -p $(CERTS_DIR)
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/postfix.key \
	    -out $(CERTS_DIR)/postfix.crt -days 3650 -nodes \
	    -subj "/CN=postfix.chaos.local"
	openssl req -x509 -newkey rsa:2048 -keyout $(CERTS_DIR)/dovecot.key \
	    -out $(CERTS_DIR)/dovecot.crt -days 3650 -nodes \
	    -subj "/CN=dovecot.chaos.local"

clean:
	rm -f $(CERTS_DIR)/postfix.* $(CERTS_DIR)/dovecot.*
```

---

## Shared Patterns

### sslyze Optional Import Guard
**Source:** `quirk/scanner/tls_scanner.py` lines 19-35
**Apply to:** `email_scanner.py`
```python
try:
    from sslyze import (
        Scanner as SslyzeScanner,
        ServerScanRequest,
        ServerNetworkLocation,
        ScanCommand,
        ServerNetworkConfiguration,
        ScanCommandAttemptStatusEnum,
        ServerScanStatusEnum,
        ProtocolWithOpportunisticTlsEnum,
    )
    import sslyze as _sslyze_module
    SSLYZE_AVAILABLE = True
except ImportError:
    SSLYZE_AVAILABLE = False
```

### session_start Plumbing (STRUCT-01)
**Source:** `quirk/scanner/dnssec_scanner.py` line 188
**Apply to:** `email_scanner.py:scan_one_email()`, `email_scanner.py:scan_email_targets()`
```python
now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
ep.scanned_at = now
```

### ConnectionRefusedError Silent Handling (D-03)
**Source:** `quirk/scanner/tls_scanner.py` lines 413-418 (error categorization)
**Apply to:** `_scan_one_sslyze_email()`, `_scan_one_fallback_email()`
```python
except ConnectionRefusedError:
    ep.tls_blocker_reason = "CONNECTION_REFUSED"
    if logger:
        logger.debug(f"Email port {port} CONNECTION_REFUSED on {host}")
    # Do NOT raise — D-03
```

### Inspector-First Migration Pattern
**Source:** `quirk/db.py` lines 49-63
**Apply to:** `_ensure_email_columns()`
```python
existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
with engine.connect() as conn:
    for col in _EMAIL_COLUMNS:
        if not _SAFE_COL_RE.match(col):
            raise ValueError(f"Unsafe column name in migration: {col!r}")
        if col not in existing:
            conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
    conn.commit()
```

### Finding Dict Shape
**Source:** `quirk/engine/risk_engine.py` lines 263-282
**Apply to:** `evaluate_email_endpoints()` in `risk_engine.py`
```python
findings.append({
    "severity": "MEDIUM",   # or "HIGH"
    "host": host,
    "port": port,
    "title": "...",
    "recommendation": "...",
})
```

### Chaos Lab Profile Service Block
**Source:** `quantum-chaos-enterprise-lab/docker-compose.yml` lines 725-756 (vault-30 block)
**Apply to:** email profile service blocks
```yaml
  service-name:
    build: { context: ./subdir, dockerfile: Dockerfile }
    profiles: ["email"]
    ports: ["HOST:CONTAINER"]
    healthcheck:
      test: [...]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 20s
```

---

## No Analog Found

All files have close analogs. No gaps.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/engine/`, `quirk/`, `tests/`, `labs/`, `quantum-chaos-enterprise-lab/`
**Files scanned:** 12 source files read directly (tls_scanner.py, dnssec_scanner.py, kerberos_scanner.py, db.py, models.py, config.py, profiles.py, risk_engine.py, run_scan.py, test_dnssec_scanner.py, docker-compose.yml, labs/vault/expected_results.md)
**Pattern extraction date:** 2026-04-27
