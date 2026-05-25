from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey

Base = declarative_base()


class CryptoEndpoint(Base):
    __tablename__ = "crypto_endpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)

    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)

    protocol = Column(String(32), nullable=True)
    scanned_at = Column(DateTime, nullable=True)

    sni_used = Column(Boolean, default=False)

    tls_version = Column(String(64), nullable=True)
    cipher_suite = Column(String(255), nullable=True)

    cert_subject = Column(Text, nullable=True)
    cert_issuer = Column(Text, nullable=True)
    cert_sans = Column(Text, nullable=True)
    cert_sig_alg = Column(String(128), nullable=True)
    cert_pubkey_alg = Column(String(64), nullable=True)
    cert_pubkey_size = Column(Integer, nullable=True)
    cert_not_before = Column(DateTime, nullable=True)
    cert_not_after = Column(DateTime, nullable=True)

    scan_error = Column(Text, nullable=True)
    scan_error_category = Column(String(32), nullable=True)  # Phase 41 D-11 + Phase 57 D-06: missing_extra|timeout|exception|config|invalid_input
    tls_blocker_reason = Column(String(64), nullable=True)
    service_detail = Column(Text, nullable=True)

    # ==========================
    # TLS capability fields
    # ==========================
    tls_supported_versions = Column(Text, nullable=True)        # e.g. "TLSv1,TLSv1.2,TLSv1.3"
    tls_supported_ciphers_sample = Column(Text, nullable=True)  # pipe or comma delimited
    tls_weak_ciphers_present = Column(Boolean, default=False)
    tls_legacy_suites_present = Column(Boolean, default=False)
    tls_pfs_supported = Column(Boolean, default=False)
    tls_enum_mode = Column(String(16), nullable=True)           # "fast" or "deep"
    tls_enum_notes = Column(Text, nullable=True)
    tls_capabilities_json = Column(Text, nullable=True)  # sslyze deep scan results (JSON)

    # ==========================
    # SSH audit fields
    # ==========================
    ssh_audit_json = Column(Text, nullable=True)  # Full ssh-audit JSON output

    # ==========================
    # Scanner fields (JWT/container/source/cloud)
    # ==========================
    jwt_scan_json = Column(Text, nullable=True)        # Full JWKS key entry JSON
    container_scan_json = Column(Text, nullable=True)   # Full syft artifact JSON
    source_scan_json = Column(Text, nullable=True)      # Full semgrep finding JSON
    cloud_scan_json = Column(Text, nullable=True)       # Full cloud resource metadata JSON

    # ==========================
    # Identity scanner fields
    # ==========================
    kerberos_scan_json = Column(Text, nullable=True)  # Full Kerberos scan JSON
    saml_scan_json = Column(Text, nullable=True)       # Full SAML scan JSON
    dnssec_scan_json = Column(Text, nullable=True)     # Full DNSSEC scan JSON
    smime_scan_json = Column(Text, nullable=True)      # Full S/MIME scan JSON (Phase 79 SMIME-03)
    adcs_scan_json = Column(Text, nullable=True)       # Full AD CS scan JSON (Phase 80 ADCS-03)

    # ==========================
    # GCP connector fields
    # ==========================
    gcs_scan_json = Column(Text, nullable=True)        # GCS bucket list JSON (Phase 28 hand-off)

    # ==========================
    # Data-at-Rest fields
    # ==========================
    dat_scan_json = Column(Text, nullable=True)  # Universal DAR scan result JSON (Phase 27+)
    severity = Column(String(16), nullable=True)  # Finding severity: HIGH, MEDIUM, LOW, INFO

    # ==========================
    # Data in Motion fields
    # ==========================
    email_scan_json = Column(Text, nullable=True)  # Per-host email port scan summary JSON (Phase 32)
    broker_scan_json = Column(Text, nullable=True)  # Phase 33 — BROKER-00 (per-scan nested broker probe summary)

    # ==========================
    # TLS finding gap fields
    # ==========================
    chain_verified = Column(Boolean, nullable=True)  # TLS-FIND-06: True/False/None per D-01

    # ==========================
    # Distributed sensor fields (Phase 107 MODEL-01)
    # ==========================
    sensor_id = Column(String(255), nullable=True)   # NULL = implicit local sensor; NO FK (D-03)
    segment   = Column(String(255), nullable=True)


class QRAMMSession(Base):
    """QRAMM assessment session (Phase 51 — QRAMM-01).

    Stores one row per assessment session. score_json holds the persisted
    weakest-link score result computed by POST /api/qramm/sessions/{id}/score.
    """

    __tablename__ = "qramm_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    model_version = Column(String(32), nullable=True)
    profile_id = Column(Integer, nullable=True)  # FK -> qramm_profiles.id (no DB-level constraint; SQLite)
    status = Column(String(32), nullable=True)   # "draft" | "scored" | "complete"
    score_json = Column(Text, nullable=True)     # JSON blob: overall, dimensions, maturity, profile_multiplier


class QRAMMAnswer(Base):
    """QRAMM per-question answer row (Phase 51 — QRAMM-01).

    Phase 53 columns (suggested_answer, confirmed_at, evidence_source) are
    pre-provisioned here per Open Question 2 to avoid ALTER TABLE in Phase 53.
    Phase 51 router does not populate them — they remain NULL.
    """

    __tablename__ = "qramm_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False)  # FK -> qramm_sessions.id (explicit cascade in router)
    question_number = Column(Integer, nullable=False)  # 1-120
    dimension = Column(String(16), nullable=False)     # "CVI" | "SGRM" | "DPE" | "ITR"
    practice_area = Column(String(8), nullable=False)  # "1.1" .. "4.3"
    answer_value = Column(Integer, nullable=True)      # 1-4; NULL until answered
    # Phase 53 columns (QRAMM-13) — pre-provisioned, unused by Phase 51:
    suggested_answer = Column(Integer, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    evidence_source = Column(String(255), nullable=True)
    evidence_note = Column(Text, nullable=True)   # Phase 54 — freeform consultant note per question


class QRAMMProfile(Base):
    """QRAMM organizational profile (Phase 51 — QRAMM-01).

    One row per assessment session. multiplier is the computed Float
    (range 0.8-1.5) applied to dimension scores during overall score
    computation.
    """

    __tablename__ = "qramm_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Phase 70 BLOCK-07/D-03: real DB-level FK (PRAGMA foreign_keys=ON enforces it).
    session_id = Column(
        Integer,
        ForeignKey("qramm_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    industry = Column(String(64), nullable=True)
    org_size = Column(String(32), nullable=True)
    data_sensitivity = Column(String(32), nullable=True)
    regulatory_obligations = Column(Text, nullable=True)  # JSON list of framework codes
    geographic_scope = Column(String(32), nullable=True)
    multiplier = Column(Float, nullable=True)             # 0.8 - 1.5
    created_at = Column(DateTime, nullable=True)


class ScheduledScan(Base):
    """Scheduled scan configuration (Phase 63 — SCHED-01).

    One row per named schedule. The scheduler dispatcher (Plan 02) reads
    enabled rows and dispatches them when cron_expr fires.
    """

    __tablename__ = "scheduled_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    cron_expr = Column(String(128), nullable=False)
    target = Column(String(512), nullable=False)
    profile = Column(String(64), nullable=True)       # None = "balanced"
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)     # None = never run
    created_at = Column(DateTime, nullable=False)


class ScheduledRun(Base):
    """Dispatch run history for a scheduled scan (Phase 63 — SCHED-01).

    One row per dispatch invocation. Plan 02 (scheduler dispatcher) populates
    rows; Plan 03 (dashboard API) exposes them. status lifecycle:
    pending -> running -> completed | failed.
    """

    __tablename__ = "scheduled_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, nullable=False)     # FK -> scheduled_scans.id (no DB-level constraint; SQLite)
    dispatched_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(16), nullable=False)       # pending/running/completed/failed
    scan_output_path = Column(Text, nullable=True)
    scan_id = Column(String(64), nullable=True)       # null until scan completes


class ScanJob(Base):
    """Ad-hoc dashboard-initiated scan job (Phase 65 UI-SCAN-01).

    Each row represents a single subprocess scan dispatched by POST /api/jobs.
    Status lifecycle: queued -> running -> (completed | failed | cancelled).
    """
    __tablename__ = "scan_jobs"

    job_id = Column(String(36), primary_key=True)        # UUID4 generated by API
    pid = Column(Integer, nullable=True)                  # Set after Popen succeeds
    status = Column(String(16), nullable=False)           # queued|running|completed|failed|cancelled
    current_stage = Column(String(32), nullable=True)     # discovery|tls|ssh|api|identity|data_at_rest|reports
    target = Column(String(512), nullable=False)
    profile = Column(String(16), nullable=False)          # quick|standard|deep
    calibration = Column(String(16), nullable=False)      # strict|balanced|lenient
    enable_nmap = Column(Boolean, default=False, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    scan_run_id = Column(String, nullable=True)           # CryptoEndpoint scan_run_id on completion
    error_message = Column(Text, nullable=True)


class ScanCheckpoint(Base):
    """Phase 67 RESUME-01: per-stage checkpoint for resumable scans.

    One row per stage per scan_run_id. Stage completes → row written.
    Resume reads completed rows to skip already-finished stages.
    status values: completed | partial | failed | skipped
    stage values:  inventory | tls | ssh | api | identity |
                   data_at_rest | broker_email | reports
    """
    __tablename__ = "scan_checkpoints"

    checkpoint_id   = Column(Integer, primary_key=True, autoincrement=True)
    scan_run_id     = Column(String, nullable=False, index=True)
    stage           = Column(String(32), nullable=False)
    status          = Column(String(16), nullable=False)
    completed_at    = Column(DateTime, nullable=False)
    endpoint_count  = Column(Integer, nullable=False, default=0)
    partial_failure = Column(Boolean, nullable=False, default=False)
    error_summary   = Column(Text, nullable=True)   # JSON array or NULL


class IntegrationDelivery(Base):
    """Phase 101 NOTIFY-07 / ISEC-03: delivery audit log for all integration phases.

    Shared by Phases 103 (SIEM), 104 (Jira), 105 (ServiceNow).
    error_summary is always safe_str(exc) — never a raw exception.
    """

    __tablename__ = "integration_deliveries"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    scan_id       = Column(String(64), nullable=False, index=True)  # ISO ts from current_session_ts
    finding_hash  = Column(String(64), nullable=True)               # SHA256 dedup key (future phases)
    destination   = Column(String(64), nullable=False)              # "slack" | "email" | "webhook"
    status        = Column(String(16), nullable=False)              # "ok" | "failed"
    attempted_at  = Column(DateTime,   nullable=False)
    error_summary = Column(Text,       nullable=True)               # safe_str(exc) — never raw exc


class Sensor(Base):
    """Distributed sensor registration record (Phase 107 — MODEL-02).

    One row per enrolled remote sensor. sensor_id is a UUID generated at
    enrollment time (Phase 108). last_push_at is updated on each accepted push
    (Phase 109). expected_cadence_minutes is set at enrollment and used by the
    console to detect silent sensors.

    No relationship() declarations — project uses plain Column style exclusively.
    """

    __tablename__ = "sensors"

    sensor_id                = Column(String(36), primary_key=True)        # UUID4 minted at enrollment
    segment                  = Column(String(255), nullable=False)          # network segment label
    engagement               = Column(String(255), nullable=True)           # optional engagement tag
    enrolled_at              = Column(DateTime,    nullable=False)           # enrollment timestamp
    last_push_at             = Column(DateTime,    nullable=True)            # None until first push
    expected_cadence_minutes = Column(Integer,     nullable=False)           # heartbeat interval
    sensor_version           = Column(String(255), nullable=True)            # sensor software version


class SensorToken(Base):
    """One-time enrollment token hash for a sensor (Phase 107 — MODEL-03).

    Stores only the SHA-256 hex digest of the raw token; the raw token is
    printed once at enrollment time and never persisted (Phase 108 / D-02).
    token_hash is 64 characters — the exact hex width of SHA-256.

    sensor_id FK uses ON DELETE CASCADE (D-04): token records are removed
    automatically when the parent sensor is deleted (re-enrollment mints a
    fresh sensor_id).
    """

    __tablename__ = "sensor_tokens"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    sensor_id  = Column(
        String(36),
        ForeignKey("sensors.sensor_id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64),  nullable=False, unique=True)  # SHA-256 hex; raw token never stored
    created_at = Column(DateTime,    nullable=False)


class SensorPush(Base):
    """Accepted push deduplication record (Phase 107 — MODEL-04).

    One row per accepted payload_id. payload_id is unique (D-07): the ingestion
    endpoint (Phase 109) returns 409 Conflict on a duplicate payload_id.
    Rows are retained indefinitely in v5.4 (no TTL/cleanup job — D-10).

    sensor_id FK uses ON DELETE CASCADE (D-04): push records are removed
    automatically when the parent sensor is deleted.
    """

    __tablename__ = "sensor_pushes"

    id          = Column(Integer,    primary_key=True, autoincrement=True)
    payload_id  = Column(String(64), nullable=False, unique=True)   # unique → 409 dedup in Phase 109
    sensor_id   = Column(
        String(36),
        ForeignKey("sensors.sensor_id", ondelete="CASCADE"),
        nullable=False,
    )
    received_at = Column(DateTime,   nullable=False)
