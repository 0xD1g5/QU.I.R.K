"""quirk/qramm/evidence_bridge.py — Phase 53 (QRAMM-12, QRAMM-13).

Auto-populates CVI dimension `suggested_answer` values from the latest scan's
CryptoEndpoint rows. Called synchronously from `create_session` in the QRAMM router.

MUST NOT import `quirk.engine.risk_engine` or any scanner module (QRAMM-12 / Phase 51 D-09).
Use `quirk.cbom.classifier.classify_algorithm` only.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from quirk.assessment.migration_advisor import CANONICAL_ALG_SYNONYMS, _matches
from quirk.cbom.classifier import classify_algorithm
from quirk.models import CryptoEndpoint, QRAMMAnswer

logger = logging.getLogger(__name__)

_EVIDENCE_SOURCE_VERSION = "v1"

# Heuristic keys most likely to hold algorithm name strings inside scanner JSON blobs.
# Verified blob shapes (RESEARCH.md §"Algorithm String Extraction per Scanner Type"):
#   kerberos_scan_json: etype_details[].name
#   ssh_audit_json:     kex[].algorithm, hostkeys[].algorithm, enc[].algorithm, mac[].algorithm
#   jwt_scan_json:      keys[].alg
#   container_scan_json: metadata.algorithm
#   cloud_scan_json:    keyAlgorithm | algorithm
_ALG_KEYS = {"algorithm", "alg", "name", "keyAlgorithm", "key_algorithm"}


def _discovery_factor(endpoint_count: int) -> float:
    """D-02 (WR-04): scale Practice 1.1 by log10(endpoint_count)/3 in [0.25, 1.0].

    Curve: 1 endpoint → 0.25 (floor), 10 → ~0.333, 100 → ~0.667, 1000+ → 1.0.
    A scan that found nothing cannot claim Discovery maturity.
    """
    return min(1.0, max(0.25, math.log10(max(endpoint_count, 1)) / 3.0))


def populate_cvi_suggestions(
    session_id: int,
    db: Session,
    *,
    session_created_at: datetime | None = None,
) -> None:
    """Derive CVI suggested_answer values from the SESSION_BRACKET scan cohort.

    Updates the 30 CVI QRAMMAnswer rows (pre-created by `create_session`) with
    `suggested_answer` and `evidence_source`. Skips silently if no scan data exists
    (D-02). Does not touch `answer_value` or `confirmed_at`.

    SCOREFIX-05 (D-03): when session_created_at is provided, the cohort is scoped
    to endpoints where scanned_at <= session_created_at so that scans from later
    engagements cannot contaminate this session's evidence.  When None, the original
    global MAX(date) behavior is preserved (back-compat).
    """
    # SESSION_BRACKET (D-01): all rows where date(scanned_at) == MAX(date(scanned_at))
    cohort_q = db.query(func.date(func.max(CryptoEndpoint.scanned_at)))
    if session_created_at is not None:
        cohort_q = cohort_q.filter(CryptoEndpoint.scanned_at <= session_created_at)
    max_date_str = cohort_q.scalar()
    if max_date_str is None:
        logger.info("evidence_bridge: no scan data found, skipping")
        return

    # D-05 (WR-01): TZ-symmetric — both sides use SQLAlchemy func.date(), evaluated
    # by the same engine, so neither side carries an implicit local-TZ offset. Any
    # downstream Python-side use of max_date_str must parse via
    # datetime.date.fromisoformat(max_date_str) before equality compare.
    endpoints_q = db.query(CryptoEndpoint).filter(
        func.date(CryptoEndpoint.scanned_at) == max_date_str
    )
    if session_created_at is not None:
        endpoints_q = endpoints_q.filter(CryptoEndpoint.scanned_at <= session_created_at)
    endpoints = endpoints_q.all()
    if not endpoints:
        logger.info("evidence_bridge: no scan data found, skipping")
        return

    protocol_set: set[str] = set()
    algorithm_set: set[str] = set()
    total_endpoints = len(endpoints)
    vulnerable_endpoint_count = 0

    for ep in endpoints:
        if ep.protocol:
            protocol_set.add(ep.protocol.upper())
        names = _extract_algorithm_names(ep)
        ep_has_vulnerable = False
        for name in names:
            _, nist_level, _ = classify_algorithm(name)
            if nist_level is None:
                # Pitfall 1: unknown algorithms must NOT inflate the vulnerable count
                continue
            algorithm_set.add(name.lower())
            if nist_level == 0:
                ep_has_vulnerable = True
        if ep_has_vulnerable:
            vulnerable_endpoint_count += 1

    # D-06 — Practice 1.1 (Discovery & Inventory): endpoint count + protocol diversity
    distinct_protocols = len(protocol_set)
    if total_endpoints == 0:
        score_1_1 = 1
    elif distinct_protocols <= 1:
        score_1_1 = 2
    elif distinct_protocols <= 3:
        score_1_1 = 3
    else:
        score_1_1 = 4

    # D-02 (WR-04): scale by log10(endpoint_count)/3 in [0.25, 1.0].
    # A scan that found nothing cannot claim Discovery maturity.
    # QC-01: cast to int() so the Integer-typed suggested_answer column receives an
    # explicit truncation rather than a silent SQLite float→integer coercion.
    score_1_1 = int(score_1_1 * _discovery_factor(total_endpoints))

    # D-05 — Practice 1.2 (Vulnerability Assessment): % endpoints with nist_level == 0
    # D-03 (WR-05): when zero algorithms classified, vuln_pct is INDETERMINATE
    # (cannot compute "% vulnerable" without a denominator of known algos).
    # Sentinel propagates through score_1_2 → _maturity_label → "Indeterminate".
    total_algos = len(algorithm_set)
    if total_algos == 0 or total_endpoints == 0:
        vuln_pct: float | None = None
        score_1_2: int | None = None
    else:
        vuln_pct = (vulnerable_endpoint_count / total_endpoints) * 100.0
        if vuln_pct <= 25.0:
            score_1_2 = 4
        elif vuln_pct <= 50.0:
            score_1_2 = 3
        elif vuln_pct <= 75.0:
            score_1_2 = 2
        else:
            score_1_2 = 1

    # D-07 — Practice 1.3 (Dependency Mapping): distinct algorithm count
    distinct_algs = len(algorithm_set)
    if distinct_algs == 0:
        score_1_3 = 1
    elif distinct_algs <= 2:
        score_1_3 = 2
    elif distinct_algs <= 5:
        score_1_3 = 3
    else:
        score_1_3 = 4

    evidence_source = f"evidence_bridge:scan:{max_date_str}:{_EVIDENCE_SOURCE_VERSION}"
    practice_scores = {"1.1": score_1_1, "1.2": score_1_2, "1.3": score_1_3}

    for practice_area, suggested_value in practice_scores.items():
        # D-06 (WR-03): idempotent skip — pre-query existing rows; if every row
        # already matches the desired (suggested_answer, evidence_source) state,
        # skip the UPDATE entirely (no-op writes are silent corruption risk).
        existing = (
            db.query(QRAMMAnswer)
            .filter(
                QRAMMAnswer.session_id == session_id,
                QRAMMAnswer.dimension == "CVI",
                QRAMMAnswer.practice_area == practice_area,
            )
            .all()
        )
        if existing and all(
            r.suggested_answer == suggested_value and r.evidence_source == evidence_source
            for r in existing
        ):
            continue  # D-06: idempotent skip — desired state already persisted
        db.query(QRAMMAnswer).filter(
            QRAMMAnswer.session_id == session_id,
            QRAMMAnswer.dimension == "CVI",
            QRAMMAnswer.practice_area == practice_area,
        ).update(
            {
                QRAMMAnswer.suggested_answer: suggested_value,
                QRAMMAnswer.evidence_source: evidence_source,
            },
            synchronize_session="fetch",
        )

    # D-06 (WR-07): wrap commit so SQLAlchemyError is logged + rolled back, never silent.
    try:
        db.commit()
    except SQLAlchemyError as e:
        logger.warning("evidence_bridge UPDATE failed: %s", e)
        db.rollback()
        return


def _extract_algorithm_names(ep: CryptoEndpoint) -> list[str]:
    """Collect raw algorithm name strings from structured fields and JSON blobs of an endpoint."""
    names: list[str] = []

    # Structured fields (D-03)
    for val in (ep.tls_version, ep.cipher_suite, ep.cert_sig_alg, ep.cert_pubkey_alg):
        if val:
            names.append(val)

    # JSON blob fields (D-03) — parsed gracefully; malformed blobs skipped without error
    for blob in (
        getattr(ep, "ssh_audit_json", None),
        getattr(ep, "jwt_scan_json", None),
        getattr(ep, "container_scan_json", None),
        getattr(ep, "cloud_scan_json", None),
        getattr(ep, "kerberos_scan_json", None),
        getattr(ep, "saml_scan_json", None),
    ):
        parsed = _parse_json_blob(blob)
        if parsed is not None:
            names.extend(_walk_json_for_alg_strings(parsed))

    return names


def _parse_json_blob(blob: str | None) -> Any:
    """Parse JSON blob defensively. Returns None on empty input or malformed JSON."""
    if not blob:
        return None
    try:
        return json.loads(blob)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _walk_json_for_alg_strings(obj: Any) -> list[str]:
    """Recursively extract algorithm-name strings from a parsed JSON structure.

    Two code paths for dict entries:
      1. Key is in ``_ALG_KEYS`` AND value is a non-empty string → yield the
         value as an algorithm name string (e.g. ``{"algorithm": "rc4-hmac"}``).
      2. Value is a dict or list → recurse into it.  This fires when the key is
         NOT in ``_ALG_KEYS`` (container wrapper entries), OR when the key IS in
         ``_ALG_KEYS`` but its value is a container rather than a string (the
         ``if`` guard fails on ``isinstance(value, str)``, so the ``elif``
         handles it).

    Non-ALG-key string values are intentionally skipped (not appended, not
    recursed — they are not algorithm names).  List elements are recursed when
    they are dicts or lists; bare strings in a list are appended directly
    (e.g. ``{"encryption_types": ["rc4-hmac", ...]}``).

    Unknown strings are kept; ``classify_algorithm()`` filters them later via
    ``nist_level=None``.
    """
    out: list[str] = []
    if obj is None:
        return out
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _ALG_KEYS and isinstance(value, str) and value:
                out.append(value)
            elif isinstance(value, (dict, list)):
                # Recurse when key is NOT in _ALG_KEYS (or when it IS but value
                # is a container rather than a string).
                out.extend(_walk_json_for_alg_strings(value))
            elif isinstance(value, str) and value:
                # Phase 74-03 D-09 (WR-10): scan non-_ALG_KEYS string values
                # for canonical algorithm tokens via the migration_advisor
                # `_matches` helper. Captures algorithm names stored under
                # non-canonical keys (schema drift across scanner JSON shapes).
                if any(_matches(canon, value) for canon in CANONICAL_ALG_SYNONYMS):
                    out.append(value)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                out.extend(_walk_json_for_alg_strings(item))
            elif isinstance(item, str) and item:
                # Bare-string lists (e.g. {"encryption_types": ["rc4-hmac", ...]})
                out.append(item)
    return out
