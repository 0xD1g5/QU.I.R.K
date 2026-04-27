# Email Protocol TLS Scanning — Implementation Research
# QU.I.R.K. v4.4 Data in Motion

**Researched:** 2026-04-27
**Confidence:** HIGH (sslyze: Context7 authoritative docs; ports: RFC standards; chaos lab: official images; CBOM: classifier.py inspection; quantum risk: NIST official docs)

---

## 1. sslyze STARTTLS Support

### Native Support Confirmed (HIGH confidence)

sslyze natively supports STARTTLS for SMTP, IMAP, and POP3 via `ProtocolWithOpportunisticTlsEnum`. No subprocess wrappers or additional libraries needed. This matches the existing `tls_scanner.py` pattern exactly.

**Supported STARTTLS protocols in `ProtocolWithOpportunisticTlsEnum`:**

```
SMTP, IMAP, POP3, XMPP, XMPP_SERVER, FTP, LDAP, RDP, POSTGRES
```

Source: Context7 (`/nabla-c0d3/sslyze`) + https://blog.adqt.fr/sslyze/documentation/running-a-scan-in-python.html

### API Call Pattern

The only change from the existing `_scan_one_sslyze()` implementation is passing `tls_opportunistic_encryption` in `ServerNetworkConfiguration`. All `ScanCommand.*` values, result parsing, and error handling are identical.

```python
from sslyze import (
    Scanner as SslyzeScanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ServerNetworkConfiguration,
    ProtocolWithOpportunisticTlsEnum,
    ScanCommand,
    ScanCommandAttemptStatusEnum,
    ServerScanStatusEnum,
)

def _scan_one_email_sslyze(
    host: str,
    port: int,
    starttls_protocol: ProtocolWithOpportunisticTlsEnum,
    timeout: int,
    logger=None,
):
    """Scan an email protocol endpoint using sslyze STARTTLS.

    starttls_protocol should be one of:
        ProtocolWithOpportunisticTlsEnum.SMTP   -- ports 25, 587
        ProtocolWithOpportunisticTlsEnum.IMAP   -- port 143
        ProtocolWithOpportunisticTlsEnum.POP3   -- port 110

    For implicit TLS (ports 465, 993, 995), pass starttls_protocol=None
    and the existing _scan_one_sslyze() handles it without modification.
    """
    scan_request = ServerScanRequest(
        server_location=ServerNetworkLocation(hostname=host, port=port),
        network_configuration=ServerNetworkConfiguration(
            tls_server_name_indication=host,
            tls_opportunistic_encryption=starttls_protocol,   # KEY DIFFERENCE
            network_timeout=timeout,
        ),
        scan_commands={
            ScanCommand.CERTIFICATE_INFO,
            ScanCommand.SSL_2_0_CIPHER_SUITES,
            ScanCommand.SSL_3_0_CIPHER_SUITES,
            ScanCommand.TLS_1_0_CIPHER_SUITES,
            ScanCommand.TLS_1_1_CIPHER_SUITES,
            ScanCommand.TLS_1_2_CIPHER_SUITES,
            ScanCommand.TLS_1_3_CIPHER_SUITES,
            ScanCommand.ELLIPTIC_CURVES,
        },
    )

    scanner = SslyzeScanner(per_server_concurrent_connections_limit=2)
    scanner.queue_scans([scan_request])
    results = list(scanner.get_results())

    if not results:
        return None

    server_result = results[0]
    if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
        return None  # trigger socket fallback

    # Result parsing is IDENTICAL to existing _scan_one_sslyze():
    scan = server_result.scan_result
    # cert_attempt = scan.certificate_info
    # tls_1_2_attempt = scan.tls_1_2_cipher_suites
    # ... same extraction logic as tls_scanner.py lines 179–308
```

### What Scan Results Return

The result object structure is identical to a standard TLS scan:

- `scan.certificate_info` — cert chain, leaf subject/issuer, SANs, key type + size, validity dates
- `scan.tls_1_2_cipher_suites.result.accepted_cipher_suites` — list of `CipherSuiteAcceptedByServer`
- `scan.tls_1_3_cipher_suites.result.accepted_cipher_suites` — TLS 1.3 suites
- `scan.ssl_2_0_cipher_suites`, `scan.ssl_3_0_cipher_suites` — legacy protocol detection
- `scan.elliptic_curves.result.supported_curves` — EC curve names

**Protocol label stored in `ep.protocol` field:** Use `"SMTP-STARTTLS"`, `"IMAP-STARTTLS"`, `"POP3-STARTTLS"`, `"SMTPS"`, `"IMAPS"`, `"POP3S"` to distinguish session type in the CBOM and findings.

### Additional sslyze config for SMTP

`ServerNetworkConfiguration` has an `smtp_ehlo_hostname` parameter for SMTP sessions. Default is fine for scanning. If the target requires a specific EHLO hostname, it can be passed:

```python
ServerNetworkConfiguration(
    tls_server_name_indication=host,
    tls_opportunistic_encryption=ProtocolWithOpportunisticTlsEnum.SMTP,
    smtp_ehlo_hostname="scanner.quirk.local",  # optional, avoids EHLO rejection
    network_timeout=timeout,
)
```

---

## 2. Socket-Level Fallback

When sslyze fails (connectivity error, STARTTLS rejection, timeout), a stdlib fallback using `smtplib`, `imaplib`, and raw socket+ssl is needed.

### Design Decision

Use protocol-specific stdlib modules (`smtplib.SMTP`, `imaplib.IMAP4`, `poplib.POP3`) for STARTTLS negotiation because they handle the protocol handshake (EHLO, CAPABILITY, STLS) correctly. Then extract cert + cipher from the wrapped socket.

### SMTP STARTTLS Fallback

```python
import smtplib
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def _email_fallback_smtp(host: str, port: int, timeout: int):
    """Returns (tls_version, cipher_name, der_cert_bytes) or raises."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with smtplib.SMTP(host, port, timeout=timeout) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ctx)
        smtp.ehlo()
        # Unwrap the socket to get TLS details
        ssock = smtp.sock  # The wrapped SSL socket after STARTTLS
        tls_version = ssock.version()
        cipher = ssock.cipher()  # (name, protocol_version, key_bits)
        der = ssock.getpeercert(binary_form=True)
    return tls_version, cipher[0] if cipher else None, der
```

### IMAP STARTTLS Fallback

```python
import imaplib
import ssl

def _email_fallback_imap_starttls(host: str, port: int, timeout: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    imap = imaplib.IMAP4(host, port)
    imap.starttls(ssl_context=ctx)
    ssock = imap.socket()
    tls_version = ssock.version()
    cipher = ssock.cipher()
    der = ssock.getpeercert(binary_form=True)
    imap.logout()
    return tls_version, cipher[0] if cipher else None, der
```

### IMAP Implicit TLS (port 993) Fallback

```python
import imaplib

def _email_fallback_imaps(host: str, port: int, timeout: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    imap = imaplib.IMAP4_SSL(host, port, ssl_context=ctx)
    ssock = imap.socket()
    tls_version = ssock.version()
    cipher = ssock.cipher()
    der = ssock.getpeercert(binary_form=True)
    imap.logout()
    return tls_version, cipher[0] if cipher else None, der
```

### POP3 STARTTLS Fallback

```python
import poplib

def _email_fallback_pop3(host: str, port: int, timeout: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    pop = poplib.POP3(host, port, timeout=timeout)
    pop.stls(context=ctx)
    ssock = pop.sock  # wrapped SSL socket after STLS
    tls_version = ssock.version()
    cipher = ssock.cipher()
    der = ssock.getpeercert(binary_form=True)
    pop.quit()
    return tls_version, cipher[0] if cipher else None, der
```

### POP3S (port 995) Fallback

```python
import poplib

def _email_fallback_pop3s(host: str, port: int, timeout: int):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    pop = poplib.POP3_SSL(host, port, context=ctx, timeout=timeout)
    ssock = pop.sock
    tls_version = ssock.version()
    cipher = ssock.cipher()
    der = ssock.getpeercert(binary_form=True)
    pop.quit()
    return tls_version, cipher[0] if cipher else None, der
```

### Fallback Certificate Extraction

After obtaining `der` bytes, use the existing `_pubkey_info()` and `_extract_sans()` helpers from `tls_scanner.py`:

```python
from cryptography import x509
from cryptography.hazmat.backends import default_backend

cert = x509.load_der_x509_certificate(der, default_backend())
ep.cert_subject = cert.subject.rfc4514_string()
ep.cert_issuer = cert.issuer.rfc4514_string()
# ... same pattern as tls_scanner._scan_one_fallback() lines 366-389
```

### Important: smtplib socket access after STARTTLS

After `smtp.starttls()`, `smtp.sock` is the `ssl.SSLSocket`. The `smtplib` source confirms this — the socket is wrapped in-place. The `getpeercert(binary_form=True)` call works on it directly. If `smtp.sock` raises AttributeError in some Python versions, use `smtp.file._sock` as a fallback.

---

## 3. Port Conventions

### Standard Port Map

| Port | Protocol | TLS Mode | Scanner Behavior |
|------|----------|----------|-----------------|
| 25   | SMTP     | STARTTLS (opportunistic) | sslyze: `ProtocolWithOpportunisticTlsEnum.SMTP`; fallback: `smtplib.SMTP + starttls()` |
| 465  | SMTPS    | Implicit TLS (wrapped) | sslyze: no `tls_opportunistic_encryption`; fallback: direct `ssl.wrap_socket()` |
| 587  | SMTP submission | STARTTLS (mandatory) | sslyze: `ProtocolWithOpportunisticTlsEnum.SMTP`; most common MSA port |
| 143  | IMAP     | STARTTLS | sslyze: `ProtocolWithOpportunisticTlsEnum.IMAP`; fallback: `imaplib.IMAP4 + starttls()` |
| 993  | IMAPS    | Implicit TLS | sslyze: no `tls_opportunistic_encryption`; fallback: `imaplib.IMAP4_SSL` |
| 110  | POP3     | STARTTLS | sslyze: `ProtocolWithOpportunisticTlsEnum.POP3`; fallback: `poplib.POP3 + stls()` |
| 995  | POP3S    | Implicit TLS | sslyze: no `tls_opportunistic_encryption`; fallback: `poplib.POP3_SSL` |

### Recommended Default Scan Profile

```python
EMAIL_DEFAULT_PORTS = [
    # (port, protocol_label, starttls_enum_or_None)
    (25,  "SMTP-STARTTLS", ProtocolWithOpportunisticTlsEnum.SMTP),
    (465, "SMTPS",         None),   # implicit TLS
    (587, "SMTP-STARTTLS", ProtocolWithOpportunisticTlsEnum.SMTP),
    (143, "IMAP-STARTTLS", ProtocolWithOpportunisticTlsEnum.IMAP),
    (993, "IMAPS",         None),   # implicit TLS
    (110, "POP3-STARTTLS", ProtocolWithOpportunisticTlsEnum.POP3),
    (995, "POP3S",         None),   # implicit TLS
]
```

Port 25 is often blocked on residential ISPs and cloud VMs. The scanner should gracefully handle `CONNECTION_REFUSED` on port 25 without failing the whole scan — use the existing `_categorize_tls_error()` pattern.

Port 587 is the most commonly open and most important for scanner validation in the chaos lab.

### Consulting Default Targets

For the interactive wizard (`quirk --config` interactive mode), the email surface target input should default to the customer's own MX records. The `quirk` config could accept `email_targets: ["mail.example.com"]` and auto-expand to all 7 ports.

---

## 4. Chaos Lab Docker Images

### Recommended Approach: Postfix + Dovecot in a Single Custom Container

**Why not off-the-shelf docker-mailserver or mailcow:**
Both enforce modern security defaults and require significant configuration to deliberately weaken. docker-mailserver v12+ removed TLS_LEVEL=intermediate (TLS 1.0/1.1) support entirely. Mailcow is too heavyweight (multi-container stack) for a chaos lab scenario. Neither is suitable out-of-the-box for "intentionally weak" configurations.

**Recommended: Custom Dockerfile with ubuntu:22.04 + Postfix + Dovecot**

This is the same pattern used for `ssh-weak` (ubuntu:18.04 + OpenSSH 7.6 with weak KEX). A Dockerfile that:

1. Installs Postfix + Dovecot
2. Generates a self-signed cert (optionally expired or RSA-1024)
3. Configures Postfix to enable TLS 1.0/1.1 and weak ciphers via `main.cf` overrides
4. Configures Dovecot similarly

**Key Postfix `main.cf` settings for weak scenarios:**

```ini
# Allow TLS 1.0 and 1.1 (weak — quantum-vulnerable)
smtpd_tls_protocols = !SSLv2, !SSLv3
smtp_tls_protocols = !SSLv2, !SSLv3

# Enable RSA key exchange (no PFS — quantum-vulnerable)
smtpd_tls_ciphers = medium
smtpd_tls_mandatory_ciphers = medium
smtpd_tls_exclude_ciphers = aNULL, eNULL, EXPORT, DES, MD5, PSK, SRP, CAMELLIA

# STARTTLS on port 25 and 587
smtpd_tls_security_level = may
smtpd_use_tls = yes
```

**Dovecot `10-ssl.conf` for weak IMAP/POP3:**

```ini
ssl = yes
ssl_protocols = !SSLv2 !SSLv3    # allows TLSv1, TLSv1.1
ssl_cipher_list = AES128-SHA:AES256-SHA:RC4-SHA  # RSA key exchange, no PFS
```

### Alternative: Greenmail (Java)

Greenmail (`greenmail/standalone` Docker image) is a lighter-weight option:
- Supports SMTP (3025), SMTPS (3465), IMAP (3143), IMAPS (3993), POP3 (3110), POP3S (3995)
- Pure Java, no Linux mail daemon complexity
- Configurable with a PKCS12 keystore (control cert key size/expiry)
- Does NOT support configuring individual cipher suites or TLS version — you get whatever the JVM provides
- **Verdict:** Good for "has TLS with configurable cert" but NOT for "accepts weak ciphers or TLS 1.0/1.1"

**Use Greenmail when:** You need a quickly-deployable mail server where the cert itself is the finding (RSA-1024 key, expired cert) and cipher/protocol enumeration is not the goal.

### Recommended Chaos Lab Profile Design

**Profile name:** `email`

**Services:**

| Service | Container | Port (host) | Scenario | Expected Findings |
|---------|-----------|-------------|----------|------------------|
| `smtp-starttls-weak` | Custom Postfix (ubuntu) | 25587:587 | STARTTLS + TLS 1.0/1.1 + RSA key exchange | MEDIUM: legacy TLS; MEDIUM: no PFS |
| `smtps-expired` | Custom Postfix or nginx TLS termination | 20465:465 | Implicit TLS + expired self-signed cert | HIGH: expired cert |
| `imap-starttls-weak` | Custom Dovecot | 20143:143 | STARTTLS + weak ciphers | MEDIUM: weak cipher suite |
| `imaps-rsa1024` | Custom Dovecot + RSA-1024 cert | 20993:993 | Implicit TLS + RSA-1024 | HIGH: small key |
| `pop3s-modern` | Dovecot | 20995:995 | Clean TLS 1.2+ + ECDHE | SAFE: baseline for comparison |

**Port allocation:** Use 25xxx range (25587, etc.) to avoid conflicts with existing profiles. The existing chaos lab already occupies:
- Core (no profile): 443, 8000, 8443–12443
- phaseA: 13443–24443
- cloud: 24566, 21000–21002
- identity: 8080, 13890, 15449, 16443, 18082, 19000
- database: 23306, 25432
- storage-s3: 29000, 29001
- vault: 28200

Recommend port range **30xxx** for email profile to avoid all conflicts.

**Suggested ports:**
- `30025` → SMTP STARTTLS (weak TLS)
- `30465` → SMTPS (expired cert)
- `30587` → SMTP submission STARTTLS (weak ciphers)
- `30143` → IMAP STARTTLS (weak)
- `30993` → IMAPS (RSA-1024 cert)
- `30110` → POP3 STARTTLS
- `30995` → POP3S (modern/clean — control baseline)

### Dockerfile Skeleton for Weak Mail Server

```dockerfile
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y postfix dovecot-core dovecot-imapd dovecot-pop3d \
    openssl && rm -rf /var/lib/apt/lists/*

# Generate weak certs (RSA-1024 or expired) at build time
COPY certs/generate-mail-certs.sh /generate-mail-certs.sh
RUN chmod +x /generate-mail-certs.sh && /generate-mail-certs.sh

# Override Postfix and Dovecot configs
COPY postfix/main.cf /etc/postfix/main.cf
COPY postfix/master.cf /etc/postfix/master.cf
COPY dovecot/10-ssl.conf /etc/dovecot/conf.d/10-ssl.conf

EXPOSE 25 465 587 110 143 993 995

COPY entrypoint.sh /entrypoint.sh
CMD ["/entrypoint.sh"]
```

### Using nginx TLS Termination (Simpler Alternative)

The existing chaos lab uses nginx extensively for TLS scenarios. A simpler approach for the email chaos lab is to use nginx stream (TCP proxy) with TLS termination in front of a plain-text Greenmail backend, then apply the existing weak cert/cipher nginx configurations. This avoids building Postfix/Dovecot entirely.

However, sslyze STARTTLS scanning requires a real mail server that responds to EHLO/CAPABILITY/STLS — nginx stream won't speak SMTP. So the nginx approach only works for implicit TLS ports (465, 993, 995), not STARTTLS ports (25, 587, 143, 110).

**Recommendation:** Use nginx for implicit TLS ports (re-use `tls-legacy`, `tls-expired`, `tls-rsa1024` nginx configs from existing `scenarios/`), and a lightweight custom Postfix container for STARTTLS ports.

---

## 5. CBOM Classification

### How Email TLS Findings Map to CBOM Components

Email TLS findings use the same three-pass CBOM structure as existing TLS scanner output. The `ep.protocol` field distinguishes them in the CBOM.

**Pass 1 — Algorithm registration:** Cert public key algorithm + TLS cipher suite algorithms go into `_ALGORITHM_TABLE` in `classifier.py`. No new entries needed — RSA, ECDSA, and all TLS cipher suites are already present.

**Pass 2 — Certificate components:** Same as TLS scanner. Each mail server cert becomes a `CertificateProperties` component. The `service_detail` field should include the protocol label: `"SMTP-STARTTLS:587"`.

**Pass 3 — Protocol components:** Use `ProtocolPropertiesType.TLS` with the cipher suites extracted. The protocol label distinguishes SMTP-STARTTLS from HTTPS TLS endpoints.

### Protocol Label Convention

```python
# In email_scanner.py — set before calling CBOM builder
ep.protocol = "SMTP-STARTTLS"   # or "SMTPS", "IMAP-STARTTLS", "IMAPS", "POP3-STARTTLS", "POP3S"
ep.service_detail = f"{ep.protocol}:{ep.port}"
```

The existing `builder.py` uses `ep.protocol` in `ProtocolProperties` construction. No changes needed to the CBOM builder — the protocol string flows through automatically.

### Algorithm Identifiers for Email TLS

The following are the most relevant cipher suite algorithm identifiers for email protocol findings. All are already in `classifier.py`:

**Quantum-vulnerable (nist_level=0):**
- `"rsa"` — RSA key exchange (TLS_RSA_* suites, no PFS)
- `"ecdsa"` — ECDSA cert (not vulnerable for key exchange but cert itself is)
- `"3des"` — 3DES-EDE-CBC suites
- `"sha-1"` — SHA-1 in cert signature

**Quantum-vulnerable key exchange specifically:**
- `TLS_RSA_WITH_AES_128_CBC_SHA` → cipher decomposed to: RSA key exchange + AES-128-CBC + SHA-1 HMAC
- `TLS_RSA_WITH_AES_256_CBC_SHA256` → RSA key exchange + AES-256-CBC + SHA-256 HMAC
- `TLS_RSA_WITH_3DES_EDE_CBC_SHA` → RSA key exchange + 3DES + SHA-1 (double vulnerability)

**PFS-with-quantum-vulnerable-cert (MEDIUM concern):**
- `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256` → ECDHE key exchange (quantum-vulnerable) + RSA cert
- These have PFS but RSA/ECDH are broken by Grover/Shor — "harvest now, decrypt later" risk

**Quantum-safe:**
- `TLS_AES_256_GCM_SHA384` (TLS 1.3) — forward-secret, AES-256 (Grover-resistant at 256-bit)
- `TLS_AES_128_GCM_SHA256` (TLS 1.3) — marginal (AES-128 reduced to ~64-bit by Grover)

### New classifier.py entries needed

Add these TLS cipher suite name mappings for direct lookup (when scanner stores full cipher suite name rather than decomposing it):

```python
# TLS cipher suite names (full IANA names)
"tls_rsa_with_aes_128_cbc_sha":        (CryptoPrimitive.BLOCK_CIPHER, 0, 128),  # RSA key exchange
"tls_rsa_with_aes_256_cbc_sha":        (CryptoPrimitive.BLOCK_CIPHER, 0, 256),  # RSA key exchange
"tls_rsa_with_aes_128_gcm_sha256":     (CryptoPrimitive.AE, 0, 128),            # RSA key exchange
"tls_rsa_with_aes_256_gcm_sha384":     (CryptoPrimitive.AE, 0, 256),            # RSA key exchange
"tls_rsa_with_3des_ede_cbc_sha":       (CryptoPrimitive.BLOCK_CIPHER, 0, 112),  # RSA + 3DES
"tls_ecdhe_rsa_with_aes_128_gcm_sha256": (CryptoPrimitive.AE, 0, 128),         # ECDHE-RSA (PFS but QV)
"tls_ecdhe_rsa_with_aes_256_gcm_sha384": (CryptoPrimitive.AE, 0, 256),         # ECDHE-RSA (PFS but QV)
"tls_aes_128_gcm_sha256":              (CryptoPrimitive.AE, 1, 128),            # TLS 1.3 (marginal)
"tls_aes_256_gcm_sha384":              (CryptoPrimitive.AE, 1, 256),            # TLS 1.3 (safe)
"tls_chacha20_poly1305_sha256":        (CryptoPrimitive.AE, 1, 256),            # TLS 1.3 (safe)
```

Note: The existing `builder.py` primarily uses the cert public key algorithm and cipher suite name from `ep.cipher_suite` — it does not do full cipher decomposition for TLS endpoints. The approach of adding full cipher suite names to `classifier.py` is optional but improves CBOM algorithm component accuracy.

---

## 6. Quantum Risk Classification for Email Protocols

### Why Email is High-Risk for "Harvest Now, Decrypt Later"

Email is particularly exposed to quantum adversaries because:
1. Email content persists for years (archived conversations)
2. Many email servers still accept TLS 1.0/1.1 with RSA key exchange
3. STARTTLS is opportunistic — can silently downgrade to plaintext if not enforced
4. Organizational email servers are rarely patched as aggressively as public-facing HTTPS

### Cipher Suite Quantum Risk Tiers

**CRITICAL — must flag immediately:**
- SSLv2, SSLv3 — broken classically AND quantumly
- NULL cipher suites — no encryption
- EXPORT-grade — 40/56-bit keys
- RC4 suites — broken stream cipher

**HIGH — quantum key exchange vulnerability:**
- `TLS_RSA_*` suites — RSA key exchange is broken by Shor's algorithm. "Harvest now, decrypt later" is active threat. No PFS means all past traffic decryptable.
- Severity: HIGH (matches existing `tls_weak_ciphers_present=True` findings)

**MEDIUM — quantum-vulnerable with PFS:**
- `TLS_ECDHE_RSA_*` and `TLS_ECDHE_ECDSA_*` suites — ECDH key exchange is quantum-vulnerable (Shor's on elliptic curve DLP), but PFS means only current session keys are at risk
- Legacy TLS 1.0/1.1 support — not quantum-specific but indicates poor hygiene
- Self-signed or expired certs on mail servers

**LOW — monitoring only:**
- TLS 1.2 with ECDHE + AES-256 but no TLS 1.3 support
- Missing HSTS on webmail endpoints (out of scope for this scanner)

**SAFE — no finding:**
- TLS 1.3 with `TLS_AES_256_GCM_SHA384` or `TLS_CHACHA20_POLY1305_SHA256`
- Certificate with RSA-4096 or ECDSA P-384 (not quantum-safe but classically strong)

### STARTTLS-Specific Risk: Protocol Downgrade

STARTTLS has an additional risk class not present in implicit TLS: a network adversary can strip the STARTTLS advertisement, causing the client to send mail in plaintext. This is distinct from weak cipher negotiation and is not detectable by sslyze (requires MITM position).

**Scanner approach:** The scanner cannot detect STARTTLS stripping (agentless constraint). Instead, flag `smtpd_tls_security_level=may` vs `enforce` as a finding type. This requires reading server-advertised EHLO capabilities, which sslyze does not expose in scan results. The finding "STARTTLS available but not enforced" should be a LOW finding noted from the protocol label — port 25 with STARTTLS is always treated as MEDIUM risk due to this inherent downgrade vulnerability regardless of cipher strength.

**Severity mapping for email endpoints:**

```python
EMAIL_SEVERITY_RULES = [
    # (condition, severity, finding_id, description)
    ("ssl_version_supported",  "CRITICAL", "EMAIL-01", "SSLv2/SSLv3 supported on email server"),
    ("rsa_key_exchange",       "HIGH",     "EMAIL-02", "RSA key exchange (no PFS) — harvest-now-decrypt-later risk"),
    ("cert_expired",           "HIGH",     "EMAIL-03", "Certificate expired on mail server"),
    ("cert_pubkey_size_small", "HIGH",     "EMAIL-04", "Certificate RSA key < 2048 bits"),
    ("legacy_tls_10_11",       "MEDIUM",   "EMAIL-05", "TLS 1.0/1.1 supported on mail server"),
    ("no_pfs",                 "MEDIUM",   "EMAIL-06", "No forward-secret cipher suites"),
    ("weak_cipher_3des",       "HIGH",     "EMAIL-07", "3DES cipher suite accepted"),
    ("starttls_port_25",       "MEDIUM",   "EMAIL-08", "STARTTLS on port 25 — downgrade attack possible"),
    ("self_signed_cert",       "MEDIUM",   "EMAIL-09", "Self-signed certificate on mail server"),
    ("tls_12_only",            "LOW",      "EMAIL-10", "No TLS 1.3 support (TLS 1.2 only)"),
    ("tls_13_ecdhe_256",       "SAFE",     None,       "TLS 1.3 with strong cipher suite"),
]
```

### Quantum Risk vs. Classical Risk for Email

| Algorithm | Classical Risk | Quantum Risk | Timeline |
|-----------|----------------|--------------|----------|
| RSA-2048 key exchange | Classically secure | Broken by Shor (CRQC) | NIST: deprecate by 2030 |
| ECDH P-256 key exchange | Classically secure | Broken by Shor variant | NIST: deprecate by 2030 |
| AES-128-GCM (symmetric) | Secure | Grover reduces to ~64-bit effective | Monitor |
| AES-256-GCM (symmetric) | Secure | Grover reduces to ~128-bit effective | Quantum-safe |
| 3DES | Classically weak (Sweet32 attack) | Also quantum-vulnerable | Immediate CRITICAL |
| RC4 | Classically broken | Also quantum-vulnerable | Immediate CRITICAL |
| TLS 1.3 cipher suites | Secure | Best currently available | Safe |

Source: NIST SP 800-131A Rev. 2, NIST PQC Migration FAQ (https://www.nist.gov/pqc), draft-ietf-uta-pqc-app (IETF datatracker)

---

## Implementation Notes for `email_scanner.py`

### Recommended File Structure

```
quirk/scanner/email_scanner.py    # New file — follows pattern of kerberos_scanner.py
```

### Entry Point Signature

```python
def scan_email_targets(
    cfg,
    targets: list[str],           # hostnames only — scanner expands to all ports
    session_start: datetime,
    logger=None,
) -> list[CryptoEndpoint]:
    """Scan email protocol TLS for a list of mail server hostnames.

    For each hostname, probes all 7 default ports (25, 465, 587, 143, 993, 110, 995).
    Uses sslyze with tls_opportunistic_encryption for STARTTLS ports.
    Falls back to smtplib/imaplib/poplib if sslyze fails.
    """
```

### Integration with Existing `run_scan.py`

The new scanner should follow the `session_start` sharing pattern established in Phase 24 (ISSUE-3 fix). All `ep.scanned_at` values should use the shared `session_start` timestamp.

### Evidence Counters (for scoring)

Add to `evidence.py`:
```python
motion_email_weak_count: int = 0    # RSA key exchange, legacy TLS, 3DES on email
motion_email_no_tls_count: int = 0  # Plaintext or scan error on mail ports
motion_email_critical_count: int = 0  # SSLv2/SSLv3, expired certs
```

Prefix: `motion_` (consistent with v4.4 milestone Data in Motion subscore).

### SQLite Column

Following the v4.x pattern, add a new column to `CryptoEndpoint`:

```python
email_scan_json = Column(Text, nullable=True)  # Email protocol scan metadata JSON
```

This stores STARTTLS protocol type, negotiated version, and raw sslyze output for the CBOM builder.

---

## Sources

- sslyze STARTTLS docs: Context7 `/nabla-c0d3/sslyze` + https://blog.adqt.fr/sslyze/documentation/running-a-scan-in-python.html
- sslyze GitHub: https://github.com/nabla-c0d3/sslyze
- Postfix TLS configuration: https://www.postfix.org/TLS_README.html
- docker-mailserver TLS: https://docker-mailserver.github.io/docker-mailserver/latest/config/security/ssl/
- Greenmail Docker: https://hub.docker.com/r/greenmail/standalone/ + https://greenmail-mail-test.github.io/greenmail/
- SSL mail protocol Python testing: https://github.com/ahaw021/SSL-MAIL-PROTOCOLS-TESTING/blob/master/connections.py
- NIST PQC: https://www.nist.gov/pqc
- IETF PQC for TLS applications: https://datatracker.ietf.org/doc/draft-ietf-uta-pqc-app/
- CycloneDX CBOM: https://cyclonedx.org/capabilities/cbom/
- Port conventions: RFC 8314 (IMAP/POP3 implicit TLS), RFC 6409 (SMTP submission port 587)
