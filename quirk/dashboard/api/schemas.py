"""Pydantic response models for the QU.I.R.K. dashboard API.

These models define the contract between FastAPI and the React frontend.
TypeScript types in src/dashboard/src/types/api.ts must mirror these exactly.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str  # "ok"


# ---- Score / Confidence ----

class SubScores(BaseModel):
    hygiene: int
    modern_tls: int
    identity_trust: int
    agility_signals: int


class ScoreData(BaseModel):
    score: int
    rating: str  # EXCELLENT / GOOD / MODERATE / FAIR / POOR
    subscores: SubScores
    drivers: List[Dict[str, Any]]


class ConfidenceData(BaseModel):
    confidence_score: int
    confidence_rating: str  # HIGH / MEDIUM / LOW / VERY_LOW / NO_DATA


# ---- Findings ----

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


class ScanSession(BaseModel):
    scan_id: str          # ISO timestamp string (matches ScanMeta.scan_id)
    scanned_at: datetime
    total_endpoints: int
