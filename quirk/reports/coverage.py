"""Phase 192 Plan 07 (OBS-02): scan-phase coverage payload for the report pipeline.

`load_scan_coverage()` is a single, failure-tolerant read of `ScanPhaseRecord` rows
(persisted by `run_scan.py`'s `_PhaseRecorder` / `_flush_scan_phase_records`, Plan
192-03) for one `scan_run_id`. It follows `writer.py::_load_closure_burndown`'s
scan_run_id-scoped, try/except-return-not-recorded shape: any DB error, missing
db_path, missing scan_run_id, or zero matching rows all collapse to the same
honest "not recorded" payload — never a raise, never a fabricated row.

D-15 requires this absence to be distinguishable from "a scan that legitimately
ran zero phases" — that is what the `recorded` boolean carries. Callers must not
infer absence from an empty `phases` list alone.
"""

from __future__ import annotations

from typing import Any, Dict


# D-15 (Phase 192 CONTEXT.md): the literal notice string. Do not reword, do not
# template the version — a future version bump does not change this scan's
# honest disclosure of what it lacked at the time it ran.
COVERAGE_NOT_RECORDED_NOTICE = "Coverage data not recorded for this scan (pre-v5.21)"


def _not_recorded_payload() -> Dict[str, Any]:
    return {"recorded": False, "ran": 0, "skipped": 0, "phases": []}


# Machine phase_name (as passed to run_scan.py's _wrapped_phase) -> human label.
# An unmapped name falls back to a title-cased derivation (see format_skip_note /
# load_scan_coverage below) rather than to a placeholder like "Unknown".
PHASE_LABELS: Dict[str, str] = {
    "ot_ics_supplemental": "OT/ICS",
    "tls_scanning": "TLS",
    "ssh_scanning": "SSH",
    "pqc_probe": "PQC Probe",
    "jwt_scanning": "JWT",
    "container_scanning": "Container",
    "source_scanning": "Source Code",
    "openapi_scanning": "OpenAPI",
    "fuzz_scanning": "Fuzzing",
    "aws_scanning": "AWS",
    "azure_scanning": "Azure",
    "gcp_scanning": "GCP",
    "db_scanning": "Database",
    "s3_scanning": "S3",
    "blob_scanning": "Azure Blob",
    "k8s_scanning": "Kubernetes",
    "dnssec_scanning": "DNSSEC",
    "saml_scanning": "SAML",
    "kerberos_scanning": "Kerberos",
    "smime_scanning": "S/MIME",
    "adcs_scanning": "ADCS",
    "codesign_scanning": "Code Signing",
    "vault_scanning": "Vault",
    "email_scanning": "Email",
    "broker_scanning": "Broker",
}


def _label_for(phase_name: str) -> str:
    label = PHASE_LABELS.get(phase_name)
    if label is not None:
        return label
    return phase_name.replace("_", " ").title()


def format_skip_note(entry: Dict[str, Any]) -> str:
    """`"Not assessed — skipped: {reason}"`, with `" ({detail})"` appended when
    `detail` is present. Used by Plan 08's D-14 per-domain-section notes.
    """
    reason = entry.get("reason")
    note = f"Not assessed — skipped: {reason}"
    detail = entry.get("detail")
    if detail:
        note += f" ({detail})"
    return note


def load_scan_coverage(db_path, scan_run_id) -> Dict[str, Any]:
    """One non-fatal read of `ScanPhaseRecord` rows for `scan_run_id`.

    Returns the not-recorded payload immediately when either argument is
    falsy, and on any read failure (broad except-return idiom, mirroring
    `_load_closure_burndown` / `_load_key_reuse`) — never a raise.
    """
    if not db_path or not scan_run_id:
        return _not_recorded_payload()

    try:
        from quirk.db import get_session as _get_session
        from quirk.models import ScanPhaseRecord

        with _get_session(db_path) as session:
            rows = (
                session.query(ScanPhaseRecord)
                .filter(ScanPhaseRecord.scan_run_id == scan_run_id)
                .order_by(ScanPhaseRecord.phase_name)
                .all()
            )
            if not rows:
                return _not_recorded_payload()

            ran = 0
            skipped = 0
            phases = []
            for row in rows:
                if row.status == "ran":
                    ran += 1
                elif row.status == "skipped":
                    skipped += 1
                phases.append(
                    {
                        "phase_name": row.phase_name,
                        "label": _label_for(row.phase_name),
                        "status": row.status,
                        "reason": row.reason,
                        "detail": row.detail,
                        "duration_sec": row.duration_sec,
                    }
                )

            return {
                "recorded": True,
                "ran": ran,
                "skipped": skipped,
                "phases": phases,
            }
    except Exception:
        import logging as _log

        _log.getLogger(__name__).warning(
            "scan coverage section skipped (non-fatal)", exc_info=True
        )
        return _not_recorded_payload()
