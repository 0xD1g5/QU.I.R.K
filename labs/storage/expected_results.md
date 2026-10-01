# Phase 28 — Object Storage Audit Expected Results

**Lab:** moto local S3-compatible server (`motoserver/moto:5.2.3`; MinIO until Phase 220 D-01R, 2026-10-01) (Docker Compose profile `storage-s3`)
**Phase:** 28 — Object Storage Audit
**Requirements:** STOR-01

## Lab Setup

Boot the S3 chaos profile (the `minio` service name is historical; it runs moto):

```sh
cd quantum-chaos-enterprise-lab
docker compose --profile storage-s3 up -d
```

The `minio-seed` init container runs `quantum-chaos-enterprise-lab/storage/s3-seed.py` (boto3) and creates two buckets:

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

Set ambient AWS credentials to the lab's test creds (historical MinIO-era values, accepted by moto):

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

- SSE-KMS validation is deferred — the profile's S3 server (moto since Phase 220; MinIO before) is
  not wired to a KMS in this profile (28-CONTEXT.md Deferred Ideas).
- Azure Blob and GCS validation requires real cloud credentials; not part of this chaos lab.
