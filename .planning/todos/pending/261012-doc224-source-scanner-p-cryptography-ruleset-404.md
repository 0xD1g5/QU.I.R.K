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

## Spike result (2026-10-28, semgrep 1.182.1, scratch venv /Volumes/Digs-1TB/tmp-semgrep-spike)

- **Failure mode confirmed, and it is silent.** `semgrep --json --config p/cryptography -- <dir>` exits 7 but prints
  VALID JSON: `results: []`, `errors: ["Failed to download configuration ... HTTP 404", ...]`. `scan_source_repo`
  parses it, sees no results, and returns `[]` with NO warning (it never reads `errors` or the exit code). Every
  source scan since the pack disappeared has reported a clean repo.
- **Registry alternatives, run on the chaos-lab fixture (seed.sh replayed offline, 6 files, ~25 planted patterns):**
  `p/default` 14 hits, `p/security-audit` 8, `p/python` 6, `p/golang` 5, `p/java` 3. All miss the deprecated-TLS,
  weak-random (Python/Java), XOR and hardcoded-AES-key patterns, and none flags RSA/ECDSA/DH key use — the
  quantum-relevant signal. They also need network at scan time; the Semgrep Rules License restricts redistributing
  registry rules, so they cannot be bundled in the wheel.
- **Bundled QUIRK rules are feasible.** A 3-rule prototype (`proto/quirk-pqc.yaml`: Python `cryptography`/PyCryptodome
  RSA/EC/DH keygen, Java `KeyPairGenerator.getInstance(RSA|EC|DSA|DH)`, Go `rsa`/`ecdsa.GenerateKey`) found 5/5
  planted uses, skipped `ML-DSA`, ran offline in ~1s with 0 errors. `cbom/builder.py:654` derives the algorithm
  from the rule ID, so rule IDs that name the algorithm feed the CBOM directly.
- **Effort:** M for a credible first ruleset (~20-30 rules over Python/Java/Go/JS: quantum-vulnerable public key,
  weak hash/cipher/mode, deprecated TLS, weak random), packaged as `quirk/scanner/rules/*.yaml`, with semgrep
  `--test` fixtures and an honest-error fix for the exit/`errors` path. Not a 235 item.

## Operator decision (2026-10-28)

**Remove the claim for v5.28.0 (LAUNCH-02).** No replacement ruleset in 235. The silent-clean defect above means
removal must also stop the connector from reporting an empty result as a clean scan.
