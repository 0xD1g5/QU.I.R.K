---
phase: 57-scanner-security-hardening
reviewed: 2026-05-09T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - quirk/scanner/broker_scanner.py
  - quirk/scanner/jwt_scanner.py
  - quirk/scanner/saml_scanner.py
  - quirk/scanner/source_scanner.py
  - quirk/util/subprocess_input.py
  - quirk/util/url_allowlist.py
  - run_scan.py
  - tests/scanner/test_broker_hardening.py
  - tests/scanner/test_container_hardening.py
  - tests/scanner/test_jwt_hardening.py
  - tests/scanner/test_phase57_invariants.py
  - tests/scanner/test_saml_hardening.py
  - tests/scanner/test_source_hardening.py
  - tests/test_source_scanner.py
  - tests/util/test_subprocess_input.py
  - tests/util/test_url_allowlist.py
findings:
  critical: 3
  warning: 6
  info: 4
  total: 13
status: issues_found
---

# Phase 57: Code Review Report

**Reviewed:** 2026-05-09
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 57 introduces a security-hardening layer across five scanners: JWT/JWKS TLS
verification, semgrep argv-injection guard, Syft/Trivy argv-injection guard, SAML SSRF
allowlist, and broker management-API cleartext gate. The design intent is sound — each
opt-out path is behind a boolean flag that defaults to the safe value, and every
opt-in emits an audit advisory. The utility modules (`subprocess_input.py`,
`url_allowlist.py`) are well-structured and independently testable.

Three blockers were found:

1. **`url_allowlist.py` does not resolve hostnames**, leaving a DNS-rebinding/alias
   gap: any RFC1918 address reachable under a public-looking domain name bypasses all
   IP-class checks. The docstring acknowledges this but the advisory check in
   `scan_saml_targets` also relies on the same function to decide whether to emit the
   HIGH advisory — so internal-hostname targets quietly bypass advisory emission as well
   as the block.

2. **`_enrich_redis_config` ignores `allow_cleartext`** in the Redis enrichment path
   called from `scan_one_redis`, passing the hardcoded default (`allow_cleartext=False`)
   regardless of the operator's security config. The `cfg.security` object is never
   threaded to `scan_one_redis` → `_enrich_redis_config`, so the cleartext-gate
   advertised in the docstring is permanently locked to `ssl_cert_reqs="required"`,
   preventing legitimate opt-in probes even when the operator explicitly sets
   `allow_cleartext_broker_probe=True`.

3. **`_fetch_jwks` follows a JWKS redirect URI from the OIDC discovery document
   without validating that URI against any allowlist.** An attacker controlling the
   OIDC discovery document can redirect JWKS fetches to `http://169.254.169.254/...`
   or any other target. The SAML scanner explicitly adds `validate_external_url` before
   every fetch; the JWT scanner has no equivalent check.

---

## Critical Issues

### CR-01: DNS-rebinding gap in url_allowlist — hostname targets bypass all IP-class checks

**File:** `quirk/util/url_allowlist.py:129-131`

**Issue:** The validator resolves only literal IP-address strings via `ipaddress.ip_address(host)`. When `host` is a domain name the function immediately returns `ok=True` with no DNS lookup. This means `http://internal.corp/saml` resolves the RFC1918 IP at runtime, bypassing both the block (CR-04) and — more critically — the advisory emission path in `scan_saml_targets` (lines 437–448). An operator who configures a hostname alias for a cloud-metadata-service or internal-only IdP gets neither a block nor an audit trail.

The docstring explicitly notes "no DNS resolution per threat model" but the threat model residual is not surfaced to the user anywhere, and the advisory logic in `scan_saml_targets` silently gives a false "not internal" result for hostname targets.

**Fix:** Emit a WARNING-level log whenever a SAML or broker target is a non-IP hostname, so the omission is visible in scan output. Alternatively, resolve the hostname to an IP before passing it to `validate_external_url` in `_fetch_metadata`. If DNS resolution is ruled out by design, the advisory logic in `scan_saml_targets` must call `validate_external_url` with the **resolved** IP, not the original URL:

```python
# In _fetch_metadata / scan_saml_targets: document residual risk in output
import socket, logging
try:
    resolved_ip = socket.gethostbyname(parsed.hostname)
    advisory_result = validate_external_url(
        f"{parsed.scheme}://{resolved_ip}/", allow_internal=False
    )
    if not advisory_result.ok:
        # emit advisory for the resolved-IP finding
        ...
except socket.gaierror:
    pass  # DNS failure — proceed; target unreachable anyway
```

---

### CR-02: `allow_cleartext` flag not propagated to `_enrich_redis_config` from `scan_one_redis`

**File:** `quirk/scanner/broker_scanner.py:770`

**Issue:** `scan_one_redis` calls `_enrich_redis_config(host, port, logger)` without passing `allow_cleartext`. The function signature defaults `allow_cleartext=False`, so Redis enrichment always uses `ssl_cert_reqs="required"` regardless of `cfg.security.allow_cleartext_broker_probe`. The `security` object is not threaded into `scan_one_redis` or `scan_redis_targets` at all.

This has two effects:
- Operators who set `allow_cleartext_broker_probe=True` cannot actually probe Redis with degraded TLS (the intended opt-in path from CR-06 is silently ignored).
- The `test_redis_cleartext_optin_uses_none` test passes because it calls `_enrich_redis_config` directly, not through the full `scan_one_redis` → `scan_redis_targets` call chain — the integration path is untested and broken.

**Fix:**
```python
# scan_one_redis: add allow_cleartext parameter
def scan_one_redis(
    host: str,
    port: int,
    timeout: int,
    logger: Optional[Logger] = None,
    session_start: Optional[datetime] = None,
    *,
    allow_cleartext: bool = False,   # ADD THIS
) -> Optional[CryptoEndpoint]:
    ...
    enrichment = _enrich_redis_config(host, port, logger, allow_cleartext=allow_cleartext)

# scan_redis_targets: accept and propagate security=None
def scan_redis_targets(..., *, security=None) -> List[CryptoEndpoint]:
    allow_cleartext = bool(security and getattr(security, "allow_cleartext_broker_probe", False))
    ...
    # In the ThreadPoolExecutor submit:
    ex.submit(scan_one_redis, h, p, timeout, logger, session_start, allow_cleartext=allow_cleartext)
```

---

### CR-03: JWKS redirect URI not validated against SSRF allowlist

**File:** `quirk/scanner/jwt_scanner.py:83-87`

**Issue:** When the OIDC discovery path (`.well-known/openid-configuration`) is followed, `_fetch_jwks` extracts `jwks_uri` from the discovery document and immediately fetches it without any URL validation:

```python
jwks_uri = data.get("jwks_uri")
...
resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=verify_tls)
```

A server-side compromise or a misconfigured IdP discovery document can set `jwks_uri` to any URL — including `http://169.254.169.254/latest/meta-data/iam/security-credentials/...`. With `allow_insecure_jwks=True` and `verify_tls=False`, the entire cloud metadata credential-theft chain is open. Even with `verify_tls=True` the redirect to an internal IP succeeds because TLS verification only checks certificate trust, not destination IP class.

The SAML scanner (`saml_scanner.py:82`) shows the correct pattern: call `validate_external_url` before every outbound fetch.

**Fix:**
```python
from quirk.util.url_allowlist import validate_external_url

# In _fetch_jwks, before fetching jwks_uri:
if not jwks_uri:
    continue
_vr = validate_external_url(jwks_uri)
if not _vr.ok:
    # blocked redirect target — skip silently or log
    continue
fetched_urls.append(jwks_uri)
resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=verify_tls)
```

---

## Warnings

### WR-01: `validate_repo_path` accepts symlinks pointing outside accepted root

**File:** `quirk/util/subprocess_input.py:129`

**Issue:** `os.path.isdir(p)` returns `True` for a symlink to a directory. A path like `/tmp/safe_name` that is a symlink to `/etc/shadow.d/` passes all checks: no metacharacters, no `..`, exists, is a directory. The path traversal guard only rejects literal `..` in the string, not resolved traversal through symlinks.

**Fix:** Replace `os.path.isdir(p)` with a check that also resolves the real path and optionally validates it stays within an expected root, or at minimum use `os.path.realpath(p)` and re-run the `..` check on the resolved path:

```python
real = os.path.realpath(p)
if ".." in real:  # should not happen after realpath, but guard anyway
    return ValidationResult(False, RC_PATH_TRAVERSAL, _redact_preview(p))
if not os.path.isdir(real):
    return ValidationResult(False, RC_NONEXISTENT_PATH, _redact_preview(p))
```

---

### WR-02: `_enrich_rabbitmq_mgmt` emits advisory even when no HTTP request was made

**File:** `quirk/scanner/broker_scanner.py:611-618`

**Issue:** The cleartext advisory is emitted for every host when `allow_cleartext=True`, unconditionally, before confirming whether the HTTP request to the management API actually succeeded or even completed. If the `urlopen` call raises an exception (connection refused, timeout), `_enrich_rabbitmq_mgmt` returns `{}` — and the scan still emits an advisory for a probe that silently failed. The advisory is supposed to document "cleartext probe was sent", but it fires even when `mgmt == {}` from a failed connection.

**Fix:** Move the advisory emission inside the `if mgmt:` block, or return a distinct sentinel from `_enrich_rabbitmq_mgmt` that distinguishes "probe attempted" from "probe succeeded":

```python
# In scan_rabbitmq_targets:
# Only emit cleartext advisory when the probe was actually attempted
mgmt_attempted = allow_cleartext  # _enrich_rabbitmq_mgmt always attempts when allow_cleartext
if allow_cleartext:
    results.append(CryptoEndpoint(..., service_detail=ADVISORY_BROKER_CLEARTEXT, ...))
```

Actually the current code IS correct in logging the advisory for the attempt (not the result), but the docstring says "when HTTP probe is sent" — the comment on line 613 says "one per host when HTTP probe is sent". The `_enrich_rabbitmq_mgmt` function does always send the request when `allow_cleartext=True`, so semantically the advisory is correct. However: the advisory is emitted even for hosts where the urlopen raised an exception before any bytes were sent (e.g., DNS failure, connection refused before send). This is a minor misclassification — the advisory is better understood as "HTTP probe was attempted", which aligns with the actual behavior.

The real fix is to clarify the docstring/comment and acknowledge this edge case in the advisory `service_detail` string.

---

### WR-03: `_classify_target` uses weak content-sniffing with no error for binary content

**File:** `quirk/scanner/saml_scanner.py:109-113`

**Issue:** `_classify_target` falls through to `return "saml"` for any content that fails `json.loads`. Binary content, gzip-compressed responses, redirected HTML login pages, and anything else non-JSON and non-XML all silently route to the SAML XML parser. `_safe_ET_fromstring` will then throw on invalid XML, which is caught by the `except Exception` in `scan_saml_targets` (line 462) and logged as a warning — but the warning message says "metadata parse failed" not "content type unknown", potentially confusing operators during diagnostics.

**Fix:** Add a content-type sniff before the XML parse attempt:
```python
def _classify_target(url: str, content: bytes) -> str:
    if ".well-known" in url:
        return "oidc"
    try:
        json.loads(content)
        return "oidc"
    except Exception:
        pass
    # Sniff for XML prologue / SAML root element
    stripped = content.lstrip()
    if stripped.startswith(b"<") or stripped.startswith(b"<?xml"):
        return "saml"
    return "unknown"  # NEW: caller should skip with a distinct warning
```

---

### WR-04: `_strip_comments` in `test_phase57_invariants.py` is fragile — strips comment-like content inside string literals

**File:** `tests/scanner/test_phase57_invariants.py:20-28`

**Issue:** The `_strip_comments` helper splits every line on `#` and discards everything after the first `#`. Python string literals containing `#` (e.g., `"#RRGGBB"` color codes, regex patterns like `r"[#;|]"`, or test fixture strings) will be incorrectly truncated, causing the invariant tests to produce false-negatives (the stripped source no longer contains the forbidden pattern even though the real source does).

This specifically matters for `test_no_unconditional_verify_false`: if a future commit adds a comment like `# verify=False is rejected here`, the stripped line becomes `` (empty) and the test would erroneously pass even if `verify=False` appeared in a string context that is effectively active code.

**Fix:** Use the `tokenize` module for comment-accurate stripping, or restrict the invariant tests to running a compiled AST walk instead of text grep:
```python
import tokenize, io

def _strip_comments(src: str) -> str:
    tokens = tokenize.generate_tokens(io.StringIO(src).readline)
    result = []
    for tok_type, tok_string, *_ in tokens:
        if tok_type == tokenize.COMMENT:
            result.append("")
        else:
            result.append(tok_string)
    return "".join(result)
```

---

### WR-05: `_IMAGE_REF_RE` allows `oci:` and `docker-daemon:` scheme-like prefixes that bypass the `dir:`/`file:` guard

**File:** `quirk/util/subprocess_input.py:69`

**Issue:** `validate_image_ref` explicitly blocks `dir:` and `file:` prefixes (Syft/Trivy local-filesystem escape vectors) but the regex `^[a-zA-Z0-9][a-zA-Z0-9._\-/:@]{0,254}$` also admits:
- `oci:tarball.tar` (Syft `--from oci-archive` local read)
- `docker-daemon:alpine` (Syft reads from local Docker socket)
- `podman:name` (Podman local image reference)

These are legitimate Syft/Trivy local-access schemes. Depending on which tool is invoked and with which version, these prefixes may cause the scanner to read local filesystem paths or daemon sockets rather than pull from a registry, which is analogous to the blocked `dir:` vector.

**Fix:** Expand the prefix blocklist:
```python
_LOCAL_REF_PREFIXES = ("dir:", "file:", "oci:", "docker-daemon:", "podman:", "docker-archive:")

def validate_image_ref(r: str) -> ValidationResult:
    ...
    if any(r.startswith(p) for p in _LOCAL_REF_PREFIXES):
        return ValidationResult(False, RC_INVALID_IMAGE_REF, _redact_preview(r))
```

---

### WR-06: `apply_security_cli_overrides` is opt-in-only by design but has no test covering the "YAML True is not overridden by absent CLI flag" invariant

**File:** `run_scan.py:49-62`

**Issue:** The function comment says "absent CLI flag (default=False) MUST NOT override a True value already loaded from YAML". The implementation is correct (`if getattr(args, "...", False): cfg.security.X = True`). However, there is no test that verifies a YAML-loaded `allow_insecure_jwks=True` is preserved when `--allow-insecure-jwks` is absent from the CLI. This is the critical security invariant for the whole opt-in pattern, and a future refactor (e.g., replacing `if` with assignment) would silently break it with no test failure.

**Fix:** Add a unit test:
```python
def test_apply_security_cli_overrides_yaml_true_not_revoked():
    from types import SimpleNamespace
    cfg = SimpleNamespace(security=SimpleNamespace(
        allow_insecure_jwks=True,
        allow_internal_targets=True,
        allow_cleartext_broker_probe=True,
    ))
    args = SimpleNamespace(
        allow_insecure_jwks=False,
        allow_internal_targets=False,
        allow_cleartext_broker_probe=False,
    )
    from run_scan import apply_security_cli_overrides
    apply_security_cli_overrides(cfg, args)
    assert cfg.security.allow_insecure_jwks is True
    assert cfg.security.allow_internal_targets is True
    assert cfg.security.allow_cleartext_broker_probe is True
```

---

## Info

### IN-01: `redacted_preview` is empty string for `ok=True` results but docstring says it is only "<=32 chars" — callers could be confused

**File:** `quirk/util/subprocess_input.py:37`, `quirk/util/url_allowlist.py:37`

**Issue:** Both `ValidationResult` dataclasses document `redacted_preview` as `"" when ok=True"` in their docstrings, but callers who pattern-match only on `result.ok` and then log `result.redacted_preview` without checking `ok` first will always log an empty string for successful results, which may make log entries look incomplete. The frozen dataclass design is correct; the documentation is adequate. Minor: the field name `redacted_preview` is slightly misleading when `ok=True` since it is not a preview of anything.

**Fix:** No code change required. Consider renaming to `rejected_input_preview` or documenting the empty-string convention more prominently in the class docstring.

---

### IN-02: `_is_ip_redis` imports `ipaddress` inside the function body on every call

**File:** `quirk/scanner/broker_scanner.py:664`

**Issue:** `import ipaddress` is executed inside `_is_ip_redis` on every invocation. While Python caches module imports and the cost is trivial (one dict lookup), it is inconsistent with the module-level import style used everywhere else in this file.

**Fix:** Move `import ipaddress` to the top of `broker_scanner.py` with the other standard-library imports.

---

### IN-03: `scan_saml_targets` checks `strict.reason in {"internal_ip", "loopback", "link_local"}` but uses string literals instead of the exported reason-code constants

**File:** `quirk/scanner/saml_scanner.py:439`

**Issue:** The advisory emission condition compares `strict.reason` against hardcoded string literals `{"internal_ip", "loopback", "link_local"}` rather than the exported constants `RC_INTERNAL_IP`, `RC_LOOPBACK`, `RC_LINK_LOCAL` from `url_allowlist`. If a reason code is renamed in `url_allowlist.py`, this comparison silently stops matching and the advisory is never emitted.

**Fix:**
```python
from quirk.util.url_allowlist import (
    validate_external_url, RC_INTERNAL_IP, RC_LOOPBACK, RC_LINK_LOCAL
)
...
if not strict.ok and strict.reason in {RC_INTERNAL_IP, RC_LOOPBACK, RC_LINK_LOCAL}:
```

---

### IN-04: `test_scan_rabbitmq_targets_default_no_advisories` does not mock the network

**File:** `tests/scanner/test_broker_hardening.py:159-172`

**Issue:** `scan_rabbitmq_targets(hosts=["rabbit.example"], ...)` is called without mocking `scan_one_rabbitmq`, `_scan_one_sslyze_broker`, `_detect_amqp_plaintext`, or `socket.create_connection`. The test may pass in CI because `rabbit.example` is unreachable (connection refused → returns `None`), but it makes a real network attempt. On a network that has a proxy or internal DNS wildcard resolving all names to an IP, the test can flake or produce false positives.

**Fix:** Mock the socket-level functions:
```python
def test_scan_rabbitmq_targets_default_no_advisories():
    with patch("quirk.scanner.broker_scanner.socket.create_connection",
               side_effect=ConnectionRefusedError):
        endpoints = scan_rabbitmq_targets(
            hosts=["rabbit.example"], timeout=5,
            security=SecurityCfg(), broker_credentials={},
        )
        advisories = [e for e in endpoints if getattr(e, "protocol", "") == "ADVISORY"]
        assert advisories == []
```

---

_Reviewed: 2026-05-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
