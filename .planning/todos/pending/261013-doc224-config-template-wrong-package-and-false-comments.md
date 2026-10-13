---
created: 2026-10-13
title: "config_template.yaml (written by `quirk init`) tells users to `pip install quirk[...]` and repeats claims fixed in configuration.md"
area: product
priority: high
source: Phase 224 GC3 (orchestrator consolidation; template comments reported by GC3-CFG3)
---

# `quirk init`'s shipped template names the wrong PyPI package and carries comments the docs no longer make

`quirk/config_template.yaml` is copied into the operator's working directory by `quirk init`
(`quirk/cli/init_cmd.py:49` `files("quirk").joinpath("config_template.yaml")`), so its comments are user-facing
instructions. Phase 224 fixed the same claims in `docs/configuration.md`, but it does not edit product files (D-10),
and the ledger gate's wrong-package sweep (`tests/test_doc_claim_ledger_gate.py::test_no_wrong_package_install_instructions`)
scans only classified user-facing docs, so this file passes unseen.

1. **Wrong package, 11 lines.** `grep -nE "pip install ['\"]?quirk\[" quirk/config_template.yaml` -> lines 103, 113, 118,
   130, 133, 143, 147, 156, 164, 179, 195 (`pip install quirk[identity]`, `quirk[adcs]`, `quirk[cloud]`, `quirk[db]`,
   `quirk[kafka,redis]`, `quirk[hw]`). The distribution is `quirk-scanner` (`pyproject.toml:6 name = "quirk-scanner"`).
   `pip install quirk[...]` resolves whatever project owns the name `quirk` on PyPI, which is the supply-chain hazard
   224-17's T-224-SC gate exists to stop. The extras themselves all exist (`identity`, `adcs`, `cloud`, `db`, `kafka`,
   `redis`, `hw` in `[project.optional-dependencies]`). The unquoted brackets also glob in zsh.
2. **Email/broker scope, lines 163 and 166.** "scans every host in the general `targets:` block". GC3-CFG3 found this is
   wrong in the same way as the `docs/configuration.md` claim it narrowed (doc fix 8 in its f-0366 notes).
3. **Scheduler check, line 178.** "the scheduler rejects any recurring config where this is true". Recurring runs load
   `quirk scheduler run --scan-config` (`quirk/cli/scheduler_cmd.py:467,480,193-194`), which is never checked for
   `enable_authenticated_mode`. This claim is also tracked as a product defect by GC3-CFG3's trusted-targets/scheduler todo.

- [ ] Replace every `pip install quirk[...]` with the quoted form `pip install 'quirk-scanner[...]'`.
- [ ] Correct the comments at :163, :166 and :178 to match `docs/configuration.md` (or the product, if fixed first).
- [ ] Extend the wrong-package sweep to `quirk/config_template.yaml` (and any other shipped template) so it cannot regress.

## Feasibility & Effort

- **Feasibility: CONFIRMED.** Comment-only edits in one YAML file; the template is loaded as text by
  `quirk/cli/init_cmd.py:49-53`, and `tests/test_doc_claim_ledger_gate.py` already holds `FORBIDDEN_INSTALL_RE` to reuse.
- **Effort: S** (under an hour including the gate extension and a negative control).
- **Unknowns:** whether any test pins the current template text byte-for-byte (`grep -rn config_template tests/`).
- **Spike:** not needed.
