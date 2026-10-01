"""Seed the chaos lab's moto S3 emulator with one SSE-S3 bucket and one plain bucket.

Phase 220 (D-01R): replaces storage/minio-seed.sh and storage/minio-seed-multihost.sh,
which used the MinIO `mc` client image. MinIO's images are no longer pullable from any
registry, so the lab's S3 services now run motoserver/moto, and this script runs inside
that same image (it ships python + boto3), so no separate client image is needed.

Usage:
    python s3-seed.py <endpoint-url> <bucket>:<sse|plain> [<bucket>:<sse|plain> ...]

    sse    create the bucket and set default SSE-S3 (AES256) encryption
           (validates the scanner's no-finding path)
    plain  create the bucket with no encryption configuration
           (validates the scanner's HIGH S3/unencrypted finding path)

Credentials come from AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (default: the lab's
historical minioadmin/minioadmin). Region is us-east-1. moto keeps state in memory,
so this must re-run on every `up`; it is idempotent (an existing bucket is fine).
"""

import os
import sys
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

_READY_TIMEOUT_S = 30
_ALREADY_EXISTS = {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}


def _parse_specs(args):
    specs = []
    for arg in args:
        name, sep, mode = arg.partition(":")
        if not sep or not name or mode not in ("sse", "plain"):
            raise ValueError(f"bad bucket spec {arg!r}; expected <bucket>:<sse|plain>")
        specs.append((name, mode))
    return specs


def _wait_ready(client):
    deadline = time.monotonic() + _READY_TIMEOUT_S
    while True:
        try:
            client.list_buckets()
            return
        except (EndpointConnectionError, ConnectionError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)


def _create_bucket(client, name):
    try:
        client.create_bucket(Bucket=name)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in _ALREADY_EXISTS:
            raise


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    endpoint = argv[1]
    try:
        specs = _parse_specs(argv[2:])
    except ValueError as exc:
        print(f"s3-seed: {exc}", file=sys.stderr)
        return 2

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    try:
        _wait_ready(client)
        for name, mode in specs:
            _create_bucket(client, name)
            if mode == "sse":
                client.put_bucket_encryption(
                    Bucket=name,
                    ServerSideEncryptionConfiguration={
                        "Rules": [
                            {
                                "ApplyServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        ]
                    },
                )
    except Exception as exc:  # noqa: BLE001 - any failure must fail the seed container
        print(f"s3-seed: FAILED against {endpoint}: {exc}", file=sys.stderr)
        return 1

    summary = ", ".join(
        f"{name} ({'SSE-S3' if mode == 'sse' else 'no encryption'})"
        for name, mode in specs
    )
    print(f"S3 (moto) seed complete at {endpoint}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
