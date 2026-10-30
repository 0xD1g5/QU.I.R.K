"""PQC-03: agility bonus for pqc_hybrid_endpoint_count.

Tests:
  1. Uplift: a scan with pqc_hybrid_endpoint_count=1 yields a strictly higher
     agility subscore than an equivalent scan with pqc_hybrid_endpoint_count=0.
  2. Clamp: even with pqc_hybrid_endpoint_count set and no other penalties, the
     agility subscore never exceeds 25 (Phase 88 orthogonal /25 constraint).
  3. Orthogonality: the five non-agility subscores are identical between the
     count=1 and count=0 evidence inputs.
  4. Presence: the bonus applies as a binary signal (count >= 1), not zero when
     the counter is missing/None/garbage.
"""
from quirk.intelligence.scoring import compute_readiness_score


def _base_evidence(**overrides):
    """Evidence dict with a moderate agility penalty to leave room for the PQC bonus uplift.

    The headroom must come from a penalty that actually lands on
    `agility_signals`, or the subscore saturates at its 25-point clamp and the
    +8 bonus becomes invisible — an uplift assertion against two saturated 25s
    is `25 > 25`, which is what this fixture produced until 999.115 repaired it.

    999.115 — the headroom source CHANGED. It used to be 2 HIGH findings out of
    4 total, driving `agility_high_impact_ratio` to 0.5 for a -7 penalty. That
    term was REMOVED by 999.115 (`523dd818`): as a prevalence measure it diluted
    as its denominator grew and was the sole remaining cause of P1, and
    `_consequence_ceiling()` now carries the high-impact signal absolutely
    instead. With it gone the fixture's only agility penalty vanished, agility
    returned to a clean 25 for BOTH arms, and both uplift tests broke.

    The headroom now comes from `agility_unknown_ratio` (weight 6.0): 2 UNKNOWN
    services out of 4 assessable endpoints = 0.5, bent by the prevalence curve,
    landing agility at 21 and leaving the +8.0 bonus visibly observable (21 ->
    25). `UNKNOWN` also feeds `modern_tls`, which is harmless here and does not
    weaken TestPqcAgilityOrthogonality: both arms carry the SAME unknown count,
    so every non-agility subscore stays identical between them, which is exactly
    what that class asserts.

    The finding_severity_counts entry is kept — it no longer creates the
    headroom, but removing it would change what the consequence ceiling does to
    these fixtures' headline scores, and these tests are about the subscore.
    """
    ev = {
        "totals": {"endpoints": 4, "findings": 4},
        # 999.115: 2 UNKNOWN of 4 assessable endpoints is the agility headroom.
        "protocol_counts": {"UNKNOWN": 2},
        "certificate_observations": {},
        "cert_key_type_counts": {},
        "scan_error": {"rate": 0.0},
        "finding_severity_counts": {"HIGH": 2},
    }
    ev.update(overrides)
    return ev


class TestPqcAgilityUplift:
    """Requirement: PQC-hybrid scan scores strictly higher on agility than classical-only."""

    def test_pqc_hybrid_beats_classical_agility(self):
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert pqc["subscores"]["agility_signals"] > classical["subscores"]["agility_signals"], (
            f"PQC-hybrid agility ({pqc['subscores']['agility_signals']}) must exceed "
            f"classical agility ({classical['subscores']['agility_signals']})"
        )

    def test_pqc_hybrid_multiple_endpoints_still_uplifts(self):
        """Multiple PQC endpoints: still an uplift (not a diminishing-returns regression)."""
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=5))
        assert pqc["subscores"]["agility_signals"] > classical["subscores"]["agility_signals"]


class TestPqcAgilityClamp:
    """Requirement: agility subscore is capped at 25 regardless of bonus."""

    def test_agility_never_exceeds_25_with_pqc(self):
        result = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert result["subscores"]["agility_signals"] <= 25, (
            f"Agility subscore {result['subscores']['agility_signals']} exceeds /25 pillar cap"
        )

    def test_agility_never_exceeds_25_with_ecdsa_and_pqc(self):
        """Both ECDSA bonus and PQC bonus active — still clamped at 25."""
        ev = _base_evidence(
            pqc_hybrid_endpoint_count=1,
            cert_key_type_counts={"ECDSA": 1},
        )
        result = compute_readiness_score(ev)
        assert result["subscores"]["agility_signals"] <= 25

    def test_agility_never_exceeds_25_strict_profile(self):
        """Strict profile multiplies agility weights up — clamp must still hold."""
        result = compute_readiness_score(
            _base_evidence(pqc_hybrid_endpoint_count=1),
            profile="strict",
        )
        assert result["subscores"]["agility_signals"] <= 25, (
            f"Strict-profile agility {result['subscores']['agility_signals']} exceeds 25"
        )


class TestPqcAgilityOrthogonality:
    """Requirement: PQC bonus must NOT alter the five non-agility subscores."""

    def _non_agility_subscores(self, result):
        s = result["subscores"]
        return {
            "hygiene": s["hygiene"],
            "modern_tls": s["modern_tls"],
            "identity_trust": s["identity_trust"],
            "data_at_rest": s["data_at_rest"],
            "data_in_motion": s["data_in_motion"],
        }

    def test_non_agility_subscores_unchanged(self):
        classical = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        pqc = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=1))
        assert self._non_agility_subscores(classical) == self._non_agility_subscores(pqc), (
            "PQC bonus leaked into non-agility subscores"
        )

    def test_non_agility_unchanged_with_penalties(self):
        """Same check when there are other findings active."""
        ev0 = _base_evidence(
            pqc_hybrid_endpoint_count=0,
            finding_severity_counts={"HIGH": 2},
            totals={"endpoints": 4, "findings": 4},
        )
        ev1 = dict(ev0)
        ev1["pqc_hybrid_endpoint_count"] = 1
        classical = compute_readiness_score(ev0)
        pqc = compute_readiness_score(ev1)
        assert self._non_agility_subscores(classical) == self._non_agility_subscores(pqc)


class TestPqcPresenceBonus:
    """Requirement: bonus is a binary presence signal; missing/bad values → no bonus."""

    def test_zero_count_no_bonus(self):
        """pqc_hybrid_endpoint_count=0 must not trigger the bonus."""
        zero = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        missing = compute_readiness_score(_base_evidence())
        # Both should produce the same agility score (no bonus from PQC)
        assert zero["subscores"]["agility_signals"] == missing["subscores"]["agility_signals"]

    def test_garbage_count_no_crash(self):
        """Non-integer pqc_hybrid_endpoint_count must not crash and must not add bonus."""
        baseline = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        for garbage in (None, "abc", [], {}, -1):
            result = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=garbage))
            assert result["subscores"]["agility_signals"] == baseline["subscores"]["agility_signals"], (
                f"garbage value {garbage!r} produced unexpected agility score"
            )

    def test_negative_count_no_bonus(self):
        """Negative counts must coerce to 0 (max(0, ...) guard)."""
        baseline = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=0))
        negative = compute_readiness_score(_base_evidence(pqc_hybrid_endpoint_count=-5))
        assert baseline["subscores"]["agility_signals"] == negative["subscores"]["agility_signals"]


# ---- Phase 234 D-04 / O-2 / O-4: the classical key rule and the single PQC credit ----

def _agility(ev):
    return compute_readiness_score(ev)["subscores"]["agility_signals"]


def test_ecdsa_cert_keys_take_the_classical_penalty():
    """O-2: ECDSA (and EdDSA) certificate keys are quantum-vulnerable, exactly
    like RSA. An ECDSA-only estate scores the same agility as an RSA-only one:
    classical keys are never a positive signal (D-04 removed the ECDSA +4)."""
    certs = {"certs_observed": 3}
    ecdsa = _base_evidence(
        certificate_observations=certs,
        cert_key_type_counts={"RSA": 0, "ECDSA": 3},
    )
    rsa = _base_evidence(
        certificate_observations=certs,
        cert_key_type_counts={"RSA": 3, "ECDSA": 0},
    )
    assert _agility(ecdsa) == _agility(rsa), (
        f"ECDSA-only agility {_agility(ecdsa)} != RSA-only agility "
        f"{_agility(rsa)}: a classical key type is being scored as a signal"
    )


def test_pqc_cert_key_earns_single_credit():
    """O-4 / D-04: a PQC certificate key earns the PQC credit even with no
    PQC key exchange observed, so it scores strictly above the same estate
    whose certificates report no PQC key."""
    certs = {"certs_observed": 2}
    pqc = _base_evidence(
        certificate_observations=certs,
        cert_key_type_counts={"RSA": 0, "ECDSA": 0, "PQC": 2},
        pqc_hybrid_endpoint_count=0,
    )
    none = _base_evidence(
        certificate_observations=certs,
        cert_key_type_counts={"RSA": 0, "ECDSA": 0, "PQC": 0},
        pqc_hybrid_endpoint_count=0,
    )
    assert _agility(pqc) > _agility(none), (
        f"PQC certificate keys gave agility {_agility(pqc)}, not above "
        f"{_agility(none)} without them"
    )


def test_pqc_cert_and_pqc_kex_credit_once_not_twice():
    """D-04: a PQC certificate key and a PQC/hybrid key exchange share ONE
    credit (+8), never +16.

    The fixture leaves room for +16 to be visible: 40 UNKNOWN services and
    40 weak bearer-token algorithms (each saturating its -6 term) plus an RSA
    certificate (the classical -8, present in every arm) put agility at 5
    before any credit, so a doubled credit (21) would score above the single
    one (13) rather than clamping into it.
    """
    common = dict(
        assessable_endpoint_count=40,
        protocol_counts={"UNKNOWN": 40},
        bearer_token_weak_alg_count=40,
        certificate_observations={"certs_observed": 2},
        pqc_hybrid_endpoint_count=1,
    )
    kex_only = _base_evidence(
        cert_key_type_counts={"RSA": 1, "ECDSA": 0, "PQC": 0}, **common,
    )
    kex_and_cert = _base_evidence(
        cert_key_type_counts={"RSA": 1, "ECDSA": 0, "PQC": 1}, **common,
    )
    no_credit = _base_evidence(
        cert_key_type_counts={"RSA": 1, "ECDSA": 0, "PQC": 0},
        **{**common, "pqc_hybrid_endpoint_count": 0},
    )
    # Headroom: the single credit is visible and a second +8 would not clamp.
    assert _agility(kex_only) > _agility(no_credit)
    assert _agility(kex_only) + 8 <= 25, (
        f"fixture has no headroom: kex-only agility {_agility(kex_only)}"
    )
    assert _agility(kex_and_cert) == _agility(kex_only), (
        f"PQC cert + PQC KEX gave agility {_agility(kex_and_cert)}, "
        f"KEX alone {_agility(kex_only)}: the credit was counted twice"
    )


def test_pqc_cert_does_not_lift_pqc_readiness_ceiling():
    """D-04: the 84 "no PQC, no 100" ceiling stays keyed on post-quantum KEY
    EXCHANGE only. A PQC certificate key alone does not lift it."""
    ev = _base_evidence(
        certificate_observations={"certs_observed": 1},
        cert_key_type_counts={"RSA": 0, "ECDSA": 0, "PQC": 1},
        pqc_hybrid_endpoint_count=0,
        # No HIGH findings, so the consequence ceiling cannot win instead.
        finding_severity_counts={},
    )
    result = compute_readiness_score(ev)
    reason = result["rating_cap_reason"] or ""
    assert "no post-quantum key exchange observed" in reason, (
        f"rating_cap_reason {reason!r} does not name the PQC-readiness ceiling"
    )


# ---- Phase 234 code review WR-02 / D-29: undetermined keys and one PQC certificate ----

def _cert_estate(key_alg_for_39):
    """40 TLS certificate rows plus 40 UNKNOWN services, through the row layer.

    39 certificates carry ``key_alg_for_39`` (``"RSA"`` or ``None`` for a key
    type the scanner did not determine); the 40th is an ML-DSA-65 certificate
    (the O-4 PQC bucket). The 40 UNKNOWN services saturate the -6 unknown term
    in both arms, so agility sits below 25 and a hidden -8 cannot be absorbed
    by the clamp.
    """
    from datetime import datetime, timedelta
    from types import SimpleNamespace

    from quirk.intelligence.evidence import build_evidence_summary

    ref = datetime(2026, 10, 1, 12, 0, 0)
    fields = (
        "host", "port", "protocol", "scanned_at", "tls_version",
        "tls_supported_versions", "cipher_suite", "cert_subject", "cert_issuer",
        "cert_pubkey_alg", "cert_pubkey_size", "cert_sig_alg", "cert_not_before",
        "cert_not_after", "scan_error", "tls_blocker_reason", "service_detail",
        "severity",
    )

    def row(**kw):
        base = {name: None for name in fields}
        base["scanned_at"] = ref
        base.update(kw)
        return SimpleNamespace(**base)

    rows = []
    for i in range(40):
        rows.append(row(
            host=f"c{i}.d29.example", port=443, protocol="TLS",
            tls_version="TLSv1.3", tls_supported_versions="TLSv1.2,TLSv1.3",
            cipher_suite="TLS_AES_256_GCM_SHA384",
            cert_subject=f"CN=c{i}", cert_issuer="CN=D29 CA",
            cert_not_before=ref - timedelta(days=30),
            cert_not_after=datetime(2099, 1, 1),
            cert_pubkey_alg="ML-DSA-65" if i == 39 else key_alg_for_39,
        ))
    rows += [row(host=f"u{i}.d29.example", port=9000 + i, protocol="UNKNOWN")
             for i in range(40)]
    return build_evidence_summary(rows, [], reference_utc=ref)


def test_undetermined_keys_with_one_pqc_cert_never_beat_classical_keys():
    """D-29: not looking at certificate keys must never score better than
    finding classical keys, even when one certificate is PQC.

    WR-02 reproduction: under the 234 rule ``elif C > 0 and PQC == 0`` one
    PQC certificate switched the "key types undetermined" -8 off, so 39
    undetermined + 1 PQC outscored 39 RSA + 1 PQC (999.115 P8 regression).
    """
    rsa = _cert_estate("RSA")
    undetermined = _cert_estate(None)
    # Non-vacuity: the two arms differ only in the 39 key types.
    assert rsa["cert_key_type_counts"] == {"RSA": 39, "ECDSA": 0, "PQC": 1}
    assert undetermined["cert_key_type_counts"] == {"RSA": 0, "ECDSA": 0, "PQC": 1}
    assert (rsa["certificate_observations"]["certs_observed"]
            == undetermined["certificate_observations"]["certs_observed"] == 40)
    assert _agility(rsa) < 25, f"no agility headroom: RSA arm {_agility(rsa)}"

    r_rsa = compute_readiness_score(rsa)
    r_und = compute_readiness_score(undetermined)
    assert _agility(undetermined) <= _agility(rsa), (
        f"39 undetermined + 1 PQC agility {_agility(undetermined)} > 39 RSA + "
        f"1 PQC agility {_agility(rsa)}: not looking at keys paid"
    )
    assert r_und["score"] <= r_rsa["score"], (
        f"39 undetermined + 1 PQC scored {r_und['score']} > 39 RSA + 1 PQC "
        f"{r_rsa['score']}"
    )
    reasons = [d.get("reason", "") for d in r_und.get("drivers", [])]
    assert "Certificate key types undetermined" in reasons, reasons
