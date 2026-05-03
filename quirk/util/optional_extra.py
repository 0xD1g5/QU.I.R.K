"""Phase 45 / Plan 02: centralized optional-extra registry + probe.

Per Phase 45 / D-08, D-10, and Q1/Q3 user decisions:

- REGISTRY covers: identity, db, cloud, dashboard.
- ``motion`` is INTENTIONALLY OMITTED — the Phase 41 inline
  ``_emit_missing_extra_advisory`` calls at ``run_scan.py:782`` (email_scanner)
  and ``run_scan.py:827`` (broker_scanner) already cover those scanners. Adding
  motion here would double-emit (see ``45-RESEARCH.md`` §4 caveat).
- ``redis`` is OMITTED — covered transitively via motion; a standalone entry
  would also double-emit and would never fire (no ``enable_*`` flag is dedicated
  to it).
- D-11: existing per-scanner ``*_AVAILABLE`` flags
  (e.g. ``broker_scanner.SSLYZE_AVAILABLE``, ``vault_connector.HVAC_AVAILABLE``)
  are NOT migrated — they keep their existing patch points for the 9+ test
  files that depend on them.

Public surface:

- ``OptionalExtra`` — frozen dataclass describing one extra.
- ``REGISTRY`` — module-level tuple of ``OptionalExtra`` (4 entries).
- ``is_extra_available(extra)`` — bool; uses ``importlib.util.find_spec`` so
  partial installs cannot trigger ImportError (RESEARCH.md anti-pattern §1).
- ``probe_missing_extras(cfg, error_endpoints)`` — appends one
  ``CryptoEndpoint(protocol="ADVISORY", scan_error_category="missing_extra")``
  row per enabled-but-unavailable extra. Config-disabled scanners stay silent
  (D-08). One advisory per skipped scanner (D-05).
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Tuple


@dataclass(frozen=True)
class OptionalExtra:
    """Describes one optional-extra group.

    Attributes:
        extra: PyPI extras name (e.g. ``"identity"`` for ``pip install quirk[identity]``).
        modules: Tuple of importable module names that gate availability.
            ALL must be importable for the extra to count as "available".
        scanner_label: Human-readable scanner name; populates ``CryptoEndpoint.host``
            on the advisory row.
        install_hint: User-facing message; MUST contain the literal
            ``pip install quirk[<extra>]`` substring (INSTALL-04 / D-09).
        enabled_attrs: Tuple of ``cfg.connectors.enable_*`` attribute names.
            The probe emits an advisory only if at least one is True
            (D-08: config-disabled = silent). An empty tuple means "always probe"
            — used for the dashboard entry, which is not gated by a scan-time flag.
    """

    extra: str
    modules: Tuple[str, ...]
    scanner_label: str
    install_hint: str
    enabled_attrs: Tuple[str, ...]


REGISTRY: Tuple[OptionalExtra, ...] = (
    OptionalExtra(
        extra="identity",
        modules=("impacket",),
        scanner_label="kerberos_scanner",
        install_hint=(
            "Kerberos scanning skipped — run `pip install quirk[identity]` to enable"
        ),
        enabled_attrs=("enable_kerberos",),
    ),
    OptionalExtra(
        extra="db",
        modules=("psycopg2", "pymysql"),
        scanner_label="db_connector",
        install_hint=(
            "Database TLS scanning (PostgreSQL/MySQL) skipped — "
            "run `pip install quirk[db]` to enable"
        ),
        enabled_attrs=("enable_db",),
    ),
    OptionalExtra(
        extra="cloud",
        modules=("googleapiclient", "kubernetes", "hvac"),
        scanner_label="cloud_connectors",
        install_hint=(
            "GCP / Kubernetes / HashiCorp Vault scanning skipped — "
            "run `pip install quirk[cloud]` to enable"
        ),
        enabled_attrs=("enable_gcp", "enable_k8s", "enable_vault"),
    ),
    OptionalExtra(
        extra="dashboard",
        modules=("fastapi", "uvicorn", "playwright"),
        scanner_label="dashboard",
        install_hint=(
            "Web dashboard / PDF export unavailable — "
            "run `pip install quirk[dashboard]` to enable"
        ),
        # Empty tuple = always probe; the dashboard / PDF export is not gated by
        # a scan-time enable_* flag (separate `quirk serve` concern). See plan
        # 45-02 task 2 step 3 (option a).
        enabled_attrs=(),
    ),
)


def is_extra_available(extra: str) -> bool:
    """Return True iff every module in the extra's gate list is importable.

    Uses ``importlib.util.find_spec`` (does NOT actually import) so partial
    installs cannot trigger ImportError (T-45-07 / RESEARCH.md anti-pattern).
    """
    entry = next((e for e in REGISTRY if e.extra == extra), None)
    if entry is None:
        return False
    return all(find_spec(m) is not None for m in entry.modules)


def probe_missing_extras(cfg, error_endpoints) -> None:
    """Walk REGISTRY; append one ADVISORY ``CryptoEndpoint`` per gap.

    For each registry entry whose ``enabled_attrs`` includes at least one True
    flag on ``cfg.connectors`` (or whose ``enabled_attrs`` is empty), AND whose
    modules are NOT all importable, append exactly one advisory row to
    ``error_endpoints``.

    The advisory shape matches the Phase 41 ``_emit_missing_extra_advisory``
    contract verbatim so the existing ``trends.py`` exclusion
    (``scan_error_category == "missing_extra"``) keeps working unchanged.

    D-08: config-disabled scanners stay silent.
    D-05: one advisory per skipped scanner — never aggregated.
    INSTALL-01: never raises ImportError; uses ``find_spec`` only.
    """
    # Local import to avoid circulars (CryptoEndpoint pulls SQLAlchemy).
    from quirk.models import CryptoEndpoint

    connectors = getattr(cfg, "connectors", cfg)

    for entry in REGISTRY:
        # Gating check: skip silently if every gating flag is False.
        if entry.enabled_attrs:
            if not any(getattr(connectors, attr, False) for attr in entry.enabled_attrs):
                continue
        # Availability check: skip silently if every module is importable.
        if all(find_spec(m) is not None for m in entry.modules):
            continue
        # Enabled (or always-probe) AND missing → emit one advisory.
        error_endpoints.append(
            CryptoEndpoint(
                host=entry.scanner_label,
                port=0,
                protocol="ADVISORY",
                scan_error=entry.install_hint,
                scan_error_category="missing_extra",
            )
        )
