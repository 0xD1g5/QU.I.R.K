"""Phase 180 Plan 04 (CLOSE-01): the two-sided, machine-observed closure computation.

This module is the requirement's substance. Plan 01 made scope-signature comparability
sound (adding the target-set digest that closes the estate-blind hole); this module is
what USES that soundness to decide closure. The failure being prevented is a client
attestation claiming remediation that never happened, so every design tension here
resolves toward under-claiming: refuse over proceed, ``not_observed`` over ``closed``,
machine-observed over asserted.

THE TWO-SIDED CONDITION (CLOSE-01): a fingerprint closes if and only if BOTH sides
hold — (a) it was present in a scope-comparable PRIOR scan, AND (b) the CURRENT scan
positively rechecked that fingerprint's host:port with a HEALTHY probe and did not find
it there. Absence alone is NEVER sufficient. This copies Qualys's explicit guardrail —
"does not mark a QID closed if the scanner did not recheck it" — which Tenable and Orca
concur with. A vanished host, a curtailed scan, or a shrunk target list is not evidence
of remediation.

``no_targets`` and ``not_run`` probe statuses (and ``unhealthy``) all yield
``not_observed``, never ``closed`` — the recheck never actually happened, or happened
and produced no positive signal either way.

A MISSING scope signature on either side of the comparison is NOT-COMPARABLE, never
comparable-by-default — this honours ``persist_scope_signature``'s docstring
(``quirk/intelligence/scope_signature.py``), written specifically for this module to
respect: a scan that crashed before producing a signature leaves no row at all, which is
the honest outcome, not a clean baseline to compare against.

Phase 229 (FIND-11) refinements: clauses (c)/(d) work on protocol SETS per host:port. A
host:port whose current rows are all non-live (CLOSED/ADVISORY protocol, scan_error
set, or a protocol no probe family classifies, e.g. UNKNOWN after a probe timeout) is
refused (``refused_probe``), and so is one carrying ANY unclassified asset row beside a
classified one (229-REVIEW iteration-2 CR-01). Clause (d) takes the families of the PRIOR scan's
protocols at that host:port (fallback: the live current protocols) and requires, PER HOST:PORT
(229-VERIFICATION gap 1, plan 229-12), that EACH family have a LIVE row at that same host:port
in the current scan and be rechecked through ``probe_family_rechecked``; a family healthy
elsewhere in the scan is not enough, and any CLOSED row or scan_error row at the host:port
refuses it. A plaintext-HTTP family closes only on a live HTTP row or on a live
fingerprint-stage re-identification (``_FINGERPRINT_RECLASS_PROTOCOLS``: TLS/SSH) whose
family was not live at that host:port in the DETECTING scan (``_host_port_rechecked``); a
co-resident SAML/JWT row is not reclassification. Any protocol with no probe family refuses. A closure is also written on the CURRENT scan
(closed fingerprint row, plus a closed item when none exists) so every current-scan
reader sees it (D-03). A REFUSED candidate is carried onto the current scan as a
``not_observed`` fingerprint row, so the next scan can still close it and burndown
keeps counting it; for such a row, clause (d) takes its families from the scan that
last DETECTED it (229-REVIEW WR-03). When such a row closes, the detecting row (and,
once all its constituents are closed, that scan's item) flips to ``closed`` too, and
the current scan gets a closed item when it has none, exactly as on the direct path
(229-REVIEW iteration-2 WR-03). The whole computation refuses
(``refused_missing_snapshot``) when the current scan has no remediation rows at all
(229-REVIEW CR-02).

Prior-scan selection deliberately does NOT use
``quirk/dashboard/api/routes/trends.py::_list_session_timestamps`` (nor its Phase 229
successor ``quirk.intelligence.trends.list_session_timestamps``). That helper folds
NULL-``scan_run_id`` (sensor-origin) rows into session grouping via a millisecond-
timestamp fallback key — precisely the sensor-origin population Phase 179 excluded from
scope-signature coverage (179-CONTEXT.md Sensor-Origin Coverage). Reusing it here would
silently re-admit sensor rows into a closure computation that must stay scoped to
``scan_run_id``-bearing CLI scans. Instead, the prior scan is selected purely by
``ScanScopeSignature.created_at DESC`` (T-180-22).

Probe health is READ from ``probe_health_json`` and NEVER re-derived from
``scan_error``/exit status — see TRIAGE-176-03: an SSH scan invocation bug caused every
scan to exit 0 with ``scan_error`` NULL while the probe had, in fact, silently degraded
to a banner grab. Trusting exit status here would let a probe reported healthy after
silent degradation close items that were never really rechecked (T-180-19). A malformed
or empty ``probe_health_json`` blob is treated as an empty dict, which makes every family
resolve to ``not_run`` and therefore every candidate closure resolve to ``not_observed``
— the honest failure direction (T-180-24).

D-28 — there is NO human-assert path, and its absence is enforced mechanically, not just
by convention. ``compute_closure``'s only parameters are ``db_path`` and ``scan_run_id``
— no flag, config key, environment variable, or function parameter anywhere lets a
caller supply a state (T-180-21). See ``tests/test_closure_verification.py``'s
``# CLOSE-01 (D-28)`` section for the falsifiable source-level proof, including a
negative control.

This module must NEVER reach the quantum-readiness weighting module
(ADVISORY-01, standing across Phases 177-181), nor the dashboard layer.
``tests/test_remediation_advisory_guard.py`` enforces the former with an
AST-level guard.

CLOSE-02 (Plan 05, D-29..D-32) — ``resurfaced``/``reclosed``: a fingerprint whose most
recent PERSISTED row says ``closed`` and that is detected again in the CURRENT scan
becomes ``resurfaced``, never a brand-new finding and never silently folded back into
``open``. D-29 rejects reading ``RemediationClosureEvent`` as an input to this decision —
the event table is a RECORD of what happened, never a second source of truth an in-place
row read has to agree with; the transition reads the persisted fingerprint row only. A
``resurfaced`` fingerprint can close again through the identical two-sided condition that
governs a first closure; the resulting STATE is ``closed`` (D-30 — there is no fifth
``ITEM_STATES`` member for "closed after a regression"), but the EVENT written is
``reclosed``, so the retained event sequence (``closed`` -> ``resurfaced`` -> ``reclosed``,
each row APPENDED and never rewritten — see ``tests/test_closure_events.py``'s append-only
guard) is what keeps the regression legible to a downstream reader. D-31: the resurface
path consumes the SAME ``scans_are_comparable`` verdict already computed for the whole
``compute_closure`` call — a scope mismatch or missing signature refuses resurfacing in
BOTH directions, exactly like it refuses closing; there is deliberately no second gate.
``closure_counts`` (D-32) is the single function that reports ``resurfaced`` separately
AND folds it into ``open_like`` (reading ``OPEN_LIKE_STATES``, never an inline literal),
so the two facts cannot drift apart across callers.

Pipeline wiring into ``run_scan.py`` is Plan 06's responsibility, NOT this module's —
nothing here is called from the scan pipeline yet.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func

from quirk.db import get_session
from quirk.intelligence.remediation import (
    CLOSURE_EVENT_TYPES,
    DEFAULT_ITEM_STATE,
    ITEM_STATES,
    OPEN_LIKE_STATES,
    RESURFACED_STATE,
)
from quirk.intelligence.evidence import NON_ASSET_PROTOCOLS
from quirk.intelligence.scope_signature import (
    SCOPE_SIGNATURE_VERSION,
    family_for_protocol,
    probe_family_rechecked,
)
from quirk.models import (
    CryptoEndpoint,
    RemediationClosureEvent,
    RemediationItem,
    RemediationItemFingerprint,
    ScanScopeSignature,
)

logger = logging.getLogger(__name__)

CLOSURE_MODEL_VERSION = "1.0.0"

# D-25: a fixed comparability ladder — the FIRST failing check names the reason. Fixed
# order means the counter a human reads is deterministic, and the most structural
# failure is reported rather than the most superficial one.
COMPARABILITY_REASONS: Tuple[str, ...] = (
    "comparable",
    "no_prior_scan",
    "missing_signature",
    "signature_version_gap",
    "missing_target_set_digest",
    "scope_mismatch",
)

_CLOSED_STATE = "closed"
# WR-03: a refused candidate is carried onto the current scan in the documented
# undetected state, never a new literal.
_NOT_OBSERVED_STATE = DEFAULT_ITEM_STATE
_TWO_SIDED_REASON = "two_sided_verified"
# 229-VERIFICATION gap 1: protocols the fingerprint stage emits for an open port, other
# than HTTP (the finding's own family) and UNKNOWN (unclassified). A live row of one of
# these is the evidence that the port was re-identified (the HTTP -> TLS move).
# tests/test_closure_verification.py pins this set against quirk/scanner/fingerprint.py
# at run time, so it cannot drift silently.
_FINGERPRINT_RECLASS_PROTOCOLS = frozenset({"SSH", "TLS"})
_RESURFACE_REASON = "detected_after_closure"

_COUNTER_KEYS: Tuple[str, ...] = (
    "closed",
    "resurfaced",
    "reclosed",
    "items_closed",
    "refused_no_prior",
    "refused_missing_signature",
    "refused_signature_version_gap",
    "refused_missing_target_set_digest",
    "refused_scope_mismatch",
    "refused_probe",
    "refused_absent_endpoint",
    "refused_missing_snapshot",
    "unchanged",
)


def _zero_counters() -> Dict[str, int]:
    return {key: 0 for key in _COUNTER_KEYS}


def select_prior_scan_run_id(session: Any, *, current_scan_run_id: str) -> Optional[str]:
    """Return the scan_run_id of the most recent OTHER scan, or None if there isn't one.

    Ordered by ``ScanScopeSignature.created_at DESC`` — deliberately NOT through
    ``trends.py::_list_session_timestamps`` (see module docstring). ``ScanScopeSignature``
    rows only ever exist for ``scan_run_id``-bearing CLI scans, which is precisely the
    population closure is scoped to.
    """
    row = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id != current_scan_run_id)
        .order_by(ScanScopeSignature.created_at.desc())
        .first()
    )
    return row.scan_run_id if row is not None else None


def scans_are_comparable(
    session: Any, *, current_scan_run_id: str, prior_scan_run_id: Optional[str]
) -> Tuple[bool, str]:
    """Evaluate D-25's fixed comparability ladder; return (True, "comparable") or
    (False, reason) at the FIRST failing check.
    """
    if not prior_scan_run_id:
        return False, "no_prior_scan"

    current_sig = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id == current_scan_run_id)
        .one_or_none()
    )
    prior_sig = (
        session.query(ScanScopeSignature)
        .filter(ScanScopeSignature.scan_run_id == prior_scan_run_id)
        .one_or_none()
    )
    # A MISSING signature on EITHER side is NOT-COMPARABLE, never
    # comparable-by-default (persist_scope_signature's docstring contract).
    if current_sig is None or prior_sig is None:
        return False, "missing_signature"

    if (
        current_sig.signature_version != SCOPE_SIGNATURE_VERSION
        or prior_sig.signature_version != SCOPE_SIGNATURE_VERSION
    ):
        return False, "signature_version_gap"

    if not current_sig.target_set_digest or not prior_sig.target_set_digest:
        return False, "missing_target_set_digest"

    if current_sig.digest != prior_sig.digest:
        return False, "scope_mismatch"

    return True, "comparable"


def _load_probe_health(current_sig: Optional[ScanScopeSignature]) -> Dict[str, Any]:
    if current_sig is None or not current_sig.probe_health_json:
        return {}
    try:
        loaded = json.loads(current_sig.probe_health_json)
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_closure_event(
    session: Any,
    *,
    slug: str,
    finding_fingerprint: Optional[str],
    scan_run_id: str,
    prior_scan_run_id: Optional[str],
    event_type: str,
    from_state: Optional[str],
    to_state: Optional[str],
    reason: Optional[str],
) -> None:
    # D-22: the write-site allowlist is enforced here, not decoratively —
    # an unvalidated allowlist is decoration.
    if event_type not in CLOSURE_EVENT_TYPES:
        raise ValueError(
            f"closure.py: refusing to write RemediationClosureEvent with "
            f"event_type={event_type!r} — not a member of CLOSURE_EVENT_TYPES"
        )
    session.add(
        RemediationClosureEvent(
            slug=slug,
            finding_fingerprint=finding_fingerprint,
            scan_run_id=scan_run_id,
            prior_scan_run_id=prior_scan_run_id,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            observed_at=datetime.now(timezone.utc),
        )
    )


def _detection_row(
    session: Any, row: RemediationItemFingerprint, current_scan_run_id: str
) -> Optional[RemediationItemFingerprint]:
    """The latest OPEN_LIKE row for ``row``'s fingerprint on an earlier scan.

    For a carried-forward ``not_observed`` row this is the row of the scan that
    last DETECTED the finding (229-REVIEW WR-03). Legacy pre-release
    ``not_observed`` rows (D-04) find none, because OPEN_LIKE excludes them.
    """
    return (
        session.query(RemediationItemFingerprint)
        .filter(
            RemediationItemFingerprint.slug == row.slug,
            RemediationItemFingerprint.finding_fingerprint == row.finding_fingerprint,
            RemediationItemFingerprint.state.in_(OPEN_LIKE_STATES),
            RemediationItemFingerprint.scan_run_id != current_scan_run_id,
        )
        .order_by(
            RemediationItemFingerprint.observed_at.desc(),
            RemediationItemFingerprint.id.desc(),
        )
        .first()
    )


def _detection_protocols(
    session: Any, detected: Optional[RemediationItemFingerprint], row: RemediationItemFingerprint
) -> set:
    """Protocols at ``row``'s host:port in the scan of ``detected``.

    Used only for a carried-forward ``not_observed`` row (229-REVIEW WR-03) whose
    adjacent prior scan has no asset row at that host:port. Returns an empty set
    when no detecting scan or endpoint row is found (callers then fall back).
    """
    if detected is None:
        return set()
    return {
        ep.protocol
        for ep in session.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scan_run_id == detected.scan_run_id,
            CryptoEndpoint.host == row.host,
            CryptoEndpoint.port == row.port,
        )
        .all()
    }


def _live_families_at(session: Any, scan_run_id: str, host: Any, port: Any) -> set:
    """Families LIVE at host:port in ``scan_run_id`` (same definition of live as the
    current-scan loop: a real asset, no scan_error, a protocol some probe classifies)."""
    fams = set()
    for ep in (
        session.query(CryptoEndpoint)
        .filter(
            CryptoEndpoint.scan_run_id == scan_run_id,
            CryptoEndpoint.host == host,
            CryptoEndpoint.port == port,
        )
        .all()
    ):
        if (
            ep.protocol
            and ep.protocol not in NON_ASSET_PROTOCOLS
            and ep.scan_error is None
        ):
            fam = family_for_protocol(ep.protocol)
            if fam is not None:
                fams.add(fam)
    return fams


def _host_port_rechecked(
    prior_families: set,
    reclass_baseline: set,
    live_families_at_k: set,
    live_protocols_at_k: set,
    probe_health: Dict[str, Any],
) -> bool:
    """Per host:port recheck decision (229-VERIFICATION gap 1, D-20/D-05/D-21).

    Every family that reported the host:port must have a LIVE row there now and be
    rechecked. ``http`` alone may instead be satisfied by positive reclassification:
    a live row whose protocol is in ``_FINGERPRINT_RECLASS_PROTOCOLS`` and whose family
    was not live at the host:port in the detecting scan (``reclass_baseline``).
    An empty family set is never vacuously rechecked.
    """
    if not prior_families:
        return False
    for fam in prior_families:
        if not probe_family_rechecked(probe_health, fam):
            return False
        if fam in live_families_at_k:
            continue
        if fam == "http" and any(
            p in _FINGERPRINT_RECLASS_PROTOCOLS
            and family_for_protocol(p) not in reclass_baseline
            for p in live_protocols_at_k
        ):
            continue
        return False
    return True


def compute_closure(db_path: str, scan_run_id: str) -> Dict[str, int]:
    """Compute two-sided closure for `scan_run_id` against its selected prior scan.

    Only parameters are db_path and scan_run_id (D-28) — no caller can supply a state.

    Returns a counters dict; every key in `_COUNTER_KEYS` is ALWAYS present (never a
    sparse dict — a missing key is indistinguishable from zero to a downstream reader).

    Advisory bookkeeping layered on already-persisted scan data — this function must
    NEVER be able to fail a scan. Any exception is caught, logged, and reported back as
    zeroed counters (mirrors persist_remediation_snapshot's exception-guard style).
    """
    counters = _zero_counters()

    if not db_path or not scan_run_id:
        logger.warning("closure: skipped — missing db_path or scan_run_id")
        return counters

    try:
        with get_session(db_path) as session:
            prior_scan_run_id = select_prior_scan_run_id(
                session, current_scan_run_id=scan_run_id
            )
            if prior_scan_run_id is None:
                counters["refused_no_prior"] = 1
                return counters

            comparable, reason = scans_are_comparable(
                session,
                current_scan_run_id=scan_run_id,
                prior_scan_run_id=prior_scan_run_id,
            )
            if not comparable:
                counters[f"refused_{reason}"] = 1
                return counters

            current_sig = (
                session.query(ScanScopeSignature)
                .filter(ScanScopeSignature.scan_run_id == scan_run_id)
                .one_or_none()
            )
            probe_health = _load_probe_health(current_sig)

            # D-20: protocol SETS per host:port (a last-row-wins dict misjudged real
            # multi-protocol host:ports). `current_present` answers clause (c) (any row
            # at all); `current_live` answers the live-row guard: a recheck needs a row
            # that is a real asset (not CLOSED/ADVISORY), carries no scan_error, AND
            # has a protocol some probe family classifies. An unclassified row
            # (UNKNOWN from a plaintext-HTTP probe timeout or an SSH banner-read
            # timeout, TCP, FINGERPRINT, ...) is not recheck evidence: clause (d)
            # judges the PRIOR protocol's family scan-wide, so admitting it would
            # let one slow endpoint close whenever its family is healthy elsewhere
            # (229-REVIEW CR-01).
            # `current_asset` keeps every error-free asset protocol (classified or
            # not) for clause (d)'s no-prior-row fallback, so an unclassified
            # protocol there still refuses rather than being filtered away.
            # `current_unclassified` (229-REVIEW iteration-2 CR-01): host:ports
            # with ANY asset row (not CLOSED/ADVISORY) whose protocol no probe
            # family classifies. A probe there failed to classify the service
            # (e.g. the HTTP probe timed out to UNKNOWN beside a healthy SAML or
            # JWT row), so the whole host:port is not rechecked, whatever other
            # classified rows it carries.
            current_present: Dict[Tuple[Any, Any], set] = defaultdict(set)
            current_live: Dict[Tuple[Any, Any], set] = defaultdict(set)
            current_asset: Dict[Tuple[Any, Any], set] = defaultdict(set)
            current_unclassified: set = set()
            # 229-VERIFICATION gap 1: `current_failed` = host:ports with a CLOSED row
            # or any asset row carrying scan_error (a probe there failed). ADVISORY
            # rows are deliberately NOT included: they are heterogeneous annotations
            # (JWKS-verify-disabled, broker cleartext, target-unreached), not probe
            # outcomes, and the per-family rule already refuses when the finding's own
            # family has no live row. `current_live_families` is the per-host family
            # set that rule is checked against.
            current_failed: set = set()
            current_live_families: Dict[Tuple[Any, Any], set] = defaultdict(set)
            for ep in (
                session.query(CryptoEndpoint)
                .filter(CryptoEndpoint.scan_run_id == scan_run_id)
                .all()
            ):
                key = (ep.host, ep.port)
                current_present[key].add(ep.protocol)
                if ep.protocol == "CLOSED" or (
                    ep.protocol not in NON_ASSET_PROTOCOLS and ep.scan_error is not None
                ):
                    current_failed.add(key)
                if (
                    ep.protocol not in NON_ASSET_PROTOCOLS
                    and family_for_protocol(ep.protocol) is None
                ):
                    current_unclassified.add(key)
                if (
                    ep.protocol
                    and ep.protocol not in NON_ASSET_PROTOCOLS
                    and ep.scan_error is None
                ):
                    current_asset[key].add(ep.protocol)
                    if family_for_protocol(ep.protocol) is not None:
                        current_live[key].add(ep.protocol)
                        current_live_families[key].add(family_for_protocol(ep.protocol))
            prior_protocols_at: Dict[Tuple[Any, Any], set] = defaultdict(set)
            # Reclassification baseline for a direct (non-carried) row: the families
            # LIVE at the host:port in the adjacent prior (= detecting) scan.
            prior_live_families: Dict[Tuple[Any, Any], set] = defaultdict(set)
            for ep in (
                session.query(CryptoEndpoint)
                .filter(CryptoEndpoint.scan_run_id == prior_scan_run_id)
                .all()
            ):
                prior_protocols_at[(ep.host, ep.port)].add(ep.protocol)
                if (
                    ep.protocol
                    and ep.protocol not in NON_ASSET_PROTOCOLS
                    and ep.scan_error is None
                    and family_for_protocol(ep.protocol) is not None
                ):
                    prior_live_families[(ep.host, ep.port)].add(
                        family_for_protocol(ep.protocol)
                    )
            current_items: Dict[str, RemediationItem] = {
                it.slug: it
                for it in session.query(RemediationItem)
                .filter(RemediationItem.scan_run_id == scan_run_id)
                .all()
            }
            current_fp_rows: Dict[Tuple[Any, Any], RemediationItemFingerprint] = {
                (row.slug, row.finding_fingerprint): row
                for row in session.query(RemediationItemFingerprint)
                .filter(RemediationItemFingerprint.scan_run_id == scan_run_id)
                .all()
            }
            current_fingerprints = set(current_fp_rows.keys())

            # 229-REVIEW CR-02: no RemediationItem and no fingerprint row on the
            # current scan means its remediation snapshot was never written (a
            # successful persist always writes the governance items). Missing
            # current rows must never read as "every prior fingerprint is gone"
            # (clause (e)) - refuse the whole computation instead.
            if not current_items and not current_fp_rows:
                logger.warning(
                    "closure: refused - no remediation snapshot persisted for "
                    "scan_run_id=%s",
                    scan_run_id,
                )
                counters["refused_missing_snapshot"] = 1
                return counters

            prior_rows = (
                session.query(RemediationItemFingerprint)
                .filter(RemediationItemFingerprint.scan_run_id == prior_scan_run_id)
                .all()
            )

            # IN-02: current-scan rows this computation inserts, per slug, so a
            # closed item inserted in the rollup can be linked back to them.
            inserted_rows: Dict[str, list] = defaultdict(list)
            # WR-03: slugs with a row closed by THIS computation, and the
            # detecting scans whose rows a carried closure flipped, per slug.
            closed_slugs: set = set()
            detecting_scans: Dict[str, set] = defaultdict(set)

            def _carry_forward(prior_row: RemediationItemFingerprint) -> None:
                """229-REVIEW WR-03: a refused candidate stays a candidate.

                A refusal is "not verified this scan", not "gone". Without a
                current-scan row the next scan's closure (which reads only its
                adjacent prior scan) would never see this fingerprint again, so it
                could never close and would drop out of every later burndown. Copy
                it onto the current scan as ``not_observed``. Clause (e) makes the
                key absent here; a re-run sees the copy and leaves it alone.
                """
                key = (prior_row.slug, prior_row.finding_fingerprint)
                if key in current_fingerprints:
                    return
                current_fingerprints.add(key)
                cur_item = current_items.get(prior_row.slug)
                carried = RemediationItemFingerprint(
                    remediation_item_id=cur_item.id if cur_item is not None else None,
                    slug=prior_row.slug,
                    scan_run_id=scan_run_id,
                    finding_fingerprint=prior_row.finding_fingerprint,
                    host=prior_row.host,
                    port=prior_row.port,
                    finding_title=prior_row.finding_title,
                    state=_NOT_OBSERVED_STATE,
                    observed_at=datetime.now(timezone.utc),
                )
                session.add(carried)
                inserted_rows[prior_row.slug].append(carried)

            touched_slugs = set()
            for row in prior_rows:
                touched_slugs.add(row.slug)

                # Idempotency: a fingerprint already closed by a prior run of this
                # exact computation stays closed and writes nothing new.
                if row.state == _CLOSED_STATE:
                    counters["unchanged"] += 1
                    continue

                # Clause (e): the fingerprint must be GONE from the current scan.
                if (row.slug, row.finding_fingerprint) in current_fingerprints:
                    counters["unchanged"] += 1
                    continue

                # Clause (c): a CryptoEndpoint must exist for the CURRENT scan at
                # this row's host:port. Absence alone is never sufficient (the
                # Qualys guardrail).
                endpoint_key = (row.host, row.port)
                if endpoint_key not in current_present:
                    counters["refused_absent_endpoint"] += 1
                    _carry_forward(row)
                    continue

                # Clause (c'): a row exists but none is LIVE (timeout/refused CLOSED
                # row, ADVISORY placeholder, scan_error set, or an unclassified
                # protocol such as UNKNOWN) - not a recheck. Nor is a host:port
                # where ANY asset row is unclassified, even beside a classified
                # one (229-REVIEW iteration-2 CR-01).
                live_protocols = current_live.get(endpoint_key, set())
                # 229-VERIFICATION gap 1: nor is one carrying a CLOSED or scan_error
                # row (a probe there failed), even beside a live co-resident row.
                if (
                    not live_protocols
                    or endpoint_key in current_unclassified
                    or endpoint_key in current_failed
                ):
                    counters["refused_probe"] += 1
                    _carry_forward(row)
                    continue

                # Clause (d): the probe family(ies) that raised the finding must ALL
                # be rechecked. Families come from the PRIOR scan's protocols at this
                # host:port (D-05); fall back to the current error-free asset ones
                # (classified or not). A protocol with no probe family can never be
                # shown rechecked, so it refuses (never dropped from the set). A
                # NULL/empty prior protocol is unmapped too: it refuses rather than
                # falling through to the current protocols (229-REVIEW WR-05).
                prior_raw = prior_protocols_at.get(endpoint_key, set())
                detected = (
                    _detection_row(session, row, scan_run_id)
                    if row.state == _NOT_OBSERVED_STATE
                    else None
                )
                if row.state == _NOT_OBSERVED_STATE:
                    # WR-03: a carried-forward row's adjacent prior scan may not have
                    # observed this host:port, or saw only a co-resident row while
                    # the finding's own probe failed (that is why it was refused
                    # there). ALWAYS union the scan that DETECTED it, so a dropped
                    # family cannot be forgotten (229-VERIFICATION gap 1, D-20).
                    prior_raw = set(prior_raw) | _detection_protocols(session, detected, row)
                if any(not p for p in prior_raw):
                    counters["refused_probe"] += 1
                    _carry_forward(row)
                    continue
                prior_set = {p for p in prior_raw if p not in NON_ASSET_PROTOCOLS}
                # 229-VERIFICATION residual gap (FIND-11): an empty probe-family
                # basis (a legacy-origin carried chain, or a prior scan that saw
                # only non-asset rows here) never falls back to the CURRENT scan's
                # protocols - that would let a co-resident SAML/JWT row stand in for
                # the probe that raised the finding. Refuse and carry forward for a
                # carried row. The direct path (an open/resurfaced row whose prior
                # scan detected it from an asset row here) keeps the fallback: the
                # production writer never persists such a row without that
                # endpoint, and seeded fixtures in test_closure_verification.py
                # rely on it.
                if row.state == _NOT_OBSERVED_STATE and not prior_set:
                    counters["refused_probe"] += 1
                    _carry_forward(row)
                    continue
                # 229-VERIFICATION residual gap 2 (FIND-11): a carried row with NO
                # detecting open/resurfaced row anywhere in its history is a
                # pre-release (D-04) legacy row. Its basis can only come from an
                # intermediate scan (e.g. one that saw just a co-resident SAML/JWT
                # row), never the probe that raised the finding, so it is refused
                # regardless of basis until a re-detection writes a real ``open``
                # row.
                if row.state == _NOT_OBSERVED_STATE and detected is None:
                    counters["refused_probe"] += 1
                    _carry_forward(row)
                    continue
                check_protocols = prior_set or current_asset.get(
                    endpoint_key, live_protocols
                )
                families = [family_for_protocol(p) for p in check_protocols]
                family_set = set(families)
                # Reclassification baseline = families LIVE at host:port in the
                # DETECTING scan, never the prior/intermediate union (W1): the union
                # only decides which families must be rechecked. A carried row with no
                # detecting row (legacy D-04) uses the full set: the stricter choice.
                if row.state != _NOT_OBSERVED_STATE:
                    reclass_baseline = prior_live_families.get(endpoint_key, set())
                elif detected is not None:
                    reclass_baseline = _live_families_at(
                        session, detected.scan_run_id, row.host, row.port
                    )
                else:
                    reclass_baseline = family_set
                if any(f is None for f in families) or not _host_port_rechecked(
                    family_set,
                    reclass_baseline,
                    current_live_families.get(endpoint_key, set()),
                    live_protocols,
                    probe_health,
                ):
                    counters["refused_probe"] += 1
                    _carry_forward(row)
                    continue

                # All five clauses hold — close it. D-30: a fingerprint whose
                # from_state is RESURFACED_STATE closes to the SAME state
                # ("closed" — no fifth ITEM_STATES member), but the EVENT
                # written is "reclosed" so the earlier regression stays
                # legible in the retained event sequence.
                # 229-REVIEW iteration-2 WR-04: a carried (not_observed) row keeps
                # the lineage of the scan that detected it - if that detection was
                # a resurface, this closure is a reclose. from_state stays the
                # flipped row's own state.
                from_state = row.state
                lineage_state = detected.state if detected is not None else from_state
                row.state = _CLOSED_STATE
                event_type = (
                    "reclosed" if lineage_state == RESURFACED_STATE else "closed"
                )
                _write_closure_event(
                    session,
                    slug=row.slug,
                    finding_fingerprint=row.finding_fingerprint,
                    scan_run_id=scan_run_id,
                    prior_scan_run_id=prior_scan_run_id,
                    event_type=event_type,
                    from_state=from_state,
                    to_state=_CLOSED_STATE,
                    reason=_TWO_SIDED_REASON,
                )
                counters[event_type] += 1
                closed_slugs.add(row.slug)
                # 229-REVIEW iteration-2 WR-03: closing a carried row also flips
                # the row of the scan that DETECTED the finding, so history reads
                # the same as on the direct path (where the adjacent prior row IS
                # the detecting row). Its item is rolled up below.
                if detected is not None:
                    detected.state = _CLOSED_STATE
                    detecting_scans[row.slug].add(detected.scan_run_id)
                # D-03: record the closure on the scan that observed it. Clause (e)
                # guarantees this fingerprint is absent from the current scan, so the
                # (scan_run_id, slug, finding_fingerprint) unique key cannot collide.
                cur_item = current_items.get(row.slug)
                closed_row = RemediationItemFingerprint(
                    remediation_item_id=cur_item.id if cur_item is not None else None,
                    slug=row.slug,
                    scan_run_id=scan_run_id,
                    finding_fingerprint=row.finding_fingerprint,
                    host=row.host,
                    port=row.port,
                    finding_title=row.finding_title,
                    state=_CLOSED_STATE,
                    observed_at=datetime.now(timezone.utc),
                )
                session.add(closed_row)
                inserted_rows[row.slug].append(closed_row)

            # CLOSE-02 (D-29): resurface detection. Evaluated on the CURRENT
            # scan's OWN fingerprint rows (a fresh row exists only when the
            # finding was actually detected again this scan), using the SAME
            # `comparable` verdict already established above (D-31 — no
            # second gate). For each key detected this scan, read the most
            # recently PERSISTED row for that exact (slug, finding_fingerprint)
            # — not the event log (D-29 rejects replaying
            # RemediationClosureEvent as a decision input; the event table is
            # a record, never an input). If that persisted state was
            # "closed", the reappearance is a regression, not a new finding:
            # the CURRENT row becomes RESURFACED_STATE and one "resurfaced"
            # event is appended. Idempotent: a current row already at
            # RESURFACED_STATE or "closed" is left alone on a re-run.
            for (fp_slug, fp_fingerprint), current_row in current_fp_rows.items():
                if current_row.state in (RESURFACED_STATE, _CLOSED_STATE):
                    counters["unchanged"] += 1
                    continue

                latest_prior_row = (
                    session.query(RemediationItemFingerprint)
                    .filter(
                        RemediationItemFingerprint.slug == fp_slug,
                        RemediationItemFingerprint.finding_fingerprint == fp_fingerprint,
                        RemediationItemFingerprint.scan_run_id != scan_run_id,
                    )
                    .order_by(
                        RemediationItemFingerprint.observed_at.desc(),
                        RemediationItemFingerprint.id.desc(),
                    )
                    .first()
                )
                if latest_prior_row is None or latest_prior_row.state != _CLOSED_STATE:
                    continue

                current_row.state = RESURFACED_STATE
                _write_closure_event(
                    session,
                    slug=fp_slug,
                    finding_fingerprint=fp_fingerprint,
                    scan_run_id=scan_run_id,
                    prior_scan_run_id=latest_prior_row.scan_run_id,
                    event_type="resurfaced",
                    from_state=_CLOSED_STATE,
                    to_state=RESURFACED_STATE,
                    reason=_RESURFACE_REASON,
                )
                counters["resurfaced"] += 1

            # D-27: item-level rollup. A RemediationItem becomes closed only when it
            # has at least one constituent fingerprint (at the prior scan) and EVERY
            # one of them is now closed. evidence_only items have zero constituent
            # fingerprints by construction and are correctly never touched here.
            # 229-REVIEW iteration-2 WR-03: the same rule applies to the item of
            # each detecting scan a carried closure flipped a row on, and the
            # current-scan closed item no longer depends on the ADJACENT prior
            # scan having an item (a carried slug often has none there).
            session.flush()
            for slug in touched_slugs:
                item = (
                    session.query(RemediationItem)
                    .filter(
                        RemediationItem.slug == slug,
                        RemediationItem.scan_run_id == prior_scan_run_id,
                    )
                    .one_or_none()
                )
                constituent_states = [
                    r.state
                    for r in prior_rows
                    if r.slug == slug
                ]
                all_closed = bool(constituent_states) and all(
                    s == _CLOSED_STATE for s in constituent_states
                )
                item_flipped = False
                if item is not None and item.state != _CLOSED_STATE and all_closed:
                    item.state = _CLOSED_STATE
                    item_flipped = True

                template = item
                for detect_scan in sorted(detecting_scans.get(slug, ())):
                    detect_item = (
                        session.query(RemediationItem)
                        .filter(
                            RemediationItem.slug == slug,
                            RemediationItem.scan_run_id == detect_scan,
                        )
                        .one_or_none()
                    )
                    if detect_item is None:
                        continue
                    if template is None:
                        template = detect_item
                    if detect_item.state == _CLOSED_STATE:
                        continue
                    detect_states = [
                        r.state
                        for r in session.query(RemediationItemFingerprint)
                        .filter(
                            RemediationItemFingerprint.slug == slug,
                            RemediationItemFingerprint.scan_run_id == detect_scan,
                        )
                        .all()
                    ]
                    if detect_states and all(s == _CLOSED_STATE for s in detect_states):
                        detect_item.state = _CLOSED_STATE
                        item_flipped = True
                if item_flipped:
                    counters["items_closed"] += 1

                # D-03: a current-scan closed item so VEX reads RESOLVED; an
                # existing current item is never flipped. Written only when this
                # computation closed something for the slug (or flipped its item),
                # so a re-run or an already-closed history writes nothing new.
                if (
                    not all_closed
                    or slug in current_items
                    or not (item_flipped or slug in closed_slugs)
                ):
                    continue
                if template is None:
                    template = (
                        session.query(RemediationItem)
                        .filter(
                            RemediationItem.slug == slug,
                            RemediationItem.scan_run_id != scan_run_id,
                        )
                        .order_by(
                            RemediationItem.created_at.desc(),
                            RemediationItem.id.desc(),
                        )
                        .first()
                    )
                if template is None:
                    continue
                closed_item = RemediationItem(
                    slug=slug,
                    scan_run_id=scan_run_id,
                    title=template.title,
                    phase=template.phase,
                    priority=template.priority,
                    constituency=template.constituency,
                    state=_CLOSED_STATE,
                    first_seen_scan_run_id=template.first_seen_scan_run_id,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(closed_item)
                current_items[slug] = closed_item
                # IN-02: link the rows inserted beside it.
                session.flush()
                for inserted in inserted_rows.get(slug, ()):
                    if inserted.remediation_item_id is None:
                        inserted.remediation_item_id = closed_item.id

            session.commit()
        return counters
    except Exception:  # noqa: BLE001 — must never fail a scan
        logger.exception(
            "closure: failed to compute closure for scan_run_id=%s", scan_run_id
        )
        return _zero_counters()


def closure_counts(session: Any, *, scan_run_id: str) -> Dict[str, int]:
    """Return state counts for `scan_run_id`'s fingerprint rows, plus `open_like`.

    D-32: this is the SINGLE function that reports `resurfaced` separately AND folds
    it into `open_like` (summed from `OPEN_LIKE_STATES`, never an inline literal) — two
    callers computing "counted as open" and "reported separately" from the same pass
    means they cannot disagree. Every member of `ITEM_STATES` is always present in the
    result, seeded to zero when absent, so a consumer can never mistake "absent" for
    "not applicable" (T-180-31) — this never returns a sparse dict or a single scalar.
    """
    counts: Dict[str, int] = {state: 0 for state in ITEM_STATES}
    rows = (
        session.query(
            RemediationItemFingerprint.state,
            func.count(RemediationItemFingerprint.id),
        )
        .filter(RemediationItemFingerprint.scan_run_id == scan_run_id)
        .group_by(RemediationItemFingerprint.state)
        .all()
    )
    for state, count in rows:
        if state in counts:
            counts[state] = count
    counts["open_like"] = sum(counts[state] for state in OPEN_LIKE_STATES)
    return counts
