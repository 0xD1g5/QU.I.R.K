# GCP Connector Setup

QU.I.R.K.'s GCP connector (`enable_gcp`) discovers cryptographic material in one GCP project: Cloud
KMS keys, Cloud SQL TLS enforcement, and Cloud Storage bucket encryption.

## Minimum IAM Permissions

The connector only issues list calls: Cloud KMS locations, key rings and crypto keys, Cloud SQL
instances, and Cloud Storage buckets. Grant the identity QU.I.R.K. runs as these predefined roles
on the project:

| Service | List call the connector makes | Predefined role |
|---------|-------------------------------|------------------|
| Cloud KMS | `cloudkms.locations.list`, `cloudkms.keyRings.list`, `cloudkms.cryptoKeys.list` | `roles/cloudkms.viewer` |
| Cloud SQL | `cloudsql.instances.list` | `roles/cloudsql.viewer` |
| Cloud Storage | `storage.buckets.list` | `roles/storage.viewer` |

> **Note:** `roles/storage.objectViewer`, which the connector's source docstring names, does not
> include `storage.buckets.list`; the Cloud Storage scan would be denied with only that role.

## Prerequisites

- A GCP project ID
- `google-api-python-client` installed; it ships in the `cloud` extra, which `[all]` includes:

  ```bash
  pip install 'quirk-scanner[cloud]'
  ```

- Application Default Credentials available to the QU.I.R.K. process (see
  [Credential Setup](#credential-setup) below)

## Credential Setup

QU.I.R.K. obtains credentials with `google.auth.default()` and the `cloud-platform` scope, so it
uses Application Default Credentials (ADC). ADC searches, in order:

1. The `GOOGLE_APPLICATION_CREDENTIALS` environment variable (path to a credential JSON file)
2. A credential file created by `gcloud auth application-default login`
3. The service account attached to the compute resource, returned by the metadata server

No credentials are stored in `config.yaml`.

## config.yaml Snippet

```yaml
connectors:
  enable_gcp: true
  gcp_project_id: "my-gcp-project"   # required — the GCP phase is skipped when empty
```

## What Gets Scanned

| Service | Resource Type | Data Collected |
|---------|---------------|----------------|
| Cloud KMS | Crypto keys in every location | The primary version's algorithm mapped to algorithm and key size (including the post-quantum algorithms ML-KEM and ML-DSA), and the protection level (`SOFTWARE`, `HSM`, `EXTERNAL`, ...). Keys whose primary version is not `ENABLED`, or whose algorithm is unspecified, are skipped |
| Cloud SQL | Instances | `settings.ipConfiguration.sslMode`: `ALLOW_UNENCRYPTED_AND_ENCRYPTED` (or unset) is HIGH, `ENCRYPTED_ONLY` is MEDIUM, `TRUSTED_CLIENT_CERTIFICATE_REQUIRED` produces no finding |
| Cloud Storage | Buckets | CMEK (a `defaultKmsKeyName` is set) versus Google-managed encryption per bucket, plus one summary record carrying the bucket list |

KMS locations are discovered automatically with the Cloud KMS locations list; no location setting
is needed.

## Graceful Degradation

If `google-api-python-client` is not installed, the GCP phase is skipped before the connector is
called and is recorded in the scan's phase-coverage records as skipped with reason `missing-extra`.
Every scan with `enable_gcp` on, verbose or not, prints a line to stderr that begins
`[QRK-INSTALL-001] Optional scanner package not installed.`, and the scan records an advisory row
whose message begins `GCP / Kubernetes / HashiCorp Vault scanning skipped`. The install command
that follows in both messages names the wrong package; install the `cloud` extra as shown in
Prerequisites instead.

If no Application Default Credentials can be found, the connector returns a single endpoint whose
scan error begins `gcp-credentials-unavailable:`. All other scanners continue to run normally.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `gcp-credentials-unavailable:` scan error | No Application Default Credentials | Run `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS` |
| `gcp-iam-denied:storage:` scan error | The identity lacks `storage.buckets.list` | Grant `roles/storage.viewer` (not `roles/storage.objectViewer`) |
| `gcp-iam-denied:cloudkms:` or `gcp-iam-denied:sqladmin:` scan error | The identity lacks the Cloud KMS or Cloud SQL viewer role | Grant `roles/cloudkms.viewer` or `roles/cloudsql.viewer` |
| GCP phase skipped with `connectors.gcp_project_id is empty` | `gcp_project_id` not set | Add `gcp_project_id` to `config.yaml` |
