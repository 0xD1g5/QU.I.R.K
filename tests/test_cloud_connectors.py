"""Tests for AWS and Azure cloud connectors (SCAN-06, SCAN-07).

Tests mock boto3/azure SDK calls to avoid requiring cloud credentials.
Scanner modules: quirk/scanner/aws_connector.py, quirk/scanner/azure_connector.py
"""
import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

from quirk.scanner.aws_connector import scan_aws_targets
from quirk.scanner.azure_connector import scan_azure_targets


# ---- AWS Tests (SCAN-06) ----

def test_aws_acm_pagination():
    """AWS ACM connector must use paginator, not direct list_certificates (pitfall 3)."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"CertificateSummaryList": [
            {"CertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc"}
        ]}
    ]
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.describe_certificate.return_value = {
        "Certificate": {
            "CertificateArn": "arn:aws:acm:us-east-1:123:certificate/abc",
            "KeyAlgorithm": "RSA_2048",
            "DomainName": "example.com",
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client

    with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        mock_client.get_paginator.assert_called_with("list_certificates")
        assert len(endpoints) >= 1
        assert endpoints[0].protocol == "AWS"


def test_kms_key_spec_mapping():
    """KMS KeySpec must be mapped to cert_pubkey_alg correctly."""
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [
        {"Keys": [{"KeyId": "1234abcd"}]}
    ]
    mock_client = MagicMock()
    mock_client.get_paginator.return_value = mock_paginator
    mock_client.describe_key.return_value = {
        "KeyMetadata": {
            "KeyId": "1234abcd",
            "Arn": "arn:aws:kms:us-east-1:123:key/1234abcd",
            "KeySpec": "RSA_2048",
            "KeyUsage": "SIGN_VERIFY",
            "KeyState": "Enabled",
        }
    }
    mock_session = MagicMock()
    mock_session.client.return_value = mock_client

    with patch("quirk.scanner.aws_connector.boto3.Session", return_value=mock_session):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        kms_eps = [ep for ep in endpoints if ep.service_detail and "KMS" in ep.service_detail]
        assert len(kms_eps) >= 1


def test_aws_boto3_unavailable():
    """If boto3 is not importable, scan_aws_targets must return empty list."""
    with patch("quirk.scanner.aws_connector.BOTO3_AVAILABLE", False):
        endpoints = scan_aws_targets(region="us-east-1", profile=None)
        assert endpoints == []


# ---- Azure Tests (SCAN-07) ----

def test_azure_keyvault():
    """Azure Key Vault key type must produce CryptoEndpoint with protocol='AZURE'."""
    mock_key = MagicMock()
    mock_key.name = "my-rsa-key"
    mock_key.key_type = "RSA"
    mock_key.key_size = 2048
    mock_key.id = "https://myvault.vault.azure.net/keys/my-rsa-key/abc123"

    mock_key_client = MagicMock()
    mock_key_client.list_properties_of_keys.return_value = [mock_key]

    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", True), \
         patch("quirk.scanner.azure_connector.KeyClient", return_value=mock_key_client), \
         patch("quirk.scanner.azure_connector.DefaultAzureCredential"):
        endpoints = scan_azure_targets(
            subscription_id="sub-123",
            keyvault_urls=["https://myvault.vault.azure.net"]
        )
        azure_eps = [ep for ep in endpoints if ep.protocol == "AZURE"]
        assert len(azure_eps) >= 1
        assert azure_eps[0].host is not None


def test_azure_sdk_unavailable():
    """If azure SDK is not importable, scan_azure_targets must return empty list."""
    with patch("quirk.scanner.azure_connector.AZURE_AVAILABLE", False):
        endpoints = scan_azure_targets(subscription_id="sub-123", keyvault_urls=[])
        assert endpoints == []
