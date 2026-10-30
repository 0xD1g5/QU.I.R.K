---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-02, D-10); generated-doc source review in plan 224-11
priority: high
area: quirk/errors.py, tests/test_cmvp_freshness.py, docs/error-codes.md (generated)
status: pending
resolves_phase: null
owner: "999.128"
---

# Two error hints tell operators to run `quirk compliance cmvp refresh`, the command the project forbids for re-verification

`docs/error-codes.md` is generated from `quirk/errors.py` (`python run_scan.py errors --dump-md`), so the fix belongs in
the source, never in the generated file. Two remediation strings recommend the refresh command:

| Source | Generated line | Text |
|---|---|---|
| `quirk/errors.py:186` (`CMVP-REFRESH-NETWORK`) | `docs/error-codes.md:24` | "retry `quirk compliance cmvp refresh`" |
| `quirk/errors.py:201` (`CMVP-STALE`) | `docs/error-codes.md:27` | "Run `quirk compliance cmvp refresh` and commit with message `chore: re-verify CMVP catalog (YYYY-MM-DD)`" |

`refresh` previously wrote an empty algorithm list into `cmvp_cache.json` with no error raised (commit `a7cf302a`,
RVW-022: it looked only for `table#fips-algo-table`, and 11 of 53 curated certificates publish their algorithms another
way). That commit added a second parse strategy, but the project's standing rule for the CMVP catalog is still to
re-verify manually against the source URL and hand-edit `last_verified`, not to run `refresh`. The CMVP-STALE hint
therefore sends an operator through the path the maintainers avoid, and tells them to commit a message that asserts a
verification the command cannot make.

The same instruction is pinned in the freshness gate's failure message: `tests/test_cmvp_freshness.py:9`, `:50` and
`:66` all say "run `quirk compliance cmvp refresh` and commit with ...".

- [ ] Decide whether `refresh` is now trustworthy (a7cf302a's second strategy plus a before/after diff of
      `cmvp_cache.json`) or whether the hints should say "re-verify against the source URL and edit `last_verified`".
- [ ] Reword `CMVP-REFRESH-NETWORK` and `CMVP-STALE` in `quirk/errors.py` accordingly, and the three messages in
      `tests/test_cmvp_freshness.py`.
- [ ] Regenerate `docs/error-codes.md` and run `tests/test_error_codes_freshness.py`.

## Feasibility & Effort

**CONFIRMED** (file:line above; `refresh` exists: `python run_scan.py compliance cmvp --help` lists `refresh` and
`status`). Effort **S** for the wording change plus regeneration. The decision about whether `refresh` is safe is the
only unknown and needs a read-only dry run against a copy of the cache. **Spike optional** (copy
`quirk/compliance/cmvp_cache.json` to a scratch dir and diff after a refresh).
