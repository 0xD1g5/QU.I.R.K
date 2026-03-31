# AWS Connector Setup

QU.I.R.K.'s AWS connector discovers cryptographic material across ACM certificates, KMS keys,
CloudFront distributions, and Elastic Load Balancers.

## Minimum IAM Policy

Apply this policy to the IAM user or role QU.I.R.K. will use. The permissions map exactly to
the boto3 API calls the scanner makes — no wildcards, no write access.

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
    }
  ]
}
```

## Prerequisites

- AWS account with access to the target resources
- boto3 installed: included automatically when you install `quirk` with the `[dashboard]` extra;
  otherwise `pip install boto3`
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
  aws_region: "us-east-1"          # required — set to your target region
  aws_profile: "quirk-readonly"    # optional — uses default credential chain if omitted
```

The `aws_profile` key is optional. If omitted, QU.I.R.K. uses the default credential chain
(environment variables, then `[default]` profile, then instance role).

## What Gets Scanned

| Service | Resource Type | Data Collected |
|---------|---------------|----------------|
| ACM | Certificates | Key algorithm, key size, expiry, domain names |
| KMS | Symmetric and asymmetric keys | Key spec (AES_256, RSA_2048, ECC_NIST_P256, etc.) |
| CloudFront | Distributions | Minimum TLS protocol version, associated certificate |
| ELBv2 | HTTPS/TLS listeners | SSL policy name, listener port |

**KMS key specs recognised:** `RSA_2048`, `RSA_3072`, `RSA_4096`, `ECC_NIST_P256`,
`ECC_NIST_P384`, `ECC_NIST_P521`, `ECC_SECG_P256K1`, `SYMMETRIC_DEFAULT` (AES-256),
`HMAC_224/256/384/512`.

## Graceful Degradation

If boto3 is not installed, the AWS connector returns an empty result set and logs:

```
boto3 not installed — AWS scanning unavailable
```

All other scanners (TLS, SSH, JWT) continue to run normally. Install boto3 and re-run to
include AWS results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `NoCredentialsError` | No credentials found in chain | Set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, or add profile to `~/.aws/credentials` |
| `AccessDeniedException` on `kms:DescribeKey` | Missing KMS permission | Ensure the IAM policy above is attached to the calling identity |
| Empty results for KMS | Keys exist but in different region | Update `aws_region` in `config.yaml` |
| CloudFront returns zero items | CloudFront is a global service but your region must be `us-east-1` for the API | Set `aws_region: "us-east-1"` |
