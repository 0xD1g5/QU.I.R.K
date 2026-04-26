# Phase 29 — Kubernetes Secrets Inspection Expected Results

**Lab:** Live managed Kubernetes clusters (EKS, GKE, AKS — no Docker chaos lab analog)
**Phase:** 29 — Kubernetes Secrets Inspection
**Requirements:** K8S-01, K8S-02, K8S-03

## Lab Setup

> **Important:** Phase 29 has **no Docker chaos lab profile**. Managed Kubernetes control
> planes (EKS/GKE/AKS) cannot be replicated in a local Docker container — the encryption
> status APIs (`describe_cluster.encryptionConfig`, `databaseEncryption.state`,
> `securityProfile.azureKeyVaultKms`) only exist on real cloud-managed control planes.
> Validation is **live-cluster UAT only** — see UAT-29-01 / UAT-29-02 / UAT-29-03 in
> [docs/UAT-SERIES.md](../../docs/UAT-SERIES.md).

Earlier QU.I.R.K. phases shipped `docker compose --profile <name>` chaos labs for protocols
that work locally (BIND9 for DNSSEC, SimpleSAMLphp for SAML, Samba DC for Kerberos, MinIO for
S3). Kubernetes etcd encryption is intentionally NOT in that set — running etcd in a sidecar
does not exercise the EKS/GKE/AKS encryption APIs Phase 29 inspects.

## Scanner Configuration

Choose the provider and add the matching block to your `config.yaml`:

### EKS (AWS)

```yaml
connectors:
  enable_k8s: true
  k8s_provider: eks
  k8s_cluster_name: my-eks-cluster
  k8s_namespace: default          # for K8S-02 secret-type enumeration
  k8s_kubeconfig: ~/.kube/config  # optional — defaults to KUBECONFIG env or ~/.kube/config
  k8s_context: my-eks-context     # optional — kubeconfig context name
  aws_region: us-east-1
```

### GKE (Google Cloud)

```yaml
connectors:
  enable_k8s: true
  k8s_provider: gke
  gke_clusters:
    - location: us-central1
      name: my-gke-cluster
  k8s_namespace: default
  k8s_kubeconfig: ~/.kube/config
  k8s_context: gke_my-gcp-project_us-central1_my-gke-cluster
```

> **Note:** The `project` key is not supported per-cluster entry — only the top-level
> `gcp_project_id` parameter is used to identify the GCP project for all GKE clusters.
> Multi-project GKE scanning requires separate scan runs with different `gcp_project_id` values.

### AKS (Azure)

```yaml
connectors:
  enable_k8s: true
  k8s_provider: aks
  aks_clusters:
    - subscription_id: <azure-subscription-uuid>
      resource_group: my-rg
      name: my-aks-cluster
  k8s_namespace: default
  k8s_kubeconfig: ~/.kube/config
  k8s_context: my-aks-context
```

## Expected Scan Output

### Cluster encryption findings (K8S-01)

Each configured cluster produces one `protocol="KUBERNETES"` row describing etcd
encryption status:

| host                                   | service_detail              | severity | meaning                              |
|----------------------------------------|-----------------------------|----------|--------------------------------------|
| `aws://eks/my-eks-cluster`             | `EKS/encrypted`             | (none)   | encryptionConfig present (positive)  |
| `aws://eks/my-eks-cluster`             | `EKS/unencrypted`           | `HIGH`   | encryptionConfig empty/absent        |
| `gcp://gke/.../my-gke-cluster`         | `GKE/encrypted`             | (none)   | databaseEncryption.state == 2        |
| `gcp://gke/.../my-gke-cluster`         | `GKE/unencrypted`           | `HIGH`   | databaseEncryption.state != 2        |
| `azure://aks/.../my-aks-cluster`       | `AKS/kv-kms`                | (none)   | Key Vault KMS enabled (positive)     |
| `azure://aks/.../my-aks-cluster`       | `AKS/platform-managed`      | `MEDIUM` | securityProfile None or kms disabled |

### Secret type enumeration (K8S-02)

Per cluster (when configured `k8s_namespace` is reachable), one neutral row:

| host                                   | service_detail              | severity |
|----------------------------------------|-----------------------------|----------|
| `<cluster-host>/secrets`               | `secret-types-summary`      | (none)   |

The row's `dat_scan_json` contains type counts only — never secret values. Phase 29 Plan 02
enforces this with the assertion-based test `test_secret_type_enumeration_never_reads_data`.

### Inaccessible / RBAC-degraded findings (K8S-03)

| host                       | service_detail                       | severity |
|----------------------------|--------------------------------------|----------|
| `<cluster-host>`           | `encryption-config-inaccessible`     | `MEDIUM` |
| `<cluster-host>/secrets`   | `rbac-403`                           | `MEDIUM` |
| `<cluster-host>`           | `sdk-unavailable`                    | `MEDIUM` |

The `encryption-config-inaccessible` finding is mandatory whenever the cluster's encryption
state cannot be determined — the scanner never silently skips a configured cluster (Phase 29
Plan 02 enforces this invariant).

## Expected Evidence/Scoring Impact

Evidence summary additions:
- `dar_k8s_unencrypted_count`: count of `EKS/unencrypted` + `GKE/unencrypted` rows
- `dar_k8s_inaccessible_count`: count of `AKS/platform-managed` rows + rows with `scan_error=encryption-config-inaccessible` + rows with `scan_error=insufficient-rbac-privileges`
- `dar_k8s_unencrypted_ratio`: count / total endpoints
- `dar_k8s_inaccessible_ratio`: count / total endpoints

Readiness score impacts (balanced profile):
- `dar_k8s_unencrypted_ratio` x **10.0** weight (etcd plaintext = high impact, narrower scope than DB-wide plaintext)
- `dar_k8s_inaccessible_ratio` x **4.0** weight (compliance gap, not active weakness)
- drivers list contains `Kubernetes etcd unencrypted` or `Kubernetes etcd encryption inaccessible`

## Expected CBOM Output

KUBERNETES rows produce **no** CBOM components:
- Pass 1 (algorithms): skipped — no key material to catalog
- Pass 2 (certificates): skipped — no certificate data on these rows
- Pass 3 (protocol-properties): skipped — KUBERNETES is a configuration protocol, not TLS/SSH

The findings list includes the HIGH/MEDIUM severity entries for unencrypted/inaccessible rows.

## Limitations

- **No Docker chaos lab.** Managed K8s control planes only — see UAT-29-01/02/03 for live-cluster validation.
- **kubeconfig required for K8S-02.** Secret-type enumeration via the `kubernetes` Python
  client needs a valid kubeconfig + context. K8S-01 (encryption status) only needs cloud
  provider credentials — kubeconfig is not required for that path.
- **CMK key inspection deferred.** Phase 29 detects encryption is enabled / not enabled.
  Inspecting the actual KMS/KMS key material (e.g., AES-256 vs RSA-2048) is deferred to
  a future Cloud KMS phase or Phase 30 (Vault).
- **etcd EncryptionConfiguration is NOT a queryable K8s API resource.** This is a known
  structural constraint documented in v4.3 roadmap decisions; managed-cluster APIs are the
  only path for Phase 29.

## See Also

- [docs/UAT-SERIES.md](../../docs/UAT-SERIES.md) — UAT-29-01 (EKS), UAT-29-02 (GKE), UAT-29-03 (AKS)
- [.planning/phases/29-kubernetes-secrets-inspection/29-RESEARCH.md](../../.planning/phases/29-kubernetes-secrets-inspection/29-RESEARCH.md) — research notes
