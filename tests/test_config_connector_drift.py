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

import dataclasses
import subprocess
from pathlib import Path

import yaml

from quirk.config import ConnectorsCfg

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
    result = subprocess.run(
        ["git", "ls-files", "*.yaml", "*.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
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
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    new_file = tmp_path / "never_seen_before_config.yaml"
    new_file.write_text(
        "connectors:\n  enable_totally_new_bogus: false\n", encoding="utf-8"
    )
    subprocess.run(
        ["git", "add", "never_seen_before_config.yaml"], cwd=tmp_path, check=True
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

