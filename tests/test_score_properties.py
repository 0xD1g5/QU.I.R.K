"""P1-P8 + calibration ladder — readiness-score PROPERTY suite: does the number
carry the MEANING?

Backlog: ``999.115`` (P1, ``.planning/HORIZON.md``) — "the readiness score's
usable range is ~85-100, so real-world badness is compressed into the top 15
points and reads as a B+". Successor to ``999.113`` (CLOSED), which was
necessary but not sufficient.

WHY THIS FILE EXISTS
--------------------
The repository already carries ~3,200 lines of scoring tests. Every one of
them asserts **mechanism** (this ratio uses that denominator), **bounds** (the
score stays within 0-100), or **rendering** (the subscore table shows an em
dash for an unassessed domain). None of them asserts **meaning** — that the
number moves the way a consulting engagement needs it to move.

The consequence is on the record three times, and each instance was found by
accident rather than by a test:

    999.95   (Phase 188 SCORE-06)  domains with ZERO evidence scored 25/25
    999.113  (2026-09-13)          domains with REAL evidence scored 25/25
    999.115  (this file's subject) realistic badness compressed at the top

P7 adds a fourth instance found by this very suite, at the opposite end of the
scale: a hygiene-perfect estate with ZERO post-quantum readiness scores 100 on
a Quantum Infrastructure Readiness Kit, and adopting hybrid PQC key exchange
everywhere is worth 0 points. Same saturating ``_clamp(total, 0.0, 25.0)`` that
makes P4's floor unreachable also makes P7's ceiling unearned — the model stops
registering signal at both extremes, which is the whole of 999.115's argument
stated twice.

P8 adds a fifth instance, found by decomposing the ladder's own ordering
violation rather than by inspection: an estate whose certificate key types are
UNREPORTED scores 100 — the same as fully-modern ECDSA, and 5 points above the
same estate honestly reporting RSA-only. Absence scoring as the best case is
999.95's exact signature, recurring at signal granularity after Phase 188
SCORE-06 closed it at domain granularity.

CALIBRATION LADDER — COMPLETE AS OF 2026-09-14
-----------------------------------------------
Operator-set, supplied BLIND (each estate described in infrastructure terms,
with no score shown), and NOT for code to revise:

    R1  pristine, PQC-ready      EXCELLENT     2026-09-14
    R2  well-run, no PQC         GOOD          2026-09-14
    R3  typical enterprise       FAIR          2026-09-14
    R4  neglected                POOR          2026-09-14
    R5  multihost (31 hosts)     score < 30    2026-09-14 (was < 40, 2026-09-13)

R5's ceiling tightened because R4's POOR target made 40 non-binding — R5 is
strictly worse infrastructure than R4, so a monotonic ladder could not leave
R5's ceiling above R4's floor. The operator resolved it downward.

THE BASELINE RESULT — measured 2026-09-14 against the model as it stood
BEFORE any 999.115 fix, and recorded here as the motivation for the work, not
as a current reading: every rung landed in ONE band, EXCELLENT, spanning 15
points (85..100) — pristine and quantum-ready through to a purpose-built
31-host catastrophe, all graded the same. Only R1 hit its target, and the
ladder was not monotonic (R4=85 below R5=87, the strictly worse estate).

**Do not read the line above as the score's behaviour today.** Fixes are
landing incrementally, each promoting its property from `xfail` to a green
gate. For a current reading, run the suite — the pass/xfail split IS the live
measurement, which is the whole reason this file exists.

``tests/test_scoring_correctness.py::test_score_always_bounded_1000_iterations``
is passed perfectly by a function that ignores its argument and returns the
constant ``91``. That is the gap this file closes: these are the assertions
such a function fails.

THE SUITE IS AN INSTRUMENT, NOT A VERDICT
-----------------------------------------
999.115 lists four candidate model shapes (A larger weights / B start-at-zero /
C absolute severity term / D non-linear penalty curve) and requires the choice
be made **by measurement against a calibration ladder, not by argument**.
Attempt #1 at fixing the score (Phase 188 SCORE-06) failed precisely because
nothing could tell whether a change had helped. These properties are the
instrument that makes the next attempt an experiment. Run the candidates
through them; do not begin by picking a shape.

READING THE ``xfail`` MARKERS — THEY ARE THE DELIVERABLE
---------------------------------------------------------
Many of the test nodes below are marked ``@pytest.mark.xfail(strict=True)``.
That is NOT a way to hide a failure — it is how a known calibration gap is kept
*standing and numeric* instead of decaying into prose:

  * Today they fail, and ``strict=True`` records each as XFAIL with the
    measured number in its reason string. ``main`` CI stays honest rather than
    carrying a bank of permanent reds (this project has documented how
    corrosive a normalised red gate is).

  * No count is stated here, deliberately. An earlier revision of this
    docstring said "Five", then "Eleven", and was wrong within one working
    session both times. Re-derive it — ``pytest -q
    tests/test_score_properties.py`` prints the live figure — and do not
    reintroduce a number anyone has to remember to update. A hand-maintained
    list of sites is not a safeguard; this project has been bitten by that five
    separate times (CLAUDE.md).
  * When a model change lands, a fixed property XPASSes — and ``strict=True``
    turns an unexpected pass into a **hard failure**. Nobody can quietly
    improve the model without coming back here, deleting the marker, and
    converting the property into a standing green gate.

So: an XFAIL here means "still miscalibrated, by exactly this much". An XPASS
failure means "you fixed it — now promote the test". Neither is noise.

Every measured figure in this file was produced by running the scorer, not by
reading it. Per ``.planning/.continue-here.md``'s blocking constraint, the
instrument itself carries a known-positive control
(``test_control_probe_can_distinguish_a_healthy_estate_from_a_broken_one``) —
a measurement that cannot tell good from bad reports its own blind spot as a
confident zero, which happened three times in the session that filed 999.115.

RED-PROOF
---------
Per Phase 205-04's precedent, the failing properties were red-proved by
execution against current ``main`` (``pytest --runxfail``), and the captured
failure messages are recorded in the task-8 report / ``999.115`` notes. A
property suite that passes on code you know is broken is testing nothing.
"""
from __future__ import annotations

import copy
from typing import Any, Dict

import pytest

from quirk.intelligence.scoring import compute_readiness_score
from quirk.severity_bands import BAND_THRESHOLDS, band_for_score


# ---------------------------------------------------------------------------
# Reference estates.
#
# `_multihost_evidence()` mirrors the fixture in
# `tests/test_score_denominator_999_113.py` — the recorded 31-host
# deliberately-vulnerable chaos-lab estate (`multihost` profile, measured
# 2026-09-13). It is duplicated rather than imported because cross-importing
# between test modules couples two suites' fixtures to each other; if you
# change one, change both, and re-measure — P4's numbers are keyed to it.
#
# `_multihost_evidence()` is rung R5 of the calibration ladder; R1-R4 are built
# from `_base_estate()` further down. All five target bands were set by the
# operator — code cannot self-certify what score should alarm a client.
# ---------------------------------------------------------------------------

# Operator-set bottom rung: the multihost reference estate must score below
# this. Not negotiable by code, and NOT to be relaxed to make a test pass —
# 999.113 D5 forbids tuning to a target, and that applies to the target as
# much as to the weights.
#
# TIGHTENED 2026-09-14, from 40 to 30. The original 40 (set 2026-09-13) is
# recorded here rather than overwritten, because the reason it moved is the
# useful part: setting R4 "neglected" to POOR (< 35) made 40 non-binding. R5 is
# strictly worse infrastructure than R4 — 5 CRITICAL and 14 HIGH against R4's
# 2 CRITICAL, 29% of certificates expired — so a ladder that stayed monotonic
# could not leave R5's ceiling above R4's floor. The operator resolved it
# downward rather than relaxing R4.
MULTIHOST_CALIBRATION_CEILING = 30


def _multihost_evidence() -> Dict[str, Any]:
    """31 hosts, purpose-built to be catastrophically bad.

    5 CRITICAL / 14 HIGH / 33 MEDIUM findings, 29% of certificates expired,
    18% self-signed, plaintext HTTP on 6 of 38 assessable endpoints. A
    consultant shown this estate would not call it a B+.
    """
    return {
        "totals": {"endpoints": 370, "findings": 5 + 14 + 33 + 16 + 330},
        "protocol_counts": {
            "TLS": 40, "HTTP": 5, "SSH": 3, "UNKNOWN": 2,
            "POSTGRESQL": 1, "S3": 1, "KUBERNETES": 1, "VAULT": 1,
            "KERBEROS": 1, "SAML": 1, "DNSSEC": 1,
            "SMTP-STARTTLS": 1, "KAFKA-TLS": 1,
        },
        "assessable_endpoint_count": 38,
        "plaintext_http_count": 6,
        "http_on_tls_port_count": 3,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 0, "ECDSA": 0},
        "certificate_observations": {
            "certs_observed": 17,
            "expired_count": 5,
            "expiring_count": 1,
            "self_signed_count": 3,
        },
        "scan_error": {"count": 0, "rate": 0.0},
        "finding_severity_counts": {
            "CRITICAL": 5, "HIGH": 14, "MEDIUM": 33, "LOW": 16, "INFO": 330,
        },
    }


def _remediated_multihost_evidence() -> Dict[str, Any]:
    """The SAME estate after a complete, successful remediation programme.

    Same hosts, same services, same domains assessed — every weakness this
    product can detect has been fixed. This is the far end of the engagement:
    the best outcome a client can buy. The distance between this and
    `_multihost_evidence()` is the entire dynamic range the score has to
    express a year of security work in.
    """
    ev = _multihost_evidence()
    ev["plaintext_http_count"] = 0
    ev["http_on_tls_port_count"] = 0
    ev["protocol_counts"]["UNKNOWN"] = 0
    ev["cert_key_type_counts"] = {"RSA": 0, "ECDSA": 17}
    ev["certificate_observations"] = {
        "certs_observed": 17,
        "expired_count": 0,
        "expiring_count": 0,
        "self_signed_count": 0,
    }
    ev["finding_severity_counts"] = {
        "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 330,
    }
    ev["totals"]["findings"] = 330
    return ev


def _pqc_ready_estate() -> Dict[str, Any]:
    """`_remediated_multihost_evidence()` plus demonstrated PQC readiness.

    Identical infrastructure and identical hygiene — the ONLY difference is
    that hybrid X25519MLKEM768 key exchange is observed on every endpoint.
    This is the top rung of the calibration ladder, and the pair
    (`_remediated_multihost_evidence()`, this) isolates what post-quantum
    adoption is worth to the headline number.
    """
    ev = _remediated_multihost_evidence()
    ev["pqc_hybrid_endpoint_count"] = ev["assessable_endpoint_count"]
    return ev


# ---------------------------------------------------------------------------
# THE CALIBRATION LADDER — rungs R1-R4, target bands set by the operator
# 2026-09-14 (R5 is the multihost estate above, set 2026-09-13).
#
# Every rung shares ONE estate SHAPE: 40 assessable endpoints, 40 observed
# certificates, and the same protocol mix so all six domains are assessed in
# every rung. Only the WEAKNESSES vary. That is deliberate — if the shape moved
# between rungs, `domains_assessed` would move the rescale denominator and the
# rungs would stop being comparable to each other, which is the one thing a
# ladder must be.
#
# The bands were supplied BLIND, before any rung was scored, so the ladder is
# an independent instrument rather than a description of the current model.
# ---------------------------------------------------------------------------

def _base_estate() -> Dict[str, Any]:
    """The shared skeleton: 40 healthy endpoints, all six domains assessed."""
    return {
        "totals": {"endpoints": 400, "findings": 100},
        "protocol_counts": {
            "TLS": 40, "SSH": 4, "UNKNOWN": 0,
            "POSTGRESQL": 2, "S3": 1, "KUBERNETES": 1, "VAULT": 1,
            "KERBEROS": 1, "SAML": 1, "DNSSEC": 1,
            "SMTP-STARTTLS": 1, "KAFKA-TLS": 1,
        },
        "assessable_endpoint_count": 40,
        "plaintext_http_count": 0,
        "http_on_tls_port_count": 0,
        "mtls_present_count": 0,
        "cert_key_type_counts": {"RSA": 0, "ECDSA": 40},
        "certificate_observations": {
            "certs_observed": 40, "expired_count": 0,
            "expiring_count": 0, "self_signed_count": 0,
        },
        "scan_error": {"count": 0, "rate": 0.0},
        "finding_severity_counts": {
            "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 100,
        },
    }


def _r1_pristine_pqc_ready() -> Dict[str, Any]:
    """R1 — target band EXCELLENT.

    TLS 1.3 throughout, hybrid X25519MLKEM768 observed on every endpoint,
    ECDSA certificates, mTLS enforced, nothing expired or self-signed, no
    plaintext, no finding above INFO. There is no further work to recommend.
    """
    ev = _base_estate()
    ev["pqc_hybrid_endpoint_count"] = 40
    ev["mtls_present_count"] = 40
    return ev


def _r2_well_run_no_pqc() -> Dict[str, Any]:
    """R2 — target band GOOD.

    Hygienically spotless but quantum-blind: RSA certificates, no PQC key
    exchange anywhere, two of forty certificates inside their renewal window,
    a handful of MEDIUM findings, zero HIGH or CRITICAL.

    This is the rung the operator's "no PQC, no 100" decision makes load
    bearing: the gap between R1 and R2 is *exactly* what post-quantum
    readiness is worth, with classical hygiene held near-perfect.
    """
    ev = _base_estate()
    ev["cert_key_type_counts"] = {"RSA": 40, "ECDSA": 0}
    ev["certificate_observations"]["expiring_count"] = 2
    ev["finding_severity_counts"]["MEDIUM"] = 5
    ev["totals"]["findings"] = 105
    return ev


def _r3_typical_enterprise() -> Dict[str, Any]:
    """R3 — target band FAIR.

    The estate most engagements actually meet: one legacy TLS endpoint, two of
    forty certificates already expired, self-signed certificates on internal
    services, a plaintext admin page, a dozen MEDIUM findings and three HIGH,
    no CRITICAL. Real gaps, nothing on fire.
    """
    ev = _base_estate()
    ev["cert_key_type_counts"] = {"RSA": 40, "ECDSA": 0}
    ev["certificate_observations"] = {
        "certs_observed": 40, "expired_count": 2,
        "expiring_count": 3, "self_signed_count": 6,
    }
    ev["plaintext_http_count"] = 1
    ev["finding_severity_counts"] = {
        "CRITICAL": 0, "HIGH": 3, "MEDIUM": 12, "LOW": 1, "INFO": 100,
    }
    ev["totals"]["findings"] = 116
    return ev


def _r4_neglected() -> Dict[str, Any]:
    """R4 — target band POOR.

    An estate that has stopped being maintained: eight expired certificates,
    twelve self-signed, five plaintext services, legacy TLS widespread, an
    unencrypted database connection, two CRITICAL findings.

    Note the ordering constraint this rung creates. R4 is strictly BETTER
    infrastructure than R5 (the 31-host multihost estate: 5 CRITICAL, 14 HIGH,
    29% of certificates expired), so a POOR target here implies R5 must score
    at or below R4 — tightening R5's original 2026-09-13 ceiling of 40. Both
    are asserted; `test_ladder_is_monotonic` is what enforces the relationship.
    """
    ev = _base_estate()
    ev["cert_key_type_counts"] = {"RSA": 40, "ECDSA": 0}
    ev["certificate_observations"] = {
        "certs_observed": 40, "expired_count": 8,
        "expiring_count": 5, "self_signed_count": 12,
    }
    ev["plaintext_http_count"] = 5
    ev["http_on_tls_port_count"] = 2
    ev["protocol_counts"]["UNKNOWN"] = 2
    ev["dar_db_plaintext_count"] = 1
    ev["finding_severity_counts"] = {
        "CRITICAL": 2, "HIGH": 8, "MEDIUM": 20, "LOW": 6, "INFO": 100,
    }
    ev["totals"]["findings"] = 136
    return ev


# Operator-set target bands, 2026-09-14, supplied blind. The ladder runs from
# best to worst; `_multihost_evidence` is the fifth rung and keeps its own
# separately-set numeric ceiling (P4).
CALIBRATION_LADDER = (
    ("R1 pristine, PQC-ready", _r1_pristine_pqc_ready, "EXCELLENT"),
    ("R2 well-run, no PQC", _r2_well_run_no_pqc, "GOOD"),
    ("R3 typical enterprise", _r3_typical_enterprise, "FAIR"),
    ("R4 neglected", _r4_neglected, "POOR"),
)


def _band_range(band: str) -> tuple:
    """Inclusive (low, high) score range for a band, derived from
    `BAND_THRESHOLDS` rather than restated — so a threshold change moves the
    ladder's targets with it instead of silently invalidating them."""
    ordered = sorted(BAND_THRESHOLDS.items(), key=lambda kv: -kv[1])
    for index, (name, low) in enumerate(ordered):
        if name == band:
            high = 100 if index == 0 else ordered[index - 1][1] - 1
            return (low, high)
    if band == "POOR":
        return (0, min(BAND_THRESHOLDS.values()) - 1)
    raise AssertionError(f"unknown band {band!r}; known: {list(BAND_THRESHOLDS)} + POOR")


def _score(evidence: Dict[str, Any]) -> int:
    """Score an estate, refusing a `None` headline.

    Every fixture in this file assesses at least one domain, so a `None` here
    means the fixture broke, not that the property under test failed. Failing
    loudly on that is the difference between a measurement and a guess.
    """
    result = compute_readiness_score(evidence)
    assert result["score"] is not None, (
        "fixture assessed zero domains — the instrument is broken, not the "
        f"subject. coverage: {result['coverage_disclosure']}"
    )
    return int(result["score"])


# ---------------------------------------------------------------------------
# CONTROL — required by .planning/.continue-here.md's blocking constraint.
# ---------------------------------------------------------------------------

def test_control_probe_can_distinguish_a_healthy_estate_from_a_broken_one():
    """Known-positive control for every other test in this file.

    A measurement you wrote can report its own blind spot as a confident
    zero — this happened three times in the session that filed 999.115, and
    each time the wrong conclusion read as good news. So before any property
    below is believed, prove the harness responds to the thing it claims to
    measure at all.

    If THIS fails, nothing else in this file means anything: the fixtures or
    the evidence-key names have drifted, and the other tests are measuring
    nothing while reporting confidently.
    """
    healthy = _remediated_multihost_evidence()
    broken = _multihost_evidence()

    healthy_score = _score(healthy)
    broken_score = _score(broken)

    assert healthy_score > broken_score, (
        f"CONTROL FAILED: a fully remediated estate scored {healthy_score} and "
        f"a catastrophically vulnerable one scored {broken_score}. The harness "
        "cannot tell good infrastructure from bad, so every other assertion in "
        "this file is vacuous. Fix the fixtures before reading any result here."
    )


# ---------------------------------------------------------------------------
# P1 — MONOTONICITY. Adding a real weakness must never RAISE the score.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "999.115 / measured 2026-09-14: 8 violations on the multihost estate. "
        "agility_high_impact_ratio divides HIGH+CRITICAL by actionable_denom "
        "(CRITICAL+HIGH+MEDIUM+LOW), so MEDIUM and LOW findings enlarge the "
        "denominator while appearing in NO numerator of that ratio — each one "
        "discovered dilutes the high-impact ratio. Measured: +50 MEDIUM moves "
        "agility_signals 21 -> 22; +100 MEDIUM moves the HEADLINE 87 -> 88; "
        "+1000 MEDIUM moves it 87 -> 89; +50/+100/+1000 LOW move agility_signals "
        "21 -> 22/23/24. The LOW cases were NOT predicted by inspection — LOW "
        "does feed a numerator elsewhere (modern_tls legacy-versions), so its "
        "headline effect is net-negative and it masks a real subscore "
        "regression. Found by sweeping, not by reading. Remove this marker "
        "when a model change makes the property pass."
    ),
)
def test_p1_adding_findings_never_raises_the_score():
    """P1 — discovering more genuine weakness must not improve the verdict.

    This is the most basic thing a client assumes about a security score, and
    it is the one a ratio-based model is structurally prone to breaking: any
    severity that sits in a denominator without also sitting in a numerator
    acts as a dilutant. A finding is not good news.

    The sweep runs INSIDE one test rather than across `parametrize` cases on
    purpose. Most combinations below behave correctly — adding LOW, HIGH or
    CRITICAL findings does lower the score — and under `xfail(strict=True)`
    each of those would be an XPASS, i.e. a hard failure, drowning the one
    real violation in noise. The property is "no combination raises the
    score", so it is asserted as one statement over the whole sweep and
    reports every violation it finds.

    The property is checked on the headline AND on every subscore, because the
    rescale-and-round path (`sum / (domains_assessed * 25) * 100`) can absorb
    a real subscore regression into an unchanged headline — the violation is
    then invisible at the only number the client reads, while still being
    present in the model.
    """
    base_result = compute_readiness_score(_multihost_evidence())
    violations = []

    for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        for added in (1, 10, 50, 100, 1000):
            worse = _multihost_evidence()
            worse["finding_severity_counts"][severity] += added
            worse["totals"]["findings"] += added
            worse_result = compute_readiness_score(worse)

            if worse_result["score"] > base_result["score"]:
                violations.append(
                    f"+{added} {severity}: headline {base_result['score']} -> "
                    f"{worse_result['score']}"
                )

            for domain, base_value in base_result["subscores"].items():
                worse_value = worse_result["subscores"][domain]
                if base_value is None or worse_value is None:
                    continue
                if worse_value > base_value:
                    violations.append(
                        f"+{added} {severity}: {domain} subscore "
                        f"{base_value}/25 -> {worse_value}/25"
                    )

    assert not violations, (
        "adding real findings RAISED the score in "
        f"{len(violations)} case(s) — discovering weakness improved the "
        "client's grade:\n  " + "\n  ".join(violations)
    )


# ---------------------------------------------------------------------------
# P2 — SCAN-CONFIG INVARIANCE. Identical infrastructure, different scan depth,
#      identical score. Looking harder is not a posture change.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("probe_count", [370, 390, 470, 870, 5000])
def test_p2a_score_is_independent_of_the_raw_probe_count(probe_count):
    """P2(a) — the 999.113 guarantee, held as a standing property.

    `totals.endpoints` is a probe count (hosts x ports attempted), including
    ports where nothing was found. Pre-999.113 it was the denominator of 34 of
    the 35 ratio sites, so widening `ports_tls` from 2 to 10 moved a real
    estate 89 -> 91 without touching the infrastructure.

    This PASSES today. It is kept here — alongside, not instead of,
    `tests/test_score_denominator_999_113.py`, which pins the same invariant
    from the regression side — so that P2's two halves read together: (a) is
    fixed, (b) below is not.
    """
    ev = _multihost_evidence()
    ev["totals"]["endpoints"] = probe_count

    assert _score(ev) == _score(_multihost_evidence()), (
        f"score moved when only totals.endpoints changed to {probe_count}. A "
        "ratio denominator is reading the probe count again — this is the "
        "999.113 defect returning."
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "999.115 / measured 2026-09-14: 999.113 removed the probe count as a "
        "denominator but the replacement, assessable_endpoint_count, ALSO "
        "grows with scan depth. Holding every weakness fixed and adding only "
        "healthy assessable endpoints: 38 -> 58 endpoints moves the score "
        "87 -> 89; -> 138 moves it to 91; -> 538 moves it to 93. The estate's "
        "absolute exposure (6 plaintext endpoints, 5 expired certs) is "
        "unchanged throughout. This is 999.115's 'no concept of CONSEQUENCE, "
        "only PREVALENCE' gap, measured."
    ),
)
@pytest.mark.parametrize("extra_healthy_endpoints", [20, 100, 500])
def test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints(
    extra_healthy_endpoints,
):
    """P2(b) — dilution survives 999.113 through the new denominator.

    999.113 replaced `totals.endpoints` with `assessable_endpoint_count`,
    which is strictly better: it excludes ADVISORY and CLOSED rows, so a scan
    that reached nothing can no longer fabricate a 100/100. But it is still a
    count that rises when you scan more ports on the same hosts.

    The honest statement of the defect: **the evidence model cannot
    distinguish "there is more infrastructure" from "we looked harder", and
    the score rewards both identically.** A purely proportional model has no
    way to say that six plaintext endpoints is the same amount of exposure
    whether they sit among 38 services or 538 — the attacker needs one.

    This is exactly the axis 999.115 candidate (C) — an absolute severity term
    extending `cap_band_for_severity`'s reasoning from the band to the number —
    exists to address. It will still fail under candidate (D) alone.
    """
    base = _multihost_evidence()
    wider = copy.deepcopy(base)
    wider["assessable_endpoint_count"] += extra_healthy_endpoints
    wider["totals"]["endpoints"] += extra_healthy_endpoints
    wider["protocol_counts"]["TLS"] += extra_healthy_endpoints

    base_score = _score(base)
    wider_score = _score(wider)

    assert wider_score <= base_score, (
        f"observing {extra_healthy_endpoints} additional healthy endpoints "
        f"RAISED the score from {base_score} to {wider_score} while every "
        "weakness count stayed identical. Scanning more ports improved the "
        "client's grade without improving the client's security."
    )


# ---------------------------------------------------------------------------
# P3 — SEVERITY COHERENCE. CRITICALs must cost more than MEDIUMs.
# ---------------------------------------------------------------------------

def test_p3_an_estate_with_criticals_scores_below_an_all_medium_estate():
    """P3 — severity must be ordered, holding the finding COUNT fixed.

    Two estates, 68 actionable findings each, identical in every other
    respect. One has 19 CRITICALs; the other has none. The CRITICAL estate
    must score lower.

    This PASSES today, in DIRECTION. The measured magnitude is the finding
    worth carrying forward to the calibration work: the gap is **2 points**
    (87 vs 89), and the all-MEDIUM estate — 52 MEDIUM findings, 5 expired
    certificates, 3 self-signed — earns the numeric band EXCELLENT. Ordering
    is necessary but nowhere near sufficient, which is the whole of 999.115's
    argument.

    Deliberately asserted as direction only: the operator owns the calibration
    ladder's middle rungs, and inventing a magnitude threshold here would be
    exactly the "tune to a number" move 999.113 D5 forbids.
    """
    with_criticals = _multihost_evidence()
    with_criticals["finding_severity_counts"] = {
        "CRITICAL": 19, "HIGH": 0, "MEDIUM": 33, "LOW": 16, "INFO": 330,
    }

    all_medium = _multihost_evidence()
    all_medium["finding_severity_counts"] = {
        "CRITICAL": 0, "HIGH": 0, "MEDIUM": 52, "LOW": 16, "INFO": 330,
    }

    critical_score = _score(with_criticals)
    medium_score = _score(all_medium)

    assert critical_score < medium_score, (
        f"an estate with 19 CRITICAL findings scored {critical_score} and an "
        f"otherwise-identical estate with 0 CRITICAL (52 MEDIUM instead) "
        f"scored {medium_score}. Severity does not order the score."
    )


# ---------------------------------------------------------------------------
# P4 — DYNAMIC RANGE. The operator's calibration bottom rung.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "999.115 / measured 2026-09-14: the multihost reference estate scores "
        "87 against an operator calibration ceiling of 30 (tightened from 40 "
        "on 2026-09-14 when R4's POOR target made 40 non-binding). THIS FAILURE IS THE "
        "DELIVERABLE — it converts 'most people will see 87 and say not bad' "
        "into a standing numeric statement of exactly how far off calibration "
        "the model is. 999.113 moved it 91 -> 87; the remaining 57 points are "
        "999.115's subject. Do NOT relax the ceiling to make this pass."
    ),
)
def test_p4_the_multihost_reference_estate_scores_below_the_calibration_ceiling():
    """P4 — dynamic range, against the one rung the operator has set.

    31 hosts built to be as bad as the product can detect: 5 CRITICAL and 14
    HIGH findings, 29% of certificates expired, 18% self-signed, plaintext
    HTTP in production. The operator's judgement is that such an estate must
    score **below 30** (set 2026-09-13 as 40, tightened 2026-09-14 when R4's
    POOR target made 40 non-binding) — it should alarm a client on
    sight, with no report-reading required.

    It scores 87.

    For grounding, from 999.115's measurements: a PERFECT estate scores 100,
    and a MAXIMALLY BROKEN one — every ratio driven to 1.0, which is to say
    every endpoint plaintext and every certificate expired — scores 19. The
    floor is reachable in principle; reaching it requires infrastructure that
    cannot exist. The model reserves roughly 80% of its scale for estates no
    consultant will ever scan.

    The root cause is the transfer function, not the range: `penalty = ratio x
    weight` is LINEAR, so 30%-of-certificates-expired is treated as exactly
    six times worse than 5%. No consultant reads it that way — 5% is hygiene
    drift, 30% is an organisation that has lost control of its PKI. Alarm is
    steeply non-linear in prevalence; the model draws a straight line through
    the origin.
    """
    score = _score(_multihost_evidence())

    assert score < MULTIHOST_CALIBRATION_CEILING, (
        f"the 31-host deliberately-vulnerable reference estate scored {score}, "
        f"not below the operator's calibration ceiling of "
        f"{MULTIHOST_CALIBRATION_CEILING}. Off by "
        f"{score - MULTIHOST_CALIBRATION_CEILING} points."
    )


# PROMOTED to a standing green gate 2026-09-14 by the P8 fix.
# Was: R5 scored 87 (numeric band EXCELLENT) — only the CRITICAL band cap hid it.
# Resolved because R5 fell 87 -> 81 once undetermined certificate key types
# stopped scoring as best-case. NOTE ON ROBUSTNESS: R5's recorded fixture has
# undetermined key types, so it takes the new assessment-gap penalty; a REAL
# scan of that estate would determine them and take the RSA-only penalty
# instead. Both are priced 8.0 by derivation, so R5 lands at 81 either way —
# the outcome does not depend on which path applies.
def test_p4b_a_catastrophic_estate_does_not_land_in_the_top_numeric_band():
    """P4(b) — the number must not contradict the label.

    `cap_band_for_severity()` floors the emitted band at FAIR whenever a
    CRITICAL is open. That cap is correct and load-bearing, but it is
    compensation, not calibration: it changes the word while leaving the digits
    saying EXCELLENT. 999.115 records why that is not a fix — "a 0-100 scale
    arrives pre-loaded with school-grade semantics that no band label or
    findings table overrides".

    A model whose band cap is the only thing preventing an incoherent verdict
    is a model whose number is not carrying the meaning.
    """
    score = _score(_multihost_evidence())
    numeric_band = band_for_score(score)

    assert numeric_band != "EXCELLENT", (
        f"the 31-host deliberately-vulnerable reference estate scored {score}, "
        f"whose NUMERIC band is {numeric_band} (EXCELLENT threshold is "
        f"{BAND_THRESHOLDS['EXCELLENT']}). Only the CRITICAL-severity band cap "
        "stops the client being shown the top grade for a catastrophic estate."
    )


# ---------------------------------------------------------------------------
# P5 — EXPLANATION FIDELITY. The drivers shown to the client are the real ones.
# ---------------------------------------------------------------------------

def test_p5a_the_dominant_weakness_is_the_top_driver():
    """P5(a) — the largest penalty must lead the client-facing driver list.

    Constructed so the answer is known by design rather than by
    re-implementing the scorer: an estate whose ONLY weakness is 100%
    plaintext HTTP (weight 18.0, the largest single coefficient in
    `SCORE_WEIGHTS`). Whatever else appears, "Plaintext HTTP exposure" must be
    the first driver.

    This PASSES today. It is the half of P5 that guards against the drivers
    list drifting away from the arithmetic — the remediation roadmap the
    client is sold is built from exactly these strings.
    """
    ev = _multihost_evidence()
    ev["plaintext_http_count"] = ev["assessable_endpoint_count"]
    ev["http_on_tls_port_count"] = 0
    ev["protocol_counts"]["UNKNOWN"] = 0
    ev["certificate_observations"] = {
        "certs_observed": 17, "expired_count": 0,
        "expiring_count": 0, "self_signed_count": 0,
    }
    ev["finding_severity_counts"] = {
        "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 330,
    }

    drivers = compute_readiness_score(ev)["drivers"]

    assert drivers, "an estate with a total plaintext-HTTP failure produced no drivers at all"
    assert drivers[0]["reason"] == "Plaintext HTTP exposure", (
        "the dominant weakness is not the leading driver. Estate is 100% "
        f"plaintext HTTP; drivers were {[d['reason'] for d in drivers]}"
    )


def test_p5b_drivers_are_ordered_by_magnitude_and_never_zero():
    """P5(b) — internal consistency of the client-facing explanation.

    Two invariants that must hold for the driver list to be readable as "the
    top five reasons": it is sorted by descending magnitude, and no entry is a
    rounded-to-zero non-reason. Both PASS today; they guard the presentation
    contract every report surface depends on.
    """
    drivers = compute_readiness_score(_multihost_evidence())["drivers"]

    assert drivers, "the multihost reference estate produced no drivers"
    magnitudes = [abs(d["points"]) for d in drivers]
    assert magnitudes == sorted(magnitudes, reverse=True), (
        f"drivers are not ordered by magnitude: {drivers}"
    )
    assert all(d["points"] != 0 for d in drivers), (
        f"a zero-point driver is being shown to the client: {drivers}"
    )


# PROMOTED to a standing green gate 2026-09-14 when the fix landed.
# Was a LATENT defect: compute_readiness_score concatenated dar_/motion_
# drivers into the client-facing list without consulting the assessed
# predicate, so a domain excluded from the headline could supply its top
# driver. Fixed by carrying each domain's drivers inside `category_table`
# alongside its score and assessed flag, so the subscore and the driver
# list read the same tuple and cannot disagree about what was assessed.
# It was unreachable from the live producer only through an incidental
# coupling in evidence.py; that coincidence is no longer load-bearing.
def test_p5c_no_driver_is_attributed_to_a_domain_excluded_from_the_headline():
    """P5(c) — the explanation must not cite evidence the score disowned.

    When a domain is not assessed, its subscore is reported as `None` and it
    is excluded from the rescale denominator entirely — the headline makes no
    claim about it. The driver list makes no such check, so the client can be
    shown "Database plaintext connections" as the single largest reason for a
    score that explicitly did not assess data-at-rest.

    Filed as a latent defect rather than a live one, with the reachability
    analysis in the xfail reason above. It is recorded here rather than in
    prose because the thing standing between this and a real client-facing
    incoherence is an *incidental* coupling in a different module, which no
    test currently pins — precisely the shape of defect this project has been
    bitten by five times (see CLAUDE.md's run-time-source-scan lesson).
    """
    ev = _multihost_evidence()
    for protocol in ("POSTGRESQL", "S3", "KUBERNETES", "VAULT"):
        ev["protocol_counts"].pop(protocol, None)
    ev["dar_db_plaintext_count"] = 30

    result = compute_readiness_score(ev)
    assert result["subscores"]["data_at_rest"] is None, (
        "fixture failed to produce an unassessed data_at_rest domain — the "
        "instrument is broken, not the subject"
    )

    dar_driver_reasons = {
        "Database plaintext connections",
        "Database weak SSL configuration",
        "Object storage unencrypted",
        "Object storage platform-managed keys",
        "Kubernetes etcd unencrypted",
        "Kubernetes etcd encryption inaccessible",
        "Vault weak crypto posture",
    }
    leaked = [d for d in result["drivers"] if d["reason"] in dar_driver_reasons]

    assert not leaked, (
        f"data_at_rest is excluded from the headline (subscore None) yet "
        f"supplied {len(leaked)} driver(s) to the client-facing explanation: "
        f"{[d['reason'] for d in leaked]}. The score disowns this domain; the "
        "narrative cites it."
    )


# ---------------------------------------------------------------------------
# P6 — SENSITIVITY. A material posture change must move the number materially.
# ---------------------------------------------------------------------------

# PROMOTED to a standing green gate 2026-09-14 by the P8 fix.
# Was: full remediation moved 87 -> 100 without changing band.
# Resolved because R5 fell 87 -> 81 once undetermined certificate key types
# stopped scoring as best-case. NOTE ON ROBUSTNESS: R5's recorded fixture has
# undetermined key types, so it takes the new assessment-gap penalty; a REAL
# scan of that estate would determine them and take the RSA-only penalty
# instead. Both are priced 8.0 by derivation, so R5 lands at 81 either way —
# the outcome does not depend on which path applies.
def test_p6a_full_remediation_changes_the_numeric_band():
    """P6(a) — the engagement's whole value must be visible in the verdict.

    The product sells a prioritised remediation roadmap. Its promise is that
    doing the work changes the answer. Take the reference estate, fix every
    weakness the scanner can detect, and the band the client is shown before
    and after is the same word.

    Band boundaries are the coarsest possible test of sensitivity — not "did
    the number move" but "did it move enough to change the sentence". Using
    `BAND_THRESHOLDS` rather than an invented constant keeps this property
    honest: it asks the product's own published bands whether a year of
    security work is legible.
    """
    before = _score(_multihost_evidence())
    after = _score(_remediated_multihost_evidence())

    assert band_for_score(before) != band_for_score(after), (
        f"a complete remediation of every detectable weakness moved the score "
        f"{before} -> {after}, leaving the numeric band unchanged at "
        f"{band_for_score(before)} (thresholds: {dict(BAND_THRESHOLDS)}). The "
        "client cannot see the engagement in the number."
    )


# PROMOTED to a standing green gate 2026-09-14 by the P8 fix.
# Was: the full-remediation span was 13 points, under the narrowest band width of 15.
# Resolved because R5 fell 87 -> 81 once undetermined certificate key types
# stopped scoring as best-case. NOTE ON ROBUSTNESS: R5's recorded fixture has
# undetermined key types, so it takes the new assessment-gap penalty; a REAL
# scan of that estate would determine them and take the RSA-only penalty
# instead. Both are priced 8.0 by derivation, so R5 lands at 81 either way —
# the outcome does not depend on which path applies.
def test_p6b_the_full_remediation_span_is_at_least_one_band_wide():
    """P6(b) — the same property as a number, for tracking progress.

    P6(a) is binary and will flip the moment any candidate model spreads the
    scale at all. This one is the continuous version: it reports the actual
    span, so successive attempts at 999.115's candidates (A/B/C/D) can be
    compared against each other rather than just against pass/fail.

    The threshold is derived from `BAND_THRESHOLDS`, not chosen: the narrowest
    gap between adjacent published bands. A remediation programme worth less
    than the narrowest band the product itself defines is not expressible in
    the product's own vocabulary.
    """
    thresholds = sorted(BAND_THRESHOLDS.values(), reverse=True)
    narrowest_band_width = min(
        thresholds[i] - thresholds[i + 1] for i in range(len(thresholds) - 1)
    )

    before = _score(_multihost_evidence())
    after = _score(_remediated_multihost_evidence())
    span = after - before

    assert span >= narrowest_band_width, (
        f"remediating every detectable weakness on a deliberately-vulnerable "
        f"31-host estate spans only {span} points ({before} -> {after}), less "
        f"than the narrowest published band width of {narrowest_band_width}. "
        f"Band thresholds: {dict(BAND_THRESHOLDS)}."
    )


# ---------------------------------------------------------------------------
# P7 — QUANTUM READINESS MUST REGISTER.
#
# Operator calibration decision, 2026-09-14: "no PQC, no 100". Recorded here
# rather than only in a planning document because this file is the ladder, and
# a rung that lives in prose is a rung that drifts — this project has been
# bitten five separate times by exactly that (see CLAUDE.md).
#
# This is a CALIBRATION input, not a model shape. It says what the top of the
# scale MEANS; it does not say which of 999.115's candidates (A/B/C/D) should
# deliver it. "Do not begin by picking a shape" still holds.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "999.115 / measured 2026-09-14: a hygiene-perfect estate with ZERO "
        "post-quantum readiness scores 100 on a Quantum Infrastructure "
        "Readiness Kit. Operator decision 2026-09-14: 'no PQC, no 100'. "
        "Remove this marker when the model earns the top of its own scale."
    ),
)
def test_p7a_a_zero_pqc_estate_does_not_reach_the_top_of_the_scale():
    """P7(a) — 100 must mean quantum-ready, on a quantum-readiness product.

    The estate under test is immaculate by every classical measure: TLS 1.3,
    ECDSA certificates, zero expired or self-signed, no plaintext, no findings
    above INFO. It also has no post-quantum key exchange anywhere — it is
    exactly as exposed to harvest-now-decrypt-later as it was before the
    engagement began.

    It scores 100.

    The product's name is the argument. A client who is shown a perfect score
    by a tool called a Quantum Infrastructure Readiness Kit has been told
    their post-quantum posture is complete, and it has not begun.
    """
    score = _score(_remediated_multihost_evidence())

    assert score < 100, (
        f"an estate with zero PQC-hybrid key exchange scored {score}/100 on a "
        "quantum-readiness assessment. The top of the scale is reachable "
        "without doing any post-quantum work at all."
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "999.115 / measured 2026-09-14: adopting hybrid X25519MLKEM768 on "
        "EVERY endpoint moves the score by 0 points (100 -> 100). The "
        "agility_pqc_hybrid_bonus of 8.0 exists and is computed, but "
        "agility_signals is already at its 25/25 ceiling, so "
        "_apply_weighted_impacts' _clamp(total, 0.0, 25.0) absorbs it "
        "entirely. Same saturation mechanism as P4's unreachable floor, "
        "pointed at the ceiling."
    ),
)
def test_p7b_adopting_pqc_improves_the_score():
    """P7(b) — the mechanism under P7(a), and P1's positive mirror.

    P1 asserts that discovering a weakness must never RAISE the score. This
    asserts the converse: performing a real, expensive, product-recommended
    security improvement must LOWER nothing and must move the number.

    Two estates, identical in every field except that one has hybrid
    X25519MLKEM768 observed on every assessable endpoint. `SCORE_WEIGHTS`
    prices that at `agility_pqc_hybrid_bonus = 8.0` — the joint-largest bonus
    in the table — and the delta is 0, because the subscore it feeds is
    already clamped at its 25-point ceiling.

    This is worth separating from P7(a) because the two fail for different
    reasons and will be fixed by different changes: P7(a) is a statement about
    what 100 should require, P7(b) is a statement about a weight that is
    computed and then discarded. A model change could satisfy one and not the
    other, and the suite should say which.
    """
    without_pqc = _score(_remediated_multihost_evidence())
    with_pqc = _score(_pqc_ready_estate())

    assert with_pqc > without_pqc, (
        f"adopting hybrid PQC key exchange on every endpoint moved the score "
        f"{without_pqc} -> {with_pqc} (delta {with_pqc - without_pqc}). The "
        "agility_pqc_hybrid_bonus weight of 8.0 is computed and then absorbed "
        "by the 25-point subscore clamp — the product cannot reward the "
        "single transition it exists to recommend."
    )


# ---------------------------------------------------------------------------
# THE LADDER ITSELF — R1..R5 against the operator's blind-set bands.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "rung_name,builder,target_band",
    [
        pytest.param(*CALIBRATION_LADDER[0], id="R1-pristine-EXCELLENT"),
        pytest.param(
            *CALIBRATION_LADDER[1], id="R2-well-run-GOOD",
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "999.115 / measured 2026-09-14: R2 scores 95, band "
                    "EXCELLENT, against a target band of GOOD (70-84). A "
                    "quantum-blind estate reads as top-of-scale."
                ),
            ),
        ),
        pytest.param(
            *CALIBRATION_LADDER[2], id="R3-typical-FAIR",
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "999.115 / measured 2026-09-14: R3 scores 91, band "
                    "EXCELLENT, against a target band of FAIR (35-54). Off by "
                    "37 points and three whole bands."
                ),
            ),
        ),
        pytest.param(
            *CALIBRATION_LADDER[3], id="R4-neglected-POOR",
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "999.115 / measured 2026-09-14: R4 scores 85, band "
                    "EXCELLENT, against a target band of POOR (0-34). An "
                    "estate with 8 expired certificates, 5 plaintext services "
                    "and 2 CRITICAL findings earns the product's top grade."
                ),
            ),
        ),
    ],
)
def test_ladder_rung_lands_in_its_target_band(rung_name, builder, target_band):
    """Each reference estate must score inside the band the operator assigned.

    The bands were supplied BLIND on 2026-09-14 — described in infrastructure
    terms (certificates, protocols, findings) with no score shown — so they
    measure the model rather than describing it. That ordering is the whole
    reason these targets mean anything, and it is why the failures below are
    evidence rather than opinion.

    Only R1 passes. The other three are not near-misses: R3 is three bands and
    37 points from target, and R4 — eight expired certificates, five plaintext
    services, widespread legacy TLS, two CRITICAL findings — earns EXCELLENT.
    """
    low, high = _band_range(target_band)
    score = _score(builder())

    assert low <= score <= high, (
        f"{rung_name} scored {score} (band {band_for_score(score)}), outside "
        f"its operator-assigned target band {target_band} ({low}-{high})."
    )


# PROMOTED to a standing green gate 2026-09-14 by the P8 fix.
# Was: R4 (85) scored BELOW R5 (87) — the strictly worse estate scored higher.
# Resolved because R5 fell 87 -> 81 once undetermined certificate key types
# stopped scoring as best-case. NOTE ON ROBUSTNESS: R5's recorded fixture has
# undetermined key types, so it takes the new assessment-gap penalty; a REAL
# scan of that estate would determine them and take the RSA-only penalty
# instead. Both are priced 8.0 by derivation, so R5 lands at 81 either way —
# the outcome does not depend on which path applies.
def test_ladder_is_monotonic():
    """Worse infrastructure must never score higher than better infrastructure.

    This is the property that makes a ladder a ladder. Band targets can all be
    wrong together and still leave a usable *ordering*; an ordering violation
    means the score is not measuring estate quality along a single axis at all.

    Asserted across all five rungs rather than the four that share a shape,
    because R5 is the rung with real recorded measurements behind it and
    excluding it would make the property easier by construction.
    """
    ladder = [(name, _score(builder())) for name, builder, _ in CALIBRATION_LADDER]
    ladder.append(("R5 multihost", _score(_multihost_evidence())))

    inversions = [
        f"{ladder[i][0]}={ladder[i][1]} < {ladder[i + 1][0]}={ladder[i + 1][1]}"
        for i in range(len(ladder) - 1)
        if ladder[i][1] < ladder[i + 1][1]
    ]

    assert not inversions, (
        "the calibration ladder is not monotonic — worse infrastructure scored "
        "higher than better infrastructure in "
        f"{len(inversions)} place(s):\n  " + "\n  ".join(inversions)
        + f"\n  full ladder: {ladder}"
    )


# PROMOTED to a standing green gate 2026-09-14 by the P8 fix.
# Was: all five rungs landed in the single band EXCELLENT, spanning 15 points.
# Resolved because R5 fell 87 -> 81 once undetermined certificate key types
# stopped scoring as best-case. NOTE ON ROBUSTNESS: R5's recorded fixture has
# undetermined key types, so it takes the new assessment-gap penalty; a REAL
# scan of that estate would determine them and take the RSA-only penalty
# instead. Both are priced 8.0 by derivation, so R5 lands at 81 either way —
# the outcome does not depend on which path applies.
def test_ladder_spans_more_than_one_band():
    """The ladder must distinguish its own rungs by band, not just by digits.

    A score whose entire realistic range fits inside one band has no
    discriminating power in the only vocabulary the client is given. The
    product can still print different numbers, but "EXCELLENT" is what gets
    read aloud, put on a slide, and remembered.

    Deliberately weak as stated — it asks only for MORE THAN ONE band across
    the full quality range, not for the five the ladder was built with. A
    property this easy failing is the finding.
    """
    scores = [_score(builder()) for _, builder, _ in CALIBRATION_LADDER]
    scores.append(_score(_multihost_evidence()))
    bands = {band_for_score(s) for s in scores}

    assert len(bands) > 1, (
        f"all {len(scores)} ladder rungs — from a pristine PQC-ready estate to "
        f"a purpose-built catastrophic one — land in the single band "
        f"{bands.pop()!r}. Scores: {scores} (spread {max(scores) - min(scores)} "
        "points across the entire range of infrastructure quality)."
    )


# ---------------------------------------------------------------------------
# P8 — ABSENT EVIDENCE MUST NOT OUTSCORE HONEST BAD EVIDENCE.
#
# Found by decomposing the R4/R5 ladder inversion above, not by inspection.
# ---------------------------------------------------------------------------

# PROMOTED to a standing green gate 2026-09-14 — the xfail(strict=True) marker
# was removed when the fix landed, which is the workflow this file's header
# describes: strict mode turned the fix into an XPASS failure and forced this
# edit rather than letting the improvement land unremarked.
#
# Was: "an estate whose certificate key types are UNREPORTED scores 100 —
# identical to fully-modern ECDSA, and 5 points ABOVE the same estate honestly
# reporting RSA-only (95)". Fixed by the `elif cert_denom > 0` arm in
# compute_readiness_score's key-type branch, priced at
# agility_unverified_key_type_penalty.
def test_p8_unknown_key_types_do_not_outscore_honest_rsa_reporting():
    """P8 — the 999.95 defect class, third recurrence.

    999.95 was "domains with ZERO evidence score 25/25", closed by Phase 188
    SCORE-06 with per-domain assessed predicates. 999.113 was the same shape
    one level down: domains with REAL evidence scoring 25/25 because their
    ratios divided by a probe count. This is the same shape one level down
    again — a single SIGNAL, rather than a whole domain, where absence is
    scored as though it were the best case.

    The consequence is an incentive, which is worse than an inaccuracy: a scan
    that fails to determine key types produces a better client-facing number
    than one that succeeds and finds RSA. Nothing in the product tells the
    reader which of the two they are looking at.

    `_endpoints_assessed` and friends exist precisely to distinguish "assessed
    and fine" from "not assessed". No equivalent exists at signal granularity.
    """
    honest_rsa = _base_estate()
    honest_rsa["cert_key_type_counts"] = {"RSA": 40, "ECDSA": 0}

    unknown_keys = _base_estate()
    unknown_keys["cert_key_type_counts"] = {"RSA": 0, "ECDSA": 0}

    honest_score = _score(honest_rsa)
    unknown_score = _score(unknown_keys)

    assert unknown_score <= honest_score, (
        f"an estate with UNREPORTED certificate key types scored "
        f"{unknown_score}, above the same estate honestly reporting RSA-only "
        f"at {honest_score}. Failing to determine the key type is worth "
        f"{unknown_score - honest_score} points more than determining it and "
        "finding RSA."
    )
