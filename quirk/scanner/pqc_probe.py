"""PQC-hybrid TLS endpoint probe — Phase 90 PQC-02.

Implements a capability-gated raw ``openssl s_client`` subprocess probe that
detects X25519MLKEM768 (NamedGroup 4588, NIST-standardized ML-KEM) support on a
target host:port.  The probe is deliberately kept OUTSIDE the sslyze/nassl flow
(D-01): sslyze bundles its own old OpenSSL and returns ERROR_NO_CONNECTIVITY
against the hybrid endpoint, so detection must be a separate subprocess.

Security requirements (T-90-03, T-90-04):
- Subprocess command is always an **argv list** — never shell=True.
- host is validated (non-empty, no shell metacharacters).
- port is coerced to int.
- Hard subprocess timeout (default 8 s) + stdin from /dev/null.
- TimeoutExpired is caught; detected=False is returned — no exception escapes.

Probe result dict::

    {
        "detected": bool,          # True only when Negotiated TLS1.3 group: X25519MLKEM768
        "negotiated_group": str | None,
        "capability_ok": bool,     # True if host OpenSSL advertises ML-KEM support
    }
"""
from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, Optional

# Shell metacharacters that must not appear in a host string (T-90-03).
_SHELL_METACHAR_RE = re.compile(r'[;&|`$<>(){}\\"\'\s]')

# Probe target group — the NIST-standardized ML-KEM hybrid (NamedGroup 4588, D-02).
_HYBRID_GROUP = "X25519MLKEM768"

# Substring parsed from openssl s_client output to confirm a successful negotiation.
_NEGOTIATED_PREFIX = "Negotiated TLS1.3 group: "


def _validate_host(host: str) -> bool:
    """Return True when host is non-empty and contains no shell metacharacters."""
    if not host:
        return False
    if _SHELL_METACHAR_RE.search(host):
        return False
    return True


def host_supports_mlkem() -> bool:
    """Return True when the host ``openssl`` binary advertises ML-KEM KEM support.

    Runs ``openssl list -kem-algorithms`` as an argv list (no shell=True) and
    checks whether ``X25519MLKEM768`` appears in the output.  Any subprocess
    failure or exception returns False (graceful degradation).
    """
    try:
        result = subprocess.run(
            ["openssl", "list", "-kem-algorithms"],
            capture_output=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=10,
            shell=False,
        )
        output = result.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return _HYBRID_GROUP in output
    except Exception:  # noqa: BLE001
        return False


def probe_pqc_hybrid(
    host: str,
    port: Any,
    timeout: int = 8,
) -> Dict[str, Any]:
    """Probe ``host:port`` for X25519MLKEM768 PQC-hybrid TLS support.

    Builds the openssl command as an argv list and never uses shell=True
    (T-90-03).  Validates host and coerces port to int before constructing
    the command.  A bounded timeout (T-90-04) with stdin from /dev/null
    prevents hung handshakes from stalling the scan.

    Args:
        host: Target hostname or IP address.
        port: Target port (coerced to int).
        timeout: Hard subprocess timeout in seconds (default 8).

    Returns:
        A dict with keys ``detected`` (bool), ``negotiated_group`` (str|None),
        and ``capability_ok`` (bool).
    """
    _not_detected: Dict[str, Any] = {
        "detected": False,
        "negotiated_group": None,
        "capability_ok": False,
    }

    # Input validation (T-90-03)
    if not _validate_host(str(host)):
        return _not_detected

    try:
        port_int = int(port)
    except (TypeError, ValueError):
        return _not_detected

    # Capability gate: check whether host openssl supports ML-KEM (D-01).
    capability_ok = host_supports_mlkem()

    connect_arg = f"{host}:{port_int}"

    # Build argv list — never shell=True (T-90-03).
    cmd = [
        "openssl", "s_client",
        "-connect", connect_arg,
        "-groups", _HYBRID_GROUP,
        # TLS 1.3 only — the hybrid group is TLS 1.3 exclusive.
        "-tls1_3",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            shell=False,
        )
        output = result.stdout or b""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        # T-90-04: hung handshake — treat as not detected, scan continues.
        return {
            "detected": False,
            "negotiated_group": None,
            "capability_ok": capability_ok,
        }
    except Exception:  # noqa: BLE001
        return {
            "detected": False,
            "negotiated_group": None,
            "capability_ok": capability_ok,
        }

    # Parse: look for the negotiated-group confirmation line.
    detected = False
    negotiated_group: Optional[str] = None
    for line in output.splitlines():
        if line.startswith(_NEGOTIATED_PREFIX):
            group = line[len(_NEGOTIATED_PREFIX):].strip()
            if group == _HYBRID_GROUP:
                detected = True
                negotiated_group = group
            break

    return {
        "detected": detected,
        "negotiated_group": negotiated_group,
        "capability_ok": capability_ok,
    }
