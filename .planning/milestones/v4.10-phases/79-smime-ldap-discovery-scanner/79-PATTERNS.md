# Phase 79: S/MIME LDAP Discovery Scanner — Pattern Map

**Mapped:** 2026-05-16
**Files analyzed:** 12 surfaces
**Analogs found:** 12 / 12

## Drift / Path Corrections Confirmed

| REQUIREMENTS-text path | Actual codebase path | Action |
|---|---|---|
| `quirk/scanners/` (plural, SMIME-01) | `quirk/scanner/` (singular — confirmed via `ls`) | Use **singular** `quirk/scanner/smime_scanner.py`. Already locked in 79-CONTEXT.md D-Path-Drift. |
| `quirk/db.py` "add column on `ScanSession`" | `class ScanSession` is a **Pydantic schema** at `quirk/dashboard/api/schemas.py:221`, **not** an SQLAlchemy ORM model. DB-level columns live in `_IDENTITY_COLUMNS` tuple (`quirk/db.py:76-80`) + `_ensure_columns` helper (`quirk/db.py:107`). | Append `("smime_scan_json", "TEXT")` to `_IDENTITY_COLUMNS`. **No ORM class edit.** |
| `IDENTITY_SKIP_PROTOCOLS` (CONTEXT D-Cross-cutting) | No constant by that name exists. Skip-list is **inline** in two locations in `quirk/cbom/builder.py`: line **528** (Pass-2 cert skip tuple) and line **610-614** (Pass-3 protocol-component skip tuple). | Two-site append of literal `"SMIME"` to both inline tuples. Optionally hoist to a named `IDENTITY_SKIP_PROTOCOLS` frozenset for parity with `DAR_SKIP_PROTOCOLS` (line 55) — but that is a refactor beyond Phase 79 scope; recommend leaving inline. |

No other naming mismatches detected across SMIME-01…08.

---

## File Classification

| Surface | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `quirk/scanner/smime_scanner.py` | scanner module | LDAP query → cert parse → finding emission | `quirk/scanner/saml_scanner.py` (cert parsing) + `quirk/scanner/kerberos_scanner.py` (ldap3/identity-extras gating) | exact (composite) |
| `quirk/db.py` (+smime_scan_json) | ORM additive column | schema migration | `_IDENTITY_COLUMNS` tuple at `quirk/db.py:76-80` | exact |
| `quirk/intelligence/scoring.py` (+3 weights) | scoring config | constant additions | `SCORE_WEIGHTS` entries at `scoring.py:29-31` | exact |
| `quirk/intelligence/evidence.py` (+3 counters) | evidence aggregator | counter accumulator | `saml_weak_signing_count` accumulator block at `evidence.py:88, 160-166, 340` | exact |
| `quirk/cbom/builder.py` (Pass-1 emit + skip-list) | CBOM Pass-1 | algorithm registration | `elif ep.protocol == "SAML"` at `builder.py:449-452` | exact |
| `tests/test_smime_scanner.py` | unit test | scanner output assertions | (existing pattern — `tests/test_saml_scanner.py`) | role-match |
| `tests/test_smime_no_envelope_leak.py` | privacy invariant test | content absence | (no exact analog — new pattern; closest privacy test is the AST gate below) | role-match |
| `tests/test_smime_ast_gate.py` | AST CI gate | static analysis | `tests/test_scan_error_gate.py` | exact |
| `quantum-chaos-enterprise-lab/docker-compose.yml` (smime profile) | compose service block | container + seed | `ldaps:` block at `docker-compose.yml:741-758` | exact |
| `quantum-chaos-enterprise-lab/smime/` | chaos lab subdir | LDIF + certs fixtures | `quantum-chaos-enterprise-lab/samba/` (build context) + `simplesamlphp/cert/` (cert fixtures) | role-match |
| `quantum-chaos-enterprise-lab/expected_results_v4.md` (smime section) | oracle | profile reference | `## Profile: ldaps` at `expected_results_v4.md:251-272` | exact |
| `pyproject.toml` | manifest | (no edit) | `[identity]` extras already include ldap3 — confirmed | n/a |

---

## Pattern Assignments

### `quirk/scanner/smime_scanner.py` (NEW scanner)

**Primary analog:** `quirk/scanner/saml_scanner.py` (cert parsing + finding emission)
**Secondary analog:** `quirk/scanner/kerberos_scanner.py` (impacket/ldap3 try-import gate; module-level logger)

**Copy — module-level optional-import gate** (`kerberos_scanner.py:3-14`):
```python
try:
    from ldap3 import Server, Connection, SUBTREE, ALL
    LDAP3_AVAILABLE = True
except ImportError:
    LDAP3_AVAILABLE = False
```
Pattern: scanner returns `[]` early if the gate is False, logger emits WARNING. Mirror exactly — `[identity]` extras supply `ldap3` from Phase 25.

**Copy — module-level logger** (`saml_scanner.py:30-31`, `kerberos_scanner.py:29-30`):
```python
logger = logging.getLogger(__name__)
```

**Copy — DER X.509 parse → key alg/bits extraction** (`saml_scanner.py:149-180`, `_parse_cert_element`):
```python
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec
# ...
cert = load_der_x509_certificate(der)
pub = cert.public_key()
if isinstance(pub, rsa.RSAPublicKey):
    key_alg = "RSA"; key_bits = pub.key_size
elif isinstance(pub, ec.EllipticCurvePublicKey):
    key_alg = "ECDSA"; key_bits = pub.key_size
# ... returns dict(key_alg, key_bits, serial, not_after)
```
**Adapt:** LDAP returns raw DER bytes directly (no base64 strip needed — that is a SAML XML-text artifact). Skip the `cleaned = ...replace(...)` lines. DER-first per CONTEXT D-Area-2; PEM fallback only on parse exception.

**Copy — severity classifier** (`saml_scanner.py:195-214`, `_classify_key_severity`):
```python
def _classify_key_severity(key_alg, key_bits):
    if alg_upper == "RSA":
        if key_bits is None: return "HIGH"
        if key_bits < 2048: return "CRITICAL"
        return "HIGH"
    return None  # ECDSA/EdDSA SAFE
```
**Adapt:** SMIME-02 mandates reuse of `quirk/util/weak_crypto.py::is_weak_cipher` for the signing-algorithm leg (e.g. SHA-1 / MD5 signature). Call signature: `is_weak_cipher(cert.signature_hash_algorithm.name)`. Key-size leg stays per-scanner like SAML does.

**Copy — endpoint emission shape** (`saml_scanner.py:279-290`):
```python
ep = CryptoEndpoint(
    host=host, port=port, protocol="SMIME",
    cert_pubkey_alg=key_alg, cert_pubkey_size=key_bits,
    service_detail=f"{user_dn}|attr=userSMIMECertificate|serial={serial}",
    severity=...,
    smime_scan_json=json.dumps(scan_dict),
    scanned_at=now,
)
```
**Adapt:** `protocol="SMIME"` (uppercase, per CONTEXT D-Area-4); `service_detail` encodes user DN + which attribute (`userCertificate` vs `userSMIMECertificate`) + cert serial; new `smime_scan_json` kwarg requires the corresponding `CryptoEndpoint` field (verify in `quirk/models.py`).

**Copy — top-level entry signature** (`saml_scanner.py:437-443`, `scan_saml_targets`):
```python
def scan_smime_targets(targets, timeout=10, logger=None, session_start=None, *, search_base=None):
```
Same shape as `scan_saml_targets`; add `search_base` kwarg per CONTEXT D-Area-1 (defaults to None → derive from Kerberos realm).

**LDAP enumeration pattern** (no exact in-repo analog — kerberos_scanner uses raw KDC TCP, not ldap3 queries). Per CONTEXT D-Area-1:
- `Server(host, port=port, use_ssl=True, get_info=ALL)`
- `Connection(server, ..., auto_bind=True)`
- `conn.extend.standard.paged_search(search_base=base, search_filter='(|(userCertificate=*)(userSMIMECertificate=*))', search_scope=SUBTREE, attributes=['userCertificate', 'userSMIMECertificate'], paged_size=500)`
- Iterate ALL values in each multi-valued attribute (D-Area-1).

**Do differently vs SAML scanner:**
- No httpx, no URL allowlist (LDAP is intranet by design — no SSRF surface).
- No XML parsing — pure binary DER input.
- **No IMAP / mailbox / envelope code path** (locked privacy invariant, enforced by SMIME-08 AST gate).

---

### `quirk/db.py` — additive `smime_scan_json` column

**Analog:** `quirk/db.py:77-80` `_IDENTITY_COLUMNS` tuple.

**Copy verbatim shape:**
```python
_IDENTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("kerberos_scan_json", "TEXT"),
    ("saml_scan_json",     "TEXT"),
    ("dnssec_scan_json",   "TEXT"),
    ("smime_scan_json",    "TEXT"),  # Phase 79 SMIME-03
)
```
**Adapt:** add one line. The `_ensure_columns` helper at `db.py:107` handles the migration automatically — no further DB code edit. Phase 77 D-21 consolidated the per-feature `_ensure_*` helpers, so do **not** re-introduce a `_ensure_smime_columns` function. The `_SAFE_COL_RE` / `_SAFE_COL_TYPE_RE` regex already accepts the column name + DDL pair.

**Do not touch:** `quirk/dashboard/api/schemas.py::ScanSession` (Pydantic) unless API-layer surface needs the field — that is dashboard wiring, separate plan.

---

### `quirk/intelligence/scoring.py` — 3 new `SCORE_WEIGHTS` entries

**Analog:** existing identity-block entries at `scoring.py:29-31`.

**Existing block (verbatim):**
```python
"identity_kerberos_weak_etype_ratio": 10.0,
"identity_saml_weak_signing_ratio":   8.0,
"identity_dnssec_weak_algo_ratio":    8.0,
```

**Add (per CONTEXT D-Area-4 — weight 2.0 each):**
```python
"identity_smime_weak_signing_count": 2.0,   # Phase 79 SMIME
"identity_smime_expired_count":      2.0,   # Phase 79 SMIME
"identity_smime_weak_key_count":     2.0,   # Phase 79 SMIME
```

**Wire into `identity_trust_impacts` list** at `scoring.py:175-184` — append three rows mirroring `scoring.py:181`:
```python
("Weak S/MIME signing", -_ratio(smime_weak_signing_count, denom) * w["identity_smime_weak_signing_count"]),
("Expired S/MIME cert", -_ratio(smime_expired_count, denom) * w["identity_smime_expired_count"]),
("Weak S/MIME key",     -_ratio(smime_weak_key_count, denom) * w["identity_smime_weak_key_count"]),
```
And add three `max(0, _as_int(evidence.get("smime_*_count", 0)))` extractions mirroring `scoring.py:150-152`.

**Naming drift to flag:** CONTEXT D-Area-4 names the keys `identity_smime_*_count` (suffix `_count`), but every other SCORE_WEIGHTS entry uses `_ratio` (`identity_saml_weak_signing_ratio`). Recommend `_count` per CONTEXT decision — it is locked. Note for planner: the **impact-list label** stays `_count` but the math at `_ratio(num, denom) * w["..._count"]` is unchanged from the existing pattern; the suffix is purely a naming convention. Either is fine; **honor CONTEXT**.

**MUST NOT touch:** `tests/test_score_weights_invariant.py` — owned by Phase 83 per CONTEXT D-Area-4 (CLEAN-01).

---

### `quirk/intelligence/evidence.py` — 3 new counters

**Analog block:** `saml_weak_signing_count` lifecycle at `evidence.py:88` (declaration), `160-166` (accumulate inside `proto == "SAML"` branch), `340` (export to dict).

**Mirror exactly — three steps:**

1. Declare zero-init at `evidence.py:~89-90` (next to `saml_weak_signing_count`):
```python
smime_weak_signing_count = 0
smime_expired_count = 0
smime_weak_key_count = 0
```

2. Add `elif proto == "SMIME":` branch after the DNSSEC branch (`evidence.py:~177`). Pattern from SAML block (160-166):
```python
elif proto == "SMIME":
    _smime_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()
    _smime_size = getattr(ep, "cert_pubkey_size", None)
    _smime_detail = str(getattr(ep, "service_detail", "") or "")
    if is_weak_cipher(_smime_alg):
        smime_weak_signing_count += 1
    if _smime_size is not None and isinstance(_smime_size, int) and _smime_size < 2048:
        smime_weak_key_count += 1
    if "expired" in _smime_detail.lower():   # or check ep.severity tag
        smime_expired_count += 1
```
**Adapt:** the expiry signal needs a stable encoding in `service_detail` (scanner contract — recommend `|expired=true`). Confirm contract in scanner plan.

3. Export at `evidence.py:~339-340`:
```python
"smime_weak_signing_count": smime_weak_signing_count,
"smime_expired_count":      smime_expired_count,
"smime_weak_key_count":     smime_weak_key_count,
```

---

### `quirk/cbom/builder.py` — Pass-1 emit + skip-list append

**Analog:** `elif ep.protocol == "SAML":` block at `builder.py:449-452`.

**Copy verbatim shape** (insert immediately after SAML branch ~line 453):
```python
elif ep.protocol == "SMIME":
    # SMIME: cert_pubkey_alg holds algorithm name (RSA, ECDSA) from userCertificate
    # / userSMIMECertificate. Pass-1 only — Pass-2/3 skipped (see IDENTITY_SKIP).
    if ep.cert_pubkey_alg:
        _register_algorithm(ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size)
```

**Skip-list append — TWO sites** (no named `IDENTITY_SKIP_PROTOCOLS` constant exists; both are inline tuples):

Site 1 — Pass-2 cert-component skip (`builder.py:528`):
```python
"SSH", "CONTAINER", "SOURCE", "KERBEROS", "SAML", "DNSSEC", "SMIME",
```

Site 2 — Pass-3 protocol-component skip (`builder.py:610-614`):
```python
elif ep.protocol in (
    "JWT", "CONTAINER", "SOURCE", "AWS", "AZURE",
    "DNSSEC", "SAML", "KERBEROS", "SMIME",
    *DAR_SKIP_PROTOCOLS,
    *MOTION_PLAINTEXT_PROTOCOLS,
):
```

**Optional cleanup (recommend deferring):** hoist both inline tuples to a module-level `IDENTITY_SKIP_PROTOCOLS = frozenset({"KERBEROS","SAML","DNSSEC","SMIME"})` next to `DAR_SKIP_PROTOCOLS` (line 55). Phase 79 scope is additive — leave the refactor for a future cleanup phase.

---

### `tests/test_smime_scanner.py` (NEW unit test)

**Analog:** any existing `tests/test_*_scanner.py` (e.g. `tests/test_saml_scanner.py`).

**Pattern to mirror:**
- Mock `ldap3.Server` and `ldap3.Connection` with `unittest.mock.patch`.
- Feed `_parse_cert_*` helper(s) DER bytes from `tests/fixtures/smime/*.der` (commit static fixtures).
- Assert: returns list of `CryptoEndpoint`, each with `protocol="SMIME"`, correct severity, `smime_scan_json` populated.
- Cover the three cert profiles (RSA-1024 SHA-1, RSA-1024 SHA-256, RSA-2048 SHA-256) per CONTEXT D-Area-3.

---

### `tests/test_smime_no_envelope_leak.py` (NEW — SMIME-04 privacy invariant)

**No exact analog in repo.** Closest privacy-style assertion is the AST gate (test_scan_error_gate.py). New pattern.

**Recommended shape:**
```python
def test_no_imap_envelope_fields_in_smime_output():
    # Construct a target object decorated with To/From/Subject sentinel strings
    target = SimpleNamespace(
        host="ldap.example.com",
        to="SENTINEL_TO_FIELD",
        from_="SENTINEL_FROM_FIELD",
        subject="SENTINEL_SUBJECT_FIELD",
    )
    endpoints = scan_smime_targets([target], ...)  # with mocked ldap3
    blob = json.dumps([ep.__dict__ for ep in endpoints])
    for sentinel in ("SENTINEL_TO_FIELD", "SENTINEL_FROM_FIELD", "SENTINEL_SUBJECT_FIELD"):
        assert sentinel not in blob, f"Envelope field leaked: {sentinel}"
```

---

### `tests/test_smime_ast_gate.py` (NEW — SMIME-08)

**Analog:** `tests/test_scan_error_gate.py:1-80` (entire file is the cleanest AST-walker template in the suite).

**Copy structure verbatim:**
```python
import ast, pathlib, pytest
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = PROJECT_ROOT / "quirk" / "scanner" / "smime_scanner.py"

FORBIDDEN_IMPORTS = {"imaplib", "poplib", "smtplib"}
FORBIDDEN_FROM_PREFIXES = ("email.",)
FORBIDDEN_FROM_MODULES = {"email"}

def test_smime_scanner_no_imap_or_envelope_imports():
    tree = ast.parse(TARGET.read_text())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORTS or alias.name in FORBIDDEN_FROM_MODULES:
                    violations.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in FORBIDDEN_FROM_MODULES or mod in FORBIDDEN_IMPORTS \
               or any(mod.startswith(p) for p in FORBIDDEN_FROM_PREFIXES):
                violations.append(f"from {mod} import ...")
    assert not violations, f"SMIME-08 violation — IMAP/envelope imports: {violations}"
```

**Adapt vs scan_error_gate:** simpler — single target file, single rule (import-presence). No SAFE/VIOLATION predicates needed.

---

### `quantum-chaos-enterprise-lab/docker-compose.yml` — `smime` profile

**Analog:** `ldaps:` block at `docker-compose.yml:741-758`.

**Copy structure** (adapt ports, env, profile name, add seed sidecar):
```yaml
  # =========================
  # PHASE 79 — SMIME LDAP DISCOVERY (profile: smime)
  # =========================
  smime-openldap:
    image: bitnamilegacy/openldap:2.6.10-debian-12-r4  # parity w/ ldaps (CONTEXT D-Area-3 says osixia 1.5.0 but ldaps already migrated 2026-05-15 for macOS — recommend bitnamilegacy)
    profiles: ["smime"]
    environment:
      LDAP_ROOT: "dc=quirk,dc=lab"
      LDAP_ADMIN_USERNAME: "admin"
      LDAP_ADMIN_PASSWORD: "admin"
      LDAP_PORT_NUMBER: 389
      LDAP_LDAPS_PORT_NUMBER: 636
      LDAP_ENABLE_TLS: "yes"
      LDAP_TLS_CERT_FILE: /opt/bitnami/openldap/certs/modern.crt
      LDAP_TLS_KEY_FILE:  /opt/bitnami/openldap/certs/modern.key
      LDAP_TLS_CA_FILE:   /opt/bitnami/openldap/certs/ca.crt
    volumes:
      - ./certs:/opt/bitnami/openldap/certs:ro
      - ./smime/ldif:/ldif:ro
      - ./smime/certs:/smime-certs:ro
    ports:
      - "38900:389"
      - "38901:636"
    restart: unless-stopped

  smime-seed:
    image: bitnamilegacy/openldap:2.6.10-debian-12-r4
    profiles: ["smime"]
    depends_on:
      smime-openldap:
        condition: service_started
    entrypoint: ["/bin/sh", "-c"]
    command: ["sleep 5 && ldapadd -x -H ldap://smime-openldap:389 -D 'cn=admin,dc=quirk,dc=lab' -w admin -f /ldif/users.ldif || true"]
    volumes:
      - ./smime/ldif:/ldif:ro
    restart: "no"
```

**Drift flag:** CONTEXT D-Area-3 pins `osixia/openldap:1.5.0`. The repo's `ldaps` profile **already migrated off osixia** to `bitnamilegacy/openldap:2.6.10` on 2026-05-15 (see `expected_results_v4.md:253` note) due to macOS bind-mount incompatibility. Planner should reconcile — either honor CONTEXT (osixia, may break macOS dev) or follow the ldaps precedent (bitnamilegacy). **Recommend bitnamilegacy; flag for user.**

**Idempotent seeding (CHAOS-04):** the `|| true` on `ldapadd` makes re-runs non-fatal when entries already exist. Mirrors the existing seeding contract.

---

### `quantum-chaos-enterprise-lab/smime/` (NEW subdir)

**Layout** (composite of `samba/` build context + `simplesamlphp/cert/` static cert pattern):
```
quantum-chaos-enterprise-lab/smime/
├── ldif/
│   └── users.ldif       # alice (RSA-1024+SHA1), bob (RSA-1024+SHA256), carol (RSA-2048+SHA256)
└── certs/
    ├── alice.der        # RSA-1024 SHA-1   — HIGH (weak sig + weak key)
    ├── bob.der          # RSA-1024 SHA-256 — HIGH (weak key only)
    └── carol.der        # RSA-2048 SHA-256 — SAFE
```

LDIF format — each user gets `userSMIMECertificate:: <base64-DER>` per RFC 4523.

---

### `quantum-chaos-enterprise-lab/expected_results_v4.md` — new `## Profile: smime` section

**Analog:** `## Profile: ldaps` at `expected_results_v4.md:251-272`, structurally combined with `## Profile: saml` at `:302-323` (which has a findings table per cert).

**Section to add** (modeled on the saml section):
```markdown
## Profile: smime

*OpenLDAP seeded with three users carrying userSMIMECertificate values exercising weak-signing, weak-key, and SAFE paths. LDAP on 38900, LDAPS on 38901.*

```bash
PROFILE_ARGS="--profile smime" ./lab.sh up
```

| User DN | Certificate | Expected Finding | Severity |
|---|---|---|---|
| uid=alice,ou=people,dc=quirk,dc=lab | RSA-1024 / SHA-1   | Weak S/MIME signing + weak key | HIGH |
| uid=bob,ou=people,dc=quirk,dc=lab   | RSA-1024 / SHA-256 | Weak S/MIME key (RSA-1024)     | HIGH |
| uid=carol,ou=people,dc=quirk,dc=lab | RSA-2048 / SHA-256 | (none — SAFE)                  | —    |

**Scanner validation command:**
```
docker compose --profile smime up -d && sleep 10 && quirk scan --smime-target ldap://localhost:38900 --smime-base dc=quirk,dc=lab
```
**Expected:** SMIME scanner returns 2 HIGH findings (alice, bob). Findings appear in the Identity tab (source="smime"). No IMAP traffic, no mailbox access. Idempotent — re-running `./lab.sh up` must not produce duplicate ldif entries.

**Ports:** 38900/tcp (LDAP), 38901/tcp (LDAPS) — chosen to avoid 636 (ldaps profile) and 389 (kerberos/samba-dc profile).
```

---

### `pyproject.toml` — no edit needed

`ldap3` already in `[identity]` extras from Phase 25. CONTEXT confirms. **No change.**

---

## Shared Patterns

### Module-level logger
**Source:** `quirk/scanner/saml_scanner.py:30-31`, `quirk/scanner/kerberos_scanner.py:29-30`
**Apply to:** `quirk/scanner/smime_scanner.py`
```python
import logging
logger = logging.getLogger(__name__)
```

### Optional-dependency import gate
**Source:** `quirk/scanner/kerberos_scanner.py:3-14`
**Apply to:** `quirk/scanner/smime_scanner.py` — `ldap3` is in `[identity]` extras, not a hard dep.

### CryptoEndpoint emission contract
**Source:** `quirk/scanner/saml_scanner.py:279-290`
**Apply to:** every finding the SMIME scanner emits. `protocol="SMIME"`, `service_detail` encodes user DN + attribute + serial + (optional) `|expired=true` sentinel for evidence.py to read.

### `safe_str()` on `scan_error` writes (Phase 59 LEAK-03)
**Source:** `tests/test_scan_error_gate.py`
**Apply to:** any `scan_error=...` assignment in `smime_scanner.py` must wrap exception messages in `safe_str(exc)` or the existing AST gate (test_scan_error_gate.py) will fail. This gate already covers `quirk/scanner/` recursively — no new test needed for this dimension.

---

## No Analog Found

| File | Reason |
|---|---|
| `tests/test_smime_no_envelope_leak.py` | No prior content-absence privacy test exists; SMIME-04 is a new test pattern. Template above. |

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/cbom/`, `quirk/intelligence/`, `quirk/util/`, `tests/`, `quantum-chaos-enterprise-lab/`.
**Files scanned:** ~25 files inspected; 7 read in detail (saml_scanner.py full, kerberos_scanner.py head, db.py columns block, scoring.py head + impact block, evidence.py grep, cbom/builder.py three sections, docker-compose.yml ldaps block, expected_results_v4.md ldaps+saml sections, test_scan_error_gate.py head).
**Pattern extraction date:** 2026-05-16
