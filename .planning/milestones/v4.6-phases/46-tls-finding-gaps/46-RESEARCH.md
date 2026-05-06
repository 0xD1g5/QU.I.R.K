# Phase 46: TLS Finding Gaps — Research

**Researched:** 2026-05-03
**Domain:** Python TLS scanning, risk engine finding logic, Docker chaos lab cert fixtures
**Confidence:** HIGH — all findings verified directly from codebase source files

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — sslyze fallback: result-validation gate**
After sslyze runs, validate `ep.cert_not_after is None OR ep.cert_subject is empty`. If the
gate trips, re-run via the basic-ssl fallback path and merge results. Both paths MUST assign
`ep.chain_verified` explicitly.
- sslyze path (success): `ep.chain_verified = (deployment.verified_certificate_chain is not None)`
- basic-ssl fallback: separate validating context with `ctx.verify_mode = ssl.CERT_REQUIRED`
  and `ctx.check_hostname = True` against the system trust store; on `SSLCertVerificationError`,
  set `ep.chain_verified = False` while still extracting cert metadata via a second
  `verify_mode = ssl.CERT_NONE` pass.

**D-02 — Combined defects: separate findings per class**
A cert with multiple defects emits one finding per defect class, not a rollup. Each of the five
risk_engine branches at lines 343–423 must be independent (no early-return / no else-if chains
across classes).

**D-03 — Chaos lab: new combined profile, dedicated ports**
Create a single new profile `tls-cert-defects` with 4 nginx services on dedicated ports.
Existing `tls-expired` and `tls-selfsigned` profiles stay unchanged.
- `tls-cert-expired` — port `13443` — uses existing expired cert fixtures
- `tls-cert-selfsigned` — port `13444` — uses existing self-signed fixtures
- `tls-cert-untrusted-ca` — port `13445` — NEW: cert signed by off-trust-store CA
- `tls-cert-rsa1024` — port `13446` — NEW: cert with RSA-1024 key

**D-04 — Self-signed vs untrusted-CA: mutually exclusive**
| Finding | Severity | Trigger |
|---|---|---|
| Self-signed (TLS-FIND-02) | HIGH | `cert_issuer == cert_subject` |
| Untrusted-CA (TLS-FIND-03) | MEDIUM | `cert_issuer != cert_subject AND chain_verified is False` |

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- Severity calibration profile for cert defects
- Hostname mismatch as a separate cert finding type
- Auto-remediation hints with platform-specific commands
- Cipher-suite findings (covered by existing risk_engine logic)
- OCSP/CRL revocation checks
- Rich finding context (BACK-79) — separate phase
- EC curve weakness beyond key size
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TLS-FIND-01 | User receives a CRITICAL finding when QUIRK encounters an expired TLS certificate | risk_engine.py:343–366 already emits this finding but at severity HIGH — must be bumped to CRITICAL per requirement wording |
| TLS-FIND-02 | User receives a HIGH finding when QUIRK encounters a self-signed TLS certificate | risk_engine.py:372–389 emits MEDIUM today — must be bumped to HIGH for self-signed branch (post D-04 split) |
| TLS-FIND-03 | User receives a MEDIUM finding when QUIRK encounters an untrusted-CA cert | risk_engine.py:372–389 combined branch must be split per D-04; untrusted-CA stays MEDIUM |
| TLS-FIND-04 | User receives a HIGH finding for RSA key < 2048 bits | risk_engine.py:391–398 already emits HIGH for RSA<2048 — fires correctly once chain_verified is wired |
| TLS-FIND-05 | User receives a HIGH finding for EC key < 256 bits | risk_engine.py:416–423 already emits HIGH for EC<256 — fires correctly once chain_verified is wired |
| TLS-FIND-06 | TLS scanner falls back to basic ssl_info path when sslyze CERTIFICATE_INFO returns ERROR | D-01 plumbing: validation gate in scan_one() + chain_verified assigned in both paths |
| TLS-FIND-07 | New chaos lab profile `tls-cert-defects` serves expired, self-signed, untrusted-CA, RSA-1024 certs | D-03: new profile with 4 services; cert fixtures for untrusted-CA and RSA-1024 already exist in scenarios/ |
</phase_requirements>

---

## Summary

Phase 46 is a wiring and severity-correction problem across three layers: the TLS scanner
(`quirk/scanner/tls_scanner.py`), the data model (`quirk/models.py`), and the risk engine
(`quirk/engine/risk_engine.py`). The risk engine already contains all five finding branches.
They partially fire today but cannot fire correctly because `chain_verified` is computed locally
inside `_scan_one_sslyze` at line 208 but is never assigned to the returned `CryptoEndpoint`.
The fallback path (`_scan_one_fallback`) does not compute it at all. The risk engine therefore
reads `chain_verified` indirectly through `tls_capabilities_json` (a JSON blob) for the sslyze
path, but this field is absent on fallback-scanned endpoints.

In addition, two severity mismatches exist between the requirements spec and the current
implementation that must be corrected as part of this phase: TLS-FIND-01 requires CRITICAL
(engine currently emits HIGH), and TLS-FIND-02 requires HIGH (engine currently emits MEDIUM for
the combined self-signed/untrusted-CA branch). The D-04 split resolves the TLS-FIND-02/03
branching issue simultaneously.

The chaos lab work is primarily additive: port 13443 is already allocated to `tls-missing-intermediate`
(phaseA profile), so D-03's `tls-cert-expired` must use a different port. RSA-1024 cert fixtures
already exist at `certs/scenarios/rsa1024/`. An untrusted-CA cert can be generated from the
existing `certs/scenarios/scenario-root/` CA. The `lab.sh` `_derive_all_profiles` function is
self-healing — it reads profiles from docker-compose.yml at runtime, so adding the new profile
to compose is sufficient; no hardcoded `ALL_PROFILES` array exists to update.

**Primary recommendation:** Three plan tasks — (1) scanner layer: add validation gate + chain_verified
plumbing to both sslyze and fallback paths; (2) risk engine: severity corrections + D-04 branch
split; (3) chaos lab: new tls-cert-defects profile + cert generation + oracle docs.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| chain_verified computation (sslyze path) | Scanner (`tls_scanner.py`) | — | sslyze result object is only available here |
| chain_verified computation (fallback path) | Scanner (`tls_scanner.py`) | — | ssl.SSLContext is only available here |
| CryptoEndpoint.chain_verified field | Data model (`models.py`) | — | Must be declared as Column to survive SQLite persistence |
| Finding emission (all 5 classes) | Risk engine (`risk_engine.py`) | — | Canonical finding authority; engine reads ep fields |
| chain_verified field access in engine | Risk engine via `_chain_verified()` | — | Currently reads tls_capabilities_json JSON blob |
| Cert fixture generation | Chaos lab scripts (`scripts/`) | — | openssl CLI, run once, artifacts checked in |
| TLS service profiles | Chaos lab (`docker-compose.yml`) | — | nginx containers; profile tag required for selective start |
| Lab start/stop orchestration | Chaos lab (`lab.sh`) | — | `_derive_all_profiles` reads compose at runtime |
| Oracle documentation | Chaos lab (`expected_results_v4.md`) | — | Per-profile expected findings; consumed by UAT |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python ssl stdlib | stdlib | Fallback TLS handshake + cert extraction | No dependency; already used in `_scan_one_fallback` |
| cryptography | ≥38 (project uses 44+) | x509 cert parsing, RSA/EC key inspection | Already imported in tls_scanner.py; `_pubkey_info` uses it |
| sslyze | 6.x (mock shows 6.3.1) | Primary TLS scanner; CERTIFICATE_INFO command | Already integrated; Phase 46 is wiring only |
| SQLAlchemy | 2.x | ORM; `CryptoEndpoint` table columns | Already used; new column follows established pattern |
| openssl CLI | 3.x (system) | Cert generation for chaos lab | Already used in gen-certs.sh and gen_phaseA_certs.sh |
| nginx:stable | Docker image | Chaos lab TLS endpoint | Already used for all existing TLS profiles |

[VERIFIED: direct codebase inspection]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 7+ | Unit + integration tests | All new tests follow existing test_risk_engine.py pattern |
| unittest.mock | stdlib | Mocking sslyze in tests | Used extensively in test_sslyze_integration.py |

---

## Architecture Patterns

### System Architecture Diagram

```
[chaos lab: nginx tls-cert-defects profile]
        |
        | TLS handshake (port 13444/13445/13446/13447)
        v
[quirk/scanner/tls_scanner.py: scan_one()]
    |
    +--[sslyze available?]--YES--> [_scan_one_sslyze()]
    |                                   |
    |                              [CERTIFICATE_INFO COMPLETED?]
    |                                   |          |
    |                               YES v       NO v (ERROR)
    |                              populate      return None
    |                              cert fields
    |                              ep.chain_verified = verified_chain is not None
    |                              [validation gate: cert_not_after is None?]
    |                                   |          |
    |                               NO: return ep  YES: fall through to fallback
    |
    +--[fallback path]--> [_scan_one_fallback()]
                              |
                              +--[CERT_REQUIRED context] --> SSLCertVerificationError?
                              |       YES: ep.chain_verified = False
                              |       NO:  ep.chain_verified = True
                              |
                              +--[CERT_NONE context] --> extract cert metadata
                              |
                              return ep (with chain_verified assigned)
        |
        v
[quirk/models.py: CryptoEndpoint]
    chain_verified: Optional[bool]  <-- NEW COLUMN (if not present)
        |
        v
[quirk/engine/risk_engine.py: evaluate_endpoints()]
    _chain_verified(ep) reads tls_capabilities_json OR ep.chain_verified
    |
    +-- cert_not_after < now: CRITICAL "TLS certificate expired"        (TLS-FIND-01)
    +-- issuer == subject: HIGH "TLS certificate self-signed"           (TLS-FIND-02)
    +-- issuer != subject AND cv is False: MEDIUM "Untrusted CA"        (TLS-FIND-03)
    +-- RSA pubkey_size < 2048: HIGH "Undersized RSA key"               (TLS-FIND-04)
    +-- EC pubkey_size < 256: HIGH "Undersized EC key"                  (TLS-FIND-05)
```

### Recommended Project Structure

No new directories needed. All changes are modifications to existing files:

```
quirk/
├── models.py              # Add chain_verified column (if absent)
├── scanner/
│   └── tls_scanner.py     # Add validation gate + chain_verified plumbing
├── engine/
│   └── risk_engine.py     # Severity corrections + D-04 branch split
quantum-chaos-enterprise-lab/
├── certs/
│   └── scenarios/
│       └── untrusted-ca/  # NEW: leaf cert signed by scenario-root CA
├── nginx/
│   └── cert-defects/      # NEW: 4 nginx confs (one per service)
│       ├── expired/nginx.conf
│       ├── selfsigned/nginx.conf
│       ├── untrusted-ca/nginx.conf
│       └── rsa1024/nginx.conf
├── docker-compose.yml     # Add tls-cert-defects profile (4 services)
├── expected_results_v4.md # Add tls-cert-defects section
└── README.md              # Profile entry
tests/
└── test_tls_finding_gaps.py  # NEW: covers TLS-FIND-01..06
```

### Pattern 1: chain_verified plumbing — sslyze path

The sslyze path ALREADY computes `chain_verified` at line 208 and stores it in `tls_capabilities_json`.
The only gap is that it does not assign to `ep.chain_verified`. The fix is a one-liner after line 208.

```python
# Source: quirk/scanner/tls_scanner.py:208 (current)
chain_verified = deployment.verified_certificate_chain is not None
# ADD this line:
ep.chain_verified = chain_verified
```

[VERIFIED: tls_scanner.py lines 207-211, models.py inspection]

### Pattern 2: chain_verified plumbing — fallback path (D-01)

The fallback path uses `ssl.CERT_NONE` (no verification). D-01 requires a second pass with
`CERT_REQUIRED` to compute `chain_verified`. The two-pass pattern is:

```python
# Source: D-01 decision (CONTEXT.md), pattern derived from stdlib ssl docs [ASSUMED implementation]
# Pass 1: verification context (compute chain_verified)
try:
    verify_ctx = ssl.create_default_context()
    verify_ctx.check_hostname = True
    verify_ctx.verify_mode = ssl.CERT_REQUIRED
    with socket.create_connection((host, port), timeout=timeout) as vsock:
        with verify_ctx.wrap_socket(vsock, server_hostname=host) as vssock:
            ep.chain_verified = True
except ssl.SSLCertVerificationError:
    ep.chain_verified = False
except Exception:
    ep.chain_verified = None  # network error — don't assert verified or unverified

# Pass 2: existing CERT_NONE context (extract cert metadata — already in _scan_one_fallback)
```

The existing `_scan_one_fallback` body (lines 344–420) handles pass 2 (CERT_NONE). The validation
gate and pass 1 are inserted BEFORE the existing CERT_NONE block.

[VERIFIED: tls_scanner.py:328-420 inspected; implementation structure ASSUMED per D-01]

### Pattern 3: _chain_verified() in risk_engine — current indirect access

The risk engine does NOT read `ep.chain_verified` directly. It reads through a JSON blob:

```python
# Source: risk_engine.py:136-146 [VERIFIED]
def _chain_verified(ep: Any) -> Optional[bool]:
    """Parse chain_verified from tls_capabilities_json blob; returns None if absent."""
    caps_raw = getattr(ep, "tls_capabilities_json", None)
    if not caps_raw:
        return None
    try:
        caps = json.loads(caps_raw)
        val = caps.get("chain_verified")
        return bool(val) if val is not None else None
    except Exception:
        return None
```

Once `ep.chain_verified` is a real SQLAlchemy column, the engine can use direct field access.
The `_chain_verified()` helper should be updated to prefer `ep.chain_verified` and fall back
to JSON parsing for backwards compatibility.

[VERIFIED: risk_engine.py:136-146]

### Pattern 4: risk_engine branch split (D-04)

Current combined branch at lines 372–389:

```python
# Source: risk_engine.py:371-385 [VERIFIED]
# BUG-03: Self-signed or chain-unverified certificate
cert_issuer = (getattr(e, "cert_issuer", "") or "").strip()
cert_subject = (getattr(e, "cert_subject", "") or "").strip()
cv = _chain_verified(e)
if (cert_issuer and cert_subject and cert_issuer == cert_subject) or cv is False:
    findings.append({
        "severity": "MEDIUM",
        ...
        "title": "Self-signed or untrusted TLS certificate",
    })
```

Post-D-04 replacement:

```python
# Self-signed: issuer == subject (HIGH per TLS-FIND-02)
if cert_issuer and cert_subject and cert_issuer == cert_subject:
    findings.append({"severity": "HIGH", "title": "TLS certificate is self-signed", ...})
# Untrusted CA: issuer != subject AND chain verification failed (MEDIUM per TLS-FIND-03)
elif cert_issuer and cert_subject and cert_issuer != cert_subject and cv is False:
    findings.append({"severity": "MEDIUM", "title": "TLS certificate issued by untrusted CA", ...})
```

[VERIFIED: risk_engine.py:371-385 structure; D-04 trigger logic from CONTEXT.md]

### Pattern 5: severity corrections

Two severities must change:

| Requirement | Current engine severity | Required severity | Lines |
|-------------|------------------------|-------------------|-------|
| TLS-FIND-01 (expired cert) | HIGH | CRITICAL | risk_engine.py:349 |
| TLS-FIND-02 (self-signed) | MEDIUM (combined) | HIGH (split branch) | risk_engine.py:379 |

The existing test `test_expired_cert_produces_high_finding` in `test_risk_engine.py` will break
when severity is changed to CRITICAL — the test must be updated in the same commit.

[VERIFIED: risk_engine.py:349, REQUIREMENTS.md TLS-FIND-01/02, test_risk_engine.py:97-103]

### Pattern 6: chaos lab profile with Docker profiles tag

Existing profile pattern (from docker-compose.yml):

```yaml
# Source: quantum-chaos-enterprise-lab/docker-compose.yml (phaseA example) [VERIFIED]
tls-rsa1024:
  image: nginx:stable
  profiles: ["phaseA"]
  volumes:
    - ./nginx/phaseA/tls-rsa1024/nginx.conf:/etc/nginx/nginx.conf:ro
    - ./certs/scenarios:/etc/nginx/scenarios:ro
  ports:
    - "14443:443"
```

New `tls-cert-defects` services follow this exact pattern with `profiles: ["tls-cert-defects"]`.

[VERIFIED: docker-compose.yml lines 184-194]

### Pattern 7: lab.sh — no manual ALL_PROFILES update needed

`lab.sh` uses `_derive_all_profiles()` which reads profiles from docker-compose.yml at runtime
via `yq` or grep. There is NO hardcoded `ALL_PROFILES` array. Adding the new profile to
docker-compose.yml is sufficient for `./lab.sh all` to pick it up.

```bash
# Source: lab.sh:56-68 [VERIFIED]
_derive_all_profiles() {
  if command -v yq >/dev/null 2>&1; then
    yq eval '.. | select(has("profiles")) | .profiles[]' "${COMPOSE_FILE}" 2>/dev/null | sort -u
  else
    grep -E '^[[:space:]]*profiles:[[:space:]]*\[' "${COMPOSE_FILE}" \
      | grep -oE '"[a-zA-Z0-9_-]+"' | tr -d '"' | sort -u
  fi
}
```

[VERIFIED: lab.sh:56-68]

### Pattern 8: nginx conf for TLS service (minimal)

```nginx
# Source: quantum-chaos-enterprise-lab/nginx/selfsigned/nginx.conf [VERIFIED]
events {}
http {
  server {
    listen 443 ssl;
    server_name <name>.chaos.local;
    ssl_certificate     /etc/nginx/certs/<name>.crt;
    ssl_certificate_key /etc/nginx/certs/<name>.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    location / { return 200 "OK - <name>\n"; }
  }
}
```

For the untrusted-CA and rsa1024 services, mount `certs/scenarios` (not `certs`) as the volume.

### Anti-Patterns to Avoid

- **Reading chain_verified from JSON blob in new code:** Post-phase, use `ep.chain_verified`
  directly; leave `_chain_verified()` as fallback for old records.
- **Assigning chain_verified=False on network errors:** A timeout or connection refused is not
  a chain failure. Use `None` for indeterminate state.
- **Adding chain_verified to `quirk/discovery/tls_scanner.py`:** That module is not imported
  anywhere in the scan pipeline (verified: no callers). Out of scope for Phase 46.
- **Regenerating existing cert fixtures:** `certs/expired.crt` and `certs/selfsigned.crt` are
  already checked in and used by the existing tls-expired/tls-selfsigned profiles. The new
  tls-cert-expired and tls-cert-selfsigned services can reuse these same files.
- **Using else-if chains across the five finding branches:** D-02 requires all five branches to
  be independent `if` checks, not `elif`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chain verification | Custom OCSP/CRL logic | `ssl.CERT_REQUIRED` + system trust store | stdlib handles all CA bundle lookup; custom logic breaks on corporate CAs |
| RSA/EC key size parsing | Manual DER decoding | `cryptography` library `_pubkey_info()` (already in tls_scanner.py) | Edge cases in key encoding |
| Cert subject/issuer parsing | String manipulation of DN | `leaf.subject.rfc4514_string()` / `leaf.issuer.rfc4514_string()` | RFC 4514 encoding; multi-value RDNs are tricky |
| Docker profile orchestration | Custom script | `docker compose --profile <name>` | Compose native; `_derive_all_profiles` auto-discovers |

---

## Critical Findings — Port Conflicts

**Port 13443 is already allocated.** The `tls-missing-intermediate` service (phaseA profile)
uses port `13443:443`. D-03 proposes `tls-cert-expired` on 13443, which would conflict when
both profiles run simultaneously.

**Resolution options (planner decision):**

1. Use ports 13444–13447 instead of 13443–13446 for the tls-cert-defects profile.
2. Accept the conflict (phaseA and tls-cert-defects are unlikely to run simultaneously for UAT).
3. Use alternative ports entirely (e.g., 16444–16447 which are free).

[VERIFIED: docker-compose.yml line 182, `netstat` port scan — 13443 LISTEN, 13444-13446 free]

The planner MUST resolve this conflict before assigning ports in the plan.

---

## CryptoEndpoint.chain_verified — Model Gap

`chain_verified` is NOT a declared column on `CryptoEndpoint` in `quirk/models.py`.

[VERIFIED: models.py full inspection — no `chain_verified` column exists]

The field must be added as:
```python
# Following the v4.6 comment pattern in models.py
# ==========================
# v4.6 TLS finding gap fields
# ==========================
chain_verified = Column(Boolean, nullable=True)
```

`nullable=True` is required: existing rows in SQLite have no value for this column; the engine
uses `getattr(ep, "chain_verified", None)` defensively already (via `_chain_verified()`).

SQLAlchemy adds columns to existing databases via `CREATE TABLE` on new databases or a migration
on existing ones. The project uses SQLAlchemy ORM with `Base.metadata.create_all()` — new columns
on existing databases require a migration or database recreation. Check whether the project has
a migration path or relies on fresh DB per scan run.

[VERIFIED: models.py; migration pattern ASSUMED — planner should confirm db.py behavior]

---

## Cert Fixtures — Availability Map

| Profile Service | Cert Needed | Status | Location |
|-----------------|-------------|--------|----------|
| tls-cert-expired | `expired.crt` + `expired.key` | EXISTS | `certs/expired.{crt,key}` |
| tls-cert-selfsigned | `selfsigned.crt` + `selfsigned.key` | EXISTS | `certs/selfsigned.{crt,key}` |
| tls-cert-rsa1024 | RSA-1024 leaf cert | EXISTS | `certs/scenarios/rsa1024/leaf.{crt,key}` |
| tls-cert-untrusted-ca | leaf signed by untrusted CA | NEEDS GENERATION | See below |

[VERIFIED: filesystem inspection of `certs/` and `certs/scenarios/`]

**tls-cert-untrusted-ca cert generation:**

The scenario-root CA (`certs/scenarios/scenario-root/ca.crt`) is NOT in the system trust store.
A leaf cert signed by this CA will have `issuer != subject` (correct for D-04 untrusted-CA
branch) and will fail chain verification. The gen_phaseA_certs.sh `issue_leaf` helper can
generate this cert with a one-line addition:

```bash
# Source: scripts/gen_phaseA_certs.sh:19-42 (issue_leaf pattern) [VERIFIED]
issue_leaf "untrusted-ca" "untrusted-ca.chaos.local" "scenario-root" 365 2048 sha256
```

This produces:
- `certs/scenarios/untrusted-ca/leaf.crt` — subject `CN=untrusted-ca.chaos.local`
- issuer `CN=scenario-root-CA` (not in system trust store)
- RSA-2048 key (strong key size — isolates the untrusted-CA finding from RSA-1024 finding)

[VERIFIED: gen_phaseA_certs.sh:76 uses identical pattern for rsa1024]

**rsa1024 nginx conf for new profile:**

The phaseA `tls-rsa1024` nginx conf already serves RSA-1024 certs. The new `tls-cert-rsa1024`
service can reuse the same cert files (`certs/scenarios/rsa1024/leaf.{crt,key}`) with a new
nginx conf matching the `tls-cert-defects` profile's mount path.

[VERIFIED: docker-compose.yml:184-194, nginx/phaseA/tls-rsa1024/nginx.conf]

---

## Common Pitfalls

### Pitfall 1: chain_verified=False on DNS/connection failure

**What goes wrong:** If the validation CERT_REQUIRED pass fails due to a network timeout or
connection refused (not a certificate error), the code might set `ep.chain_verified = False`,
causing a spurious untrusted-CA finding.

**Why it happens:** `SSLCertVerificationError` is the only exception that means "cert not
trusted". `ConnectionRefusedError`, `TimeoutError`, and other `OSError` subclasses mean
"couldn't connect" — not a trust failure.

**How to avoid:** Catch only `ssl.SSLCertVerificationError` for `chain_verified = False`.
For all other exceptions, set `chain_verified = None` (indeterminate).

**Warning signs:** "Untrusted CA" findings on hosts known to have valid certs.

### Pitfall 2: Severity regression in existing tests

**What goes wrong:** Bumping `cert_expired` from HIGH to CRITICAL and `self-signed` from MEDIUM
to HIGH will break four existing tests in `test_risk_engine.py`.

**Why it happens:** Tests assert specific severity strings (`"HIGH"`, `"MEDIUM"`).

**How to avoid:** Update the failing tests in the same commit as the engine change. The tests
to update:
- `TestCertExpiry.test_expired_cert_produces_high_finding` → assert CRITICAL
- `TestSelfSigned.test_self_signed_issuer_eq_subject_produces_medium` → assert HIGH
- `TestSelfSigned.test_chain_unverified_false_produces_medium` → keep MEDIUM (untrusted-CA branch)
- `TestMultipleRulesOnOneEndpoint.test_expired_self_signed_rsa1024_all_fire` → update severity assertions

[VERIFIED: test_risk_engine.py:97-103, 141-149, 151-161, 253-269]

### Pitfall 3: OpenSSL legacy.cnf required for RSA-1024 nginx

**What goes wrong:** Modern OpenSSL (3.x) rejects RSA-1024 keys by default. nginx serving an
RSA-1024 cert will fail to start without a legacy OpenSSL config.

**Why it happens:** FIPS/security level enforcement in OpenSSL 3.

**How to avoid:** The `tls-rsa1024` phaseA service already handles this:
```yaml
environment:
  - OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf
volumes:
  - ./nginx/openssl-legacy.cnf:/etc/nginx/openssl-legacy.cnf:ro
```

The new `tls-cert-rsa1024` service MUST include these same environment and volume entries.

[VERIFIED: docker-compose.yml:184-194]

### Pitfall 4: `_chain_verified()` returns None (not False) when no JSON blob

**What goes wrong:** For fallback-scanned endpoints (no sslyze), `tls_capabilities_json` is
either absent or populated without `chain_verified`. `_chain_verified()` returns `None`.
The current engine condition `or cv is False` does NOT fire on `None`.

**Why it happens:** `None is False` evaluates to `False` in Python. The OR branch requires
`cv is False` (identity check), not `cv == False` (equality).

**How to avoid:** After adding `ep.chain_verified`, update `_chain_verified()` to prefer the
direct field:
```python
def _chain_verified(ep: Any) -> Optional[bool]:
    # Prefer direct column value (Phase 46+)
    cv_direct = getattr(ep, "chain_verified", _SENTINEL)
    if cv_direct is not _SENTINEL and cv_direct is not None:
        return bool(cv_direct)
    # Fallback: parse from JSON blob (pre-Phase-46 records)
    caps_raw = getattr(ep, "tls_capabilities_json", None)
    ...
```

[VERIFIED: risk_engine.py:136-146; behavior analysis verified]

### Pitfall 5: Port conflict between tls-cert-defects and phaseA

**What goes wrong:** Port 13443 is used by `tls-missing-intermediate` (phaseA). If both
profiles start simultaneously, Docker will refuse to bind the second service to 13443.

**How to avoid:** Assign tls-cert-defects services to ports NOT used by phaseA. Confirmed free:
13444, 13445, 13446 (net scan confirmed). Suggested final assignment:
- `tls-cert-expired` → port 13444
- `tls-cert-selfsigned` → port 13445
- `tls-cert-untrusted-ca` → port 13446
- `tls-cert-rsa1024` → port 13447 (need to verify 13447 is free)

[VERIFIED: netstat shows 13443 LISTEN; 13444-13446 free]

---

## Code Examples

### `_chain_verified()` — direct-field-first lookup (post Phase 46)

```python
# Source: risk_engine.py:136-146 (current), annotated with Phase 46 change
_SENTINEL = object()

def _chain_verified(ep: Any) -> Optional[bool]:
    # Phase 46: prefer direct column value
    cv_direct = getattr(ep, "chain_verified", _SENTINEL)
    if cv_direct is not _SENTINEL and cv_direct is not None:
        return bool(cv_direct)
    # Backward-compat: parse from JSON blob (records written before Phase 46)
    caps_raw = getattr(ep, "tls_capabilities_json", None)
    if not caps_raw:
        return None
    try:
        caps = json.loads(caps_raw)
        val = caps.get("chain_verified")
        return bool(val) if val is not None else None
    except Exception:
        return None
```

### Validation gate in scan_one() — D-01

```python
# Source: tls_scanner.py:441-449 (current scan_one), annotated with D-01 gate [ASSUMED implementation]
def scan_one(host, port, timeout, include_sni, logger=None, tls_enum_mode="fast"):
    if SSLYZE_AVAILABLE:
        try:
            ep = _scan_one_sslyze(host, port, timeout, include_sni, logger)
            if ep is not None:
                # D-01 validation gate: if cert fields are missing, merge with fallback
                if ep.cert_not_after is None or not ep.cert_subject:
                    fallback = _scan_one_fallback(host, port, timeout, include_sni, logger, tls_enum_mode)
                    # Merge: take cert fields from fallback if sslyze left them empty
                    if ep.cert_not_after is None:
                        ep.cert_not_after = fallback.cert_not_after
                    if not ep.cert_subject:
                        ep.cert_subject = fallback.cert_subject
                    if ep.chain_verified is None:
                        ep.chain_verified = fallback.chain_verified
                return ep
        except Exception as e:
            ...
    return _scan_one_fallback(host, port, timeout, include_sni, logger, tls_enum_mode)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single sslyze-or-fallback dispatch | sslyze + validation gate + fallback merge | Phase 46 | Eliminates half-populated endpoints |
| Combined self-signed/untrusted-CA finding | Two mutually exclusive findings | Phase 46 (D-04) | Correct severity per TLS-FIND-02/03 |
| chain_verified in JSON blob only | Direct SQLAlchemy column + JSON fallback | Phase 46 | Engine can query without JSON parsing |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_scan_one_fallback` D-01 two-pass implementation: catch SSLCertVerificationError for chain_verified=False, else None | Architecture Patterns / Pitfall 1 | If wrong exception type used, chain_verified may be set incorrectly for network failures |
| A2 | scan_one() D-01 validation gate merges sslyze+fallback results (not a full re-run) | Code Examples | Planner may implement differently; confirm with D-01 wording |
| A3 | db.py uses `Base.metadata.create_all()` without migrations; new columns work on fresh DB only | CryptoEndpoint model gap section | If existing DB is reused between scans, chain_verified column may be absent at runtime |
| A4 | Port 13447 is free (only verified 13444-13446) | Port conflict section | Minor — pick any free port; planner should run netstat |
| A5 | `_chain_verified()` sentinel-object pattern is the right approach for backward-compat | Code Examples | Simpler approach (check column exists via hasattr) would also work |

---

## Open Questions

1. **Port assignment for tls-cert-defects profile**
   - What we know: 13443 conflicts with phaseA `tls-missing-intermediate`; 13444-13446 are free
   - What's unclear: Whether 13447 is free (not verified); whether D-03's proposed ports 13443-13446 should shift by 1
   - Recommendation: Planner uses 13444-13447 (shift by 1) or verifies 13447 free before finalizing

2. **db.py migration handling**
   - What we know: `CryptoEndpoint` has no `chain_verified` column today
   - What's unclear: Whether `db.py` calls `create_all()` (adds column on fresh DB only) or uses Alembic migrations
   - Recommendation: Planner reads `db.py` and determines if an `ALTER TABLE` migration step is needed for existing databases

3. **Severity of TLS-FIND-01 in existing tests**
   - What we know: `test_risk_engine.py:97` asserts HIGH for expired cert; requirement says CRITICAL
   - What's unclear: Whether the test was written before TLS-FIND-01 was spec'd as CRITICAL, or if the requirement changed
   - Recommendation: Change engine to CRITICAL per REQUIREMENTS.md; update the test

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | All scanner/engine code | ✓ | 3.14 (verified by test run) | — |
| openssl CLI | Cert generation scripts | ✓ | System OpenSSL 3.x | — |
| Docker Compose | Chaos lab profiles | ✓ | Running (13443 in LISTEN) | — |
| sslyze | Primary TLS scanner path | ✓ | 6.3.1 (from test mock) | Fallback path |
| cryptography library | Cert parsing | ✓ | 44+ (SHA1 conftest shim implies 45.x) | — |
| pytest | Test runner | ✓ | Passes 720+ tests | — |

[VERIFIED: test run output, netstat, conftest.py]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_tls_finding_gaps.py tests/test_risk_engine.py tests/test_sslyze_integration.py -x` |
| Full suite command | `pytest tests/ -m 'not slow'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TLS-FIND-01 | CRITICAL finding for expired cert | unit | `pytest tests/test_tls_finding_gaps.py::TestExpiredCert -x` | ❌ Wave 0 |
| TLS-FIND-02 | HIGH finding for self-signed cert | unit | `pytest tests/test_tls_finding_gaps.py::TestSelfSigned -x` | ❌ Wave 0 |
| TLS-FIND-03 | MEDIUM finding for untrusted-CA cert | unit | `pytest tests/test_tls_finding_gaps.py::TestUntrustedCA -x` | ❌ Wave 0 |
| TLS-FIND-04 | HIGH finding for RSA<2048 | unit | `pytest tests/test_risk_engine.py::TestQuantumVulnerableCertKey::test_rsa_1024_produces_high -x` | ✅ (exists but may need update) |
| TLS-FIND-05 | HIGH finding for EC<256 | unit | `pytest tests/test_risk_engine.py::TestQuantumVulnerableCertKey::test_ecdsa_192_produces_high -x` | ✅ (exists but may need update) |
| TLS-FIND-06 | Fallback fires when sslyze CERT_INFO returns ERROR + chain_verified set | unit | `pytest tests/test_tls_finding_gaps.py::TestChainVerifiedPlumbing -x` | ❌ Wave 0 |
| TLS-FIND-07 | tls-cert-defects profile services reachable | smoke/manual | `curl -k https://localhost:13444` | ❌ manual |
| D-04 exclusivity | Self-signed cert NEVER emits untrusted-CA finding | unit | `pytest tests/test_tls_finding_gaps.py::TestFindingExclusivity -x` | ❌ Wave 0 |
| D-01 validation gate | sslyze with CERT_INFO ERROR → chain_verified on ep | unit | `pytest tests/test_tls_finding_gaps.py::TestValidationGate -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_tls_finding_gaps.py tests/test_risk_engine.py tests/test_sslyze_integration.py -x`
- **Per wave merge:** `pytest tests/ -m 'not slow'` (baseline: 720 passed, 18 cbom-schema failures pre-existing)
- **Phase gate:** Full suite green (excluding pre-existing failures) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_tls_finding_gaps.py` — new test file covering TLS-FIND-01..06 + D-04 exclusivity
- Existing `tests/test_risk_engine.py` needs 4 severity assertion updates (not a new file)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | cert field getattr with defaults; no user-controlled input |
| V6 Cryptography | yes | SSL context: always CERT_REQUIRED for chain validation pass; never hand-roll CA bundle |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Self-signed cert accepted silently | Spoofing | chain_verified=False triggers finding; CERT_REQUIRED pass for chain check |
| Expired cert accepted | Tampering/Spoofing | cert_not_after < now triggers CRITICAL finding |
| RSA-1024 in TLS cert | Information Disclosure | cert_pubkey_size < 2048 triggers HIGH finding |

---

## Sources

### Primary (HIGH confidence)

- `quirk/scanner/tls_scanner.py` — inspected: lines 100-449; identified chain_verified gap at line 208
- `quirk/engine/risk_engine.py` — inspected: lines 136-146 (`_chain_verified`), 343-437 (finding branches), severity values
- `quirk/models.py` — full inspection; `chain_verified` column confirmed absent
- `quantum-chaos-enterprise-lab/docker-compose.yml` — port map and profile structure verified
- `quantum-chaos-enterprise-lab/lab.sh` — `_derive_all_profiles()` runtime derivation confirmed
- `quantum-chaos-enterprise-lab/scripts/gen_phaseA_certs.sh` — `issue_leaf` pattern verified
- `quantum-chaos-enterprise-lab/certs/scenarios/` — rsa1024/leaf.crt key size confirmed (1024 bit via openssl)
- `tests/test_risk_engine.py` — existing severity assertions mapped
- `tests/test_sslyze_integration.py` — existing test patterns reviewed

### Secondary (MEDIUM confidence)

- `netstat` port scan — confirmed 13443 in use, 13444-13446 free
- `pytest tests/ -m 'not slow'` run — 720 passed, 18 pre-existing failures (cbom-schema only)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; Phase 46 is wiring only
- Architecture: HIGH — source code verified at exact line numbers
- Pitfalls: HIGH — confirmed from code inspection (severity mismatch, port conflict, OpenSSL legacy.cnf requirement)
- Chaos lab structure: HIGH — filesystem and docker-compose inspected

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (stable codebase; main risk is port 13447 not checked)
