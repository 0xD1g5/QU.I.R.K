"""Phase 49 D-01: Compliance mapping for QUIRK findings (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3).

Maintenance cadence: see docs/operators-guide.md §"Compliance Map Maintenance".

Compliance refs are EAGERLY attached to every finding dict by
quirk.engine.risk_engine._build_finding (Phase 49 D-02). Renderers and JSON
exports consume the `compliance` field as already-attached data — DO NOT
import COMPLIANCE_MAP into renderer code.

Title normalization (Pitfall 1): COMPLIANCE_MAP keys are the LITERAL title
strings emitted by risk_engine, parens preserved. The 7 f-string titles
whose runtime form contains an interpolated value go through
TITLE_PREFIX_ALIASES: a literal source-text prefix maps to a canonical
COMPLIANCE_MAP (or UNMAPPED_TITLES) key. See _normalize_for_compliance in
quirk/engine/risk_engine.py.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, FrozenSet, List

# Phase 49 D-04 / COMPLY-08: configurable freshness threshold.
STALENESS_THRESHOLD_DAYS: int = 365

# Stable ISO date used as the initial last_verified for every Phase 49 entry.
# Bump per-entry on re-verification, not on cosmetic edits.
_PHASE_49_VERIFIED: str = "2026-05-05"

# Source URL anchors (lifted to module-level constants so refactors stay one-touch).
_PCI_4_0_1_URL = (
    "https://docs-prv.pcisecuritystandards.org/PCI%20DSS/Standard/PCI-DSS-v4_0_1.pdf"
)
_HIPAA_164_312_URL = (
    "https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/"
    "subpart-C/section-164.312"
)
_FIPS_140_3_URL = "https://csrc.nist.gov/pubs/fips/140-3/final"

# Phase 52 — SOC2 + ISO 27001:2022 framework constants (D-05, D-07)
_PHASE_52_VERIFIED: str = "2026-05-05"
_SOC2_CC_URL = "https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater/trust-services-criteria"
_ISO_27001_URL = "https://www.iso.org/standard/82875.html"


def _pci(control: str) -> Dict[str, Any]:
    return {
        "framework": "PCI-DSS 4.0.1",
        "control": control,
        "version": "4.0.1",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _PCI_4_0_1_URL,
    }


def _hipaa(control: str) -> Dict[str, Any]:
    return {
        "framework": "HIPAA 45 CFR",
        "control": control,
        "version": "2024-rev",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _HIPAA_164_312_URL,
    }


def _fips(control: str) -> Dict[str, Any]:
    return {
        "framework": "FIPS 140-3",
        "control": control,
        "version": "FIPS 140-3",
        "last_verified": _PHASE_49_VERIFIED,
        "source_url": _FIPS_140_3_URL,
    }


def _soc2(control: str) -> Dict[str, Any]:
    """SOC2 Trust Services Criteria 2017 revision builder (Phase 52 D-05)."""
    return {
        "framework": "SOC2 CC",
        "control": control,
        "version": "2017-rev",
        "last_verified": _PHASE_52_VERIFIED,
        "source_url": _SOC2_CC_URL,
    }


def _iso(control: str) -> Dict[str, Any]:
    """ISO 27001:2022 builder. Use 8.x clause numbering only (Phase 52 D-07)."""
    return {
        "framework": "ISO 27001:2022",
        "control": control,
        "version": "ISO 27001:2022",
        "last_verified": _PHASE_52_VERIFIED,
        "source_url": _ISO_27001_URL,
    }


# Phase 49 Pitfall 1: f-string titles whose runtime form contains an
# interpolated value. Each key is a LITERAL source-text PREFIX from
# risk_engine.py; the value is the canonical key in COMPLIANCE_MAP (or
# UNMAPPED_TITLES) the runtime title resolves to.
#
# _normalize_for_compliance applies LONGEST-PREFIX-FIRST matching, so
# "Severely outdated Python cryptography package (" wins over any shorter
# overlap. Order in this dict is informational only.
TITLE_PREFIX_ALIASES: Dict[str, str] = {
    # line 90 — interpolated label sits mid-string, no parens.
    "End-of-life ": "End-of-life in container image",
    # line 105 — interpolated (name@version) at end-paren.
    "Container image uses quantum-vulnerable crypto library (":
        "Container image uses quantum-vulnerable crypto library",
    # line 127
    "Severely outdated Python cryptography package (":
        "Severely outdated Python cryptography package in container image",
    # line 143
    "Outdated Python cryptography package (":
        "Outdated Python cryptography package in container image",
    # line 161
    "Outdated pyOpenSSL package (":
        "Outdated pyOpenSSL package in container image",
    # line 178
    "Outdated libgcrypt (":
        "Outdated libgcrypt in container image",
    # line 190 — interpolated (name@version) at end-paren; mapped to UNMAPPED.
    "Container image contains crypto library (":
        "Container image contains crypto library",
}


COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]] = {
    # ── PCI 4.2.1 + HIPAA §164.312(e)(1) family — plaintext / weak transit
    "Plaintext HTTP service detected": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    # NB: parens preserved verbatim — risk_engine.py:464 emits this exact string.
    "Legacy TLS versions allowed (TLS 1.0/1.1)": [
        _pci("4.2.1"),
        _pci("4.2.1.1"),
        _hipaa("§164.312(e)(1)"),
        _fips("Not-Approved (SP 800-131A R2)"),
        _soc2("CC6.6"), _soc2("CC6.7"), _iso("8.26"),
    ],
    "Legacy TLS cipher suites accepted": [
        _pci("4.2.1"),
        _hipaa("§164.312(e)(1)"),
        _fips("Not-Approved (SP 800-131A R2)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    # ── PCI 4.2.1.1 — cert/key inventory
    "TLS certificate expired": [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
    "TLS certificate expiring within 30 days": [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
    "TLS certificate is self-signed": [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
    "TLS certificate issued by untrusted CA": [_pci("4.2.1.1"), _soc2("CC6.6"), _iso("8.24")],
    # ── PCI 6.3.3 + HIPAA §164.312(a)(2)(iv) + FIPS — undersized keys
    "TLS certificate uses undersized RSA key": [
        _pci("6.3.3"),
        _hipaa("§164.312(a)(2)(iv)"),
        _fips("Not-Approved (SP 800-131A R2: RSA <2048)"),
        _soc2("CC6.6"), _iso("8.24"),
    ],
    "TLS certificate uses undersized ECDSA key": [
        _pci("6.3.3"),
        _hipaa("§164.312(a)(2)(iv)"),
        _fips("Not-Approved (SP 800-186: curve <256-bit)"),
        _soc2("CC6.6"), _iso("8.24"),
    ],
    # ── Quantum-vulnerable strong-but-deprecated keys
    "TLS certificate uses quantum-vulnerable RSA key": [
        _pci("6.3.3"),
        _fips("Approved with Deprecation 2030/2035 (NIST IR 8547)"),
        _soc2("CC6.6"), _iso("8.24"),
    ],
    "TLS certificate uses quantum-vulnerable ECDSA key": [
        _pci("6.3.3"),
        _fips("Approved with Deprecation 2030/2035 (NIST IR 8547)"),
        _soc2("CC6.6"), _iso("8.24"),
    ],
    # ── Email TLS family
    "STARTTLS downgrade risk on SMTP": [
        _pci("4.2.1"), _hipaa("§164.312(e)(2)(ii)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Weak cipher suite on email TLS endpoint": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Non-PFS cipher suite on email TLS endpoint": [_pci("4.2.1"), _soc2("CC6.7"), _iso("8.26")],
    # ── Broker plaintext / weak family
    "Plaintext Kafka listener detected": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Plaintext AMQP listener detected": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    # NB: parens preserved verbatim — risk_engine.py emits this exact string.
    "Plaintext Redis listener (no auth)": [
        _pci("4.2.1"),
        _pci("8.3.2"),
        _hipaa("§164.312(e)(1)"),
        _soc2("CC6.6"), _soc2("CC6.7"), _iso("8.26"),
    ],
    "Weak cipher suite on broker TLS endpoint": [
        _pci("4.2.1"), _hipaa("§164.312(e)(1)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    # ── Container findings — keys are CANONICAL FORMS (TITLE_PREFIX_ALIASES targets)
    "End-of-life in container image": [
        _pci("6.3.3"),
        _fips("Not-Approved (legacy crypto library default primitives)"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Container image uses quantum-vulnerable crypto library": [
        _fips("Approved with Deprecation 2030/2035 (NIST IR 8547)"),
        _soc2("CC6.6"), _iso("8.24"),
    ],
    "Severely outdated Python cryptography package in container image": [
        _pci("6.3.3"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Outdated Python cryptography package in container image": [
        _pci("6.3.3"),
        _soc2("CC6.7"), _iso("8.26"),
    ],
    "Outdated pyOpenSSL package in container image": [_pci("6.3.3"), _soc2("CC6.7"), _iso("8.26")],
    "Outdated libgcrypt in container image": [_pci("6.3.3"), _soc2("CC6.7"), _iso("8.26")],
}


# Phase 49 D-04: titles intentionally NOT mapped to compliance frameworks.
# Each entry MUST carry an inline `# ` comment justifying omission.
UNMAPPED_TITLES: FrozenSet[str] = frozenset({
    # Coverage-gap advisory — informational about scanner availability.
    "Scanner skipped — optional extra not installed",
    # Scan-execution failure surfacing — describes scanner state.
    "TLS handshake blocked assessment",
    # Informational; mTLS being required indicates already-secure config.
    "mTLS required",
    # Informational protocol observation — no direct control implication.
    "Informational protocol observation",
    # Forward-looking advisory; no current control violation.
    "SSH quantum planning advisory",
    # Discovery-time observation; control implication only after follow-up scanner.
    "Unknown open service",
    # Informational baseline — container has crypto library; no defect implied.
    # Canonical alias for risk_engine.py:190 f-string family.
    "Container image contains crypto library",
})


def check_compliance_staleness(
    today: datetime.date | None = None,
) -> List[Dict[str, Any]]:
    """QC-05: Production compliance staleness gate (365-day cadence).

    Iterates every entry in COMPLIANCE_MAP and checks whether its
    ``last_verified`` date is older than ``STALENESS_THRESHOLD_DAYS``.

    A MALFORMED or unparseable ``last_verified`` value is treated as a
    FAILURE (it appears in the returned stale list with ``malformed=True``)
    so that corrupt entries cannot silently escape the gate.

    Args:
        today: reference date (default: datetime.date.today()).  Injected
               in tests to avoid calendar drift.

    Returns:
        A list of dicts describing each stale or malformed entry::

            [{"title": str, "framework": str, "last_verified": str,
              "age_days": int,  # -1 when malformed
              "malformed": bool}]

        An empty list means all entries are fresh.

    Raises:
        RuntimeError: when any stale or malformed entry is found, so that
                      callers such as ``status_report`` can surface the
                      problem.  The exception message lists all violations.
    """
    reference = today or datetime.date.today()
    violations: List[Dict[str, Any]] = []
    for title, entries in COMPLIANCE_MAP.items():
        for entry in entries:
            raw = entry.get("last_verified", "")
            try:
                verified = datetime.date.fromisoformat(raw)
            except (TypeError, ValueError):
                violations.append(
                    {
                        "title": title,
                        "framework": entry.get("framework", ""),
                        "last_verified": raw,
                        "age_days": -1,
                        "malformed": True,
                    }
                )
                continue
            age = (reference - verified).days
            if age > STALENESS_THRESHOLD_DAYS:
                violations.append(
                    {
                        "title": title,
                        "framework": entry.get("framework", ""),
                        "last_verified": raw,
                        "age_days": age,
                        "malformed": False,
                    }
                )
    if violations:
        lines = []
        for v in violations:
            detail = "malformed date" if v["malformed"] else f"{v['age_days']} days old"
            lines.append(f"  {v['framework']} / {v['title']!r}: {detail}")
        raise RuntimeError(
            f"Compliance map has {len(violations)} stale or malformed "
            f"entr{'y' if len(violations) == 1 else 'ies'} "
            f"(threshold: {STALENESS_THRESHOLD_DAYS} days):\n"
            + "\n".join(lines)
        )
    return violations


def status_report(format: str = "text") -> None:
    """Print per-framework version + last_verified + source_url to stdout.

    Also runs the compliance staleness gate (QC-05) so stale or malformed
    entries are surfaced at `quirk compliance status` time.

    Used by `quirk compliance status` (D-05, COMPLY-09)."""
    # QC-05: surface staleness in the production CLI path.  Exceptions are
    # caught and printed as warnings rather than aborting the status display,
    # so operators still see the full table alongside the staleness alert.
    try:
        check_compliance_staleness()
    except RuntimeError as exc:
        print(f"WARNING: {exc}\n")

    seen: Dict[str, Dict[str, Any]] = {}
    for entries in COMPLIANCE_MAP.values():
        for e in entries:
            key = e["framework"]
            # Keep the OLDEST last_verified per framework (worst-case staleness signal).
            if (
                key not in seen
                or datetime.date.fromisoformat(e["last_verified"])
                < datetime.date.fromisoformat(seen[key]["last_verified"])
            ):
                seen[key] = {
                    "framework": e["framework"],
                    "version": e["version"],
                    "last_verified": e["last_verified"],
                    "source_url": e["source_url"],
                }
    if format == "json":
        import json as _json
        print(_json.dumps(seen, indent=2, sort_keys=True))
        return
    print(f"{'Framework':<20} {'Version':<14} {'Last Verified':<14} Source URL")
    print("-" * 100)
    for fw in sorted(seen):
        row = seen[fw]
        print(
            f"{row['framework']:<20} {row['version']:<14} "
            f"{row['last_verified']:<14} {row['source_url']}"
        )


__all__ = [
    "COMPLIANCE_MAP",
    "UNMAPPED_TITLES",
    "TITLE_PREFIX_ALIASES",
    "STALENESS_THRESHOLD_DAYS",
    "check_compliance_staleness",
    "status_report",
]
