"""Tests for GCP connector — CLOUD-03 (Phase 72).

Covers:
  - WR-04 (D-01): _scan_kms triple-nested pagination cap raises ValueError after
    MAX_KMS_PAGES iterations per loop. Parametrized 1001-page test.
  - WR-05 (D-16): _scan_kms skips both CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED
    and UNKNOWN raw algorithm strings with an INFO log naming the algorithm.
  - WR-22 (D-17 / C-3): _scan_cloud_sql surfaces the Cloud SQL instance
    description in service_detail via slash-suffix encoding.

No live GCP API required — all GCP client objects are MagicMock-built.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from quirk.scanner.gcp_connector import (
    MAX_KMS_PAGES,
    _GCP_KMS_SKIP_ALGORITHMS,
    _scan_cloud_sql,
    _scan_kms,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kms_service(pages: int, key_payload=None):
    """Build a MagicMock GCP cloudkms service that returns `pages` pagination pages.

    Outer (locations) loop is the one driven; key-rings and crypto-keys loops
    terminate after a single page each so the test exercises only the outer cap.
    """
    service = MagicMock()

    # locations: pages pagination pages; each page yields one location.
    locations_handle = MagicMock()
    service.projects.return_value.locations.return_value = locations_handle

    # Build a chain of `pages` requests. Each .execute() returns a fixed payload.
    page_requests = [MagicMock(name=f"loc_req_{i}") for i in range(pages)]
    for req in page_requests:
        req.execute.return_value = {"locations": [{"locationId": "us-central1"}]}

    locations_handle.list.return_value = page_requests[0]
    # list_next walks the chain: returns page_requests[i+1], then None at end.
    list_next_side_effect = list(page_requests[1:]) + [None]
    locations_handle.list_next.side_effect = list_next_side_effect

    # key-rings: single page with optionally one ring carrying `key_payload`.
    keyrings_handle = MagicMock()
    locations_handle.keyRings.return_value = keyrings_handle
    kr_req = MagicMock()
    if key_payload is not None:
        kr_req.execute.return_value = {
            "keyRings": [{"name": "projects/p/locations/us-central1/keyRings/r1"}]
        }
    else:
        kr_req.execute.return_value = {"keyRings": []}
    keyrings_handle.list.return_value = kr_req
    keyrings_handle.list_next.return_value = None

    # crypto-keys: single page carrying `key_payload` if provided.
    cryptokeys_handle = MagicMock()
    keyrings_handle.cryptoKeys.return_value = cryptokeys_handle
    ck_req = MagicMock()
    ck_req.execute.return_value = {"cryptoKeys": [key_payload] if key_payload else []}
    cryptokeys_handle.list.return_value = ck_req
    cryptokeys_handle.list_next.return_value = None

    return service


def _make_sql_service(instance_payload):
    """Build a MagicMock GCP sqladmin service that yields a single Cloud SQL instance."""
    service = MagicMock()
    instances_handle = MagicMock()
    service.instances.return_value = instances_handle

    req = MagicMock()
    req.execute.return_value = {"items": [instance_payload]}
    instances_handle.list.return_value = req
    instances_handle.list_next.return_value = None
    return service


# ---------------------------------------------------------------------------
# WR-04: Pagination cap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pages", [MAX_KMS_PAGES + 1])
def test_kms_pagination_cap_raises_after_1000_pages(pages):
    """1001 successive non-None locations pages must trip the MAX_KMS_PAGES cap."""
    service = _make_kms_service(pages=pages)
    # _scan_kms swallows ValueError in the outer try/except, so we patch the
    # except to re-raise by checking caplog OR we observe via logger.v sink.
    # Easier: assert via the swallow-path — collect the logger.v messages and
    # assert the exception text is logged.
    logger = MagicMock()
    results = _scan_kms(service, "my-project", logger)
    # No findings produced — the outer except logged and bailed.
    assert results == []
    # The logger.v sink received the ValueError text.
    logged_messages = " ".join(
        str(call.args[0]) if call.args else "" for call in logger.v.call_args_list
    )
    assert "exceeded 1000 pages" in logged_messages


def test_kms_pagination_under_cap_completes():
    """5 pagination pages must complete normally without raising."""
    service = _make_kms_service(pages=5)
    logger = MagicMock()
    results = _scan_kms(service, "my-project", logger)
    # No keys in payload -> empty list, but no ValueError logged.
    logged_messages = " ".join(
        str(call.args[0]) if call.args else "" for call in logger.v.call_args_list
    )
    assert "exceeded" not in logged_messages
    assert results == []


# ---------------------------------------------------------------------------
# WR-05: UNSPECIFIED / UNKNOWN skip set
# ---------------------------------------------------------------------------

def _kms_key_payload(algorithm: str, name: str = "projects/p/locations/us-central1/keyRings/r1/cryptoKeys/k1") -> dict:
    return {
        "name": name,
        "primary": {
            "state": "ENABLED",
            "algorithm": algorithm,
            "protectionLevel": "SOFTWARE",
        },
        "purpose": "ENCRYPT_DECRYPT",
    }


@pytest.mark.parametrize(
    "skip_algorithm",
    sorted(_GCP_KMS_SKIP_ALGORITHMS),
)
def test_kms_skips_unspecified_and_unknown_algorithms(caplog, skip_algorithm):
    """Both CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED and UNKNOWN keys are skipped
    with an INFO log that names the raw algorithm string."""
    caplog.set_level(logging.INFO, logger="quirk.scanner.gcp_connector")
    payload = _kms_key_payload(algorithm=skip_algorithm)
    service = _make_kms_service(pages=1, key_payload=payload)
    logger = logging.getLogger("quirk.scanner.gcp_connector")
    results = _scan_kms(service, "my-project", logger)

    assert results == [], f"expected no finding for skipped algorithm {skip_algorithm}"
    assert f"algorithm={skip_algorithm}" in caplog.text


def test_kms_emits_for_real_algorithm():
    """A real GCP KMS algorithm string must NOT be skipped (negative-of-skip)."""
    payload = _kms_key_payload(algorithm="GOOGLE_SYMMETRIC_ENCRYPTION")
    service = _make_kms_service(pages=1, key_payload=payload)
    logger = MagicMock()
    results = _scan_kms(service, "my-project", logger)
    assert len(results) == 1, "real algorithm must emit one finding"
    assert results[0].cert_pubkey_alg == "AES"
    assert results[0].cert_pubkey_size == 256


# ---------------------------------------------------------------------------
# WR-22: Cloud SQL service_detail surfaces description
# ---------------------------------------------------------------------------

def test_cloud_sql_service_detail_contains_description():
    """Cloud SQL instance description must be surfaced in CryptoEndpoint.service_detail
    via the slash-suffix encoding pattern (D-17 / C-3)."""
    instance = {
        "name": "primary-db",
        "description": "Production primary DB",
        "settings": {
            "ipConfiguration": {"sslMode": "ALLOW_UNENCRYPTED_AND_ENCRYPTED"},
        },
    }
    service = _make_sql_service(instance)
    logger = MagicMock()
    results = _scan_cloud_sql(service, "my-project", logger)

    assert len(results) == 1
    detail = results[0].service_detail
    assert detail is not None
    assert "Production-primary-DB" in detail, (
        f"expected slash-suffix-encoded instance description in service_detail, got {detail!r}"
    )
