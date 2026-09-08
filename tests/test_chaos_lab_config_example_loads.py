"""Phase 189 / TRIAGE-03: docs/chaos-lab.md config-lab-core.yaml example
drift gate — docs==code proven by execution, not byte comparison.

The `# config-lab-core.yaml` fenced yaml block in docs/chaos-lab.md is
extracted at test-run time (anchored on the comment line, never a
hand-counted line range — the file is 1000+ lines and still growing) and
fed through the REAL quirk.config.load_config(). If the doc example ever
drifts from the current ScanCfg/OutputCfg schema, this test fails loudly
instead of an operator discovering it by copy-pasting a broken example.
"""
import re
from pathlib import Path

from quirk.config import load_config

CHAOS_LAB_MD = Path(__file__).resolve().parents[1] / "docs" / "chaos-lab.md"

# IN-02: anchored to the ```yaml fence so a future prose mention of the
# literal anchor line earlier in the doc cannot hijack extraction. The
# `# config-lab-core.yaml` comment line itself is excluded from the capture
# (it is a YAML comment, so including it would also be harmless).
_EXAMPLE_RE = re.compile(r"```yaml\n# config-lab-core\.yaml\n(.*?)```", re.DOTALL)


def _extract_config_lab_core_example() -> str:
    text = CHAOS_LAB_MD.read_text(encoding="utf-8")
    match = _EXAMPLE_RE.search(text)
    assert match, (
        "docs/chaos-lab.md no longer contains a `# config-lab-core.yaml` "
        "example block — a missing example must fail this gate, never "
        "silently skip it."
    )
    return match.group(1)


def test_chaos_lab_core_example_loads_verbatim(tmp_path):
    """TRIAGE-03: the docs/chaos-lab.md config-lab-core.yaml example must
    load through the real load_config() — docs==code proven by execution."""
    yaml_text = _extract_config_lab_core_example()
    cfg_path = tmp_path / "config-lab-core.yaml"
    cfg_path.write_text(yaml_text, encoding="utf-8")

    cfg = load_config(str(cfg_path))  # must not raise

    assert cfg.scan.ports_tls, "parsed example must not have an empty ports_tls (vacuous parse)"
    assert cfg.output.directory, "parsed example must not have an empty output.directory (vacuous parse)"


def test_chaos_lab_core_example_anchor_present():
    """A missing `# config-lab-core.yaml` anchor comment must fail loudly,
    not silently no-op the gate (covered implicitly by the assert inside
    _extract_config_lab_core_example(), exercised directly here so a
    regression in the anchor regex itself is caught even if the fixture
    above happens to still pass for an unrelated reason)."""
    yaml_text = _extract_config_lab_core_example()
    assert yaml_text.strip(), "extracted example block must not be empty"
