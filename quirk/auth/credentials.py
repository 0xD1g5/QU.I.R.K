"""Ephemeral credential context for QU.I.R.K. authenticated scans (Phase 93).

Decision enforcement:
  D-04: Secret stored as bytearray; zeroed in close()/finally block.
  D-05: Zeroization is best-effort — Python GC may retain heap copies.
  D-14: Zero imports from quirk.scanner.* to prevent circular deps.

Public surface:
  CredentialContext.from_cli(...)  -> Optional[CredentialContext]
  CredentialContext.as_headers()   -> dict[str, str]
  CredentialContext.query_param()  -> tuple[str, str] | None
  CredentialContext.close()        -> None
"""
from __future__ import annotations

import getpass
import os
from dataclasses import dataclass, field
from typing import Optional

from quirk.util.targets import (
    load_targets_file,
    TargetFileError,
    _BLOCKED_PREFIXES,
    RC_PATH_TRAVERSAL,
    RC_PATH_NOT_ALLOWED_PREFIX,
)
from quirk.util.safe_exc import safe_str

# D-14 enforcement note: NO imports from quirk.scanner.* below this line.
# quirk.util.* imports (targets, safe_exc) are permitted and required.


@dataclass
class CredentialContext:
    """In-memory credential holder for a single authenticated scan run.

    Secret is stored as bytearray (D-04). Call close() or use as a
    context manager to zero the buffer when the scan completes.

    Fields:
        scheme: one of "bearer" | "api_key_header" | "api_key_query" | "basic"
        _secret_buf: bytearray holding the secret (repr=False to prevent leakage)
        _header_name: custom header name for api_key_header scheme (repr=False)
        _query_param: query parameter name for api_key_query scheme (repr=False)
    """

    scheme: str  # "bearer" | "api_key_header" | "api_key_query" | "basic"
    _secret_buf: bytearray = field(default_factory=bytearray, repr=False, compare=False)
    _header_name: Optional[str] = field(default=None, repr=False)
    _query_param: Optional[str] = field(default=None, repr=False)

    def as_headers(self) -> dict[str, str]:
        """Materialize auth headers — str only at injection boundary (D-04).

        Returns {} for api_key_query scheme; query placement via query_param() (D-03).
        """
        secret = self._secret_buf.decode("utf-8")
        if self.scheme == "bearer":
            return {"Authorization": f"Bearer {secret}"}
        if self.scheme == "api_key_header":
            return {self._header_name or "X-Api-Key": secret}
        if self.scheme == "basic":
            return {"Authorization": f"Basic {secret}"}
        # api_key_query: secret goes on query string, never in headers (D-03)
        return {}

    def query_param(self) -> Optional[tuple[str, str]]:
        """Return (param_name, secret) for api_key_query scheme; None otherwise.

        The caller appends this to the URL query string — the secret never
        lands in a header (D-03).
        """
        if self.scheme != "api_key_query":
            return None
        secret = self._secret_buf.decode("utf-8")
        return (self._query_param or "api_key", secret)

    def close(self) -> None:
        """Zero the secret buffer in place (best-effort, D-04/D-05)."""
        n = len(self._secret_buf)
        if n:
            self._secret_buf[:] = b"\x00" * n

    def __enter__(self) -> "CredentialContext":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @classmethod
    def from_cli(
        cls,
        *,
        bearer: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_query: Optional[str] = None,
        basic: Optional[str] = None,
    ) -> Optional["CredentialContext"]:
        """Build CredentialContext from CLI reference args (D-01/D-02).

        Each scheme arg is a REFERENCE, not a secret:
          - Empty string or "PROMPT" sentinel: interactive getpass prompt
          - Starts with "@": read file via load_targets_file path-traversal guard
          - Looks like an env-var name (all-caps, set in environment): read and
            delete the env var (prevents subprocess inheritance, PITFALLS Pitfall 1)
          - Anything else: raise ValueError with reference-usage guidance (teach
            the consultant the correct pattern; error text scrubbed via safe_str)

        Precedence (D-02): prompt > env var > @file / flag-reference.
        Returns None when no scheme arg is supplied.
        """
        # Resolve in priority order: bearer, api_key, api_key_query, basic.
        # Only one scheme is active per call (first non-None wins for precedence).
        if bearer is not None:
            raw = _resolve_reference("bearer", bearer, prompt="Bearer token: ")
            return cls(
                scheme="bearer",
                _secret_buf=bytearray(raw.encode("utf-8")),
            )

        if api_key is not None:
            raw = _resolve_reference("api_key", api_key, prompt="API key (header): ")
            return cls(
                scheme="api_key_header",
                _secret_buf=bytearray(raw.encode("utf-8")),
                _header_name=None,  # defaults to X-Api-Key
            )

        if api_key_query is not None:
            raw = _resolve_reference("api_key_query", api_key_query, prompt="API key (query): ")
            return cls(
                scheme="api_key_query",
                _secret_buf=bytearray(raw.encode("utf-8")),
                _query_param="api_key",
            )

        if basic is not None:
            raw = _resolve_reference("basic", basic, prompt="Basic auth credentials: ")
            return cls(
                scheme="basic",
                _secret_buf=bytearray(raw.encode("utf-8")),
            )

        return None


def _resolve_reference(scheme: str, ref: str, *, prompt: str) -> str:
    """Resolve a credential reference to the raw secret string.

    Precedence (D-02): prompt > env var > @file / flag-reference.

    Args:
        scheme: credential scheme name (for error messages)
        ref: the reference string from the CLI arg
        prompt: prompt text for interactive getpass

    Returns:
        The resolved credential string.

    Raises:
        TargetFileError: if @file path fails traversal/prefix guard
        ValueError: if the ref is neither a known pattern nor a set env var
    """
    # 1. Empty string or "PROMPT" sentinel → interactive getpass (highest precedence)
    if ref == "" or ref == "PROMPT":
        return getpass.getpass(prompt)

    # 2. @file reference → load via the v4.8 hardened guard (D-13/D-14 / CR-09).
    #    Apply the same traversal + blocked-prefix checks as parse_target_tokens
    #    before delegating to load_targets_file.
    if ref.startswith("@"):
        file_path = ref[1:]
        _real = os.path.realpath(file_path)
        _cwd_real = os.path.realpath(os.getcwd())
        if not (_real.startswith(_cwd_real + os.sep) or _real == _cwd_real):
            raise TargetFileError(file_path, RC_PATH_TRAVERSAL)
        if any(_real.startswith(p) for p in _BLOCKED_PREFIXES):
            raise TargetFileError(file_path, RC_PATH_NOT_ALLOWED_PREFIX)
        return load_targets_file(file_path).strip()

    # 3. Env-var name → read and delete (prevents subprocess inheritance)
    if ref in os.environ:
        raw = os.environ[ref]
        del os.environ[ref]
        return raw

    # 4. Nothing matched → the ref is not a known reference pattern.
    #    Route through safe_str so an accidentally-inlined secret cannot
    #    leak into the error text (LEAK-03).
    _dummy_exc = ValueError(ref)
    _scrubbed = safe_str(_dummy_exc)
    raise ValueError(
        f"Cannot resolve {scheme!r} credential reference {_scrubbed!r}. "
        f"Pass one of: @<file-path> (e.g. @/path/to/token), "
        f"an environment variable name containing the secret, "
        f"or a bare flag (empty string) to trigger an interactive prompt. "
        f"Do NOT pass the secret value directly on the command line."
    )
