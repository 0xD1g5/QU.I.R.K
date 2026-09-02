"""Phase 180-02 (CLOSE-03) — classify_algorithm-backed deadline mapping tests:
catalog contents, the PKE disambiguation rule, primitive-coverage, and drift guards.

Intentionally NOT named with "staleness"/"freshness" — this file runs in the full
suite, not the CI staleness gate step (which filters with -k "staleness or freshness").
"""
from __future__ import annotations

from cyclonedx.model.crypto import CryptoPrimitive

from quirk.cbom.classifier import _ALGORITHM_TABLE
from quirk.scanner.pqc_deadlines import (
    PQC_DEADLINES,
    PRIMITIVE_DEADLINE,
    _PKE_DISAMBIGUATION,
    _PKE_SENTINEL,
    deadline_for_algorithm,
)


# ---------------- catalog contents ----------------


def test_catalog_has_exactly_four_deadlines() -> None:
    assert set(PQC_DEADLINES.keys()) == {
        "key_establishment",
        "digital_signature",
        "nist_subset",
        "far_contractor",
    }


def test_algorithm_class_deadlines_carry_standard_and_scope() -> None:
    assert PQC_DEADLINES["key_establishment"]["date"] == "2030-12-31"
    assert PQC_DEADLINES["key_establishment"]["standard"] == "FIPS 203 (ML-KEM)"
    assert PQC_DEADLINES["key_establishment"]["scope"] == "algorithm_class"

    assert PQC_DEADLINES["digital_signature"]["date"] == "2031-12-31"
    assert PQC_DEADLINES["digital_signature"]["standard"] == "FIPS 186-5 (DSS)"
    assert PQC_DEADLINES["digital_signature"]["scope"] == "algorithm_class"


def test_organisation_scope_deadlines_carry_correct_dates() -> None:
    assert PQC_DEADLINES["nist_subset"]["date"] == "2027-12-31"
    assert PQC_DEADLINES["nist_subset"]["scope"] == "organisation"

    assert PQC_DEADLINES["far_contractor"]["date"] == "2030-12-31"
    assert PQC_DEADLINES["far_contractor"]["scope"] == "organisation"


# ---------------- deadline_for_algorithm() dispatch ----------------


def test_deadline_for_algorithm_pke_disambiguation() -> None:
    assert deadline_for_algorithm("rsa-kex") == "key_establishment"
    assert deadline_for_algorithm("rsasha256") == "digital_signature"
    assert deadline_for_algorithm("rsa-2048") == "digital_signature"


def test_deadline_for_algorithm_non_pke_primitives() -> None:
    assert deadline_for_algorithm("ml-kem-768") == "key_establishment"
    assert deadline_for_algorithm("ecdsa-sha2-nistp256") == "digital_signature"
    assert deadline_for_algorithm("aes-256-gcm") is None


# ---------------- T-180-10: PKE drift guard ----------------


def _pke_slugs_in_algorithm_table() -> set:
    return {
        k for k, v in _ALGORITHM_TABLE.items() if v[0] is CryptoPrimitive.PKE
    }


def test_pke_disambiguation_covers_every_pke_row() -> None:
    """The 11-row PKE audit (reproduced 2026-09-02):
    rsa, rsa-1024, rsa-2048, rsa-3072, rsa-4096, rsa-kex,
    rsamd5, rsasha1, rsasha1-nsec3-sha1, rsasha256, rsasha512.

    A new upstream PKE row must fail this RED, not silently default.
    """
    expected = _pke_slugs_in_algorithm_table()
    assert set(_PKE_DISAMBIGUATION.keys()) == expected, (
        f"_PKE_DISAMBIGUATION drifted from _ALGORITHM_TABLE's PKE rows: "
        f"missing={expected - set(_PKE_DISAMBIGUATION.keys())}, "
        f"extra={set(_PKE_DISAMBIGUATION.keys()) - expected}"
    )


def test_pke_disambiguation_guard_detects_drift_negative_control() -> None:
    """Negative control: the same set-equality check applied to a fixture dict
    that OMITS one known PKE slug must report a mismatch. A guard that can only
    pass is not a guard (Phase 179 _SLUG_PRIORITY precedent)."""
    expected = _pke_slugs_in_algorithm_table()
    incomplete_fixture = dict(_PKE_DISAMBIGUATION)
    removed_slug = next(iter(incomplete_fixture))
    del incomplete_fixture[removed_slug]

    mismatch = set(incomplete_fixture.keys()) != expected
    assert mismatch, "negative control fixture should NOT equal the real PKE slug set"
    missing = expected - set(incomplete_fixture.keys())
    assert missing == {removed_slug}, (
        f"drift guard failed to detect the removed slug {removed_slug!r}: "
        f"detected missing={missing}"
    )


# ---------------- T-180-11: every primitive has an explicit disposition ----------------


def test_every_classifier_primitive_has_an_explicit_disposition() -> None:
    primitives_in_table = {v[0] for v in _ALGORITHM_TABLE.values()}
    valid_values = {"key_establishment", "digital_signature", None, _PKE_SENTINEL}

    for primitive in primitives_in_table:
        assert primitive in PRIMITIVE_DEADLINE, (
            f"CryptoPrimitive {primitive} appears in _ALGORITHM_TABLE but has no "
            f"entry in PRIMITIVE_DEADLINE — every emitted primitive must have an "
            f"explicit disposition, None included."
        )
        assert PRIMITIVE_DEADLINE[primitive] in valid_values, (
            f"PRIMITIVE_DEADLINE[{primitive}] = {PRIMITIVE_DEADLINE[primitive]!r} "
            f"is not one of {valid_values}"
        )


# ---------------- T-180-12: no parallel algorithm->deadline table ----------------


def test_no_parallel_algorithm_deadline_table() -> None:
    """The only algorithm-keyed structure in the module is _PKE_DISAMBIGUATION,
    whose values are bucket NAMES, never dates."""
    import re
    import inspect

    from quirk.scanner import pqc_deadlines

    source = inspect.getsource(pqc_deadlines)
    date_literal = re.compile(r"20\d{2}-\d{2}-\d{2}")

    # Strip PQC_DEADLINES block and the docstring/comments — dates are expected
    # there. Verify no date literal exists inside the deadline_for_algorithm /
    # PRIMITIVE_DEADLINE / _PKE_DISAMBIGUATION section of the module.
    mapping_section_start = source.index("_PKE_SENTINEL = ")
    mapping_section = source[mapping_section_start:]
    # Strip comment lines (`#`-prefixed prose, e.g. D-17's rule explanation, is
    # allowed to reference dates in passing) — mirrors the plan's
    # `grep -v '^\s*#'` acceptance check.
    code_only = "\n".join(
        line for line in mapping_section.splitlines()
        if not line.strip().startswith("#")
    )

    assert not date_literal.search(code_only), (
        "found a date literal in the algorithm-mapping section of the module — "
        "this suggests a parallel algorithm->deadline table has been introduced. "
        "Dates must live ONLY in PQC_DEADLINES; mapping logic must dispatch "
        "through classify_algorithm() and bucket NAMES only."
    )

    for value in _PKE_DISAMBIGUATION.values():
        assert not date_literal.match(value), (
            f"_PKE_DISAMBIGUATION value {value!r} looks like a date literal — "
            f"values must be bucket names (key_establishment/digital_signature), "
            f"never dates."
        )


# ---------------- T-180-11/D-16: organisation-scope deadlines unreachable ----------------


def test_organisation_scope_deadlines_are_never_returned() -> None:
    """Sweeping every algorithm key in _ALGORITHM_TABLE, deadline_for_algorithm
    must never yield nist_subset or far_contractor (D-16)."""
    for algorithm in _ALGORITHM_TABLE:
        result = deadline_for_algorithm(algorithm)
        assert result not in ("nist_subset", "far_contractor"), (
            f"deadline_for_algorithm({algorithm!r}) returned {result!r} — "
            f"organisation-scope deadlines must never be reachable from an "
            f"algorithm-keyed lookup."
        )
