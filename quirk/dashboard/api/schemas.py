"""Pydantic response models for the QU.I.R.K. dashboard API.

These models define the contract between FastAPI and the React frontend.
TypeScript types in src/dashboard/src/types/api.ts must mirror these exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    status: str  # "ok"


class ConfigResponse(BaseModel):
    vertical: str  # "general" | "healthcare"


# ---- Score / Confidence ----

class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int
    data_at_rest: int = 0
    data_in_motion: int = 0   # NEW — Phase 36 D-06


class ScoreData(BaseModel):
    score: int
    rating: str  # EXCELLENT / GOOD / MODERATE / FAIR / POOR
    subscores: SubScores
    drivers: List[Dict[str, Any]]


class ConfidenceData(BaseModel):
    confidence_score: int
    confidence_rating: str  # HIGH / MEDIUM / LOW / VERY_LOW / NO_DATA
    factor_breakdown: Optional[Dict[str, Any]] = None


# ---- Findings ----

# DO NOT UNIFY: dashboard FindingItem uses `remediation` while the risk-engine
# finding dicts (quirk/engine/risk_engine.py _build_finding) use `recommendation`.
# This asymmetry is intentional and pre-existing — the dashboard route in
# routes/scan.py constructs FindingItem from CryptoEndpoint state directly and
# does NOT consume risk-engine dicts. See Phase 48 PATTERNS §3.
class FindingItem(BaseModel):
    id: Optional[int] = None
    host: str
    port: int
    severity: str        # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None   # quantum-safety label
    source: Optional[str] = None        # scanner type
    category: Optional[str] = None      # Phase 45 — coverage_gap visibility (Q2)
    # Phase 49 D-02: eager compliance attachment surface (forward-compat
    # for BACK-72 dashboard work; HTML/PDF reports already read from the
    # finding dict directly). Each entry: {framework, control, version,
    # last_verified, source_url}.
    compliance: List[Dict[str, Any]] = []
    # Phase 111 DASH-01: distributed sensor provenance fields (nullable for
    # backward compat — NULL-sensor local scans are unaffected).
    sensor_id: Optional[str] = None
    segment: Optional[str] = None


# ---- Certificates ----

class CertItem(BaseModel):
    host: str
    port: int
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
    cert_not_after: Optional[datetime] = None
    cert_pubkey_alg: Optional[str] = None
    cert_pubkey_size: Optional[int] = None
    quantum_safety: Optional[str] = None   # Safe / At Risk / Vulnerable / Unknown


# ---- CBOM ----

class CbomComponent(BaseModel):
    algorithm: str
    type: Optional[str] = None        # hash / cipher / kem / signature / etc.
    key_size: Optional[int] = None
    quantum_safety: Optional[str] = None
    source_systems: List[str] = []    # ["host:port", "file/path.py", ...]
    # Phase 111 DASH-01: distributed sensor provenance fields (nullable for
    # backward compat — NULL-sensor local scans are unaffected).
    sensor_id: Optional[str] = None
    segment: Optional[str] = None


# ---- Identity Findings ----

class IdentityFinding(BaseModel):
    host: str
    port: int
    severity: str            # CRITICAL / HIGH / MEDIUM / LOW / INFO
    title: str
    protocol: Optional[str] = None    # KERBEROS / SAML / DNSSEC
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None
    algorithm: str           # e.g. "rc4-hmac", "RSA-1024", "RSASHA1"


# ---- Motion Findings (Phase 36 DASH-05) ----

class MotionFinding(BaseModel):
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None
    tls_version: Optional[str] = None
    cipher_suite: Optional[str] = None
    cert_not_after: Optional[str] = None    # ISO date string, not datetime
    plaintext_exposed: bool = False         # NON-OPTIONAL per D-02
    starttls_warning: bool = False          # NON-OPTIONAL per D-02


# ---- DAR Findings (Phase 39 GAP-04) ----

class DarFinding(BaseModel):
    # Universal baseline (matches MotionFinding baseline)
    host: str
    port: int
    severity: str
    title: str
    protocol: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None
    source: Optional[str] = None

    # Discriminator (D-02)
    category: str  # "database" | "object_storage" | "kubernetes" | "vault"

    # Database fields
    encryption_at_rest: Optional[bool] = None
    tls_in_transit: Optional[bool] = None

    # Object Storage fields
    encryption_mode: Optional[str] = None
    kms_key_id: Optional[str] = None
    public_access: Optional[bool] = None
    versioning: Optional[bool] = None

    # Kubernetes fields
    namespace: Optional[str] = None
    secret_type: Optional[str] = None
    encryption_provider: Optional[str] = None

    # Vault fields
    seal_type: Optional[str] = None
    auto_unseal: Optional[bool] = None
    mount_type: Optional[str] = None


# ---- Roadmap ----

class RoadmapEdge(BaseModel):
    source: str
    target: str
    reason: Optional[str] = None


class RoadmapNode(BaseModel):
    id: str
    title: str
    timeframe: str   # 0-30 days / 31-90 days / 90+ days
    why: Optional[str] = None
    phase: Optional[str] = None   # NOW / NEXT / LATER


class RoadmapData(BaseModel):
    nodes: List[RoadmapNode]
    edges: List[RoadmapEdge]


# ---- Scan Summary ----

class PartialFailureEntry(BaseModel):
    """Phase 67 RESUME-02: one entry per scanner that had a partial failure.

    Sourced from scan_checkpoints.error_summary JSON array.
    stage: inventory|tls|ssh|api|identity|data_at_rest|broker_email|reports
    error_category: exception|missing_extra
    """
    stage: str
    scanner: str
    error_category: str
    error_message: str
    endpoint_count: int = 0


class ScanMeta(BaseModel):
    scan_id: str          # ISO timestamp of most recent scan
    scanned_at: Optional[datetime] = None
    total_endpoints: int
    total_findings: int


class ScanLatestResponse(BaseModel):
    meta: ScanMeta
    score: ScoreData
    confidence: ConfidenceData
    findings: List[FindingItem]
    certificates: List[CertItem]
    cbom_components: List[CbomComponent]
    roadmap: RoadmapData
    identity_findings: List[IdentityFinding] = []
    motion_findings: List[MotionFinding] = []   # NEW — Phase 36 DASH-05
    dar_findings: List[DarFinding] = []          # Phase 39 GAP-04
    partial_failures: List[PartialFailureEntry] = []  # Phase 67 RESUME-02


class ScanSession(BaseModel):
    scan_id: str          # ISO timestamp string (matches ScanMeta.scan_id)
    scanned_at: datetime
    total_endpoints: int
    # Phase 66 UI-HIST-01 additions — all Optional/default for backward compat with ScanSelector
    score: int = 0
    profile: Optional[str] = None
    calibration: Optional[str] = None
    target: Optional[str] = None
    finding_counts: "FindingCounts" = Field(default_factory=lambda: FindingCounts())


# Trend Analysis (Phase 31)

class SampleFinding(BaseModel):
    host: str
    port: int
    protocol: str
    severity: str


class TrendReportResponse(BaseModel):
    current_session_ts: Optional[datetime] = None
    previous_session_ts: Optional[datetime] = None
    current_score: Optional[int] = None
    previous_score: Optional[int] = None
    score_delta: Optional[int] = None
    new_high: int = 0
    new_medium: int = 0
    new_low: int = 0
    resolved_high: int = 0
    resolved_medium: int = 0
    resolved_low: int = 0
    scan_errors_new_count: int = 0
    scan_errors_resolved_count: int = 0
    new_findings_sample: List[SampleFinding] = []
    resolved_findings_sample: List[SampleFinding] = []


# ---- Timeline (Phase 64 TREND-01) ----

class FindingCounts(BaseModel):
    """Severity-bucketed counts for a single scan session.

    Mirrors the bucket keys produced by quirk.intelligence.trends._count_by_bucket
    (CRITICAL/HIGH -> high, MEDIUM -> medium, LOW -> low; INFO excluded).
    """
    high: int = 0
    medium: int = 0
    low: int = 0


# Phase 66 UI-HIST-02: compare endpoint schemas

def _zero_subscores() -> "SubScores":
    return SubScores(hygiene=0, modern_tls=0, identity_trust=0, agility_signals=0)


class CompareScanSummary(BaseModel):
    scan_id: str
    scanned_at: datetime
    score: int
    subscores: SubScores = Field(default_factory=_zero_subscores)


class SubscoreDelta(BaseModel):
    hygiene: int = 0
    modern_tls: int = 0
    identity_trust: int = 0
    agility_signals: int = 0
    data_at_rest: int = 0
    data_in_motion: int = 0


class CompareFinding(BaseModel):
    host: str
    protocol: Optional[str] = None
    severity: str
    description: Optional[str] = None


class CompareEndpoint(BaseModel):
    host: str
    reason: Optional[str] = None


class CompareResponse(BaseModel):
    scan_a: CompareScanSummary
    scan_b: CompareScanSummary
    score_delta: int
    subscore_deltas: SubscoreDelta
    added_findings: List[CompareFinding] = []
    removed_findings: List[CompareFinding] = []
    endpoints_only_in_a: List[str] = []
    endpoints_only_in_b: List[str] = []
    changed_endpoints: List[CompareEndpoint] = []


class TrendSessionPoint(BaseModel):
    """One point on the multi-scan timeline.

    session_ts is an ISO 8601 datetime string (per D-02).
    subscores reuses the existing SubScores model (per D-06).
    """
    session_ts: str
    score: int
    subscores: SubScores
    finding_counts: FindingCounts


class TrendTimelineResponse(BaseModel):
    """Response for GET /api/trends/timeline (TREND-01).

    sessions are returned newest-first per D-02; the frontend reverses
    before passing to Recharts.
    """
    sessions: List[TrendSessionPoint] = []


# Phase 65 UI-SCAN-01: dashboard-initiated scan submission
class ScanSubmitRequest(BaseModel):
    """POST /api/jobs request body. Pydantic is authoritative validation.

    Per Phase 120 / AC-03, ``allow_internal_targets`` is server-policy only and
    sourced from ``quirk.config.SecurityConfig.allow_internal_targets``; any
    client-supplied value is silently dropped via ``extra="ignore"``.
    """
    model_config = ConfigDict(extra="ignore")

    targets: str = Field(..., min_length=1, max_length=1024)
    profile: Literal["quick", "standard", "deep"] = "standard"
    calibration: Literal["strict", "balanced", "lenient"] = "balanced"
    enable_nmap: bool = False

    # Phase 121: per-scan port scope control (PORT-03, PORT-04)
    port_scope: Literal["common", "top1000", "all", "custom"] = "top1000"
    custom_ports: Optional[str] = None

    @field_validator("targets")
    @classmethod
    def no_file_paths(cls, v: str) -> str:
        """Reject @file targets — CLI-only by design (D-05 defense-in-depth)."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Targets field is required.")
        if stripped.startswith("@"):
            raise ValueError("@file paths are not supported from the dashboard — use the CLI")
        return v

    @model_validator(mode="after")
    def validate_custom_ports(self) -> "ScanSubmitRequest":
        """Require custom_ports when port_scope is 'custom' (PORT-04)."""
        if self.port_scope == "custom":
            if not self.custom_ports or not self.custom_ports.strip():
                raise ValueError(
                    "custom_ports is required when port_scope is 'custom'"
                )
        return self


# Phase 65 UI-SCAN-02: live scan job status
class JobStatusResponse(BaseModel):
    """GET /api/jobs/{id} response body."""
    job_id: str
    status: str            # queued | running | completed | failed | cancelled
    current_stage: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    scan_run_id: Optional[str] = None
    error_message: Optional[str] = None
    stage_index: int       # 0..7, backend-computed
    stage_total: int = 7


# ---- Phase 111 DASH-02 / DASH-03: Sensor registry + merge endpoints ----

class SensorRegistryItem(BaseModel):
    """One enrolled sensor with its current push status."""
    sensor_id: str
    segment: str
    sensor_version: Optional[str] = None
    last_push_at: Optional[datetime] = None
    status: str  # "current" | "stale" | "unknown"


class SensorRegistryResponse(BaseModel):
    """GET /api/sensor/registry response body."""
    sensors: List[SensorRegistryItem]


class MergeLatestData(BaseModel):
    """Payload inside MergeLatestResponse when a merge_run row exists."""
    scan_id: Optional[str] = None
    merged_at: Optional[datetime] = None
    score: Optional[int] = None
    endpoint_count: int = 0
    sensor_count: int = 0
    coverage_warning: Optional[Dict[str, Any]] = None
    per_segment_scores: Dict[str, int] = {}


class MergeLatestResponse(BaseModel):
    """GET /api/merge/latest response body.

    merge is null when no merge_run row exists yet (first-boot / no merges run).
    """
    merge: Optional[MergeLatestData] = None
