"""Phase 193 / Plan 01: connector availability parity helper (D-06).

Single source of truth mapping every one of the 25 ``ConnectorsCfg.enable_*``
flags to its real availability source, so both the ``GET
/api/connectors/availability`` route (plan 04) and the ``POST /api/jobs``
422 submit-time gate (plan 06) call the SAME function and can never disagree
(RESEARCH Pitfall 4).

Design, mirroring ``quirk/util/optional_extra.py``'s registry shape (Phase 45):

- ``AvailabilitySource`` — frozen dataclass describing how one flag's
  availability is determined: an ``optional_extra.REGISTRY`` key, a tuple of
  ``(dotted module path, FLAG_NAME)`` pairs read live via
  ``getattr(importlib.import_module(module), flag_name, False)``, an
  optional system ``binary`` name probed via ``shutil.which`` (mirrors
  ``OptionalExtra.binary``, Phase 47 / D-08 — added here as a Rule 2
  deviation: ``enable_container``/``enable_source`` gate on the ``syft``/
  ``semgrep`` external CLI binaries, which have no Python-importable flag
  and no ``optional_extra.REGISTRY`` entry of their own, so without this
  field they could not be honestly probed and would otherwise have to be
  mis-disposed as ``always_available`` — which the guard test explicitly
  forbids for anything but the two named behavior toggles), or a bare
  ``always_available=True`` disposition for the two pure behavior-toggle
  flags that have no optional import anywhere (Phase 93 AUTH-01,
  Phase 156 HWLC-12).
- ``CONNECTOR_AVAILABILITY_MAP`` — exactly 25 keys, one per
  ``ConnectorsCfg.enable_*`` field (verified by
  ``tests/test_connector_availability_mapping.py`` via
  ``dataclasses.fields(ConnectorsCfg)`` introspection at test-run time, per
  this repo's standing "a written list of known sites is not a safeguard"
  lesson — CLAUDE.md's GSD ``state.*`` clause).
- ``probe_connector`` / ``probe_all_connectors`` — D-07: probed FRESH on
  every call. No memoizing cache decorator, no module-scope memoization, no
  cached probe results anywhere in this module — every call re-runs
  ``find_spec``/``shutil.which``/``getattr``.

Disposition notes (grep-verified against ``run_scan.py`` and each scanner
module's own optional-import guard, 2026-09-09):

- ``enable_aws`` / ``enable_s3`` share ``aws_connector.BOTO3_AVAILABLE``
  (run_scan.py:3250, 3419) — many-to-one, recorded per entry below.
- ``enable_azure`` / ``enable_blob`` share
  ``azure_connector.AZURE_AVAILABLE`` (run_scan.py:3272, 3448).
- ``enable_gcp`` -> ``gcp_connector.GCP_AVAILABLE`` (run_scan.py:3297) alone
  — deliberately NOT ``optional_extra.REGISTRY``'s ``"cloud"`` extra, whose
  ``is_extra_available`` requires ALL of googleapiclient/kubernetes/hvac to
  be importable (AND semantics across three unrelated deps). Using
  ``extra="cloud"`` here would falsely report GCP unavailable whenever only
  the Kubernetes or Vault SDKs are missing — the same 1:1-name-mismatch
  pitfall RESEARCH Pitfall 7 warns about. ``enable_k8s`` and ``enable_vault``
  get the identical treatment below for the same reason.
- ``enable_k8s`` -> ``k8s_connector.K8S_AVAILABLE`` (run_scan.py:3477) ONLY.
  Per this plan's explicit ruling, ``GKE_AVAILABLE``/``AKS_AVAILABLE`` are
  provider-specific and are NOT part of the base availability boolean, so
  D-08's server reject has a definite yes/no; GKE/AKS absence is a reason-text
  nuance only, never surfaced here as a separate probe.
- ``enable_vault`` -> ``vault_connector.HVAC_AVAILABLE`` (run_scan.py:3711).
- ``enable_db`` -> BOTH ``extra="db"`` AND
  ``db_connector.PSYCOPG2_AVAILABLE``/``PYMYSQL_AVAILABLE`` in
  ``module_flags`` (run_scan.py:3320-3322), per this plan's explicit
  disposition. Note this is stricter (AND) than ``run_scan.py``'s own gate
  (``not (PSYCOPG2_AVAILABLE or PYMYSQL_AVAILABLE)`` — an OR), which is a
  known, deliberate divergence: the plan's generic probe formula ANDs every
  ``module_flags`` entry, and this plan's disposition intentionally lists
  both flags rather than special-casing an OR path into the shared formula.
- ``enable_nmap`` -> ``extra="nmap"`` only; ``REGISTRY``'s ``binary="nmap"``
  probe already covers the ``shutil.which`` check.
- ``enable_kerberos`` -> ``extra="identity"`` (``REGISTRY``'s ``impacket``
  gate matches ``kerberos_scanner.IMPACKET_AVAILABLE`` exactly).
- ``enable_smime`` / ``enable_adcs`` / ``enable_codesign`` each probe their
  OWN scanner module's ``LDAP3_AVAILABLE`` (``smime_scanner.py``,
  ``adcs_scanner.py``, ``codesign_scanner.py`` each carry an independent
  optional-import guard for ``ldap3`` — run_scan.py:472, :488, and
  ``codesign_scanner.py:24``) — NOT ``optional_extra.REGISTRY``'s
  ``"identity"`` extra, which gates on ``impacket`` only and has no ``ldap3``
  module listed.
- ``enable_saml`` / ``enable_dnssec`` / ``enable_jwt`` probe
  ``saml_scanner.LXML_AVAILABLE`` / ``dnssec_scanner.DNSPYTHON_AVAILABLE`` /
  ``jwt_scanner.HTTPX_AVAILABLE`` respectively. ``lxml``/``dnspython``/
  ``httpx`` are core (non-optional) dependencies in ``pyproject.toml``, but
  D-07 still requires a live probe rather than a hardcoded ``True`` — this
  catches a broken/partial install honestly instead of assuming success.
- ``enable_container`` / ``enable_source`` gate on the external ``syft`` /
  ``semgrep`` CLI binaries via the ``binary`` field (see Rule 2 deviation
  note above) — ``container_scanner.py`` / ``source_scanner.py`` have no
  Python-importable optional dependency at all.
- ``enable_email`` -> ``email_scanner.SSLYZE_AVAILABLE``.
- ``enable_broker`` -> ALL THREE of ``broker_scanner.SSLYZE_AVAILABLE`` /
  ``KAFKA_AVAILABLE`` / ``REDIS_AVAILABLE`` (run_scan.py:372-385).
- ``enable_snmp`` / ``enable_modbus`` / ``enable_bacnet`` -> their own
  scanner module's private ``_PYSNMP_AVAILABLE`` / ``_PYMODBUS_AVAILABLE`` /
  ``_PYBACNET_AVAILABLE`` flags (leading underscore is a module-privacy
  convention only; ``getattr`` reads it exactly the same as a public name).
  These map to the ``quirk-scanner[hw]`` extras group, which is
  intentionally NOT an ``optional_extra.REGISTRY`` entry (``hw`` is
  deliberately excluded from ``[all]`` — see ``pyproject.toml``), so
  ``extra=None`` here with the reason text naming ``quirk-scanner[hw]``
  directly.
- ``enable_authenticated_mode`` / ``enable_recurring_otics`` ->
  ``always_available=True`` — pure behavior toggles (Phase 93 AUTH-01,
  Phase 156 HWLC-12) with no optional import anywhere. These MUST be
  explicit entries, never omissions, and are the ONLY two flags permitted
  this disposition (locked by
  ``tests/test_connector_availability_mapping.py``).

T-193-01 (Tampering): ``importlib.import_module`` is only ever called with a
dotted path taken from this frozen map, never from request input;
``probe_connector`` raises ``KeyError`` for a ``flag`` not present in the
map rather than guessing.

T-193-03 (Information Disclosure): reason strings are built from the flag
name, the module/binary name, and (when an ``extra`` is set) the matching
``optional_extra.REGISTRY`` entry's ``install_hint`` verbatim — never from
``find_spec`` return values, exception tracebacks, or ``sys.path``.
"""
from __future__ import annotations

import importlib
import shutil
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Dict, Optional, Tuple

from quirk.util.optional_extra import REGISTRY, is_extra_available


@dataclass(frozen=True)
class AvailabilitySource:
    """Describes how one ``ConnectorsCfg.enable_*`` flag's availability is
    determined.

    Attributes:
        extra: Key into ``optional_extra.REGISTRY``, or ``None``.
        module_flags: Tuple of ``(dotted module path, FLAG_NAME)`` pairs.
            Every entry must resolve truthy (via live ``getattr``) for the
            connector to be considered available.
        always_available: Phase 193 Pitfall-6 disposition — True only for a
            pure behavior toggle with no optional import anywhere. Requires
            an inline justification comment at the map entry. Locked to
            exactly ``{enable_authenticated_mode, enable_recurring_otics}``
            by the guard test.
        category: One of the six 193-UI-SPEC category strings.
        label: Human-readable connector name for UI copy.
        binary: Optional system binary name probed via ``shutil.which``
            (Rule 2 deviation — mirrors ``OptionalExtra.binary``, Phase 47 /
            D-08 — for connectors gated on an external CLI tool with no
            Python-importable flag: ``enable_container`` / ``syft`` and
            ``enable_source`` / ``semgrep``).
    """

    extra: Optional[str]
    module_flags: Tuple[Tuple[str, str], ...]
    always_available: bool = False
    category: str = ""
    label: str = ""
    binary: Optional[str] = None


@dataclass(frozen=True)
class ConnectorAvailability:
    """One probed availability result for a single ``enable_*`` flag."""

    flag: str
    available: bool
    reason: str
    install_hint: str
    category: str
    label: str


def _registry_entry(extra: str):
    return next((e for e in REGISTRY if e.extra == extra), None)


def _module_flag_value(module: str, flag_name: str) -> Tuple[bool, Optional[str]]:
    """Read ``flag_name`` off ``module`` live, never caching, never raising.

    Returns ``(value, problem)`` where ``problem`` is ``None`` on success or
    a human-readable string naming what went wrong (missing module, missing
    attribute) when the probe could not be completed cleanly. D-07: every
    call re-imports and re-reads — no memoization.
    """
    try:
        mod = importlib.import_module(module)
    except ImportError as exc:
        return False, f"{module} is not importable ({exc.__class__.__name__})"
    value = getattr(mod, flag_name, False)
    if not value:
        return False, f"{module}.{flag_name} is False"
    return True, None


def probe_connector(flag: str) -> ConnectorAvailability:
    """Probe a single ``enable_*`` flag's live availability.

    Available iff (``extra`` is ``None`` or ``is_extra_available(extra)``)
    AND every ``(module, flag)`` in ``module_flags`` resolves truthy AND
    (``binary`` is ``None`` or ``shutil.which(binary)`` is not ``None``),
    unless ``always_available`` is ``True`` (then always available with an
    empty reason/hint).

    T-193-01: raises ``KeyError`` for a ``flag`` not present in
    ``CONNECTOR_AVAILABILITY_MAP`` rather than guessing — ``flag`` is never
    used to construct an import path itself, only as a lookup key into the
    frozen map.
    """
    source = CONNECTOR_AVAILABILITY_MAP[flag]

    if source.always_available:
        return ConnectorAvailability(
            flag=flag,
            available=True,
            reason="",
            install_hint="",
            category=source.category,
            label=source.label,
        )

    problems: list[str] = []

    extra_ok = True
    if source.extra is not None:
        extra_ok = is_extra_available(source.extra)
        if not extra_ok:
            problems.append(f"optional extra {source.extra!r} is not installed")

    for module, flag_name in source.module_flags:
        ok, problem = _module_flag_value(module, flag_name)
        if not ok:
            problems.append(problem or f"{module}.{flag_name} unavailable")

    binary_ok = True
    if source.binary is not None:
        binary_ok = shutil.which(source.binary) is not None
        if not binary_ok:
            problems.append(f"{source.binary!r} binary not found on PATH")

    available = not problems

    install_hint = ""
    if not available and source.extra is not None:
        entry = _registry_entry(source.extra)
        if entry is not None:
            install_hint = entry.install_hint

    reason = "; ".join(problems) if not available else ""

    return ConnectorAvailability(
        flag=flag,
        available=available,
        reason=reason,
        install_hint=install_hint,
        category=source.category,
        label=source.label,
    )


def probe_all_connectors() -> Dict[str, ConnectorAvailability]:
    """Probe every mapped connector flag fresh. D-07: no caching."""
    return {flag: probe_connector(flag) for flag in CONNECTOR_AVAILABILITY_MAP}


CONNECTOR_AVAILABILITY_MAP: Dict[str, AvailabilitySource] = {
    # -- Cloud -----------------------------------------------------------
    "enable_aws": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.aws_connector", "BOTO3_AVAILABLE"),),
        category="Cloud",
        label="AWS KMS",
    ),
    "enable_azure": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.azure_connector", "AZURE_AVAILABLE"),),
        category="Cloud",
        label="Azure Key Vault",
    ),
    "enable_gcp": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.gcp_connector", "GCP_AVAILABLE"),),
        category="Cloud",
        label="GCP Cloud KMS",
    ),
    "enable_s3": AvailabilitySource(
        # Many-to-one: shares aws_connector.BOTO3_AVAILABLE with enable_aws.
        extra=None,
        module_flags=(("quirk.scanner.aws_connector", "BOTO3_AVAILABLE"),),
        category="Cloud",
        label="S3 Object Storage",
    ),
    "enable_blob": AvailabilitySource(
        # Many-to-one: shares azure_connector.AZURE_AVAILABLE with enable_azure.
        extra=None,
        module_flags=(("quirk.scanner.azure_connector", "AZURE_AVAILABLE"),),
        category="Cloud",
        label="Azure Blob Storage",
    ),
    "enable_k8s": AvailabilitySource(
        # Base K8S_AVAILABLE only (GKE_AVAILABLE/AKS_AVAILABLE deliberately
        # excluded per this plan's ruling — see module docstring).
        extra=None,
        module_flags=(("quirk.scanner.k8s_connector", "K8S_AVAILABLE"),),
        category="Cloud",
        label="Kubernetes Secrets",
    ),
    "enable_vault": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.vault_connector", "HVAC_AVAILABLE"),),
        category="Cloud",
        label="HashiCorp Vault",
    ),
    # -- Database ----------------------------------------------------------
    "enable_db": AvailabilitySource(
        extra="db",
        module_flags=(
            ("quirk.scanner.db_connector", "PSYCOPG2_AVAILABLE"),
            ("quirk.scanner.db_connector", "PYMYSQL_AVAILABLE"),
        ),
        category="Database",
        label="Database TLS (PostgreSQL/MySQL)",
    ),
    # -- Identity ------------------------------------------------------------
    "enable_kerberos": AvailabilitySource(
        extra="identity",
        module_flags=(),
        category="Identity",
        label="Kerberos",
    ),
    "enable_saml": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.saml_scanner", "LXML_AVAILABLE"),),
        category="Identity",
        label="SAML / OIDC",
    ),
    "enable_dnssec": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.dnssec_scanner", "DNSPYTHON_AVAILABLE"),),
        category="Identity",
        label="DNSSEC",
    ),
    "enable_smime": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.smime_scanner", "LDAP3_AVAILABLE"),),
        category="Identity",
        label="S/MIME (LDAP)",
    ),
    "enable_adcs": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.adcs_scanner", "LDAP3_AVAILABLE"),),
        category="Identity",
        label="AD CS (LDAP)",
    ),
    "enable_codesign": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.codesign_scanner", "LDAP3_AVAILABLE"),),
        category="Identity",
        label="Code Signing Certificates",
    ),
    "enable_authenticated_mode": AvailabilitySource(
        # Pure behavior toggle (Phase 93 AUTH-01) — no optional import
        # anywhere; scheduler rejects recurring configs where this is True.
        extra=None,
        module_flags=(),
        always_available=True,
        category="Identity",
        label="Authenticated Scanning",
    ),
    # -- Email & Broker --------------------------------------------------
    "enable_email": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.email_scanner", "SSLYZE_AVAILABLE"),),
        category="Email & Broker",
        label="Email / SMTP",
    ),
    "enable_broker": AvailabilitySource(
        extra=None,
        module_flags=(
            ("quirk.scanner.broker_scanner", "SSLYZE_AVAILABLE"),
            ("quirk.scanner.broker_scanner", "KAFKA_AVAILABLE"),
            ("quirk.scanner.broker_scanner", "REDIS_AVAILABLE"),
        ),
        category="Email & Broker",
        label="Message Broker (Kafka/Redis)",
    ),
    # -- OT/ICS ------------------------------------------------------------
    "enable_snmp": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.snmp_scanner", "_PYSNMP_AVAILABLE"),),
        category="OT/ICS",
        label="SNMP Hardware Fingerprinting",
    ),
    "enable_modbus": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.modbus_scanner", "_PYMODBUS_AVAILABLE"),),
        category="OT/ICS",
        label="Modbus (OT/ICS)",
    ),
    "enable_bacnet": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.bacnet_scanner", "_PYBACNET_AVAILABLE"),),
        category="OT/ICS",
        label="BACnet (OT/ICS)",
    ),
    "enable_recurring_otics": AvailabilitySource(
        # Pure behavior/scheduling toggle (Phase 156 HWLC-12) — not a
        # scanner itself, no optional import anywhere.
        extra=None,
        module_flags=(),
        always_available=True,
        category="OT/ICS",
        label="Recurring OT/ICS Scheduling",
    ),
    # -- Source & API --------------------------------------------------------
    "enable_jwt": AvailabilitySource(
        extra=None,
        module_flags=(("quirk.scanner.jwt_scanner", "HTTPX_AVAILABLE"),),
        category="Source & API",
        label="JWT / API Endpoints",
    ),
    "enable_container": AvailabilitySource(
        # No Python-importable dep; gates on the external `syft` CLI binary.
        extra=None,
        module_flags=(),
        binary="syft",
        category="Source & API",
        label="Container Images (syft)",
    ),
    "enable_source": AvailabilitySource(
        # No Python-importable dep; gates on the external `semgrep` CLI binary.
        extra=None,
        module_flags=(),
        binary="semgrep",
        category="Source & API",
        label="Source Code (semgrep)",
    ),
    "enable_nmap": AvailabilitySource(
        extra="nmap",
        module_flags=(),
        category="Source & API",
        label="Nmap Discovery",
    ),
}
