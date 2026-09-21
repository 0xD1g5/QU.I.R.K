# `lab.sh up` silently reuses a stale prober image — a scan can report a superseded model's score

**Filed:** 2026-09-14 (demo-prep task 1)
**Priority:** P1 before any demo, P2 otherwise
**Status:** open (worked around by hand on 2026-09-14; the hazard is unfixed)

## What happened

`PROFILE_ARGS="--profile multihost" ./lab.sh up`, then the documented scan command, produced a
confident **91/100** readiness score. `main` had been on scoring v3 since earlier that day, and the
same evidence scores **15/100** under v3. The scan exited 0, wrote 11 report artifacts, and gave no
warning of any kind.

Cause: `lab.sh`'s `up` subcommand runs `compose up -d "$@"` with **no `--build`**
(`quantum-chaos-enterprise-lab/lab.sh:233,277,299,347`). An existing `chaoslab-mh-prober` image is
reused regardless of how far the repo has moved. The image in question had been built
2026-09-13T22:47Z; the v3 merge landed 2026-09-14.

`sensor.Dockerfile` is **not** at fault — it does `COPY . /quirk/` + `pip install ".[all]"` from the
local checkout, so a rebuild picks up working-tree code correctly. Only the missing `--build` is.

## Second trap found while fixing it

`docker compose --profile multihost build mh-prober` (no `-p`) derives the project name from the
directory and tags **`quantum-chaos-enterprise-lab-mh-prober`** — a different image from the
`chaoslab-mh-prober` the running container uses. The build succeeds, reports "Built", and changes
nothing. `-p chaoslab` is required:

```bash
docker compose -p chaoslab --profile multihost build mh-prober
docker compose -p chaoslab --profile multihost up -d --force-recreate mh-prober
docker exec chaoslab-mh-prober-1 python -c \
  "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"
```

## Why this is worth a real fix

The failure is silent and the output is plausible. Nothing in the scan output names the scanner
build, so there is no way to tell a v2 score from a v3 score by looking at the result — only the
magnitude (91 vs 15) betrays it, and only to someone who already knows both numbers. The reports
print `Platform version 5.21.0` in both cases, because `pyproject.toml` has not bumped since the
PyPI release; the platform version is not a staleness signal.

## Fix options (pick one; not yet decided)

1. **`lab.sh up --build` passthrough plus a warning** when a `quirk/`-touching git commit is newer
   than the prober image's created timestamp. Cheapest honest option.
2. **Always `--build` for prober-like services only.** A blanket `--build` on `up` would rebuild
   nothing else (every other service is a pinned public image), so the cost is bounded — but the
   1.4 GB build context makes even a cache-hit rebuild slow enough to notice.
3. **Stamp the scanner build into scan output.** Print `SCORING_VERSION` and a source SHA in the
   scan summary so any artifact self-identifies. This fixes the whole class rather than this
   instance, and would have caught it immediately.

Option 3 is the one that generalises; 1 is the one that unblocks a demo.

## Related

Same failure shape as the project's standing lesson that a green result about one artifact gets
asserted about a broader one (CLAUDE.md §GSD `state.*` clause (e)/(h): "the toolchain is patched"
was only ever "one install of the toolchain is patched"). Here: "the lab runs current code" was only
ever "the lab runs whatever was current when someone last rebuilt".

---

## RESOLVED 2026-09-20 — options 3 + 1, operator-selected

The todo left three options undecided and noted "Option 3 is the one that generalises; 1 is the
one that unblocks a demo." Both were taken.

### Option 3 — stamp the build into scan output (the class fix)

The scan summary now carries two rows beside `Platform version`:

```
Scoring model      v3.0            <- read live from SCORING_VERSION
Scanner build      a612e60fd3a2    <- $QUIRK_BUILD_SHA, else .git, else "unknown"
```

`Scoring model` is the decisive one and is *always* knowable — it is a Python constant, needs no
infrastructure, and alone would have caught the 91-vs-15 scan. The SHA corroborates.

**`unknown` is deliberate.** The tempting fallback is the package version, so the row is never
empty — but that substitution *is* the defect being fixed: `Platform version 5.21.0` printed
identically for the stale and current scanner, so it read as an answer while carrying no
information. An honest absence beats a value that cannot discriminate.

`quirk/build_stamp.py` reads `.git` as plain files and never shells out. A scan has no reason to
fork, this repo has a standing macOS fork()-after-Network.framework SIGSEGV hazard on any
default-`close_fds` spawn, and `git` is usually absent from the slim images the stamp most needs
to describe. The parser was cross-checked against `git rev-parse HEAD`: byte-identical.
`sensor.Dockerfile` gains an `ARG`/`ENV` so a built image self-identifies.

### Option 1 — `--build` passthrough plus a staleness warning

`up` **and `all`** now forward `"$@"` to compose, so `./lab.sh up --build` works. `all` was
included because it starts the multihost profile and therefore the same prober — fixing only `up`
would have left the identical hazard one subcommand away.

A pre-start warning fires when the prober image predates the newest commit touching `quirk/`. It
warns rather than rebuilding (a blanket rebuild costs a 1.4 GB context on every `up`, even on a
cache hit) and is suppressed when `--build` was passed. Every dependency (docker, git, python3) is
checked and the function returns silently if any is absent — a warning is not worth breaking `up`
over. The docs say plainly to treat `--build` as the reliable path and the warning as a backstop.

Date logic verified on four cases, including the exact incident shape (image 2026-09-13, commit
2026-09-14 → warns) and garbage input (→ silent).

### Also recorded

The todo's "second trap" — `docker compose build` without `-p chaoslab` tagging a different image
and changing nothing — was already documented in `docs/chaos-lab.md` §3.32 and remains there. It
is now less reachable, since `./lab.sh up --build` carries the right project name automatically.

**Not locally verified:** `tests/test_chaos_lab_idempotency.py` parametrizes over
`docker compose config --profiles` at collection time and collected 0 cases here, because the
local Docker daemon is unresponsive. CI exercises it.
