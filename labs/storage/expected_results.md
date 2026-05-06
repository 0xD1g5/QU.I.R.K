# Phase 28 — Object Storage Audit Expected Results

**Lab:** MinIO local S3-compatible server (Docker Compose profile `storage-s3`)
**Phase:** 28 — Object Storage Audit
**Requirements:** STOR-01

## Lab Setup

Boot the MinIO chaos profile:

```sh
cd quantum-chaos-enterprise-lab
docker compose --profile storage-s3 up -d
```

The `minio-seed` init container creates two buckets:

| Bucket               | Encryption  | Expected Finding         |
|----------------------|-------------|--------------------------|
| `encrypted-bucket`   | SSE-S3      | No finding (positive)    |
| `unencrypted-bucket` | None        | HIGH `S3/unencrypted`    |

## Scanner Configuration

Add to your `config.yaml` (or use a dedicated lab config):

```yaml
connectors:
  enable_s3: true
  aws_region: us-east-1
  aws_endpoint_url: http://localhost:29000
```

Set ambient AWS credentials to MinIO test creds:

```sh
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
```

## Expected Scan Output

```
quirk --config lab.yaml
```

Two `protocol="S3"` CryptoEndpoint rows are produced:

| host                                         | service_detail     | severity |
|----------------------------------------------|--------------------|----------|
| `arn:aws:s3:::encrypted-bucket`              | `S3/sse-s3`        | (none)   |
| `arn:aws:s3:::unencrypted-bucket`            | `S3/unencrypted`   | `HIGH`   |

## Expected Evidence/Scoring Impact

Evidence summary additions:
- `dar_storage_unencrypted_count`: 1
- `dar_storage_aws_managed_count`: 0
- `dar_storage_unencrypted_ratio`: depends on total endpoints (1 / total)

Readiness score (with these two endpoints alone, balanced profile):
- data_at_rest subscore reflects the unencrypted bucket via the
  `dar_storage_unencrypted_ratio` × 12.0 weight per D-10
- drivers list contains `Object storage unencrypted`

## Expected CBOM Output

The two S3 rows produce NO algorithm components (they have no key material). Pass 2/3 skip
them (no certificate, no TLS protocol). The findings list contains the HIGH severity entry
for `unencrypted-bucket`.

## Teardown

```sh
docker compose --profile storage-s3 down -v
```

## Limitations

- SSE-KMS validation is deferred — MinIO does not run an external KMS sidecar in this profile
  (28-CONTEXT.md Deferred Ideas).
- Azure Blob and GCS validation requires real cloud credentials; not part of this chaos lab.
