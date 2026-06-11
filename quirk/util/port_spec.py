"""Port-spec parser for QU.I.R.K. — Phase 121 PORT-01/PORT-02.

Parses user-supplied port specifications (comma-separated values and low-high
ranges) into a validated, deduplicated, sorted list of TCP port numbers.

Public surface:
  parse_port_spec(s: str) -> List[int]
"""
from __future__ import annotations

import re
from typing import Final, List

# Maximum number of distinct ports a single spec may expand to.
# Rejects obviously oversized custom ranges (e.g. "1-65535") that would
# produce pathological scans and oversized ports_tls lists.
_PORT_SPEC_CAP: Final[int] = 2048

# Only accept tokens that are either a bare integer ("443") or an int-int
# range ("8000-8002"). Anything else is malformed.
_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"^\d+(-\d+)?$")

_PORT_MIN: Final[int] = 1
_PORT_MAX: Final[int] = 65535


def parse_port_spec(s: str) -> List[int]:
    """Parse a comma/range port spec string into a sorted, deduplicated list.

    Parameters
    ----------
    s:
        Port specification string.  Accepts comma-separated tokens where each
        token is either a bare integer (``443``) or a ``low-high`` inclusive
        range (``8000-8002``).  Whitespace around tokens is stripped.

    Returns
    -------
    List[int]
        Sorted, deduplicated list of port numbers in 1–65535.

    Raises
    ------
    ValueError
        On any of: empty input, non-numeric token, port out of 1-65535 bounds,
        malformed range (non-digit chars, inverted endpoints), or an expanded
        result that exceeds the :data:`_PORT_SPEC_CAP` limit.
    """
    if not s or not s.strip():
        raise ValueError("port spec must not be empty")

    ports: set[int] = set()

    for raw_token in s.split(","):
        token = raw_token.strip()
        if not token:
            raise ValueError(f"empty token in port spec: {s!r}")

        if not _TOKEN_RE.match(token):
            raise ValueError(
                f"invalid port token {token!r} — expected integer or 'low-high' range"
            )

        if "-" in token:
            # Range token
            low_str, high_str = token.split("-", 1)
            low = int(low_str)
            high = int(high_str)
            if low < _PORT_MIN or low > _PORT_MAX:
                raise ValueError(
                    f"port {low} out of bounds (1–65535) in range token {token!r}"
                )
            if high < _PORT_MIN or high > _PORT_MAX:
                raise ValueError(
                    f"port {high} out of bounds (1–65535) in range token {token!r}"
                )
            if low > high:
                raise ValueError(
                    f"inverted range {token!r}: low ({low}) must be <= high ({high})"
                )
            ports.update(range(low, high + 1))
        else:
            # Bare integer token
            port = int(token)
            if port < _PORT_MIN or port > _PORT_MAX:
                raise ValueError(
                    f"port {port} out of bounds — must be in 1–65535"
                )
            ports.add(port)

        if len(ports) > _PORT_SPEC_CAP:
            raise ValueError(
                f"port spec exceeds maximum of {_PORT_SPEC_CAP} ports"
            )

    return sorted(ports)
