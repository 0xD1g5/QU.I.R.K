"""OpenAPI/Swagger spec scanner — Phase 94 SPEC-01/02/03.

Parses a local or scope-gated-URL OpenAPI spec for crypto posture:
  - Security schemes (type, algorithm, bearerFormat)
  - Plaintext http:// server declarations
  - Unauthenticated endpoints (paths with no security requirement)

All findings surface as CryptoEndpoint(protocol="OPENAPI") rows — no new
findings surface or table introduced.

SSRF hardening (T-94-05):
  _assert_no_external_refs() pre-scans ALL $ref values and raises SpecParsingError
  on any ref not starting with '#' — BEFORE calling openapi_spec_validator.validate().
  This is CRITICAL because validate() follows external $refs via urllib (confirmed
  live: 169.254.169.254 TCP connection on validate() call). Subclassing the resolver
  does NOT block it.

DoS hardening (T-94-07):
  MAX_SPEC_BYTES = 10 MB gate applied BEFORE yaml.safe_load on both file and URL paths.

Graceful degradation (Pitfall 4):
  OPENAPI_AVAILABLE = False when [api] extras not installed → returns a single
  CryptoEndpoint(scan_error_category="missing_extra") without raising.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

import yaml

try:
    from openapi_spec_validator import validate as _oas_validate
    OPENAPI_AVAILABLE = True
except ImportError:
    _oas_validate = None  # type: ignore[assignment]
    OPENAPI_AVAILABLE = False

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import _redact_preview, validate_external_url

logger = logging.getLogger(__name__)

# Hard limit: reject specs over 10 MB before parse (SPEC-03 DoS guard, T-94-07).
MAX_SPEC_BYTES = 10 * 1024 * 1024  # 10 MB


class SpecParsingError(Exception):
    """Raised for SSRF attempts, oversized specs, out-of-scope URLs, or parse failures.

    Messages must not contain the raw URL/ref value — use _redact_preview() instead.
    """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_refs(obj: Any, refs: Optional[list] = None) -> list:
    """Recursively collect all $ref string values from a parsed spec dict.

    Only values under the "$ref" key are collected — other keys are traversed
    but their values are not added to the ref list.
    """
    if refs is None:
        refs = []
    if isinstance(obj, dict):
        ref = obj.get("$ref")
        if ref is not None:
            refs.append(str(ref))
        for v in obj.values():
            _collect_refs(v, refs)
    elif isinstance(obj, list):
        for item in obj:
            _collect_refs(item, refs)
    return refs


def _assert_no_external_refs(spec_dict: dict) -> None:
    """Raise SpecParsingError if any $ref is external (not starting with '#').

    CRITICAL: This MUST be called BEFORE openapi_spec_validator.validate() to
    prevent SSRF. The validator follows external $refs via urllib during
    validation — confirmed live in openapi-spec-validator 0.9.0 / jsonschema-path 0.5.0.
    Subclassing the resolver is INSUFFICIENT (RESEARCH Pitfall 2).

    External refs include: http://, https://, ./relative-file, ../parent-file.
    Local (intra-document) refs start with '#' and are safe.

    T-94-05: Messages use _redact_preview() — never the raw ref value.
    """
    refs = _collect_refs(spec_dict)
    external = [r for r in refs if not str(r).startswith("#")]
    if external:
        first_safe = _redact_preview(str(external[0]))
        raise SpecParsingError(
            f"Spec contains {len(external)} external $ref(s) — blocked to prevent SSRF. "
            f"Only intra-document refs (#/...) are permitted. "
            f"First rejected: {first_safe!r}"
        )


def _load_spec_bytes_from_file(path: str) -> bytes:
    """Read raw bytes from a local file, applying the 10 MB gate BEFORE yaml.safe_load.

    Raises SpecParsingError if file is missing or exceeds MAX_SPEC_BYTES.
    T-94-07: size gate is the first thing checked to prevent decompression bombs.
    """
    if not os.path.isfile(path):
        raise SpecParsingError(f"Spec file not found: {_redact_preview(path)!r}")

    # Read exactly MAX_SPEC_BYTES + 1 bytes — if we get more than the limit, reject.
    with open(path, "rb") as fh:
        raw = fh.read(MAX_SPEC_BYTES + 1)
    if len(raw) > MAX_SPEC_BYTES:
        size = os.path.getsize(path)
        raise SpecParsingError(
            f"Spec file exceeds 10 MB limit ({size} bytes) — refused to parse."
        )
    return raw


def _fetch_spec_bytes_from_url(url: str, cfg_targets: list, *, allow_internal: bool = False) -> bytes:
    """Fetch raw spec bytes from URL — ONLY when within configured scan-target scope.

    Scope gate (SPEC-02): the URL's HOST must match one of cfg_targets (T-94-06).
    cfg_targets are bare FQDNs (e.g. "api.example.com"); a full URL is also accepted
    and reduced to its host. Raises SpecParsingError BEFORE any network request if the
    URL host is out of scope.

    Then validate_external_url() (SSRF guard): blocks metadata IPs always,
    blocks private/loopback unless allow_internal. Raises SpecParsingError on not-ok.

    Finally fetches with httpx and applies the 10 MB gate on response content.
    """
    import httpx
    from urllib.parse import urlparse

    # CR-01 fix: compare the URL HOST against target FQDNs, not a string-prefix of the
    # full URL (a bare FQDN like "api.example.com" never prefix-matches "https://...").
    url_host = (urlparse(url).hostname or "").lower()
    allowed_hosts = {
        (urlparse(t).hostname or t.split("/")[0]).lower().rstrip("/")
        for t in (cfg_targets or [])
    }
    # Scope gate — reject before any network request (SPEC-02, T-94-06)
    if not url_host or url_host not in allowed_hosts:
        raise SpecParsingError(
            f"OpenAPI spec URL is outside configured scan-target scope — "
            f"URL fetch is only permitted for URLs whose host is in the targets list: "
            f"{_redact_preview(url)!r}"
        )

    # SSRF gate — validate_external_url blocks metadata IPs always; loopback/private
    # only permitted when allow_internal is set (WR-01: thread --allow-internal-targets).
    vr = validate_external_url(url, allow_internal=allow_internal)
    if not vr.ok:
        raise SpecParsingError(
            f"OpenAPI spec URL rejected ({vr.reason}): {vr.redacted_preview!r}"
        )

    try:
        resp = httpx.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        raise SpecParsingError(
            f"Failed to fetch OpenAPI spec URL: {safe_str(exc)}"
        ) from exc

    content = resp.content
    if len(content) > MAX_SPEC_BYTES:
        raise SpecParsingError("Fetched spec content exceeds 10 MB limit.")
    return content


def _parse_spec_dict(raw_bytes: bytes) -> dict:
    """Parse raw YAML/JSON bytes into a spec dict.

    Wraps yaml.safe_load — JSON is valid YAML so both formats work.
    Raises SpecParsingError on parse failure.
    """
    try:
        result = yaml.safe_load(raw_bytes)
    except Exception as exc:
        raise SpecParsingError(
            f"Spec YAML/JSON parse error: {safe_str(exc)}"
        ) from exc
    if not isinstance(result, dict):
        raise SpecParsingError(
            f"Spec did not parse as a dict (got {type(result).__name__!r})."
        )
    return result


def _validate_spec_lenient(spec_dict: dict) -> None:
    """Run openapi-spec-validator.validate() in lenient mode.

    Per CONTEXT: validate structure but don't block on validation errors.
    A ValidationError produces a warning and we continue (lenient parse-what-we-can).
    RESEARCH Pitfall 7: strict validation breaks on real-world Swagger 2.0 specs.

    MUST be called only AFTER _assert_no_external_refs() (SPEC-03 SSRF guard).
    """
    if not OPENAPI_AVAILABLE or _oas_validate is None:
        return
    try:
        _oas_validate(spec_dict)
    except Exception as exc:
        # Lenient: log warning but continue with raw spec dict
        logger.warning("OpenAPI spec structural validation warning (continuing): %s", safe_str(exc))


def _scanned_at() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Crypto posture extraction
# ---------------------------------------------------------------------------

def extract_crypto_posture(spec_dict: dict) -> List[CryptoEndpoint]:
    """Extract crypto-relevant findings from a parsed OpenAPI spec dict.

    Returns CryptoEndpoint rows (protocol="OPENAPI"):
      - Security scheme declarations → service_detail "security_scheme:<name>"
        - bearerFormat JWT → cert_pubkey_alg set to the bearerFormat value
      - Plaintext http:// servers → service_detail "plaintext_server", severity HIGH
      - Unauthenticated paths → service_detail "unauthenticated_endpoint"
    """
    endpoints: List[CryptoEndpoint] = []
    _now = _scanned_at()

    # Extract the spec host for use as the CryptoEndpoint host field.
    # Use the first server URL, or "unknown" if not present.
    servers = spec_dict.get("servers", [])
    primary_host = "unknown"
    for srv in servers:
        url = str(srv.get("url", ""))
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            primary_host = parsed.netloc or url[:64]
            break

    # ---- Security scheme declarations ----
    components = spec_dict.get("components", {}) or {}
    security_schemes = components.get("securitySchemes", {}) or {}
    # Swagger 2.0 uses top-level securityDefinitions
    if not security_schemes:
        security_schemes = spec_dict.get("securityDefinitions", {}) or {}

    for scheme_name, scheme_def in security_schemes.items():
        if not isinstance(scheme_def, dict):
            continue
        scheme_type = str(scheme_def.get("type", "")).lower()
        bearer_format = scheme_def.get("bearerFormat") or ""
        # For bearer JWT schemes, use bearerFormat as the declared algorithm hint
        cert_pubkey_alg: Optional[str] = None
        if scheme_type == "http" and str(scheme_def.get("scheme", "")).lower() == "bearer":
            if bearer_format:
                cert_pubkey_alg = str(bearer_format)

        endpoints.append(CryptoEndpoint(
            host=primary_host,
            port=443,
            protocol="OPENAPI",
            cert_pubkey_alg=cert_pubkey_alg,
            service_detail=f"security_scheme:{scheme_name}",
            severity="INFO",
            scanned_at=_now,
        ))

    # ---- Server URL declarations ----
    for srv in servers:
        url = str(srv.get("url", ""))
        if not url:
            continue
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme == "http":
            # Plaintext server — HIGH severity (T-94-07 / SPEC-01)
            endpoints.append(CryptoEndpoint(
                host=parsed.netloc or url[:64],
                port=80,
                protocol="OPENAPI",
                service_detail="plaintext_server",
                severity="HIGH",
                scanned_at=_now,
            ))

    # ---- Unauthenticated path operations ----
    # A path operation is unauthenticated if it has no security requirement
    # and the global security is also absent or empty.
    global_security = spec_dict.get("security", [])
    paths = spec_dict.get("paths", {}) or {}
    http_methods = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}

    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Handle $ref-resolved path items (if any remain after guard)
        if "$ref" in path_item:
            continue
        for method, operation in path_item.items():
            if method.lower() not in http_methods:
                continue
            if not isinstance(operation, dict):
                continue
            # Per-operation security overrides global. Empty list [] means "no auth required".
            op_security = operation.get("security")
            if op_security is None:
                # Falls back to global; if global is empty/absent → unauthenticated
                effective_security = global_security
            else:
                effective_security = op_security

            if not effective_security:  # empty list or no security at all
                endpoints.append(CryptoEndpoint(
                    host=primary_host,
                    port=443,
                    protocol="OPENAPI",
                    service_detail=f"unauthenticated_endpoint:{method.upper()} {path_str}",
                    severity="MEDIUM",
                    scanned_at=_now,
                ))

    return endpoints


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_openapi_spec(
    path_or_url: str,
    *,
    cfg_targets: Optional[list] = None,
    allow_internal: bool = False,
) -> List[CryptoEndpoint]:
    """Parse an OpenAPI spec from a local file or scope-gated URL and return findings.

    Args:
        path_or_url: Local file path or HTTP/HTTPS URL to the spec.
        cfg_targets: List of target base URLs from AppConfig.targets. Required when
            path_or_url is a URL (scope gate enforced). Safe to pass [] for local files.

    Returns:
        List of CryptoEndpoint(protocol="OPENAPI") rows.

    Raises:
        SpecParsingError: On SSRF attempt, oversized spec, out-of-scope URL, or missing file.
        Does NOT raise on missing optional dep — returns a degraded endpoint instead.

    Security:
        - _assert_no_external_refs() called BEFORE _oas_validate() (SPEC-03 SSRF)
        - 10 MB gate applied BEFORE yaml.safe_load (SPEC-03 DoS)
        - URL scope gate applied BEFORE any network request (SPEC-02)
        - SpecParsingError messages use _redact_preview() — never raw URL/ref values
    """
    _targets = cfg_targets or []

    # Graceful degradation: missing optional dep → missing_extra endpoint, never raise
    if not OPENAPI_AVAILABLE:
        return [CryptoEndpoint(
            host=path_or_url[:64] if path_or_url else "unknown",
            port=0,
            protocol="OPENAPI",
            service_detail="openapi-spec-validator not installed",
            severity="INFO",
            scan_error_category="missing_extra",
            scanned_at=_scanned_at(),
        )]

    # Determine if input is a URL or a local file path
    is_url = path_or_url.startswith("http://") or path_or_url.startswith("https://")

    if is_url:
        raw_bytes = _fetch_spec_bytes_from_url(path_or_url, _targets, allow_internal=allow_internal)
    else:
        raw_bytes = _load_spec_bytes_from_file(path_or_url)

    spec_dict = _parse_spec_dict(raw_bytes)

    # CRITICAL ORDER: assert_no_external_refs BEFORE _oas_validate (T-94-05 SSRF guard)
    _assert_no_external_refs(spec_dict)

    # Lenient structural validation (warns but does not block on ValidationError)
    _validate_spec_lenient(spec_dict)

    return extract_crypto_posture(spec_dict)
