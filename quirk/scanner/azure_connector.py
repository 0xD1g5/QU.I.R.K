"""Azure cloud connector for cryptographic resource enumeration (SCAN-07).

Scans Key Vault keys and App Gateway TLS policies.
Uses DefaultAzureCredential for ambient auth — no credentials stored.
Degrades gracefully when azure SDK is not installed.
"""
from __future__ import annotations

import json
from typing import List, Optional

from quirk.models import CryptoEndpoint

# ---------------------------------------------------------------------------
# azure SDK optional import (D-16, D-18)
# Names must remain at module level (even as None) for test patching.
# ---------------------------------------------------------------------------
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.keys import KeyClient
    from azure.keyvault.certificates import CertificateClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    DefaultAzureCredential = None  # type: ignore[assignment,misc]
    KeyClient = None  # type: ignore[assignment,misc]
    CertificateClient = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Azure Key Type -> (algorithm, key_size_hint) mapping
# Actual key_size comes from key properties when available.
# ---------------------------------------------------------------------------
AZURE_KEY_TYPE_MAP = {
    "RSA": ("RSA", None),
    "RSA-HSM": ("RSA", None),
    "EC": ("ECDSA", None),
    "EC-HSM": ("ECDSA", None),
    "oct": ("AES", None),
    "oct-HSM": ("AES", None),
}


def _scan_keyvault_keys(credential, vault_url: str, logger) -> List[CryptoEndpoint]:
    """Enumerate Key Vault keys and map to CryptoEndpoint instances."""
    results: List[CryptoEndpoint] = []
    try:
        client = KeyClient(vault_url, credential)
        for key in client.list_properties_of_keys():
            try:
                key_type_str = str(key.key_type) if key.key_type is not None else ""
                alg_name, _ = AZURE_KEY_TYPE_MAP.get(key_type_str, (key_type_str, None))
                key_size = getattr(key, "key_size", None)
                host = key.id if key.id else vault_url
                cloud_data = {
                    "name": key.name,
                    "key_type": key_type_str,
                    "key_size": key_size,
                    "vault_url": vault_url,
                }
                ep = CryptoEndpoint(
                    host=host,
                    port=0,
                    protocol="AZURE",
                    cert_pubkey_alg=alg_name,
                    cert_pubkey_size=key_size,
                    cloud_scan_json=json.dumps(cloud_data, default=str),
                    service_detail="KeyVault",
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"KeyVault key scan error for key in {vault_url}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"KeyVault scan error for {vault_url}: {exc}")
    return results


def _scan_app_gateways(credential, subscription_id: str, logger) -> List[CryptoEndpoint]:
    """Enumerate Azure Application Gateways and capture TLS policy info."""
    results: List[CryptoEndpoint] = []
    try:
        from azure.mgmt.network import NetworkManagementClient  # type: ignore[import-untyped]
        client = NetworkManagementClient(credential, subscription_id)
        for gateway in client.application_gateways.list_all():
            try:
                ssl_policy = getattr(gateway, "ssl_policy", None)
                if ssl_policy is None:
                    continue
                min_proto = getattr(ssl_policy, "min_protocol_version", None)
                cipher_suites = getattr(ssl_policy, "cipher_suites", None)
                policy_name = getattr(ssl_policy, "policy_name", None)
                ssl_policy_dict = {
                    "min_protocol_version": str(min_proto) if min_proto else None,
                    "cipher_suites": [str(c) for c in (cipher_suites or [])],
                    "policy_name": str(policy_name) if policy_name else None,
                }
                ep = CryptoEndpoint(
                    host=gateway.id,
                    port=443,
                    protocol="AZURE",
                    tls_version=str(min_proto) if min_proto else None,
                    cloud_scan_json=json.dumps(ssl_policy_dict, default=str),
                    service_detail="AppGateway",
                )
                results.append(ep)
            except Exception as exc:
                if logger:
                    logger.v(f"AppGateway policy scan error: {exc}")
    except ImportError:
        if logger:
            logger.v("azure-mgmt-network not installed — App Gateway scanning unavailable")
    except Exception as exc:
        if logger:
            logger.v(f"App Gateway scan error: {exc}")
    return results


def scan_azure_targets(
    subscription_id: str,
    keyvault_urls: Optional[List[str]] = None,
    logger=None,
) -> List[CryptoEndpoint]:
    """Enumerate Azure cryptographic resources and return as CryptoEndpoint list.

    Scans: Key Vault keys, App Gateway TLS policies.

    Args:
        subscription_id: Azure subscription UUID string.
        keyvault_urls: List of Key Vault base URLs (e.g. "https://myvault.vault.azure.net").
        logger: Optional logger with .v() method.

    Returns:
        List of CryptoEndpoint instances. Empty list if azure SDK not installed.
    """
    if not AZURE_AVAILABLE:
        if logger:
            logger.v("azure SDK not installed — Azure scanning unavailable")
        return []
    credential = DefaultAzureCredential()
    results: List[CryptoEndpoint] = []
    for vault_url in (keyvault_urls or []):
        results.extend(_scan_keyvault_keys(credential, vault_url, logger))
    if subscription_id:
        results.extend(_scan_app_gateways(credential, subscription_id, logger))
    return results
