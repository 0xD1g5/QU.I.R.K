from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class OperatorContext:
    data_types: List[str]              # e.g., ["PCI","PHI"]
    data_longevity_years: int          # e.g., 7
    exposure: str                      # "internal" | "mixed" | "internet"
    crown_jewels: List[str]            # list of hosts / fqdn / ip strings

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_choice(s: str) -> str:
    return (s or "").strip().upper()


def _prompt_list(prompt: str) -> List[str]:
    raw = input(prompt).strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def prompt_for_context() -> OperatorContext:
    print("\n🧠 Assessment Context (v3.5.1)")
    print("This helps generate a better Quantum Readiness Score + Transition Roadmap.\n")

    print("Select data types present (comma-separated). Examples: PCI, PHI, FINANCIAL, TRADE, PUBLIC")
    dt = _prompt_list("Data types: ")
    dt = [_normalize_choice(x) for x in dt]

    # Longevity
    try:
        years_raw = input("How many years must this data remain confidential? (default 7): ").strip()
        years = int(years_raw) if years_raw else 7
    except Exception:
        years = 7

    # Exposure
    print("\nExposure context:")
    print("  1) internal  (internal-only / segmented)")
    print("  2) mixed     (internal + some internet-facing)")
    print("  3) internet  (many internet-facing services)")
    exp_raw = input("Choose 1/2/3 (default 2): ").strip()
    exposure = "mixed"
    if exp_raw == "1":
        exposure = "internal"
    elif exp_raw == "3":
        exposure = "internet"

    # Crown jewels
    cj = _prompt_list("\nOptional: crown jewels hosts/IPs/FQDNs (comma-separated, blank to skip): ")
    cj = [x.strip() for x in cj if x.strip()]

    ctx = OperatorContext(
        data_types=dt or ["PUBLIC"],
        data_longevity_years=years,
        exposure=exposure,
        crown_jewels=cj,
    )
    print("\n✅ Context captured.\n")
    return ctx


def attach_context(cfg, ctx: OperatorContext) -> None:
    """
    Attach context to cfg in a way that is safe across dataclass/pydantic configs.
    Prefer cfg.assessment_context if possible; otherwise attach to cfg.assessment if it exists.
    """
    ctx_dict = ctx.to_dict()

    # Try top-level storage
    try:
        setattr(cfg, "assessment_context", ctx_dict)
        return
    except Exception:
        pass

    # Try nested (cfg.assessment.*)
    try:
        assessment = getattr(cfg, "assessment", None)
        if assessment is not None:
            setattr(assessment, "context", ctx_dict)
            return
    except Exception:
        pass

    # Last resort: no-op (still safe; score engine will default)
    return


def get_context(cfg) -> Dict[str, Any]:
    """
    Retrieve context dict if available; otherwise return defaults.
    """
    # 1) top-level
    ctx = getattr(cfg, "assessment_context", None)
    if isinstance(ctx, dict):
        return ctx

    # 2) nested
    assessment = getattr(cfg, "assessment", None)
    if assessment is not None:
        ctx2 = getattr(assessment, "context", None)
        if isinstance(ctx2, dict):
            return ctx2

    # defaults
    return {
        "data_types": ["PUBLIC"],
        "data_longevity_years": 7,
        "exposure": "mixed",
        "crown_jewels": [],
    }
