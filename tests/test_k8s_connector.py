"""Tests for K8S secrets inspection — K8S-01 / K8S-02 / K8S-03 (Phase 29).

Tests mock kubernetes, google-cloud-container, and azure-mgmt-containerservice SDK calls.
No live cluster required. Scanner: quirk/scanner/k8s_connector.py +
aws_connector._scan_eks_encryption.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _k8s_available_flags():
    """Phase 69.1: patch *_AVAILABLE flags + stub missing cloud-SDK modules.

    Tests in this file exercise scan_k8s_targets's SDK-dispatch branches. The
    module-level K8S_AVAILABLE / AKS_AVAILABLE / GKE_AVAILABLE flags default to
    False in .venv because the cloud SDKs (kubernetes, azure-mgmt-containerservice,
    google-cloud-container) are opt-in extras.

    Some tests also patch attributes on those modules via patch("module.X",
    create=True) — but patch() can only create missing attributes on objects
    that already exist. So we stub the parent modules in sys.modules with
    MagicMock placeholders before patches resolve.

    Tests that want to exercise the K8S-03 path A/B fallbacks can override via
    patch("...K8S_AVAILABLE", False) inside the test body.
    """
    import sys
    # patch() with create=True can only add missing *attributes* on existing
    # modules. quirk.scanner.k8s_connector already self-stubs
    # google.cloud.container_v1 (and azure.mgmt.containerservice) in sys.modules
    # at import time, but doesn't stub the parent packages (`google`,
    # `google.cloud`). pkgutil.resolve_name() needs the parents to traverse the
    # dotted path. Add only the parent stubs — leave the leaf module alone so
    # patches and the module's own `_gke_container` alias point to the same
    # object.
    parent_stubs = {}
    if "google" not in sys.modules:
        parent_stubs["google"] = MagicMock()
    if "google.cloud" not in sys.modules:
        parent_stubs["google.cloud"] = MagicMock()
    with patch("quirk.scanner.k8s_connector.K8S_AVAILABLE", True), \
         patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True), \
         patch("quirk.scanner.k8s_connector.GKE_AVAILABLE", True), \
         patch.dict(sys.modules, parent_stubs):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_secret_list(types):
    """Build a mock V1SecretList with secrets of the given type strings."""
    mock_secrets = []
    for stype in types:
        s = MagicMock()
        s.type = stype
        mock_secrets.append(s)
    mock_list = MagicMock()
    mock_list.items = mock_secrets
    return mock_list


# ---------------------------------------------------------------------------
# ISSUE-2: pyproject.toml [cloud] extras structural test
# ---------------------------------------------------------------------------

def test_pyproject_cloud_extras_lists_phase_29_sdks():
    """ISSUE-2: [cloud] extras must declare all three Phase 29 SDKs."""
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "kubernetes>=35.0.0" in text, "kubernetes>=35.0.0 missing from pyproject.toml"
    assert "google-cloud-container>=2.0.0" in text, (
        "google-cloud-container>=2.0.0 missing from pyproject.toml"
    )
    assert "azure-mgmt-containerservice>=35.0.0" in text, (
        "azure-mgmt-containerservice>=35.0.0 missing from pyproject.toml"
    )


# ---------------------------------------------------------------------------
# K8S-01: EKS encryption detection (in aws_connector.py)
# ---------------------------------------------------------------------------

def test_eks_unencrypted_empty_config_produces_high():
    """K8S-01 EKS: encryptionConfig empty list → HIGH/EKS/unencrypted."""
    from quirk.scanner.aws_connector import _scan_eks_encryption
    mock_session = MagicMock()
    mock_eks = MagicMock()
    mock_eks.get_paginator.return_value.paginate.return_value = [
        {"clusters": ["my-cluster"]}
    ]
    mock_eks.describe_cluster.return_value = {
        "cluster": {"name": "my-cluster", "encryptionConfig": []}
    }
    mock_session.client.return_value = mock_eks
    results = _scan_eks_encryption(mock_session, logger=None)
    assert len(results) == 1
    assert results[0].protocol == "KUBERNETES"
    assert results[0].service_detail == "EKS/unencrypted"
    assert results[0].severity == "HIGH"
    assert results[0].host == "aws://eks/my-cluster"


def test_eks_unencrypted_absent_config_produces_high():
    """K8S-01 EKS: encryptionConfig key absent → HIGH/EKS/unencrypted (handles both shapes)."""
    from quirk.scanner.aws_connector import _scan_eks_encryption
    mock_session = MagicMock()
    mock_eks = MagicMock()
    mock_eks.get_paginator.return_value.paginate.return_value = [
        {"clusters": ["other-cluster"]}
    ]
    mock_eks.describe_cluster.return_value = {
        "cluster": {"name": "other-cluster"}  # encryptionConfig missing
    }
    mock_session.client.return_value = mock_eks
    results = _scan_eks_encryption(mock_session, logger=None)
    assert len(results) == 1
    assert results[0].service_detail == "EKS/unencrypted"
    assert results[0].severity == "HIGH"


def test_eks_encrypted_no_severity():
    """K8S-01 EKS: encryptionConfig with secrets+keyArn → EKS/encrypted, no severity."""
    from quirk.scanner.aws_connector import _scan_eks_encryption
    mock_session = MagicMock()
    mock_eks = MagicMock()
    mock_eks.get_paginator.return_value.paginate.return_value = [
        {"clusters": ["secure-cluster"]}
    ]
    key_arn = "arn:aws:kms:us-east-1:123456789:key/abc-def"
    mock_eks.describe_cluster.return_value = {
        "cluster": {
            "name": "secure-cluster",
            "encryptionConfig": [
                {"resources": ["secrets"], "provider": {"keyArn": key_arn}}
            ],
        }
    }
    mock_session.client.return_value = mock_eks
    results = _scan_eks_encryption(mock_session, logger=None)
    assert len(results) == 1
    assert results[0].service_detail.startswith("EKS/encrypted:")
    assert key_arn in results[0].service_detail
    assert getattr(results[0], "severity", None) is None


# ---------------------------------------------------------------------------
# K8S-01: GKE encryption detection (in k8s_connector.py)
# ---------------------------------------------------------------------------

def test_gke_encrypted_no_severity():
    """K8S-01 GKE: current_state == 2 (CURRENT_STATE_ENCRYPTED) → GKE/encrypted, no severity."""
    with patch("quirk.scanner.k8s_connector.GKE_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_gke_encryption
        with patch(
            "google.cloud.container_v1.ClusterManagerClient", create=True
        ) as mock_cls:
            mock_client = MagicMock()
            cluster = MagicMock()
            cluster.database_encryption.current_state = 2
            cluster.database_encryption.key_name = (
                "projects/p/locations/global/keyRings/r/cryptoKeys/k"
            )
            mock_client.get_cluster.return_value = cluster
            mock_cls.return_value = mock_client
            results = _scan_gke_encryption(
                project_id="my-proj",
                cluster_configs=[{"name": "my-gke", "location": "us-central1"}],
                logger=None,
            )
    assert len(results) == 1
    assert results[0].protocol == "KUBERNETES"
    assert results[0].service_detail.startswith("GKE/encrypted:")
    assert getattr(results[0], "severity", None) is None


def test_gke_unencrypted_produces_high():
    """K8S-01 GKE: current_state == 1 (DECRYPTED) → HIGH/GKE/unencrypted."""
    with patch("quirk.scanner.k8s_connector.GKE_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_gke_encryption
        with patch(
            "google.cloud.container_v1.ClusterManagerClient", create=True
        ) as mock_cls:
            mock_client = MagicMock()
            cluster = MagicMock()
            cluster.database_encryption.current_state = 1
            cluster.database_encryption.key_name = ""
            mock_client.get_cluster.return_value = cluster
            mock_cls.return_value = mock_client
            results = _scan_gke_encryption(
                project_id="my-proj",
                cluster_configs=[{"name": "my-gke", "location": "us-central1"}],
                logger=None,
            )
    assert len(results) == 1
    assert results[0].service_detail == "GKE/unencrypted"
    assert results[0].severity == "HIGH"


# ---------------------------------------------------------------------------
# K8S-01: AKS encryption detection (in k8s_connector.py)
# ---------------------------------------------------------------------------

def test_aks_kv_kms_enabled_no_severity():
    """K8S-01 AKS: azure_key_vault_kms.enabled == True → AKS/kv-kms, no severity."""
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_aks_encryption
        with patch(
            "azure.mgmt.containerservice.ContainerServiceClient", create=True
        ) as mock_cls:
            client = MagicMock()
            cluster = MagicMock()
            kv_kms = MagicMock()
            kv_kms.enabled = True
            cluster.security_profile.azure_key_vault_kms = kv_kms
            client.managed_clusters.get.return_value = cluster
            mock_cls.return_value = client
            results = _scan_aks_encryption(
                credential=MagicMock(),
                subscription_id="sub-1",
                cluster_configs=[{"name": "my-aks", "resource_group": "rg"}],
                logger=None,
            )
    assert len(results) == 1
    assert results[0].protocol == "KUBERNETES"
    assert results[0].service_detail == "AKS/kv-kms"
    assert getattr(results[0], "severity", None) is None


def test_aks_platform_managed_medium():
    """K8S-01 AKS: kv_kms.enabled == False → MEDIUM/AKS/platform-managed."""
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_aks_encryption
        with patch(
            "azure.mgmt.containerservice.ContainerServiceClient", create=True
        ) as mock_cls:
            client = MagicMock()
            cluster = MagicMock()
            kv_kms = MagicMock()
            kv_kms.enabled = False
            cluster.security_profile.azure_key_vault_kms = kv_kms
            client.managed_clusters.get.return_value = cluster
            mock_cls.return_value = client
            results = _scan_aks_encryption(
                credential=MagicMock(),
                subscription_id="sub-1",
                cluster_configs=[{"name": "my-aks", "resource_group": "rg"}],
                logger=None,
            )
    assert len(results) == 1
    assert results[0].service_detail == "AKS/platform-managed"
    assert results[0].severity == "MEDIUM"


def test_aks_security_profile_none_defaults_platform_managed():
    """K8S-01 AKS: security_profile None on old clusters → MEDIUM/AKS/platform-managed (no AttributeError)."""
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_aks_encryption
        with patch(
            "azure.mgmt.containerservice.ContainerServiceClient", create=True
        ) as mock_cls:
            client = MagicMock()
            cluster = MagicMock(spec=["security_profile"])
            cluster.security_profile = None
            client.managed_clusters.get.return_value = cluster
            mock_cls.return_value = client
            results = _scan_aks_encryption(
                credential=MagicMock(),
                subscription_id="sub-1",
                cluster_configs=[{"name": "old-aks", "resource_group": "rg"}],
                logger=None,
            )
    assert len(results) == 1
    assert results[0].service_detail == "AKS/platform-managed"
    assert results[0].severity == "MEDIUM"


# ---------------------------------------------------------------------------
# K8S-02: Secret type enumeration (no data read)
# ---------------------------------------------------------------------------

def test_secret_type_counts_basic():
    """K8S-02: list_namespaced_secret returns mixed types → Counter dict in dat_scan_json."""
    from quirk.scanner.k8s_connector import _enumerate_secret_types
    mock_v1 = MagicMock()
    mock_v1.list_namespaced_secret.return_value = _make_secret_list([
        "Opaque",
        "Opaque",
        "kubernetes.io/tls",
        "kubernetes.io/dockerconfigjson",
    ])
    ep = _enumerate_secret_types(mock_v1, namespace="default", logger=None)
    assert ep is not None
    assert ep.protocol == "KUBERNETES"
    assert ep.service_detail == "secret-types-summary"
    payload = json.loads(ep.dat_scan_json)
    counts = payload["secret_type_counts"]
    assert counts["Opaque"] == 2
    assert counts["kubernetes.io/tls"] == 1
    assert counts["kubernetes.io/dockerconfigjson"] == 1
    assert payload["namespace"] == "default"


def test_secret_type_enumeration_never_reads_data():
    """K8S-02: implementation must access only secret.type, never secret.data."""
    from quirk.scanner.k8s_connector import _enumerate_secret_types
    # Build mock secrets that raise if .data is touched
    secrets = []
    for stype in ("Opaque", "kubernetes.io/tls"):
        s = MagicMock()
        s.type = stype
        # Sentinel: any read of .data raises AssertionError
        type(s).data = property(
            lambda self: (_ for _ in ()).throw(AssertionError("secret.data MUST NOT be read"))
        )
        secrets.append(s)
    mock_list = MagicMock()
    mock_list.items = secrets
    mock_v1 = MagicMock()
    mock_v1.list_namespaced_secret.return_value = mock_list
    ep = _enumerate_secret_types(mock_v1, namespace="default", logger=None)
    assert ep is not None
    counts = json.loads(ep.dat_scan_json)["secret_type_counts"]
    assert counts["Opaque"] == 1
    assert counts["kubernetes.io/tls"] == 1


def test_secret_rbac_403_produces_insufficient_privileges():
    """K8S-02: ApiException(status=403) → scan_error=insufficient-rbac-privileges."""
    from quirk.scanner.k8s_connector import _enumerate_secret_types
    try:
        from kubernetes.client.rest import ApiException
    except ImportError:
        class ApiException(Exception):
            def __init__(self, status=None, reason=None, *args, **kwargs):
                self.status = status
                self.reason = reason
                super().__init__(f"{status} {reason}")
    mock_v1 = MagicMock()
    mock_v1.list_namespaced_secret.side_effect = ApiException(
        status=403, reason="Forbidden"
    )
    ep = _enumerate_secret_types(mock_v1, namespace="default", logger=None)
    assert ep is not None
    assert ep.protocol == "KUBERNETES"
    assert ep.scan_error == "insufficient-rbac-privileges"
    assert "secrets" in ep.service_detail.lower()


# ---------------------------------------------------------------------------
# K8S-03: encryption-config-inaccessible — never silent empty
# ---------------------------------------------------------------------------

def test_unknown_provider_produces_inaccessible_finding():
    """K8S-03: provider not in {eks,gke,aks} → 1 endpoint, scan_error=encryption-config-inaccessible."""
    from quirk.scanner.k8s_connector import scan_k8s_targets
    results = scan_k8s_targets(
        provider="self-hosted",
        cluster_name="some-cluster",
        namespace="default",
        logger=None,
    )
    assert len(results) >= 1
    assert any(
        getattr(ep, "scan_error", "") == "encryption-config-inaccessible"
        for ep in results
    ), "K8S-03 violated: unknown provider must produce explicit inaccessible finding, not empty list"


def test_sdk_unavailable_produces_inaccessible_finding():
    """K8S-03: K8S_AVAILABLE=False with valid provider → inaccessible finding (NOT empty list)."""
    with patch("quirk.scanner.k8s_connector.K8S_AVAILABLE", False):
        from quirk.scanner.k8s_connector import scan_k8s_targets
        results = scan_k8s_targets(
            provider="gke",
            cluster_name="my-cluster",
            namespace="default",
            logger=None,
        )
    assert len(results) >= 1
    assert any(
        getattr(ep, "scan_error", "") == "encryption-config-inaccessible"
        for ep in results
    ), "K8S-03 violated: SDK absence must produce inaccessible finding"


# ---------------------------------------------------------------------------
# ISSUE-3: session_start threading
# ---------------------------------------------------------------------------

def test_session_start_stamped_on_endpoints():
    """ISSUE-3: session_start parameter must stamp scanned_at on produced endpoints."""
    fixed = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
    from quirk.scanner.k8s_connector import scan_k8s_targets
    results = scan_k8s_targets(
        provider="self-hosted",  # forces K8S-03 path quickly with at least 1 endpoint
        cluster_name="x",
        namespace="default",
        logger=None,
        session_start=fixed,
    )
    assert len(results) >= 1
    ep = results[0]
    assert ep.scanned_at is not None
    # tzinfo must be stripped (matches db_connector / aws_connector convention)
    assert ep.scanned_at.tzinfo is None
    # The stamped datetime must reflect the provided session_start (not "now")
    assert ep.scanned_at.year == 2026
    assert ep.scanned_at.month == 4
    assert ep.scanned_at.day == 26
    assert ep.scanned_at.hour == 12


# ---------------------------------------------------------------------------
# CR-02 regression: AKS credential failure must emit per-cluster inaccessible
# ---------------------------------------------------------------------------

def test_aks_credential_failure_emits_inaccessible_per_cluster():
    """CR-02: K8S-03 invariant — DefaultAzureCredential() raise must emit one
    inaccessible finding per configured aks_clusters entry (not silently drop)."""
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import scan_k8s_targets
        with patch(
            "azure.identity.DefaultAzureCredential",
            create=True,
            side_effect=RuntimeError("no credentials configured"),
        ):
            results = scan_k8s_targets(
                provider="aks",
                cluster_name="",
                namespace="default",
                azure_subscription_id="sub-1",
                aks_clusters=[
                    {"name": "aks-prod", "resource_group": "rg-prod"},
                    {"name": "aks-dev", "resource_group": "rg-dev"},
                ],
                logger=None,
            )
    # Filter to inaccessible findings emitted by our credential-failure branch
    inaccessible = [
        ep for ep in results
        if getattr(ep, "scan_error", None) == "encryption-config-inaccessible"
    ]
    # Two configured clusters → two inaccessible findings (final safety net does
    # not double up because we already populated results in the except branch).
    assert len(inaccessible) == 2, (
        f"Expected 2 inaccessible findings (one per configured cluster); got "
        f"{len(inaccessible)}: {[ep.host for ep in results]}"
    )
    hosts = {ep.host for ep in inaccessible}
    assert any("aks-prod" in h for h in hosts), hosts
    assert any("aks-dev" in h for h in hosts), hosts
    for ep in inaccessible:
        assert ep.protocol == "KUBERNETES"
        assert "Azure credential unavailable" in (ep.service_detail or "")


def test_aks_credential_failure_no_clusters_still_emits_one_inaccessible():
    """CR-02 corollary: aks_clusters=[] with provider='aks' and credential failure must
    still emit at least one inaccessible finding (K8S-03 invariant)."""
    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import scan_k8s_targets
        with patch(
            "azure.identity.DefaultAzureCredential",
            create=True,
            side_effect=RuntimeError("no credentials"),
        ):
            results = scan_k8s_targets(
                provider="aks",
                cluster_name="",
                namespace="default",
                aks_clusters=[],
                logger=None,
            )
    inaccessible = [
        ep for ep in results
        if getattr(ep, "scan_error", None) == "encryption-config-inaccessible"
    ]
    assert len(inaccessible) >= 1, (
        f"K8S-03 invariant violated: empty aks_clusters + credential failure produced "
        f"no inaccessible finding. results={results}"
    )


# ---------------------------------------------------------------------------
# CR-09 regression (BLOCK-03, Phase 69): valid azure_cred + empty aks_clusters
# must short-circuit to [] WITHOUT raising AttributeError and WITHOUT emitting
# an inaccessible finding from this path (per locked decision D-09).
# The K8S-03 "at least one finding" invariant applies at the per-provider level,
# NOT for an empty cluster list when credentials are valid.
# ---------------------------------------------------------------------------

def test_aks_empty_cluster_list_returns_empty():
    """CR-09 / D-09: valid azure_cred + empty aks_clusters returns [] cleanly.

    Pre-fix, _scan_aks_encryption was called with cluster_configs=[] and raised
    AttributeError. Post-fix, the function short-circuits to [] without calling
    _scan_aks_encryption and without emitting an inaccessible finding for this
    path (inaccessible findings are reserved for the credential=None branch,
    which is Phase 29 work).
    """
    sentinel_cred = MagicMock(name="azure-credential")

    def _should_not_be_called(*_args, **_kwargs):
        raise AssertionError(
            "_scan_aks_encryption must NOT be called when aks_clusters is empty "
            "(CR-09 / D-09 short-circuit)"
        )

    with patch("quirk.scanner.k8s_connector.AKS_AVAILABLE", True):
        from quirk.scanner.k8s_connector import scan_k8s_targets
        with patch(
            "azure.identity.DefaultAzureCredential",
            create=True,
            return_value=sentinel_cred,
        ), patch(
            "quirk.scanner.k8s_connector._scan_aks_encryption",
            side_effect=_should_not_be_called,
        ):
            # Must not raise.
            results = scan_k8s_targets(
                provider="aks",
                cluster_name="",
                namespace="default",
                azure_subscription_id="sub-1",
                aks_clusters=[],
                logger=None,
            )

    # D-09: returns [] for the empty-aks_clusters + valid-credential case.
    # No inaccessible finding must be emitted from THIS path (that path is
    # reserved for the credential=None branch — Phase 29).
    assert results == [], (
        f"CR-09 / D-09: expected [] for valid azure_cred + empty aks_clusters; "
        f"got {results}"
    )


# ---------------------------------------------------------------------------
# Phase 72 / WR-06 / D-13: _emit_inaccessible_finding strips ':' from cluster_name
# ---------------------------------------------------------------------------

def test_emit_inaccessible_finding_strips_colon_from_cluster_name():
    """WR-06 (D-13): colons in cluster_name break CSV/CBOM dedup. Strip them at
    function entry before embedding in the finding host identity."""
    from quirk.scanner.k8s_connector import _emit_inaccessible_finding
    ep = _emit_inaccessible_finding(
        provider="gke",
        cluster_name="my:cluster:dev",
        reason="sdk-absent",
    )
    # Identity is encoded into host="k8s://{cluster_name}"; assert no colons
    # remain in the cluster_name segment.
    assert ep.host == "k8s://myclusterdev"
    assert ":" not in ep.host.split("//", 1)[1]


def test_emit_inaccessible_finding_empty_cluster_name_safe():
    """Defensive: empty cluster_name still strips cleanly and falls back to provider."""
    from quirk.scanner.k8s_connector import _emit_inaccessible_finding
    ep = _emit_inaccessible_finding(
        provider="gke",
        cluster_name="",
        reason="sdk-absent",
    )
    assert ep.host == "k8s://gke"


# ---------------------------------------------------------------------------
# Phase 72 / WR-17 / D-14: _enumerate_secret_types excludes None-typed secrets
# ---------------------------------------------------------------------------

def test_enumerate_secret_types_excludes_none():
    """WR-17 (D-14): None-typed secrets must be filtered out of the Counter
    rather than coerced to 'Opaque' (which masked them as indistinguishable
    from real Opaque secrets)."""
    from quirk.scanner.k8s_connector import _enumerate_secret_types
    mock_v1 = MagicMock()
    mock_v1.list_namespaced_secret.return_value = _make_secret_list(
        [None, "Opaque", "kubernetes.io/tls", None]
    )
    logger = MagicMock()
    ep = _enumerate_secret_types(mock_v1, namespace="default", logger=logger)
    assert ep is not None
    counts = json.loads(ep.dat_scan_json)["secret_type_counts"]
    # None is excluded; Opaque and kubernetes.io/tls each appear once.
    assert counts == {"Opaque": 1, "kubernetes.io/tls": 1}
    assert None not in counts
    # DEBUG log of skipped count must fire (2 Nones).
    assert any(
        "skipped 2" in str(c.args) or "skipped 2 " in str(c.args)
        for c in logger.v.call_args_list
    )


# ---------------------------------------------------------------------------
# Phase 72 / WR-20 / D-15: dat_scan_json is a fresh dict per branch — unencrypted
# path MUST NOT include key_name
# ---------------------------------------------------------------------------

def test_dat_scan_json_unencrypted_omits_key_name():
    """WR-20 (D-15): the unencrypted GKE branch (current_state != 2) produces
    a fresh dat_scan_json that does NOT include a key_name key."""
    with patch("quirk.scanner.k8s_connector.GKE_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_gke_encryption
        with patch(
            "google.cloud.container_v1.ClusterManagerClient", create=True
        ) as mock_cls:
            mock_client = MagicMock()
            cluster = MagicMock()
            cluster.database_encryption.current_state = 1  # DECRYPTED
            # Even if SDK echoes a stale key_name on db_enc, the unencrypted
            # branch must NOT propagate it into dat_scan_json.
            cluster.database_encryption.key_name = "stale-leak"
            mock_client.get_cluster.return_value = cluster
            mock_cls.return_value = mock_client
            results = _scan_gke_encryption(
                project_id="p",
                cluster_configs=[{"name": "g", "location": "us"}],
                logger=None,
            )
    assert len(results) == 1
    payload = json.loads(results[0].dat_scan_json)
    assert "key_name" not in payload, (
        f"WR-20: unencrypted path must omit key_name; got {payload}"
    )
    assert payload.get("encrypted") is False


def test_dat_scan_json_encrypted_includes_key_name():
    """Positive guard: the encrypted branch DOES include key_name (we did not
    over-strip in the D-15 restructure)."""
    with patch("quirk.scanner.k8s_connector.GKE_AVAILABLE", True):
        from quirk.scanner.k8s_connector import _scan_gke_encryption
        with patch(
            "google.cloud.container_v1.ClusterManagerClient", create=True
        ) as mock_cls:
            mock_client = MagicMock()
            cluster = MagicMock()
            cluster.database_encryption.current_state = 2  # ENCRYPTED
            cluster.database_encryption.key_name = (
                "projects/p/locations/g/keyRings/r/cryptoKeys/k"
            )
            mock_client.get_cluster.return_value = cluster
            mock_cls.return_value = mock_client
            results = _scan_gke_encryption(
                project_id="p",
                cluster_configs=[{"name": "g", "location": "us"}],
                logger=None,
            )
    assert len(results) == 1
    payload = json.loads(results[0].dat_scan_json)
    assert "key_name" in payload
    assert payload["key_name"].endswith("/cryptoKeys/k")
    assert payload.get("encrypted") is True
