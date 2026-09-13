#!/bin/sh
# Multi-host variant of minio-seed.sh (profile: multihost).
#
# Identical intent to the sibling script — one SSE-S3 encrypted bucket and one
# unencrypted bucket, so a scan has a genuine data-at-rest finding to report —
# but aliased to the multihost profile's own MinIO host rather than the
# single-host `minio` service. The sibling script hardcodes
# `http://minio:9000`, which is why this is a separate file rather than a
# parameter: keeping the original untouched means the storage-s3 profile's
# oracle expectations cannot be disturbed by multihost work.
set -e

mc alias set archive http://mh-storage-archive:9000 minioadmin minioadmin

mc mb --ignore-existing archive/finance-archive-encrypted
mc mb --ignore-existing archive/finance-archive-plain

# SSE-S3 auto-encryption on one bucket only. The contrast is the point: a
# scanner that reports both as "encrypted" (or both as "plaintext") is wrong,
# and this profile is meant to catch that.
mc encrypt set sse-s3 archive/finance-archive-encrypted

echo "multihost MinIO seed complete: finance-archive-encrypted (SSE-S3), finance-archive-plain (no encryption)"
