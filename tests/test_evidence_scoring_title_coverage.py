"""Phase 211-04 (DENOM-04 residual): run-time source-scan coverage gate over
`quirk/intelligence/evidence.py`'s SCORING-CRITICAL finding-title lookups.

**Why this gate exists, and why `SCORING_TITLE_DISPOSITIONS` alone is not enough.** 211-02 made
`evidence.py::_finding_targets` a consumer of
`quirk/dashboard/api/finding_title_bridge.py::canonical_cli_title`, which turns that bridge module
into a SCORING input, not merely a remediation-theme input. `tests/test_finding_title_bridge.py`
already regenerates the bridge's occurrence sets for the remediation axis; it does NOT know that
`evidence.py` separately consumes specific CLI titles for scoring counters. This file adds that
missing axis, following the exact in-repo precedent: no hand-maintained list of "the titles
evidence.py cares about" is trusted anywhere in this file -- both the evidence-side occurrence set
and the CLI-side vocabulary are regenerated from installed source at every test run. CLAUDE.md
records six-plus prior instances in this repo of a hand-maintained list silently drifting from the
real set; this file does not add a seventh.

**The AST-walk vs. regex choice for the evidence.py side.** `_finding_targets(...)` call sites are
extracted via `ast`, not regex, so a comment or docstring that happens to mention a title string
cannot be mistaken for a real call site. Any call passing a non-literal `wanted_title` (a variable)
FAILS the gate loudly, naming the line -- a computed title is invisible to a source scan and must
never pass silently.

**The two-emission-form axis on the CLI side.** `findings_evaluator.py` emits titles via TWO
distinct forms: the `title="..."` kwarg form (already covered by
`test_finding_title_bridge.py::_extract_cli_titles`, reused here rather than reimplemented) and the
`f["title"] = "..."` REWRITE form used inside `_postprocess_findings`'s HTTP-on-TLS-port upgrade
logic (`findings_evaluator.py:417-436`). `_extract_cli_titles` does NOT match the rewrite form --
confirmed live, not assumed (see `test_cli_rewrite_extractor_sees_the_rewrite_only_title` below,
cross-checked against a second, independent method: plain `grep`). "HTTP on TLS-designated port" is
emitted ONLY via the rewrite form and is exactly the title `evidence.py` looks up for
`http_on_tls_port_count` -- an extractor that silently misses this form would report its own blind
spot as a confident "fully dispositioned" pass, which is the failure mode CLAUDE.md names "measure
with a method independent of the audited code".
"""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
from typing import List, Set, Tuple

from quirk.dashboard.api.finding_title_bridge import (
    DASHBOARD_TITLE_BRIDGE,
    SCORING_TITLE_DISPOSITIONS,
    canonical_cli_title,
)
from quirk.intelligence.evidence import build_evidence_summary
from tests.test_finding_title_bridge import _extract_cli_titles

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EVIDENCE_PY = _REPO_ROOT / "quirk" / "intelligence" / "evidence.py"
_EVALUATOR_PY = _REPO_ROOT / "quirk" / "engine" / "findings_evaluator.py"

# Matches the f["title"] = "..." / f['title'] = "..." REWRITE emission form.
# Deliberately a SEPARATE regex from test_finding_title_bridge.py's _TITLE_RE
# (which matches `title=` kwargs only) -- these are two independent
# emission shapes and must be extracted independently, not unified into one
# regex (unifying independent extractors is a recorded anti-pattern in this
# repo -- 210-02 collapsed two deliberately independent AST walkers into a
# union with itself and had to be reverted).
_REWRITE_RE = re.compile(r'f\[\s*["\']title["\']\s*\]\s*=\s*"((?:[^"\\]|\\.)*)"')


def _extract_evidence_scoring_titles() -> List[Tuple[int, str]]:
    """AST-walk evidence.py for `_finding_targets(...)` calls and collect the
    literal `wanted_title` string argument (positional arg index 1).

    An AST walk (rather than regex) cannot be fooled by a comment or
    docstring mentioning a title string. FAILS LOUDLY -- raises, does not
    skip -- if any call passes a non-literal `wanted_title`: a computed
    title is invisible to this gate and must not pass silently.
    """
    source = _EVIDENCE_PY.read_text()
    tree = ast.parse(source, filename=str(_EVIDENCE_PY))
    results: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_finding_targets"
        ):
            continue
        if len(node.args) < 2:
            raise AssertionError(
                f"evidence.py line {node.lineno}: _finding_targets(...) call has "
                f"fewer than 2 positional args ({len(node.args)}) -- cannot "
                "extract wanted_title. Investigate before trusting this gate."
            )
        title_arg = node.args[1]
        if isinstance(title_arg, ast.Constant) and isinstance(title_arg.value, str):
            results.append((node.lineno, title_arg.value))
        else:
            raise AssertionError(
                f"evidence.py line {node.lineno}: _finding_targets(...) called "
                f"with a NON-LITERAL wanted_title ({ast.dump(title_arg)}) -- a "
                "computed title is invisible to this gate and must not pass "
                "silently. Either make the title a string literal or extend "
                "this extractor to resolve it before trusting the gate again."
            )
    return results


def _extract_cli_rewrite_titles() -> List[Tuple[int, str]]:
    """Scan findings_evaluator.py for the f["title"] = "..." REWRITE
    emission form -- the form test_finding_title_bridge.py's
    `_extract_cli_titles` (kwarg-only) does not see. Returns
    (line_number, literal_title) tuples.
    """
    source = _EVALUATOR_PY.read_text()
    results: List[Tuple[int, str]] = []
    for i, line in enumerate(source.splitlines(), start=1):
        m = _REWRITE_RE.search(line)
        if m:
            results.append((i, m.group(1)))
    return results


def _run_time_cli_title_vocabulary() -> Set[str]:
    """The true CLI title vocabulary: the union of BOTH emission forms."""
    kwarg_titles = {t for _, t in _extract_cli_titles()}
    rewrite_titles = {t for _, t in _extract_cli_rewrite_titles()}
    return kwarg_titles | rewrite_titles


# ---------------------------------------------------------------------------
# Group 1: extraction sanity + vacuous-pass guards
# ---------------------------------------------------------------------------


def test_evidence_extractor_finds_plausible_number_of_sites() -> None:
    sites = _extract_evidence_scoring_titles()
    assert len(sites) >= 3, (
        f"evidence.py scoring-title extractor found only {len(sites)} "
        "_finding_targets(...) call sites -- expected >= 3 (plaintext HTTP, "
        "HTTP-on-TLS-port, mTLS required). Either the AST walk is broken "
        "(a vacuous pass) or a site was genuinely removed; investigate "
        "before trusting the rest of this gate."
    )


def test_cli_rewrite_extractor_finds_plausible_number_of_sites() -> None:
    sites = _extract_cli_rewrite_titles()
    assert len(sites) >= 2, (
        f"CLI rewrite-form extractor found only {len(sites)} "
        'f["title"] = "..." sites in findings_evaluator.py -- expected >= 2 '
        "(mTLS required, HTTP on TLS-designated port). Investigate before "
        "trusting this gate."
    )


def test_cli_rewrite_extractor_sees_the_rewrite_only_title() -> None:
    """"HTTP on TLS-designated port" is emitted ONLY via the f["title"] =
    rewrite form. Proven two ways: (1) the rewrite extractor finds it, and
    (2) an INDEPENDENT method -- plain `grep -n` for the literal string --
    also finds it attached to an `f["title"]` (or `f['title']`) assignment.
    Also confirms the kwarg-only extractor genuinely does NOT see it, so
    this is demonstrably a distinct emission form, not redundant detection.
    """
    rewrite_titles = {t for _, t in _extract_cli_rewrite_titles()}
    assert "HTTP on TLS-designated port" in rewrite_titles, (
        "rewrite-form extractor did not find 'HTTP on TLS-designated port' "
        "-- the extractor's blind spot this gate exists to catch."
    )

    grep_result = subprocess.run(
        ["grep", "-n", "HTTP on TLS-designated port", str(_EVALUATOR_PY)],
        capture_output=True,
        text=True,
        check=True,
    )
    grep_lines = [
        line for line in grep_result.stdout.splitlines()
        if 'f["title"]' in line or "f['title']" in line
    ]
    assert grep_lines, (
        "independent grep cross-check found no f[\"title\"]-shaped line "
        "containing 'HTTP on TLS-designated port' -- the two methods "
        "disagree, which this project's rule treats as the finding, not "
        "as something to paper over."
    )

    kwarg_titles = {t for _, t in _extract_cli_titles()}
    assert "HTTP on TLS-designated port" not in kwarg_titles, (
        "the kwarg-form extractor unexpectedly saw 'HTTP on TLS-designated "
        "port' -- if a kwarg-form emission site was added for it, this "
        "title is no longer rewrite-only and this assertion (and the "
        "surrounding module docstring) should be revisited."
    )


# ---------------------------------------------------------------------------
# Group 2: ledger completeness gate (the core safeguard)
# ---------------------------------------------------------------------------


def test_every_evidence_scoring_title_is_dispositioned() -> None:
    """Adding a new title-matched counter to evidence.py without a
    disposition FAILS. A dispositioned title evidence.py no longer looks up
    also FAILS -- the ledger must track the code exactly, not accumulate
    stale rows.
    """
    sites = _extract_evidence_scoring_titles()
    extracted = {t for _, t in sites}
    disposed = set(SCORING_TITLE_DISPOSITIONS)

    missing_disposition = extracted - disposed
    assert not missing_disposition, (
        f"evidence.py looks up these titles via _finding_targets with NO "
        f"disposition in SCORING_TITLE_DISPOSITIONS: {missing_disposition} "
        "-- add a dispositioned entry in "
        "quirk/dashboard/api/finding_title_bridge.py before this gate can "
        "pass."
    )

    stale_disposition = disposed - extracted
    assert not stale_disposition, (
        f"SCORING_TITLE_DISPOSITIONS has entries for titles evidence.py no "
        f"longer looks up: {stale_disposition} -- remove the stale entry "
        "from quirk/dashboard/api/finding_title_bridge.py."
    )


def test_every_disposition_verdict_is_one_of_the_three_allowed() -> None:
    allowed = {"bridged", "endpoint-derived", "unbridgeable-latent-divergence"}
    for title, verdict in SCORING_TITLE_DISPOSITIONS.items():
        assert verdict in allowed, (
            f"{title!r} carries verdict {verdict!r}, not one of the three "
            f"allowed verdicts {allowed}."
        )


def test_every_bridged_disposition_has_a_dashboard_bridge_entry() -> None:
    bridge_values = set(DASHBOARD_TITLE_BRIDGE.values())
    for title, verdict in SCORING_TITLE_DISPOSITIONS.items():
        if verdict != "bridged":
            continue
        assert title in bridge_values, (
            f"{title!r} is dispositioned 'bridged' in "
            "SCORING_TITLE_DISPOSITIONS but does not appear as a value in "
            "DASHBOARD_TITLE_BRIDGE -- fix the disposition or add the "
            "bridge entry."
        )


def test_every_dispositioned_title_still_exists_in_cli_vocabulary() -> None:
    """A dispositioned title that the CLI generator stops emitting FAILS
    rather than rotting silently in the ledger.
    """
    cli_vocab = _run_time_cli_title_vocabulary()
    for title in SCORING_TITLE_DISPOSITIONS:
        assert title in cli_vocab, (
            f"{title!r} is dispositioned in SCORING_TITLE_DISPOSITIONS but "
            "no longer appears in the run-time-extracted CLI title "
            "vocabulary (kwarg form or rewrite form) -- either the CLI "
            "generator stopped emitting it (update/remove the disposition) "
            "or this gate's extractor has a new blind spot (investigate "
            "before assuming the former)."
        )


def test_unbridgeable_dispositions_name_a_real_evidence_counter() -> None:
    """Every unbridgeable-latent-divergence entry's cited counter must
    actually exist in build_evidence_summary's output, so the disposition
    cannot describe a counter that no longer exists. The mapping below is
    intentionally small and is itself gated by an exact-set-equality
    assertion against SCORING_TITLE_DISPOSITIONS' live content, so a new
    unbridgeable disposition added without updating this mapping FAILS
    loudly rather than being silently skipped.
    """
    # title -> the counter name its disposition comment in
    # finding_title_bridge.py names, kept in lockstep by the equality
    # assertion immediately below.
    known_counters = {
        "HTTP on TLS-designated port": "http_on_tls_port_count",
    }
    unbridgeable = {
        title
        for title, verdict in SCORING_TITLE_DISPOSITIONS.items()
        if verdict == "unbridgeable-latent-divergence"
    }
    assert unbridgeable == set(known_counters), (
        f"unbridgeable-latent-divergence titles {unbridgeable} do not match "
        f"this test's known-counter mapping {set(known_counters)} -- a new "
        "unbridgeable disposition was added (or removed) without updating "
        "this test. Verify the new entry's counter name against "
        "evidence.py directly, then update known_counters here."
    )

    summary = build_evidence_summary([], [])
    for title, counter in known_counters.items():
        assert counter in summary, (
            f"{title!r} is dispositioned unbridgeable-latent-divergence "
            f"citing counter {counter!r}, but build_evidence_summary()'s "
            "output carries no such key -- the disposition describes a "
            "counter that no longer exists; fix the comment in "
            "finding_title_bridge.py."
        )


# ---------------------------------------------------------------------------
# Group 3: translation identity over the full CLI vocabulary (211-02 guard)
# ---------------------------------------------------------------------------


def test_canonical_cli_title_is_identity_preserving_over_cli_vocabulary() -> None:
    """For every CLI title (kwarg form or rewrite form), canonical_cli_title
    must return either None or the exact same string back -- never a THIRD
    string. This is what keeps 211-02's dashboard->CLI translation from
    silently rewriting a genuine CLI title when handed one by accident (a
    CLI title is never meant to be passed through canonical_cli_title in
    production, but the function's own contract must hold regardless).
    """
    cli_vocab = _run_time_cli_title_vocabulary()
    assert len(cli_vocab) >= 10, (
        f"run-time CLI vocabulary union only has {len(cli_vocab)} titles -- "
        "expected >= 10 (kwarg-form alone already clears that bar per "
        "test_finding_title_bridge.py). Vacuous-pass guard; investigate "
        "before trusting this test."
    )
    for title in cli_vocab:
        translated = canonical_cli_title(title)
        assert translated in (None, title), (
            f"canonical_cli_title({title!r}) returned {translated!r} -- a "
            "THIRD string, neither None nor the input title back. This "
            "would silently rewrite a genuine CLI title, which is exactly "
            "what 211-02's translation must never do."
        )
