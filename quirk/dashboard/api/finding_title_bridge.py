"""Phase 202 (D-06): dashboard-title -> CLI-canonical-title translation.

**Why two vocabularies exist.** `quirk/dashboard/api/schemas.py:126-129` carries an explicit
"DO NOT UNIFY" comment: the dashboard's `_derive_findings()` (`quirk/dashboard/api/routes/scan.py`)
and the CLI pipeline's `evaluate_endpoints()` (`quirk/engine/findings_evaluator.py`) are two
independently-maintained generators for the same underlying endpoint conditions, each with its own
title wording, tuned for its own surface (operator console vs. client deliverable). This module does
NOT unify them, does NOT change either generator, and does NOT add any new narrative text (D-05).
It exists solely because `RemediationItemFingerprint` rows — and therefore every score-lift theme —
are written ONLY from the CLI vocabulary (`remediation_persist.py:254`, hashing
`evaluate_endpoints()` output). A per-finding storyline route that receives a dashboard title must
translate it to the CLI canonical title BEFORE it can look up a theme, or it will silently miss for
most classes.

**Why translation happens BEFORE `normalize_finding_title()`, not instead of it or after it.**
`compliance/__init__.py`'s `FINGERPRINT_TITLE_ALIASES` already contains the entry
`"Certificate expiring in "` -> `"Certificate expiring soon"` — a DASHBOARD-side prefix mapped to a
string that is itself NOT a CLI canonical title (the CLI's title for the same condition is
`"TLS certificate expiring within 30 days"`). Calling `normalize_finding_title()` on a dashboard
title before this module's translation would silently produce that wrong, non-CLI string and any
downstream fingerprint lookup would miss. This module's ledger keys are matched first; its output
(a genuine CLI title, or `None`) is the only thing that may be handed onward to
`normalize_finding_title()` / `compute_fingerprint()`.

**Re-verification method (not title-name similarity).** Every entry below was produced by reading
both generators' actual `if`/`elif` conditions and the endpoint field(s) each reads — not by
comparing how similar the two title strings look. Two titles naming the same general concept are
NOT sufficient for a `bridged` verdict if the two generators fire on different endpoint fields;
that mismatch means bridging them would attribute one condition's theme (and lift) to a different
condition, which is the T-202-01 failure this module exists to prevent. See
`tests/test_finding_title_bridge.py` for the full per-class evidence and
`202-01-SUMMARY.md` for the human-readable verification table.

**The gate, not this file, is the safeguard.** `tests/test_finding_title_bridge.py` regenerates
both generators' title-emission-site occurrence sets from installed source at test-run time (D-06)
— this module is dispositioned DATA the gate checks, not a hand-maintained list that IS the
safeguard. CLAUDE.md records five prior instances of a hand-maintained-list-as-safeguard failing
silently in this repo; this module does not add a sixth.

**Phase 211-04 (DENOM-04 residual): `SCORING_TITLE_DISPOSITIONS`, a second, independent axis.**
211-02 made `quirk/intelligence/evidence.py::_finding_targets` a THIRD consumer of this module (via
`canonical_cli_title`), which turns this module into a scoring input, not merely a remediation-theme
input. `SCORING_TITLE_DISPOSITIONS` below is dispositioned DATA for THAT axis, exactly as
`DASHBOARD_TITLE_BRIDGE` / `UNBRIDGED_DASHBOARD_TITLES` are dispositioned data for the remediation
axis — it is not itself the safeguard either. `tests/test_evidence_scoring_title_coverage.py` is
the gate: it regenerates, from installed source at run time, the exact set of CLI titles
`evidence.py`'s `_finding_targets` calls look up, and fails if that set and this dict's key set ever
diverge in either direction.
"""
from __future__ import annotations

from typing import Dict, Optional

# ---------------------------------------------------------------------------
# DASHBOARD_TITLE_BRIDGE
#
# Key: the literal dashboard title, or (for interpolated f-string titles) the
# literal PREFIX text up to the first `{`. Value: the CLI canonical title
# (verbatim, asserted present in quirk/engine/findings_evaluator.py by the
# gate).
#
# Each entry's comment cites both source line numbers as of this writing —
# 2026-09-12 — read at HEAD; the gate does not trust these numbers, only the
# titles/prefixes themselves.
#
# Includes the three verdict=identity rows (self-signed, untrusted-CA,
# undersized-RSA) as explicit self-mappings rather than relying on
# fall-through, so every dashboard emission site is visible to the gate as a
# dispositioned row, none by omission.
# ---------------------------------------------------------------------------
DASHBOARD_TITLE_BRIDGE: Dict[str, str] = {
    # scan.py:137-143 "Unencrypted HTTP service" fires on
    # `ep.protocol.upper() == "HTTP"`.
    # findings_evaluator.py:537-549 "Plaintext HTTP service detected" fires
    # on `proto == "HTTP"`. Same field (protocol), same comparison. bridged.
    "Unencrypted HTTP service": "Plaintext HTTP service detected",

    # scan.py:154-168 "Legacy TLS version: {ep.tls_version}" fires on
    # `ep.tls_version in ("TLSv1", "TLSv1.1", "TLS 1.0", "TLS 1.1")`.
    # findings_evaluator.py:551-565 "Legacy TLS versions allowed (TLS
    # 1.0/1.1)" fires on `_has_legacy_tls_versions(e)`
    # (findings_evaluator.py:278-287), which checks `ep.tls_version in
    # {"TLSv1", "TLSv1.1"}` OR a `{"TLSv1", "TLSv1.1"}` intersection against
    # `tls_supported_versions`. Same primary field (tls_version); the CLI
    # condition is a superset (also considers tls_supported_versions) and
    # omits the spaced "TLS 1.0"/"TLS 1.1" forms the dashboard also matches.
    # Overlapping-but-not-byte-identical conditions on the same field and
    # same concept -- bridged, not identity, per Task 1's read.
    "Legacy TLS version: ": "Legacy TLS versions allowed (TLS 1.0/1.1)",

    # scan.py:188-207 "Certificate expired" fires on
    # `days_to_expiry < 0` (from `ep.cert_not_after`).
    # findings_evaluator.py:586-608 "TLS certificate expired" fires on
    # `na < now_naive` (also from `cert_not_after`). Same field, same
    # comparison direction. bridged.
    "Certificate expired": "TLS certificate expired",

    # scan.py:208-222 "Certificate expiring in {days_to_expiry} day(s)"
    # fires on `0 <= days_to_expiry < 30`.
    # findings_evaluator.py:609-624 "TLS certificate expiring within 30
    # days" fires on `now_naive <= na < now_naive + timedelta(days=30)`.
    # Same field, same 30-day window. bridged.
    #
    # NOTE (ordering trap, see module docstring): do NOT confuse this
    # dashboard prefix with compliance/__init__.py's
    # FINGERPRINT_TITLE_ALIASES["Certificate expiring in "] ->
    # "Certificate expiring soon", which is a DIFFERENT alias table for a
    # DIFFERENT purpose (compliance-framework identity collapsing) and
    # "Certificate expiring soon" is NOT a CLI title. Translation via this
    # ledger must happen first; normalize_finding_title() must never be
    # applied to an un-translated dashboard title.
    "Certificate expiring in ": "TLS certificate expiring within 30 days",

    # scan.py:230-255 "TLS certificate uses undersized RSA key" fires on
    # `cert_pubkey_alg.upper().startswith("RSA") and cert_pubkey_size < 2048`.
    # findings_evaluator.py:676-697, same title, fires on
    # `cert_pubkey_alg.upper() == "RSA" and cert_pubkey_size < 2048`.
    # Byte-identical title; near-identical condition (startswith vs exact
    # "RSA" -- in practice cert_pubkey_alg is always exactly "RSA" for RSA
    # certs, so this does not change real-world behaviour). identity.
    "TLS certificate uses undersized RSA key": "TLS certificate uses undersized RSA key",

    # scan.py:263-286 "TLS certificate is self-signed" fires on
    # `issuer and subject and issuer == subject`.
    # findings_evaluator.py:634-652, byte-identical title and condition.
    # identity.
    "TLS certificate is self-signed": "TLS certificate is self-signed",

    # scan.py:287-307 "TLS certificate issued by untrusted CA" fires on
    # `issuer and subject and issuer != subject (implicit) and
    # _chain_verified(ep) is False`.
    # findings_evaluator.py:653-671, byte-identical title and condition.
    # identity.
    "TLS certificate issued by untrusted CA": "TLS certificate issued by untrusted CA",
}

# ---------------------------------------------------------------------------
# UNBRIDGED_DASHBOARD_TITLES
#
# Dashboard title/prefix -> one-sentence reason naming the specific
# divergence. A first-class declaration of a known limitation (D-07), not a
# TODO. `canonical_cli_title()` returns None for every key here.
# ---------------------------------------------------------------------------
UNBRIDGED_DASHBOARD_TITLES: Dict[str, str] = {
    # scan.py:171-185 fires on `ep.tls_weak_ciphers_present`.
    # findings_evaluator.py:568-584's nearest-sounding title, "Legacy TLS
    # cipher suites accepted", fires on `ep.tls_legacy_suites_present`.
    # These are two DISTINCT, independently-populated boolean columns
    # (quirk/models.py:45-46; quirk/scanner/tls_scanner.py:323-324 sets both
    # from different capability checks in the same scan). They can and do
    # disagree on a given endpoint. Bridging them would attribute the CLI's
    # legacy-cipher-suites theme (and its lift) to a dashboard finding whose
    # firing condition is a different column -- exactly the T-202-01 failure
    # this module exists to prevent. Confirmed unbridged, matching the
    # plan's own "suspect unbridged" hypothesis.
    "Weak cipher suites enabled": (
        "Fires on ep.tls_weak_ciphers_present; the CLI's nearest title "
        "('Legacy TLS cipher suites accepted') fires on the distinct "
        "ep.tls_legacy_suites_present column -- different firing condition, "
        "no 1:1 CLI equivalent."
    ),

    # scan.py:309-331 fires on `cert_pubkey_alg` truthy and NOT starting
    # with "RSA", i.e. EVERY non-RSA public-key algorithm the CBOM
    # classifier (`classify_algorithm`/`quantum_safety_label`) marks
    # Vulnerable or At-Risk (DSA, DH, Ed25519, and ECDSA all included), with
    # ONE title regardless of key size.
    # findings_evaluator.py has algorithm-specific sites ONLY for RSA
    # (:676-715) and ECDSA (:716-753), and even restricted to the ECDSA
    # subset the CLI splits into two DIFFERENT titles by key-size threshold
    # (undersized vs quantum-vulnerable) where the dashboard emits one title
    # regardless of size. No CLI site covers DSA/DH/Ed25519 at all. No safe
    # 1:1 mapping exists at any granularity. Confirmed unbridged, matching
    # the plan's own "suspect unbridged" hypothesis.
    "Quantum-": (
        "Fires on any non-RSA cert_pubkey_alg the CBOM classifier scores "
        "Vulnerable/At-Risk (DSA, DH, Ed25519, ECDSA of any size, one "
        "title); the CLI has algorithm-specific sites only for RSA and "
        "ECDSA, and even the ECDSA subset splits into two size-gated CLI "
        "titles the dashboard does not distinguish -- no 1:1 CLI "
        "equivalent at any granularity."
    ),
}

# ---------------------------------------------------------------------------
# BRIDGE_REACHABILITY (Task 3 / D-08 / D-09)
#
# CLI title (a DASHBOARD_TITLE_BRIDGE value) -> reachability classification:
#   "specific"      -- appears in some slug's REMEDIATION_CONSTITUENCY
#                       "fingerprint" tuple; can reach a specific theme.
#   "catchall-only" -- not in any fingerprint tuple, but the dashboard
#                       finding's severity is HIGH/CRITICAL, so it can only
#                       ever constitute the "high-impact-findings" severity
#                       catch-all (D-09: this IS rendered when it is the
#                       finding's only theme).
#   "unreachable"   -- neither: constitutes no theme at all (honest A1).
#
# This is the DISPOSITIONED expectation. tests/test_finding_title_bridge.py
# RECOMPUTES the same classification from REMEDIATION_CONSTITUENCY plus each
# dashboard site's literal severity at test-run time and fails on any
# disagreement -- this dict is not itself the safeguard.
# ---------------------------------------------------------------------------
BRIDGE_REACHABILITY: Dict[str, str] = {
    # In "plaintext-http-exposure" fingerprint tuple (remediation.py:81).
    "Plaintext HTTP service detected": "specific",
    # In "legacy-tls-versions" fingerprint tuple (remediation.py:97).
    "Legacy TLS versions allowed (TLS 1.0/1.1)": "specific",
    # In "expired-certificates" fingerprint tuple (remediation.py:88).
    "TLS certificate expired": "specific",
    # In "near-expiry-certificates" fingerprint tuple (remediation.py:91).
    "TLS certificate expiring within 30 days": "specific",
    # In "self-signed-certificates" fingerprint tuple (remediation.py:93).
    "TLS certificate is self-signed": "specific",
    # NOT in any fingerprint tuple. Dashboard severity is HIGH
    # (scan.py:240-241) -> constitutes the "high-impact-findings" severity
    # catch-all as its ONLY theme (D-09).
    "TLS certificate uses undersized RSA key": "catchall-only",
    # NOT in any fingerprint tuple. Dashboard severity is MEDIUM
    # (scan.py:292-293), below the HIGH/CRITICAL catch-all threshold ->
    # constitutes no theme at all.
    "TLS certificate issued by untrusted CA": "unreachable",
}


def canonical_cli_title(dashboard_title: str) -> Optional[str]:
    """Translate a dashboard finding title to its CLI canonical title.

    Longest-prefix-first matching against `DASHBOARD_TITLE_BRIDGE`, mirroring
    `quirk.compliance.normalize_finding_title`'s
    `sorted(table, key=len, reverse=True)` idiom so the two behave
    consistently. Returns the CLI title on a hit; returns **None** for any
    key present in `UNBRIDGED_DASHBOARD_TITLES` or for anything unrecognised.
    Never returns the input title as a fallback -- a guess here becomes a
    confidently wrong theme downstream, which D-06/D-07 treat as worse than
    honest absence.
    """
    for prefix in sorted(DASHBOARD_TITLE_BRIDGE, key=len, reverse=True):
        if dashboard_title.startswith(prefix):
            return DASHBOARD_TITLE_BRIDGE[prefix]
    return None


# ---------------------------------------------------------------------------
# SCORING_TITLE_DISPOSITIONS (Phase 211-04, DENOM-04 residual)
#
# Key: a CLI-canonical title that quirk/intelligence/evidence.py's
# `_finding_targets(finding_list, "<title>")` looks up for a SCORING-CRITICAL
# counter (i.e. one that feeds quirk/intelligence/scoring.py, not merely a
# remediation theme). Value: one of three verdicts, each defined here and
# nowhere else:
#
#   "bridged"                       -- a DASHBOARD_TITLE_BRIDGE entry maps a
#                                       dashboard title to this CLI title, so
#                                       both pipelines produce the same
#                                       counter value via canonical_cli_title
#                                       (211-02).
#   "endpoint-derived"               -- the counter this title feeds does NOT
#                                       depend on the finding-title vocabulary
#                                       for its actual value: either the
#                                       counter is computed straight from
#                                       endpoint fields (the shape 211-03
#                                       applied to legacy_tls_count), or —
#                                       as measured live for "mTLS required"
#                                       below — every finding that could ever
#                                       carry this title corresponds to an
#                                       endpoint object that is ALSO counted
#                                       directly by evidence.py's own
#                                       endpoint-field loop, so the
#                                       finding-title match is a strict,
#                                       always-redundant subset that never
#                                       changes the counter's value. No
#                                       bridge entry is needed either way.
#   "unbridgeable-latent-divergence" -- no dashboard emission site exists for
#                                       this CLI title, and none can safely
#                                       be added (schemas.py:126-129's "DO NOT
#                                       UNIFY"). The dashboard pipeline is
#                                       therefore structurally 0 for this
#                                       counter regardless of the estate. The
#                                       entry MUST name the affected counter,
#                                       the scoring category and weight it
#                                       reaches, and the estate condition
#                                       under which the divergence becomes
#                                       non-zero. Tracked as a todo, not
#                                       silently accepted.
#
# `tests/test_evidence_scoring_title_coverage.py` is the gate that keeps this
# dict honest: it regenerates the true occurrence set of
# `_finding_targets(...)` literal-string call sites from installed source at
# run time and asserts EXACT set equality against this dict's keys (no gaps,
# no extras), plus that every "bridged" value appears in
# DASHBOARD_TITLE_BRIDGE.values() and every key (any verdict) still appears
# in the run-time-extracted CLI title vocabulary.
# ---------------------------------------------------------------------------
SCORING_TITLE_DISPOSITIONS: Dict[str, str] = {
    # evidence.py's _finding_targets(finding_list, "Plaintext HTTP service
    # detected") feeds plaintext_http_count -> scoring.py's Hygiene category
    # ("Plaintext HTTP exposure", weight hygiene_plaintext_http_ratio=18.0).
    # Bridged from the dashboard's "Unencrypted HTTP service" via
    # DASHBOARD_TITLE_BRIDGE (fixed in 211-02, commit 127913ca). Both
    # pipelines now produce the same counter value for the same endpoint
    # condition.
    "Plaintext HTTP service detected": "bridged",

    # evidence.py's _finding_targets(finding_list, "mTLS required") feeds
    # (unions into) mtls_present_count -> scoring.py's Identity category
    # ("mTLS enforcement signals", weight identity_mtls_ratio_bonus, a BONUS
    # term). Measured live (211-04, two probe scenarios against the real
    # evaluate_endpoints()/build_evidence_summary() functions, not asserted
    # by inspection):
    #   (a) a lone TLS endpoint with tls_blocker_reason="MTLS_REQUIRED" and
    #       no finding at all -> mtls_present_count == 1, entirely via
    #       evidence.py's endpoint-field loop (mtls_targets.add((host,
    #       port)) on blocker == "MTLS_REQUIRED"), unioned with ZERO
    #       finding-title matches.
    #   (b) a two-endpoint-object pair sharing one host:port (one classified
    #       HTTP -- the object that produces the initiating "Plaintext HTTP
    #       service detected" finding -- one classified TLS with
    #       tls_blocker_reason="MTLS_REQUIRED" -- the object
    #       findings_evaluator._postprocess_findings' ep_map lookup resolves
    #       to and upgrades the finding to title "mTLS required") ->
    #       mtls_present_count == 1 again, and STILL fully accounted for by
    #       evidence.py's endpoint-field loop alone, because that TLS/blocked
    #       endpoint object is itself iterated by evidence.py's own loop
    #       over the full endpoint list (evidence.py does not dedupe by
    #       host:port the way ep_map does) -- the same (host, port) pair the
    #       "mTLS required" finding would also contribute is therefore
    #       ALWAYS already present in mtls_targets before the `|=` union
    #       runs. The finding-title match is provably redundant, not merely
    #       coincidentally so: any endpoint object whose fields make
    #       findings_evaluator emit "mTLS required" necessarily has
    #       tls_blocker_reason == "MTLS_REQUIRED" on itself, which is exactly
    #       evidence.py's own direct-count condition. No dashboard bridge
    #       entry is needed because the dashboard pipeline reaches the
    #       correct value through the shared endpoint-field loop alone --
    #       both pipelines call the same build_evidence_summary().
    "mTLS required": "endpoint-derived",

    # evidence.py's _finding_targets(finding_list, "HTTP on TLS-designated
    # port") feeds http_on_tls_port_count -> scoring.py's Hygiene category
    # ("HTTP on TLS-designated ports", scoring.py:493, weight
    # hygiene_http_on_tls_ratio=16.0). No dashboard emission site exists for
    # this condition (confirmed: no "title=" construct anywhere in
    # quirk/dashboard/api/routes/scan.py matches "TLS-design" or
    # "designated"), and schemas.py:126-129's "DO NOT UNIFY" forbids adding
    # one by unification. The dashboard pipeline is therefore structurally 0
    # for this counter regardless of the estate -- a LATENT divergence, not
    # an active one, because it also measured 0 on the reference estate
    # (identical live report/dashboard numbers happened to coincide, not
    # because the counter is correct on the dashboard side). Becomes
    # non-zero the moment plaintext HTTP is observed on a port in the
    # TLS-designated set (WELL_KNOWN_TLS_PORTS unioned with the operator's
    # config_template.yaml `tls_designated_ports` override). Tracked at
    # .planning/todos/pending/211-http-on-tls-designated-port-has-no-dashboard-equivalent.md
    # -- see that file for the full estate condition, fix shapes and
    # tag-blocking verdict.
    "HTTP on TLS-designated port": "unbridgeable-latent-divergence",
}
