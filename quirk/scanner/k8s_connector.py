"""Kubernetes secrets inspection connector (Phase 29, K8S-01 / K8S-02 / K8S-03).

Detects:
  - GKE databaseEncryption.state (K8S-01 GKE path)
  - AKS security_profile.azure_key_vault_kms (K8S-01 AKS path)
  - K8S secret type enumeration (K8S-02 — accesses only secret.type, NEVER secret.data)
  - Explicit encryption-config-inaccessible findings (K8S-03 invariant — NEVER silently returns [])

EKS path handled separately in aws_connector._scan_eks_encryption (boto3, not kubernetes client).

Security invariants enforced:
  - T-29-04: Only secret.type accessed; secret.data is never read in any executable line
  - T-29-05: dat_scan_json contains only namespace + type counts — no credentials, no secret values
  - T-29-06: 403 ApiException → explicit insufficient-rbac-privileges finding; no escalation
  - T-29-07: Unauthorized calls → logger.v message only; no silent enumeration
  - T-29-08: Per-cluster try/except; one failed cluster does not abort the scan
  - T-29-09: Logger receives only cluster name + exception string; never raw secret objects
"""
from __future__ import annotations

import json
import sys
import types
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional

from quirk.models import CryptoEndpoint

# ---------------------------------------------------------------------------
# kubernetes Python client optional import — required for test patching.
# Each name must live at module level even when the import fails so that
# unittest.mock.patch("quirk.scanner.k8s_connector.K8S_AVAILABLE", ...) works.
# ---------------------------------------------------------------------------
try:
    from kubernetes import client as k8s_client, config as k8s_config
    from kubernetes.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    k8s_client = None        # type: ignore[assignment]
    k8s_config = None        # type: ignore[assignment]
    ApiException = None      # type: ignore[assignment]
    K8S_AVAILABLE = False

# ---------------------------------------------------------------------------
# google-cloud-container optional import — GKE path only.
# Register a stub module in sys.modules so that test patches of the form:
#   patch("google.cloud.container_v1.ClusterManagerClient", create=True)
# can successfully set the attribute on the stub even when the real SDK is absent.
# The function _scan_gke_encryption accesses ClusterManagerClient via _gke_container
# (the module-level alias), so the patch is effective immediately.
# ---------------------------------------------------------------------------
try:
    from google.cloud import container_v1 as _gke_container
    GKE_AVAILABLE = True
except ImportError:
    # Register stub so patch("google.cloud.container_v1.ClusterManagerClient", create=True) works.
    # patch() resolves the target by importing google.cloud then getting container_v1 attr;
    # pre-registering ensures the attribute exists for create=True to land on.
    _stub_gke = types.ModuleType("google.cloud.container_v1")
    sys.modules.setdefault("google.cloud.container_v1", _stub_gke)
    _gc = sys.modules.get("google.cloud")
    if _gc is not None and not hasattr(_gc, "container_v1"):
        _gc.container_v1 = _stub_gke  # type: ignore[attr-defined]
    _gke_container = _stub_gke        # type: ignore[assignment]
    GKE_AVAILABLE = False

# ---------------------------------------------------------------------------
# azure-mgmt-containerservice optional import — AKS path only.
# Register a stub module in sys.modules so that test patches of the form:
#   patch("azure.mgmt.containerservice.ContainerServiceClient", create=True)
# can successfully set the attribute on the stub even when the real SDK is absent.
# ---------------------------------------------------------------------------
try:
    from azure.mgmt.containerservice import ContainerServiceClient as _AKSClient
    AKS_AVAILABLE = True
except ImportError:
    _stub_aks_mod = types.ModuleType("azure.mgmt.containerservice")
    sys.modules.setdefault("azure.mgmt.containerservice", _stub_aks_mod)
    # Ensure azure.mgmt (if present) has containerservice attribute
    _azm = sys.modules.get("azure.mgmt")
    if _azm is not None and not hasattr(_azm, "containerservice"):
        _azm.containerservice = _stub_aks_mod  # type: ignore[attr-defined]
    _AKSClient = None        # type: ignore[assignment]
    AKS_AVAILABLE = False

# Canonical set of managed K8S cloud providers supported by this connector.
# EKS is included (boto3-based; dispatched via aws_connector from run_scan.py).
SUPPORTED_PROVIDERS = frozenset({"eks", "gke", "aks"})


# ---------------------------------------------------------------------------
# GKE encryption detection — K8S-01 GKE path
# ---------------------------------------------------------------------------

def _scan_gke_encryption(
    project_id: str,
    cluster_configs: list,
    logger,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]:
    """Detect GKE cluster etcd encryption via databaseEncryption.state (K8S-01 GKE path).

    Severity ladder:
        current_state == 2 (CURRENT_STATE_ENCRYPTED)   → GKE/encrypted:{key_name} (no severity)
        current_state == 0 / 1 (unspecified/DECRYPTED)  → HIGH/GKE/unencrypted

    Pattern: equivalent to azure_connector._scan_blob_encryption — guard check at top,
    module-level reference for SDK client, per-item try/except, session_start timestamp,
    dat_scan_json, severity conditional, getattr defensiveness.

    PITFALL 4: Compare current_state as int(state) == 2, NOT as string (int vs enum).
    PITFALL 2: Do NOT use google-api-python-client (_gcp_build) — use google-cloud-container.
    """
    if not GKE_AVAILABLE:
        return []
    results: List[CryptoEndpoint] = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        # Access ClusterManagerClient via module-level _gke_container reference.
        # The test patches google.cloud.container_v1.ClusterManagerClient (create=True),
        # which sets ClusterManagerClient on the same module object _gke_container points to.
        gke_client = _gke_container.ClusterManagerClient()
        for cfg in cluster_configs or []:
            cluster_name_path = (
                f"projects/{project_id}/locations/{cfg['location']}"
                f"/clusters/{cfg['name']}"
            )
            try:
                cluster = gke_client.get_cluster(name=cluster_name_path)
                db_enc = cluster.database_encryption
                # PITFALL 4: int() cast avoids string vs enum comparison errors
                state_val = int(db_enc.current_state) if db_enc else 0
                # 2 == CURRENT_STATE_ENCRYPTED; 0 == unspecified; 1 == DECRYPTED
                # Phase 72 D-15 (WR-20): build dat_scan_json as a fresh dict per
                # branch. Previously the unencrypted path inherited the encrypted
                # branch's key_name (read via getattr(db_enc, "key_name", "")),
                # which could leak a stale key_name value on the unencrypted path.
                if state_val == 2:
                    key_name = getattr(db_enc, "key_name", "")
                    service_detail = f"GKE/encrypted:{key_name}"
                    severity = None
                    dat_scan_json = {
                        "cluster": cfg["name"],
                        "provider": "GKE",
                        "current_state": state_val,
                        "encrypted": True,
                        "key_name": key_name,
                    }
                else:
                    service_detail = "GKE/unencrypted"
                    severity = "HIGH"
                    # NOTE: no key_name key — the unencrypted path must NOT
                    # include it (Phase 72 D-15).
                    dat_scan_json = {
                        "cluster": cfg["name"],
                        "provider": "GKE",
                        "current_state": state_val,
                        "encrypted": False,
                    }
                ep = CryptoEndpoint(
                    host=f"gcp://gke/{project_id}/{cfg['name']}",
                    port=0,
                    protocol="KUBERNETES",
                    service_detail=service_detail,
                    dat_scan_json=json.dumps(dat_scan_json, default=str),
                    scanned_at=now,
                )
                if severity:
                    ep.severity = severity
                results.append(ep)
            except Exception as exc:
                # T-29-09: log only cluster name + exception string — never raw cluster obj
                if logger:
                    logger.v(f"GKE cluster scan error for {cfg.get('name', '?')}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"GKE encryption scan error: {exc}")
    return results


# ---------------------------------------------------------------------------
# AKS encryption detection — K8S-01 AKS path
# ---------------------------------------------------------------------------

def _scan_aks_encryption(
    credential,
    subscription_id: str,
    cluster_configs: list,
    logger,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]:
    """Detect AKS etcd encryption via security_profile.azure_key_vault_kms (K8S-01 AKS path).

    Severity ladder:
        azure_key_vault_kms.enabled == True  → AKS/kv-kms (no severity)
        azure_key_vault_kms.enabled == False
            or security_profile is None
            or azure_key_vault_kms is None   → MEDIUM/AKS/platform-managed

    Pattern: equivalent to azure_connector._scan_app_gateways — access via sys.modules
    for testability (test patches "azure.mgmt.containerservice.ContainerServiceClient"),
    three nested getattr defenses to prevent AttributeError on old clusters that predate
    the security_profile API (PITFALL 5).
    """
    if not AKS_AVAILABLE:
        return []
    results: List[CryptoEndpoint] = []
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    try:
        # Access ContainerServiceClient via sys.modules so the test's patch
        # ("azure.mgmt.containerservice.ContainerServiceClient", create=True) is visible.
        _aks_mod = sys.modules.get("azure.mgmt.containerservice")
        ContainerServiceClient = (
            getattr(_aks_mod, "ContainerServiceClient", None)
            if _aks_mod is not None else None
        )
        if ContainerServiceClient is None:
            if logger:
                logger.v("azure-mgmt-containerservice ContainerServiceClient not available")
            return results
        aks_client = ContainerServiceClient(credential, subscription_id)
        for cfg in cluster_configs or []:
            try:
                cluster = aks_client.managed_clusters.get(
                    resource_group_name=cfg["resource_group"],
                    resource_name=cfg["name"],
                )
                # Three nested getattr calls prevent AttributeError on old clusters
                # where security_profile, azure_key_vault_kms, or enabled may be absent.
                sec = getattr(cluster, "security_profile", None)
                kv_kms = getattr(sec, "azure_key_vault_kms", None)
                kv_enabled = bool(getattr(kv_kms, "enabled", False))
                if kv_enabled:
                    service_detail = "AKS/kv-kms"
                    severity = None
                else:
                    service_detail = "AKS/platform-managed"
                    severity = "MEDIUM"
                ep = CryptoEndpoint(
                    host=f"azure://aks/{cfg['resource_group']}/{cfg['name']}",
                    port=0,
                    protocol="KUBERNETES",
                    service_detail=service_detail,
                    dat_scan_json=json.dumps(
                        {
                            "cluster": cfg["name"],
                            "provider": "AKS",
                            "kv_kms_enabled": kv_enabled,
                        },
                        default=str,
                    ),
                    scanned_at=now,
                )
                if severity:
                    ep.severity = severity
                results.append(ep)
            except Exception as exc:
                # T-29-09: log only cluster name + exception string — never raw cluster obj
                if logger:
                    logger.v(f"AKS cluster scan error for {cfg.get('name', '?')}: {exc}")
    except Exception as exc:
        if logger:
            logger.v(f"AKS encryption scan error: {exc}")
    return results


# ---------------------------------------------------------------------------
# Secret type enumeration — K8S-02
# ---------------------------------------------------------------------------

def _enumerate_secret_types(
    k8s_core_v1,
    namespace: str,
    logger,
    session_start: Optional[datetime] = None,
) -> Optional[CryptoEndpoint]:
    """Enumerate K8S secret types in namespace without reading any secret values (K8S-02).

    Strict invariant: only secret.type is accessed. secret.data is NEVER read.
    Plan 01 test_secret_type_enumeration_never_reads_data enforces this with a property
    sentinel that raises AssertionError if .data is touched.

    T-29-04: Only type counts are written to dat_scan_json — no credentials, no secret values.
    T-29-06: 403 ApiException → explicit insufficient-rbac-privileges finding; no fallback escalation.

    NOTE: The broad `except Exception` with `getattr(exc, "status", None)` discriminator
    (rather than `except ApiException`) handles the case where ApiException is None at module
    level when the kubernetes SDK is absent — duck typing on .status still works, and matches
    Plan 01's RBAC test which raises ApiException(status=403).
    """
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    host_id = f"k8s://secrets/{namespace}"
    try:
        secrets = k8s_core_v1.list_namespaced_secret(namespace=namespace)
        # Count by type — T-29-04 invariant: only secret.type accessed, never secret.data
        # Phase 72 D-14 (WR-17): filter None-typed secrets explicitly rather than
        # coercing them to "Opaque" — None and Opaque are semantically distinct
        # and the prior coercion masked the gap in count signal.
        secret_types = [s.type for s in secrets.items]
        skipped_nones = sum(1 for t in secret_types if t is None)
        if skipped_nones and logger:
            logger.v(
                f"K8s _enumerate_secret_types: skipped {skipped_nones} "
                "None-typed secrets in namespace "
                f"{namespace!r}"
            )
        type_counts = dict(Counter(t for t in secret_types if t is not None))
        return CryptoEndpoint(
            host=host_id,
            port=0,
            protocol="KUBERNETES",
            service_detail="secret-types-summary",
            dat_scan_json=json.dumps(
                {"namespace": namespace, "secret_type_counts": type_counts},
                default=str,
            ),
            scanned_at=now,
        )
    except Exception as exc:
        # T-29-06: discriminate on status 403 for RBAC insufficient-privilege path.
        # Using getattr duck-typing because ApiException may be None at module level
        # when kubernetes SDK is absent — explicit import guard protects this.
        status = getattr(exc, "status", None)
        if status == 403:
            return CryptoEndpoint(
                host=host_id,
                port=0,
                protocol="KUBERNETES",
                scan_error="insufficient-rbac-privileges",
                service_detail=(
                    f"Remediation: RBAC role requires get,list on secrets "
                    f"in namespace '{namespace}'"
                ),
                scanned_at=now,
            )
        # T-29-09: log only namespace + exception string — never raw secret objects
        if logger:
            logger.v(f"K8S secret enumeration error in {namespace}: {exc}")
        return None


# ---------------------------------------------------------------------------
# K8S-03 helper — explicit inaccessible finding emission
# ---------------------------------------------------------------------------

def _emit_inaccessible_finding(
    provider: str,
    cluster_name: str,
    reason: str,
    session_start: Optional[datetime] = None,
) -> CryptoEndpoint:
    """K8S-03 invariant: emit explicit encryption-config-inaccessible CryptoEndpoint.

    Required when:
      - provider is not in SUPPORTED_PROVIDERS (unknown/self-hosted)
      - K8S SDK is absent even when provider is valid (SDK-absent path)
      - GKE SDK absent when provider == 'gke'
      - AKS SDK absent when provider == 'aks'
      - No findings produced for a supported provider (final safety net)

    NEVER returns empty list — K8S-03 requires at least one endpoint per scan call.
    """
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    # Phase 72 D-13 (WR-06): strip colons from cluster_name before embedding it
    # in the finding identity tuple. Colons in cluster names break CSV/CBOM
    # output ordering and dedup downstream.
    cluster_name = (cluster_name or "").replace(":", "")
    return CryptoEndpoint(
        host=f"k8s://{cluster_name or provider or 'unknown'}",
        port=0,
        protocol="KUBERNETES",
        scan_error="encryption-config-inaccessible",
        service_detail=reason,
        scanned_at=now,
    )


# ---------------------------------------------------------------------------
# Public entry point — scan_k8s_targets (K8S-03 master enforcement)
# ---------------------------------------------------------------------------

def scan_k8s_targets(
    provider: str,
    cluster_name: str,
    namespace: str = "default",
    kubeconfig: Optional[str] = None,
    context: Optional[str] = None,
    gcp_project_id: str = "",
    gke_clusters: list = None,
    azure_subscription_id: str = "",
    aks_clusters: list = None,
    logger=None,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]:
    """K8S scan dispatcher (public entry point, called by run_scan.py).

    K8S-03 invariant: NEVER returns an empty list silently. Every scan call produces
    at least one CryptoEndpoint — either a real finding or an inaccessible finding.

    EKS path is NOT handled here — it uses boto3 (not the kubernetes Python client)
    and is dispatched separately from run_scan.py via aws_connector._scan_eks_encryption.

    Dispatch:
      provider == 'gke' → _scan_gke_encryption + optional _enumerate_secret_types
      provider == 'aks' → _scan_aks_encryption + optional _enumerate_secret_types
      provider == 'eks' → only _enumerate_secret_types (EKS encryption handled in aws_connector)
      provider not in SUPPORTED_PROVIDERS → inaccessible finding (K8S-03 path A)
      K8S_AVAILABLE == False → inaccessible finding (K8S-03 path B)
    """
    provider_norm = (provider or "").strip().lower()
    results: List[CryptoEndpoint] = []

    # ── K8S-03 path A: unsupported/unknown provider ─────────────────────────
    if provider_norm not in SUPPORTED_PROVIDERS:
        results.append(_emit_inaccessible_finding(
            provider=provider_norm,
            cluster_name=cluster_name,
            reason=(
                f"Provider '{provider_norm or '(unset)'}' is not a supported "
                "managed cluster type. Supported: EKS, GKE, AKS. "
                "Self-hosted clusters require direct etcd access (out of scope)."
            ),
            session_start=session_start,
        ))
        return results

    # ── K8S-03 path B: kubernetes SDK unavailable (even when provider is valid) ─
    # Secret enumeration cannot proceed; emit inaccessible finding.
    if not K8S_AVAILABLE:
        results.append(_emit_inaccessible_finding(
            provider=provider_norm,
            cluster_name=cluster_name,
            reason=(
                "kubernetes Python SDK is not installed. "
                "Install with: pip install quirk[cloud]"
            ),
            session_start=session_start,
        ))
        return results

    # ── GKE encryption scan (K8S-01 path 2) ─────────────────────────────────
    if provider_norm == "gke":
        if not GKE_AVAILABLE:
            # GKE SDK absent — emit inaccessible finding but continue to secret enumeration
            results.append(_emit_inaccessible_finding(
                provider="gke",
                cluster_name=cluster_name,
                reason=(
                    "google-cloud-container SDK is not installed. "
                    "Install with: pip install quirk[cloud]"
                ),
                session_start=session_start,
            ))
        else:
            results.extend(_scan_gke_encryption(
                project_id=gcp_project_id or "",
                cluster_configs=gke_clusters or [],
                logger=logger,
                session_start=session_start,
            ))

    # ── AKS encryption scan (K8S-01 path 3) ─────────────────────────────────
    if provider_norm == "aks":
        if not AKS_AVAILABLE:
            # AKS SDK absent — emit inaccessible finding but continue to secret enumeration
            results.append(_emit_inaccessible_finding(
                provider="aks",
                cluster_name=cluster_name,
                reason=(
                    "azure-mgmt-containerservice SDK is not installed. "
                    "Install with: pip install quirk[cloud]"
                ),
                session_start=session_start,
            ))
        else:
            try:
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
            except Exception as exc:
                credential = None
                if logger:
                    logger.v(f"Azure credential unavailable: {exc}")
                # CR-02 (Phase 29 gap closure): K8S-03 invariant requires an explicit
                # inaccessible finding for every configured AKS cluster when
                # DefaultAzureCredential cannot be constructed. Without this, a credential
                # failure silently drops the AKS scan even though clusters were configured.
                reason = (
                    f"Azure credential unavailable: {exc}. "
                    "Configure az login, managed identity, or env vars per "
                    "DefaultAzureCredential chain."
                )
                cfg_items = aks_clusters or []
                if cfg_items:
                    for cfg_item in cfg_items:
                        cn = (
                            (cfg_item or {}).get("name")
                            if isinstance(cfg_item, dict)
                            else None
                        ) or cluster_name or "aks"
                        results.append(_emit_inaccessible_finding(
                            provider="aks",
                            cluster_name=cn,
                            reason=reason,
                            session_start=session_start,
                        ))
                else:
                    # No configured aks_clusters list — still emit one finding so the
                    # K8S-03 invariant holds for the AKS provider invocation.
                    results.append(_emit_inaccessible_finding(
                        provider="aks",
                        cluster_name=cluster_name or "aks",
                        reason=reason,
                        session_start=session_start,
                    ))
            if credential is not None:
                # CE-01: when credentials are valid but no AKS clusters were
                # configured, emit an advisory (INFO) finding so the operator
                # knows WHY the result is empty — K8S-03 invariant requires at
                # least one finding per provider invocation.
                # _scan_aks_encryption is NOT called on the empty path (Phase 69 /
                # CR-09: cluster_configs=[] can raise AttributeError).
                if not (aks_clusters or []):
                    results.append(_emit_inaccessible_finding(
                        provider="aks",
                        cluster_name=cluster_name or "aks",
                        reason=(
                            "valid AKS credentials supplied but no aks_clusters configured"
                            " — no cluster encryption posture could be evaluated"
                        ),
                        session_start=session_start,
                    ))
                    return results
                results.extend(_scan_aks_encryption(
                    credential=credential,
                    subscription_id=azure_subscription_id or "",
                    cluster_configs=aks_clusters or [],
                    logger=logger,
                    session_start=session_start,
                ))

    # ── K8S-02: secret type enumeration ─────────────────────────────────────
    # Only executed when we have a target cluster_name to load kubeconfig for.
    # Applies to all supported providers (GKE, AKS, EKS) when K8S_AVAILABLE.
    if cluster_name:
        try:
            k8s_config.load_kube_config(
                config_file=kubeconfig or None,
                context=context or None,
            )
            core_v1 = k8s_client.CoreV1Api()
            ep = _enumerate_secret_types(
                core_v1,
                namespace=namespace or "default",
                logger=logger,
                session_start=session_start,
            )
            if ep is not None:
                results.append(ep)
        except Exception as exc:
            if logger:
                logger.v(f"K8S secret enumeration setup error: {exc}")

    # ── K8S-03 final safety net ──────────────────────────────────────────────
    # If somehow no results were produced for a supported provider (e.g., empty
    # cluster_configs with no cluster_name), emit an inaccessible finding rather
    # than silently returning [].
    if not results:
        results.append(_emit_inaccessible_finding(
            provider=provider_norm,
            cluster_name=cluster_name,
            reason=(
                f"No encryption findings produced for provider '{provider_norm}'. "
                "Verify cluster credentials and IAM permissions."
            ),
            session_start=session_start,
        ))

    return results
