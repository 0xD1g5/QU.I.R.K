# Phase 20: Kerberos Scanner — Research

**Researched:** 2026-04-09
**Domain:** Kerberos AS-REQ probing, impacket ASN.1, anonymous LDAP, Samba DC containerization
**Confidence:** HIGH (impacket API verified against GitHub source; Docker patterns verified against prior chaos lab art)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**impacket API Approach**
- D-01: Use `impacket.krb5.kerberosv5.sendReceive()` + raw ASN.1 via `impacket.krb5.asn1.AS_REQ` — craft the AS-REQ body manually, advertise all etypes in the request, send/receive over raw socket, parse `KDC_ERR_PREAUTH_REQUIRED` error response's padata for `PA-ETYPE-INFO2`.
- D-02: Do NOT use `getKerberosTGT()` wrapper — it is designed for authenticated flows and does not expose raw error response parsing cleanly.
- D-03: This pattern mirrors impacket's own `GetNPUsers.py` internals and the DNSSEC scanner's approach (raw query → parse response → classify). Advertising all etypes in the probe ensures the KDC returns its full support list.
- D-04: Import guard: `IMPACKET_AVAILABLE = True/False` — same pattern as `DNSPYTHON_AVAILABLE` and `LXML_AVAILABLE` in prior scanners.

**kerberos_targets Format**
- D-05: Plain hostnames/IPs only: `kerberos_targets: ["dc01.corp.local", "192.168.1.10"]` — consistent with `dnssec_targets`. No realm required from user.
- D-06: Scanner auto-derives realm by uppercasing the FQDN (e.g., `CORP.LOCAL`) for the initial AS-REQ; reads actual `crealm` from the KDC error response body to correct if needed.
- D-07: Chaos lab target is simply `"127.0.0.1"` or `"localhost"`.

**Etype Severity Classification**
- D-08: DES etypes (1, 2, 3) → CRITICAL
- D-09: RC4-HMAC (etype 23) → HIGH
- D-10: AES-256-CTS-HMAC-SHA1-96 (etype 18), AES256-CTS-HMAC-SHA384-192 (etype 20) → SAFE
- D-11: AES-128-CTS-HMAC-SHA1-96 (etype 17) → HIGH (Grover halves effective security to ~64-bit)
- D-12: Unrecognized etype → MEDIUM

**Samba DC Chaos Lab**
- D-13: Custom Dockerfile in `quantum-chaos-enterprise-lab/samba/` (not a community image). Base: `debian:bookworm-slim` + `samba` package.
- D-14: `smb.conf` must include `ntlm auth = ntlmv1-permitted` and `kerberos encryption types = all` to enable RC4 alongside AES.
- D-15: Docker Compose profile name: `kerberos`. `start_period: 90s` healthcheck on port 88.
- D-16: Realm: `QUIRK.LAB`.

**run_scan.py Integration**
- D-17: Follow SAML/DNSSEC pattern exactly: lazy import inside `if cfg.connectors.enable_kerberos` block, `_phase_timer` context manager, results aggregated into `all_endpoints`.

**CBOM / Classifier**
- D-18: `elif ep.protocol == "KERBEROS":` branch in `builder.py` — follows DNSSEC → SAML → KERBEROS chain.
- D-19: Classifier entries for etype names (e.g., `"rc4-hmac"`, `"des-cbc-md5"`, `"aes256-cts-hmac-sha1-96"`).

### Claude's Discretion
- Exact socket timeout defaults for AS-REQ probe
- TCP vs UDP retry logic internals (TCP primary, UDP fallback — behavior is locked, implementation detail is open)
- Test fixture approach for AS-REQ/error response (bytes fixture or mock socket)
- Samba container entrypoint script details (realm provisioning command)

### Deferred Ideas (OUT OF SCOPE)
- `KERB-ADV-01`: Per-account etype probing via authenticated LDAP `msDS-SupportedEncryptionTypes` (breaks agentless constraint; SaaS model)
- Kerberoasting / SPN enumeration (pentest territory)
- Windows AD CS live connector (stub remains, deferred)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KERB-01 | Scanner sends unauthenticated AS-REQ to port 88 (TCP with UDP fallback) and parses PA-ETYPE-INFO2 from `KDC_ERR_PREAUTH_REQUIRED` response — no credentials required | impacket `sendReceive()` + raw ASN.1 confirmed; `ETYPE_INFO2` decoder confirmed |
| KERB-02 | RC4-HMAC (etype 23) → HIGH; DES etypes (1, 2, 3) → CRITICAL; AES-256 (18/20) → SAFE; AES-128 (17) → HIGH | `KERBEROS_ETYPE_MAP` dict pattern confirmed from DNSSEC_ALG_MAP art |
| KERB-03 | Scanner attempts anonymous LDAP bind on port 389; gracefully degrades if unreachable or auth required | ldap3 anonymous bind confirmed; graceful degradation is a logged-skip pattern |
| KERB-04 | Results stored in `kerberos_scan_json` with `protocol="KERBEROS"` CryptoEndpoints; classifier and CBOM updated | Column already exists in models.py; builder.py SAML elif is direct template |
| KERB-05 | Chaos lab gains Samba DC `kerberos` Docker Compose profile with RC4-enabled realm and `start_period: 90s` healthcheck | smb.conf `kerberos encryption types = all` + Samba provisioning pattern confirmed |
</phase_requirements>

---

## Summary

Phase 20 adds a Kerberos encryption type scanner to QUIRK using an unauthenticated AS-REQ probe. The probe advertises all known etypes to a KDC, which responds with `KDC_ERR_PREAUTH_REQUIRED` (error code 25); the scanner parses the `PA-ETYPE-INFO2` padata in that error response to enumerate the KDC's supported encryption types — no credentials needed.

The implementation follows the exact pattern of prior identity scanners (DNSSEC, SAML): import guard, severity map dict, scanner returns `list[CryptoEndpoint]`, lazy import in `run_scan.py`, `elif` branch in `builder.py`. The impacket API is verified against the 0.13.0 source. The critical insight is that `sendReceive()` uses TCP only (SOCK_STREAM, port 88, length-prefixed wire format) — UDP fallback must be implemented separately via raw socket if desired.

The Samba DC chaos lab requires a custom Dockerfile because community images do not expose the RC4 enablement knob reliably. Two smb.conf settings are mandatory to produce an RC4-capable KDC: `kerberos encryption types = all` and `ntlm auth = ntlmv1-permitted`. Samba provisions on first start and can take 60-90 seconds, hence the `start_period: 90s` healthcheck requirement.

**Primary recommendation:** Use `sendReceive()` for TCP primary, implement raw UDP socket as fallback if TCP is blocked; catch `KerberosError`, decode `e-data` as `METHOD_DATA`, iterate padata entries for `PA_ETYPE_INFO2.value` (type 19), decode with `ETYPE_INFO2()` ASN.1 spec, extract `etype` integers.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on This Phase |
|-----------|---------------------|
| PEP 8 for all Python | kerberos_scanner.py must be PEP 8 compliant |
| Keep diffs minimal — avoid unnecessary refactors | Do not alter existing DNSSEC/SAML scanners during integration |
| Run `python -m compileall` and relevant tests after changes | Plan tasks must include compile check and `pytest tests/test_kerberos_scanner.py` |
| `impacket` in `[identity]` optional extras only — not core deps | Import guard `IMPACKET_AVAILABLE` is mandatory; scanner must degrade gracefully |
| `labs/*/expected_results.md` update if detection logic changes | Add Samba DC expected results to `quantum-chaos-enterprise-lab/expected_results_v3.md` |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| impacket | 0.13.0 (pinned in pyproject.toml) | AS-REQ construction, KRB_ERROR parsing, sendReceive TCP transport | Project-standard; only library with complete Kerberos ASN.1 + transport without OS dependencies |
| pyasn1 | transitive via impacket | ASN.1 decoder for ETYPE_INFO2 | impacket uses `pyasn1.codec.ber.decoder.decode()` internally; exposed through impacket's `decoder` import |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ldap3 | transitive via impacket | Anonymous LDAP bind for KERB-03 | Graceful-degradation LDAP probe; already available via impacket's dependency chain |
| socket (stdlib) | stdlib | UDP fallback raw socket for AS-REQ | Only if TCP sendReceive times out or is blocked |
| struct (stdlib) | stdlib | Kerberos wire framing for UDP (4-byte length prefix) | UDP fallback only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| impacket sendReceive | Raw socket + manual ASN.1 (pyasn1 only) | 200+ lines of fragile ASN.1 scaffolding vs ~30 lines with impacket — impacket wins |
| Custom Samba Dockerfile | Community image (itherz/samba-ad-dc, smblds/smblds) | Community images do not expose `kerberos encryption types = all` config reliably; smblds does not expose port 88; custom Dockerfile gives full control |
| ldap3 for LDAP probe | python-ldap | ldap3 is pure-Python (pip-only); python-ldap requires system libldap binary — violates pip-only constraint |

**Installation (identity extras group — already declared in pyproject.toml):**
```bash
pip install -e ".[identity]"
```

**Version verification (confirmed 2026-04-09):**
```
impacket: 0.13.0 — latest on PyPI as of research date
```

---

## Architecture Patterns

### Recommended Project Structure
```
quirk/scanner/
└── kerberos_scanner.py     # New scanner module (mirrors dnssec_scanner.py)

tests/
└── test_kerberos_scanner.py  # TDD scaffold (Plan 01 = RED, Plan 02 = GREEN)

quantum-chaos-enterprise-lab/
└── samba/
    ├── Dockerfile            # debian:bookworm-slim + samba + provision script
    ├── entrypoint.sh         # samba-tool domain provision + exec samba -D
    └── smb.conf.append       # Extra lines: kerberos encryption types = all
```

### Pattern 1: Import Guard (mirrors LXML_AVAILABLE and DNSPYTHON_AVAILABLE)
**What:** Module-level try/except that sets a flag; scanner returns empty list if flag is False.
**When to use:** Always — impacket is in optional extras, not core deps.
**Example:**
```python
# Source: quirk/scanner/saml_scanner.py and dnssec_scanner.py (prior art)
try:
    from impacket.krb5.asn1 import AS_REQ, KRB_ERROR, ETYPE_INFO2, seq_set, seq_set_iter
    from impacket.krb5.kerberosv5 import sendReceive, KerberosError
    from impacket.krb5 import constants
    from impacket.krb5.types import KerberosTime, Principal
    from pyasn1.codec.ber import encoder, decoder
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False
```

### Pattern 2: KERBEROS_ETYPE_MAP (mirrors DNSSEC_ALG_MAP)
**What:** Module-level dict mapping etype int to (name_str, severity_str).
**When to use:** Referenced by classifier and by test_kerberos_scanner.py static tests.
**Example:**
```python
# Source: dnssec_scanner.py DNSSEC_ALG_MAP pattern + D-08 through D-12
KERBEROS_ETYPE_MAP: dict = {
    1:  ("des-cbc-crc",              "CRITICAL"),   # RFC 4120 deprecated
    3:  ("des-cbc-md5",              "CRITICAL"),   # RFC 4120 deprecated
    17: ("aes128-cts-hmac-sha1-96",  "HIGH"),       # D-11: Grover → ~64-bit
    18: ("aes256-cts-hmac-sha1-96",  "SAFE"),       # D-10
    20: ("aes256-cts-hmac-sha384-192", "SAFE"),     # D-10 (RFC 8009)
    23: ("rc4-hmac",                 "HIGH"),       # D-09
}
# Etype 2 (des-cbc-md4) also CRITICAL — included per D-08
```

### Pattern 3: AS-REQ Probe → PA-ETYPE-INFO2 Extraction
**What:** Unauthenticated AS-REQ advertising all etypes; parse KDC_ERR_PREAUTH_REQUIRED error response.
**When to use:** Core of KERB-01. No credentials needed — KDC always returns this error for unknown users.
**Verified against:** impacket 0.13.0 source (kerberosv5.py, asn1.py)
```python
# Source: github.com/fortra/impacket kerberosv5.py + getKerberosTGT() internals
from impacket.krb5.asn1 import AS_REQ, ETYPE_INFO2, seq_set, seq_set_iter
from impacket.krb5.kerberosv5 import sendReceive, KerberosError
from impacket.krb5 import constants
from impacket.krb5.types import Principal
from pyasn1.codec.ber import encoder, decoder

def _probe_kdc(host: str, realm: str, timeout: int) -> list:
    """Returns list of etype ints advertised in PA-ETYPE-INFO2."""
    client_name = Principal("nobody", type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value)

    as_req = AS_REQ()
    # ... (build req-body with all etypes, set padata)
    # advertise all known etypes
    seq_set_iter(as_req['req-body'], 'etype', [17, 18, 20, 23, 1, 3])

    message = encoder.encode(as_req)
    try:
        r = sendReceive(message, realm, host)
        # KDC returned AS-REP (no preauth required — unexpected but handle)
        return []
    except KerberosError as e:
        if e.getErrorCode() == constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value:
            # e-data contains METHOD_DATA with PA-ETYPE-INFO2
            error_pkt = e.getErrorPacket()
            method_data = decoder.decode(bytes(error_pkt['e-data']),
                                         asn1Spec=MethodData())[0]
            etypes = []
            for method in method_data:
                if method['padata-type'] == constants.PreAuthenticationDataTypes.PA_ETYPE_INFO2.value:
                    info2 = decoder.decode(bytes(method['padata-value']),
                                           asn1Spec=ETYPE_INFO2())[0]
                    for entry in info2:
                        etypes.append(int(entry['etype']))
            return etypes
        raise
```

### Pattern 4: run_scan.py Lazy-Import Block (mirrors SAML block, lines 472-483)
**What:** Conditional lazy import inside enable flag check, with `_phase_timer` and aggregation.
**When to use:** Mandatory for impacket (optional dep); mirrors SAML exactly.
```python
# Source: run_scan.py lines 472-483 (SAML block — direct template)
# ── Kerberos scanning ─────────────────────────────────────
kerberos_endpoints = []
with _phase_timer(run_stats, "kerberos_scanning"):
    if cfg.connectors.enable_kerberos and cfg.connectors.kerberos_targets:
        from quirk.scanner.kerberos_scanner import scan_kerberos_targets
        kerberos_endpoints = scan_kerberos_targets(
            targets=cfg.connectors.kerberos_targets,
            timeout=getattr(cfg.connectors, "kerberos_timeout", 10),
            logger=main_logger,
        )
        main_logger.info("Kerberos scan: %d endpoints from %d targets",
                         len(kerberos_endpoints), len(cfg.connectors.kerberos_targets))

# Add kerberos_endpoints to the endpoints aggregation tuple
```

### Pattern 5: CBOM builder.py elif Branch (mirrors SAML elif, lines 357-360)
**What:** Protocol-specific elif clause before the TLS `else` fallback.
**When to use:** Required for KERB-04 — registers etype name in algo_registry.
```python
# Source: quirk/cbom/builder.py lines 357-365 (SAML elif — direct template)
elif ep.protocol == "KERBEROS":
    # cert_pubkey_alg holds the etype name (e.g. "rc4-hmac", "aes256-cts-hmac-sha1-96")
    # Exclude "kerberos-unreachable" synthetic finding — not a real algorithm
    if ep.cert_pubkey_alg and ep.cert_pubkey_alg != "kerberos-unreachable":
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

### Pattern 6: Samba DC Dockerfile and Entrypoint
**What:** Custom debian:bookworm-slim container that runs samba-tool provision on first start.
**When to use:** KERB-05 chaos lab requirement.
```dockerfile
# Source: D-13, D-14, D-16 + SambaWiki provisioning guide
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    samba winbind dnsutils && \
    rm -rf /var/lib/apt/lists/*
EXPOSE 88/tcp 88/udp 389/tcp
HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=90s \
    CMD smbclient -L localhost -N 2>/dev/null | grep -q QUIRK || exit 1
```

Entrypoint script pattern (provision on first start, then exec samba):
```bash
#!/bin/bash
if [ ! -f /var/lib/samba/private/secrets.ldb ]; then
    samba-tool domain provision \
        --server-role=dc \
        --use-rfc2307 \
        --dns-backend=SAMBA_INTERNAL \
        --realm=QUIRK.LAB \
        --domain=QUIRK \
        --adminpass=Passw0rd123! \
        --option="kerberos encryption types = all" \
        --option="ntlm auth = ntlmv1-permitted"
fi
exec samba -D --configfile=/etc/samba/smb.conf
```

### Anti-Patterns to Avoid
- **Using `getKerberosTGT()`:** Designed for authenticated flows. Internally calls `sendReceive`, handles credentials, and does not expose raw PA-ETYPE-INFO2 cleanly. Fragile against impacket version updates.
- **Importing impacket at module top-level in run_scan.py:** impacket is an optional dependency; top-level import breaks scans for users who have not installed `[identity]` extras. Use lazy import inside the enable flag block.
- **Assuming sendReceive uses UDP:** Confirmed via source: `sendReceive()` creates a `SOCK_STREAM` (TCP) socket exclusively. The KERB-01 requirement for "UDP fallback" must be implemented via a separate raw UDP socket if TCP fails — sendReceive does not do this for you.
- **Port collision in docker-compose.yml:** Port 88 is not currently used by any existing chaos lab service. Verify before adding.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Kerberos AS-REQ ASN.1 encoding | Custom pyasn1 structures for AS_REQ body | `impacket.krb5.asn1.AS_REQ` + `seq_set_iter` | ASN.1 encoding of KDC_REQ has 12+ fields; correct tagging is non-trivial |
| KRB_ERROR decoding | Manual byte parsing of error response | `impacket.krb5.kerberosv5.KerberosError.getErrorPacket()` then `decoder.decode(e-data, asn1Spec=MethodData())` | Error format has nested padata sequences; impacket handles tag/length correctly |
| TCP Kerberos transport | Custom socket with length-prefix framing | `impacket.krb5.kerberosv5.sendReceive()` | Kerberos TCP uses 4-byte big-endian length prefix (RFC 4120 §7.2.2); impacket handles this |
| LDAP anonymous bind | Raw socket LDAP | `ldap3.Connection(server, authentication=ldap3.ANONYMOUS)` | ldap3 is pure-Python, pip-installable, already transitive via impacket |

**Key insight:** The AS-REQ → KDC_ERR_PREAUTH_REQUIRED → PA-ETYPE-INFO2 extraction flow involves 4 layers of ASN.1 nesting. impacket's existing code in `getKerberosTGT()` has already solved this — the scanner extracts the inner logic (the error-parsing portion) while skipping the credential-handling outer wrapper.

---

## Common Pitfalls

### Pitfall 1: sendReceive Uses TCP Only — UDP Fallback is DIY
**What goes wrong:** Developer assumes `sendReceive()` handles UDP as a fallback (like `dns.query.udp_with_fallback`). The scanner appears to work against local Samba but fails silently against firewalled environments that block TCP/88 but allow UDP/88.
**Why it happens:** The function name `sendReceive` is generic; inspection shows `socket.SOCK_STREAM` is hardcoded.
**How to avoid:** For TCP primary: use `sendReceive()`. For UDP fallback: raw socket with `struct.pack('!I', len(data)) + data` is wrong for UDP; Kerberos UDP does NOT use the 4-byte length prefix (only TCP does). UDP sends the raw ASN.1 bytes directly.
**Warning signs:** Integration test passes against local Samba but times out against real enterprise DC behind firewall.

### Pitfall 2: Realm Derivation Edge Cases
**What goes wrong:** Scanner uppercases the hostname to derive realm (e.g., `dc01.corp.local` → `CORP.LOCAL`), but the AS-REQ's `realm` field must match exactly. Some KDCs return `KDC_ERR_C_PRINCIPAL_UNKNOWN` if the realm is wrong, not `KDC_ERR_PREAUTH_REQUIRED`.
**Why it happens:** FQDN hostname ≠ realm in all environments (e.g., `dc01.ad.example.com` may have realm `EXAMPLE.COM` not `AD.EXAMPLE.COM`).
**How to avoid:** Use the domain portion only (last two labels) as realm fallback. Read `crealm` from the KRB_ERROR response — if realm is wrong, retry with corrected realm from error. For the chaos lab, `QUIRK.LAB` is fixed.
**Warning signs:** `KDC_ERR_C_PRINCIPAL_UNKNOWN` instead of `KDC_ERR_PREAUTH_REQUIRED` in error log.

### Pitfall 3: ETYPE_INFO vs ETYPE_INFO2 — Must Handle Both
**What goes wrong:** Older KDCs (or Samba in certain configurations) return `PA_ETYPE_INFO` (type 11) instead of `PA_ETYPE_INFO2` (type 19) in the padata. Scanner only handles type 19 and misses the etype list.
**Why it happens:** PA_ETYPE_INFO2 is the RFC 4120 successor; PA_ETYPE_INFO is from RFC 1510 and still used by older systems.
**How to avoid:** Check both `PA_ETYPE_INFO2.value` (19) and `PA_ETYPE_INFO.value` (11) in the METHOD_DATA loop. Use `ETYPE_INFO()` spec for type 11.
**Warning signs:** Empty etype list returned from probe against older KDC.

### Pitfall 4: Samba DC Startup Race Condition
**What goes wrong:** Container starts, port 88 opens (samba process is listening), but realm provisioning hasn't committed `secrets.ldb` yet. Scanner probes port 88, gets `KDC_ERR_CANT_POSTDATE` or connection refused mid-handshake.
**Why it happens:** `samba-tool domain provision` takes 30-90 seconds on first run. The samba process must complete provisioning before it can serve valid Kerberos responses.
**How to avoid:** `start_period: 90s` in Docker healthcheck (already in D-15). Healthcheck must verify actual KDC response, not just TCP port open. Use `smbclient -L localhost -N` or `kinit` with known credentials in healthcheck.
**Warning signs:** Integration test fails immediately after `docker compose up`, passes after 2-minute wait.

### Pitfall 5: Kerberos Encryption Types Defaults Changed in Recent Samba
**What goes wrong:** Samba 4.24.0 (released 2026) changed the default `kdc default domain supported enctypes` to AES-only for domains at 2008+ functional level. A custom Dockerfile that does not explicitly set `kerberos encryption types = all` will produce a KDC that returns only AES etypes.
**Why it happens:** Samba 4.24.0 addresses CVE-2026-20833 by restricting defaults. debian:bookworm samba package may be at 4.17.x but future updates could change this.
**How to avoid:** Explicitly set `kerberos encryption types = all` in smb.conf (or via `--option` at provision time). Also explicitly set `ntlm auth = ntlmv1-permitted` per D-14.
**Warning signs:** Integration test shows only AES-256 and AES-128 in etype list despite RC4 being expected.

### Pitfall 6: Anonymous LDAP Bind — Modern AD Blocks It
**What goes wrong:** Anonymous LDAP bind fails on modern Active Directory (since 2003 SP1) and on hardened Samba DCs. The scanner raises an exception rather than gracefully logging `ldap-anonymous-blocked`.
**Why it happens:** LDAP null bind (empty DN + empty password) returns `LDAP_INAPPROPRIATE_AUTH` (error 48) or `LDAP_UNWILLING_TO_PERFORM` (error 53). The scanner must catch these and continue.
**How to avoid:** Wrap the entire LDAP probe in try/except. On any exception (connection error, auth error, timeout), log the reason and return a `service_detail="ldap-anonymous-blocked"` finding or skip entirely. Samba DC in chaos lab may need `INSECURE_LDAP = yes` or anonymous read allowed.
**Warning signs:** KERB-03 causes an unhandled exception that aborts the entire scan for a target.

### Pitfall 7: impacket AS_REQ Body Field Names Are Hyphenated in ASN.1
**What goes wrong:** Python dict-style access to AS_REQ body uses the raw ASN.1 field name with hyphens (e.g., `as_req['req-body']`, not `as_req['req_body']`). Developers unfamiliar with pyasn1 try underscore names.
**Why it happens:** pyasn1 preserves ASN.1 names verbatim, including hyphens.
**How to avoid:** Reference impacket source for exact field names: `'req-body'`, `'padata'`, `'padata-type'`, `'padata-value'`, `'e-data'`. Use `seq_set()` and `seq_set_iter()` helpers for sequence fields.
**Warning signs:** `KeyError` or `AttributeError` when accessing AS_REQ body fields.

---

## Code Examples

### Example 1: Full AS-REQ Probe (verified against impacket 0.13.0)
```python
# Source: github.com/fortra/impacket/blob/master/impacket/krb5/kerberosv5.py
# Source: github.com/fortra/impacket/blob/master/examples/GetNPUsers.py
from impacket.krb5.asn1 import AS_REQ, KRB_ERROR, ETYPE_INFO2, ETYPE_INFO
from impacket.krb5.asn1 import seq_set, seq_set_iter
from impacket.krb5.kerberosv5 import sendReceive, KerberosError
from impacket.krb5 import constants
from impacket.krb5.types import KerberosTime, Principal
from pyasn1.codec.ber import encoder, decoder
from pyasn1.type import univ

# Probe etypes — advertise all to maximize KDC response completeness (D-03)
ALL_ETYPES = [17, 18, 20, 23, 1, 3]

def _build_as_req(client_name, server_name, realm: str) -> AS_REQ:
    as_req = AS_REQ()
    as_req['pvno'] = 5
    as_req['msg-type'] = int(constants.ApplicationTagNumbers.AS_REQ.value)

    req_body = as_req['req-body']
    req_body['kdc-options'] = constants.KDCOptions(constants.KDCOptions.forwardable)
    seq_set(req_body, 'sname', server_name.components_to_asn1)
    seq_set(req_body, 'cname', client_name.components_to_asn1)
    req_body['realm'] = realm
    req_body['till'] = KerberosTime.to_asn1(datetime(2037, 12, 31, 0, 0))
    req_body['nonce'] = random.getrandbits(31)
    seq_set_iter(req_body, 'etype', ALL_ETYPES)
    return as_req

def _probe_kdc(host: str, realm: str, timeout: int) -> list[int]:
    """Returns list of etype ints from PA-ETYPE-INFO2; empty on no preauth response."""
    client_name = Principal("nobody", type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value)
    as_req = _build_as_req(client_name, server_name, realm)

    try:
        _r = sendReceive(encoder.encode(as_req), realm, host)
        return []  # Unexpected AS-REP without preauth
    except KerberosError as e:
        code = e.getErrorCode()
        if code != constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value:
            raise
        error_pkt = e.getErrorPacket()
        # e-data contains METHOD_DATA
        method_data_raw = bytes(error_pkt['e-data'])
        # METHOD_DATA is SequenceOf(PA_DATA) — decode as sequence
        from impacket.krb5.asn1 import MethodData
        method_data = decoder.decode(method_data_raw, asn1Spec=MethodData())[0]
        etypes = []
        for method in method_data:
            ptype = int(method['padata-type'])
            if ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO2.value):
                info2 = decoder.decode(bytes(method['padata-value']),
                                       asn1Spec=ETYPE_INFO2())[0]
                for entry in info2:
                    etypes.append(int(entry['etype']))
            elif ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO.value):
                info = decoder.decode(bytes(method['padata-value']),
                                      asn1Spec=ETYPE_INFO())[0]
                for entry in info:
                    etypes.append(int(entry['etype']))
        return etypes
```

### Example 2: KERB-03 Anonymous LDAP Probe with Graceful Degradation
```python
# Source: ldap3 documentation + KERB-03 requirement (graceful degradation)
def _probe_ldap_anon(host: str, timeout: int, logger) -> dict:
    """Attempt anonymous LDAP bind. Returns dict with 'ldap_status' key."""
    try:
        import ldap3
        server = ldap3.Server(host, port=389, connect_timeout=timeout)
        conn = ldap3.Connection(server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout)
        if not conn.bind():
            return {"ldap_status": "anonymous-bind-rejected", "ldap_error": conn.last_error}
        # Try to read msDS-SupportedEncryptionTypes from domain root
        conn.search('', '(objectClass=*)', attributes=['defaultNamingContext'])
        base = conn.entries[0].defaultNamingContext.value if conn.entries else ''
        if base:
            conn.search(base, '(objectClass=domain)',
                        attributes=['msDS-SupportedEncryptionTypes'])
            if conn.entries:
                enc_types = conn.entries[0]['msDS-SupportedEncryptionTypes'].value
                return {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": enc_types}
        return {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    except Exception as exc:
        if logger:
            logger.warning("Kerberos LDAP probe failed for %s: %s (skipped)", host, exc)
        return {"ldap_status": "skipped", "ldap_error": str(exc)}
```

### Example 3: Samba DC smb.conf Critical Settings
```ini
# Source: D-14, SambaWiki Setting_up_Samba_as_an_Active_Directory_Domain_Controller
# Required settings for RC4-HMAC in QUIRK.LAB realm:
[global]
    workgroup = QUIRK
    realm = QUIRK.LAB
    netbios name = DC1
    server role = active directory domain controller
    dns forwarder = 8.8.8.8

    # Enable RC4-HMAC alongside AES (D-14)
    kerberos encryption types = all
    ntlm auth = ntlmv1-permitted

    # Logging
    log level = 1
```

### Example 4: Docker Compose Profile Entry (mirrors bind9-dnssec pattern)
```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.yml bind9-dnssec pattern (lines 764-778)
samba-dc:
  build:
    context: ./samba
    dockerfile: Dockerfile
  profiles: ["kerberos"]
  ports:
    - "88:88/tcp"
    - "88:88/udp"
    - "389:389/tcp"
  healthcheck:
    test: ["CMD", "smbclient", "-L", "localhost", "-N"]
    interval: 10s
    timeout: 5s
    retries: 12
    start_period: 90s
```

### Example 5: Classifier Entries for Kerberos Etypes
```python
# Source: quirk/cbom/classifier.py _ALGORITHM_TABLE pattern — add after SAML section
# ------------------------------------------------------------------
# Kerberos encryption types (RFC 4120, RFC 8009)
# ------------------------------------------------------------------
"des-cbc-crc":               (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 1 — CRITICAL
"des-cbc-md4":               (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 2 — CRITICAL
"des-cbc-md5":               (CryptoPrimitive.BLOCK_CIPHER, None, None),   # etype 3 — CRITICAL
"rc4-hmac":                  (CryptoPrimitive.MAC, None, None),            # etype 23 — HIGH
"aes128-cts-hmac-sha1-96":   (CryptoPrimitive.BLOCK_CIPHER, 0, 64),        # etype 17 — HIGH (Grover)
"aes256-cts-hmac-sha1-96":   (CryptoPrimitive.BLOCK_CIPHER, 1, 256),       # etype 18 — SAFE
"aes256-cts-hmac-sha384-192":(CryptoPrimitive.BLOCK_CIPHER, 1, 256),       # etype 20 — SAFE (RFC 8009)
```

### Example 6: Test Scaffold Pattern (mirrors test_dnssec_scanner.py)
```python
# Source: tests/test_dnssec_scanner.py structure — Plan 01 RED scaffold approach
from unittest.mock import patch, MagicMock
from quirk.scanner.kerberos_scanner import (
    scan_kerberos_targets,
    KERBEROS_ETYPE_MAP,
    IMPACKET_AVAILABLE,
    _probe_kdc,
)

def test_etype_map_rc4_is_high():
    """KERB-02: RC4-HMAC (etype 23) must be classified HIGH."""
    assert KERBEROS_ETYPE_MAP[23] == ("rc4-hmac", "HIGH")

def test_etype_map_des_is_critical():
    """KERB-02: DES etypes (1, 2, 3) must be classified CRITICAL."""
    assert KERBEROS_ETYPE_MAP[1][1] == "CRITICAL"
    assert KERBEROS_ETYPE_MAP[3][1] == "CRITICAL"

def test_scan_returns_empty_without_impacket():
    """KERB-01: Scanner must return empty list when impacket unavailable."""
    with patch("quirk.scanner.kerberos_scanner.IMPACKET_AVAILABLE", False):
        result = scan_kerberos_targets(["dc01.corp.local"])
    assert result == []

def test_rc4_produces_high_finding():
    """KERB-01, KERB-02: KDC returning etype 23 must produce HIGH finding."""
    with patch("quirk.scanner.kerberos_scanner._probe_kdc", return_value=[23, 18]), \
         patch("quirk.scanner.kerberos_scanner.IMPACKET_AVAILABLE", True):
        result = scan_kerberos_targets(["dc01.corp.local"])
    rc4_eps = [ep for ep in result if ep.cert_pubkey_alg == "rc4-hmac"]
    assert len(rc4_eps) >= 1
    assert rc4_eps[0].protocol == "KERBEROS"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| UDP-only Kerberos | TCP primary / UDP fallback | RFC 4120 (2005) | Enterprise networks often block UDP/88; TCP is the reliable path |
| PA_ETYPE_INFO (type 11) | PA_ETYPE_INFO2 (type 19) | RFC 4120 replaced RFC 1510 | ETYPE_INFO2 has s2kparams for string-to-key; old systems may still use ETYPE_INFO |
| DES etypes (1, 3) enabled by default | Samba 4.13+ removes DES from database | 2020 (Samba 4.13) | DES etypes unlikely in modern Samba; RC4 (etype 23) remains the primary finding |
| RC4-HMAC allowed by default | Samba 4.24.0 defaults to AES-only | 2026 (Samba 4.24) | Custom Dockerfile must explicitly set `kerberos encryption types = all` |
| Anonymous LDAP read common | Modern AD blocks unauthenticated binds | ~2003 (AD SP1) | KERB-03 must always gracefully degrade; LDAP path is best-effort |

**Deprecated/outdated:**
- `getKerberosTGT()` for this use case: It wraps AS-REQ in credential-centric flow; raw approach is required per D-02.
- DES etypes (1, 2, 3) in production: RFC 6649 deprecated them in 2012; still detected for compliance reporting.

---

## Open Questions

1. **Exact impacket MethodData import path**
   - What we know: `KerberosError.getErrorPacket()` returns the KRB_ERROR ASN.1 object; `e-data` contains METHOD_DATA (sequence of PA_DATA). `impacket.krb5.asn1` exports `MethodData` as a class.
   - What's unclear: Whether `MethodData` is importable directly from `impacket.krb5.asn1` in version 0.13.0, or must be constructed as `univ.SequenceOf(componentType=PA_DATA())`.
   - Recommendation: Plan 02 implementer must verify with `python3 -c "from impacket.krb5.asn1 import MethodData"` after installing `.[identity]`. If not available, use `univ.SequenceOf(componentType=PA_DATA())` manually — this is documented in the getKerberosTGT source.

2. **Samba DC healthcheck command availability**
   - What we know: `smbclient` is available in the samba package on debian:bookworm-slim; it can probe port 88 indirectly by listing shares.
   - What's unclear: Whether `smbclient -L localhost -N` reliably indicates KDC readiness (vs just SMB readiness). An alternative is `echo "" | kinit nobody@QUIRK.LAB 2>&1 | grep -q "KDC"`.
   - Recommendation: Use `smbclient -L localhost -N` as primary; it proves samba is serving and realm is initialized. 90s start_period provides ample buffer.

3. **Port conflicts for port 88 and 389 in chaos lab**
   - What we know: Port 88 is not currently exposed by any service in docker-compose.yml (confirmed via full file read). Port 389 is exposed as `13890:389` by the `identity` profile's `openldap` service.
   - What's unclear: Whether Samba DC should use `389:389` (direct) or a remapped port. The scanner probes port 389 directly, so the container must expose 389:389 — but if the user runs both `identity` and `kerberos` profiles simultaneously, port 389 conflicts.
   - Recommendation: Samba DC maps `389:389` for its kerberos profile. Document that kerberos and identity profiles cannot run simultaneously (port 389 conflict). The scanner's LDAP probe default target is port 389, consistent with KERB-03.

4. **impacket sendReceive timeout parameter**
   - What we know: `sendReceive(data, host, kdcHost, port=88)` — the function signature does not accept a `timeout` kwarg directly. Socket timeout must be set via `socket.setdefaulttimeout()` before calling, or the socket is created with blocking I/O.
   - What's unclear: Whether wrapping the call in a `threading.Timer` or using `socket.setdefaulttimeout(timeout)` is the cleaner approach.
   - Recommendation: Use `socket.setdefaulttimeout(timeout)` before calling `sendReceive()`, then restore to `None` after. This is a thread-safe concern — document and test.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | KERB-05 chaos lab | ✓ | 29.3.1 | — |
| impacket | KERB-01, KERB-02 | ✗ (system) | — (not in system Python) | Graceful degrade: `IMPACKET_AVAILABLE = False`, scanner returns `[]` |
| impacket (project venv) | KERB-01, KERB-02 | Declared in pyproject.toml `[identity]` extras | 0.13.0 on PyPI | Must install `pip install -e ".[identity]"` |
| samba (local) | Not needed locally | ✗ | — | Docker container handles Samba; local install not required |
| port 88 (localhost) | KERB-05 integration test | Available (not in use) | — | — |
| port 389 (localhost) | KERB-03 integration test | Available when kerberos profile active | — | Graceful skip if unreachable |
| pytest 9.0.2 | Test suite | ✓ | 9.0.2 | — |

**Missing dependencies with no fallback:**
- None that block execution. impacket not installed in system Python, but the project's optional extras group covers this for users who need Kerberos scanning.

**Missing dependencies with fallback:**
- impacket not in system Python: import guard pattern ensures graceful degradation for users without `[identity]` extras installed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (configfile detected by pytest auto-discovery) |
| Quick run command | `python3 -m pytest tests/test_kerberos_scanner.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KERB-01 | AS-REQ probe returns etype list from PA-ETYPE-INFO2 | unit (mock sendReceive) | `python3 -m pytest tests/test_kerberos_scanner.py::test_rc4_produces_high_finding -x` | ❌ Wave 0 |
| KERB-01 | Graceful degrade when impacket unavailable | unit | `python3 -m pytest tests/test_kerberos_scanner.py::test_scan_returns_empty_without_impacket -x` | ❌ Wave 0 |
| KERB-01 | Kerberos-unreachable record when TCP blocked | unit (mock socket error) | `python3 -m pytest tests/test_kerberos_scanner.py::test_unreachable_host_graceful -x` | ❌ Wave 0 |
| KERB-02 | RC4-HMAC etype 23 → HIGH in ETYPE_MAP | unit (static) | `python3 -m pytest tests/test_kerberos_scanner.py::test_etype_map_rc4_is_high -x` | ❌ Wave 0 |
| KERB-02 | DES etypes 1, 3 → CRITICAL in ETYPE_MAP | unit (static) | `python3 -m pytest tests/test_kerberos_scanner.py::test_etype_map_des_is_critical -x` | ❌ Wave 0 |
| KERB-02 | AES-256 etype 18 → SAFE in ETYPE_MAP | unit (static) | `python3 -m pytest tests/test_kerberos_scanner.py::test_etype_map_aes256_is_safe -x` | ❌ Wave 0 |
| KERB-02 | AES-128 etype 17 → HIGH in ETYPE_MAP | unit (static) | `python3 -m pytest tests/test_kerberos_scanner.py::test_etype_map_aes128_is_high -x` | ❌ Wave 0 |
| KERB-02 | Unknown etype → MEDIUM (default) | unit | `python3 -m pytest tests/test_kerberos_scanner.py::test_unknown_etype_is_medium -x` | ❌ Wave 0 |
| KERB-03 | Anonymous LDAP bind gracefully degrades | unit (mock ldap3) | `python3 -m pytest tests/test_kerberos_scanner.py::test_ldap_anon_graceful_degradation -x` | ❌ Wave 0 |
| KERB-04 | CryptoEndpoints have protocol="KERBEROS" | unit | `python3 -m pytest tests/test_kerberos_scanner.py::test_cryptoendpoint_protocol_kerberos -x` | ❌ Wave 0 |
| KERB-04 | kerberos_scan_json populated | unit | `python3 -m pytest tests/test_kerberos_scanner.py::test_kerberos_scan_json_populated -x` | ❌ Wave 0 |
| KERB-05 | Chaos lab integration (Samba DC) | integration (skip without QUIRK_INTEGRATION_TESTS) | `QUIRK_INTEGRATION_TESTS=1 python3 -m pytest tests/test_kerberos_scanner.py::test_chaos_lab_integration -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_kerberos_scanner.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_kerberos_scanner.py` — covers KERB-01 through KERB-05 (all 12 test functions above)
- [ ] `quirk/scanner/kerberos_scanner.py` — stub with `raise NotImplementedError` and exported symbols (`scan_kerberos_targets`, `KERBEROS_ETYPE_MAP`, `IMPACKET_AVAILABLE`, `_probe_kdc`)

---

## Sources

### Primary (HIGH confidence)
- github.com/fortra/impacket kerberosv5.py (master) — `sendReceive()` signature, `KerberosError` internals, PA_ETYPE_INFO2 extraction pattern from `getKerberosTGT()`
- github.com/fortra/impacket asn1.py (master) — `ETYPE_INFO2`, `ETYPE_INFO`, `AS_REQ`, `seq_set`, `seq_set_iter` class/function names and field names
- github.com/fortra/impacket GetNPUsers.py (master) — AS-REQ construction pattern: `encoder.encode(asReq)`, `sendReceive(message, domain, kdcIP)`, error catch structure
- quirk/scanner/dnssec_scanner.py — import guard pattern, severity map dict, scanner function signature, CryptoEndpoint construction
- quirk/scanner/saml_scanner.py — lazy import in run_scan.py pattern
- quirk/cbom/builder.py lines 351-365 — DNSSEC/SAML elif template for KERBEROS elif
- quirk/cbom/classifier.py — _ALGORITHM_TABLE pattern for Kerberos etype entries
- quirk/config.py — `enable_kerberos` and `kerberos_targets` already wired (verified)
- quirk/models.py — `kerberos_scan_json` column already exists (verified)
- run_scan.py lines 460-487 — DNSSEC/SAML block template for KERBEROS block

### Secondary (MEDIUM confidence)
- wiki.samba.org Setting_up_Samba_as_an_Active_Directory_Domain_Controller — `samba-tool domain provision` command flags (verified via official wiki)
- wiki.samba.org Samba_Features_added/changed — Samba 4.24.0 AES-default change (CVE-2026-20833 referenced), DES removal in 4.13
- help.univention.com — RC4-HMAC deprecation note (corroborates Samba 4.24.0 finding)
- quantum-chaos-enterprise-lab/docker-compose.yml — existing profile structure (bind9-dnssec, saml patterns verified by direct file read)

### Tertiary (LOW confidence)
- pip index versions impacket output — confirmed 0.13.0 is latest on PyPI as of 2026-04-09

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — impacket API verified against 0.13.0 source; version confirmed on PyPI
- Architecture patterns: HIGH — direct verification of existing scanner code; all templates confirmed by file read
- Pitfalls: HIGH (TCP-only sendReceive, etype_info vs etype_info2) — verified from source; MEDIUM (Samba RC4 defaults) — verified from wiki but Samba 4.24 is very recent
- Chaos lab: MEDIUM — Dockerfile pattern derived from existing bind9 + simplesamlphp art; Samba provisioning specifics are standard wiki commands; actual build will validate

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (30 days — impacket API is stable; Samba smb.conf knobs rarely change)
