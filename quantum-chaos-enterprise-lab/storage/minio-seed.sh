#!/bin/sh
# MinIO seed script — Phase 28 (D-08): create encrypted-bucket (SSE-S3) and unencrypted-bucket
# Used by docker-compose storage-s3 profile minio-seed init container
set -e

# Wait for MinIO to be ready (mc alias retries automatically)
mc alias set local http://minio:9000 minioadmin minioadmin

# Create both buckets
mc mb local/encrypted-bucket --ignore-existing
mc mb local/unencrypted-bucket --ignore-existing

# Enable SSE-S3 on encrypted-bucket (validates no-finding path + ThreadPoolExecutor enumeration)
mc encrypt set sse-s3 local/encrypted-bucket

# unencrypted-bucket intentionally left without encryption policy (validates HIGH finding path)
echo "MinIO seed complete: encrypted-bucket (SSE-S3), unencrypted-bucket (no encryption)"
