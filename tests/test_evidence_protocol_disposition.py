"""Run-time source scan protecting `_NON_ASSET_PROTOCOLS` (D-11, plan 184.1-03).

`{ADVISORY, CLOSED}` -- `quirk.intelligence.evidence._NON_ASSET_PROTOCOLS` -- is itself an
enumeration. This module exists so a *new* scanner protocol string cannot silently participate in
`coverage_ratio`'s denominator (D-06/D-07) without a human deliberately classifying it, and so a
future protocol that legitimately belongs in the exclusion set cannot be added to production code
without this gate noticing and demanding a matching disposition.

BINDING DESIGN CONSTRAINT (mirrors CLAUDE.md's "GSD `state.*` Verb Integrity" clause (b)/(h), and
`tests/test_gsd_state_patch.py::test_bold_field_regex_class_is_fully_dispositioned`, the primary
analog for this file -- see plan 182-07 / TOOL-04): the occurrence set below is GENERATED AT RUN
TIME by parsing the installed source tree with `ast.parse` -- it is NEVER seeded from a list
written into this file. `_PROTOCOL_DISPOSITIONS` supplies a *disposition* (`"asset"` /
`"non-asset"`) for whatever the scan finds; it must never supply the occurrences themselves. A gate
fed by a hand-written occurrence list is a hand-maintained allowlist wearing a test's clothes --
exactly the defect class TOOL-04 found three separate times in the same file.

Ledger keys are content-addressed -- `(relpath, literal_value, construction_shape)` -- and are
NEVER keyed on line number. `tests/test_skip_registry.py`'s `(file, LINENO)` keying is this repo's
own cautionary counter-example: seven of its rows broke on pure line drift from an unrelated
Phase 183 refactor (`STATE.md`, "183 (complete, 2026-09-04)"). Line numbers appear in this file
only inside human-facing failure messages, never inside a dict key.

Zero DB, zero Docker dependency (D-11 explicitly rejects asserting against the live
`quirk-output/quirk.db`: CI has no such DB, so that would degrade to an honest skip, and a skip is
not a pass).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from quirk.intelligence.evidence import _NON_ASSET_PROTOCOLS

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Scan roots (D-11 / RESEARCH.md Pattern 2). Globbed at call time -- `root` is a parameter, not a
# module-level constant baked into the scan function, specifically so the falsifiability self-test
# below can point the real scanner at a throwaway `tmp_path` tree and prove the derivation
# property itself, not merely the detector logic (mirrors
# `tests/test_cli_helper_usage.py::_derive_test_files`'s `root` parameter).
_SCAN_ROOT_SPECS: tuple[tuple[str, str], ...] = (
    ("quirk/scanner", "**/*.py"),
    ("quirk/cbom", "writer.py"),
    ("quirk/util", "optional_extra.py"),
)


def _scan_files(root: Path) -> list[Path]:
    """Every `.py` file under *root* matching one of the three scan-root specs, discovered by
    globbing at call time. Missing directories/files are tolerated (a synthetic `tmp_path` tree in
    the falsifiability self-test below has none of the real subdirectories)."""
    files: list[Path] = []
    for subdir, pattern in _SCAN_ROOT_SPECS:
        base = root / subdir
        if not base.exists():
            continue
        if pattern == "**/*.py":
            files.extend(sorted(base.glob(pattern)))
        else:
            candidate = base / pattern
            if candidate.exists():
                files.append(candidate)
    return files


class _ProtocolOccurrence:
    __slots__ = ("relpath", "value", "shape", "lineno", "construct")

    def __init__(self, relpath: str, value: str, shape: str, lineno: int, construct: str) -> None:
        self.relpath = relpath
        self.value = value
        self.shape = shape
        self.lineno = lineno
        self.construct = construct

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.relpath, self.value, self.shape)


def _module_level_string_constants(tree: ast.Module) -> dict[str, str]:
    """`NAME = "literal"` assignments at module scope, e.g.
    `quirk/scanner/codesign_scanner.py`'s `CODE_SIGNING = "CODE_SIGNING"`. Resolving these lets the
    keyword_literal shape below see `protocol=CODE_SIGNING` (a Name reference) as the literal it
    actually is, rather than silently dropping it -- the same kind of blind spot D-11 exists to
    catch, just one level removed from a bare string constant."""
    consts: dict[str, str] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            consts[node.targets[0].id] = node.value.value
    return consts


def _scan_one_file(path: Path, relpath: str) -> list[_ProtocolOccurrence]:
    occurrences: list[_ProtocolOccurrence] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return occurrences

    consts = _module_level_string_constants(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)

            # Shape 1: keyword_literal -- an `ast.keyword` named "protocol" on ANY call, whose
            # value is a string constant (resolving a same-module NAME reference, see above).
            for kw in node.keywords:
                if kw.arg != "protocol":
                    continue
                value: str | None = None
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    value = kw.value.value
                elif isinstance(kw.value, ast.Name) and kw.value.id in consts:
                    value = consts[kw.value.id]
                if value:
                    occurrences.append(
                        _ProtocolOccurrence(
                            relpath, value, "keyword_literal", node.lineno,
                            f"{func_name or '<call>'}(protocol=...)",
                        )
                    )

            # Shape 2: positional_arg -- `Fingerprint(is_open, proto, detail=...)`. `proto` is the
            # dataclass's second positional field (documented at fingerprint.py:13). A
            # `protocol="` regex finds ZERO of these -- this is the shape "CLOSED" (the single
            # largest-volume protocol string in the DB, per 184.1-RESEARCH.md) uses exclusively.
            if func_name == "Fingerprint" and len(node.args) >= 2:
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    occurrences.append(
                        _ProtocolOccurrence(
                            relpath, arg.value, "positional_arg", node.lineno,
                            "Fingerprint(<is_open>, proto, ...)",
                        )
                    )

    # Shape 3: table_assigned_variable -- a module-level tuple/list literal named EMAIL_PORTS,
    # whose second tuple element feeds `protocol_label` and is later assigned via
    # `ep.protocol = protocol_label` / `CryptoEndpoint(..., protocol=protocol_label)`
    # (email_scanner.py:386,496). A `protocol="` regex finds none of these six literals -- they
    # never appear next to the word "protocol" at all. Special-cased by name: EMAIL_PORTS is the
    # only such table across quirk/scanner/** as of this plan. GENERALISATION RISK: a future
    # scanner author could introduce a differently-named table feeding a `.protocol` assignment
    # the same way and this scan would be blind to it -- if that happens, widen this special case
    # rather than assuming EMAIL_PORTS remains unique forever.
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "EMAIL_PORTS"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            for elt in node.value.elts:
                if isinstance(elt, ast.Tuple) and len(elt.elts) >= 2:
                    v = elt.elts[1]
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        occurrences.append(
                            _ProtocolOccurrence(
                                relpath, v.value, "table_assigned_variable", node.lineno,
                                "EMAIL_PORTS[i][1]",
                            )
                        )

    return occurrences


def _scan_protocol_occurrences(root: Path) -> list[_ProtocolOccurrence]:
    occurrences: list[_ProtocolOccurrence] = []
    for path in _scan_files(root):
        try:
            relpath = str(path.relative_to(root))
        except ValueError:
            relpath = str(path)
        occurrences.extend(_scan_one_file(path, relpath))
    return occurrences


# ---------------------------------------------------------------------------
# Disposition ledger. Populated from this scan's REAL output (run against the
# live tree, then classified) -- not pre-populated from plan prose. Every
# `ADVISORY` / `CLOSED` row is "non-asset"; every genuine assessed protocol is
# "asset". `disposition` is exactly "asset" or "non-asset" -- D-11's own
# vocabulary -- deliberately NOT reusing "anchored" / "accepted-read-only",
# which are specific to the unrelated bold-field defect class.
# ---------------------------------------------------------------------------

_NON_ASSET_REASON = (
    "D-06/D-07: scanner self-report / non-probe pseudo-endpoint, excluded from "
    "coverage_ratio's denominator -- not a scanned asset."
)
_ASSET_REASON = "A genuine scanned asset/protocol; counted in coverage_ratio's denominator."

_PROTOCOL_DISPOSITIONS: dict[tuple[str, str, str], tuple[str, str]] = {
    # --- non-asset (D-06/D-07 exclusion set) ---
    ("quirk/cbom/writer.py", "ADVISORY", "keyword_literal"): ("non-asset", _NON_ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "ADVISORY", "keyword_literal"): ("non-asset", _NON_ASSET_REASON),
    ("quirk/scanner/jwt_scanner.py", "ADVISORY", "keyword_literal"): ("non-asset", _NON_ASSET_REASON),
    ("quirk/scanner/saml_scanner.py", "ADVISORY", "keyword_literal"): ("non-asset", _NON_ASSET_REASON),
    ("quirk/util/optional_extra.py", "ADVISORY", "keyword_literal"): ("non-asset", _NON_ASSET_REASON),
    ("quirk/scanner/fingerprint.py", "CLOSED", "positional_arg"): ("non-asset", _NON_ASSET_REASON),
    # --- asset (everything else the scan actually finds) ---
    ("quirk/scanner/adcs_scanner.py", "ADCS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/aws_connector.py", "AWS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/aws_connector.py", "KUBERNETES", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/aws_connector.py", "RDS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/aws_connector.py", "S3", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/azure_connector.py", "AZURE", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/azure_connector.py", "AZURE_BLOB", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "AMQP-PLAIN", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "KAFKA-PLAIN", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "KAFKA-TLS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "REDIS-PLAIN", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/broker_scanner.py", "REDIS-TLS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/codesign_scanner.py", "CODE_SIGNING", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/container_scanner.py", "CONTAINER", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/db_connector.py", "MYSQL", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/db_connector.py", "POSTGRESQL", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/dnssec_scanner.py", "DNSSEC", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "IMAP-STARTTLS", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "IMAPS", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "POP3-STARTTLS", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "POP3S", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "SMTP-STARTTLS", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/email_scanner.py", "SMTPS", "table_assigned_variable"): ("asset", _ASSET_REASON),
    ("quirk/scanner/fingerprint.py", "HTTP", "positional_arg"): ("asset", _ASSET_REASON),
    ("quirk/scanner/fingerprint.py", "SSH", "positional_arg"): ("asset", _ASSET_REASON),
    ("quirk/scanner/fingerprint.py", "TLS", "positional_arg"): ("asset", _ASSET_REASON),
    (
        "quirk/scanner/fingerprint.py", "UNKNOWN", "positional_arg",
    ): (
        "asset",
        "D-09: UNKNOWN is excluded from coverage_ratio's NUMERATOR but stays in the "
        "DENOMINATOR (mirrors D-05's scan_error handling) -- it is a reached, assessable "
        "endpoint that yielded no crypto result, not a non-probe pseudo-endpoint like "
        "ADVISORY/CLOSED. This ledger's asset/non-asset axis tracks denominator membership, "
        "which is why UNKNOWN is 'asset' here even though it is excluded elsewhere.",
    ),
    ("quirk/scanner/gcp_connector.py", "CLOUD_SQL", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/gcp_connector.py", "GCP", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/jwt_scanner.py", "JWT", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/k8s_connector.py", "KUBERNETES", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/kerberos_scanner.py", "KERBEROS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/openapi_scanner.py", "OPENAPI", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/rest_fuzzer.py", "REST_FUZZ", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/saml_scanner.py", "SAML", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/smime_scanner.py", "SMIME", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/source_scanner.py", "SOURCE", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/ssh_scanner.py", "SSH", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/tls_scanner.py", "TLS", "keyword_literal"): ("asset", _ASSET_REASON),
    ("quirk/scanner/vault_connector.py", "VAULT", "keyword_literal"): ("asset", _ASSET_REASON),
}

_VALID_DISPOSITIONS = frozenset({"asset", "non-asset"})


# ---------------------------------------------------------------------------
# Failure mode 1: every occurrence the scan finds must carry a ledger entry.
# ---------------------------------------------------------------------------


def test_every_protocol_literal_is_dispositioned() -> None:
    occurrences = _scan_protocol_occurrences(_REPO_ROOT)
    assert occurrences, "the run-time scan collected zero protocol-literal occurrences at all"

    for occ in occurrences:
        assert occ.key in _PROTOCOL_DISPOSITIONS, (
            f"undispositioned protocol literal found by the run-time scan: "
            f"file={occ.relpath!r} value={occ.value!r} shape={occ.shape!r} "
            f"(construct: {occ.construct}, line {occ.lineno}). "
            f"Disposition it deliberately in _PROTOCOL_DISPOSITIONS as 'asset' or "
            f"'non-asset' with a written reason -- do not add it reflexively just to "
            f"satisfy this assertion."
        )
        disposition, reason = _PROTOCOL_DISPOSITIONS[occ.key]
        assert disposition in _VALID_DISPOSITIONS, (
            f"unknown disposition {disposition!r} for {occ.key} -- must be 'asset' or "
            f"'non-asset'"
        )
        assert reason.strip(), f"ledger entry {occ.key} has an empty reason"


# ---------------------------------------------------------------------------
# Failure mode 2: every ledger entry must match a real occurrence.
# ---------------------------------------------------------------------------


def test_no_stale_disposition_rows() -> None:
    occurrences = _scan_protocol_occurrences(_REPO_ROOT)
    matched_keys = {occ.key for occ in occurrences}
    stale = set(_PROTOCOL_DISPOSITIONS) - matched_keys
    assert not stale, (
        "ledger entries with no matching occurrence in the installed source -- a stale "
        f"allowlist row is how a gate quietly stops gating anything: {sorted(stale)}"
    )


# ---------------------------------------------------------------------------
# Failure mode 3: the scan must not be blind to any root or construction shape.
# ---------------------------------------------------------------------------


def test_scan_is_not_blind_to_any_shape_or_root() -> None:
    occurrences = _scan_protocol_occurrences(_REPO_ROOT)

    by_shape: dict[str, int] = {}
    for occ in occurrences:
        by_shape[occ.shape] = by_shape.get(occ.shape, 0) + 1

    for shape in ("keyword_literal", "positional_arg", "table_assigned_variable"):
        assert by_shape.get(shape, 0) > 0, (
            f"the run-time scan collected ZERO occurrences of the {shape!r} construction "
            f"shape. A scanner tuned for only one shape is blind to the others -- e.g. a "
            f"bare `protocol=\"` regex finds zero of fingerprint.py's positional "
            f"`Fingerprint(False, \"CLOSED\", ...)` calls and zero of email_scanner.py's "
            f"EMAIL_PORTS table-driven `protocol_label` assignments. Fix the scan's shape "
            f"detection, not the ledger."
        )

    by_root: dict[str, int] = {}
    for occ in occurrences:
        root_label = occ.relpath.split("/", 1)[0]
        by_root[root_label] = by_root.get(root_label, 0) + 1

    for subdir, _pattern in _SCAN_ROOT_SPECS:
        root_label = subdir.split("/", 1)[0]
        assert by_root.get(root_label, 0) > 0, (
            f"the run-time scan collected ZERO occurrences from scan root {subdir!r}. "
            f"Either that root's source no longer emits any protocol literal (update "
            f"_SCAN_ROOT_SPECS deliberately) or the scan has gone blind to that root -- "
            f"fix the scan, not the ledger."
        )


# ---------------------------------------------------------------------------
# Cross-check: the ledger's non-asset set must equal the production constant exactly.
# ---------------------------------------------------------------------------


def test_ledger_non_assets_match_production_exclusion_set() -> None:
    ledger_non_assets = {
        value for (_relpath, value, _shape), (disposition, _reason) in _PROTOCOL_DISPOSITIONS.items()
        if disposition == "non-asset"
    }
    assert ledger_non_assets == set(_NON_ASSET_PROTOCOLS), (
        f"the ledger's 'non-asset' literals {sorted(ledger_non_assets)} do not exactly "
        f"match quirk.intelligence.evidence._NON_ASSET_PROTOCOLS "
        f"{sorted(_NON_ASSET_PROTOCOLS)}. This is the link that makes this gate protect "
        f"the production constant rather than a parallel, driftable copy of it."
    )


# ---------------------------------------------------------------------------
# Falsifiability self-test: proves the gate is not vacuously passing.
# ---------------------------------------------------------------------------


def test_new_unlisted_protocol_is_caught_without_ledger_edit(tmp_path: Path) -> None:
    """Point the real scanner's `root` parameter at a throwaway `tmp_path` tree containing a
    brand-new, never-seen protocol literal, and confirm it is caught -- proving the derivation
    property itself, not just the detector logic (mirrors
    `tests/test_cli_helper_usage.py::test_new_unlisted_file_is_caught_without_list_edit`)."""
    scanner_dir = tmp_path / "quirk" / "scanner"
    scanner_dir.mkdir(parents=True)
    (scanner_dir / "synthetic_scanner.py").write_text(
        "from quirk.models import CryptoEndpoint\n\n"
        "def probe(host, port):\n"
        "    return CryptoEndpoint(host=host, port=port, protocol=\"FICTIONAL\")\n"
    )

    occurrences = _scan_protocol_occurrences(tmp_path)
    keys = {occ.key for occ in occurrences}

    assert ("quirk/scanner/synthetic_scanner.py", "FICTIONAL", "keyword_literal") in keys, (
        "derivation missed a brand-new protocol literal in a never-seen file"
    )
    assert (
        "quirk/scanner/synthetic_scanner.py", "FICTIONAL", "keyword_literal"
    ) not in _PROTOCOL_DISPOSITIONS, (
        "the synthetic literal must NOT already carry a ledger entry -- otherwise this "
        "self-test proves nothing"
    )


def test_deleted_ledger_row_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """Companion falsifiability proof: removing a real ledger row must fail
    `test_every_protocol_literal_is_dispositioned`'s underlying assertion -- proving the gate can
    still fail, not just that it currently passes."""
    trimmed = dict(_PROTOCOL_DISPOSITIONS)
    victim_key = ("quirk/scanner/tls_scanner.py", "TLS", "keyword_literal")
    assert victim_key in trimmed, "fixture assumption stale -- re-derive the victim key"
    del trimmed[victim_key]
    monkeypatch.setattr(
        "tests.test_evidence_protocol_disposition._PROTOCOL_DISPOSITIONS", trimmed
    )

    occurrences = _scan_protocol_occurrences(_REPO_ROOT)
    undispositioned = [occ for occ in occurrences if occ.key not in trimmed]
    assert any(occ.key == victim_key for occ in undispositioned), (
        "deleting the TLS/tls_scanner.py/keyword_literal ledger row did not surface as an "
        "undispositioned occurrence -- the gate would not actually catch a stale-row deletion"
    )
