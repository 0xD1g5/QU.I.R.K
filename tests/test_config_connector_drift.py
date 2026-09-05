"""Phase 184.2 D-09/D-10/D-15: derived drift gate for `ConnectorsCfg` keys.

Owns the shared derivation this phase needs across every config surface and
every programmatic config generator, so Plans 03 and 04 import from here
rather than recomputing a second, divergent derivation.

Two directions, both derived at test-run time (never from a written list),
per CLAUDE.md's "GSD `state.*` Verb Integrity" clause (e): "a written list of
known sites is not a safeguard."

1. D-09/D-10 -- every `connectors:` key in every git-tracked YAML config with
   a top-level `connectors:` block must be a real `ConnectorsCfg` field. The
   file SET is discovered via `git ls-files` + `yaml.safe_load` at call time
   -- no path literal anywhere in this module. As of 2026-09-04 this
   resolves to four files: `config.yaml`, `docs/sample-config.yaml`,
   `lab-registry.yaml`, and `quirk/config_template.yaml`. `lab-registry.yaml`
   is not hand-listed anywhere -- it is caught purely because its document
   body (indented two spaces) still parses to a top-level `connectors:`
   mapping key under `yaml.safe_load`. A regex anchored on `^connectors:`
   would silently miss it; that is exactly the blindness this gate exists to
   prevent, so this module never uses one.

2. D-15 -- every `ConnectorsCfg(...)` keyword argument, every dict-literal
   string key assigned to a variable named `connectors_block`/`connectors`,
   and every `<obj>.connectors.<attr> = ...` attribute assignment in
   `quirk/interactive.py` and `quirk/dashboard/api/routes/jobs.py` must name
   a real `ConnectorsCfg` field. Uses `ast.parse` + `ast.walk`, never a
   regex over source text -- `enable_` legitimately appears in docstrings
   and comments in both files and would false-positive on a text scan (the
   same rationale already written into `tests/test_cli_helper_usage.py`).

Both directions reuse the identical `_connector_field_names()` expression
`quirk/config.py:444` already uses (`_KNOWN_CONNECTOR_KEYS`) -- the loader,
the D-10 gate, and the D-15 AST gate can never disagree about what a valid
connector key is.

Every gate here carries a convention-blindness guard (an empty diff must
never be silently readable as "everything is fine") and at least one
permanent self-test proving the *derivation* -- not merely the detector
logic -- catches a brand-new, never-before-seen violation with zero list
edits anywhere.
"""
from __future__ import annotations

import ast
import dataclasses
import shutil
from pathlib import Path

import yaml

import quirk.dashboard.api.routes.jobs
import quirk.interactive
from quirk.config import ConnectorsCfg
from tests.cli_helpers import run_fork_safe

_REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Shared field-set derivation (D-09) -- identical expression to
# quirk/config.py:444's `_KNOWN_CONNECTOR_KEYS`, so loader and gate can never
# disagree about what a valid connector key is.
# ---------------------------------------------------------------------------


def _connector_field_names() -> set[str]:
    """Return every real `ConnectorsCfg` field name, derived at call time
    from `dataclasses.fields(ConnectorsCfg)` -- the exact same expression
    `quirk/config.py:444` uses to build `_KNOWN_CONNECTOR_KEYS`. Never a
    second, hand-copied set."""
    return {f.name for f in dataclasses.fields(ConnectorsCfg)}


# ---------------------------------------------------------------------------
# D-10: derived YAML file set. No path literal anywhere below -- the set is
# discovered fresh on every test run via `git ls-files` + `yaml.safe_load`.
# ---------------------------------------------------------------------------


def _derive_connector_config_files(root: Path = _REPO_ROOT) -> list[Path]:
    """Return every git-tracked `*.yaml`/`*.yml` file under *root* whose
    parsed document is a mapping with a top-level `connectors:` key that is
    itself a mapping, discovered at call time via `git ls-files` (never a
    hand-maintained list).

    `root` is a parameter (not hidden behind a hardcoded repo-root constant
    only) specifically so the falsifiability self-test below can point this
    same derivation at a throwaway `tmp_path` git repo and prove the
    derivation property itself, not merely the detector logic.

    Uses `yaml.safe_load`, never a `^connectors:`-anchored regex --
    `lab-registry.yaml`'s document body is indented two spaces and a
    line-anchored regex would silently miss it, which is the exact class of
    blindness this gate exists to prevent.
    """
    git_exe = shutil.which("git")
    if not git_exe:
        raise AssertionError("git executable not found on PATH")
    result = run_fork_safe(
        [git_exe, "-C", str(root), "ls-files", "*.yaml", "*.yml"], check=True
    )
    tracked = [line for line in result.stdout.splitlines() if line.strip()]

    out: list[Path] = []
    for rel in tracked:
        path = root / rel
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise AssertionError(
                f"{rel}: could not parse as YAML for the connector drift gate: {exc}"
            ) from exc
        if isinstance(data, dict) and isinstance(data.get("connectors"), dict):
            out.append(path)
    return sorted(out)


def _connector_key_problems_for_file(
    path: Path, label: str, known_keys: set[str]
) -> list[str]:
    """Return 'label: unknown connector key ...' strings for every key in
    *path*'s `connectors:` block that is not in *known_keys*. Pure function
    over a single file so both the real gate and the self-tests below (which
    point it at a hand-written or tmp_path file) go through identical
    checking logic."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    connectors = data.get("connectors") if isinstance(data, dict) else None
    if not isinstance(connectors, dict):
        return []
    unknown = sorted(set(connectors) - known_keys)
    return [
        f"{label}: unknown connector key {key!r} is not a real ConnectorsCfg field"
        for key in unknown
    ]


# ---------------------------------------------------------------------------
# Grandfather ledger -- ships EMPTY. Phase 184.2 planning found no legitimate
# grandfathering candidate for D-09/D-10 (unlike D-15's second-surface check,
# which has none either as of this plan). Because it ships empty, a test
# that merely loops over `_GRANDFATHERED.items()` would pass vacuously
# forever without ever exercising its own failure modes against real data --
# which is precisely why `test_grandfathered_entries_are_current` also runs
# the identical validation helper against a synthetic stale entry below.
# ---------------------------------------------------------------------------

_GRANDFATHERED: dict[str, str] = {}


def _validate_grandfather_ledger(ledger: dict[str, str]) -> list[str]:
    """Return problem descriptions for *ledger* -- a blank reason, or a key
    naming a file that no longer exists under `_REPO_ROOT`. Empty return
    means the ledger is clean."""
    problems: list[str] = []
    for relpath, reason in ledger.items():
        if not reason.strip():
            problems.append(f"{relpath}: blank grandfather reason")
        if not (_REPO_ROOT / relpath).exists():
            problems.append(
                f"{relpath}: grandfathered but no longer exists on disk -- "
                "remove the stale entry"
            )
    return problems


def test_grandfathered_entries_are_current() -> None:
    """`_GRANDFATHERED` ships EMPTY, so looping over it alone is vacuous.
    The synthetic case below is load-bearing: it proves
    `_validate_grandfather_ledger` actually catches a stale key against real
    data, since the empty real ledger gives that failure mode zero
    real-data coverage."""
    real_problems = _validate_grandfather_ledger(_GRANDFATHERED)
    assert not real_problems, real_problems

    assert _GRANDFATHERED == {}, (
        "Phase 184.2 planning found no legitimate D-09/D-10 grandfathering "
        "candidate -- do not add one reflexively just to satisfy a failing "
        "assertion elsewhere in this module."
    )

    stale_key_problems = _validate_grandfather_ledger(
        {"does_not_exist.yaml": "a reason that would otherwise be fine"}
    )
    assert stale_key_problems, (
        "_validate_grandfather_ledger failed to flag a key naming a file "
        "that does not exist on disk"
    )
    assert any("no longer exists on disk" in p for p in stale_key_problems)

    blank_reason_problems = _validate_grandfather_ledger({'config.yaml': "  "})
    assert blank_reason_problems, (
        "_validate_grandfather_ledger failed to flag a blank grandfather reason"
    )
    assert any("blank grandfather reason" in p for p in blank_reason_problems)


# ---------------------------------------------------------------------------
# D-09/D-10 main gate
# ---------------------------------------------------------------------------


def test_every_connector_key_in_every_discovered_config_is_a_real_field() -> None:
    """Every `connectors:` key in every derived config file must be a real
    `ConnectorsCfg` field.

    Convention-blindness guard: fails loudly if the field set or the file
    set comes back implausibly small -- an empty diff must never be
    readable as "everything is fine" when the derivation itself is broken.
    """
    known_keys = _connector_field_names()
    assert len(known_keys) >= 20, (
        f"_connector_field_names() returned only {len(known_keys)} fields -- "
        "this is implausibly small for ConnectorsCfg and suggests the "
        "dataclasses.fields() derivation is broken, not that the schema "
        "shrank. An empty/tiny diff here must not be trusted."
    )

    files = _derive_connector_config_files()
    assert len(files) >= 2, (
        f"_derive_connector_config_files() found only {len(files)} file(s) -- "
        "this is implausibly small; the git ls-files / yaml.safe_load "
        "derivation itself may be broken. An empty diff here must not be "
        "trusted as 'everything is fine'."
    )

    problems: list[str] = []
    for path in files:
        label = str(path.relative_to(_REPO_ROOT))
        if label in _GRANDFATHERED:
            continue
        problems.extend(_connector_key_problems_for_file(path, label, known_keys))

    assert not problems, (
        f"unknown connector key(s) found in tracked config file(s): {problems}. "
        "Either the key is a typo (fix the YAML) or the field is genuinely "
        "new and ConnectorsCfg needs the field added (Phase 184.2 D-09)."
    )


def test_derived_file_set_includes_lab_registry_with_no_hardcoded_path() -> None:
    """Locks the phase's own stated finding: the derivation resolves to
    FOUR files today, including `lab-registry.yaml`, which is discovered
    purely because `yaml.safe_load` sees its (two-space-indented) top-level
    `connectors:` key -- not because any path literal names it."""
    files = _derive_connector_config_files()
    names = sorted(p.name for p in files)
    assert 'lab-registry.yaml' in names, names
    assert len(files) >= 4, names


def test_gate_catches_synthetic_bogus_connector_key(tmp_path: Path) -> None:
    """Detector-logic self-test (hand-supplied file): a bogus connectors key
    written into a throwaway file is reported by name."""
    bogus = tmp_path / "bogus_config.yaml"
    bogus.write_text("connectors:\n  enable_bogus_planted: false\n", encoding="utf-8")

    problems = _connector_key_problems_for_file(
        bogus, "bogus_config.yaml", _connector_field_names()
    )

    assert problems, "gate failed to flag a synthetic bogus connector key"
    assert any("enable_bogus_planted" in p for p in problems), problems


def test_new_unlisted_config_file_is_caught_without_list_edit(tmp_path: Path) -> None:
    """Proves the DERIVATION property itself, not just the detector: point
    the real `_derive_connector_config_files` at a throwaway git repo
    containing a brand-new, never-seen YAML filename with a bogus
    `connectors:` key, and confirm it is caught with NO edit to any list,
    anywhere, of any kind.

    Must go through `_derive_connector_config_files(root=tmp_path)` --
    calling `_connector_key_problems_for_file` directly on a hand-supplied
    path (as the self-test above does) would silently reduce this to a
    duplicate of that test and would no longer prove the `git ls-files`
    derivation mechanism works at all.
    """
    git_exe = shutil.which("git")
    if not git_exe:
        raise AssertionError("git executable not found on PATH")
    run_fork_safe([git_exe, "-C", str(tmp_path), "init", "-q"], check=True)
    new_file = tmp_path / "never_seen_before_config.yaml"
    new_file.write_text(
        "connectors:\n  enable_totally_new_bogus: false\n", encoding="utf-8"
    )
    run_fork_safe(
        [git_exe, "-C", str(tmp_path), "add", "never_seen_before_config.yaml"],
        check=True,
    )

    files = _derive_connector_config_files(root=tmp_path)
    assert any(p.name == "never_seen_before_config.yaml" for p in files), files

    known_keys = _connector_field_names()
    problems: list[str] = []
    for path in files:
        problems.extend(
            _connector_key_problems_for_file(path, path.name, known_keys)
        )

    assert problems, "derivation missed a brand-new file with no ledger entry"
    assert any("enable_totally_new_bogus" in p for p in problems), problems


# ---------------------------------------------------------------------------
# D-15: AST checks on the two programmatic config generators.
# ---------------------------------------------------------------------------

_CONNECTORS_DICT_TARGET_NAMES = {"connectors_block", "connectors"}


def _scan_connector_ast(
    tree: ast.AST, label: str, known_keys: set[str]
) -> tuple[int, list[str]]:
    """Walk *tree* (an `ast.parse` result) and return
    `(occurrence_count, problems)` where *occurrence_count* is the number of
    connector-key-shaped constructs found (regardless of validity) and
    *problems* names every one that is NOT a real `ConnectorsCfg` field.

    Three node shapes are checked, all via `ast.walk` -- never a regex over
    source text, since `enable_` legitimately appears in docstrings/comments
    in both target files and would false-positive on a text scan:

    1. `ConnectorsCfg(...)` call sites -- every `ast.keyword.arg` (ALL
       kwargs, not just `enable_*` ones -- a stale `container_target` typo
       is the same bug class as a stale `enable_*` typo).
    2. Dict literals assigned to a name in `{"connectors_block",
       "connectors"}` -- every `ast.Constant` string key.
    3. `<obj>.connectors.<attr> = ...` attribute assignments -- the `<attr>`
       name (catches `quirk/interactive.py`'s
       `cfg.connectors.enable_nmap = ...` post-construction write).
    """
    occurrences = 0
    problems: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            is_connectors_cfg_call = (
                isinstance(func, ast.Name) and func.id == "ConnectorsCfg"
            ) or (isinstance(func, ast.Attribute) and func.attr == "ConnectorsCfg")
            if is_connectors_cfg_call:
                for kw in node.keywords:
                    if kw.arg is None:  # **kwargs spread -- nothing to name
                        continue
                    occurrences += 1
                    if kw.arg not in known_keys:
                        problems.append(
                            f"{label}:{node.lineno}: ConnectorsCfg(...) kwarg "
                            f"{kw.arg!r} is not a real ConnectorsCfg field"
                        )

        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Dict):
                target_names = {
                    t.id for t in node.targets if isinstance(t, ast.Name)
                }
                if target_names & _CONNECTORS_DICT_TARGET_NAMES:
                    for key_node in node.value.keys:
                        if isinstance(key_node, ast.Constant) and isinstance(
                            key_node.value, str
                        ):
                            occurrences += 1
                            if key_node.value not in known_keys:
                                problems.append(
                                    f"{label}:{node.lineno}: dict literal key "
                                    f"{key_node.value!r} assigned to "
                                    f"{'/'.join(sorted(target_names))} is not "
                                    "a real ConnectorsCfg field"
                                )

            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Attribute)
                    and target.value.attr == "connectors"
                ):
                    occurrences += 1
                    if target.attr not in known_keys:
                        problems.append(
                            f"{label}:{node.lineno}: attribute assignment "
                            f".connectors.{target.attr} is not a real "
                            "ConnectorsCfg field"
                        )

    return occurrences, problems


def _generator_modules() -> dict[str, Path]:
    """The two programmatic config generators, derived from importable
    module objects (not string paths) so a module move is caught at import
    time rather than passing vacuously against a missing file."""
    return {
        "quirk/interactive.py": Path(quirk.interactive.__file__),
        "quirk/dashboard/api/routes/jobs.py": Path(
            quirk.dashboard.api.routes.jobs.__file__
        ),
    }


def test_connector_ast_usage_in_generators_matches_real_fields() -> None:
    """Every `ConnectorsCfg(...)` kwarg, every connectors dict-literal key,
    and every `.connectors.<attr>` assignment in the two programmatic config
    generators must name a real `ConnectorsCfg` field.

    Convention-blindness guard: fails if either source file yields ZERO
    occurrences -- a scan that cannot see its own target must not read as a
    pass.
    """
    known_keys = _connector_field_names()
    zero_occurrence_files: list[str] = []
    all_problems: list[str] = []

    for label, path in _generator_modules().items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=label)
        occurrences, problems = _scan_connector_ast(tree, label, known_keys)
        if occurrences == 0:
            zero_occurrence_files.append(label)
        all_problems.extend(problems)

    assert not zero_occurrence_files, (
        f"the AST scan collected ZERO connector occurrences from: "
        f"{zero_occurrence_files} -- a scan that cannot see its own target "
        "must not silently read as a pass. Check the node-shape predicates "
        "in _scan_connector_ast against the current source."
    )
    assert not all_problems, all_problems


def test_ast_gate_catches_synthetic_bogus_connectorscfg_kwarg() -> None:
    """Self-test: a synthetic `ConnectorsCfg(enable_totally_bogus=True)` call
    is reported by the same checking function used against the real
    files."""
    tree = ast.parse("cfg = ConnectorsCfg(enable_totally_bogus=True)\n")
    occurrences, problems = _scan_connector_ast(
        tree, "synthetic.py", _connector_field_names()
    )
    assert occurrences >= 1
    assert any("enable_totally_bogus" in p for p in problems), problems


def test_ast_gate_catches_synthetic_bogus_dict_literal_key() -> None:
    """Self-test: a synthetic `connectors_block = {"enable_nope": False}` is
    reported by the same checking function used against the real files."""
    tree = ast.parse('connectors_block = {"enable_nope": False}\n')
    occurrences, problems = _scan_connector_ast(
        tree, "synthetic.py", _connector_field_names()
    )
    assert occurrences >= 1
    assert any("enable_nope" in p for p in problems), problems


def test_ast_gate_catches_synthetic_bogus_attribute_assignment() -> None:
    """Self-test: a synthetic `cfg.connectors.enable_totally_fake = True` is
    reported by the same checking function used against the real files."""
    tree = ast.parse("cfg.connectors.enable_totally_fake = True\n")
    occurrences, problems = _scan_connector_ast(
        tree, "synthetic.py", _connector_field_names()
    )
    assert occurrences >= 1
    assert any("enable_totally_fake" in p for p in problems), problems


# ---------------------------------------------------------------------------
# Phase 184.2 Plan 03: D-09 completeness gate, D-06 vocabulary gate, D-18
# advisory-pre-gate guard, and port parity -- all against the single shipped
# template `quirk/config_template.yaml`. Reuses `_connector_field_names()`
# above; introduces no second field-set derivation.
# ---------------------------------------------------------------------------

import re

from quirk.interactive import CONSULTING_TLS_PORTS
from quirk.util.optional_extra import REGISTRY

_TEMPLATE_PATH = _REPO_ROOT / "quirk" / "config_template.yaml"

# D-06's closed reason-tag vocabulary. This is a user decision specifying a
# CLOSED SET of five strings -- not a hand-maintained enumeration of code
# sites -- so writing it down here does not repeat the "written list with no
# proof" defect CLAUDE.md's GSD state.* clause (e) warns against; the *set
# membership* of any given tag is what the gate below verifies at run time.
_D06_VOCABULARY = frozenset(
    {
        "requires-credentials",
        "requires-targets",
        "requires-extra-install",
        "probes-live-equipment",
        "not-a-connector",
    }
)

# Matches one D-06-tagged live `enable_*` line, e.g.:
#   enable_aws: false  # off: requires-credentials - needs AWS_ACCESS_KEY_ID...
# The tag lives inside a YAML comment, which `yaml.safe_load` discards, so a
# text-level regex scan is required -- this is not recoverable from the
# parsed document.
_TAGGED_LINE_RE = re.compile(
    r"^[ \t]+(enable_[a-zA-Z0-9_]+):[ \t]+(true|false)[ \t]{2}#[ \t]"
    r"(on|off):[ \t]([a-z-]+)[ \t]-[ \t](.+)$",
    re.MULTILINE,
)


def _enable_field_names() -> set[str]:
    """Return only the `enable_*`-prefixed `ConnectorsCfg` fields (25 as of
    this plan) -- the D-09/D-06/D-18 gates below are scoped to enable flags
    only, unlike `_connector_field_names()` above which also covers
    target/credential sub-keys for the D-09/D-10 file-wide key gate."""
    return {k for k in _connector_field_names() if k.startswith("enable_")}


def _parse_tagged_lines(text: str) -> dict[str, tuple[bool, str, str, str]]:
    """Return `{field_name: (bool_value, prefix, tag, detail)}` for every
    D-06-tagged live `enable_*` line found via `_TAGGED_LINE_RE`. Pure
    function over raw text so both the real template and synthetic strings
    in the self-tests below go through identical parsing logic."""
    out: dict[str, tuple[bool, str, str, str]] = {}
    for m in _TAGGED_LINE_RE.finditer(text):
        key, value_str, prefix, tag, detail = m.groups()
        out[key] = (value_str == "true", prefix, tag, detail.strip())
    return out


def _completeness_problems(known_keys: set[str], tagged: dict) -> list[str]:
    """D-09: every real `ConnectorsCfg` `enable_*` field must have a live,
    D-06-tagged template key. A field with no tagged key fails, naming the
    field -- this is what lets a synthetic planted field be caught with zero
    edits to any enumerated list (see the self-test below)."""
    missing = sorted(known_keys - set(tagged))
    return [
        f"{name}: no live, D-06-tagged quirk/config_template.yaml key found "
        "for this ConnectorsCfg field (D-09)"
        for name in missing
    ]


def _vocabulary_problems(tagged: dict) -> list[str]:
    """D-06: prefix/value agreement, closed-vocabulary tag membership, and a
    minimum detail length/word-count for every tagged line."""
    problems: list[str] = []
    for key, (value, prefix, tag, detail) in tagged.items():
        expected_prefix = "on" if value else "off"
        if prefix != expected_prefix:
            problems.append(
                f"{key}: tag prefix {prefix!r} disagrees with boolean value "
                f"{value!r} (expected {expected_prefix!r}) -- a stale tag on "
                "a flipped value is a failure, not a formatting nit"
            )
        if tag not in _D06_VOCABULARY:
            problems.append(
                f"{key}: tag {tag!r} is not one of D-06's closed vocabulary "
                f"{sorted(_D06_VOCABULARY)}"
            )
        if len(detail) < 30 or len(detail.split()) < 5:
            problems.append(
                f"{key}: detail {detail!r} is shorter than the required "
                "30 characters / 5 whitespace-separated words"
            )
    return problems


def _armed_extras_hazard_problems(tagged: dict) -> list[str]:
    """D-18: no field shipping `true` in the template may appear in any
    `optional_extra.REGISTRY` entry's `enabled_attrs` -- that would emit
    INSTALL-001 on a stock default scan. The hazard set is unioned from
    REGISTRY at test-run time, never hardcoded (so a future extra registered
    against a currently-armed connector fails immediately, with no edit to
    this test)."""
    hazardous_attrs: set[str] = set()
    for entry in REGISTRY:
        hazardous_attrs.update(entry.enabled_attrs)
    problems: list[str] = []
    for key, (value, _prefix, _tag, _detail) in tagged.items():
        if value and key in hazardous_attrs:
            problems.append(
                f"{key}: ships true in the template but appears in "
                "optional_extra.REGISTRY's enabled_attrs -- would emit "
                "INSTALL-001 on every stock default scan (D-18)"
            )
    return problems


# `_NOT_A_CONNECTOR` is a disposition LEDGER, not a skip list: every entry
# names the real driver for a field that is NOT an armed connector (D-08's
# not-a-connector set is four, not three, per D-20). Checked in BOTH
# directions below -- a bare membership skip is exactly the "written list
# with no proof" defect CLAUDE.md's GSD state.* clause (e) warns against.
_NOT_A_CONNECTOR: dict[str, str] = {
    "enable_nmap": (
        "driven by the --discovery nmap CLI flag (run_scan.py), which "
        "overwrites this attribute at scan start"
    ),
    "enable_authenticated_mode": (
        "driven by the credential CLI flags (run_scan.py); the scheduler "
        "rejects configs where this is true (QRK-SCHED-AUTH-001)"
    ),
    "enable_recurring_otics": (
        "a scheduler safety gate for recurring Modbus/BACnet probing with a "
        "168h cadence floor, not a scanner toggle itself"
    ),
    "enable_codesign": (
        "driven by the --inventory-code-signing CLI flag (run_scan.py); "
        "setting this key changes zero scan behavior (D-20)"
    ),
}


def _not_a_connector_problems(known_keys: set[str], tagged: dict) -> list[str]:
    """Bidirectional ledger check: every ledger key must be a real field with
    a non-empty driver pointer (stale-entry direction), and every template
    field tagged `not-a-connector` must have a ledger entry (completeness
    direction)."""
    problems: list[str] = []
    for field, driver in _NOT_A_CONNECTOR.items():
        if field not in known_keys:
            problems.append(
                f"_NOT_A_CONNECTOR entry {field!r} is not a real "
                "ConnectorsCfg field -- stale ledger entry"
            )
        if not driver.strip():
            problems.append(
                f"_NOT_A_CONNECTOR entry {field!r} has a blank driver pointer"
            )
    for key, (_value, _prefix, tag, _detail) in tagged.items():
        if key in _NOT_A_CONNECTOR and tag != "not-a-connector":
            problems.append(
                f"{key}: ledgered in _NOT_A_CONNECTOR but the template tag "
                f"is {tag!r}, not 'not-a-connector'"
            )
        if tag == "not-a-connector" and key not in _NOT_A_CONNECTOR:
            problems.append(
                f"{key}: template tags this 'not-a-connector' but there is "
                "no _NOT_A_CONNECTOR ledger entry naming its real driver"
            )
    return problems


def test_template_connectors_are_complete_tagged_and_hazard_free() -> None:
    """The single combined D-09/D-06/D-18/not-a-connector-ledger gate against
    the real, shipped `quirk/config_template.yaml`.

    Convention-blindness guard: fails loudly if the field set or the tagged-
    line scan comes back implausibly small -- an empty diff must never be
    silently readable as "everything is fine" when a regex or derivation is
    broken.
    """
    known_keys = _enable_field_names()
    assert len(known_keys) >= 20, (
        f"_connector_field_names() returned only {len(known_keys)} fields -- "
        "implausibly small; the dataclasses.fields() derivation may be broken."
    )

    text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    tagged = _parse_tagged_lines(text)
    assert len(tagged) > 0, (
        "the D-06 tagged-line regex matched ZERO lines in "
        "quirk/config_template.yaml -- a scan that cannot see its own target "
        "must not silently read as a pass; check _TAGGED_LINE_RE against "
        "the current template formatting"
    )

    problems: list[str] = []
    problems.extend(_completeness_problems(known_keys, tagged))
    problems.extend(_vocabulary_problems(tagged))
    problems.extend(_armed_extras_hazard_problems(tagged))
    problems.extend(_not_a_connector_problems(known_keys, tagged))
    assert not problems, problems


def test_ports_tls_matches_consulting_tls_ports() -> None:
    """Port parity: `scan.ports_tls` in the shipped template must equal
    `CONSULTING_TLS_PORTS` (quirk/interactive.py) by value AND order, so a
    future edit to either surface without the other fails immediately. No
    literal 17-port list is written in this test."""
    data = yaml.safe_load(_TEMPLATE_PATH.read_text(encoding="utf-8"))
    assert data["scan"]["ports_tls"] == list(CONSULTING_TLS_PORTS), (
        data["scan"]["ports_tls"]
    )


def test_not_a_connector_ledger_has_exactly_four_entries() -> None:
    """Locks D-20's corrected arithmetic: the not-a-connector set is four
    fields, not the original three-field claim D-08 made before the D-20
    amendment."""
    assert len(_NOT_A_CONNECTOR) == 4, _NOT_A_CONNECTOR
    assert set(_NOT_A_CONNECTOR) == {
        "enable_nmap",
        "enable_authenticated_mode",
        "enable_recurring_otics",
        "enable_codesign",
    }, _NOT_A_CONNECTOR
    for field, driver in _NOT_A_CONNECTOR.items():
        assert driver.strip(), f"{field}: blank driver pointer"


def test_not_a_connector_ledger_stale_entry_is_caught() -> None:
    """Self-test proving the stale-entry direction: a ledger key naming a
    field that is not a real ConnectorsCfg field is caught, and a ledger
    entry with a blank driver pointer is caught."""
    known_keys = _enable_field_names()
    problems = _not_a_connector_problems(
        known_keys, {}
    )
    # The real ledger is clean against real fields.
    assert not problems, problems

    stale = {"enable_totally_made_up": "no such field exists"}
    orig = dict(_NOT_A_CONNECTOR)
    try:
        _NOT_A_CONNECTOR.clear()
        _NOT_A_CONNECTOR.update(stale)
        stale_problems = _not_a_connector_problems(known_keys, {})
        assert stale_problems, "failed to flag a stale ledger key"
        assert any("stale ledger entry" in p for p in stale_problems), stale_problems

        _NOT_A_CONNECTOR.clear()
        _NOT_A_CONNECTOR.update({"enable_nmap": "   "})
        blank_problems = _not_a_connector_problems(known_keys, {})
        assert blank_problems, "failed to flag a blank driver pointer"
        assert any("blank driver pointer" in p for p in blank_problems), blank_problems
    finally:
        _NOT_A_CONNECTOR.clear()
        _NOT_A_CONNECTOR.update(orig)


def test_planted_connector_field_is_caught_without_list_edit() -> None:
    """Derivation self-test: a synthetic `enable_planted_field` added to the
    real known-keys set (simulating a new `ConnectorsCfg` field with no
    dispositioned template entry) is reported by name by the same
    `_completeness_problems` function used against the real template --
    zero edits to any enumerated list."""
    known_keys = _enable_field_names() | {"enable_planted_field"}
    text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    tagged = _parse_tagged_lines(text)

    problems = _completeness_problems(known_keys, tagged)
    assert problems, "completeness check failed to catch a synthetic unlisted field"
    assert any("enable_planted_field" in p for p in problems), problems


def test_out_of_vocabulary_tag_is_caught() -> None:
    """Self-test: a tag outside the closed D-06 vocabulary is reported by
    name, naming both the offending key and the tag."""
    tagged = _parse_tagged_lines(
        "  enable_fake: true  # on: requires-magic - "
        "some detail text that is long enough to pass the length check\n"
    )
    assert tagged, "test fixture line failed to match _TAGGED_LINE_RE"

    problems = _vocabulary_problems(tagged)
    assert problems, "vocabulary check failed to catch an out-of-vocabulary tag"
    assert any("enable_fake" in p and "requires-magic" in p for p in problems), problems


def test_stale_prefix_disagreement_is_caught() -> None:
    """Self-test: a `true` value tagged with an `off:` prefix is caught."""
    tagged = _parse_tagged_lines(
        "  enable_fake: true  # off: requires-targets - "
        "some detail text that is long enough to pass the length check\n"
    )
    problems = _vocabulary_problems(tagged)
    assert problems
    assert any("enable_fake" in p and "disagrees" in p for p in problems), problems


def test_short_detail_is_caught() -> None:
    """Self-test: a detail shorter than 30 characters / 5 words is caught."""
    tagged = _parse_tagged_lines(
        "  enable_fake: false  # off: requires-credentials - too short\n"
    )
    problems = _vocabulary_problems(tagged)
    assert problems
    assert any("enable_fake" in p and "shorter than" in p for p in problems), problems


def test_armed_extras_hazard_guard_is_caught() -> None:
    """Self-test: a template field shipping true that also appears in some
    REGISTRY entry's enabled_attrs is caught -- proves the D-18 guard logic
    against a synthetic hazard rather than only against today's real
    (currently hazard-free) template."""
    real_entry = REGISTRY[0]
    hazardous_field = real_entry.enabled_attrs[0]
    tagged = {
        hazardous_field: (
            True,
            "on",
            "requires-targets",
            "synthetic hazard case for the D-18 self-test only",
        )
    }
    problems = _armed_extras_hazard_problems(tagged)
    assert problems, "D-18 guard failed to catch a synthetic armed-hazard field"
    assert any(hazardous_field in p for p in problems), problems
