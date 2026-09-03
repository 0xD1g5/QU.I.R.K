"""Phase 180 Plan 06 (CLOSE-03): per-deadline burndown aggregation test suite.

Burndown is REPORT-SHAPED DATA ONLY — no rendering, no CLI, no VEX. Phase 181
owns every surface that reads this data; this file only proves the data
shape and its invariants are correct in isolation.

CLOSE-03's substance is that ONE SCALAR cannot express "this endpoint's RSA
key exchange is late against 2030-12-31 while that endpoint's RSA
certificate signature is late against 2031-12-31" — the two EO 14412 dates
report SEPARATELY, buckets OVERLAP and are NEVER summed, and there is no
top-level scalar anywhere in the return value (D-36).

D-34's accepted under-claim: the algorithm evidence `compute_burndown` reads
is limited to a matched `CryptoEndpoint`'s three declared columns
(`cert_pubkey_alg`, `cert_sig_alg`, `cipher_suite`). A finding whose only
algorithm evidence lives in a JSON blob (ssh_audit_json, JWT/container/cloud
blobs) resolves to `unmapped`, not a date bucket — this is a decided,
documented under-claim (D-34), not a missed case. `unmapped` is a
first-class REPORTED bucket (D-35), never a silent drop.
"""
from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

from quirk.db import get_session, init_db
from quirk.models import CryptoEndpoint, RemediationItemFingerprint

SCAN_RUN_ID = "scan-burndown-0001"
SLUG = "weak-tls-cipher"


def _seed_fingerprint(
    session,
    *,
    scan_run_id=SCAN_RUN_ID,
    slug=SLUG,
    finding_fingerprint="fp-0001",
    host="10.0.0.9",
    port=443,
    state="open",
):
    fp = RemediationItemFingerprint(
        remediation_item_id=None,
        slug=slug,
        scan_run_id=scan_run_id,
        finding_fingerprint=finding_fingerprint,
        host=host,
        port=port,
        finding_title="Weak TLS cipher suite in use",
        state=state,
        observed_at=datetime.now(timezone.utc),
    )
    session.add(fp)
    return fp


def _seed_endpoint(
    session,
    *,
    scan_run_id=SCAN_RUN_ID,
    host="10.0.0.9",
    port=443,
    protocol="TLS",
    cipher_suite=None,
    cert_sig_alg=None,
    cert_pubkey_alg=None,
):
    ep = CryptoEndpoint(
        scan_run_id=scan_run_id,
        host=host,
        port=port,
        protocol=protocol,
        cipher_suite=cipher_suite,
        cert_sig_alg=cert_sig_alg,
        cert_pubkey_alg=cert_pubkey_alg,
    )
    session.add(ep)
    return ep


# ---------------------------------------------------------------------------
# CLOSE-03 acceptance: two dates report separately
# ---------------------------------------------------------------------------
def test_burndown_reports_two_dates_separately(tmp_path):
    """The CLOSE-03 acceptance test — name it so a failure says so."""
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        _seed_endpoint(session, host="10.0.0.1", port=443, cipher_suite="rsa-kex")
        _seed_fingerprint(session, host="10.0.0.1", port=443, finding_fingerprint="fp-kex")

        _seed_endpoint(session, host="10.0.0.2", port=443, cert_sig_alg="rsasha256")
        _seed_fingerprint(session, host="10.0.0.2", port=443, finding_fingerprint="fp-sig")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    assert result["key_establishment"]["date"] == "2030-12-31"
    assert result["key_establishment"]["fingerprints"] >= 1
    assert result["digital_signature"]["date"] == "2031-12-31"
    assert result["digital_signature"]["fingerprints"] >= 1


# ---------------------------------------------------------------------------
# D-36: no scalar anywhere
# ---------------------------------------------------------------------------
def test_burndown_returns_no_scalar(tmp_path):
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        _seed_endpoint(session, cipher_suite="rsa-kex")
        _seed_fingerprint(session)
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(value, dict), f"top-level key {key!r} is not a mapping: {value!r}"
    forbidden_keys = {"total", "score", "percent"}
    assert not (forbidden_keys & set(result.keys())), (
        f"forbidden scalar-shaped top-level key found: {forbidden_keys & set(result.keys())}"
    )


# ---------------------------------------------------------------------------
# D-36: overlap, never deduplicated
# ---------------------------------------------------------------------------
def test_buckets_overlap_and_are_not_deduplicated(tmp_path):
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        # One endpoint carrying BOTH an rsa-kex cipher_suite AND an rsasha256
        # cert_sig_alg — late against BOTH deadlines simultaneously.
        _seed_endpoint(
            session,
            host="10.0.0.3",
            port=443,
            cipher_suite="rsa-kex",
            cert_sig_alg="rsasha256",
        )
        _seed_fingerprint(session, host="10.0.0.3", port=443, finding_fingerprint="fp-both")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    key_est_count = result["key_establishment"]["fingerprints"]
    sig_count = result["digital_signature"]["fingerprints"]
    assert key_est_count == 1
    assert sig_count == 1
    # The single fingerprint counted in both buckets: the two bucket counts
    # must NOT sum to the total distinct fingerprint count seeded (1) summed
    # as if mutually exclusive would give 2 == fingerprint_count*2, which is
    # what we assert IS the case (both buckets independently see it) rather
    # than a deduplicated total of 1 across both.
    assert key_est_count + sig_count != 1  # not deduplicated down to 1
    assert key_est_count + sig_count == 2  # both buckets independently counted it


# ---------------------------------------------------------------------------
# D-35: unmapped always present and reported
# ---------------------------------------------------------------------------
def test_unmapped_bucket_is_always_present_and_reported(tmp_path):
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        _seed_endpoint(session, cipher_suite="aes-256-gcm")  # deadline: None
        _seed_fingerprint(session, finding_fingerprint="fp-unmapped")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    assert "unmapped" in result
    assert result["unmapped"]["date"] is None
    assert result["unmapped"]["fingerprints"] >= 1

    # A scan with zero unmapped findings STILL returns the key, zeroed.
    db_path2 = str(tmp_path / "quirk2.db")
    init_db(db_path2)
    with get_session(db_path2) as session:
        _seed_endpoint(session, cipher_suite="rsa-kex")
        _seed_fingerprint(session, finding_fingerprint="fp-mapped")
        session.commit()
    with get_session(db_path2) as session:
        result2 = compute_burndown(session, scan_run_id=SCAN_RUN_ID)
    assert "unmapped" in result2
    assert result2["unmapped"]["fingerprints"] == 0


# ---------------------------------------------------------------------------
# D-16: organisation-scope deadlines never appear
# ---------------------------------------------------------------------------
def test_organisation_scope_deadlines_never_appear(tmp_path):
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        _seed_endpoint(session, host="10.0.0.4", port=443, cipher_suite="rsa-kex")
        _seed_fingerprint(session, host="10.0.0.4", port=443, finding_fingerprint="fp-a")
        _seed_endpoint(session, host="10.0.0.5", port=443, cert_sig_alg="rsasha256")
        _seed_fingerprint(session, host="10.0.0.5", port=443, finding_fingerprint="fp-b")
        _seed_endpoint(session, host="10.0.0.6", port=443, cipher_suite="aes-256-gcm")
        _seed_fingerprint(session, host="10.0.0.6", port=443, finding_fingerprint="fp-c")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    assert "nist_subset" not in result
    assert "far_contractor" not in result


# ---------------------------------------------------------------------------
# Shape must reuse the closure vocabulary
# ---------------------------------------------------------------------------
def test_burndown_states_use_the_closure_vocabulary(tmp_path):
    from quirk.intelligence.burndown import compute_burndown
    from quirk.intelligence.remediation import ITEM_STATES

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        _seed_endpoint(session, cipher_suite="rsa-kex")
        _seed_fingerprint(session, state="open")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    for bucket_name, bucket in result.items():
        for state in ITEM_STATES:
            assert state in bucket, f"bucket {bucket_name!r} missing state {state!r}"
        assert "open_like" in bucket
        assert "fingerprints" in bucket


# ---------------------------------------------------------------------------
# No parallel algorithm->deadline table
# ---------------------------------------------------------------------------
def _uses_only_deadline_for_algorithm(source: str) -> bool:
    """AST-walk `source`; return True iff the ONLY algorithm-classification
    call present is `deadline_for_algorithm` (never `classify_algorithm`
    called directly, and never a dict literal mapping an algorithm string to
    a date literal).
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "classify_algorithm":
                return False
    return True


def _has_parallel_alg_deadline_dict(source: str) -> bool:
    """Return True iff `source` contains a dict literal whose values look
    like date strings (a parallel algorithm->deadline table).
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    v = value.value
                    if len(v) == 10 and v[4] == "-" and v[7] == "-" and v.replace("-", "").isdigit():
                        return True
    return False


def test_burndown_uses_classify_algorithm_only(tmp_path):
    burndown_path = Path(__file__).resolve().parent.parent / "quirk" / "intelligence" / "burndown.py"
    if not burndown_path.exists():
        pytest.skip("burndown.py not yet created (Task 1 is RED-only)")
    source = burndown_path.read_text()
    assert _uses_only_deadline_for_algorithm(source), (
        "burndown.py calls classify_algorithm() directly — it must dispatch "
        "through deadline_for_algorithm() only"
    )
    assert not _has_parallel_alg_deadline_dict(source), (
        "burndown.py appears to contain a parallel algorithm->date dict literal"
    )
    assert "deadline_for_algorithm" in source

    # Negative control: the SAME check against a fixture that DOES contain a
    # parallel table must report a violation.
    fixture_source = (
        "_ALG_DEADLINES = {\"rsa\": \"2030-12-31\"}\n"
        "def f():\n"
        "    return _ALG_DEADLINES.get('rsa')\n"
    )
    assert _has_parallel_alg_deadline_dict(fixture_source), (
        "negative control failed — the parallel-table detector did not fire "
        "on a fixture source that DOES contain one"
    )


# ---------------------------------------------------------------------------
# Missing endpoint row -> unmapped, never an exception
# ---------------------------------------------------------------------------
def test_burndown_handles_missing_endpoint_row(tmp_path):
    from quirk.intelligence.burndown import compute_burndown

    db_path = str(tmp_path / "quirk.db")
    init_db(db_path)
    with get_session(db_path) as session:
        # No matching CryptoEndpoint row for this fingerprint's host:port.
        _seed_fingerprint(session, host="10.0.0.99", port=9999, finding_fingerprint="fp-orphan")
        session.commit()

    with get_session(db_path) as session:
        result = compute_burndown(session, scan_run_id=SCAN_RUN_ID)

    assert result["unmapped"]["fingerprints"] >= 1
    assert "key_establishment" in result
    assert "digital_signature" in result


# ---------------------------------------------------------------------------
# Task 3: pipeline ordering source assertions (added when run_scan.py wired)
# ---------------------------------------------------------------------------
def test_closure_verify_phase_ordering():
    run_scan_path = Path(__file__).resolve().parent.parent / "run_scan.py"
    source = run_scan_path.read_text()
    assert '"scope_signature"' in source
    assert '"closure_verify"' in source
    assert source.index('"scope_signature"') < source.index('"closure_verify"')
    assert source.index('"closure_verify"') < source.index('_phase_timer(run_stats, "reporting")')


def test_run_scan_does_not_call_compute_burndown():
    run_scan_path = Path(__file__).resolve().parent.parent / "run_scan.py"
    source = run_scan_path.read_text()
    assert "compute_burndown" not in source
