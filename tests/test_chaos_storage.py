"""Integration tests for Phase 28 MinIO chaos lab (D-08).

These tests run only with `pytest -m integration`. They require Docker and the
storage-s3 compose profile to be running (`docker compose --profile storage-s3 up -d`).
"""
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


LAB_DIR = Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
SEED_SCRIPT = LAB_DIR / "storage" / "minio-seed.sh"


def test_minio_seed_script_exists():
    assert SEED_SCRIPT.is_file(), f"Expected MinIO seed script at {SEED_SCRIPT}"


def test_minio_seed_creates_two_buckets():
    """The seed script must create both encrypted-bucket and unencrypted-bucket."""
    assert SEED_SCRIPT.is_file()
    text = SEED_SCRIPT.read_text()
    assert "mc mb local/encrypted-bucket" in text
    assert "mc mb local/unencrypted-bucket" in text
    assert "mc encrypt set sse-s3 local/encrypted-bucket" in text


def test_minio_compose_profile_storage_s3():
    """docker-compose.yml must declare a storage-s3 profile with minio + minio-seed."""
    compose = (LAB_DIR / "docker-compose.yml").read_text()
    assert "minio/minio:latest" in compose
    assert "storage-s3" in compose
    assert "minio-seed" in compose


@pytest.mark.skipif(
    not os.environ.get("QUIRK_RUN_DOCKER_IT"),
    reason="Set QUIRK_RUN_DOCKER_IT=1 to run live Docker integration",
)
def test_minio_unencrypted_bucket_produces_high_finding():
    """Live MinIO scan: unencrypted-bucket → HIGH finding via _scan_s3_encryption."""
    # This test assumes `docker compose --profile storage-s3 up -d` has run successfully.
    # It is gated behind QUIRK_RUN_DOCKER_IT to keep CI deterministic.
    import boto3
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session = boto3.Session(
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    )
    result = _scan_s3_encryption(
        session=session,
        logger=None,
        endpoint_url="http://localhost:29000",
    )
    unencrypted = [ep for ep in result if "unencrypted-bucket" in (ep.host or "")]
    assert len(unencrypted) == 1
    assert unencrypted[0].severity == "HIGH"
    assert "S3/unencrypted" in unencrypted[0].service_detail


@pytest.mark.skipif(
    not os.environ.get("QUIRK_RUN_DOCKER_IT"),
    reason="Set QUIRK_RUN_DOCKER_IT=1 to run live Docker integration",
)
def test_minio_encrypted_bucket_no_finding():
    import boto3
    from quirk.scanner.aws_connector import _scan_s3_encryption
    session = boto3.Session(
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
        region_name="us-east-1",
    )
    result = _scan_s3_encryption(
        session=session,
        logger=None,
        endpoint_url="http://localhost:29000",
    )
    encrypted = [ep for ep in result if "encrypted-bucket" in (ep.host or "") and "unencrypted" not in (ep.host or "")]
    assert len(encrypted) == 1
    # SSE-S3 means service_detail starts with S3/sse-s3 and no severity
    assert encrypted[0].service_detail == "S3/sse-s3"
    assert getattr(encrypted[0], "severity", None) is None
