---
phase: 30-hashicorp-vault-connector
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - quirk/scanner/vault_connector.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/scoring.py
  - quirk/cbom/builder.py
  - quirk/config.py
  - quirk/config_template.yaml
  - pyproject.toml
  - run_scan.py
  - tests/test_vault_connector.py
  - tests/test_dar_vault_scoring.py
  - tests/conftest.py
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/vault/seed.sh
  - labs/vault/expected_results.md
  - docs/UAT-SERIES.md
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-04-26
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 30 adds a HashiCorp Vault connector (VAULT-01/02/03) scanning transit keys, PKI mounts,
and auth methods. The overall design is sound — sub-scanner isolation, graceful degradation when
`hvac` is absent, and the `dar_vault_weak_count` evidence counter and scoring weight are correctly
wired. The most significant finding is a CBOM algorithm registration bug: VAULT endpoints fall
through `build_cbom`'s Pass 1 `else` (TLS) branch, which constructs size-qualified names like
`"RSA-2048"` that `classify_algorithm` cannot resolve, producing `UNKNOWN` primitives. This
directly contradicts the D-14 spec requirement that transit keys be registered as algorithm
components. Three warnings involve the conftest SHA-1 shim silently masking failures, inconsistent
service_detail path casing between connector and expected-results doc, and a scan_error endpoint
that increments the global `scan_error_count` alongside `dar_vault_weak_count`, which can distort
scoring. The info items cover a dead comment thread, an unresolvable `key_size` in auth-method
endpoints, and a VAULT_ADDR double-check in `run_scan.py` that re-reads the env var after
`scan_vault_targets` itself handles the fallback.

---

## Warnings

### WR-01: VAULT endpoints fall through to TLS branch in CBOM Pass 1, producing UNKNOWN algorithm classification

**File:** `quirk/cbom/builder.py:415`

**Issue:** `build_cbom` Pass 1 has explicit `elif` branches for SSH, JWT, CONTAINER, SOURCE, AWS,
AZURE, GCP, CLOUD_SQL, DNSSEC, SAML, KERBEROS, and POSTGRESQL/MYSQL/RDS/S3/AZURE_BLOB/KUBERNETES,
but has no branch for `"VAULT"`. VAULT endpoints therefore fall through to the final `else` block
(the TLS path). For transit key endpoints that have `cert_pubkey_alg="RSA"` and
`cert_pubkey_size=2048`, the TLS branch builds a size-qualified name:

```python
pubkey_name = f"{ep.cert_pubkey_alg}-{ep.cert_pubkey_size}"  # -> "RSA-2048"
_register_algorithm(pubkey_name, algo_registry, key_size=key_size)
```

`classify_algorithm("RSA-2048")` lowercases to `"rsa-2048"`, which is not in `_ALGORITHM_TABLE`
(only `"rsa"` is present at line 95 of `classifier.py`). The fuzzy step does not help because
the hyphen is already present. The result is a CBOM component with
`CryptoPrimitive.UNKNOWN, nist_level=None, classical_level=None` — i.e., an unclassified entry.

This violates D-14: "RSA-2048 registered as algorithm component via Pass 1 (D-14 — transit keys
NOT skipped)" as stated in `labs/vault/expected_results.md`. The test suite does not cover CBOM
output for Vault endpoints, so this is undetected.

For auth-method endpoints (e.g., `cert_pubkey_alg="token"`, no `cert_pubkey_size`), the `else`
path also tries the cipher-suite decomposition on the empty `cipher_suite` field (no-op) and then
registers `"token"` as an algorithm name — which is also unclassifiable noise in the CBOM.

**Fix:** Add an explicit `elif ep.protocol == "VAULT":` branch in Pass 1, mirroring the KERBEROS
pattern. Register `cert_pubkey_alg` directly (without size qualification) only for transit key
and PKI endpoints; skip auth-method endpoints (which carry method type strings like "token" or
"userpass", not algorithm names):

```python
elif ep.protocol == "VAULT":
    # Transit keys and PKI CAs carry real algorithm names in cert_pubkey_alg.
    # Auth-method endpoints carry method-type strings (token, userpass) — skip.
    sd = str(getattr(ep, "service_detail", "") or "")
    if ep.cert_pubkey_alg and not sd.startswith("auth/"):
        _register_algorithm(
            ep.cert_pubkey_alg, algo_registry, key_size=ep.cert_pubkey_size
        )
```

---

### WR-02: conftest SHA-1 shim silently ignores OpenSSL errors, hiding test infrastructure failures

**File:** `tests/conftest.py:16-68`

**Issue:** `_patch_sha1_signing()` wraps the entire patching operation in a bare `except Exception`
that returns `False` on failure (line 67). When OpenSSL is unavailable, misconfigured, or the
`openssl req -sha1` command is blocked by system policy, the function silently returns `False`
and the patch is never applied. The test at line 71 then proceeds without patching, and
`test_pki_sha1_signed_ca_high_severity` will raise `cryptography.exceptions.UnsupportedAlgorithm`
at cert-generation time, producing a confusing failure rather than an explicit skip/error.

Additionally, the `subprocess.run` call at line 47 does not set a timeout. On a slow or
unresponsive system, the test suite can hang indefinitely.

**Fix:**

```python
def _patch_sha1_signing():
    try:
        ...
        result = subprocess.run(
            ["openssl", "req", ...],
            capture_output=True,
            timeout=15,   # prevent indefinite hang
        )
        ...
        return True
    except Exception as exc:
        import warnings
        warnings.warn(
            f"SHA-1 cert signing shim unavailable ({exc}); "
            "test_pki_sha1_signed_ca_high_severity will be skipped or fail.",
            stacklevel=1,
        )
        return False
```

If the patch is not applied, `test_pki_sha1_signed_ca_high_severity` should call
`pytest.skip("openssl SHA1 shim unavailable")` rather than letting it fail with an opaque
`UnsupportedAlgorithm` error.

---

### WR-03: scan_error Vault endpoints increment global scan_error_count, inflating scan_error_rate and distorting hygiene score

**File:** `quirk/intelligence/evidence.py:103-105`

**Issue:** `build_evidence_summary` increments `scan_error_count` for every endpoint where
`scan_error` is truthy (lines 103-105), regardless of protocol. This is correct behavior for
network endpoints. However, Vault scan-error endpoints (e.g., `vault-no-token`,
`vault-auth-failed`, `vault-client-init-failed`) are also counted. The `scan_error_rate` is then
used as a penalty in both the `hygiene` subscore (`hygiene_scan_error_rate` weight=6.0) and the
`modern_tls` subscore (`modern_tls_scan_error_rate` weight=5.0).

A misconfigured Vault (wrong token, sealed, unreachable) emits exactly one scan_error endpoint.
If the total endpoint count is small, this single Vault error can produce a non-trivial
`scan_error_rate` that penalises the TLS hygiene and modern_tls subscores — domains entirely
unrelated to Vault configuration. Prior phases with scan_error endpoints (e.g., PostgreSQL
`insufficient-privilege` at evidence.py line 158) have explicit guards to prevent this cross-
contamination; Vault does not.

The comment at evidence.py line 209 ("Per D-11: only HIGH … increments dar_vault_weak_count")
calls out the Vault-specific counting rule, but there is no corresponding guard for scan_error.

**Fix:** Add a protocol guard before the generic scan_error increment. The cleanest fix mirrors
the POSTGRESQL `insufficient-privilege` guard: when the protocol is VAULT and a scan_error is
present, do not increment `scan_error_count` (or introduce a separate `vault_scan_error_count`
that does not feed into `scan_error_rate`):

```python
scan_error = getattr(ep, "scan_error", None)
if scan_error:
    # VAULT scan errors (misconfigured token, sealed vault) are connector-layer
    # failures, not network scan failures. Do not inflate scan_error_rate.
    if proto != "VAULT":
        scan_error_count += 1
```

---

### WR-04: service_detail path casing inconsistency between connector output and expected_results doc for auth and PKI endpoints

**File:** `quirk/scanner/vault_connector.py:349-361` and `labs/vault/expected_results.md:47-51`

**Issue:** The expected_results table (lines 47-51 of `expected_results.md`) shows:

```
auth/token      (service_detail = "auth/token")
auth/userpass   (service_detail = "auth/userpass")
PKI/pki         (service_detail = "PKI/pki")
```

In the connector:
- `_scan_auth_methods` (line 354) builds `service_detail=f"auth/{path}"` where `path` comes
  directly from `list_auth_methods()` including the trailing slash (e.g., `"token/"`). So the
  actual `service_detail` value is `"auth/token/"` — with a trailing slash.
- The comment at lines 346-348 acknowledges this: "service_detail preserves the original path
  including trailing slash to match the expected format."

This means the expected_results doc is incorrect: it omits the trailing slash on all auth entries.
The test helper `_auth_endpoint(results, path)` in `test_vault_connector.py` line 369 searches
for `f"auth/{path}"` where path is passed as `"token/"` (with slash) by the test callers, so
tests pass. But the expected_results doc is misleading to operators and to future test writers.

Separately, PKI `service_detail` uses uppercase `"PKI/"` prefix while `host` uses lowercase
`"/pki/"` (lines 249/254). This is cosmetically inconsistent but not a bug since both fields
are documented.

**Fix:** Update `labs/vault/expected_results.md` table rows for auth entries to show the
trailing slash:

```
| http://localhost:28200/auth/token    | auth/token/    | HIGH   | token    |
| http://localhost:28200/auth/userpass | auth/userpass/ | MEDIUM | userpass |
```

---

## Info

### IN-01: vault_token stored in plain config field — no guidance in config_template.yaml on avoiding plaintext token in config files

**File:** `quirk/config_template.yaml:100-101`

**Issue:** The config template comments note `vault_token: null  # defaults to VAULT_TOKEN env
var` but does not warn operators against storing the token value in a plain YAML file that may
be committed to version control. Every other credential in the template (pg_scanner_password,
mysql_scanner_password) also lacks this warning, but the Vault token is higher-stakes: it grants
broad access to transit keys and PKI CAs.

**Fix:** Add a comment adjacent to the vault_token field:

```yaml
  # vault_token: null    # Prefer VAULT_TOKEN env var; never commit a real token to source control.
```

---

### IN-02: Auth-method endpoints have key_size=None in cert_key_type_counts, silently skipping RSA/ECDSA count increment

**File:** `quirk/intelligence/evidence.py:111-115`

**Issue:** Auth-method VAULT endpoints emit `cert_pubkey_alg` set to the method type string
(`"token"`, `"ldap"`, `"userpass"`). The evidence loop checks
`key_alg.startswith("RSA")` / `.startswith("ECDSA")` — these will not match method type strings,
so no cert_key_type_counts inflation occurs. This is the correct behaviour, but it is accidental:
if the connector ever changes to emit `cert_pubkey_alg="RSA"` for auth methods (it currently
does not), those would incorrectly be counted as RSA certificate keys.

The `VAULT` protocol is not guarded in the `cert_key_type_counts` section in the way that
POSTGRESQL/MYSQL/RDS/S3/KUBERNETES are guarded (those protocols are in the explicit `elif`
branches and reach the generic cert_key_type_counts code only after their explicit logic). VAULT
falls through to the generic `key_alg` check with no protocol guard. This is not currently a
bug but is fragile.

No fix required at this time; noting for awareness.

---

### IN-03: run_scan.py re-reads VAULT_ADDR env var redundantly — scan_vault_targets handles the fallback internally

**File:** `run_scan.py:675-686`

**Issue:** Lines 675-676 in `run_scan.py` check:

```python
elif not (cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR")):
    logger.v("vault_addr not set -- Vault scanning skipped")
```

And then line 679-682 passes:

```python
vault_addr=(cfg.connectors.vault_addr or os.environ.get("VAULT_ADDR", "")),
```

Inside `scan_vault_targets` (vault_connector.py line 406), `resolved_addr` already falls back
to `os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")` when `vault_addr` is empty. So
the `os.environ.get("VAULT_ADDR")` read in `run_scan.py` is partially redundant: the pre-check
prevents calling `scan_vault_targets` when neither config nor env provides an address, but
`scan_vault_targets` would handle the empty string case gracefully anyway (it would attempt to
connect to `"http://127.0.0.1:8200"` as the default).

The `os.environ` double-read is a minor consistency issue, not a functional bug. The pre-check
on line 675 is actually useful as a fast-path skip, so only the redundant `os.environ.get` in
the argument on line 681 is unnecessary if the caller intent is "use what the config says":

```python
# Cleaner: let the connector own the env-var fallback
vault_addr=cfg.connectors.vault_addr or "",
```

---

_Reviewed: 2026-04-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
