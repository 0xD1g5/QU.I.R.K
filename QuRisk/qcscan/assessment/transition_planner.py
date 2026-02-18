from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from qcscan.assessment.operator_context import get_context


@dataclass
class RoadmapItem:
    title: str
    rationale: str
    deliverable: str
    owner_hint: str
    effort: str
    timeline: str


@dataclass
class TransitionRoadmap:
    wave_1: List[RoadmapItem]
    wave_2: List[RoadmapItem]
    wave_3: List[RoadmapItem]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_transition_roadmap(cfg, endpoints, findings) -> TransitionRoadmap:
    ctx = get_context(cfg)
    data_types = [str(x).upper() for x in (ctx.get("data_types") or [])]
    longevity = int(ctx.get("data_longevity_years") or 7)
    exposure = (ctx.get("exposure") or "mixed").lower()

    sev = [f.get("severity") for f in findings]
    has_crit = "CRITICAL" in sev
    http_plain = [e for e in endpoints if getattr(e, "protocol", "") == "HTTP"]
    tls12 = [e for e in endpoints if getattr(e, "protocol", "") == "TLS" and getattr(e, "tls_version", "") == "TLSv1.2"]

    wave_1: List[RoadmapItem] = []
    wave_2: List[RoadmapItem] = []
    wave_3: List[RoadmapItem] = []

    # Wave 1 — Hygiene (0–6 months)
    if has_crit:
        wave_1.append(RoadmapItem(
            title="Remove deprecated TLS versions and weak configurations",
            rationale="Deprecated protocols increase immediate exploitability and slow future crypto upgrades.",
            deliverable="Baseline standard: TLS 1.2+ (prefer TLS 1.3); removal plan for TLS 1.0/1.1",
            owner_hint="Security Engineering + App/Infra Owners",
            effort="M",
            timeline="0–6 months",
        ))
    if http_plain:
        wave_1.append(RoadmapItem(
            title="Eliminate plaintext HTTP where feasible (especially management interfaces)",
            rationale="Plaintext endpoints undermine identity, session security, and governance.",
            deliverable="HTTP→HTTPS migration list; TLS termination pattern selection",
            owner_hint="Infra + Platform Teams",
            effort="M",
            timeline="0–6 months",
        ))

    # Context-driven hygiene emphasis
    if any(x in data_types for x in ["PCI", "PHI"]) or longevity >= 10 or exposure == "internet":
        wave_1.append(RoadmapItem(
            title="Prioritize long-lived sensitive data flows for immediate hardening",
            rationale="Harvest-now-decrypt-later risk increases with confidentiality duration and sensitivity.",
            deliverable="Crown-jewel data flow list; crypto termination points; quick wins backlog",
            owner_hint="Security Leadership + Data Owners + Architecture",
            effort="M",
            timeline="0–6 months",
        ))

    wave_1.append(RoadmapItem(
        title="Certificate lifecycle hygiene and ownership validation",
        rationale="Operational discipline reduces outages and enables future algorithm agility.",
        deliverable="Inventory with owners; renewal SLAs; automation backlog (managed PKI/ACME where possible)",
        owner_hint="PKI/Identity + Service Owners",
        effort="S",
        timeline="0–6 months",
    ))

    # Wave 2 — Modernization (6–24 months)
    if tls12:
        wave_2.append(RoadmapItem(
            title="Adopt TLS 1.3 at termination points and standardize modern configs",
            rationale="TLS 1.3 reduces downgrade/config risk and simplifies crypto baselines.",
            deliverable="TLS 1.3 enablement plan; standard cipher policy; rollout checklist",
            owner_hint="Network/LB + App Owners",
            effort="M",
            timeline="6–24 months",
        ))

    wave_2.append(RoadmapItem(
        title="Centralize crypto where possible (termination/offload patterns)",
        rationale="Centralization improves agility: fewer places to change algorithms, keys, and policies.",
        deliverable="Approved termination architectures (LB/WAF/Gateway patterns) + exceptions process",
        owner_hint="Architecture + Platform",
        effort="L",
        timeline="6–24 months",
    ))

    wave_2.append(RoadmapItem(
        title="Dependency and library baselining (crypto-agility workstream)",
        rationale="Most PQC blockers are dependencies (libraries, runtimes, embedded stacks).",
        deliverable="Crypto dependency SBOM-lite; upgrade candidates; deprecation schedule",
        owner_hint="AppSec + Engineering",
        effort="L",
        timeline="6–24 months",
    ))

    # Wave 3 — PQC Preparation (24+ months)
    wave_3.append(RoadmapItem(
        title="Vendor capability mapping + PQC/hybrid pilot selection",
        rationale="PQC readiness is vendor- and system-dependent; pilots de-risk timelines.",
        deliverable="Vendor matrix (TLS/SSH/PKI/Signing); pilot shortlist; success criteria",
        owner_hint="Security Leadership + Procurement + Architecture",
        effort="M",
        timeline="24+ months",
    ))

    # If high longevity/sensitivity, add a stronger PQC emphasis item
    if any(x in data_types for x in ["PCI", "PHI", "FINANCIAL", "TRADE", "TRADE SECRETS"]) and longevity >= 7:
        wave_3.append(RoadmapItem(
            title="PQC readiness plan for long-lived sensitive datasets",
            rationale="Long-lived sensitive data should be first in PQC planning and hybrid pilots.",
            deliverable="Data-longevity map + PQC prioritization list + pilot timeline",
            owner_hint="Security Program + Data Governance",
            effort="M",
            timeline="24+ months",
        ))

    wave_3.append(RoadmapItem(
        title="Hybrid key exchange and certificate strategy planning",
        rationale="Hybrid approaches are likely early path to PQC for many stacks.",
        deliverable="Hybrid design patterns; PKI impact assessment; migration playbook draft",
        owner_hint="PKI/Identity + Platform Security",
        effort="L",
        timeline="24+ months",
    ))

    wave_3.append(RoadmapItem(
        title="Program governance (metrics, waves, and change management)",
        rationale="PQC transition is a multi-year program; governance prevents stall-out.",
        deliverable="Roadmap cadence; readiness KPI tracking; wave execution plan",
        owner_hint="Security Program Mgmt",
        effort="M",
        timeline="24+ months",
    ))

    return TransitionRoadmap(wave_1=wave_1, wave_2=wave_2, wave_3=wave_3)
