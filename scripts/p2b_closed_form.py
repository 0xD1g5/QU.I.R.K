"""SCORE-08 (Phase 233): an independent closed-form model of the readiness score.

WHY THIS FILE EXISTS
--------------------
The P2b instrument (``scripts/p2b_instrument.py``) diffs this model against
``quirk.intelligence.scoring.compute_readiness_score`` at every sweep point
and on a set of one-field probes (``tests/test_p2b_instrument.py``). The
model is written from a WRITTEN SPEC (the prose below), not from the code it
audits. If it imported or copied that code, agreement would prove nothing
(CONTEXT D-03). So this file must never import anything from ``quirk``: it
imports only allowlisted stdlib modules, every constant is restated here, and
``tests/test_p2b_instrument.py::test_closed_form_is_independent`` checks that
with an AST import allowlist, a ban on dynamic-import and exec routes, a ban
on non-docstring strings naming the audited code, and a fresh subprocess that
proves no ``quirk`` module is loaded. Mentions of the audited code live in
docstrings only.

A disagreement between this model and the code is a FINDING. It is recorded
in ``scripts/p2b_instrument.py``'s ``KNOWN_DISAGREEMENTS`` table with its
cause and never tuned away. Only an input-mapping error (this model reading
the wrong evidence key) may be corrected here.

WHEN THE SCORER CHANGES (Phase 234 and later)
---------------------------------------------
When ``quirk/intelligence/scoring.py`` changes, the closed-form test nodes are
expected to go red. Update the written spec below, and the code under it, to
the NEW INTENDED formula. Do not copy the code (D-10): the value of this file
is that it is a second, independent statement of what the score should be.

THE SPEC
--------
Inputs: an evidence dict. ``profile`` must be None or ``"balanced"``; any
other profile raises ``UncoveredBranch`` (no weights override is modelled).

* E is ``assessable_endpoint_count``. If the key is missing the model raises
  ``UncoveredBranch``: the code would fall back to ``totals.endpoints``, a
  branch this model does not specify.
* C is ``certificate_observations.certs_observed``.
* sev is ``scored_finding_severity_counts`` when present as a mapping, else
  ``finding_severity_counts``.
* legacy is ``legacy_tls_count`` when present, else ``sev["LOW"]`` (the
  documented fallback the dict ladder relies on).
* The e-mail plaintext numerator is ``motion_email_plaintext_count`` plus
  ``motion_email_starttls_missing_count``.
* Every numerator read is ``max(0, int(value or 0))``; a missing key reads 0.
* curve(n, d) is 0 when d <= 0, else ``(n / d) ** EXPONENT`` with
  EXPONENT = 0.5. The constant is used, never a square-root call, so mutating
  the constant changes the output (RESEARCH Pitfall 4).
* rate is ``scan_error.rate`` clamped to [0, 1].

Each of the six DOMAINS starts at DOMAIN_CAP = 25.0 and adds signed terms:

* RATIO_TERMS: one row per (domain, numerator key path, denominator, weight,
  sign). The denominator is ``"E"`` or ``"C"``. Each row adds
  ``sign * curve(numerator, denominator) * weight`` to its domain. The 35
  rows are, by domain:

  - hygiene: plaintext HTTP 18-, HTTP on a TLS port 16- (both over E).
  - modern_tls: legacy TLS 14-, ``protocol_counts.UNKNOWN`` 6- (over E).
  - identity_trust: expired 14-, expiring 7-, self-signed 9- (all over C);
    mTLS present 6+, weak Kerberos etype 10-, SAML weak signing 8-, DNSSEC
    weak algorithm 8-, then seven S/MIME and AD CS rows at 2- each (over E).
  - agility_signals: ``protocol_counts.UNKNOWN`` 6-, bearer-token weak alg
    6-, OpenAPI plaintext server 4-, code-signing weak algorithm 6-, fuzz
    finding 4- (over E).
  - data_at_rest: DB plaintext 12-, DB weak SSL 6-, storage unencrypted 12-,
    storage AWS-managed key 4-, k8s unencrypted 10-, k8s inaccessible 4-,
    Vault weak 8- (over E).
  - data_in_motion: e-mail plaintext (with STARTTLS missing) 12-, e-mail weak
    cipher 6-, broker plaintext 14-, broker weak TLS 8-, broker weak cipher
    6- (over E).

* Scan error: hygiene -= rate x 6; modern_tls -= rate x 5.
* Key-type branch on agility_signals, from ``cert_key_type_counts``, in this
  if/elif order: RSA > 0 and ECDSA == 0 -> -8; elif ECDSA > 0 -> +4; elif
  C > 0 -> -8; else 0.
* PQC: ``pqc_hybrid_endpoint_count`` > 0 -> agility_signals +8.

subscore = int(round(clamp(raw, 0, 25))) with Python's round (half to even).

Assessed domains: hygiene, modern_tls and agility_signals iff E > 0;
identity_trust iff C > 0 or the sum of ``protocol_counts`` over IDENTITY_KEYS
is > 0; data_at_rest iff the sum over DAR_KEYS is > 0; data_in_motion iff the
sum over MOTION_KEYS is > 0. n is the number assessed; n == 0 raises
``UncoveredBranch``. Unassessed subscores are reported as None.

computed = int(round(sum of assessed subscores / (n x 25) x 100)).

Ceilings. Consequence ceiling, first match only: CRITICAL >= 5 -> 25
("deep-critical"); CRITICAL >= 1 -> 34 ("critical"); HIGH >= 3 -> 54
("high>=3"); HIGH >= 1 -> 69 ("high"). PQC-readiness ceiling: no PQC hybrid
endpoint -> 84 ("pqc"). The band tops 84/69/54/34 are the band thresholds
85/70/55/35 minus one, restated here. The winner is the minimum by
(value, source); the others are returned as ``losing_ceilings`` so the record
can argue a constant-ceiling pass-through analytically (D-12).

emitted = computed when no ceiling applies, else
int(round(winner x computed / 100)): a LINEAR SQUEEZE, not a cap.

Return keys: ``emitted``, ``computed``, ``ceiling``, ``ceiling_source``
("none" | "consequence" | "pqc_readiness"), ``ceiling_rule``,
``losing_ceilings`` (list of ``[value, source]``), ``subscores`` and
``domains_assessed``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


class UncoveredBranch(Exception):
    """The evidence takes a branch this written spec does not model."""


# ---------------------------------------------------------------------------
# Constants. Every one is read at call time, so a one-constant edit changes
# the output.
# ---------------------------------------------------------------------------

EXPONENT = 0.5
DOMAIN_CAP = 25.0

# Band thresholds 85 / 70 / 55 / 35, each minus one.
TOP_GOOD = 84
TOP_MODERATE = 69
TOP_FAIR = 54
TOP_POOR = 34

DEEP_CRITICAL_COUNT = 5
DEEP_CRITICAL_CEILING = 25
HIGH_MANY_COUNT = 3

KEY_TYPE_RSA_ONLY = -8.0
KEY_TYPE_ECDSA = 4.0
KEY_TYPE_UNREPORTED_WITH_CERTS = -8.0
PQC_HYBRID_BONUS = 8.0

DOMAINS = (
    "hygiene",
    "modern_tls",
    "identity_trust",
    "agility_signals",
    "data_at_rest",
    "data_in_motion",
)

# (domain, numerator key path, denominator, weight, sign).
# Denominator "E" = assessable endpoints, "C" = certificates observed.
RATIO_TERMS: List[Tuple[str, Tuple[str, ...], str, float, int]] = [
    ("hygiene", ("plaintext_http_count",), "E", 18.0, -1),
    ("hygiene", ("http_on_tls_port_count",), "E", 16.0, -1),
    ("modern_tls", ("legacy_tls_count",), "E", 14.0, -1),
    ("modern_tls", ("protocol_counts", "UNKNOWN"), "E", 6.0, -1),
    ("identity_trust", ("certificate_observations", "expired_count"),
     "C", 14.0, -1),
    ("identity_trust", ("certificate_observations", "expiring_count"),
     "C", 7.0, -1),
    ("identity_trust", ("certificate_observations", "self_signed_count"),
     "C", 9.0, -1),
    ("identity_trust", ("mtls_present_count",), "E", 6.0, +1),
    ("identity_trust", ("identity_weak_etype_count",), "E", 10.0, -1),
    ("identity_trust", ("saml_weak_signing_count",), "E", 8.0, -1),
    ("identity_trust", ("dnssec_weak_algo_count",), "E", 8.0, -1),
    ("identity_trust", ("smime_weak_signing_count",), "E", 2.0, -1),
    ("identity_trust", ("smime_expired_count",), "E", 2.0, -1),
    ("identity_trust", ("smime_weak_key_count",), "E", 2.0, -1),
    ("identity_trust", ("adcs_weak_template_count",), "E", 2.0, -1),
    ("identity_trust", ("adcs_misconfig_count",), "E", 2.0, -1),
    ("identity_trust", ("adcs_weak_signing_count",), "E", 2.0, -1),
    ("identity_trust", ("adcs_coverage_gap_count",), "E", 2.0, -1),
    ("agility_signals", ("protocol_counts", "UNKNOWN"), "E", 6.0, -1),
    ("agility_signals", ("bearer_token_weak_alg_count",), "E", 6.0, -1),
    ("agility_signals", ("openapi_plaintext_server_count",), "E", 4.0, -1),
    ("agility_signals", ("codesign_weak_algo_count",), "E", 6.0, -1),
    ("agility_signals", ("fuzz_finding_count",), "E", 4.0, -1),
    ("data_at_rest", ("dar_db_plaintext_count",), "E", 12.0, -1),
    ("data_at_rest", ("dar_db_weak_ssl_count",), "E", 6.0, -1),
    ("data_at_rest", ("dar_storage_unencrypted_count",), "E", 12.0, -1),
    ("data_at_rest", ("dar_storage_aws_managed_count",), "E", 4.0, -1),
    ("data_at_rest", ("dar_k8s_unencrypted_count",), "E", 10.0, -1),
    ("data_at_rest", ("dar_k8s_inaccessible_count",), "E", 4.0, -1),
    ("data_at_rest", ("dar_vault_weak_count",), "E", 8.0, -1),
    ("data_in_motion", ("motion_email_plaintext_count",), "E", 12.0, -1),
    ("data_in_motion", ("motion_email_weak_cipher_count",), "E", 6.0, -1),
    ("data_in_motion", ("motion_broker_plaintext_count",), "E", 14.0, -1),
    ("data_in_motion", ("motion_broker_weak_tls_count",), "E", 8.0, -1),
    ("data_in_motion", ("motion_broker_weak_cipher_count",), "E", 6.0, -1),
]

# Extra numerator paths summed into a RATIO_TERMS row's numerator.
NUMERATOR_ADDENDS: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]] = {
    ("motion_email_plaintext_count",): (
        ("motion_email_starttls_missing_count",),
    ),
}
LEGACY_TLS_PATH = ("legacy_tls_count",)

SCAN_ERROR_WEIGHTS: Dict[str, float] = {"hygiene": 6.0, "modern_tls": 5.0}

IDENTITY_KEYS = ("KERBEROS", "SAML", "DNSSEC", "SMIME", "ADCS")
DAR_KEYS = (
    "POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES", "VAULT",
)
MOTION_KEYS = (
    "SMTP-STARTTLS", "SMTPS", "IMAPS", "IMAP-STARTTLS", "POP3S",
    "POP3-STARTTLS", "KAFKA-PLAIN", "KAFKA-TLS", "AMQP-PLAIN", "AMQPS",
    "AMQPS/AZURE-SERVICEBUS", "HTTPS/AWS-SQS", "REDIS-PLAIN", "REDIS-TLS",
)

SUPPORTED_PROFILES = (None, "balanced")


# ---------------------------------------------------------------------------
# Readers.
# ---------------------------------------------------------------------------

def _count(value: Any) -> int:
    """max(0, int(value or 0))."""
    return max(0, int(value or 0))


def _read(evidence: Mapping[str, Any], path: Sequence[str]) -> int:
    """Read a count at a key path; a missing key (or non-mapping) reads 0."""
    node: Any = evidence
    for key in path:
        if not isinstance(node, Mapping):
            return 0
        node = node.get(key, 0)
    return _count(node)


def _severity(evidence: Mapping[str, Any]) -> Mapping[str, Any]:
    scored = evidence.get("scored_finding_severity_counts")
    if isinstance(scored, Mapping):
        return scored
    fallback = evidence.get("finding_severity_counts")
    return fallback if isinstance(fallback, Mapping) else {}


def _legacy(evidence: Mapping[str, Any], sev: Mapping[str, Any]) -> int:
    if evidence.get(LEGACY_TLS_PATH[0]) is not None:
        return _read(evidence, LEGACY_TLS_PATH)
    return _count(sev.get("LOW", 0))


def _numerator(evidence: Mapping[str, Any], path: Tuple[str, ...],
               sev: Mapping[str, Any]) -> int:
    if tuple(path) == LEGACY_TLS_PATH:
        total = _legacy(evidence, sev)
    else:
        total = _read(evidence, path)
    for extra in NUMERATOR_ADDENDS.get(tuple(path), ()):
        total += _read(evidence, extra)
    return total


def _curve(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return (numerator / denominator) ** EXPONENT


def _scan_error_rate(evidence: Mapping[str, Any]) -> float:
    block = evidence.get("scan_error")
    if not isinstance(block, Mapping):
        return 0.0
    rate = float(block.get("rate", 0.0) or 0.0)
    return min(1.0, max(0.0, rate))


def _protocol_sum(evidence: Mapping[str, Any], keys: Sequence[str]) -> int:
    counts = evidence.get("protocol_counts")
    if not isinstance(counts, Mapping):
        return 0
    return sum(_count(counts.get(key, 0)) for key in keys)


# ---------------------------------------------------------------------------
# The model.
# ---------------------------------------------------------------------------

def _raw_domains(evidence: Mapping[str, Any], e_count: int,
                 c_count: int) -> Dict[str, float]:
    sev = _severity(evidence)
    raw = {domain: DOMAIN_CAP for domain in DOMAINS}
    for domain, path, denom, weight, sign in RATIO_TERMS:
        if denom == "E":
            denominator = e_count
        elif denom == "C":
            denominator = c_count
        else:
            raise UncoveredBranch(f"unknown denominator {denom!r}")
        numerator = _numerator(evidence, tuple(path), sev)
        raw[domain] += sign * _curve(numerator, denominator) * weight

    rate = _scan_error_rate(evidence)
    for domain, weight in SCAN_ERROR_WEIGHTS.items():
        raw[domain] -= rate * weight

    rsa = _read(evidence, ("cert_key_type_counts", "RSA"))
    ecdsa = _read(evidence, ("cert_key_type_counts", "ECDSA"))
    if rsa > 0 and ecdsa == 0:
        raw["agility_signals"] += KEY_TYPE_RSA_ONLY
    elif ecdsa > 0:
        raw["agility_signals"] += KEY_TYPE_ECDSA
    elif c_count > 0:
        raw["agility_signals"] += KEY_TYPE_UNREPORTED_WITH_CERTS

    if _read(evidence, ("pqc_hybrid_endpoint_count",)) > 0:
        raw["agility_signals"] += PQC_HYBRID_BONUS
    return raw


def _assessed(evidence: Mapping[str, Any], e_count: int,
              c_count: int) -> Dict[str, bool]:
    return {
        "hygiene": e_count > 0,
        "modern_tls": e_count > 0,
        "identity_trust": (
            c_count > 0 or _protocol_sum(evidence, IDENTITY_KEYS) > 0
        ),
        "agility_signals": e_count > 0,
        "data_at_rest": _protocol_sum(evidence, DAR_KEYS) > 0,
        "data_in_motion": _protocol_sum(evidence, MOTION_KEYS) > 0,
    }


def _ceilings(evidence: Mapping[str, Any]) -> List[Tuple[int, str, str]]:
    """Every applicable ceiling as (value, source, rule)."""
    sev = _severity(evidence)
    critical = _count(sev.get("CRITICAL", 0))
    high = _count(sev.get("HIGH", 0))
    found: List[Tuple[int, str, str]] = []
    if critical >= DEEP_CRITICAL_COUNT:
        found.append((DEEP_CRITICAL_CEILING, "consequence", "deep-critical"))
    elif critical >= 1:
        found.append((TOP_POOR, "consequence", "critical"))
    elif high >= HIGH_MANY_COUNT:
        found.append((TOP_FAIR, "consequence", "high>=3"))
    elif high >= 1:
        found.append((TOP_MODERATE, "consequence", "high"))
    if _read(evidence, ("pqc_hybrid_endpoint_count",)) == 0:
        found.append((TOP_GOOD, "pqc_readiness", "pqc"))
    return found


def closed_form(evidence: Mapping[str, Any],
                profile: Optional[str] = None) -> Dict[str, Any]:
    """Score an evidence dict by the written spec in the module docstring."""
    if profile not in SUPPORTED_PROFILES:
        raise UncoveredBranch(
            f"profile {profile!r}: only the balanced profile is specified"
        )
    if "assessable_endpoint_count" not in evidence:
        raise UncoveredBranch(
            "no assessable_endpoint_count: the endpoint-total fallback is "
            "not specified"
        )
    e_count = _read(evidence, ("assessable_endpoint_count",))
    c_count = _read(evidence, ("certificate_observations", "certs_observed"))

    raw = _raw_domains(evidence, e_count, c_count)
    subscores = {
        domain: int(round(min(DOMAIN_CAP, max(0.0, raw[domain]))))
        for domain in DOMAINS
    }
    assessed = _assessed(evidence, e_count, c_count)
    n_assessed = sum(1 for domain in DOMAINS if assessed[domain])
    if n_assessed == 0:
        raise UncoveredBranch("zero domains assessed")

    total = sum(subscores[d] for d in DOMAINS if assessed[d])
    computed = int(round(total / (n_assessed * DOMAIN_CAP) * 100))

    ceilings = sorted(_ceilings(evidence), key=lambda c: (c[0], c[1]))
    if ceilings:
        win_value, win_source, win_rule = ceilings[0]
        losing = [[value, source] for value, source, _rule in ceilings[1:]]
        emitted = int(round(win_value * computed / 100))
        ceiling: Optional[int] = win_value
        source = win_source
        rule: Optional[str] = win_rule
    else:
        losing = []
        emitted = computed
        ceiling = None
        source = "none"
        rule = None

    return {
        "emitted": emitted,
        "computed": computed,
        "ceiling": ceiling,
        "ceiling_source": source,
        "ceiling_rule": rule,
        "losing_ceilings": losing,
        "subscores": {
            d: (subscores[d] if assessed[d] else None) for d in DOMAINS
        },
        "domains_assessed": n_assessed,
    }
