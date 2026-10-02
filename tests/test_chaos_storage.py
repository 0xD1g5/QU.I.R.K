"""Integration tests for Phase 28 S3 chaos lab (D-08).

Phase 220 D-01R: the lab's S3 server is moto (motoserver/moto), no longer MinIO; the
`minio`/`minio-seed` service names and minioadmin creds are kept as historical names.

These tests run only with `pytest -m integration`. They require Docker and the
storage-s3 compose profile to be running (`docker compose --profile storage-s3 up -d`).
"""
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


LAB_DIR = Path(__file__).resolve().parent.parent / "quantum-chaos-enterprise-lab"
SEED_SCRIPT = LAB_DIR / "storage" / "s3-seed.py"


def test_minio_seed_script_exists():
    assert SEED_SCRIPT.is_file(), f"Expected S3 (moto) seed script at {SEED_SCRIPT}"


def test_minio_seed_creates_two_buckets():
    """The seed must create encrypted-bucket (SSE-S3) and unencrypted-bucket (plain).

    Phase 220 D-01R: s3-seed.py is generic (bucket specs arrive as argv), so the
    bucket names are asserted on the compose entrypoint that invokes it, and the
    SSE-S3 behaviour on the script itself.
    """
    assert SEED_SCRIPT.is_file()
    text = SEED_SCRIPT.read_text()
    assert "create_bucket" in text
    assert "put_bucket_encryption" in text
    assert '"SSEAlgorithm": "AES256"' in text
    compose = (LAB_DIR / "docker-compose.yml").read_text()
    assert (
        '"http://minio:9000", "encrypted-bucket:sse", "unencrypted-bucket:plain"'
        in compose
    )
    assert (
        '"http://mh-storage-archive:9000", "finance-archive-encrypted:sse", '
        '"finance-archive-plain:plain"' in compose
    )


def test_minio_compose_profile_storage_s3():
    """docker-compose.yml must declare a storage-s3 profile with minio + minio-seed."""
    compose = (LAB_DIR / "docker-compose.yml").read_text()
    # Phase 220 D-01R: MinIO's images are unpullable from every channel (Docker Hub
    # 404, quay.io 401, dl.min.io 410) and the GHCR mirror plan (ghcr.io/0xd1g5/...)
    # died with the local cache it depended on, so the S3 services run moto. Assert
    # the moto prefix (version-agnostic; the tag is pinned in compose) AND the
    # absence of both retired MinIO image sources, so a regression to either one
    # fails loudly instead of passing on a stale substring.
    assert "motoserver/moto:" in compose
    assert "ghcr.io/0xd1g5/" not in compose
    assert "quay.io/minio/" not in compose
    assert "storage-s3" in compose
    assert "minio-seed" in compose


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("QUIRK_RUN_DOCKER_IT"),
    reason="Set QUIRK_RUN_DOCKER_IT=1 to run live Docker integration",
)
def test_minio_unencrypted_bucket_produces_high_finding():
    """Live S3 (moto) scan: unencrypted-bucket → HIGH finding via _scan_s3_encryption."""
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


@pytest.mark.slow
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
