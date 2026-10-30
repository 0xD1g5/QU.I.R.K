---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONN-DOCKER-*, DCL-CONN-GIT-*
priority: medium
area: quirk/scanner/container_scanner.py, quirk/scanner/source_scanner.py, run_scan.py
status: pending
resolves_phase: null
owner: "999.127"
---

# Container/source scanner hints and three phase-skip reasons name extras that do not install the tool

Found while verifying `docs/connectors/docker.md` and `docs/connectors/git.md`. Related to, but distinct from,
`261012-doc224-install-hints-name-wrong-pypi-package.md` (that todo covers the 18 `pip install quirk[...]` sites it
lists; these sites are not in it).

- `quirk/scanner/container_scanner.py:78` tells the user to `pip install 'quirk[cbom]'` and `brew install syft`;
  `quirk/scanner/source_scanner.py:55` tells them to `pip install 'quirk[cbom]'` and `pip install semgrep`.
  The PyPI project `quirk` is unrelated (see the other todo), and the `cbom` extra is
  `cyclonedx-python-lib`, which is already a core dependency; it has nothing to do with syft or semgrep, which are
  external binaries. The only useful part of each hint is the second install command.
- `run_scan.py:3330` skips with `boto3 not installed (extras: aws)` and `run_scan.py:3802` with
  `hvac not installed (extras: vault)`. `pyproject.toml` defines no `aws` or `vault` extra (the real extras are
  adcs, all, api, broker, cbom, cloud, dashboard, db, dev, docx, email, hw, identity, kafka, motion, notify, redis,
  tickets). boto3 is a core dependency; hvac lives in `cloud`. `run_scan.py:3892` and `:3932` still say
  `sslyze not installed (extras: motion)` although sslyze became a core dependency in v5.22.
- Separately, `docs/connectors/docker.md` used to recommend `pip install syft`, which installs OpenMined's PySyft,
  not Anchore's Syft CLI. The doc is fixed; no product code recommends it.

- [ ] Reword the two scanner hints to the single working command (`brew install syft` / `pip install semgrep`).
- [ ] Correct the `aws` / `vault` / `motion` extras in the run_scan.py skip reasons.
- [ ] Update any test or golden fixture that pins the old strings (`grep -rn "extras: aws\|extras: vault" tests`).

## Feasibility & Effort

**CONFIRMED** (every site above was read at the cited line on 2026-10-12; extras list read from
`tomllib.load(open("pyproject.toml","rb"))["project"]["optional-dependencies"]`). Effort **S**: string edits, plus
whichever tests pin the text. **No spike needed.**
