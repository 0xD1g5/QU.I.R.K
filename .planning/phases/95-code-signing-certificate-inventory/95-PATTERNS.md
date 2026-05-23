# Phase 95: Code-Signing Certificate Inventory - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 13 new/modified files
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/scanner/codesign_scanner.py` | scanner | CRUD (LDAP paged search + in-process filter) | `quirk/scanner/smime_scanner.py` | exact |
| `quirk/config.py` (ConnectorsCfg additions) | config | — | `quirk/config.py` lines 223-238 (SMIME block) | exact |
| `run_scan.py` (`_run_codesign_phase` + CLI flag + endpoints assembly) | controller/wiring | request-response | `run_scan.py` lines 1691-1733 (SMIME + ADCS wiring) | exact |
| `quirk/cbom/builder.py` (Pass-1 elif, Pass-2 skip, Pass-3 skip, dedup pass) | service | transform | `quirk/cbom/builder.py` lines 508-527, 619-627, 705-714 (SMIME/ADCS/BEARER_TOKEN branches) | exact |
| `quirk/intelligence/evidence.py` (`_PROTOCOL_KEYS` + CODE_SIGNING counter) | service | transform | `quirk/intelligence/evidence.py` lines 11-17, 305-321 (BEARER_TOKEN/OPENAPI Phase 94 block) | exact |
| `quirk/intelligence/scoring.py` (SCORE_WEIGHTS + agility block) | service | transform | `quirk/intelligence/scoring.py` lines 54-60, 225-233 (Phase 94 agility block) | exact |
| `tests/test_score_weights_invariant.py` (update assertions) | test | — | same file, lines 5-44 | exact |
| `tests/test_codesign_scanner.py` | test | — | `tests/test_smime_scanner.py` | exact |
| `tests/fixtures/codesign/` (DER cert fixtures) | test fixture | — | `quantum-chaos-enterprise-lab/smime/certs/regen.sh` | role-match |
| `quantum-chaos-enterprise-lab/docker-compose.yml` (ldaps seed additions) | config | — | `docker-compose.yml` lines 784-801 (smime-seed sidecar) | exact |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` (ldaps oracle update) | documentation/oracle | — | `expected_results_v4.md` lines 264-288 (ldaps profile) + lines 510-540 (smime profile) | exact |
| `quantum-chaos-enterprise-lab/README.md` (ldaps fixture description) | documentation | — | README.md smime section | role-match |
| `quantum-chaos-enterprise-lab/lab.sh` (verify no changes needed) | config | — | `lab.sh` lines 58-168 (`_derive_all_profiles`) | exact |

---

## Pattern Assignments

### `quirk/scanner/codesign_scanner.py` (scanner, LDAP paged search + in-process filter)

**Analog:** `quirk/scanner/smime_scanner.py` (near-exact copy with EKU filter added)
**Secondary analog:** `quirk/scanner/adcs_scanner.py` (EKU OID constant style)

**Imports pattern** (`smime_scanner.py` lines 15-38):
```python
from __future__ import annotations

try:
    import ldap3
    LDAP3_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    LDAP3_AVAILABLE = False

import json
import logging
from datetime import datetime, timezone

from cryptography.x509 import (
    load_der_x509_certificate,
    load_pem_x509_certificate,
)
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives import hashes
from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID

from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import is_weak_cipher
from quirk.util.safe_exc import safe_str

logger = logging.getLogger(__name__)

# Phase 95 CSIGN-01: code-signing queries userCertificate ONLY (not userSMIMECertificate)
_CODESIGN_ATTRS = ("userCertificate",)
CODE_SIGNING = "CODE_SIGNING"   # module constant — NEVER use the string literal directly
EKU_CODE_SIGNING = ExtendedKeyUsageOID.CODE_SIGNING  # OID 1.3.6.1.5.5.7.3.3
```

**Core helper — cert parse** (`smime_scanner.py` lines 58-100, adapted):
```python
def _parse_codesign_cert(cert_bytes: bytes) -> "dict | None":
    """Parse DER first, fallback PEM. Returns parsed dict or None on failure.
    Mirrors smime_scanner._parse_smime_cert but also computes SHA-256 fingerprint.
    """
    cert = None
    try:
        cert = load_der_x509_certificate(cert_bytes)
    except Exception as exc_der:
        logger.debug("CODESIGN DER parse failed, attempting PEM: %s", safe_str(exc_der))
        try:
            cert = load_pem_x509_certificate(cert_bytes)
        except Exception as exc_pem:
            logger.debug("CODESIGN PEM parse also failed: %s", safe_str(exc_pem))
            return None

    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_alg, key_bits = "RSA", pub.key_size
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_alg, key_bits = "ECDSA", pub.key_size
    else:
        key_alg, key_bits = "UNKNOWN", None

    try:
        sig_hash = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else ""
    except Exception:
        sig_hash = ""

    fingerprint_hex = cert.fingerprint(hashes.SHA256()).hex()

    return {
        "key_alg": key_alg,
        "key_bits": key_bits,
        "sig_hash": sig_hash,
        "serial": format(cert.serial_number, "x"),
        "not_after": cert.not_valid_after_utc.isoformat(),
        "expired": cert.not_valid_after_utc < datetime.now(timezone.utc),
        "fingerprint": fingerprint_hex,   # CSIGN-03 dedup key
    }
```

**EKU filter helper** (new — no direct analog; see RESEARCH Pattern 1):
```python
def _has_codesigning_eku(cert_obj) -> bool:
    """True when the cert carries EKU OID 1.3.6.1.5.5.7.3.3."""
    try:
        eku_ext = cert_obj.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        return EKU_CODE_SIGNING in eku_ext.value
    except x509.ExtensionNotFound:
        return False
    except Exception:
        return False
```

**Severity classification** (`smime_scanner.py` lines 103-123, adapted for EC<256):
```python
def _classify_codesign_severity(parsed: dict) -> "tuple[str | None, list[str]]":
    reasons: list[str] = []
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")
    key_alg = (parsed.get("key_alg") or "").upper()
    key_bits = parsed.get("key_bits")
    if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
        reasons.append("weak-rsa-key")
    # EC<256 is NOT covered by is_weak_cipher() — inline check required (RESEARCH Pitfall 6)
    if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:
        reasons.append("weak-ec-key")
    if reasons:
        return "HIGH", reasons
    return None, reasons   # SAFE — no finding
```

**LDAP bind+search** (`smime_scanner.py` lines 126-148 — copy `_bind_and_search` and `_parse_target` verbatim, adjust filter + attrs):
```python
# _parse_target: copy verbatim from smime_scanner.py lines 151-184
# _realm_to_base_dn: copy verbatim from smime_scanner.py lines 44-55

def _bind_and_search_codesign(host: str, port: int, base_dn: str, timeout: int):
    server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
    conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout)
    if not conn.bind():
        logger.warning("CODESIGN: anonymous bind rejected on %s:%d", host, port)
        return []
    return conn.extend.standard.paged_search(
        search_base=base_dn,
        search_filter="(userCertificate=*)",      # only userCertificate — NOT userSMIMECertificate
        search_scope=ldap3.SUBTREE,
        attributes=["userCertificate", "cn", "uid"],
        paged_size=500,
        generator=True,
    )
```

**Main scan function — LDAP path** (`smime_scanner.py` lines 187-291 — adapt `scan_smime_targets` structure):
```python
def scan_codesign_from_ldap(targets, timeout=10, logger=None, session_start=None, *, search_base=None):
    log = logger or logging.getLogger(__name__)
    if not LDAP3_AVAILABLE:
        log.warning("ldap3 not installed — code-signing LDAP scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list = []

    for target in targets:
        host, port, realm = _parse_target(target)
        base_dn = search_base or _realm_to_base_dn(realm or "")
        if not base_dn:
            log.warning("CODESIGN: no search base for %s (no realm; pass codesign_search_base)", host)
            continue

        try:
            entries = _bind_and_search_codesign(host, port, base_dn, timeout)
        except Exception as exc:
            log.warning("CODESIGN: bind/search failed for %s:%d: %s", host, port, safe_str(exc))
            results.append(CryptoEndpoint(
                host=host, port=port, protocol=CODE_SIGNING,
                service_detail=f"codesign-unreachable|base={base_dn}",
                scan_error=safe_str(exc), scan_error_category="exception", scanned_at=now,
            ))
            continue

        for entry in entries:
            if not isinstance(entry, dict): continue
            if entry.get("type") and entry.get("type") != "searchResEntry": continue
            raw = entry.get("raw_attributes") or {}
            user_dn = entry.get("dn") or ""
            for cert_bytes in (raw.get("userCertificate") or []):
                if not isinstance(cert_bytes, (bytes, bytearray)): continue
                cert_obj = None
                try:
                    cert_obj = load_der_x509_certificate(bytes(cert_bytes))
                except Exception:
                    try:
                        cert_obj = load_pem_x509_certificate(bytes(cert_bytes))
                    except Exception:
                        cert_obj = None
                if cert_obj is None: continue
                if not _has_codesigning_eku(cert_obj): continue   # EKU filter
                parsed = _parse_codesign_cert(bytes(cert_bytes))
                if parsed is None: continue
                severity, reasons = _classify_codesign_severity(parsed)
                if severity is None: continue  # SAFE — no endpoint emitted
                fp = parsed["fingerprint"]
                detail = f"{user_dn}|attr=userCertificate|serial={parsed['serial']}|fingerprint={fp}"
                scan_dict = dict(parsed); scan_dict["reasons"] = reasons; scan_dict["user_dn"] = user_dn
                results.append(CryptoEndpoint(
                    host=host, port=port, protocol=CODE_SIGNING,
                    cert_pubkey_alg=parsed["key_alg"], cert_pubkey_size=parsed["key_bits"],
                    cert_sig_alg=parsed.get("sig_hash") or None,
                    service_detail=detail, severity=severity,
                    smime_scan_json=json.dumps(scan_dict),   # reuse existing column
                    scanned_at=now,
                ))
    return results
```

**TLS EKU in-process check** (new function — no direct analog, follows same CryptoEndpoint emission shape):
```python
def scan_codesign_from_tls_endpoints(tls_endpoints, session_start=None, logger=None):
    """Filter already-captured TLS CryptoEndpoint objects for CodeSigning EKU.
    No new network I/O — operates on cert metadata already in memory.
    """
    log = logger or logging.getLogger(__name__)
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results = []
    for ep in tls_endpoints:
        # TLS scanner does not store raw DER; use surrogate dedup key for TLS path
        # (cert_subject + cert_pubkey_alg + not_after as compound key — see CSIGN-03 note)
        # EKU field not stored in CryptoEndpoint; this path relies on the scanner
        # checking tls_scan_json or a dedicated EKU field (implementation detail)
        pass  # Planner: implement per CSIGN-03 open question resolution
    return results
```

**Error handling pattern** (`smime_scanner.py` lines 224-238 — bind failure → CryptoEndpoint with scan_error):
```python
# On bind/search failure, emit error endpoint rather than raising:
except Exception as exc:
    log.warning("CODESIGN: bind/search failed for %s:%d: %s", host, port, safe_str(exc))
    err_ep = CryptoEndpoint(
        host=host, port=port, protocol=CODE_SIGNING,
        service_detail=f"codesign-unreachable|base={base_dn}",
        scan_error=safe_str(exc), scan_error_category="exception", scanned_at=now,
    )
    results.append(err_ep)
    continue
```

---

### `quirk/config.py` — ConnectorsCfg additions (config)

**Analog:** `quirk/config.py` lines 223-238 (SMIME block — exact structural mirror)

**Pattern** (lines 223-238):
```python
# Phase 79 SMIME-01: S/MIME LDAP discovery scanner enable flag
enable_smime: bool = False
# ...
smime_targets: list = field(default_factory=list)
smime_search_base: Optional[str] = None
smime_timeout: int = 10
```

**Phase 95 additions** (insert after SMIME block, before GCP block at line 239):
```python
# Phase 95 CSIGN-01: code-signing certificate inventory scanner enable flag
enable_codesign: bool = False
# LDAP targets for codesign userCertificate discovery (URLs or bare host[:port])
codesign_targets: list = field(default_factory=list)
codesign_search_base: Optional[str] = None
codesign_timeout: int = 10
```

Note: `_KNOWN_CONNECTOR_KEYS` at line 364 is derived from `dataclasses.fields(ConnectorsCfg)` automatically — no manual update needed when fields are declared as proper dataclass fields.

---

### `run_scan.py` — `_run_codesign_phase` + CLI flag + endpoints assembly (controller/wiring)

**Analog:** `run_scan.py` lines 1691-1733 (`_run_smime_phase` + `_run_adcs_phase`)

**CLI flag pattern** (`--openapi-spec` flag at lines 728-739 for flag shape; `_run_smime_phase` for enable-flag guard):
```python
# Add near the smime/adcs argparse block (currently no --inventory-smime flag;
# SMIME is enabled via YAML cfg.connectors.enable_smime).
# Per CONTEXT D-07 and RESEARCH Pattern 6, the CLI flag is --inventory-code-signing
# which sets args.inventory_code_signing = True.
# No separate argparse block needed if using YAML enable_codesign flag (mirrors smime pattern).
# The CONTEXT says "--inventory-code-signing CLI flag gates the whole feature."
# Add to argparse:
parser.add_argument(
    "--inventory-code-signing",
    dest="inventory_code_signing",
    action="store_true",
    default=False,
    help="Inventory code-signing certificates from LDAP userCertificate and TLS EKU checks (CSIGN-01).",
)
```

**Phase function pattern** (`run_scan.py` lines 1691-1733):
```python
# ── Code-signing inventory (Phase 95 CSIGN-01) ────────────────────
def _run_codesign_phase():
    if not (getattr(args, "inventory_code_signing", False)
            and getattr(cfg.connectors, "codesign_targets", None)):
        return []
    from quirk.scanner.codesign_scanner import scan_codesign_from_ldap
    eps = scan_codesign_from_ldap(
        targets=cfg.connectors.codesign_targets,
        timeout=getattr(cfg.connectors, "codesign_timeout", 10),
        logger=logger,
        session_start=session_start,
        search_base=getattr(cfg.connectors, "codesign_search_base", None),
    )
    logger.info("CODE_SIGNING scan: %d endpoints from %d targets",
                len(eps), len(cfg.connectors.codesign_targets))
    return eps
codesign_endpoints = _wrapped_phase(
    run_stats, "codesign_scanning", "codesign_scanner",
    _run_codesign_phase, error_endpoints, logger,
) or []
```

**`_dar_protocols` update** (`run_scan.py` line 1503):
```python
# Current:
_dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS")
# Phase 95 target:
_dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML",
                  "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING")
```

**Resume path** (mirrors lines 1512-1513):
```python
# In the `if _stage_completed(_completed_stages, "data_at_rest"):` block,
# add after adcs_endpoints:
codesign_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "CODE_SIGNING"]
```

**Endpoints assembly** (`run_scan.py` lines 1948-1965 — add `+ codesign_endpoints` after `adcs_endpoints`):
```python
endpoints = (inventory_endpoints + tls_endpoints + ssh_endpoints
             + pqc_endpoints
             + jwt_endpoints + container_endpoints + source_endpoints
             + openapi_endpoints
             + bearer_token_endpoints
             + aws_endpoints + azure_endpoints + gcp_endpoints
             + db_endpoints
             + s3_endpoints + blob_endpoints + gcs_storage_endpoints
             + k8s_endpoints
             + dnssec_endpoints + saml_endpoints + kerberos_endpoints
             + smime_endpoints
             + adcs_endpoints
             + codesign_endpoints           # Phase 95 CSIGN-01
             + vault_endpoints
             + email_endpoints
             + kafka_endpoints + rabbit_endpoints + redis_endpoints
             + error_endpoints)
```

---

### `quirk/cbom/builder.py` — Pass-1 elif, Pass-2 skip, Pass-3 skip, fingerprint dedup (service, transform)

**Analog:** `quirk/cbom/builder.py` lines 508-527 (SMIME/ADCS Pass-1 branches); lines 619-627 (Pass-2 skip); lines 705-714 (Pass-3 skip)

**Pass-1 branch** (insert after ADCS elif at line 525):
```python
elif ep.protocol == "CODE_SIGNING":
    # CODE_SIGNING: cert_pubkey_alg holds key algorithm (RSA, ECDSA) from
    # userCertificate / TLS EKU check. Pass-1 only — Pass-2 skip (fingerprint
    # dedup pass handles cert components); Pass-3 skip (not a transport protocol).
    # Phase 95 CSIGN-01.
    if ep.cert_pubkey_alg:
        _register_algorithm(
            ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
        )
```

**Pass-2 skip tuple** (lines 620-624 — add `"CODE_SIGNING"`):
```python
if ep.protocol in (
    "SSH", "BEARER_TOKEN", "JWT", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC",
    "SMIME", "ADCS", "CODE_SIGNING",   # CODE_SIGNING added Phase 95 CSIGN-03
    *DAR_SKIP_PROTOCOLS,
    *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue
```

**Pass-3 skip tuple** (lines 705-710 — add `"CODE_SIGNING"`):
```python
elif ep.protocol in (
    "JWT", "BEARER_TOKEN", "CONTAINER", "SOURCE", "AWS", "AZURE",
    "DNSSEC", "SAML", "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING",  # Phase 95
    *DAR_SKIP_PROTOCOLS,
    *MOTION_PLAINTEXT_PROTOCOLS,
):
    continue
```

**Fingerprint dedup pass** (new — insert between Pass-1 and Pass-2, or as a sub-step in Pass-2):
```python
# CSIGN-03: Build fingerprint → bom_ref lookup from CODE_SIGNING endpoints.
# Two CODE_SIGNING endpoints with the same SHA-256 fingerprint = same cert;
# emit only the first, annotate subsequent matches with a CycloneDX Property.
# Fingerprint is stored as "fingerprint=<hex>" token in service_detail.
_codesign_fp_seen: dict[str, str] = {}  # fp_hex → bom_ref of first emitter

def _extract_fp(service_detail: str | None) -> str | None:
    if not service_detail:
        return None
    for part in service_detail.split("|"):
        if part.startswith("fingerprint="):
            return part[len("fingerprint="):]
    return None

# After Pass-2, add dedup pass for CODE_SIGNING cert components:
for ep in endpoints:
    if ep.protocol != "CODE_SIGNING":
        continue
    if not ep.cert_pubkey_alg:
        continue
    fp = _extract_fp(ep.service_detail)
    if fp and fp in _codesign_fp_seen:
        # Duplicate — annotate existing component rather than emitting new one
        continue   # or add Property("quirk:code-signing-eku", "true") to existing bom_ref
    # Emit cert component
    cert_bom_ref = f"crypto/certificate/codesign/{ep.host}:{fp or ep.host}"
    if fp:
        _codesign_fp_seen[fp] = cert_bom_ref
    # ... build CertificateProperties as in Pass-2 TLS pattern (lines 644-663)
```

---

### `quirk/intelligence/evidence.py` — `_PROTOCOL_KEYS` + CODE_SIGNING counter (service, transform)

**Analog:** `quirk/intelligence/evidence.py` lines 11-17 (`_PROTOCOL_KEYS`); lines 121-123 + 305-321 (Phase 94 bearer/openapi counter pattern)

**`_PROTOCOL_KEYS` update** (lines 11-17):
```python
# Current (ends at line 17):
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT",
                  "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                  # Phase 94 — bearer-token and OpenAPI spec analysis protocols
                  "BEARER_TOKEN", "OPENAPI")

# Phase 95 target (add CODE_SIGNING):
_PROTOCOL_KEYS = ("TLS", "HTTP", "SSH", "UNKNOWN", "KERBEROS", "SAML", "DNSSEC",
                  "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT",
                  "CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL",
                  "BEARER_TOKEN", "OPENAPI",
                  # Phase 95 — code-signing certificate inventory
                  "CODE_SIGNING")
```

**Counter declaration** (after line 123, following Phase 94 pattern):
```python
# Phase 95 — Code-signing weak algorithm counter (CSIGN-02, SCORE-01)
codesign_weak_algo_count = 0    # CODE_SIGNING endpoints with weak RSA/EC/SHA-1
```

**Counter increment branch** (after the OPENAPI elif block at lines 314-321, following exact Phase 94 shape):
```python
# ---- Phase 95 — Code-signing weak algorithm counter (CSIGN-02, SCORE-01) ----
elif proto == "CODE_SIGNING":
    # Increment when service_detail contains "weak" — scanner encodes this
    # via reasons list in smime_scan_json and appends reason tokens to service_detail.
    # Mirrors the BEARER_TOKEN pattern (lines 306-312) and SMIME service_detail check.
    _cs_detail = str(getattr(ep, "service_detail", "") or "").lower()
    if "weak" in _cs_detail:
        codesign_weak_algo_count += 1
```

**Return dict update** (after line 471, following Phase 94 pair pattern):
```python
"codesign_weak_algo_count": codesign_weak_algo_count,
"agility_codesign_weak_algo_ratio": round(codesign_weak_algo_count / total_endpoints, 4) if total_endpoints else 0.0,
```

---

### `quirk/intelligence/scoring.py` — SCORE_WEIGHTS + agility block (service, transform)

**Analog:** `quirk/intelligence/scoring.py` lines 54-60 (SCORE_WEIGHTS agility block); lines 225-233 (Phase 94 agility_impacts extension)

**SCORE_WEIGHTS addition** (after line 60, following Phase 94 pair):
```python
# Current (lines 59-60):
"agility_weak_jwt_alg_ratio": 6.0,      # Phase 94 SCORE-01
"agility_openapi_plaintext_ratio": 4.0, # Phase 94 SCORE-01

# Phase 95 addition (sum 293.0 → 299.0, count 39 → 40):
"agility_codesign_weak_algo_ratio": 6.0,  # Phase 95 SCORE-01 — weak RSA/EC/SHA-1 on code-signing cert
```

**agility_impacts extension** (after lines 228-233, following Phase 94 block):
```python
# Phase 94 SCORE-01 block (lines 226-233):
bearer_weak_jwt_alg = max(0, _as_int(evidence.get("bearer_token_weak_alg_count", 0)))
openapi_plaintext = max(0, _as_int(evidence.get("openapi_plaintext_server_count", 0)))
agility_impacts.extend([
    ("Bearer token weak algorithm",
     -_ratio(bearer_weak_jwt_alg, denom) * w["agility_weak_jwt_alg_ratio"]),
    ("OpenAPI plaintext servers (http://)",
     -_ratio(openapi_plaintext, denom) * w["agility_openapi_plaintext_ratio"]),
])

# Phase 95 SCORE-01 addition — append to agility_impacts (not extend; mirror shape):
codesign_weak_algo = max(0, _as_int(evidence.get("codesign_weak_algo_count", 0)))
agility_impacts.append((
    "Code-signing cert weak algorithm",
    -_ratio(codesign_weak_algo, denom) * w["agility_codesign_weak_algo_ratio"],
))
```

---

### `tests/test_score_weights_invariant.py` — update assertions (test)

**Analog:** Same file (`tests/test_score_weights_invariant.py` lines 5-44)

**Sum assertion** (line 27):
```python
# Current:
assert abs(sum(SCORE_WEIGHTS.values()) - 293.0) < 1e-9, (...)
# Phase 95 target:
assert abs(sum(SCORE_WEIGHTS.values()) - 299.0) < 1e-9, (...)
```

**Count assertion** (line 44):
```python
# Current:
assert len(SCORE_WEIGHTS) == 39
# Phase 95 target:
assert len(SCORE_WEIGHTS) == 40
```

**Docstring update** (test_score_weights_sum_invariant docstring, after Phase 94 paragraph):
```
Phase 95 SCORE-01: bumped from 293.0 -> 299.0 (+6.0) for code-signing weak-algo signal:
  - agility_codesign_weak_algo_ratio: +1 entry at +6.0
Net delta = +1 entry / +6.0 sum (39 -> 40, 293.0 -> 299.0).
```

---

### `tests/test_codesign_scanner.py` (test)

**Analog:** `tests/test_smime_scanner.py` (near-exact copy structure)

**Module structure** (`test_smime_scanner.py` lines 1-64):
```python
"""Phase 95 Plan XX — Unit tests for quirk/scanner/codesign_scanner.py.

Mocks the LDAP bind+paged-search layer by patching
`quirk.scanner.codesign_scanner._bind_and_search_codesign` to return a
synthetic iterable of searchResEntry dicts carrying pre-built DER fixtures.
"""
from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from quirk.scanner import codesign_scanner
from quirk.scanner.codesign_scanner import scan_codesign_from_ldap

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "codesign"

def _load(name: str) -> bytes:
    return (FIXTURE_DIR / name).read_bytes()

def _entry(uid: str, der: bytes) -> dict:
    """Build a fake ldap3 searchResEntry dict."""
    return {
        "type": "searchResEntry",
        "dn": f"uid={uid},ou=people,dc=quirk,dc=lab",
        "raw_attributes": {
            "userCertificate": [der],
            "cn": [uid.encode()],
            "uid": [uid.encode()],
        },
    }

def _target() -> SimpleNamespace:
    return SimpleNamespace(host="ldaps-openldap", port=636, realm="QUIRK.LAB")

def _run_with_entries(entries: list[dict]) -> list:
    with patch.object(codesign_scanner, "LDAP3_AVAILABLE", True), \
         patch.object(codesign_scanner, "_bind_and_search_codesign", return_value=iter(entries)):
        return scan_codesign_from_ldap([_target()], timeout=5)
```

**Key test function shapes** (mirror `test_smime_scanner.py` lines 70-141):
```python
# CSIGN-02 tests (mirrors test_alice_rsa1024_sha1_emits_high_with_two_reasons):
def test_rsa1024_sha1_emits_high():
    eps = _run_with_entries([_entry("rsa1024sha1", _load("codesign_rsa1024_sha1.der"))])
    assert len(eps) == 1
    assert eps[0].protocol == "CODE_SIGNING"   # UPPERCASE — critical
    assert eps[0].severity == "HIGH"
    blob = json.loads(eps[0].smime_scan_json)
    assert "weak-signing-alg" in blob["reasons"]
    assert "weak-rsa-key" in blob["reasons"]

def test_ec192_emits_high():
    """EC<256 → HIGH (not covered by is_weak_cipher — inline key-size check)."""
    eps = _run_with_entries([_entry("ec192", _load("codesign_ec192.der"))])
    assert len(eps) == 1
    assert eps[0].severity == "HIGH"
    blob = json.loads(eps[0].smime_scan_json)
    assert "weak-ec-key" in blob["reasons"]

def test_strong_rsa2048_sha256_safe():
    """Strong cert → SAFE, zero endpoints emitted."""
    eps = _run_with_entries([_entry("strong", _load("codesign_rsa2048_sha256.der"))])
    assert eps == []

# CSIGN-01 — non-CodeSigning EKU cert filtered out:
def test_non_codesign_eku_filtered():
    eps = _run_with_entries([_entry("noeku", _load("codesign_rsa2048_sha256_noncoding.der"))])
    assert eps == []

# CSIGN-03 — fingerprint dedup:
def test_cbom_dedup_stable_count():
    """Same cert seen twice via two CODE_SIGNING endpoints → stable CBOM component count."""
    from quirk.cbom.builder import build_cbom
    der = _load("codesign_rsa1024_sha1.der")
    eps = _run_with_entries([_entry("dup1", der), _entry("dup2", der)])
    bom = build_cbom(eps)
    # Assert component count is stable (no duplicate cert components for same fingerprint)
    cert_components = [c for c in bom.components if ...]
    assert len(cert_components) == 1   # Exact count depends on dedup implementation
```

---

### `tests/fixtures/codesign/` — DER cert fixtures (test fixture)

**Analog:** `quantum-chaos-enterprise-lab/smime/certs/regen.sh` (developer tool for generating DER blobs)

**Required fixtures** (per RESEARCH Validation Architecture Wave 0 Gaps):
```
tests/fixtures/codesign/
├── codesign_rsa1024_sha1.der          # RSA-1024 SHA-1 + CodeSigning EKU → HIGH (weak-signing + weak-rsa-key)
├── codesign_ec192.der                 # EC-192 + CodeSigning EKU → HIGH (weak-ec-key)
├── codesign_rsa2048_sha256.der        # RSA-2048 SHA-256 + CodeSigning EKU → SAFE (filtered out)
└── codesign_rsa2048_sha256_noncoding.der  # RSA-2048 SHA-256 WITHOUT CodeSigning EKU → filtered (CSIGN-01)
```

**Generation pattern** (mirror `smime/certs/regen.sh` + add `-addext extendedKeyUsage=codeSigning`):
```bash
# CodeSigning EKU: extendedKeyUsage = 1.3.6.1.5.5.7.3.3
openssl req -x509 -newkey rsa:1024 -sha1 -keyout /tmp/key.pem \
  -out tests/fixtures/codesign/codesign_rsa1024_sha1.der \
  -outform DER -days 36500 -nodes \
  -subj "/CN=codesign-weak/O=QUIRK Chaos Lab" \
  -addext "extendedKeyUsage=codeSigning"

# EC-192 fixture (uses prime192v1 curve — key_size = 192):
openssl req -x509 -newkey ec:<(openssl ecparam -name prime192v1) -sha256 \
  -keyout /tmp/key.pem \
  -out tests/fixtures/codesign/codesign_ec192.der \
  -outform DER -days 36500 -nodes \
  -subj "/CN=codesign-ec192/O=QUIRK Chaos Lab" \
  -addext "extendedKeyUsage=codeSigning"
```

---

### `quantum-chaos-enterprise-lab/docker-compose.yml` — ldaps seed additions (config)

**Analog:** `docker-compose.yml` lines 784-801 (smime-seed sidecar pattern)

**Key insight from RESEARCH Pitfall 5:** The `ldaps` profile currently has NO seed sidecar and NO user data — it is only a TLS LDAP server for TLS cert scanning. Adding a code-signing cert fixture requires adding an OpenLDAP user with `userCertificate` containing a CodeSigning EKU cert. This means adding BOTH an OpenLDAP service with seed data AND a seed sidecar to the `ldaps` profile, or extending the existing `ldaps` service with a new sidecar.

**Seed sidecar pattern** (copy from smime-seed block, lines 784-801):
```yaml
# Extend existing ldaps profile with a code-signing fixture user
  ldaps-codesign-seed:
    image: bitnamilegacy/openldap:2.6.10-debian-12-r4
    profiles: ["ldaps"]
    depends_on:
      ldaps:
        condition: service_started
    entrypoint: ["/bin/sh", "-c"]
    command:
      - "sleep 5 && ldapadd -c -x -H ldap://ldaps:389 -D 'cn=admin,dc=chaos,dc=local' -w admin -f /ldif/codesign-users.ldif; rc=$$?; if [ $$rc -eq 0 ] || [ $$rc -eq 68 ]; then exit 0; else exit $$rc; fi"
    volumes:
      - ./ldaps/ldif:/ldif:ro
      - ./ldaps/certs:/codesign-certs:ro
    restart: "no"
```

Note: `_derive_all_profiles()` in `lab.sh` reads profiles from docker-compose.yml dynamically — the `ldaps` profile is already included in `all`. No change to `lab.sh` ALL_PROFILES logic is needed (RESEARCH confirms this).

---

### `quantum-chaos-enterprise-lab/expected_results_v4.md` — ldaps oracle update (documentation/oracle)

**Analog:** `expected_results_v4.md` lines 264-288 (ldaps profile section) + lines 510-540 (smime section as table structure model)

**Pattern** — append to the ldaps profile section (after line 288):
```markdown
## Profile: ldaps — Code-Signing Fixture

*Added Phase 95 CSIGN-01: the `ldaps` service now also carries a user with a
`userCertificate` attribute containing a cert with CodeSigning EKU (1.3.6.1.5.5.7.3.3)
and a weak RSA-1024 / SHA-1 signature — exercises the code-signing scanner.*

| User DN | Certificate | Expected Finding | Severity |
|---|---|---|---|
| uid=codesign-weak,ou=people,dc=chaos,dc=local | RSA-1024 / SHA-1 + CodeSigning EKU | CODE-SIGN/weak-algorithm | HIGH |

**Expected:** CODE_SIGNING scanner returns 1 HIGH finding from the ldaps profile.
```

---

### `quantum-chaos-enterprise-lab/lab.sh` — verify _derive_all_profiles (config)

**Analog:** `lab.sh` lines 58-168 (`_derive_all_profiles`)

**Key finding from RESEARCH (Secondary confidence):** `_derive_all_profiles()` reads profiles dynamically from docker-compose.yml — no hardcoded ALL_PROFILES list exists. The `ldaps` profile is already included because it is defined in compose. Adding a `ldaps-codesign-seed` service under `profiles: ["ldaps"]` adds it to the ldaps profile without touching `lab.sh`.

**Verification action:** Confirm `_derive_all_profiles` reads the compose file — no edit to `lab.sh` is needed for this phase.

---

## Shared Patterns

### Protocol casing — UPPERCASE string constant
**Source:** `quirk/intelligence/evidence.py` lines 11-17 (`_PROTOCOL_KEYS` uses `"CODE_SIGNING"`)
**Apply to:** Every file that references `ep.protocol` for CODE_SIGNING
```python
# In codesign_scanner.py module top — ALWAYS use the constant, never the literal:
CODE_SIGNING = "CODE_SIGNING"
# All CryptoEndpoint emissions must use: protocol=CODE_SIGNING
```

### Anonymous LDAP bind + paged search
**Source:** `quirk/scanner/smime_scanner.py` lines 126-148
**Apply to:** `codesign_scanner.py` `_bind_and_search_codesign`
```python
server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout)
if not conn.bind():
    logger.warning("...: anonymous bind rejected on %s:%d", host, port)
    return []
return conn.extend.standard.paged_search(
    ..., paged_size=500, generator=True,
)
```

### Error handling — bind failure → CryptoEndpoint (never raise)
**Source:** `quirk/scanner/smime_scanner.py` lines 224-238
**Apply to:** `codesign_scanner.scan_codesign_from_ldap`
```python
except Exception as exc:
    log.warning("CODESIGN: bind/search failed for %s:%d: %s", host, port, safe_str(exc))
    results.append(CryptoEndpoint(
        host=host, port=port, protocol=CODE_SIGNING,
        service_detail=f"codesign-unreachable|base={base_dn}",
        scan_error=safe_str(exc), scan_error_category="exception", scanned_at=now,
    ))
    continue
```

### DER/PEM dual-parse with try/except
**Source:** `quirk/scanner/smime_scanner.py` lines 63-72
**Apply to:** `codesign_scanner._parse_codesign_cert`
```python
try:
    cert = load_der_x509_certificate(cert_bytes)
except Exception as exc_der:
    logger.debug("CODESIGN DER parse failed, attempting PEM: %s", safe_str(exc_der))
    try:
        cert = load_pem_x509_certificate(cert_bytes)
    except Exception as exc_pem:
        logger.debug("CODESIGN PEM parse also failed: %s", safe_str(exc_pem))
        return None
```

### safe_str() on all LDAP-derived strings
**Source:** `quirk/scanner/smime_scanner.py` throughout (every `.warning()` call uses `safe_str(exc)`)
**Apply to:** All `codesign_scanner.py` logging calls involving LDAP data
```python
from quirk.util.safe_exc import safe_str
# Always: log.warning("...: %s", safe_str(exc))
# Never: str(exc) or f"{exc}"
```

### _wrapped_phase invocation shape
**Source:** `run_scan.py` lines 1707-1710
**Apply to:** `run_scan.py` `_run_codesign_phase`
```python
codesign_endpoints = _wrapped_phase(
    run_stats, "codesign_scanning", "codesign_scanner",
    _run_codesign_phase, error_endpoints, logger,
) or []
```

### Chaos lab seed sidecar idempotency
**Source:** `docker-compose.yml` lines 790-798 (smime-seed sidecar `ldapadd -c` with exit-68 swallow)
**Apply to:** `ldaps-codesign-seed` sidecar
```bash
# ldapadd -c = continue on already-exists; swallow exit 68 (LDAP_ALREADY_EXISTS)
sleep 5 && ldapadd -c -x -H ldap://ldaps:389 -D '...' -w admin -f /ldif/codesign-users.ldif; \
rc=$$?; if [ $$rc -eq 0 ] || [ $$rc -eq 68 ]; then exit 0; else exit $$rc; fi
```

---

## No Analog Found

No files are without a close analog for Phase 95. All new files have strong existing precedents.

---

## Critical Caveats for Planner

1. **EC<256 is NOT covered by `is_weak_cipher()`** — `_classify_codesign_severity` must add an inline `if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:` check alongside the RSA<2048 check. Do NOT add `"ECDSA-256"` to `_WEAK_CIPHER_TOKENS` (substring match would falsely flag `AES-256`).

2. **`_CODESIGN_ATTRS = ("userCertificate",)` only** — do NOT copy `_SMIME_ATTRS = ("userCertificate", "userSMIMECertificate")`. The code-signing EKU filter provides additional specificity; the smime cert attribute is out of scope (RESEARCH Pitfall 4).

3. **CBOM dedup open question** — RESEARCH Open Question 1 notes TLS scanner does not store raw DER in `CryptoEndpoint`. The CSIGN-03 dedup test must specify its exact contract: fingerprint-vs-fingerprint among CODE_SIGNING endpoints (two LDAP entries for the same cert), not cross-protocol TLS vs CODE_SIGNING dedup. The annotation approach adds a CycloneDX Property to existing TLS cert components when the same fingerprint appears.

4. **Chaos lab LDAP base DN mismatch** — the `ldaps` profile uses `dc=chaos,dc=local` (line 745 docker-compose.yml), but `smime` uses `dc=quirk,dc=lab`. The code-signing LDIF and scanner config must use `dc=chaos,dc=local`.

5. **SCORE_WEIGHTS dual invariant** — both `test_score_weights_sum_invariant` (293.0 → 299.0) AND `test_score_weights_count_invariant` (39 → 40) must be updated in the same commit. Missing either causes CI failure.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/cbom/`, `quirk/intelligence/`, `quirk/config.py`, `run_scan.py`, `tests/`, `quantum-chaos-enterprise-lab/`
**Files scanned:** 14 source files read
**Pattern extraction date:** 2026-05-23
