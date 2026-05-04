"""CBOM file writer — JSON and XML serialization.

D-13/D-14/D-15/D-16 (Phase 47 / Plan 03) enforce the post-write JSON schema
validation contract:
- D-13: depends on cyclonedx-python-lib[json-validation] (NOT [validation]).
- D-14: validation runs AFTER output_to_file; file is NOT deleted on failure.
- D-15: schema violation → one coverage_gap WARN finding; scan continues (soft-fail).
- D-16: missing jsonschema/referencing → MissingOptionalDependencyException caught
        silently; the optional-extra registry probe in run_scan.py emits the INFO
        advisory — writer does NOT double-emit.
"""
from __future__ import annotations

import os
from typing import Optional

from cyclonedx.model.bom import Bom
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.output.xml import XmlV1Dot6
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import (
    JsonStrictValidator,
    MissingOptionalDependencyException,
)


def write_cbom_files(
    bom: Bom,
    outdir: str,
    stamp: str,
    *,
    error_endpoints: Optional[list] = None,  # D-15: keyword-only; positional callers unchanged
) -> tuple[str, str]:
    """Serialize a CycloneDX Bom to JSON and XML files.

    After the JSON file is written, it is read back and validated against the
    CycloneDX 1.6 JSON schema (D-14). On validation failure, one
    coverage_gap WARN finding is appended to error_endpoints (D-15) and the
    file is preserved. If json-validation deps are absent, the validator raises
    MissingOptionalDependencyException; this is caught silently (D-16) — the
    optional-extra registry probe in run_scan.py emits the INFO advisory.

    Args:
        bom: The CycloneDX Bom object to serialize.
        outdir: Output directory path.
        stamp: Timestamp string for filename (e.g. "20260329-120000").
        error_endpoints: Mutable list to append advisory CryptoEndpoint rows.
            Keyword-only with default None; positional callers are unaffected.

    Returns:
        Tuple of (json_path, xml_path) — absolute paths to created files.
    """
    os.makedirs(outdir, exist_ok=True)

    json_path = os.path.join(outdir, f"cbom-{stamp}.cdx.json")
    xml_path = os.path.join(outdir, f"cbom-{stamp}.cdx.xml")

    # JSON output (CycloneDX 1.6)
    json_out = JsonV1Dot6(bom)
    json_out.output_to_file(filename=json_path, allow_overwrite=True, indent=2)

    # D-14: validate the JSON we just wrote; do NOT delete the file on failure.
    # Per RESEARCH F6: MissingOptionalDependencyException can fire at validator
    # construction OR at validate_str() time — wrap BOTH inside the same try.
    try:
        with open(json_path, "r", encoding="utf-8") as fh:
            json_text = fh.read()
        validator = JsonStrictValidator(SchemaVersion.V1_6)  # may raise MissingOptionalDependencyException
        err = validator.validate_str(json_text)               # may also raise it
        if err is not None and error_endpoints is not None:
            # D-15: soft-fail WARN finding; scan continues.
            from quirk.models import CryptoEndpoint  # local import to avoid SQLAlchemy circular
            error_endpoints.append(
                CryptoEndpoint(
                    host="cbom_validator",
                    port=0,
                    protocol="ADVISORY",
                    scan_error=f"CBOM JSON failed schema validation: {err}",
                    scan_error_category="coverage_gap",
                )
            )
    except MissingOptionalDependencyException:
        # D-16: deps missing — registry probe in run_scan.py emits the INFO advisory; skip silently here.
        pass
    except Exception as exc:  # D-15: any other validation error is a soft-fail WARN, not a crash
        if error_endpoints is not None:
            from quirk.models import CryptoEndpoint
            error_endpoints.append(
                CryptoEndpoint(
                    host="cbom_validator",
                    port=0,
                    protocol="ADVISORY",
                    scan_error=f"CBOM JSON validation error: {exc}",
                    scan_error_category="coverage_gap",
                )
            )

    # XML output (CycloneDX 1.6, uses stdlib xml.etree — no lxml needed)
    xml_out = XmlV1Dot6(bom)
    xml_out.output_to_file(filename=xml_path, allow_overwrite=True, indent=2)

    return json_path, xml_path
