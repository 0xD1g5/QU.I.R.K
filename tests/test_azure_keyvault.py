"""Phase 72 / CLOUD-02 / WR-03 (D-12): Azure KeyVault key_size population.

Verifies that `_scan_keyvault_keys` populates `key_size` correctly per key
type rather than uniformly returning None:

  - RSA  → key.n.bit_length()
  - EC   → curve-name lookup in _AZURE_EC_CURVE_SIZES
  - OCT  → key.key_size (existing field)
  - Unknown / unrecognized key_type → None (log at DEBUG via logger.v)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _make_keyvault_key(
    *,
    name: str = "k",
    key_type: str = "RSA",
    n_bit_length: int | None = None,
    crv: str | None = None,
    key_size: int | None = None,
    kid: str | None = None,
):
    """Build a mock KeyVault key/properties object exposing the attributes the
    connector inspects (.key_type, .name, .id, .n, .crv, .key_size)."""
    key = MagicMock()
    key.key_type = key_type
    key.name = name
    key.id = kid or f"https://vault.azure.net/keys/{name}"
    if n_bit_length is not None:
        n = MagicMock()
        n.bit_length.return_value = n_bit_length
        key.n = n
    else:
        # Ensure .n is absent (so getattr(key, "n", None) returns None).
        del key.n
    if crv is not None:
        key.crv = crv
    else:
        del key.crv
    # Curve fallback name (some SDK shapes expose .curve)
    try:
        del key.curve
    except AttributeError:
        pass
    if key_size is not None:
        key.key_size = key_size
    else:
        # Some test cases want getattr(key, "key_size", None) → None.
        try:
            del key.key_size
        except AttributeError:
            pass
    return key


def _scan(keys):
    """Invoke _scan_keyvault_keys with a stubbed KeyClient yielding `keys`."""
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True):
        from quirk.scanner import azure_connector
        mock_client = MagicMock()
        mock_client.list_properties_of_keys.return_value = iter(keys)
        with patch.object(
            azure_connector, "KeyClient", return_value=mock_client
        ):
            return azure_connector._scan_keyvault_keys(
                credential=MagicMock(),
                vault_url="https://vault.azure.net",
                logger=None,
            )


def test_keyvault_rsa_key_size_populated():
    """RSA key: key_size derived from key.n.bit_length() (D-12)."""
    keys = [_make_keyvault_key(key_type="RSA", n_bit_length=2048)]
    results = _scan(keys)
    assert len(results) == 1
    ep = results[0]
    assert ep.cert_pubkey_alg == "RSA"
    assert ep.cert_pubkey_size == 2048
    payload = json.loads(ep.cloud_scan_json)
    assert payload["key_size"] == 2048


def test_keyvault_rsa_hsm_key_size_populated():
    """RSA-HSM also follows the RSA branch (kt contains 'rsa')."""
    keys = [_make_keyvault_key(key_type="RSA-HSM", n_bit_length=4096)]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 4096


def test_keyvault_ec_p256_key_size():
    """EC P-256 curve → key_size 256 (D-12)."""
    keys = [_make_keyvault_key(key_type="EC", crv="P-256")]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 256


def test_keyvault_ec_p384_key_size():
    keys = [_make_keyvault_key(key_type="EC", crv="P-384")]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 384


def test_keyvault_ec_p521_key_size():
    keys = [_make_keyvault_key(key_type="EC", crv="P-521")]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 521


def test_keyvault_ec_secp256k1_key_size():
    keys = [_make_keyvault_key(key_type="EC-HSM", crv="secp256k1")]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 256


def test_keyvault_oct_key_size():
    """OCT (symmetric) key: key_size comes from properties.key_size."""
    keys = [_make_keyvault_key(key_type="oct", key_size=256)]
    results = _scan(keys)
    assert results[0].cert_pubkey_size == 256


def test_keyvault_unknown_key_type_leaves_none():
    """Unknown key_type → key_size remains None, logger.v emitted at DEBUG."""
    keys = [_make_keyvault_key(key_type="foo")]
    logger = MagicMock()
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True):
        from quirk.scanner import azure_connector
        mock_client = MagicMock()
        mock_client.list_properties_of_keys.return_value = iter(keys)
        with patch.object(
            azure_connector, "KeyClient", return_value=mock_client
        ):
            results = azure_connector._scan_keyvault_keys(
                credential=MagicMock(),
                vault_url="https://vault.azure.net",
                logger=logger,
            )
    assert len(results) == 1
    assert results[0].cert_pubkey_size is None
    # logger.v called for the unknown-key-type DEBUG log
    assert logger.v.call_count >= 1


def test_keyvault_ec_unknown_curve_leaves_none():
    """EC key with curve not in _AZURE_EC_CURVE_SIZES → key_size None."""
    keys = [_make_keyvault_key(key_type="EC", crv="P-999")]
    results = _scan(keys)
    assert results[0].cert_pubkey_size is None


# ---------------------------------------------------------------------------
# Phase 235.3 (COVTRUTH-01): per-target outcome recording
# ---------------------------------------------------------------------------

import pytest  # noqa: E402

from quirk.scanner.target_outcome import (  # noqa: E402
    TargetOutcomeContractError,
    TargetOutcomes,
)

_VAULT = "https://vault.azure.net"


# Stubs carry the exact class names the classifier matches by (no azure import).
class CredentialUnavailableError(Exception):
    pass


class ClientAuthenticationError(Exception):
    pass


class ServiceRequestError(Exception):
    pass


def _kv_with(effect_or_keys, outcomes, vault_url=_VAULT):
    from quirk.scanner import azure_connector
    client = MagicMock()
    if isinstance(effect_or_keys, Exception):
        client.list_properties_of_keys.side_effect = effect_or_keys
    else:
        client.list_properties_of_keys.return_value = iter(effect_or_keys)
    with patch.object(azure_connector, "KeyClient", return_value=client):
        return azure_connector._scan_keyvault_keys(
            MagicMock(), vault_url, None, outcomes=outcomes
        )


@pytest.mark.parametrize(
    "exc, kind",
    [
        (CredentialUnavailableError("no cred"), "missing_credentials"),
        (ClientAuthenticationError("bad token"), "auth_failed"),
        (ServiceRequestError("conn refused"), "unreachable"),
    ],
)
def test_keyvault_outcome_failure_kinds(exc, kind):
    sink = TargetOutcomes([_VAULT])
    assert _kv_with(exc, sink) == []
    (o,) = sink.resolved()
    assert o.kind == kind


def test_keyvault_outcome_zero_keys_answered():
    sink = TargetOutcomes([_VAULT])
    _kv_with([], sink)
    (o,) = sink.resolved()
    assert o.kind == "answered"


def test_keyvault_outcome_none_sink_unchanged():
    results = _kv_with([_make_keyvault_key(key_type="RSA", n_bit_length=2048)], None)
    assert len(results) == 1


def test_keyvault_outcome_contract_violation_propagates():
    sink = TargetOutcomes(["not-this-target"])
    with pytest.raises(TargetOutcomeContractError):
        _kv_with([], sink)
    sink2 = TargetOutcomes(["not-this-target"])
    with pytest.raises(TargetOutcomeContractError):
        _kv_with(ServiceRequestError("x"), sink2)


def test_scan_azure_targets_outcome_labels_exact_and_hermetic(monkeypatch):
    """One answered per configured target (vault URLs + subscription), no extras;
    DefaultAzureCredential is stubbed so no real credential chain runs."""
    from quirk.scanner import azure_connector
    sub = "sub-0000"
    sink = TargetOutcomes([_VAULT, sub])
    client = MagicMock()
    client.list_properties_of_keys.return_value = iter([])
    net = MagicMock()
    net.application_gateways.list_all.return_value = []
    fake_net_mod = MagicMock()
    fake_net_mod.NetworkManagementClient.return_value = net
    monkeypatch.setitem(__import__("sys").modules, "azure.mgmt.network", fake_net_mod)
    with patch.object(azure_connector, "AZURE_AVAILABLE", True), \
         patch.object(azure_connector, "DefaultAzureCredential", return_value=MagicMock()), \
         patch.object(azure_connector, "KeyClient", return_value=client):
        azure_connector.scan_azure_targets(sub, [_VAULT], None, outcomes=sink)
    out = sink.resolved()
    assert len(out) == 2
    assert all(o.kind == "answered" for o in out)


def test_scan_azure_targets_credential_construction_failure_recorded():
    from quirk.scanner import azure_connector
    sink = TargetOutcomes([_VAULT])
    with patch.object(azure_connector, "AZURE_AVAILABLE", True), \
         patch.object(
             azure_connector, "DefaultAzureCredential",
             side_effect=CredentialUnavailableError("none"),
         ):
        assert azure_connector.scan_azure_targets("", [_VAULT], None, outcomes=sink) == []
    assert sink.resolved()[0].kind == "missing_credentials"


def test_app_gateway_outcome_zero_gateways_answered_and_failure(monkeypatch):
    from quirk.scanner import azure_connector
    net = MagicMock()
    net.application_gateways.list_all.return_value = []
    mod = MagicMock()
    mod.NetworkManagementClient.return_value = net
    monkeypatch.setitem(__import__("sys").modules, "azure.mgmt.network", mod)
    sink = TargetOutcomes(["sub-1"])
    azure_connector._scan_app_gateways(MagicMock(), "sub-1", None, outcomes=sink)
    assert sink.resolved()[0].kind == "answered"

    net.application_gateways.list_all.side_effect = ClientAuthenticationError("401")
    sink2 = TargetOutcomes(["sub-1"])
    azure_connector._scan_app_gateways(MagicMock(), "sub-1", None, outcomes=sink2)
    assert sink2.resolved()[0].kind == "auth_failed"
