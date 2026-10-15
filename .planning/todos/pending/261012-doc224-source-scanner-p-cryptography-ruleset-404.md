---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONN-GIT-*
priority: high
area: quirk/scanner/source_scanner.py, README.md, docs/chaos-lab.md, quantum-chaos-enterprise-lab/expected_results_v3.md, quantum-chaos-enterprise-lab/expected_results_v4.md
status: pending
resolves_phase: null
owner: "999.127"
---

# The source scanner's `p/cryptography` Semgrep ruleset does not resolve at the registry

`quirk/scanner/source_scanner.py:62` runs `semgrep --json --config p/cryptography -- <path>`. On 2026-10-12 the
Semgrep registry URL for that pack returned 404, while other packs returned 200:

    curl -s -o /dev/null -w '%{http_code}' https://semgrep.dev/c/p/cryptography      -> 404
    curl -s -o /dev/null -w '%{http_code}' https://semgrep.dev/c/p/security-audit    -> 200
    curl -s -o /dev/null -w '%{http_code}' https://semgrep.dev/c/p/default           -> 200
    curl -s -o /dev/null -w '%{http_code}' https://semgrep.dev/c/p/nonexistentpackxyz -> 404

If semgrep cannot load the config it will not print a results list, so `json.loads(proc.stdout)` fails (or yields no
`results`) and the connector returns `[]` after a warning. The same name appears in `README.md:91`,
`docs/chaos-lab.md:1571`, and the chaos-lab oracles (`expected_results_v3.md:165`, `expected_results_v4.md:244`).
`docs/connectors/git.md` states the observation as a dated known issue and no longer claims language coverage.

Not reproduced end to end: semgrep is not installed on the verifying host and installing it was out of scope for a
docs phase. The registry observation is solid; the runtime consequence is inferred from the code path.

- [ ] Install semgrep in a scratch venv and run `semgrep --config p/cryptography <dir>` to confirm the failure mode.
- [ ] Choose a ruleset that exists (e.g. a curated local rules directory bundled with QU.I.R.K., or an existing
      registry pack) and update `source_scanner.py`, the README row, `docs/chaos-lab.md` and both oracles.
- [ ] Add a test that fails when the configured pack name does not appear in a pinned list of resolvable packs, or
      bundle the rules so no network fetch is needed.
- [ ] Remove the Known-issue note from `docs/connectors/git.md` and re-verify its rows.

## Feasibility & Effort

**LIKELY** (404 observed on the registry; semgrep behaviour on an unknown pack inferred). Effort **M**: ruleset
choice is a product decision, then a one-line scanner change plus doc/oracle updates. Unknown: whether a rules
directory should ship in the wheel. **Spike recommended** (one hour: install semgrep in a scratch venv and confirm).
