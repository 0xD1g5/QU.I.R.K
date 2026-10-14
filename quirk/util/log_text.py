"""Printable-text helpers for untrusted strings that reach logs or stored fields.

``safe_exc.safe_str`` is for exceptions; this is for plain strings.
Dependency-free on purpose (stdlib ``re`` only), matching the
module-independence rule in ``safe_exc``.
"""
from __future__ import annotations

import re

# C0 controls, DEL, and C1 controls.
_CTRL = re.compile(r"[\x00-\x1f\x7f\x80-\x9f]")


def strip_control_chars(value) -> str:
    """Return ``value`` as text with C0, DEL and C1 characters removed."""
    if value is None:
        return ""
    return _CTRL.sub("", str(value))
