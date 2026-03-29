"""CBOM file writer — JSON and XML serialization."""
from __future__ import annotations

import os

from cyclonedx.model.bom import Bom
from cyclonedx.output.json import JsonV1Dot6
from cyclonedx.output.xml import XmlV1Dot6


def write_cbom_files(bom: Bom, outdir: str, stamp: str) -> tuple[str, str]:
    """Serialize a CycloneDX Bom to JSON and XML files.

    Args:
        bom: The CycloneDX Bom object to serialize.
        outdir: Output directory path.
        stamp: Timestamp string for filename (e.g. "20260329-120000").

    Returns:
        Tuple of (json_path, xml_path) — absolute paths to created files.
    """
    os.makedirs(outdir, exist_ok=True)

    json_path = os.path.join(outdir, f"cbom-{stamp}.cdx.json")
    xml_path = os.path.join(outdir, f"cbom-{stamp}.cdx.xml")

    # JSON output (CycloneDX 1.6)
    json_out = JsonV1Dot6(bom)
    json_out.output_to_file(filename=json_path, allow_overwrite=True, indent=2)

    # XML output (CycloneDX 1.6, uses stdlib xml.etree — no lxml needed)
    xml_out = XmlV1Dot6(bom)
    xml_out.output_to_file(filename=xml_path, allow_overwrite=True, indent=2)

    return json_path, xml_path
