# Kubernetes Connector Setup

QU.I.R.K.'s Kubernetes connector (`enable_k8s`) checks the encryption posture of managed Kubernetes
clusters (EKS, GKE, AKS) and counts the secret types in one namespace. It never reads secret
values.

## Minimum Permissions

| Provider | What the connector calls | Permission to grant |
|----------|--------------------------|---------------------|
| GKE | `ClusterManagerClient.get_cluster` for each cluster in `gke_clusters` | `roles/container.clusterViewer` (includes `container.clusters.get`) |
| AKS | `managed_clusters.get` for each cluster in `aks_clusters` | Azure `Reader` at the subscription or resource group (its `*/read` action covers cluster reads) |
| EKS | `eks:ListClusters` and `eks:DescribeCluster` through boto3 | See [AWS Connector Setup](aws.md) for the IAM policy; EKS uses `aws_region` and `aws_profile` |
| Secret-type enumeration (all providers) | one `list` call on secrets in the configured namespace | A Kubernetes Role granting `list` on `secrets` in that namespace |

> **Warning:** Kubernetes documents that `list` access on Secrets effectively reveals their
> contents, because the list response includes them. QU.I.R.K. reads only each secret's `type` and
> never its data, but use a dedicated identity for the scan and scope its Role to the namespace you
> configure.

## Prerequisites

- The `kubernetes`, `google-cloud-container` and `azure-mgmt-containerservice` packages; they ship
  in the `cloud` extra, which `[all]` includes:

  ```bash
  pip install 'quirk-scanner[cloud]'
  ```

- For secret-type enumeration: a kubeconfig file readable by the QU.I.R.K. process
- For GKE: a GCP project ID and Application Default Credentials (see [GCP Connector
  Setup](gcp.md#credential-setup))
- For AKS: an Azure subscription ID and a `DefaultAzureCredential` identity (see [Azure Connector
  Setup](azure.md#service-principal-credentials))

## config.yaml Snippet

```yaml
connectors:
  enable_k8s: true
  k8s_provider: "gke"                    # required — one of eks, gke, aks
  k8s_cluster_name: "prod-cluster-1"     # needed for secret-type enumeration
  k8s_namespace: "default"               # optional — defaults to "default"
  k8s_kubeconfig: "/path/to/kubeconfig"  # optional — default kubeconfig when omitted
  k8s_context: "prod"                    # optional — kubeconfig context
  gcp_project_id: "my-gcp-project"       # needed for gke
  gke_clusters:                          # needed for gke: name + location
    - name: "prod-cluster-1"
      location: "us-east1"
  aks_clusters:                          # needed for aks: name + resource group
    - name: "prod-aks"
      resource_group: "rg-prod"
```

For `aks`, also set `azure_subscription_id`. `k8s_cluster_name` gates only the secret-type
enumeration; the GKE and AKS posture scans use the `gke_clusters` and `aks_clusters` lists.

## What Gets Scanned

| Provider | Resource Type | Data Collected |
|----------|---------------|----------------|
| GKE | Clusters in `gke_clusters` | `databaseEncryption` state: encrypted (with the key name) produces no finding; anything else is HIGH `GKE/unencrypted` |
| AKS | Clusters in `aks_clusters` | `securityProfile.azureKeyVaultKms.enabled`: enabled is `AKS/kv-kms` with no finding; disabled or absent is MEDIUM `AKS/platform-managed` |
| EKS | Clusters in the configured region | Etcd `encryptionConfig` through boto3 (see [AWS Connector Setup](aws.md)) |
| All | Secrets in `k8s_namespace` | A count of secrets per secret type; secret data is never read |

## Graceful Degradation

The Kubernetes connector never returns an empty result silently: when it cannot evaluate a cluster
it emits an "inaccessible" finding that says why. The reasons include:

- `Provider '(unset)' is not a supported managed cluster type. Supported: EKS, GKE, AKS.` when
  `k8s_provider` is unset or not `eks`, `gke` or `aks`
- `kubernetes Python SDK is not installed.` when the `kubernetes` package is missing (the install
  hint that follows it in the message is wrong; use the `cloud` extra shown above)
- `valid AKS credentials supplied but no aks_clusters configured` for `aks` without `aks_clusters`
- `No encryption findings produced for provider '<provider>'. Verify cluster credentials and IAM
  permissions.` as the final fallback

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `insufficient-rbac-privileges` scan error on `k8s://secrets/<namespace>` | The identity may not list secrets in that namespace (HTTP 403) | Bind a Role granting `list` on `secrets` in the namespace, or accept the missing secret-type counts |
| "Provider '(unset)' is not a supported managed cluster type" finding | `k8s_provider` not set | Set `k8s_provider` to `eks`, `gke` or `aks` |
| No GKE cluster results | `gke_clusters` empty, or the identity lacks `container.clusters.get` | List each cluster with `name` and `location`; grant `roles/container.clusterViewer` |
| No secret-type summary | `k8s_cluster_name` is empty, or the kubeconfig cannot be loaded | Set `k8s_cluster_name`; check `k8s_kubeconfig` and `k8s_context` |
