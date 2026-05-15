"""RED tests for STOR-02 — Azure Blob container encryption keySource detection."""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


def _make_account(name: str, key_source, rg: str = "myrg", containers=("default",)):
    account = MagicMock()
    account.name = name
    account.id = (
        f"/subscriptions/sub-1/resourceGroups/{rg}/providers/Microsoft.Storage/"
        f"storageAccounts/{name}"
    )
    if key_source is None:
        account.encryption = None
    else:
        enc = MagicMock()
        enc.key_source = key_source
        account.encryption = enc
    # store containers metadata for lookups
    account._test_containers = containers
    return account


def test_azure_blob_unavailable_returns_empty():
    from quirk.scanner.azure_connector import _scan_blob_encryption
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", False):
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
        assert result == []


def test_azure_blob_platform_managed_medium():
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("acct1", "Microsoft.Storage", containers=("c1",))
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/c1"
        container.name = "c1"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.protocol == "AZURE_BLOB"
    assert ep.service_detail == "BLOB/platform-managed"
    assert ep.severity == "MEDIUM"
    payload = json.loads(ep.dat_scan_json)
    assert payload["finding_id"] == "BLOB-PLATFORM"
    assert "Platform-managed" in payload["description"]


def test_azure_blob_absent_key_source_unknown():
    """encryption=None → BLOB/unknown (MEDIUM) — distinct from platform-managed (BLOCK-04)."""
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("acct_unknown", None)
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/c"
        container.name = "c"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "BLOB/unknown"
    assert ep.severity == "MEDIUM"
    payload = json.loads(ep.dat_scan_json)
    assert payload["finding_id"] == "BLOB-UNKNOWN"
    assert payload["key_source"] == "absent"
    assert "unavailable" in payload["description"].lower()


@pytest.mark.parametrize("key_source,expected_sd,expected_fid", [
    ("Microsoft.Keyvault", "BLOB/cmk", "BLOB-CMK"),
    ("Microsoft.Storage", "BLOB/platform-managed", "BLOB-PLATFORM"),
    (None, "BLOB/unknown", "BLOB-UNKNOWN"),
])
def test_azure_blob_finding_id_in_dat_scan_json(key_source, expected_sd, expected_fid):
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("acct_fid", key_source)
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/c"
        container.name = "c"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == expected_sd
    payload = json.loads(ep.dat_scan_json)
    assert payload["finding_id"] == expected_fid
    assert "description" in payload


def test_azure_blob_cmk_no_finding():
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("acct2", "Microsoft.Keyvault")
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/default"
        container.name = "default"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert len(result) == 1
    ep = result[0]
    assert ep.service_detail == "BLOB/cmk"
    assert getattr(ep, "severity", None) is None


def test_azure_blob_per_container_endpoint():
    """Three containers under one account → three CryptoEndpoint rows."""
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("multiacct", "Microsoft.Storage")
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        containers = []
        for n in ("c1", "c2", "c3"):
            c = MagicMock()
            c.id = f"{account.id}/blobServices/default/containers/{n}"
            c.name = n
            containers.append(c)
        client.blob_containers.list.return_value = containers
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert len(result) == 3
    names = sorted(json.loads(ep.dat_scan_json).get("container", "") for ep in result)
    assert names == ["c1", "c2", "c3"]


def test_azure_blob_session_start_propagates():
    from quirk.scanner.azure_connector import _scan_blob_encryption
    fixed = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
    account = _make_account("acct4", "Microsoft.Storage")
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/c"
        container.name = "c"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(
            credential=MagicMock(), subscription_id="s", logger=None, session_start=fixed
        )
    assert len(result) == 1
    assert result[0].scanned_at == fixed.replace(tzinfo=None)


def test_azure_blob_protocol_value():
    from quirk.scanner.azure_connector import _scan_blob_encryption
    account = _make_account("acct5", "Microsoft.Storage")
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("azure.mgmt.storage.StorageManagementClient", create=True) as mock_cls:
        client = MagicMock()
        client.storage_accounts.list.return_value = [account]
        container = MagicMock()
        container.id = f"{account.id}/blobServices/default/containers/c"
        container.name = "c"
        client.blob_containers.list.return_value = [container]
        mock_cls.return_value = client
        result = _scan_blob_encryption(credential=MagicMock(), subscription_id="s", logger=None)
    assert all(ep.protocol == "AZURE_BLOB" for ep in result)
