"""QRAMM compliance framework weights — Phase 55 QRAMM-15.

Pure-data module. Defines static per-practice-per-framework weights, the
scanner-coverage ceiling, framework display names, and the practice-area to
dimension map used by the compliance-map endpoint.

Per Phase 51 D-09: zero engine or scanner imports allowed.
Per Phase 55 D-04: server-side single source of truth — no
duplicate weight data in the React app.
"""
from __future__ import annotations

from typing import Dict, Final, Literal, Tuple

# Phase 74-03 D-10 (WR-11): Coverage status semantics for SCANNER_COVERAGE.
# Distinguishes "covered" (contributes to rollup at full weight), "partial"
# (half weight), "pending" (in-scope but not yet implemented — EXCLUDED from
# rollup), and "n/a" (intentionally out-of-scope — EXCLUDED). Resolves the
# weight=0.0 ambiguity flagged in audit row qramm-compliance/WR-11.
CoverageStatus = Literal["covered", "partial", "pending", "n/a"]


FRAMEWORK_KEYS: Tuple[str, ...] = (
    "NIST_PQC", "NSM10", "CNSA2", "ISO27001",
    "ETSI_QS", "PCI_DSS", "CC", "BSI_TR",
)

FRAMEWORK_DISPLAY_NAMES: Dict[str, str] = {
    "NIST_PQC": "NIST PQC Standards",
    "NSM10":    "NSM-10",
    "CNSA2":    "CNSA 2.0",
    "ISO27001": "ISO 27001:2022",
    "ETSI_QS":  "ETSI Quantum-Safe",
    "PCI_DSS":  "PCI-DSS v4.0",
    "CC":       "Common Criteria",
    "BSI_TR":   "BSI TR-02102",
}

# Per Phase 55 D-07: only CVI is scanner-informed in v4.7. v4.8 evidence
# bridge expansion (QRAMM-F01) lifts SGRM/DPE/ITR ceilings; only this dict
# changes when that ships.
SCANNER_COVERAGE: Dict[str, float] = {
    "CVI": 1.0,
    "SGRM": 0.0,
    "DPE": 0.0,
    "ITR": 0.0,
}

# Phase 74-03 D-10 (WR-11): parallel status dict. Keys MUST match
# SCANNER_COVERAGE.keys() (CI gate: tests/test_compliance_coverage_status.py).
# CVI is scanner-informed in v4.8; SGRM/DPE/ITR remain 'pending' until the
# v5.x evidence-bridge expansion (QRAMM-F01) wires them in.
SCANNER_COVERAGE_STATUS: Final[Dict[str, CoverageStatus]] = {
    "CVI":  "covered",
    "SGRM": "pending",
    "DPE":  "pending",
    "ITR":  "pending",
}

PRACTICE_AREA_TO_DIMENSION: Dict[str, str] = {
    "1.1": "CVI", "1.2": "CVI", "1.3": "CVI",
    "2.1": "SGRM", "2.2": "SGRM", "2.3": "SGRM",
    "3.1": "DPE", "3.2": "DPE", "3.3": "DPE",
    "4.1": "ITR", "4.2": "ITR", "4.3": "ITR",
}

PRACTICE_AREA_NAMES: Dict[str, str] = {
    "1.1": "Cryptographic Discovery & Inventory Management",
    "1.2": "Vulnerability Assessment & Classification",
    "1.3": "Cryptographic Dependency Mapping",
    "2.1": "Executive Leadership",
    "2.2": "Risk & Compliance",
    "2.3": "Third-Party Management",
    "3.1": "Data Classification",
    "3.2": "Storage Security",
    "3.3": "Transit Security",
    "4.1": "Infrastructure",
    "4.2": "Implementation",
    "4.3": "Testing & Validation",
}

QRAMM_COMPLIANCE_WEIGHTS: Dict[str, Dict[str, float]] = {
    # ----- CVI: Cryptographic Visibility & Inventory -----
    # 1.1 Discovery & Inventory — strong quantum focus
    "1.1": {"NIST_PQC": 0.9, "NSM10": 0.8, "CNSA2": 0.9, "ISO27001": 0.7,
            "ETSI_QS": 0.8, "PCI_DSS": 0.5, "CC": 0.4, "BSI_TR": 0.7},
    # 1.2 Vulnerability Assessment — quantum risk classification
    "1.2": {"NIST_PQC": 0.9, "NSM10": 0.9, "CNSA2": 0.9, "ISO27001": 0.6,
            "ETSI_QS": 0.9, "PCI_DSS": 0.4, "CC": 0.5, "BSI_TR": 0.7},
    # 1.3 Dependency Mapping — supply-chain crypto
    "1.3": {"NIST_PQC": 0.7, "NSM10": 0.7, "CNSA2": 0.7, "ISO27001": 0.6,
            "ETSI_QS": 0.7, "PCI_DSS": 0.5, "CC": 0.5, "BSI_TR": 0.6},

    # ----- SGRM: Strategy, Governance, Risk Management -----
    # 2.1 Executive Leadership — governance frameworks dominate
    "2.1": {"NIST_PQC": 0.4, "NSM10": 0.5, "CNSA2": 0.5, "ISO27001": 0.9,
            "ETSI_QS": 0.4, "PCI_DSS": 0.6, "CC": 0.6, "BSI_TR": 0.7},
    # 2.2 Risk & Compliance — strong governance
    "2.2": {"NIST_PQC": 0.4, "NSM10": 0.5, "CNSA2": 0.5, "ISO27001": 0.9,
            "ETSI_QS": 0.4, "PCI_DSS": 0.8, "CC": 0.7, "BSI_TR": 0.8},
    # 2.3 Third-Party Management — supply chain governance
    "2.3": {"NIST_PQC": 0.4, "NSM10": 0.5, "CNSA2": 0.5, "ISO27001": 0.8,
            "ETSI_QS": 0.4, "PCI_DSS": 0.7, "CC": 0.6, "BSI_TR": 0.7},

    # ----- DPE: Data Protection Engineering -----
    # 3.1 Data Classification
    "3.1": {"NIST_PQC": 0.5, "NSM10": 0.6, "CNSA2": 0.6, "ISO27001": 0.8,
            "ETSI_QS": 0.5, "PCI_DSS": 0.8, "CC": 0.6, "BSI_TR": 0.7},
    # 3.2 Storage Security — data-at-rest crypto
    "3.2": {"NIST_PQC": 0.7, "NSM10": 0.7, "CNSA2": 0.7, "ISO27001": 0.7,
            "ETSI_QS": 0.7, "PCI_DSS": 0.9, "CC": 0.7, "BSI_TR": 0.8},
    # 3.3 Transit Security — TLS / data-in-flight
    "3.3": {"NIST_PQC": 0.8, "NSM10": 0.8, "CNSA2": 0.8, "ISO27001": 0.7,
            "ETSI_QS": 0.8, "PCI_DSS": 0.9, "CC": 0.7, "BSI_TR": 0.8},

    # ----- ITR: Implementation, Testing, Resilience -----
    # 4.1 Infrastructure — operational crypto deployment
    "4.1": {"NIST_PQC": 0.7, "NSM10": 0.7, "CNSA2": 0.8, "ISO27001": 0.7,
            "ETSI_QS": 0.7, "PCI_DSS": 0.6, "CC": 0.6, "BSI_TR": 0.8},
    # 4.2 Implementation — algorithm deployment
    "4.2": {"NIST_PQC": 0.9, "NSM10": 0.8, "CNSA2": 0.9, "ISO27001": 0.6,
            "ETSI_QS": 0.9, "PCI_DSS": 0.6, "CC": 0.7, "BSI_TR": 0.8},
    # 4.3 Testing & Validation — Common Criteria & BSI evaluation focus
    "4.3": {"NIST_PQC": 0.7, "NSM10": 0.7, "CNSA2": 0.7, "ISO27001": 0.6,
            "ETSI_QS": 0.7, "PCI_DSS": 0.7, "CC": 0.9, "BSI_TR": 0.9},
}
