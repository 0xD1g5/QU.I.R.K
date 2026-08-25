from __future__ import annotations

from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Text, Float, ForeignKey

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
    scan_error_category = Column(String(32), nullable=True)  # Phase 41 D-11 + Phase 57 D-06 + Phase 145 D-05: missing_extra|timeout|exception|config|invalid_input|liveness_skip|privilege_fallback
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
    smime_scan_json = Column(Text, nullable=True)      # Full S/MIME scan JSON (Phase 79 SMIME-03) — genuine S/MIME scanner only
    codesign_scan_json = Column(Text, nullable=True)   # Full code-signing scan JSON (Phase 130 AUDIT-01) — smime_scan_json retained for SMIME protocol
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

    # RVW-003: stored scan-session identity. Set to the run's `started_utc`
    # ISO timestamp — the same value ScanJob.scan_run_id and
    # ScanCheckpoint.scan_run_id already carry, and stable across --resume-scan-id.
    # Read paths group on this instead of truncating `scanned_at`, which cannot
    # work: each stage stamps its own rows as it runs, so one scan's rows span
    # many seconds. Nullable for rows written before this column existed — those
    # fall back to the legacy timestamp grouping. NO FK (mirrors sensor_id/D-03:
    # a CryptoEndpoint may be written by a CLI scan that never created a ScanJob).
    scan_run_id = Column(String(64), nullable=True, index=True)


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

    # Phase 162 HWLC-20 / D-01: this schedule dispatches a lightweight check-in
    # re-probe (`run_scan --check-in`) rather than a scored profile scan.
    # A dedicated boolean rather than a `profile="check-in"` sentinel: every
    # other consumer of `profile` feeds it to `run_scan --profile`, which accepts
    # only quick|standard|deep — putting an invalid value there is exactly the
    # confusion that made every default-profile schedule fail at argparse
    # (SCHED-02, fixed in ac219e4). NULL reads as False.
    check_in = Column(Boolean, default=False, nullable=True)


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
    # Phase 146 DISC-04: nmap discovery batch-progress fields. All nullable —
    # null until the first discovery batch completes; never overload
    # current_stage (jobs.py::_stage_index does an exact-match lookup on it).
    discovery_batch_index = Column(Integer, nullable=True)
    discovery_batch_total = Column(Integer, nullable=True)
    discovery_hosts_checked = Column(Integer, nullable=True)


class ScanCheckpoint(Base):
    """Phase 67 RESUME-01: per-stage checkpoint for resumable scans.

    One row per stage per scan_run_id. Stage completes → row written.
    Resume reads completed rows to skip already-finished stages.
    status values: completed | partial | failed | skipped
    stage values:  discovery | inventory | tls | ssh | api | identity |
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
    revoked_at = Column(DateTime,    nullable=True)   # None = active; set = revoked (Phase 113 AUTH-02 / D-06)


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


class MergeRun(Base):
    """Merged scan result record (Phase 110 — MERGE-05).

    One row per merge_scan() execution. coverage_warning_json is NULL when
    all enrolled sensors are current, else a JSON object with missing_sensors
    and reason. Phase 111 dashboard reads this table to display the coverage
    banner.

    No relationship() declarations — project uses plain Column style exclusively.
    """

    __tablename__ = "merge_runs"

    id                    = Column(Integer,    primary_key=True, autoincrement=True)
    scan_id               = Column(String(64), nullable=False, index=True)   # ISO merge timestamp
    merged_at             = Column(DateTime,   nullable=False)
    endpoint_count        = Column(Integer,    nullable=False, default=0)
    sensor_count          = Column(Integer,    nullable=False, default=0)
    score                 = Column(Integer,    nullable=True)
    coverage_warning_json = Column(Text,       nullable=True)  # JSON or NULL


class HardwareDriftEvent(Base):
    """Persisted hardware lifecycle drift-event record (Phase 155 — HWLC-04/05/06/07/09).

    One row per confirmed drift transition for a (host, port) device — a
    detected change in remediation tier, upstream-mitigated bridge status,
    correlated firmware CVE set, or EOL/EOS lifecycle state. Rows are written
    only once a change has been confirmed across the N-of-M history window
    (D-02/D-03), not on every scan.

    No relationship() declarations — project uses plain Column style exclusively.

    event_type values: tier_crossing | upstream_mitigated_change | cve_delta | eol_state_change

    old_value/new_value are short enum/scalar transition values only
    (String(255)) — never raw probe payloads. Do NOT store raw_banner,
    bridge_evidence_json, SNMP community strings, or any other raw probe
    payload in these columns (T-155-03). event_type is validated at the write
    site against an explicit allowlist constant (never free text) — the V5
    input-validation control from RESEARCH.md's Security Domain; the
    allowlist itself lives in hardware_drift.py (plan 155-03).

    is_partial_scan (Phase 159 WR-03 fix): captured at insert time by
    ``reconcile_device_history()`` from the ``HardwareDevice`` row that
    actually produced this event (``rows[0].is_partial_scan``), NOT derived
    later via a join against the device's current-state row. This makes the
    dashboard's "Partial re-probe" badge provenance-correct and immune to a
    later scan changing the device's own is_partial_scan value — without
    this column, joining historical/windowed drift events against a single
    current-state device snapshot can silently flip the badge for events
    that predate the most recent scan. Nullable/no DDL default, same
    coercion convention as HardwareDevice.is_partial_scan: NULL reads as
    False via bool(getattr(row, "is_partial_scan", False)), never a bare
    passthrough.
    """

    __tablename__ = "hardware_drift_events"

    id           = Column(Integer,     primary_key=True, autoincrement=True)
    host         = Column(String(255), nullable=False, index=True)
    port         = Column(Integer,     nullable=False)
    event_type   = Column(String(32),  nullable=False)
    old_value    = Column(String(255), nullable=True)
    new_value    = Column(String(255), nullable=True)
    detected_at  = Column(DateTime,    nullable=False)
    confirmed_at = Column(DateTime,    nullable=True)
    is_partial_scan = Column(Boolean,  nullable=True)


class VendorPqcTrendEvent(Base):
    """Persisted catalog-level, vendor-scoped PQC-status trend event
    (Phase 160 — HWLC-17).

    One row per confirmed HARDWARE_MATRIX-derived ``pqc_status`` transition
    for a VENDOR (fleet-wide, cross-device, cross-host) — distinct from
    ``hardware_drift_events``, which is per-(host, port) device-scoped.
    Deliberately has NO ``host``/``port`` columns: rows here summarize a
    vendor's fleet, never a single device.

    No relationship() declarations — project uses plain Column style
    exclusively.

    event_type values: ``pqc_status_change``, validated at the write site
    against the ``VENDOR_EVENT_TYPES`` allowlist in
    ``quirk/scanner/hardware_drift.py`` — never free text (V5 input
    validation, mirrors T-155-03).

    old_value/new_value are ``String(32)`` scalar enum values only (matching
    ``HardwareDevice.pqc_status``'s own column width) — never raw banners,
    never free text.

    ASSUMPTION for future catalog maintainers: vendor-level and device-level
    ``pqc_status`` are equivalent today only because ``HARDWARE_MATRIX``
    currently holds exactly one entry per vendor (8 entries, 8 distinct
    vendors, verified 2026-08-18) — this is a DATA property, not a schema
    guarantee. A future catalog edit adding a second entry for an existing
    vendor with a different ``pqc_status`` must be reviewed against this
    coupling before shipping (RESEARCH.md Pitfall 2 / Assumption A2).
    """

    __tablename__ = "vendor_pqc_trend_events"

    id           = Column(Integer,     primary_key=True, autoincrement=True)
    vendor       = Column(String(255), nullable=False, index=True)
    event_type   = Column(String(32),  nullable=False)
    old_value    = Column(String(32),  nullable=True)
    new_value    = Column(String(32),  nullable=True)
    detected_at  = Column(DateTime,    nullable=False)
    confirmed_at = Column(DateTime,    nullable=True)


class HardwareDevice(Base):
    """Agentless hardware fingerprint record (Phase 127 — HWCOMPAT-01).

    Populated by quirk/scanner/hardware_scanner.py from SSH banners and HTTP
    management interface probes. Advisory-only: no score impact (D-01).

    No relationship() declarations — project uses plain Column style exclusively.
    pqc_status values: supported | partial | unsupported | unknown | VENDOR-SILENT
    confidence values: high | medium | low | unknown
    fingerprint_method values: ssh_banner | http_mgmt | unknown
    match_confidence values: high | low
    probe_status values: success | failed

    Note: match_confidence (Phase 154 HWLC-01/02) is cross-scan IDENTITY-match
    confidence — how sure we are this row is "the same device" as a prior
    scan's row — and is deliberately distinct from confidence (probe-RESULT
    confidence). The two are never conflated.

    is_partial_scan values (Phase 159 HWLC-13): True (check-in re-probe) |
    NULL/False (full scan).
    """

    __tablename__ = "hardware_devices"

    id                 = Column(Integer,     primary_key=True, autoincrement=True)
    scan_id            = Column(Integer,     nullable=True)       # FK -> crypto_endpoints.id (no DB constraint; SQLite)
    host               = Column(String(255), nullable=False)
    port               = Column(Integer,     nullable=False)
    vendor             = Column(String(255), nullable=False)      # "Unknown" when unrecognized (D-06)
    model              = Column(String(255), nullable=True)
    pqc_status         = Column(String(32),  nullable=False)      # enum: see class docstring
    eol_date           = Column(Date,        nullable=True)
    confidence         = Column(String(16),  nullable=False)      # enum: see class docstring
    fingerprint_method = Column(String(32),  nullable=False)      # enum: see class docstring
    raw_banner         = Column(Text,        nullable=True)
    scanned_at         = Column(DateTime,    nullable=False)
    remediation_tier   = Column(String(16),  nullable=False, default="Tier N/A")  # Phase 128 D-02
    # Phase 133 SNMP-01/SNMP-03: SNMP fingerprint fields
    # Populated by quirk/scanner/snmp_scanner.py when enable_snmp=True.
    # All fields are nullable — null when SNMP not enabled or target unreachable.
    snmp_sysdescr    = Column(Text,        nullable=True)   # raw sysDescr OID 1.3.6.1.2.1.1.1.0
    snmp_sysname     = Column(String(255), nullable=True)   # sysName OID 1.3.6.1.2.1.1.5.0
    snmp_sysobjectid = Column(String(255), nullable=True)   # sysObjectID OID 1.3.6.1.2.1.1.2.0
    snmp_vendor      = Column(String(255), nullable=True)   # parsed vendor from sysDescr
    # Phase 139 SNMPV3-01: negotiated SNMPv3 session metadata. Protocol NAMES
    # only — never keys/passphrases. snmp_version sized at 24 chars to fit the
    # longest mode label (e.g. "v3-protocol-mismatch", added in 139-02/139-03).
    snmp_version        = Column(String(24), nullable=True)   # e.g. "v1"|"v2c"|"v3"
    snmp_auth_protocol  = Column(String(16), nullable=True)   # e.g. "SHA256" (name only)
    snmp_priv_protocol  = Column(String(16), nullable=True)   # e.g. "AES256" (name only)
    # Phase 140 BRIDGE-02: SNMP-confirmed bridge-mitigation evidence. Both
    # null until a confirmation probe succeeds; populated by the sensor,
    # read by the console annotation and downstream projection sites.
    bridge_evidence_json = Column(Text,     nullable=True)
    bridge_confirmed_at  = Column(DateTime, nullable=True)
    # Phase 141 OTICS-06 / D-14: Modbus/BACnet OT-ICS fingerprint fields.
    # Populated by quirk/scanner/modbus_scanner.py and bacnet_scanner.py when
    # enable_modbus/enable_bacnet=True. All nullable — null when the relevant
    # protocol is not enabled or the target didn't respond. *_firmware columns
    # feed the CBOM FIRMWARE component (D-15). *_probe_state values: see
    # RESEARCH Open Question #3 — identified | no_response | no_match |
    # aborted_anomalous_response (sized 32 to fit the longest label).
    modbus_vendor       = Column(String(255), nullable=True)
    modbus_model        = Column(String(255), nullable=True)
    modbus_firmware     = Column(String(255), nullable=True)
    modbus_probe_state  = Column(String(32),  nullable=True)
    bacnet_vendor       = Column(String(255), nullable=True)
    bacnet_model        = Column(String(255), nullable=True)
    bacnet_firmware     = Column(String(255), nullable=True)
    bacnet_probe_state  = Column(String(32),  nullable=True)
    # Phase 154 HWLC-01/02: cross-scan identity + probe-outcome fields.
    # All nullable — pre-Phase-154 rows keep NULL, never backfilled (D-06).
    ssh_host_key_fingerprint = Column(String(255), nullable=True)  # ssh-audit SHA256 host-key fingerprint, e.g. "SHA256:abc123..."; populated by hardware_scanner.py::fingerprint_one
    match_confidence         = Column(String(16),  nullable=True)  # enum: high | low (D-04/D-05); see class docstring
    probe_status             = Column(String(16),  nullable=True)  # enum: success | failed (D-07)
    # Phase 159 HWLC-13: check-in re-probe marker. NULL means "not a check-in /
    # pre-Phase-159 row" — never backfilled. True = check-in re-probe; NULL/False
    # = full scan.
    is_partial_scan          = Column(Boolean,     nullable=True)
