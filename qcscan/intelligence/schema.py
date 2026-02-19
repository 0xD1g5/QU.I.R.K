from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Tuple

SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class ScoreInputs:
    total_endpoints: int
    tls_success: int
    ssh_success: int
    http_plain: int
    unknown_open: int
    high_impact: int

    def to_dict(self) -> Dict[str, int]:
        return {
            "total_endpoints": self.total_endpoints,
            "tls_success": self.tls_success,
            "ssh_success": self.ssh_success,
            "http_plain": self.http_plain,
            "unknown_open": self.unknown_open,
            "high_impact": self.high_impact,
        }


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: int
    rating: str
    drivers: Tuple[Tuple[str, int], ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "score": self.score,
            "rating": self.rating,
            "drivers": [{"label": label, "points": points} for label, points in self.drivers],
        }


@dataclass(frozen=True, slots=True)
class ConfidenceResult:
    confidence_score: int
    confidence_rating: str
    coverage_pct: float
    tls_enum_coverage_pct: float
    blockers_top: Tuple[Tuple[str, int], ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "confidence_score": self.confidence_score,
            "confidence_rating": self.confidence_rating,
            "coverage_pct": self.coverage_pct,
            "tls_enum_coverage_pct": self.tls_enum_coverage_pct,
            "blockers_top": [{"category": category, "count": count} for category, count in self.blockers_top],
        }


@dataclass(frozen=True, slots=True)
class RoadmapItem:
    wave: str
    title: str
    rationale: str
    deliverable: str
    owner_hint: str
    effort: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "wave": self.wave,
            "title": self.title,
            "rationale": self.rationale,
            "deliverable": self.deliverable,
            "owner_hint": self.owner_hint,
            "effort": self.effort,
        }


@dataclass(frozen=True, slots=True)
class IntelligenceReport:
    generated_utc: str
    score_inputs: ScoreInputs
    score_result: ScoreResult
    confidence_result: ConfidenceResult
    roadmap: Tuple[RoadmapItem, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generated_utc": self.generated_utc,
            "score_inputs": self.score_inputs.to_dict(),
            "score_result": self.score_result.to_dict(),
            "confidence_result": self.confidence_result.to_dict(),
            "roadmap": [item.to_dict() for item in self.roadmap],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
