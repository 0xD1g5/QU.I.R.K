"""Phase 193 review CR-03 -- documented "default" host-slot fallback.

The dashboard's single-slot credential UI files broker/SNMPv3 credentials
under the literal host key ``"default"``. Every consumer must fall back to
that entry when no host-specific entry exists, otherwise the UI promises
delivery it cannot perform (the original CR-03 defect). These tests pin the
fallback at a real consumer call site (``hardware_scanner``'s
bridge-evidence ARP walk), asserting both directions:

- a host with NO host-specific entry receives the ``"default"`` credential;
- a host WITH a host-specific entry keeps its own (default never shadows).
"""
from __future__ import annotations

from types import SimpleNamespace

import quirk.scanner.hardware_scanner as hardware_scanner
from quirk.config import SnmpV3Credential


def _capture_walk(calls):
    def _walk_arp_table(host, community=None, timeout=None, v3_credential=None):
        calls.append({"host": host, "community": community, "v3_credential": v3_credential})
        return []  # empty -> _confirm_bridge_evidence exits without persisting

    return _walk_arp_table


def _cfg_with_creds(creds_map):
    return SimpleNamespace(
        connectors=SimpleNamespace(
            snmp_v3_credentials=creds_map,
            snmp_community="public",
            _user_set_fields=frozenset(),
        )
    )


def test_default_v3_credential_used_when_no_host_specific_entry(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "quirk.scanner.snmp_scanner.walk_arp_table", _capture_walk(calls)
    )
    default_cred = SnmpV3Credential(username="ops", auth_key_env="QUIRK_JOB_SNMPV3_DEFAULT_AUTH")
    device = SimpleNamespace(host="10.0.0.7", bridge_evidence_json=None, bridge_confirmed_at=None)

    hardware_scanner._confirm_bridge_evidence(
        device, timeout=1, cfg=_cfg_with_creds({"default": default_cred})
    )

    assert len(calls) == 1
    assert calls[0]["v3_credential"] is default_cred


def test_host_specific_v3_credential_wins_over_default(monkeypatch):
    calls: list = []
    monkeypatch.setattr(
        "quirk.scanner.snmp_scanner.walk_arp_table", _capture_walk(calls)
    )
    default_cred = SnmpV3Credential(username="ops", auth_key_env="ENV_DEFAULT")
    host_cred = SnmpV3Credential(username="host-ops", auth_key_env="ENV_HOST")
    device = SimpleNamespace(host="10.0.0.7", bridge_evidence_json=None, bridge_confirmed_at=None)

    hardware_scanner._confirm_bridge_evidence(
        device,
        timeout=1,
        cfg=_cfg_with_creds({"default": default_cred, "10.0.0.7": host_cred}),
    )

    assert len(calls) == 1
    assert calls[0]["v3_credential"] is host_cred
