"""Phase 77 D-10 / cbom-intel-reports/IN-04 — _PROTOCOL_KEYS extended to
include the 6 missing scanner-emitted protocol keys per RESEARCH C-10:
CONTAINER, SOURCE, AWS, AZURE, GCP, CLOUD_SQL.

KUBERNETES and VAULT are already present (regression guard).
"""
from __future__ import annotations

from quirk.intelligence.evidence import _PROTOCOL_KEYS


def test_protocol_keys_includes_phase77_d10_additions() -> None:
    expected = {"CONTAINER", "SOURCE", "AWS", "AZURE", "GCP", "CLOUD_SQL"}
    keys = set(_PROTOCOL_KEYS)
    missing = expected - keys
    assert not missing, (
        f"Phase 77 D-10: _PROTOCOL_KEYS missing required entries {sorted(missing)} "
        "(cbom-intel-reports/IN-04)"
    )


def test_protocol_keys_regression_existing_members_preserved() -> None:
    keys = set(_PROTOCOL_KEYS)
    # Regression guard for RESEARCH C-10 (KUBERNETES + VAULT already present pre-D-10)
    assert "KUBERNETES" in keys
    assert "VAULT" in keys
    # Core protocols
    for proto in ("TLS", "HTTP", "SSH", "POSTGRESQL", "MYSQL", "RDS"):
        assert proto in keys, f"regression: {proto} dropped from _PROTOCOL_KEYS"
