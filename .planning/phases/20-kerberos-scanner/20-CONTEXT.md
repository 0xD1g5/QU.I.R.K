# Phase 20: Kerberos Scanner - Context

**Gathered:** 2026-04-09 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. can enumerate Kerberos encryption types from a KDC using an unauthenticated AS-REQ
probe — detecting RC4 and DES etypes that represent classical and quantum cryptographic risk.
Results stored in `kerberos_scan_json`, surfaced as `protocol="KERBEROS"` CryptoEndpoint rows,
CBOM integrated. Samba DC chaos lab profile added for scanner validation.

Two-plan TDD structure: Plan 01 creates RED scaffold, Plan 02 implements to GREEN.
Phase 21 (Identity Surface) depends on this phase completing.

</domain>

<decisions>
## Implementation Decisions

### impacket API Approach
- **D-01:** Use `impacket.krb5.kerberosv5.sendReceive()` + raw ASN.1 via `impacket.krb5.asn1.AS_REQ`
  — craft the AS-REQ body manually, advertise all etypes in the request, send/receive over raw
  socket, parse `KDC_ERR_PREAUTH_REQUIRED` error response's padata for `PA-ETYPE-INFO2`.
- **D-02:** Do NOT use `getKerberosTGT()` wrapper — it is designed for authenticated flows and
  does not expose raw error response parsing cleanly. Fragile against impacket updates.
- **D-03:** This pattern mirrors impacket's own `GetNPUsers.py` internals and the DNSSEC scanner's
  approach (raw query → parse response → classify). Advertising all etypes in the probe ensures
  the KDC returns its full support list, not a filtered subset.
- **D-04:** Import guard: `IMPACKET_AVAILABLE = True/False` — same pattern as `DNSPYTHON_AVAILABLE`
  and `LXML_AVAILABLE` in prior scanners.

### kerberos_targets Format
- **D-05:** Plain hostnames/IPs only: `kerberos_targets: ["dc01.corp.local", "192.168.1.10"]`
  — consistent with `dnssec_targets` (domain names). No realm required from user.
- **D-06:** Scanner auto-derives realm by uppercasing the FQDN (e.g., `CORP.LOCAL`) for the
  initial AS-REQ; reads actual `crealm` from the KDC error response body to correct if needed.
- **D-07:** Chaos lab target is simply `"127.0.0.1"` or `"localhost"` — no special format.

### Etype Severity Classification
- **D-08:** DES etypes (1, 2, 3) → CRITICAL (from KERB-02)
- **D-09:** RC4-HMAC (etype 23) → HIGH (from KERB-02)
- **D-10:** AES-256-CTS-HMAC-SHA1-96 (etype 18), AES256-CTS-HMAC-SHA384-192 (etype 20) → SAFE (from KERB-02)
- **D-11:** AES-128-CTS-HMAC-SHA1-96 (etype 17) → HIGH — Grover's algorithm reduces effective
  security to ~64 bits, below the 128-bit post-quantum threshold. Not SAFE; not CRITICAL.
  Consultant talking point: "migrate to AES-256 for long-term quantum safety."
- **D-12:** Any unrecognized etype → MEDIUM (safe default, logged for review).

### Samba DC Chaos Lab
- **D-13:** Custom Dockerfile in `quantum-chaos-enterprise-lab/samba/` (not a community image).
  Base: `debian:bookworm-slim` + `samba` package.
- **D-14:** `smb.conf` must include `ntlm auth = ntlmv1-permitted` and
  `kerberos encryption types = all` to enable RC4 (etype 23) alongside AES.
- **D-15:** Docker Compose profile name: `kerberos`. `start_period: 90s` healthcheck on port 88
  (matches KERB-05 requirement — Samba DC takes time to provision realm on first start).
- **D-16:** Realm: `QUIRK.LAB` (consistent with lab domain naming; short, no conflicts).

### run_scan.py Integration
- **D-17:** Follow SAML/DNSSEC pattern exactly: lazy import inside `if cfg.connectors.enable_kerberos`
  block, `_phase_timer` context manager, results aggregated into `all_endpoints`.

### CBOM / Classifier
- **D-18:** `elif ep.protocol == "KERBEROS":` branch in `builder.py` — follows DNSSEC → SAML → KERBEROS chain.
- **D-19:** Classifier entries for etype names (e.g., `"rc4-hmac"`, `"des-cbc-md5"`, `"aes256-cts-hmac-sha1-96"`).

### Claude's Discretion
- Exact socket timeout defaults for AS-REQ probe
- TCP vs UDP retry logic internals (TCP primary, UDP fallback — behavior is locked, implementation detail is open)
- Test fixture approach for AS-REQ/error response (bytes fixture or mock socket)
- Samba container entrypoint script details (realm provisioning command)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §KERB-01 through KERB-05 — all 5 Kerberos requirements

### Prior Scanner Art (read these for pattern consistency)
- `quirk/scanner/dnssec_scanner.py` — import guard, severity map dict, scanner function signature, CryptoEndpoint construction
- `quirk/scanner/saml_scanner.py` — import guard, scan entry point pattern, CBOM integration
- `tests/test_dnssec_scanner.py` — TDD scaffold structure (RED tests, fixture approach, integration skip marker)
- `tests/test_saml_scanner.py` — TDD scaffold structure (26 tests, cert fixtures embedded)

### Integration Points (read before modifying)
- `run_scan.py` lines 460–485 — DNSSEC and SAML scanner integration blocks (copy pattern for KERBEROS)
- `quirk/cbom/builder.py` line 351–365 — DNSSEC and SAML elif branches (add KERBEROS elif after SAML)
- `quirk/cbom/classifier.py` — existing etype/algorithm entries (add Kerberos etype names)
- `quirk/config.py` line 62, 66 — `enable_kerberos` and `kerberos_targets` already wired
- `quirk/models.py` line 67 — `kerberos_scan_json` column already exists

### Chaos Lab Reference
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing profile structure (saml, dnssec, bind9)
- `quantum-chaos-enterprise-lab/simplesamlphp/` — SAML lab subdirectory structure to mirror

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/models.py:CryptoEndpoint` — existing model, no changes needed for KERBEROS protocol
- `quirk/config.py:ConnectorsCfg.enable_kerberos` + `kerberos_targets` — already wired in Phase 17
- `quirk/models.py:ScanResult.kerberos_scan_json` — column already exists
- `_phase_timer` context manager in `run_scan.py` — reuse for KERBEROS block

### Established Patterns
- Import guard: `try: import X; FLAG = True except ImportError: FLAG = False`
- Severity dict: `KERBEROS_ETYPE_MAP: dict = {etype_int: (name, severity), ...}`
- Scanner returns `list[CryptoEndpoint]`, empty list on missing dependency or error
- TDD: Plan 01 creates stub with `raise NotImplementedError`, Plan 02 implements

### Integration Points
- `run_scan.py` SAML block (lines 472–483) is the direct template for the KERBEROS block
- `builder.py` SAML elif (lines 357–365) is the direct template for KERBEROS elif
- No new columns needed — Phase 17 pre-wired everything

</code_context>

<specifics>
## Specific Ideas

- Advertise ALL etypes in the AS-REQ probe to maximize KDC response completeness
- `QUIRK.LAB` as the Samba realm name
- AES-128 (etype 17) = HIGH with explicit rationale: Grover halves effective security to 64-bit equivalent
- Mirroring the SimpleSAMLphp chaos lab pattern: custom Dockerfile in its own subdirectory

</specifics>

<deferred>
## Deferred Ideas

- `KERB-ADV-01`: Per-account etype probing via authenticated LDAP `msDS-SupportedEncryptionTypes`
  — already explicitly deferred in REQUIREMENTS.md (breaks agentless constraint; SaaS model)
- Kerberoasting / SPN enumeration — explicitly out of scope (pentest territory)
- Windows AD CS live connector — stub remains, deferred

</deferred>

---

*Phase: 20-kerberos-scanner*
*Context gathered: 2026-04-09*
