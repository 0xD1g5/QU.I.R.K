"""Phase 180 Plan 06 (CLOSE-03): per-deadline burndown aggregation.

Burndown is computed RELATIVE TO A NAMED TARGET DATE — this module returns NO
SCALAR anywhere: one number cannot say "this endpoint's RSA key exchange is
late against its key-establishment deadline while that endpoint's RSA
certificate signature is late against a LATER, separate signature deadline"
simultaneously (see ``PQC_DEADLINES`` in ``quirk/scanner/pqc_deadlines.py``
for the literal dates). That is CLOSE-03's substance.

D-33: this is a SEPARATE module from ``quirk/intelligence/closure.py``.
``closure.py`` WRITES state; this module only READS it. The module with
write authority has no reason to import the deadline catalog, and the
module that reads policy dates has no path to mutate an item's state.

D-36: ``BURNDOWN_BUCKETS`` OVERLAP by design and are NEVER summed. A TLS
endpoint whose cipher suite resolves to ``key_establishment`` AND whose
certificate signature resolves to ``digital_signature`` is late against
BOTH deadlines and is counted in BOTH buckets. ``compute_burndown`` returns
per-bucket counts with NO grand total, NO percentage, and NO scalar
"burndown score" anywhere in its return value — computing one would require
choosing an arbitrary de-duplication rule and would recreate precisely the
single-scalar failure CLOSE-03 exists to correct.

The ONLY algorithm-classification call in this file is
``quirk.scanner.pqc_deadlines.deadline_for_algorithm``, which itself
dispatches through the CBOM classifier's algorithm-to-primitive function.
There is NO parallel
algorithm->date table anywhere in this module — a second hand-maintained
mapping is the exact defect class this milestone has already corrected
three times (three normalizer copies in 178, two alias tables in 178,
``_SLUG_PRIORITY`` in 179).

D-34 — the algorithm evidence read here is limited to a matched
``CryptoEndpoint``'s three declared columns: ``cert_pubkey_alg``,
``cert_sig_alg``, ``cipher_suite``. Rejected: importing
``quirk.qramm.evidence_bridge._extract_algorithm_names`` — a private name,
and pulling the QRAMM scoring surface into this module creates exactly the
coupling ADVISORY-01 exists to prevent, even though the data would flow the
harmless direction. Rejected: re-implementing ``quirk/cbom/builder.py``'s
per-protocol extraction (ssh_audit_json walking, cipher-suite decomposition,
JWT/container/cloud blob parsing) — that machinery exists to emit CBOM
components, a different output contract, and copying it would be the fourth
instance of the duplicate-extraction defect this milestone keeps
correcting. Accepted cost: findings whose only algorithm evidence lives in
a JSON blob resolve to ``unmapped``. That is an UNDER-claim, consistent
with this phase's bias, and D-35 makes it visible rather than silent.

D-35 — ``unmapped`` is a FIRST-CLASS REPORTED bucket, never a silent drop.
A fingerprint whose endpoint algorithms produce no deadline (or whose
endpoint row is entirely absent) lands in ``unmapped`` with ``date: None``.
The key is ALWAYS present in the return value, including when its counts
are all zero — a consumer that sees ``unmapped: {open: 40}`` knows there is
unclassified exposure; a consumer handed a dict that quietly omits those 40
does not.

This module never reaches the quantum-readiness weighting module
(ADVISORY-01, standing across Phases 177-181) and never writes state — it
is READ-ONLY over already-persisted closure/remediation data.

This is REPORT-SHAPED DATA ONLY — no rendering, no CLI, no VEX emission. All
surfacing is Phase 181's responsibility, not this module's.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from quirk.intelligence.remediation import ITEM_STATES, OPEN_LIKE_STATES
from quirk.intelligence.scope_signature import family_for_protocol
from quirk.models import CryptoEndpoint, RemediationItemFingerprint
from quirk.scanner.pqc_deadlines import PQC_DEADLINES, deadline_for_algorithm

logger = logging.getLogger(__name__)

BURNDOWN_MODEL_VERSION = "1.0.0"

# Exactly the two algorithm-class deadlines plus `unmapped`. The
# organisation-scope keys (`nist_subset`, `far_contractor`) are structurally
# unreachable here (D-16) — `deadline_for_algorithm` never returns them.
BURNDOWN_BUCKETS = ("key_establishment", "digital_signature", "unmapped")

_UNMAPPED = "unmapped"


def _empty_bucket(bucket_name: str) -> Dict[str, Any]:
    """Seed a single bucket's shape — every ITEM_STATES member plus
    `open_like` and `fingerprints`, all zeroed, plus `date`/`standard` read
    from the catalog (never restated as a literal here).
    """
    catalog_entry = PQC_DEADLINES.get(bucket_name)
    bucket: Dict[str, Any] = {
        "date": catalog_entry["date"] if catalog_entry else None,
        "standard": catalog_entry["standard"] if catalog_entry else None,
        "fingerprints": 0,
    }
    for state in ITEM_STATES:
        bucket[state] = 0
    bucket["open_like"] = 0
    return bucket


def _resolve_buckets_for_endpoint(endpoint: Optional[CryptoEndpoint]) -> list:
    """Return the list of DISTINCT deadline buckets an endpoint's algorithm
    evidence resolves to (D-34's three columns), or `["unmapped"]` if none
    resolve / the endpoint is absent (D-35).

    A fingerprint may resolve to MORE THAN ONE bucket (D-36) — e.g. an
    endpoint whose cipher_suite is rsa-kex (key_establishment) AND whose
    cert_sig_alg is rsasha256 (digital_signature) belongs to both.
    """
    if endpoint is None:
        return [_UNMAPPED]

    family = None
    try:
        family = family_for_protocol(getattr(endpoint, "protocol", None))
    except Exception:  # noqa: BLE001 — never let a malformed protocol raise
        logger.debug("burndown: family_for_protocol failed for endpoint", exc_info=True)

    candidate_values = [
        getattr(endpoint, "cert_pubkey_alg", None),
        getattr(endpoint, "cert_sig_alg", None),
        getattr(endpoint, "cipher_suite", None),
    ]

    resolved = set()
    for value in candidate_values:
        if not value:
            continue
        try:
            bucket = deadline_for_algorithm(value, family=family)
        except Exception:  # noqa: BLE001 — a malformed value falls to unmapped
            logger.debug("burndown: deadline_for_algorithm failed for value=%r", value, exc_info=True)
            bucket = None
        if bucket:
            resolved.add(bucket)

    if not resolved:
        return [_UNMAPPED]
    return sorted(resolved)


def compute_burndown(session: Any, *, scan_run_id: str) -> Dict[str, Dict[str, Any]]:
    """Aggregate per-deadline burndown for `scan_run_id`'s fingerprint rows.

    Returns one entry per member of `BURNDOWN_BUCKETS`, ALWAYS present (D-35)
    — the dict is never sparse. Each entry is
    `{"date", "standard", "open", "closed", "not_observed", "resurfaced",
    "open_like", "fingerprints"}`. No other top-level key, and no top-level
    scalar anywhere (D-36) — every value in the returned mapping is itself a
    mapping.

    A fingerprint whose endpoint algorithms resolve to MULTIPLE buckets is
    counted in EVERY one of them (D-36) — bucket counts are never
    de-duplicated across buckets and this function never computes or returns
    a sum/total/percent across buckets.

    Read-only: this function persists nothing (D-33's write/read split) and
    is never called from the scan pipeline itself (D-38 — `run_scan.py`
    calls `compute_closure` only).
    """
    result: Dict[str, Dict[str, Any]] = {
        bucket_name: _empty_bucket(bucket_name) for bucket_name in BURNDOWN_BUCKETS
    }

    endpoints_by_key = {
        (row.host, row.port): row
        for row in session.query(CryptoEndpoint)
        .filter(CryptoEndpoint.scan_run_id == scan_run_id)
        .all()
    }

    fingerprint_rows = (
        session.query(RemediationItemFingerprint)
        .filter(RemediationItemFingerprint.scan_run_id == scan_run_id)
        .all()
    )

    for fp_row in fingerprint_rows:
        endpoint = endpoints_by_key.get((fp_row.host, fp_row.port))
        buckets = _resolve_buckets_for_endpoint(endpoint)

        state = fp_row.state if fp_row.state in ITEM_STATES else None

        for bucket_name in buckets:
            bucket = result[bucket_name]
            bucket["fingerprints"] += 1
            if state is not None:
                bucket[state] += 1
                if state in OPEN_LIKE_STATES:
                    bucket["open_like"] += 1

    return result
