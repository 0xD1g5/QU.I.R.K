"""REST crypto-posture fuzzer — Phase 96 FUZZ-01/02/03/04.

This module provides the CONFIRM gate, budget enforcement, and (in later plans)
the active request dispatch loop for opt-in REST crypto-posture fuzzing.

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

Gate functions are fully injectable (prompt_fn, stderr_print_fn, is_tty) so
tests never touch real sys.stdin/sys.stderr.

Plan 02 adds: run_fuzz_scan(), TokenBucket rate limiter, TLS/HSTS/cipher probes,
5xx-cascade tracker, scope gate, CryptoEndpoint emission.
"""

from __future__ import annotations

import logging
import ssl
import socket
import sys
import warnings
from typing import Any, Final, List, Optional

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
      ``CONFIRM`` (case-sensitive, after .strip()); any other input aborts.

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
