"""Phase 45 / Plan 02: centralized optional-extra registry + probe.
Phase 47 / Plan 02: extended with optional ``binary`` field for binary-availability probing.

Per Phase 45 / D-08, D-10, and Q1/Q3 user decisions:

- REGISTRY covers: identity, db, cloud, dashboard, nmap.
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

The optional ``binary`` field (added Phase 47 / D-08) extends the availability
check: when ``binary`` is set, the entry is only "available" if all ``modules``
are importable AND ``shutil.which(binary)`` is not None. This lets binary deps
like ``nmap`` participate in the same advisory-emit loop without a new helper.

Public surface:

- ``OptionalExtra`` — frozen dataclass describing one extra.
- ``REGISTRY`` — module-level tuple of ``OptionalExtra`` (5 entries).
- ``is_extra_available(extra)`` — bool; uses ``importlib.util.find_spec`` so
  partial installs cannot trigger ImportError (RESEARCH.md anti-pattern §1).
  When ``binary`` is set, also checks ``shutil.which``.
- ``probe_missing_extras(cfg, error_endpoints)`` — appends one
  ``CryptoEndpoint(protocol="ADVISORY", scan_error_category="missing_extra")``
  row per enabled-but-unavailable extra. Config-disabled scanners stay silent
  (D-08). One advisory per skipped scanner (D-05).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from importlib.util import find_spec
from typing import Optional, Tuple


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
            ``pip install quirk[<extra>]`` substring (INSTALL-04 / D-09) OR contain
            actionable install instructions (for binary-only extras like nmap).
        enabled_attrs: Tuple of ``cfg.connectors.enable_*`` attribute names.
            The probe emits an advisory only if at least one is True
            (D-08: config-disabled = silent). An empty tuple means "always probe"
            — used for the dashboard entry, which is not gated by a scan-time flag.
        binary: Optional system binary name (e.g. ``"nmap"``). When set, the entry
            is only "available" if all ``modules`` are importable AND
            ``shutil.which(binary)`` is not None. Default None (Phase 45 entries
            are unaffected — backward compatible). Phase 47 / D-08.
    """

    extra: str
    modules: Tuple[str, ...]
    scanner_label: str
    install_hint: str
    enabled_attrs: Tuple[str, ...]
    binary: Optional[str] = None


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
    OptionalExtra(
        extra="nmap",
        modules=(),
        binary="nmap",  # D-08: binary-availability probe via shutil.which
        scanner_label="nmap_discovery",
        install_hint=(
            "Nmap discovery unavailable — install nmap "
            "(https://nmap.org/) and ensure it is in PATH; "
            "falling back to consulting-tls port list"
        ),
        enabled_attrs=("enable_nmap",),
    ),
)


def is_extra_available(extra: str) -> bool:
    """Return True iff every module in the extra's gate list is importable,
    AND (if the entry has a ``binary`` set) the binary is resolvable via
    ``shutil.which``.

    Uses ``importlib.util.find_spec`` (does NOT actually import) so partial
    installs cannot trigger ImportError (T-45-07 / RESEARCH.md anti-pattern).
    Phase 47 / D-08: binary field extends the check.
    """
    entry = next((e for e in REGISTRY if e.extra == extra), None)
    if entry is None:
        return False
    if not all(find_spec(m) is not None for m in entry.modules):
        return False
    if entry.binary is not None and shutil.which(entry.binary) is None:
        return False
    return True


def select_nmap_port_list(cfg, nmap_available: bool) -> list:
    """Return the port list to use for nmap scanning (D-08).

    When nmap is available, returns ``cfg.scan.ports_tls`` (the operator-
    configured list). When nmap is NOT available, falls back to
    ``CONSULTING_TLS_PORTS`` from ``quirk.interactive`` — the curated 17-port
    consulting list. This is a pure helper so both ``run_scan.py`` and tests
    can import from the same canonical location.

    Args:
        cfg: AppConfig instance with a ``.scan.ports_tls`` attribute.
        nmap_available: True if the nmap binary was found via is_extra_available.

    Returns:
        List of port integers.
    """
    if not nmap_available:
        from quirk.interactive import CONSULTING_TLS_PORTS  # D-08: fallback
        return CONSULTING_TLS_PORTS
    return getattr(cfg.scan, "ports_tls", None) or []


def probe_missing_extras(cfg, error_endpoints) -> None:
    """Walk REGISTRY; append one ADVISORY ``CryptoEndpoint`` per gap.

    For each registry entry whose ``enabled_attrs`` includes at least one True
    flag on ``cfg.connectors`` (or whose ``enabled_attrs`` is empty), AND whose
    modules are NOT all importable (or whose ``binary`` is set and not found),
    append exactly one advisory row to ``error_endpoints``.

    The advisory shape matches the Phase 41 ``_emit_missing_extra_advisory``
    contract verbatim so the existing ``trends.py`` exclusion
    (``scan_error_category == "missing_extra"``) keeps working unchanged.

    D-08: config-disabled scanners stay silent.
    D-05: one advisory per skipped scanner — never aggregated.
    INSTALL-01: never raises ImportError; uses ``find_spec`` only.
    Phase 47 / D-08: binary check uses shutil.which (not a new helper).
    """
    # Local import to avoid circulars (CryptoEndpoint pulls SQLAlchemy).
    from quirk.models import CryptoEndpoint

    connectors = getattr(cfg, "connectors", cfg)

    for entry in REGISTRY:
        # Gating check: skip silently if every gating flag is False.
        if entry.enabled_attrs:
            if not any(getattr(connectors, attr, False) for attr in entry.enabled_attrs):
                continue
        # Availability check: skip if every module is importable AND binary (if set) is found.
        modules_ok = all(find_spec(m) is not None for m in entry.modules)
        binary_ok = (entry.binary is None) or (shutil.which(entry.binary) is not None)
        if modules_ok and binary_ok:
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
