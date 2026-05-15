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
