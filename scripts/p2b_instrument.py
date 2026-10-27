"""SCORE-08 (Phase 233): the third P2b measurement instrument.

WHAT IT MEASURES
----------------
P2b asks whether the readiness score improves when an estate gains healthy
endpoints and nothing else changes. This instrument sweeps the five
calibration rungs (R1..R5) at +0/+20/+100/+500 healthy endpoints (D-04) and
records, at every point, the EMITTED score, the COMPUTED (pre-ceiling) score,
the WINNING ceiling and the LOSING ceilings (D-02).

THE METHOD
----------
* D-01, row layer. Each rung is rebuilt as synthetic endpoint rows plus
  finding dicts and assembled through ``build_evidence_summary`` with a fixed
  ``reference_utc``. At +0 the rows reproduce the dict ladder's score-relevant
  projection, emitted, computed and all six subscores. Fields scoring never
  reads (``totals.endpoints``, ``protocol_counts.TLS`` ...) may differ and are
  reported per field by ``projection_gaps``.
* D-05/D-18, healthy rows. The primary reading (``rows_ecdsa``) appends TLS
  1.3 rows that present a valid, unexpired ECDSA P-256 certificate with the
  scanner's own field values (alg ``ECDSA``, size 256, sig ``sha256``). The
  ``rows_rsa`` (RSA-2048) and ``rows_certless`` readings decompose that row
  into its certificate and non-certificate effects. No weakness rows are
  ever added; ``row_evidence`` refuses healthy rows that derive a CRITICAL or
  HIGH finding.
* D-06, continuity. ``mutator_212`` keeps Phase 212's three-field dict
  mutator as a labelled continuity reading, so this instrument can be checked
  against the R5 values 212 recorded (computed 71 at +0, 74 at +20).
* D-03, closed-form diff. Every point is also scored by
  ``scripts/p2b_closed_form.py``, which re-derives the score from a written
  spec without importing ``quirk``. A disagreement is recorded in
  ``KNOWN_DISAGREEMENTS`` with its cause; it is never tuned away.
* D-07, the dict ladder is imported from ``tests/test_score_properties.py``,
  never copied or edited.

WHY IT IS INDEPENDENT OF PHASE 212
----------------------------------
212's dict mutator and its scratch harness both edited evidence DICTS and read
only the computed score, so they could not see changes that live in
``build_evidence_summary`` (the 228-230 evidence work) and could not see which
ceiling masked a change. This instrument enters at the row layer, reads the
ceiling, and is cross-checked against a model that shares no code with the
audited scorer.

WHAT IT IS NOT
--------------
This is measurement tooling, not scoring code (D-09). It never changes how a
score is computed. It imports ``tests.test_score_properties``, which imports
``pytest``, so ``pytest`` is a runtime dependency of this script; install the
dev extra with ``pip install -e '.[dev]'``.

Phase 234 changes the scoring model; it must re-run this instrument across all
five rungs and all four readings, not only the R5 continuity pair (D-20).

REAL-ESTATE MODE (local only, D-08)
-----------------------------------
``--real-db PATH`` copies the database through the sqlite backup API from a
``mode=ro`` connection into a fresh temp dir, reads the 2026-09-14 run from
the copy, then deletes the temp dir. It never opens the source for writing,
never calls ``init_db`` and never serves an app. ``--real-json PATH`` reads a
recorded intelligence JSON's ``evidence_summary``. No committed test uses
either flag.

Usage::

    python -m scripts.p2b_instrument [--json | --markdown] [--points 0,20,100,500]
        [--real-db quirk-output/quirk.db] [--real-json quirk-output/intelligence-....json]
"""
from __future__ import annotations

import copy
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Sequence, Tuple

from quirk.engine.findings_evaluator import derive_report_findings
from quirk.intelligence.evidence import build_evidence_summary
from quirk.intelligence.scoring import compute_readiness_score
from scripts.p2b_closed_form import (
    DAR_KEYS,
    IDENTITY_KEYS,
    LEGACY_TLS_PATH,
    MOTION_KEYS,
    NUMERATOR_ADDENDS,
    RATIO_TERMS,
    closed_form,
)
from tests.test_score_properties import (
    _multihost_evidence,
    _r1_pristine_pqc_ready,
    _r2_well_run_no_pqc,
    _r3_typical_enterprise,
    _r4_neglected,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Pinned names and constants.
# ---------------------------------------------------------------------------

RUNGS = ("R1", "R2", "R3", "R4", "R5")
READINGS = ("rows_ecdsa", "rows_rsa", "rows_certless", "mutator_212")
PRIMARY_READING = "rows_ecdsa"
CONTINUITY_READING = "mutator_212"
POINTS = (0, 20, 100, 500)
HEALTHY_KINDS = ("ecdsa", "rsa", "certless")

REF = datetime(2026, 10, 1, 12, 0, 0)
FUTURE = REF + timedelta(days=400)
EXPIRED = REF - timedelta(days=30)
EXPIRING = REF + timedelta(days=10)

PQC_MARKER = "pqc-hybrid-detected"
KERBEROS_DETAIL = "etype:18:aes256-cts-hmac-sha1-96:SAFE"
AEAD_CIPHER = "TLS_AES_256_GCM_SHA384"

# Sweep cell or probe id -> the cause of a closed-form / code disagreement.
# Empty: 233-02 found 0 of 395 probes disagreeing, and the sweep agrees at
# every point. An entry is a finding, never a tolerance.
KNOWN_DISAGREEMENTS: Dict[str, str] = {}

_ROW_FIELDS = (
    "host", "port", "protocol", "scanned_at", "tls_version",
    "tls_supported_versions", "cipher_suite", "cert_subject", "cert_issuer",
    "cert_pubkey_alg", "cert_pubkey_size", "cert_sig_alg", "cert_not_before",
    "cert_not_after", "scan_error", "tls_blocker_reason", "service_detail",
    "severity",
)
_CERT_FIELDS = (
    "cert_subject", "cert_issuer", "cert_pubkey_alg", "cert_pubkey_size",
    "cert_sig_alg", "cert_not_before", "cert_not_after",
)

_DICT_BUILDERS = {
    "R1": _r1_pristine_pqc_ready,
    "R2": _r2_well_run_no_pqc,
    "R3": _r3_typical_enterprise,
    "R4": _r4_neglected,
    "R5": _multihost_evidence,
}


def _ratio_paths() -> List[Tuple[str, ...]]:
    paths: List[Tuple[str, ...]] = []
    for _domain, path, _denom, _weight, _sign in RATIO_TERMS:
        path = tuple(path)
        if path == tuple(LEGACY_TLS_PATH):
            continue  # projected through the derived "legacy_tls" entry
        if path not in paths:
            paths.append(path)
    for addends in NUMERATOR_ADDENDS.values():
        for path in addends:
            if tuple(path) not in paths:
                paths.append(tuple(path))
    return paths


_FIXED_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("assessable_endpoint_count",),
    ("plaintext_http_count",),
    ("http_on_tls_port_count",),
    ("mtls_present_count",),
    ("scan_error", "rate"),
    ("protocol_counts", "UNKNOWN"),
    ("certificate_observations", "certs_observed"),
    ("certificate_observations", "expired_count"),
    ("certificate_observations", "expiring_count"),
    ("certificate_observations", "self_signed_count"),
    ("cert_key_type_counts", "RSA"),
    ("cert_key_type_counts", "ECDSA"),
    ("pqc_hybrid_endpoint_count",),
)
_PROJECTED_PATHS: Tuple[Tuple[str, ...], ...] = tuple(
    list(_FIXED_PATHS) + [p for p in _ratio_paths() if p not in _FIXED_PATHS]
)
_DERIVED = (
    "legacy_tls", "CRITICAL", "HIGH",
    "identity_protocols_present", "dar_protocols_present",
    "motion_protocols_present",
)
SCORE_RELEVANT_PATHS: Tuple[str, ...] = tuple(
    [".".join(p) for p in _PROJECTED_PATHS] + list(_DERIVED)
)
GAP_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("protocol_counts", "TLS"),
    ("protocol_counts", "SSH"),
    ("protocol_counts", "HTTP"),
    ("totals", "endpoints"),
    ("totals", "findings"),
)


# ---------------------------------------------------------------------------
# Rows and findings.
# ---------------------------------------------------------------------------

def _row(**fields: Any) -> SimpleNamespace:
    base: Dict[str, Any] = {name: None for name in _ROW_FIELDS}
    base["scanned_at"] = REF
    base.update(fields)
    return SimpleNamespace(**base)


def _finding(severity: str, title: str, host: str, port: int) -> Dict[str, Any]:
    return {"severity": severity, "title": title, "host": host, "port": port}


def _top_up(counts: Tuple[int, int, int, int, int],
            preplaced: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add generic findings until the C/H/M/L/I counts are exact."""
    have = Counter(f["severity"] for f in preplaced)
    out = list(preplaced)
    for sev, want in zip(("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"), counts):
        need = want - have.get(sev, 0)
        if need < 0:
            raise ValueError(f"{sev}: {have[sev]} preplaced exceeds {want}")
        out += [_finding(sev, f"generic {sev}", f"g-{sev}-{i}", 1)
                for i in range(need)]
    return out


def _detail(*parts: str) -> str:
    return "|".join(p for p in parts if p)


def _ladder_rows(*, key_alg: str, expired: int, expiring: int,
                 self_signed: int, unknown: int, legacy: int, pqc: bool,
                 pg_plaintext: int) -> List[SimpleNamespace]:
    """40 assessable rows for an R1-R4 rung (``_base_estate`` shape)."""
    total = 40
    marker = PQC_MARKER if pqc else ""
    others = [
        ("SSH", 22, ""), ("SSH", 22, ""), ("SSH", 22, ""), ("SSH", 22, ""),
        ("POSTGRESQL", 5432, "ssl-off" if pg_plaintext >= 1 else "ssl-on"),
        ("POSTGRESQL", 5433, "ssl-off" if pg_plaintext >= 2 else "ssl-on"),
        ("S3", 443, "S3/sse-s3"),
        ("KUBERNETES", 6443, "EKS/encrypted"),
        ("VAULT", 8200, ""),
        ("KERBEROS", 88, KERBEROS_DETAIL),
        ("SAML", 443, ""),
        ("DNSSEC", 53, ""),
        ("SMTP-STARTTLS", 587, ""),
        ("KAFKA-TLS", 9093, ""),
    ]
    rows: List[SimpleNamespace] = []
    for j, (proto, port, detail) in enumerate(others):
        fields: Dict[str, Any] = dict(
            host=f"svc-{j}", port=port, protocol=proto,
            service_detail=_detail(detail, marker),
        )
        if proto in ("SMTP-STARTTLS", "KAFKA-TLS"):
            fields.update(tls_version="TLSv1.3", cipher_suite=AEAD_CIPHER)
        rows.append(_row(**fields))
    for j in range(unknown):
        rows.append(_row(host=f"unk-{j}", port=9000 + j, protocol="UNKNOWN",
                         service_detail=marker))
    for j in range(total - len(rows)):
        is_legacy = j < legacy
        rows.append(_row(
            host=f"tls-{j}", port=443, protocol="TLS",
            tls_version="TLSv1.1" if is_legacy else "TLSv1.3",
            tls_supported_versions=(
                "TLSv1.1,TLSv1.2" if is_legacy else "TLSv1.2,TLSv1.3"),
            service_detail=marker,
        ))
    if len(rows) != total:
        raise AssertionError(f"built {len(rows)} rows, expected {total}")
    for j, row in enumerate(rows):
        if j < expired:
            row.cert_not_after = EXPIRED
        elif j < expired + expiring:
            row.cert_not_after = EXPIRING
        else:
            row.cert_not_after = FUTURE
        row.cert_subject = f"CN=r{j}"
        row.cert_issuer = row.cert_subject if j >= total - self_signed else "CN=Corp CA"
        row.cert_pubkey_alg = key_alg
    return rows


# Per-rung parameters for the R1-R4 builder (see the plan's interfaces table).
_LADDER_PARAMS: Dict[str, Dict[str, Any]] = {
    "R1": dict(key_alg="ECDSA", expired=0, expiring=0, self_signed=0,
               unknown=0, legacy=0, pqc=True, pg_plaintext=0),
    "R2": dict(key_alg="RSA", expired=0, expiring=2, self_signed=0,
               unknown=0, legacy=0, pqc=False, pg_plaintext=0),
    "R3": dict(key_alg="RSA", expired=2, expiring=3, self_signed=6,
               unknown=0, legacy=1, pqc=False, pg_plaintext=0),
    "R4": dict(key_alg="RSA", expired=8, expiring=5, self_signed=12,
               unknown=2, legacy=6, pqc=False, pg_plaintext=1),
}
_LADDER_TOP_UP: Dict[str, Tuple[int, int, int, int, int]] = {
    "R1": (0, 0, 0, 0, 100),
    "R2": (0, 0, 5, 0, 100),
    "R3": (0, 3, 12, 1, 100),
    "R4": (2, 8, 20, 6, 100),
}


def _r5_rows() -> Tuple[List[SimpleNamespace], List[Dict[str, Any]]]:
    """38 assessable rows, 17 certificates with undetermined key type."""
    others = (
        [("HTTP", 80, "")] * 5 + [("SSH", 22, "")] * 3
        + [("UNKNOWN", 9000, "")] * 2
        + [("POSTGRESQL", 5432, "ssl-on"), ("S3", 443, "S3/sse-s3"),
           ("KUBERNETES", 6443, "EKS/encrypted"), ("VAULT", 8200, ""),
           ("KERBEROS", 88, KERBEROS_DETAIL), ("SAML", 443, ""),
           ("DNSSEC", 53, ""), ("SMTP-STARTTLS", 587, ""),
           ("KAFKA-TLS", 9093, "")]
    )
    rows: List[SimpleNamespace] = []
    for j, (proto, port, detail) in enumerate(others):
        fields: Dict[str, Any] = dict(host=f"svc-{j}", port=port,
                                      protocol=proto, service_detail=detail)
        if proto in ("SMTP-STARTTLS", "KAFKA-TLS"):
            fields.update(tls_version="TLSv1.3", cipher_suite=AEAD_CIPHER)
        rows.append(_row(**fields))
    tls_rows: List[SimpleNamespace] = []
    for j in range(38 - len(rows)):
        is_legacy = j < 16
        row = _row(
            host=f"tls-{j}", port=443, protocol="TLS",
            tls_version="TLSv1.1" if is_legacy else "TLSv1.3",
            tls_supported_versions=(
                "TLSv1.1,TLSv1.2" if is_legacy else "TLSv1.2,TLSv1.3"),
        )
        tls_rows.append(row)
    rows += tls_rows
    for j, row in enumerate(tls_rows[:17]):
        row.cert_not_after = EXPIRED if j < 5 else EXPIRING if j < 6 else FUTURE
        row.cert_subject = f"CN=r5-{j}"
        row.cert_issuer = row.cert_subject if j >= 14 else "CN=Corp CA"
        row.cert_pubkey_alg = None  # dict: RSA 0 / ECDSA 0, undetermined
    preplaced = [_finding("HIGH", "Plaintext HTTP service detected", f"p{i}", 80)
                 for i in range(6)]
    preplaced += [_finding("HIGH", "HTTP on TLS-designated port", f"q{i}", 443)
                  for i in range(3)]
    return rows, _top_up((5, 14, 33, 16, 330), preplaced)


def rung_rows(rung: str) -> Tuple[List[SimpleNamespace], List[Dict[str, Any]]]:
    """The weakness rows and finding dicts that rebuild ``rung``."""
    if rung == "R5":
        return _r5_rows()
    if rung not in _LADDER_PARAMS:
        raise KeyError(rung)
    rows = _ladder_rows(**_LADDER_PARAMS[rung])
    preplaced: List[Dict[str, Any]] = []
    if rung == "R1":
        preplaced = [_finding("INFO", "mTLS required", r.host, r.port)
                     for r in rows]
    elif rung == "R3":
        preplaced = [_finding("HIGH", "Plaintext HTTP service detected",
                              "admin", 80)]
    elif rung == "R4":
        preplaced = [_finding("HIGH", "Plaintext HTTP service detected",
                              f"p{i}", 80) for i in range(5)]
        preplaced += [_finding("HIGH", "HTTP on TLS-designated port",
                               f"q{i}", 443) for i in range(2)]
    return rows, _top_up(_LADDER_TOP_UP[rung], preplaced)


def healthy_row(i: int, kind: str = "ecdsa",
                ref: Optional[datetime] = None) -> SimpleNamespace:
    """The i-th healthy TLS 1.3 row (D-05 primary kind is ``ecdsa``)."""
    if kind not in HEALTHY_KINDS:
        raise ValueError(f"unknown healthy kind {kind!r}")
    ref = REF if ref is None else ref
    host = f"healthy-{i}.p2b.example"
    row = _row(
        host=host, port=443, protocol="TLS", scanned_at=ref,
        tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
        cipher_suite=AEAD_CIPHER,
        cert_subject=f"CN={host}", cert_issuer="CN=P2b Issuing CA",
        cert_not_before=ref - timedelta(days=30),
        cert_not_after=ref + timedelta(days=400),
        service_detail="",
    )
    if kind == "ecdsa":
        # tls_scanner._pubkey_info's own values: "EC" would skip the
        # evaluator's key finding, a DNSSEC-style RSA+SHA256 label would
        # count as RSA.
        row.cert_pubkey_alg, row.cert_pubkey_size, row.cert_sig_alg = (
            "ECDSA", 256, "sha256")
    elif kind == "rsa":
        row.cert_pubkey_alg, row.cert_pubkey_size, row.cert_sig_alg = (
            "RSA", 2048, "sha256")
    else:
        for name in _CERT_FIELDS:
            setattr(row, name, None)
    return row


def _healthy(n: int, kind: str,
             ref: Optional[datetime] = None
             ) -> Tuple[List[SimpleNamespace], List[Dict[str, Any]]]:
    rows = [healthy_row(i, kind, ref) for i in range(n)]
    findings = derive_report_findings(rows) if rows else []
    bad = sorted({
        str(f.get("title")) for f in findings
        if str(f.get("severity", "")).upper() in ("CRITICAL", "HIGH")
    })
    if bad:
        raise AssertionError(
            f"healthy {kind} rows derive CRITICAL/HIGH findings: {bad}")
    return rows, findings


# ---------------------------------------------------------------------------
# Evidence for each reading.
# ---------------------------------------------------------------------------

def dict_rung(rung: str) -> Dict[str, Any]:
    """A fresh copy of the dict ladder's rung (imported, never copied)."""
    return _DICT_BUILDERS[rung]()


def row_evidence(rung: str, extra: int, kind: str = "ecdsa") -> Dict[str, Any]:
    """The rung's rows plus ``extra`` healthy rows, through the row layer.

    Healthy-row findings come only from ``derive_report_findings`` over the
    healthy rows; running it over the weakness rows would double-count the
    synthetic finding dicts.
    """
    rows, findings = rung_rows(rung)
    h_rows, h_findings = _healthy(extra, kind)
    return build_evidence_summary(rows + h_rows, findings + h_findings,
                                  reference_utc=REF)


def mutator_212(evidence: Dict[str, Any], n: int) -> Dict[str, Any]:
    """Phase 212's three-field mutator, kept as a continuity reading (D-06)."""
    ev = copy.deepcopy(evidence)
    ev["assessable_endpoint_count"] = int(ev.get("assessable_endpoint_count", 0) or 0) + n
    ev.setdefault("totals", {})
    ev["totals"]["endpoints"] = int(ev["totals"].get("endpoints", 0) or 0) + n
    ev.setdefault("protocol_counts", {})
    ev["protocol_counts"]["TLS"] = int(ev["protocol_counts"].get("TLS", 0) or 0) + n
    return ev


def evidence_for(rung: str, reading: str, extra: int) -> Dict[str, Any]:
    if reading == "mutator_212":
        return mutator_212(dict_rung(rung), extra)
    if reading.startswith("rows_") and reading[5:] in HEALTHY_KINDS:
        return row_evidence(rung, extra, reading[5:])
    raise KeyError(reading)


# ---------------------------------------------------------------------------
# Reading the score.
# ---------------------------------------------------------------------------

_COMPUTED_RE = re.compile(r"computed (\d+)")


def read_score(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """emitted, computed and the winning ceiling's source, from the code."""
    result = compute_readiness_score(copy.deepcopy(evidence))
    if result.get("score") is None:
        raise AssertionError(
            f"zero domains assessed: {result.get('coverage_disclosure')}")
    reason = result.get("rating_cap_reason") or ""
    match = _COMPUTED_RE.search(reason)
    computed = int(match.group(1)) if match else int(result["score"])
    if reason.startswith("no post-quantum"):
        source = "pqc_readiness"
    elif match:
        source = "consequence"
    else:
        source = "none"
    return {
        "emitted": int(result["score"]),
        "computed": computed,
        "ceiling_source": source,
        "rating_cap_reason": reason or None,
        "subscores": dict(result["subscores"]),
    }


def _get(evidence: Dict[str, Any], path: Sequence[str]) -> Any:
    node: Any = evidence
    for key in path:
        if not isinstance(node, dict):
            return 0
        node = node.get(key, 0)
    return 0 if node is None else node


def _sev(evidence: Dict[str, Any]) -> Dict[str, Any]:
    scored = evidence.get("scored_finding_severity_counts")
    if isinstance(scored, dict):
        return scored
    return evidence.get("finding_severity_counts", {}) or {}


def _protocols_present(evidence: Dict[str, Any], keys: Sequence[str]) -> bool:
    counts = evidence.get("protocol_counts") or {}
    return sum(int(counts.get(k, 0) or 0) for k in keys) > 0


def projection(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """The score-relevant projection of an evidence dict."""
    out: Dict[str, Any] = {".".join(p): _get(evidence, p)
                           for p in _PROJECTED_PATHS}
    sev = _sev(evidence)
    legacy = evidence.get(LEGACY_TLS_PATH[0])
    out["legacy_tls"] = int(sev.get("LOW", 0) or 0) if legacy is None else legacy
    out["CRITICAL"] = int(sev.get("CRITICAL", 0) or 0)
    out["HIGH"] = int(sev.get("HIGH", 0) or 0)
    out["identity_protocols_present"] = _protocols_present(evidence, IDENTITY_KEYS)
    out["dar_protocols_present"] = _protocols_present(evidence, DAR_KEYS)
    out["motion_protocols_present"] = _protocols_present(evidence, MOTION_KEYS)
    return out


def projection_gaps(rung: str) -> List[Tuple[str, Any, Any]]:
    """(field, dict value, row value) for score-irrelevant fields that differ."""
    d_ev = dict_rung(rung)
    r_ev = row_evidence(rung, 0, "ecdsa")
    gaps: List[Tuple[str, Any, Any]] = []
    for path in GAP_PATHS:
        d_val, r_val = _get(d_ev, path), _get(r_ev, path)
        if d_val != r_val:
            gaps.append((".".join(path), d_val, r_val))
    return gaps


def _score_point(evidence: Dict[str, Any]) -> Dict[str, Any]:
    code = read_score(evidence)
    spec = closed_form(copy.deepcopy(evidence))
    if code["ceiling_source"] == "none":
        ceiling_value = None
    else:
        ceiling_value = spec["ceiling"]
    squeeze_ok = (
        code["emitted"] == code["computed"] if ceiling_value is None
        else code["emitted"] == int(round(ceiling_value * code["computed"] / 100))
    )
    agrees = (
        spec["emitted"] == code["emitted"]
        and spec["computed"] == code["computed"]
        and dict(spec["subscores"]) == code["subscores"]
        and spec["ceiling_source"] == code["ceiling_source"]
    )
    return {
        "emitted": code["emitted"],
        "computed": code["computed"],
        "ceiling_source": code["ceiling_source"],
        "ceiling_value": ceiling_value,
        "ceiling_identity_holds": squeeze_ok,
        "losing_ceilings": [list(c) for c in spec["losing_ceilings"]],
        "rating_cap_reason": code["rating_cap_reason"],
        "subscores": code["subscores"],
        "closed_form": spec,
        "agrees": agrees,
    }


def measure_point(rung: str, reading: str, extra: int) -> Dict[str, Any]:
    point: Dict[str, Any] = {"rung": rung, "reading": reading, "extra": extra}
    point.update(_score_point(evidence_for(rung, reading, extra)))
    return point


def run(points: Sequence[int] = POINTS,
        readings: Sequence[str] = READINGS,
        rungs: Sequence[str] = RUNGS) -> List[Dict[str, Any]]:
    """Every (rung, reading, extra) point, rung-major."""
    return [measure_point(rung, reading, int(extra))
            for rung in rungs for reading in readings for extra in points]
