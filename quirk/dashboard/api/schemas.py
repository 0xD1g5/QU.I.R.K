"""Pydantic response models for the QU.I.R.K. dashboard API.

These models define the contract between FastAPI and the React frontend.
TypeScript types in src/dashboard/src/types/api.ts must mirror these exactly.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# SCORE-03 / D-03a: the single stamping contract that attaches a UTC offset
# to every instant-bearing field at the JSON serialization boundary only —
# see quirk/dashboard/api/_timestamp_utils.py for the full rationale.
from ._timestamp_utils import UTCDateTime


class HealthResponse(BaseModel):
    status: str  # "ok"


class ConfigResponse(BaseModel):
    vertical: str  # "general" | "healthcare"


# Phase 192 / PARITY-01: GET /api/config/effective response shapes. Frozen
# interfaces — Plan 10 (scan-new.tsx panel) consumes this shape directly.

class ConfigField(BaseModel):
    name: str
    value: Any
    provenance: Literal["default", "user", "preset"]
    redacted: bool
    credential_status: Optional[Literal["set", "not set"]] = None


class ConfigSection(BaseModel):
    name: str
    title: str
    fields: List[ConfigField]


class ConfigEffectiveResponse(BaseModel):
    vertical: str
    profile: str
    sections: List[ConfigSection]
    raw: dict
    redacted_field_count: int


# Phase 193 / PARITY-02: GET /api/connectors/availability response shapes.
# Frozen interfaces -- plan 04's route and plan 07's React panel consume
# these shapes directly.

class ConnectorAvailabilityEntry(BaseModel):
    flag: str            # "enable_adcs"
    label: str            # "AD CS"
    category: str         # one of the six 193-UI-SPEC categories
    available: bool
    reason: str = ""          # non-empty whenever available is False
    install_hint: str = ""    # verbatim optional_extra.REGISTRY install_hint, "" when none


class ConnectorAvailabilityResponse(BaseModel):
    connectors: List[ConnectorAvailabilityEntry]
    unavailable_count: int


# ---- Score / Confidence ----

class SubScores(BaseModel):
    # Phase 188 SCORE-06 (RQ-3 schema-compatibility check): each subscore is
    # None when compute_readiness_score() excluded that category as
    # unassessed (exclude-and-rescale) rather than a fabricated 0-25 value.
    hygiene: Optional[int] = None
    modern_tls: Optional[int] = None
    identity_trust: Optional[int] = None
    agility_signals: Optional[int] = None
    data_at_rest: Optional[int] = None
    data_in_motion: Optional[int] = None   # NEW — Phase 36 D-06


class ScoreData(BaseModel):
    # Phase 188 SCORE-06 (RQ-3 schema-compatibility check): None means "not
    # computed" — zero domains were assessed (compute_readiness_score()'s
    # explicit honest-absence edge case), never a fabricated 0/100.
    score: Optional[int] = None
    rating: str  # EXCELLENT / GOOD / MODERATE / FAIR / POOR / NOT_ASSESSED
    # SCORE-04 / D-09/D-10 (184.4): structured cap-reason from
    # compute_readiness_score()'s rating_cap_reason key, mirroring the
    # confidence_formula_version precedent immediately below. None means the
    # band was NOT capped — an absent reason is a positive statement, not
    # missing data.
    rating_cap_reason: Optional[str] = None
    subscores: SubScores
    drivers: List[Dict[str, Any]]
    # Phase 188 SCORE-06 — coverage/version disclosure, additive keys on
    # score_raw. Defaults keep this model backward-compatible for any caller
    # still constructing ScoreData from a pre-188-shaped dict.
    domains_assessed: Optional[int] = None
    domains_total: Optional[int] = None
    score_divisor: Optional[float] = None
    coverage_disclosure: Optional[str] = None
    scoring_version: Optional[str] = None
    scoring_version_note: Optional[str] = None


class ConfidenceData(BaseModel):
    confidence_score: int
    confidence_rating: str  # HIGH / MEDIUM / LOW / VERY_LOW / NO_DATA
    # 184.1-06 / SC-3 / D-12: optional-with-default keeps the model backward
    # compatible for callers that do not supply it; None on the compute-failure
    # fallback path (an unmarked response on failure is honest, per D-15).
    confidence_formula_version: Optional[str] = None
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
    cert_not_after: Optional[UTCDateTime] = None
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


class HardwareComponent(BaseModel):
    """Minimal hardware device entry for the CBOM tab Hardware Inventory section.

    CBOM-02 D-02: originally exactly six fields — no SNMP fields, no
    confidence, no fingerprint_method.  sensor_id/segment deferred
    (HardwareDevice has no sensor_id column yet).

    Phase 139 SNMPV3-02: intentionally extends the six-field lock with three
    optional SNMPv3 metadata fields (protocol NAMES only, never secrets) —
    all Optional[str] = None, so existing six-field construction call sites
    remain fully backward-compatible.
    """

    host: str
    port: int
    vendor: str
    model: str
    pqc_status: str
    remediation_tier: str
    snmp_version: Optional[str] = None
    snmp_auth_protocol: Optional[str] = None
    snmp_priv_protocol: Optional[str] = None
    bridge_status: Optional[str] = None  # Phase 140 BRIDGE-03 — dashboard bridge badge
    # Phase 141 OTICS-05/D-12: nullable Modbus/BACnet fingerprint metadata
    modbus_vendor: Optional[str] = None
    modbus_model: Optional[str] = None
    modbus_firmware: Optional[str] = None
    modbus_probe_state: Optional[str] = None
    bacnet_vendor: Optional[str] = None
    bacnet_model: Optional[str] = None
    bacnet_firmware: Optional[str] = None
    bacnet_probe_state: Optional[str] = None


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


# ---- Hardware Findings (Phase 128 HWCOMPAT-07) ----

class HardwareFinding(BaseModel):
    # Universal baseline (mirrors MotionFinding / DarFinding baseline)
    host: str
    port: int
    severity: str
    title: str
    description: Optional[str] = None
    remediation: Optional[str] = None
    quantum_risk: Optional[str] = None

    # Hardware-specific fields (D-11)
    vendor: str
    model: Optional[str] = None
    pqc_status: str
    remediation_tier: str
    confidence: str
    fingerprint_method: str
    eol_date: Optional[str] = None
    snmp_version: Optional[str] = None  # Phase 139 SNMPV3-02 — dashboard SNMP badge
    bridge_status: Optional[str] = None  # Phase 140 BRIDGE-03 — dashboard bridge badge
    # Phase 141 OTICS-05/D-12: nullable Modbus/BACnet fingerprint metadata
    modbus_vendor: Optional[str] = None
    modbus_model: Optional[str] = None
    modbus_firmware: Optional[str] = None
    modbus_probe_state: Optional[str] = None
    bacnet_vendor: Optional[str] = None
    bacnet_model: Optional[str] = None
    bacnet_firmware: Optional[str] = None
    bacnet_probe_state: Optional[str] = None
    # Phase 142 CVE-01/D-04/D-08: nullable CVE correlation metadata (advisory-only)
    cve_matches: Optional[list[dict]] = None
    cve_confidence: Optional[str] = None
    cve_attempted: Optional[bool] = None


# ---- Hardware Lifecycle Drift (Phase 156 HWLC-10/11) ----

# V5 input-validation: the three direction literals a drift event may carry.
# Sourced here (not re-derived) so HardwareDriftEventItem's validator has a
# single place to check against.
DRIFT_DIRECTIONS: tuple[str, ...] = ("improved", "worsened", "neutral")


class HardwareDriftEventItem(BaseModel):
    """One serialized ``HardwareDriftEvent`` row (Phase 155) for the
    dashboard API.

    Deliberately has NO ``severity`` field (D-06): a drift event is a
    lifecycle change, not a scored finding, and must never inherit
    finding-shaped severity semantics that could feed finding-shaped
    sorting/scoring aggregation downstream.
    """
    host: str
    port: int
    event_type: str              # tier_crossing | upstream_mitigated_change | cve_delta | eol_state_change
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    direction: str                # improved | worsened | neutral (D-06 — NOT severity)
    detected_at: str              # ISO 8601
    vendor: Optional[str] = None
    model: Optional[str] = None
    # Phase 159 HWLC-13: True when the triggering HardwareDevice row came
    # from a --check-in partial re-probe; NULL/absent device rows read as
    # False. Badge, not filter (D-159-I) — check-in-sourced drift events
    # keep appearing on every drift surface, just labeled.
    is_partial_scan: bool = False

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, v: str) -> str:
        if v not in DRIFT_DIRECTIONS:
            raise ValueError(f"direction must be one of {DRIFT_DIRECTIONS}, got {v!r}")
        return v

    @field_validator("event_type")
    @classmethod
    def _validate_event_type(cls, v: str) -> str:
        from quirk.scanner.hardware_drift import EVENT_TYPES
        if v not in EVENT_TYPES:
            raise ValueError(f"event_type must be one of {EVENT_TYPES}, got {v!r}")
        return v


class HardwareDriftResponse(BaseModel):
    """GET /api/hardware/drift response body (HWLC-10)."""
    has_prior_scan: bool
    latest_scan_at: Optional[str] = None
    latest_events: List[HardwareDriftEventItem] = []
    historical_events: List[HardwareDriftEventItem] = []
    historical_truncated: bool = False


# ---- Catalog-Level PQC Vendor Trend Tracking (Phase 160 HWLC-17) ----


class VendorPqcTrendEventItem(BaseModel):
    """One serialized ``VendorPqcTrendEvent`` row for the dashboard API.

    Read-only, advisory-only projection of a confirmed, fleet-wide vendor
    PQC-status transition — never feeds the readiness score. Deliberately
    has NO ``host``/``port`` field (vendor-scoped, not device-scoped) and
    NO score/numeric field.
    """
    vendor: str
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detected_at: UTCDateTime
    confirmed_at: Optional[UTCDateTime] = None


class VendorPqcTrendResponse(BaseModel):
    """GET /api/hardware/vendor-trends response body (Phase 160 HWLC-17).

    Read-only, advisory-only, bounded projection — never feeds the
    readiness score.
    """
    events: List[VendorPqcTrendEventItem] = []
    truncated: bool = False


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
    # Phase 181 SURF-03: persisted closure state, joined by slug (never by
    # the display `id` above, which is regenerated per-response and has no
    # stable identity). None when the item has no db-backed lookup available
    # (no db/scan_run_id supplied) or its title maps to no known slug.
    closure_state: Optional[str] = None   # open | closed | not_observed | resurfaced
    slug: Optional[str] = None            # the slug_for_title() join key, or None


class RoadmapData(BaseModel):
    nodes: List[RoadmapNode]
    edges: List[RoadmapEdge]


# ---- Closure Burndown (Phase 181 SURF-03) ----


class BurndownBucket(BaseModel):
    """One per-deadline burndown bucket (mirrors quirk.intelligence.burndown).

    D-36 (burndown.py): buckets OVERLAP by design and are NEVER summed — a
    fingerprint late against both the key-establishment and digital-signature
    deadlines is counted in both. Deliberately NO `total`, NO `percent`, NO
    `severity`, NO `host`, NO `port` field: any aggregate here would
    re-introduce the single-scalar failure CLOSE-03 eliminated, and a
    host/port/severity field would pull this advisory-only payload back
    toward the findings/scoring chokepoint.
    """
    bucket: str                       # "key_establishment" | "digital_signature" | "unmapped"
    date: Optional[str] = None        # "2030-12-31" | "2031-12-31" | None for unmapped
    standard: Optional[str] = None
    fingerprints: int = 0
    open: int = 0
    closed: int = 0
    not_observed: int = 0
    resurfaced: int = 0
    open_like: int = 0


class ClosureBurndown(BaseModel):
    """GET /api/scan/latest `burndown` field (Phase 181 SURF-03).

    Advisory-only, read-only projection of `compute_burndown()`. When no
    `RemediationItemFingerprint` rows exist for the scan, `buckets` is empty
    and `unavailable_reason` explains why — never a zero-filled table, which
    would misread as "nothing to remediate" rather than "not measured".
    """
    buckets: List[BurndownBucket] = []
    unavailable_reason: Optional[str] = None


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
    scanned_at: Optional[UTCDateTime] = None
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
    hardware_findings: List[HardwareFinding] = []  # Phase 128 HWCOMPAT-07
    hardware_devices: List[HardwareComponent] = []   # Phase 134 CBOM-02
    partial_failures: List[PartialFailureEntry] = []  # Phase 67 RESUME-02
    burndown: Optional[ClosureBurndown] = None        # Phase 181 SURF-03
    # Phase 194 DASH-09 / D-13: count of TLS endpoints excluded from
    # `certificates` because they lacked a cert_subject or carried a
    # scan_error (phantom rows — failed handshakes, not real certificates).
    # Default 0 (not Optional[...] = None) — "nothing excluded" is the
    # honest reading for any caller/fixture that does not set it, mirroring
    # the Phase 188 coverage_disclosure additive-default precedent.
    excluded_cert_count: int = 0


class ScanSession(BaseModel):
    scan_id: str          # ISO timestamp string (matches ScanMeta.scan_id)
    scanned_at: UTCDateTime
    total_endpoints: int
    # Phase 66 UI-HIST-01 additions — all Optional/default for backward compat with ScanSelector
    # 188 review CR-04: Optional[int], mirroring CompareScanSummary.score —
    # None means the scan's score was not computed (zero domains assessed),
    # never a fabricated 0 (which would read as worst-case POOR beside a
    # rating of "NOT_ASSESSED" in the scan-history list).
    score: Optional[int] = None
    profile: Optional[str] = None
    calibration: Optional[str] = None
    target: Optional[str] = None
    finding_counts: "FindingCounts" = Field(default_factory=lambda: FindingCounts())
    # SCORE-04 / D-07 (184.4-07): the session-history rating and its optional cap
    # reason, mirroring ScoreData.rating / ScoreData.rating_cap_reason (D-09).
    # `rating` defaults to "" (not a real band) for pre-fix rows that somehow
    # bypass scoring; `rating_cap_reason` absent/None means NOT capped.
    rating: str = ""
    rating_cap_reason: Optional[str] = None


# Trend Analysis (Phase 31)

class SampleFinding(BaseModel):
    """Mirrors quirk.intelligence.trends.SampleFindingItem.

    ``severity`` is Optional because ``CryptoEndpoint.severity`` is
    ``nullable=True`` (models.py) and is written ONLY by the cloud connectors
    (aws/azure/k8s) — TLS, SSH, container, email, and source endpoints leave it
    NULL, which is correct rather than missing data. ``_sample_findings`` in
    quirk/intelligence/trends.py deliberately includes such rows: "a row is
    included whenever its endpoint identity is in target_keys, regardless of
    its severity (including None)" (D-03). Declaring this ``str`` made the
    schema stricter than the contract it mirrors and 500'd GET /api/trends on
    any database whose endpoints came from non-cloud scanners. Sibling model
    SeverityTransitionResponse below already had this right.
    """

    host: str
    port: int
    protocol: str
    severity: Optional[str] = None


class SeverityTransitionResponse(BaseModel):
    """Mirrors quirk.intelligence.trends.SeverityTransitionItem — an endpoint
    whose severity changed between two sessions without its identity
    changing (replaces the old severity-in-key double-count, D-03)."""
    host: str
    port: int
    protocol: str
    previous_severity: Optional[str] = None
    current_severity: Optional[str] = None


class TrendReportResponse(BaseModel):
    current_session_ts: Optional[UTCDateTime] = None
    previous_session_ts: Optional[UTCDateTime] = None
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
    severity_transitions: List[SeverityTransitionResponse] = Field(default_factory=list)
    new_total: int = 0
    resolved_total: int = 0


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
    scanned_at: UTCDateTime
    # Phase 188 SCORE-06 (RQ-3 schema-compatibility check): None means the
    # scan's score was not computed (zero domains assessed) -- never a
    # fabricated 0.
    score: Optional[int] = None
    subscores: SubScores = Field(default_factory=_zero_subscores)
    # SCORE-04 / D-07 (184.4-07): per-side rating + optional cap reason, so
    # /compare can prove the two sides' bands independently — a shared or
    # swapped findings basis between sides would otherwise be invisible to
    # any test that only checks the numeric score_delta.
    rating: str = ""
    rating_cap_reason: Optional[str] = None


class SubscoreDelta(BaseModel):
    # Phase 188 SCORE-06 (RQ-3 schema-compatibility check): None means the
    # delta could not be computed because the category was unassessed on
    # at least one side being compared -- never a fabricated 0 delta.
    hygiene: Optional[int] = None
    modern_tls: Optional[int] = None
    identity_trust: Optional[int] = None
    agility_signals: Optional[int] = None
    data_at_rest: Optional[int] = None
    data_in_motion: Optional[int] = None


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
    # Phase 188 SCORE-06 (RQ-3 schema-compatibility check): None means one or
    # both sides had no computed score -- never a fabricated 0 delta.
    score_delta: Optional[int] = None
    subscore_deltas: SubscoreDelta
    added_findings: List[CompareFinding] = []
    removed_findings: List[CompareFinding] = []
    endpoints_only_in_a: List[str] = []
    endpoints_only_in_b: List[str] = []
    changed_endpoints: List[CompareEndpoint] = []
    hardware_drift: List[HardwareDriftEventItem] = []  # Phase 156 HWLC-10/D-04


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

    Phase 193 / PARITY-02 / PARITY-03 (D-11, D-13): ``connectors`` and
    ``credentials`` are deliberately SEPARATE fields, never merged into one
    dict, so a stray log of the connectors toggle map can never leak a
    secret. ``connectors`` is a delta of only the ``enable_*`` toggles the
    operator explicitly touched in this request (D-13) -- it is merged into
    the job's config overlay, never treated as a full replacement of
    ``ConnectorsCfg``. ``credentials`` values are request-scoped only: they
    are never assigned to a ``ScanJob`` column, never written to the job's
    ``config.yaml``, and never passed to a logger (D-11) -- they exist only
    to be injected into the scan subprocess's environment.
    """
    model_config = ConfigDict(extra="ignore")

    targets: str = Field(..., min_length=1, max_length=1024)
    profile: Literal["quick", "standard", "deep"] = "standard"
    calibration: Literal["strict", "balanced", "lenient"] = "balanced"
    enable_nmap: bool = False

    # Phase 121: per-scan port scope control (PORT-03, PORT-04)
    port_scope: Literal["common", "top1000", "all", "custom"] = "top1000"
    custom_ports: Optional[str] = None

    # Phase 193 / PARITY-02 (D-13): delta-only connector toggle overlay, key
    # = enable_* flag name.
    connectors: Optional[Dict[str, bool]] = None
    # Phase 193 / PARITY-03 (D-09/D-10/D-11): request-scoped credential
    # values, NEVER persisted -- see class docstring.
    credentials: Optional[Dict[str, str]] = None

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

    @field_validator("connectors")
    @classmethod
    def known_connector_toggle_keys_only(
        cls, v: Optional[Dict[str, bool]]
    ) -> Optional[Dict[str, bool]]:
        """Allowlist submitted connector keys against ConnectorsCfg's own
        field set (D-13 + ASVS V5). Rejects rather than silently drops, so
        the operator learns their toggle did nothing. Also requires an
        ``enable_`` prefix so non-toggle connector fields (e.g.
        ``adcs_password``, ``broker_targets``) can never be smuggled
        through the boolean toggle path.

        Imported inside the validator body (not at module scope) to avoid a
        circular import between quirk.dashboard.api.schemas and quirk.config.
        """
        if v is None:
            return v
        from quirk.config import _KNOWN_CONNECTOR_KEYS

        if len(v) > len(_KNOWN_CONNECTOR_KEYS):
            raise ValueError(
                f"connectors payload has {len(v)} entries, more than the "
                f"{len(_KNOWN_CONNECTOR_KEYS)} known connector fields"
            )
        unknown = sorted(k for k in v if k not in _KNOWN_CONNECTOR_KEYS)
        if unknown:
            raise ValueError(f"Unknown connector key(s): {', '.join(unknown)}")
        non_toggle = sorted(k for k in v if not k.startswith("enable_"))
        if non_toggle:
            raise ValueError(
                f"connectors only accepts enable_* toggle keys, got: "
                f"{', '.join(non_toggle)}"
            )
        return v

    @field_validator("credentials")
    @classmethod
    def known_credential_keys_only(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Allowlist submitted credential names against
        ``CREDENTIAL_REGISTRY`` (D-10), plus the ``broker:<host>`` and
        ``snmpv3:<host>:<auth|priv>`` per-host shapes plan 06 injects.
        Rejects unknown keys and explicitly rejects ``api_token`` -- the
        dashboard's own API token is never a scan-submission credential.
        """
        if v is None:
            return v
        from quirk.config_redaction import CREDENTIAL_REGISTRY

        if len(v) > 64:
            raise ValueError(
                f"credentials payload has {len(v)} entries, more than the 64-entry cap"
            )
        for key, value in v.items():
            if len(value) > 4096:
                raise ValueError(
                    f"credential value for {key!r} exceeds the 4096-character cap"
                )

        allowed_names = {
            entry.name for entry in CREDENTIAL_REGISTRY if entry.section == "connectors"
        }
        # Phase 193 review CR-03: `username` added — carries the USM
        # username (identifier, not a secret; lands inline in the job YAML's
        # snmp_v3_credentials fragment, never the subprocess env).
        snmpv3_re = re.compile(r"^snmpv3:.+:(auth|priv|username)$")

        unknown = []
        for key in v:
            if key == "api_token":
                unknown.append(key)
                continue
            if key in allowed_names:
                continue
            if key.startswith("broker:"):
                continue
            if snmpv3_re.match(key):
                continue
            unknown.append(key)
        if unknown:
            raise ValueError(f"Unknown credential key(s): {', '.join(sorted(unknown))}")
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
    # Phase 146 DISC-04: nmap discovery batch-progress fields. None until the
    # first discovery batch completes.
    discovery_batch_index: Optional[int] = None
    discovery_batch_total: Optional[int] = None
    discovery_hosts_checked: Optional[int] = None


# ---- Phase 111 DASH-02 / DASH-03: Sensor registry + merge endpoints ----

class SensorRegistryItem(BaseModel):
    """One enrolled sensor with its current push status."""
    sensor_id: str
    segment: str
    sensor_version: Optional[str] = None
    last_push_at: Optional[UTCDateTime] = None
    status: str  # "current" | "stale" | "unknown"


class SensorRegistryResponse(BaseModel):
    """GET /api/sensor/registry response body."""
    sensors: List[SensorRegistryItem]


class MergeLatestData(BaseModel):
    """Payload inside MergeLatestResponse when a merge_run row exists."""
    scan_id: Optional[str] = None
    merged_at: Optional[UTCDateTime] = None
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


# ---- Scan Coverage (Phase 192 Plan 09 / OBS-02) ----
# Mirrors quirk/reports/coverage.py::load_scan_coverage's frozen payload shape
# verbatim — the dashboard and the report pipeline read the same loader.

class ScanCoveragePhase(BaseModel):
    phase_name: str
    label: str
    status: str
    reason: Optional[str] = None
    detail: Optional[str] = None
    duration_sec: Optional[float] = None


class ScanCoverageResponse(BaseModel):
    recorded: bool
    ran: int
    skipped: int
    phases: List[ScanCoveragePhase]
