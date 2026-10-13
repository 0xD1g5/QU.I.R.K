# AWS Connector Setup

QU.I.R.K.'s AWS connector (`enable_aws`) discovers cryptographic material across ACM
certificates, KMS keys, CloudFront distributions, Elastic Load Balancers, and RDS instance
encryption. Two more AWS surfaces use the same boto3 credentials but are switched on separately:
S3 bucket encryption (`enable_s3`) and EKS cluster encryption (`enable_k8s` with
`k8s_provider: "eks"`).

## Minimum IAM Policy

Apply this policy to the IAM user or role QU.I.R.K. will use. The permissions map exactly to
the boto3 API calls the scanner makes — no wildcard actions, no write access.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "QuirkACMReadOnly",
      "Effect": "Allow",
      "Action": [
        "acm:ListCertificates",
        "acm:DescribeCertificate"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkKMSReadOnly",
      "Effect": "Allow",
      "Action": [
        "kms:ListKeys",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkCloudFrontReadOnly",
      "Effect": "Allow",
      "Action": [
        "cloudfront:ListDistributions"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkELBReadOnly",
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeListeners"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkRDSReadOnly",
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkEKSReadOnly",
      "Effect": "Allow",
      "Action": [
        "eks:ListClusters",
        "eks:DescribeCluster"
      ],
      "Resource": "*"
    },
    {
      "Sid": "QuirkS3EncryptionReadOnly",
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetEncryptionConfiguration"
      ],
      "Resource": "*"
    }
  ]
}
```

## Prerequisites

- AWS account with access to the target resources
- boto3 installed: it is a core dependency of `quirk-scanner`, so a normal install already
  includes it — no extra is needed
- Credentials configured (see [Credential Setup](#credential-setup) below)

## Credential Setup

QU.I.R.K. uses `boto3.Session(region_name=..., profile_name=...)` which resolves credentials
via the standard boto3 chain:

1. **Environment variables** — `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
2. **~/.aws/credentials** — named profiles (recommended for local use)
3. **IAM instance role** — for EC2 or ECS execution

For a named profile, add to `~/.aws/credentials`:

```ini
[quirk-readonly]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

## config.yaml Snippet

```yaml
connectors:
  enable_aws: true
  aws_region: "us-east-1"          # optional — defaults to "us-east-1"
  aws_profile: "quirk-readonly"    # optional — uses default credential chain if omitted
```

The `aws_profile` key is optional. If omitted, QU.I.R.K. uses the default credential chain
(environment variables, then `[default]` profile, then instance role).

To also scan S3 bucket encryption, add `enable_s3: true`; `aws_endpoint_url` is an optional S3
endpoint override for S3-compatible test servers (leave it unset for real AWS). To also scan EKS
cluster encryption, add `enable_k8s: true` and `k8s_provider: "eks"`; that check uses the same
`aws_region` and `aws_profile`.

## What Gets Scanned

| Service | Resource Type | Data Collected |
|---------|---------------|----------------|
| ACM | Certificates | Key algorithm, key size, expiry, domain names |
| KMS | Symmetric and asymmetric keys | Key spec (AES_256, RSA_2048, ECC_NIST_P256, etc.) |
| CloudFront | Distributions | Minimum TLS protocol version, associated certificate |
| ELBv2 | HTTPS/TLS listeners | SSL policy name, listener port |
| RDS | DB instances | `StorageEncrypted` flag and KMS key id — feeds the `data_at_rest` subscore |
| EKS (needs `enable_k8s` + `k8s_provider: "eks"`) | Managed clusters | etcd encryption provider, KMS key id, secrets encryption configuration — feeds the `data_at_rest` subscore |
| S3 (needs `enable_s3`) | Buckets | SSE mode (SSE-S3 / SSE-KMS / CMK / none) per `GetBucketEncryption` — feeds the `data_at_rest` subscore |

**KMS key specs recognised:** `RSA_2048`, `RSA_3072`, `RSA_4096`, `ECC_NIST_P256`,
`ECC_NIST_P384`, `ECC_NIST_P521`, `ECC_SECG_P256K1`, `SYMMETRIC_DEFAULT` (AES-256),
`HMAC_224/256/384/512`, `SM2`.

## Graceful Degradation

boto3 is a core dependency, so this only happens if it was removed from the environment. In that
case the AWS phase is skipped before the connector is called, so nothing is printed, even in
`--verbose` runs. The phase is recorded in the scan's phase-coverage records as skipped with
reason `missing-extra`. (The S3 phase, when `enable_s3` is on, does log
`boto3 not installed — S3 scanning skipped` in verbose runs.)

All other scanners (TLS, SSH, JWT) continue to run normally. Install boto3 and re-run to
include AWS results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `Unable to locate credentials` (botocore `NoCredentialsError`) in the `--verbose` log | No credentials found in chain | Set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or add profile to `~/.aws/credentials` |
| `AccessDeniedException` on `kms:DescribeKey` | Missing KMS permission | Ensure the IAM policy above is attached to the calling identity |
| Empty results for KMS | Keys exist but in different region | Update `aws_region` in `config.yaml` |
| CloudFront returns zero items | CloudFront is a global service; boto3 uses one global endpoint whatever `aws_region` is, so zero items means the account has no distributions | Confirm the credentials belong to the account that owns the distributions |
