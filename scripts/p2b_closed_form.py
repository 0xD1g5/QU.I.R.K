"""SCORE-08 (Phase 233), rewritten for scoring 4.0 (Phase 234): a
mechanism-independent closed-form model of the readiness score.

WHY THIS FILE EXISTS
--------------------
The P2b instrument (``scripts/p2b_instrument.py``) diffs this model against
``quirk.intelligence.scoring.compute_readiness_score`` at every sweep point
and on a set of one-field probes (``tests/test_p2b_instrument.py``). The
model implements the WRITTEN SPEC below.

For scoring 3.0 (Phase 233) that spec was derived by reading the scorer, so
agreement validated only the instrument's reading of the code, not the
code's intent (233 decision record section 13, limitation W2). For scoring
4.0 the spec was written SPEC-FIRST (Phase 234 CONTEXT D-06): it was written
from the Phase 234 CONTEXT decision prose (O-2, O-3, O-4, D-01, D-02, D-03,
D-04, D-11) and the research section "D-06 Closed-form plan (spec-first)",
and committed BEFORE ``quirk/intelligence/scoring.py`` changed. Agreement
therefore now tests the scorer against the intended 4.0 formula, and the W2
limitation is retired for 4.0.

Independence. If this file imported or called the audited code, agreement
would prove nothing at all (233 CONTEXT D-03). So this file must never import
anything from ``quirk``: it imports only allowlisted stdlib modules, every
constant is restated here, and
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
the NEW INTENDED formula. Do not copy or import the code (D-10): the value of
this file is that it is a second implementation, sharing no code with the
scorer, of a separately written statement of the formula. Phase 234 did
exactly this: the 4.0 spec below was written from the decisions before the
scorer was changed, so the closed-form nodes were red between the two
commits by design.

THE SPEC (scoring 4.0)
----------------------
Inputs: an evidence dict. ``profile`` must be None or ``"balanced"``; any
other profile raises ``UncoveredBranch`` (no weights override is modelled).

* E is ``assessable_endpoint_count``. If the key is missing the model raises
  ``UncoveredBranch``: the code would fall back to ``totals.endpoints``, a
  branch this model does not specify. Under 4.0, E is read ONLY as the
  assessed gate for hygiene, modern_tls and agility_signals. It is never a
  denominator.
* C is ``certificate_observations.certs_observed``. Under 4.0, C is read ONLY
  as the undetermined-key gate (the key-type rule below) and as part of the
  identity assessed gate. It is never a denominator.
* sev is ``scored_finding_severity_counts`` when present as a mapping, else
  ``finding_severity_counts``.
* legacy is ``legacy_tls_count`` when present, else ``sev["LOW"]`` (the
  documented fallback the dict ladder relies on).
* The e-mail plaintext numerator is ``motion_email_plaintext_count`` plus
  ``motion_email_starttls_missing_count``.
* Every count read is ``max(0, int(value or 0))``; a missing key reads 0.
* N_REF = 40 is a CONTINUITY ANCHOR, not a fitted value (O-3): it is the
  ladder skeleton population, so rungs R1-R4 keep their own-size values and
  only the dependence on estate size is removed. One constant serves both
  the endpoint and the certificate families (D-01).
* curve(n) is 0 when n <= 0, else ``min(1, n / N_REF) ** EXPONENT`` with
  EXPONENT = 0.5 (the 999.115 exponent and curve family, D-01). It depends
  on the weakness COUNT alone: there is no denominator. The constants are
  used, never a square-root call, so mutating either changes the output
  (233 RESEARCH Pitfall 4).

Each of the six DOMAINS starts at DOMAIN_CAP = 25.0 and adds signed terms:

* COUNT_TERMS: one row per (domain, count key path, weight, sign). Each row
  adds ``sign * curve(count) * weight`` to its domain. The mTLS row is the
  one positive row: an absolute count that saturates at N_REF (D-02). The 35
  rows (the 3.0 ratio sites, same paths, weights and signs) are, by domain:

  - hygiene: plaintext HTTP 18-, HTTP on a TLS port 16-.
  - modern_tls: legacy TLS 14-, ``protocol_counts.UNKNOWN`` 6-.
  - identity_trust: expired 14-, expiring 7-, self-signed 9-; mTLS present
    6+, weak Kerberos etype 10-, SAML weak signing 8-, DNSSEC weak algorithm
    8-, then seven S/MIME and AD CS rows at 2- each.
  - agility_signals: ``protocol_counts.UNKNOWN`` 6-, bearer-token weak alg
    6-, OpenAPI plaintext server 4-, code-signing weak algorithm 6-, fuzz
    finding 4-.
  - data_at_rest: DB plaintext 12-, DB weak SSL 6-, storage unencrypted 12-,
    storage AWS-managed key 4-, k8s unencrypted 10-, k8s inaccessible 4-,
    Vault weak 8-.
  - data_in_motion: e-mail plaintext (with STARTTLS missing) 12-, e-mail weak
    cipher 6-, broker plaintext 14-, broker weak TLS 8-, broker weak cipher
    6-.

* Scan error (D-03): the scan-error COUNT ``scan_error.count`` goes through
  the same curve: hygiene -= curve(count) x 6; modern_tls -= curve(count) x
  5. The scan-error rate is never read.
* Key type on agility_signals, from ``cert_key_type_counts`` (O-2, D-04).
  Classical certificate keys are quantum-vulnerable and are never a positive
  signal. EdDSA keys are counted under ECDSA by the evidence builder.
  In this if/elif order: RSA + ECDSA > 0 -> KEY_TYPE_CLASSICAL (-8, flat, not
  count-based); elif C > 0 and PQC == 0 (certificates observed with no key
  type reported) -> -8; else 0. There is no ECDSA bonus.
* PQC credit (O-4, D-04): ONE +8 credit on agility_signals when
  ``pqc_hybrid_endpoint_count`` > 0 OR ``cert_key_type_counts.PQC`` > 0.
  Never +16: a KEX observation and a certificate observation share it. The
  single-observation step is deliberate, sanctioned credit (O-2), not
  dilution.

subscore = int(round(clamp(raw, 0, 25))) with Python's round (half to even).

Assessed domains: hygiene, modern_tls and agility_signals iff E > 0;
identity_trust iff C > 0 or (effective KERBEROS + SAML + DNSSEC + SMIME +
ADCS) > 0 over ``protocol_counts``, where effective KERBEROS is
max(0, KERBEROS - ``kerberos_placeholder_count``): placeholder Kerberos rows
are not identity evidence (D-11); data_at_rest iff the sum over DAR_KEYS is
> 0; data_in_motion iff the sum over MOTION_KEYS is > 0. n is the number
assessed; n == 0 raises ``UncoveredBranch``. Unassessed subscores are
reported as None.

computed = int(round(sum of assessed subscores / (n x 25) x 100)).

Ceilings. Consequence ceiling, first match only: CRITICAL >= 5 -> 25
("deep-critical"); CRITICAL >= 1 -> 34 ("critical"); HIGH >= 3 -> 54
("high>=3"); HIGH >= 1 -> 69 ("high"). PQC-readiness ceiling: no PQC hybrid
endpoint -> 84 ("pqc"); the ceiling stays keyed on
``pqc_hybrid_endpoint_count`` ONLY (a PQC certificate key does not lift it).
The band tops 84/69/54/34 are the band thresholds 85/70/55/35 minus one,
restated here. The winner is the minimum by (value, source); the others are
returned as ``losing_ceilings`` so the record can argue a constant-ceiling
pass-through analytically (D-12).

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

# Continuity anchor (O-3): the ladder skeleton population, not a fit.
N_REF = 40

# Band thresholds 85 / 70 / 55 / 35, each minus one.
TOP_GOOD = 84
TOP_MODERATE = 69
TOP_FAIR = 54
TOP_POOR = 34

DEEP_CRITICAL_COUNT = 5
DEEP_CRITICAL_CEILING = 25
HIGH_MANY_COUNT = 3

# Classical certificate keys (RSA, ECDSA, EdDSA) are never positive (O-2).
KEY_TYPE_CLASSICAL = -8.0
KEY_TYPE_UNREPORTED_WITH_CERTS = -8.0
# The single PQC credit, KEX or certificate, never doubled (O-4, D-04).
PQC_HYBRID_BONUS = 8.0

KERBEROS_PLACEHOLDER_PATH = ("kerberos_placeholder_count",)
PQC_CERT_PATH = ("cert_key_type_counts", "PQC")

DOMAINS = (
    "hygiene",
    "modern_tls",
    "identity_trust",
    "agility_signals",
    "data_at_rest",
    "data_in_motion",
)

# (domain, count key path, weight, sign). No denominator column: under
# 4.0 every term is a curve of the weakness count alone (D-01, D-02).
COUNT_TERMS: List[Tuple[str, Tuple[str, ...], float, int]] = [
    ("hygiene", ("plaintext_http_count",), 18.0, -1),
    ("hygiene", ("http_on_tls_port_count",), 16.0, -1),
    ("modern_tls", ("legacy_tls_count",), 14.0, -1),
    ("modern_tls", ("protocol_counts", "UNKNOWN"), 6.0, -1),
    ("identity_trust", ("certificate_observations", "expired_count"),
     14.0, -1),
    ("identity_trust", ("certificate_observations", "expiring_count"),
     7.0, -1),
    ("identity_trust", ("certificate_observations", "self_signed_count"),
     9.0, -1),
    ("identity_trust", ("mtls_present_count",), 6.0, +1),
    ("identity_trust", ("identity_weak_etype_count",), 10.0, -1),
    ("identity_trust", ("saml_weak_signing_count",), 8.0, -1),
    ("identity_trust", ("dnssec_weak_algo_count",), 8.0, -1),
    ("identity_trust", ("smime_weak_signing_count",), 2.0, -1),
    ("identity_trust", ("smime_expired_count",), 2.0, -1),
    ("identity_trust", ("smime_weak_key_count",), 2.0, -1),
    ("identity_trust", ("adcs_weak_template_count",), 2.0, -1),
    ("identity_trust", ("adcs_misconfig_count",), 2.0, -1),
    ("identity_trust", ("adcs_weak_signing_count",), 2.0, -1),
    ("identity_trust", ("adcs_coverage_gap_count",), 2.0, -1),
    ("agility_signals", ("protocol_counts", "UNKNOWN"), 6.0, -1),
    ("agility_signals", ("bearer_token_weak_alg_count",), 6.0, -1),
    ("agility_signals", ("openapi_plaintext_server_count",), 4.0, -1),
    ("agility_signals", ("codesign_weak_algo_count",), 6.0, -1),
    ("agility_signals", ("fuzz_finding_count",), 4.0, -1),
    ("data_at_rest", ("dar_db_plaintext_count",), 12.0, -1),
    ("data_at_rest", ("dar_db_weak_ssl_count",), 6.0, -1),
    ("data_at_rest", ("dar_storage_unencrypted_count",), 12.0, -1),
    ("data_at_rest", ("dar_storage_aws_managed_count",), 4.0, -1),
    ("data_at_rest", ("dar_k8s_unencrypted_count",), 10.0, -1),
    ("data_at_rest", ("dar_k8s_inaccessible_count",), 4.0, -1),
    ("data_at_rest", ("dar_vault_weak_count",), 8.0, -1),
    ("data_in_motion", ("motion_email_plaintext_count",), 12.0, -1),
    ("data_in_motion", ("motion_email_weak_cipher_count",), 6.0, -1),
    ("data_in_motion", ("motion_broker_plaintext_count",), 14.0, -1),
    ("data_in_motion", ("motion_broker_weak_tls_count",), 8.0, -1),
    ("data_in_motion", ("motion_broker_weak_cipher_count",), 6.0, -1),
]

# Extra numerator paths summed into a COUNT_TERMS row's count.
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


def _curve(count: int) -> float:
    """0 when n <= 0, else min(1, n / N_REF) ** EXPONENT (no denominator)."""
    if count <= 0:
        return 0.0
    return min(1.0, count / N_REF) ** EXPONENT


def _scan_error_count(evidence: Mapping[str, Any]) -> int:
    """The scan-error COUNT (D-03); the rate is never read."""
    return _read(evidence, ("scan_error", "count"))


def _protocol_sum(evidence: Mapping[str, Any], keys: Sequence[str]) -> int:
    counts = evidence.get("protocol_counts")
    if not isinstance(counts, Mapping):
        return 0
    return sum(_count(counts.get(key, 0)) for key in keys)


# ---------------------------------------------------------------------------
# The model.
# ---------------------------------------------------------------------------

def _raw_domains(evidence: Mapping[str, Any],
                 c_count: int) -> Dict[str, float]:
    sev = _severity(evidence)
    raw = {domain: DOMAIN_CAP for domain in DOMAINS}
    for domain, path, weight, sign in COUNT_TERMS:
        count = _numerator(evidence, tuple(path), sev)
        raw[domain] += sign * _curve(count) * weight

    scan_error_curve = _curve(_scan_error_count(evidence))
    for domain, weight in SCAN_ERROR_WEIGHTS.items():
        raw[domain] -= scan_error_curve * weight

    rsa = _read(evidence, ("cert_key_type_counts", "RSA"))
    ecdsa = _read(evidence, ("cert_key_type_counts", "ECDSA"))
    pqc_cert = _read(evidence, PQC_CERT_PATH)
    if rsa + ecdsa > 0:
        raw["agility_signals"] += KEY_TYPE_CLASSICAL
    elif c_count > 0 and pqc_cert == 0:
        raw["agility_signals"] += KEY_TYPE_UNREPORTED_WITH_CERTS

    pqc_kex = _read(evidence, ("pqc_hybrid_endpoint_count",))
    if pqc_kex > 0 or pqc_cert > 0:
        raw["agility_signals"] += PQC_HYBRID_BONUS
    return raw


def _identity_protocol_sum(evidence: Mapping[str, Any]) -> int:
    """IDENTITY_KEYS sum with Kerberos placeholder rows removed (D-11)."""
    counts = evidence.get("protocol_counts")
    if not isinstance(counts, Mapping):
        counts = {}
    total = 0
    for key in IDENTITY_KEYS:
        value = _count(counts.get(key, 0))
        if key == "KERBEROS":
            value = max(0, value - _read(evidence, KERBEROS_PLACEHOLDER_PATH))
        total += value
    return total


def _assessed(evidence: Mapping[str, Any], e_count: int,
              c_count: int) -> Dict[str, bool]:
    return {
        "hygiene": e_count > 0,
        "modern_tls": e_count > 0,
        "identity_trust": c_count > 0 or _identity_protocol_sum(evidence) > 0,
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

    raw = _raw_domains(evidence, c_count)
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
