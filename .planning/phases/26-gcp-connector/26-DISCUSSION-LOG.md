# Phase 26: GCP Connector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 26-gcp-connector
**Areas discussed:** Dependency placement, Cloud SQL TLS detection API, GCS data hand-off, KMS key version enumeration, KMS location scope

---

## Dependency Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Create [cloud] extras now | GCP libs in new [cloud] optional extras group; boto3/azure stay in main deps | ✓ |
| Main deps (match boto3/azure) | Add GCP libs alongside boto3/azure in main dependencies | |
| Full cloud extras refactor | Move boto3 + azure + GCP all into [cloud] extras together | |

**User's choice:** Create [cloud] extras now
**Notes:** boto3 and azure remain in main deps for backward compatibility. [cloud] extras created now so Phase 30 (hvac) can land there too.

---

## Cloud SQL TLS Detection API

| Option | Description | Selected |
|--------|-------------|----------|
| google-api-python-client for all | Single package; uniform call pattern for KMS, Cloud SQL, GCS | ✓ |
| Mixed (dedicated KMS/GCS + discovery for Cloud SQL) | google-cloud-kms + google-cloud-storage + google-api-python-client | |

**User's choice:** google-api-python-client for all 3 GCP services
**Notes:** User initially wanted to understand differences between dedicated clients vs discovery API. After analysis: no clean dedicated admin client exists for Cloud SQL (google-cloud-sql-connector is for DB connections, not metadata). Using google-api-python-client for all 3 gives uniform code, single package, consistent dict-style responses that align naturally with cloud_scan_json=json.dumps(). User prioritized end-user simplicity and consistent output with existing QUIRK patterns.

---

## GCS Data Hand-off to Phase 28

| Option | Description | Selected |
|--------|-------------|----------|
| New gcs_scan_json column | Per-scan JSON blob column; same pattern as kerberos/saml/dnssec_scan_json | ✓ |
| Protocol='GCS' CryptoEndpoint rows | One row per bucket; Phase 28 queries rows | |

**User's choice:** New gcs_scan_json column
**Notes:** Follows _IDENTITY_COLUMNS / _ensure_identity_columns() pattern from db.py exactly. Satisfies STOR-03 (zero duplicate storage.buckets.list calls). Clean seam between Phase 26 and Phase 28.

---

## KMS Key Version Enumeration

| Option | Description | Selected |
|--------|-------------|----------|
| Primary version only | One CryptoEndpoint per key; matches AWS KMS model | ✓ |
| All enabled versions | One row per key version (enabled state); surfaces algorithm diversity | |

**User's choice:** Primary version only
**Notes:** Consistent with AWS connector model. Destroyed/disabled versions skipped. Algorithm-downgrade visibility deferred — primary version is what matters for current posture assessment.

---

## KMS Location Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Enumerate all locations automatically | projects.locations.list; zero config beyond project_id | ✓ |
| User-configured location list | gcp_kms_locations: [...] in config | |

**User's choice:** Enumerate all locations automatically
**Notes:** Matches GCS bucket enumeration (no per-region config). User prioritized zero config friction.

---

## Claude's Discretion

- Quantum-safety classification: use existing classifier.py — no new logic
- CBOM integration: existing builder pass 1 handles GCP rows without changes
- Error handling style: per-resource try/except with logger.v()
- Connector function signatures: follow aws_connector.py style
- `service_detail` encoding for KMS protection level: `"CloudKMS/SOFTWARE"`, `"CloudKMS/HSM"`, `"CloudKMS/EXTERNAL"`

## Deferred Ideas

- GCP chaos lab profile — LocalStack has no GCP support; deferred
- Moving boto3/azure to [cloud] extras — breaking change; separate cleanup phase
- gcp_kms_locations user filter — auto-discovery preferred; add only if needed
