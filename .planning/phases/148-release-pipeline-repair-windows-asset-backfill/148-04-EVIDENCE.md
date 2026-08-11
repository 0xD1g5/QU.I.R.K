# Phase 148 Plan 04: Live-Run Evidence

**Gathered:** 2026-08-11

This file records concrete run IDs, URLs, job/step conclusions, and command output proving the
four phase success criteria against live GitHub — not code inspection.

---

## SC-1 + SC-2: Release dry-run (`release.yml`, `workflow_dispatch`)

- **Run ID:** `31524058796`
- **Run URL:** https://github.com/0xD1g5/QU.I.R.K/actions/runs/31524058796
- **Event:** `workflow_dispatch`
- **Ref:** `main`
- **Triggered:** 2026-08-11T18:41:47Z
- **Overall conclusion:** `success`

### Pre-dispatch baseline (captured before dispatching)

`gh release list --json tagName -q '.[].tagName' | sort`:
```
v5.5.1
v5.5.2
v5.5.2.1
v5.5.2.2
v5.5.2.3
v5.5.2.4
v5.5.2.5
v5.6.0
v5.7.0
v5.8.0
```

`quirk-scanner` PyPI version list (pypi.org/pypi/quirk-scanner/json):
```
['4.10.0', '4.10.1', '5.0.0', '5.11.0', '5.5.0', '5.5.1', '5.5.2', '5.5.2.3', '5.5.2.4', '5.5.2.5', '5.5.3', '5.6.0', '5.8.0']
```

### Job conclusions

| Job | Conclusion |
|-----|------------|
| Build wheel + sdist | `success` |
| Build Windows zip + attach GitHub Release asset (windows-package) | `success` |
| Publish to PyPI (Trusted Publishers + Sigstore) | `skipped` |

### Step conclusions inside `windows-package`

| Step | Conclusion |
|------|------------|
| Set up job | success |
| Checkout | success |
| Set up Python 3.11 | success |
| Install project and PyInstaller | success |
| Build onedir EXE | success |
| Read version | success |
| Determine signing capability | success |
| Sign with production certificate (if configured) | **skipped** (no cert secrets configured) |
| Clean up production signing artifacts | success |
| CI self-test — ephemeral cert signing round-trip | **success** (the `1a6effc` repair, D-08) |
| Clean up self-test artifacts | success |
| Assemble Windows operator zip | success |
| Upload dry-run zip artifact | **success** (D-07) |
| Attach zip to GitHub Release | **skipped** (D-06) |
| Post Set up Python 3.11 | success |
| Post Checkout | success |
| Complete job | success |

Duration of `windows-package` job: 3m43s.

### CI self-test log line (proves D-08 — the `1a6effc` repair actually executes and passes)

```
Build Windows zip + attach GitHub Release asset  CI self-test — ephemeral cert signing round-trip
2026-08-11T18:45:17.5342716Z SELF_TEST_SIGNING: OK — signtool wiring verified end-to-end
```

### Artifact proof (D-07 — dry-run output is inspectable, not lost)

`gh api repos/0xD1g5/QU.I.R.K/actions/runs/31524058796/artifacts`:
```json
{"name":"quirk-windows-dry-run","size_in_bytes":57330823}
{"name":"dist","size_in_bytes":3266460}
```

### Zero side-effect proof

- `gh release list --json tagName -q '.[].tagName' | sort` AFTER the dry-run — **byte-identical**
  to the pre-dispatch baseline above (confirmed via `diff`, no output).
- `quirk-scanner` PyPI version list AFTER the dry-run — **unchanged**:
  ```
  ['4.10.0', '4.10.1', '5.0.0', '5.11.0', '5.5.0', '5.5.1', '5.5.2', '5.5.2.3', '5.5.2.4', '5.5.2.5', '5.5.3', '5.6.0', '5.8.0']
  ```

**Conclusion:** SC-1 and SC-2 proven — the `publish` job was literally `skipped` (event+ref guard
holds under a real dispatch), the `windows-package` job ran end-to-end including the repaired
signing self-test, the dry-run zip artifact was produced and is downloadable, and no external
state (GitHub Releases, PyPI) was mutated.

---

## SC-3: Tag hygiene guard (`release-tag-hygiene.yml`)

- **Run ID:** `31524420671`
- **Run URL:** https://github.com/0xD1g5/QU.I.R.K/actions/runs/31524420671
- **Event:** `workflow_dispatch`
- **Ref:** `main`
- **Overall conclusion:** `success`
- **Job `tag-hygiene` conclusion:** `success` (9s)

### Job summary content (reproduced by re-running `scripts/release_tag_hygiene.py`
locally against the same repo state immediately after the run — the script is a pure
git-tag/gh-API cross-reference with no time-dependent behavior beyond tag/run state, which had
not changed between the live run and this local reproduction)

```
## Release Tag Hygiene

### OK (backed by a successful release run)
- v4.10.0, v4.10.1, v5.1.0, v5.5.0, v5.5.1, v5.5.2, v5.5.2.1, v5.5.2.2,
  v5.5.2.3, v5.5.2.4, v5.5.2.5, v5.6.0, v5.7.0, v5.8.0

### EXEMPT (baselined historical disposition)
- v3.8.0 ... v5.4.0 — historical baseline — predates the tag hygiene guard (2026-08-11)
- v5.9 — malformed two-component tag, never matched release.yml's v*.*.* glob
- v5.10.0 — tag created locally, never pushed to origin
- v5.11.0 — PyPI-only release; Windows asset gap dispositioned per D-148-RELEASE04

No flagged tags.
```

**Conclusion:** SC-3 proven — the guard ran live, went green because the baseline was correctly
seeded in 148-02, and its summary explicitly names `v5.9`, `v5.10.0`, and `v5.11.0` in the EXEMPT
section with their specific incident-accurate reasons (malformed glob, never pushed, and
PyPI-only disposition respectively).

---

## SC-4: v5.11.0 GitHub Release (bare, zero assets)

- **Release URL:** https://github.com/0xD1g5/QU.I.R.K/releases/tag/v5.11.0
- **Command used:** `gh release create v5.11.0 --title "v5.11.0 — PyPI-only release (no Windows asset)" --notes-file docs/release-notes/5.11.0-github-release-body.md --latest=false --verify-tag`

### Verification output

`gh release view v5.11.0 --json tagName,assets,isDraft,isPrerelease -q '.tagName, (.assets|length), .isDraft, .isPrerelease'`:
```
v5.11.0
0
false
false
```

`gh release view v5.11.0 --json body -q .body` — first lines of published body (full text
confirmed to contain `PyPI-only`, `1a6effc`, `v5.12.0`, and a link ending
`/docs/release-notes/5.11.0.md`):
```
## v5.11.0 — PyPI-only release, no Windows asset

This release was published to PyPI but **no Windows operator zip was attached** to this
GitHub Release...
[full body confirmed to include: PyPI-only / 1a6effc / v5.12.0 / docs/release-notes/5.11.0.md link]
```

`gh release list --json tagName -q '.[].tagName'` now includes `v5.11.0` and still excludes
`v5.9` and `v5.10.0` (no Release objects were created for those tags, per D-01/D-148-RELEASE04
scope).

**Conclusion:** SC-4 proven — a published (non-draft, non-prerelease), non-latest v5.11.0 Release
exists with zero attached assets and a body stating the PyPI-only disposition, root cause, fix
commit, and first-fixed version, linking the full notes.

---

## Mapping to phase success criteria

| Success Criterion | Evidence section |
|--------------------|-------------------|
| SC-1: dry-run exercises windows-package end-to-end with the repaired signing self-test | SC-1 + SC-2 above |
| SC-2: proven by a real workflow_dispatch run, not code inspection | SC-1 + SC-2 above (run 31524058796) |
| SC-3: tag-hygiene guard runs live and reports per-tag status | SC-3 above (run 31524420671) |
| SC-4: v5.11.0 Releases-page entry states PyPI-only, zero assets | SC-4 above |
