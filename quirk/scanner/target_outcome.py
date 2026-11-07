"""Phase 235.3 D-05: the single source for the per-target outcome shape.

Every connector scanner records, per configured target, one of five outcome
kinds (answered / refused / missing_credentials / auth_failed / unreachable)
into a ``TargetOutcomes`` sink; ``run_scan._classify_connector_outcomes`` turns
the sink into ``ran`` or a named ``skipped`` phase. Keeping the vocabulary, the
skip-reason mapping and the advisory categories in ONE module follows
``quirk/util/scanner_binaries.py``: hand-maintained parallel lists have drifted
repeatedly in this project.

Import discipline: stdlib plus ``quirk.util`` only. Optional-extra packages
(botocore, hvac, psycopg2, pymysql, ldap3, azure, google) are NEVER imported
here; exceptions are classified by ``type(exc).__mro__`` class names and
duck-typed attributes so the module imports on a minimal install.

Label contract: scanners record only against targets the closure supplied
(iterate the same raw list passed to ``TargetOutcomes(...)`` or use
``sole_target()``); they never rebuild a label. Targets are keyed by the RAW
configured value (``str()``-coerced); ``redact_target`` is display-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Iterable, List, Tuple

from quirk.util.safe_exc import safe_str
from quirk.util.url_allowlist import (
    RC_CONSOLE_ENDPOINT,
    RC_INTERNAL_IP,
    RC_LINK_LOCAL,
    RC_LOOPBACK,
    RC_METADATA_SERVICE_IP,
    RC_SCHEME_PREFIX,
    _redact_url_preview,
)

OUTCOME_ANSWERED: Final[str] = "answered"
OUTCOME_REFUSED: Final[str] = "refused"
OUTCOME_MISSING_CREDENTIALS: Final[str] = "missing_credentials"
OUTCOME_AUTH_FAILED: Final[str] = "auth_failed"
OUTCOME_UNREACHABLE: Final[str] = "unreachable"
OUTCOME_KINDS: Final[frozenset] = frozenset({
    OUTCOME_ANSWERED,
    OUTCOME_REFUSED,
    OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_AUTH_FAILED,
    OUTCOME_UNREACHABLE,
})

OUTCOME_TO_SKIP_REASON: Final[Dict[str, str]] = {
    OUTCOME_REFUSED: "internal-target-refused",
    OUTCOME_MISSING_CREDENTIALS: "missing-credentials",
    OUTCOME_AUTH_FAILED: "auth-failed",
    OUTCOME_UNREACHABLE: "failed",
}

SKIP_REASON_TO_ADVISORY_CATEGORY: Final[Dict[str, str]] = {
    "internal-target-refused": "internal_target_refused",
    "auth-failed": "auth_failed",
    "missing-credentials": "missing_credentials",
    "failed": "targets_unreachable",
}

COVERAGE_SKIP_ADVISORY_CATEGORIES: Final[frozenset] = frozenset({
    "missing_extra",
    "missing_binary",
    *SKIP_REASON_TO_ADVISORY_CATEGORY.values(),
})

# P-14: a target that did not answer inside an otherwise-ran phase is a real
# scan error (trends may count it), deliberately NOT an advisory category.
PER_TARGET_ERROR_CATEGORY: Final[str] = "target_unanswered"

# P-06 priority (highest first) when no target answered and kinds are mixed.
_FAILURE_PRIORITY: Final[Tuple[str, ...]] = (
    OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_AUTH_FAILED,
    OUTCOME_REFUSED,
    OUTCOME_UNREACHABLE,
)

_NO_OUTCOME_DETAIL: Final[str] = "no outcome recorded by scanner"


class TargetOutcomeContractError(ValueError):
    """Label-contract violation. Scanners must re-raise it, never reclassify."""


def redact_target(raw) -> str:
    """Display label for *raw*: userinfo/query/fragment stripped, max 64. NEVER a key."""
    text = str(raw)
    if "://" not in text:
        # Scheme-less refs (container images, host:port) bypass urlsplit's
        # userinfo handling; drop a ``user:pass@`` before the first "/".
        authority, sep, rest = text.partition("/")
        userinfo, at, host = authority.rpartition("@")
        if at and ":" in userinfo:
            text = host + sep + rest
    return _redact_url_preview(text, max_len=64)


@dataclass(frozen=True)
class TargetOutcome:
    target: str  # redacted display label
    kind: str
    detail: str = ""
    row_emitted: bool = False


class TargetOutcomes:
    """Per-target outcome sink keyed by the raw configured value (str()-coerced)."""

    def __init__(self, expected: Iterable) -> None:
        self.expected: List[str] = []
        self.labels: Dict[str, str] = {}
        for raw in expected:
            key = str(raw)
            if key in self.labels:
                continue
            self.expected.append(key)
            self.labels[key] = redact_target(key)
        self._extras: List[str] = []
        # raw key -> list of (kind, detail, row_emitted) in record order
        self.items: Dict[str, List[Tuple[str, str, bool]]] = {}

    def record(
        self,
        target,
        kind: str,
        detail: str = "",
        *,
        row_emitted: bool = False,
        extra: bool = False,
    ) -> None:
        if kind not in OUTCOME_KINDS:
            raise ValueError(f"Unknown target outcome kind: {kind!r}")
        key = str(target)
        if key not in self.labels:
            if not extra:
                raise TargetOutcomeContractError(
                    f"target {redact_target(key)!r} is not in the expected set; "
                    "record against outcomes.expected / sole_target() or pass extra=True"
                )
            self.labels[key] = redact_target(key)
            self._extras.append(key)
        self.items.setdefault(key, []).append((kind, detail, row_emitted))

    def answered(self, target) -> None:
        self.record(target, OUTCOME_ANSWERED)

    def sole_target(self) -> str:
        if len(self.expected) != 1:
            raise TargetOutcomeContractError(
                f"sole_target() requires exactly one expected target, got {len(self.expected)}"
            )
        return self.expected[0]

    def resolved(self) -> List[TargetOutcome]:
        out: List[TargetOutcome] = []
        for key in [*self.expected, *self._extras]:
            label = self.labels[key]
            recs = self.items.get(key, [])
            if not recs:
                out.append(TargetOutcome(label, OUTCOME_UNREACHABLE, _NO_OUTCOME_DETAIL))
                continue
            if any(r[0] == OUTCOME_ANSWERED for r in recs):
                out.append(TargetOutcome(label, OUTCOME_ANSWERED))
                continue
            chosen = None
            for kind in _FAILURE_PRIORITY:
                for r in recs:
                    if r[0] == kind:
                        chosen = r
                        break
                if chosen is not None:
                    break
            assert chosen is not None
            out.append(TargetOutcome(label, chosen[0], chosen[1], chosen[2]))
        return out


# ---------------------------------------------------------------------------
# Exception / reason-code classifiers (pure; no optional-extra imports)
# ---------------------------------------------------------------------------

def outcome_for_url_guard(reason_code: str) -> Tuple[str, str]:
    if reason_code in (RC_LOOPBACK, RC_INTERNAL_IP, RC_LINK_LOCAL):
        return OUTCOME_REFUSED, reason_code
    if reason_code in (RC_METADATA_SERVICE_IP, RC_CONSOLE_ENDPOINT, RC_SCHEME_PREFIX):
        return OUTCOME_UNREACHABLE, f"refused: {reason_code} (always blocked)"
    return OUTCOME_UNREACHABLE, str(reason_code)


_MISSING_CREDENTIAL_CLASSES: Final[frozenset] = frozenset({
    "NoCredentialsError", "PartialCredentialsError", "ProfileNotFound",
    "TokenRetrievalError", "SSOTokenLoadError", "UnauthorizedSSOTokenError",
    "CredentialRetrievalError", "CredentialUnavailableError",
    "DefaultCredentialsError",
})
AUTH_FAILED_CODES: Final[frozenset] = frozenset({
    "InvalidAccessKeyId", "SignatureDoesNotMatch", "InvalidClientTokenId",
    "ExpiredToken", "ExpiredTokenException", "UnrecognizedClientException",
    "AccessDenied", "AccessDeniedException",
    # 235.3 review A-WR-01: AWS EC2-style denial plus Azure ARM / Key Vault
    # RBAC denials and Azure token rejections.
    "UnauthorizedOperation", "AuthorizationFailed", "Forbidden",
    "InvalidAuthenticationToken", "ExpiredAuthenticationToken",
})
_IAM_PERMISSION_CODES: Final[frozenset] = frozenset({
    "AccessDenied", "AccessDeniedException", "UnauthorizedOperation",
    "AuthorizationFailed", "Forbidden",
})

# 235.3 review A-WR-02: DefaultAzureCredential / ChainedTokenCredential raise a
# plain ClientAuthenticationError carrying this sentence when no credential in
# the chain produced a token. Each "Attempted credentials" line that reports
# one of these markers is a credential that never attempted authentication
# (CredentialUnavailableError); a line without any marker is a credential that
# tried and was rejected, which ends the chain.
_AZURE_CHAIN_SENTENCE: Final[str] = "failed to retrieve a token from the included credentials"
_AZURE_UNAVAILABLE_MARKERS: Final[Tuple[str, ...]] = (
    "unavailable", "not found", "not installed", "could not be found",
    "requires the", "no accounts", "not fully configured", "not configured",
    "az login", "connect-azaccount", "azd auth login",
)


def _azure_chain_had_no_credentials(message: str) -> bool:
    if _AZURE_CHAIN_SENTENCE not in message:
        return False
    _head, sep, tail = message.partition("Attempted credentials:")
    if not sep:
        return "unavailable" in message.lower()
    attempts = []
    for line in tail.splitlines():
        line = line.strip()
        if not line or line.lower().startswith(("to mitigate", "visit https")):
            continue
        attempts.append(line.lower())
    if not attempts:
        return "unavailable" in message.lower()
    return all(any(m in a for m in _AZURE_UNAVAILABLE_MARKERS) for a in attempts)


def _http_status(exc: BaseException):
    """HTTP status of a GCP HttpError / Azure HttpResponseError (duck-typed)."""
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _mro_names(exc: BaseException) -> List[str]:
    return [c.__name__ for c in type(exc).__mro__]


def _error_code(exc: BaseException) -> str:
    resp = getattr(exc, "response", None)
    if isinstance(resp, dict):
        err = resp.get("Error")
        if isinstance(err, dict) and err.get("Code"):
            return str(err["Code"])
    err_obj = getattr(exc, "error", None)
    code = getattr(err_obj, "code", None) if err_obj is not None else None
    if code:
        return str(code)
    code = getattr(exc, "code", None)
    return str(code) if isinstance(code, str) else ""


def outcome_for_cloud_exception(exc: BaseException) -> Tuple[str, str]:
    names = _mro_names(exc)
    if any(n in _MISSING_CREDENTIAL_CLASSES for n in names):
        return OUTCOME_MISSING_CREDENTIALS, safe_str(exc)
    if "ClientAuthenticationError" in names:
        try:
            message = str(getattr(exc, "message", None) or exc)
        except Exception:
            message = ""
        if _azure_chain_had_no_credentials(message):
            return (
                OUTCOME_MISSING_CREDENTIALS,
                "no Azure credential source available (DefaultAzureCredential chain "
                "exhausted: no environment credentials, az login, or managed identity)",
            )
        return OUTCOME_AUTH_FAILED, safe_str(exc)
    if "RefreshError" in names:
        # google.auth: expired / revoked ADC (invalid_grant) -- present but rejected.
        return OUTCOME_AUTH_FAILED, safe_str(exc)
    if "ClientError" in names or "HttpResponseError" in names:
        code = _error_code(exc)
        if code in AUTH_FAILED_CODES:
            if code in _IAM_PERMISSION_CODES:
                return (
                    OUTCOME_AUTH_FAILED,
                    "credentials lack a required IAM permission: " + safe_str(exc),
                )
            return OUTCOME_AUTH_FAILED, safe_str(exc)
    if "HttpError" in names or "HttpResponseError" in names:
        # googleapiclient.errors.HttpError (resp.status) / Azure HttpResponseError
        # (status_code) with no recognised error code: 401/403 is a denial.
        if _http_status(exc) in (401, 403):
            return (
                OUTCOME_AUTH_FAILED,
                "credentials lack a required permission: " + safe_str(exc),
            )
    return OUTCOME_UNREACHABLE, safe_str(exc)


def outcome_for_db_exception(exc: BaseException) -> Tuple[str, str]:
    detail = safe_str(exc)
    first = exc.args[0] if exc.args else None
    if first == 1045 or first == "1045":
        return OUTCOME_AUTH_FAILED, detail
    low = (str(exc) + " " + detail).lower()
    if "authentication failed" in low or "access denied" in low:
        return OUTCOME_AUTH_FAILED, detail
    return OUTCOME_UNREACHABLE, detail


def outcome_for_vault_exception(exc: BaseException) -> Tuple[str, str]:
    if any(n in ("Unauthorized", "Forbidden") for n in _mro_names(exc)):
        return OUTCOME_AUTH_FAILED, safe_str(exc)
    return OUTCOME_UNREACHABLE, safe_str(exc)
