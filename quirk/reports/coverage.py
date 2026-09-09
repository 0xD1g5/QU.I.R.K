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


def get_phase_entry(coverage: Dict[str, Any] | None, phase_name: str) -> Dict[str, Any] | None:
    """Return the coverage `phases` entry for *phase_name*, or `None`.

    `None` is returned whenever `coverage` is falsy, `coverage["recorded"]` is
    False, or no entry matches — a single guard that every D-14 call site
    shares, so "coverage was never recorded" and "phase not found" both
    collapse to the same safe no-note outcome (T-192-30: an unrecorded scan
    must never license a per-domain skip claim).
    """
    if not coverage or not coverage.get("recorded"):
        return None
    for entry in coverage.get("phases") or []:
        if entry.get("phase_name") == phase_name:
            return entry
    return None


# D-14 (Phase 192 Plan 08 / OBS-02): scanner phase_name -> the report section
# title(s) that present that phase's results, derived by reading each renderer's
# actual `if <data>:`-gated section emits (not guessed):
#   - "tls_scanning" -> "TLS Capabilities" — the ONLY section in this codebase whose
#     HEADING itself is omitted (not merely its body/rows) when its backing data is
#     empty: quirk/reports/technical.py:166-181 (`if tls_eps: lines.append("## TLS
#     Capabilities")`). Plan 08 adds an identically-titled "TLS Capabilities" note to
#     html_renderer.py (render_tls_capabilities_skip_note, wired into
#     report.html.j2's technical-appendix, before "Endpoint Inventory") and to
#     docx_renderer.py (before the "Findings" heading) so the same disclosure lands
#     on all three surfaces per this phase's "CLI + HTML + DOCX" convention.
#
# Every other scanner phase funnels into an OMNIBUS section that already renders
# unconditionally with an honest empty-state message regardless of which phase(s)
# produced zero data — quirk/reports/technical.py:226 ("## Findings", no
# `if findings:` guard), quirk/reports/templates/report.html.j2:682-699
# ("Endpoint Inventory", `{% else %}No endpoints recorded for this scan.{% endif %}`)
# and :600 ("All Findings", same pattern), quirk/reports/docx_renderer.py:550-568
# ("Top Findings", `else: row_cells[0].text = "No findings recorded..."`) and :577-599
# ("Findings", same D-12 empty-state-row convention). A per-domain skip note bolted
# onto one of THOSE sections would misattribute a skip reason to a table that mixes
# every other phase's findings together, so they are deliberately left unmapped here.
# For every phase below, the Scan Coverage section (Plan 07/08) is the sole per-phase
# disclosure surface: ssh_scanning, pqc_probe, jwt_scanning, container_scanning,
# source_scanning, openapi_scanning, fuzz_scanning, aws_scanning, azure_scanning,
# gcp_scanning, db_scanning, s3_scanning, blob_scanning, k8s_scanning,
# dnssec_scanning, saml_scanning, kerberos_scanning, smime_scanning, adcs_scanning,
# codesign_scanning, vault_scanning, email_scanning, broker_scanning,
# ot_ics_supplemental.
PHASE_TO_REPORT_SECTION: Dict[str, tuple] = {
    "tls_scanning": ("TLS Capabilities",),
}


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
