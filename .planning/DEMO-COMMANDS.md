---
project: QU.I.R.K.
type: runbook
subtype: commands-only
status: active
audience: operator at the keyboard
demo_date: 2026-09-18
target_host: Ubuntu (arm64) guest · VMware Fusion · Apple Silicon MacBook Pro
companion: .planning/DEMO-RUNBOOK.md (structure, talk tracks, hazards)
updated: 2026-09-15
---

# Demo Command Runbook

> **SUPERSEDED 2026-09-20.** The demo was delivered 2026-09-18. The authoritative walkthrough is
> `docs/demo-runbook-2026-09-18.md` on `main`. This file is retained only for its **arm64 /
> Apple Silicon** material, which exists in no other file and is pending a move into
> `docs/chaos-lab.md` — see `.planning/DEMO-PREP-HARVEST.md` §5.1 and §7.


Every command needed to go from a cold Ubuntu VM to a finished demo and back to a clean
machine. No talk track — that lives in `DEMO-RUNBOOK.md`.

Each command block states **what it does**, **what you should see**, and where a step is a
gate, **what to do when it fails**. Commands were read out of this repo's own source
(`lab.sh`, `docker-compose.yml`, `sensor.Dockerfile`, `multihost-scan-config.yaml`,
`docs/installation.md`), not reconstructed from memory.

**Conventions**

- `$REPO` is the QU.I.R.K. checkout root. `$LAB` is `$REPO/quantum-chaos-enterprise-lab`.
- Every `quirk` command on the host requires the venv active. If you see
  `quirk: command not found`, you dropped out of it — `source $REPO/.venv/bin/activate`.
- `-p chaoslab` is **not optional** on any compose command. See Phase 0 note.

---

## Phase 0 — Read this before typing

Three facts that turn into wasted demo time if you learn them at the keyboard.

**`-p chaoslab` on every compose command.** `lab.sh` hardcodes `docker compose -p chaoslab`.
If you drop it on a manual `docker compose` call, compose derives the project name from the
directory instead, builds a *different* image (`quantum-chaos-enterprise-lab-mh-prober`),
prints "Built", and the running container never sees it. The rebuild appears to succeed and
changes nothing.

**`lab.sh up` never passes `--build`.** It runs `compose up -d`. A stale `mh-prober` image is
reused silently. This is the single highest-cost failure in the whole path — see Phase 5.

**`./lab.sh down` needs no `PROFILE_ARGS`.** It runs `compose --profile "*" down`, so it
catches every profile regardless of what you started. `up`, `build` and `ps` **do** need the
profile flag.

---

## Phase 1 — Ubuntu VM prerequisites

Skip to Phase 2 if the guest is already set up. Run once per machine.

### 1.1 Base packages

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl ca-certificates
```

### 1.2 Docker Engine

Use Docker's own apt repo, not the distro `docker.io` package — the bundled compose plugin
matters here.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
                        docker-buildx-plugin docker-compose-plugin
```

Run Docker without sudo, then **log out and back in** (or `newgrp docker`) so the group takes
effect:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

**Verify:**

```bash
docker version
docker compose version    # must be v2.x — "docker-compose" v1 will not work
docker run --rm hello-world
```

### 1.3 Confirm you are on arm64

```bash
uname -m          # expect: aarch64
docker info --format '{{.Architecture}}'
```

If this says `aarch64`, Phase 2 is mandatory. If it says `x86_64`, skip Phase 2 entirely.

### 1.4 Clone and install QU.I.R.K.

The venv is **mandatory** on Ubuntu 23.04+ — PEP 668 makes the system Python externally
managed and a bare `pip install` fails with `error: externally-managed-environment`.

```bash
git clone https://github.com/0xD1g5/QU.I.R.K
cd QU.I.R.K
export REPO="$PWD"
export LAB="$REPO/quantum-chaos-enterprise-lab"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dashboard]'
```

PDF export needs a browser. This is what backs the `/print` route you eyeball in Phase 8:

```bash
playwright install chromium
sudo playwright install-deps chromium
```

**Verify:**

```bash
quirk --help
quirk serve --help      # note: no --db-path flag exists
python3 -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"
```

That last line must print **`3.0`**. It is the host-side counterpart of the Phase 5 gate.

---

## Phase 2 — arm64 fix for `mh-saml-idp`

**Only on aarch64.** `kenchan0130/simplesamlphp:1.19.7` publishes a single-architecture
`linux/amd64` manifest — verified against the Docker Hub registry API on 2026-09-15. No arm64
variant exists under that tag. Every other image in the `multihost` profile is multi-arch,
including `osixia/openldap:1.5.0`; `mh-prober` builds from source and builds native.

### 2.1 Install amd64 emulation

Per boot of the VM. This registers qemu-user-static handlers in the guest kernel's
`binfmt_misc`. It is **not** Docker Desktop's Rosetta — that does not exist in a native Linux
guest.

```bash
docker run --privileged --rm tonistiigi/binfmt --install amd64
```

**Verify:**

```bash
docker run --rm --platform linux/amd64 alpine:3.20 uname -m   # expect: x86_64
```

### 2.2 Pin the one service

An override file keeps the tracked compose file clean. `lab.sh` passes a single explicit
`-f`, which disables compose's automatic override discovery, so this file is used by the
direct compose calls in 2.3 rather than by `lab.sh up`.

```bash
cat > "$LAB/docker-compose.arm64.yml" <<'YAML'
# arm64 demo override — kenchan0130/simplesamlphp:1.19.7 is amd64-only.
# Not committed. Delete after the demo.
services:
  mh-saml-idp:
    platform: linux/amd64
YAML
```

### 2.3 Bring the lab up with the override

`./lab.sh certs` first, because that is what materializes the lab CA and mTLS client keys
(they are deliberately not committed) — bypassing `lab.sh up` would otherwise skip it.

```bash
cd "$LAB"
./lab.sh certs

docker compose -p chaoslab \
  -f docker-compose.yml -f docker-compose.arm64.yml \
  --profile multihost up -d
```

> Going this route skips `lab.sh`'s CHAOS-05 image-pin gate. That gate only checks for
> `:latest` and untagged images; nothing in this override touches image tags. Acceptable for a
> demo — do not make it the habit.

**Simpler alternative if you would rather not manage an override file:** add
`platform: linux/amd64` directly under `mh-saml-idp:` in `docker-compose.yml` and use the
normal `./lab.sh up` path in Phase 3. One line, `git checkout` reverts it. The pin gate reads
only `image:` keys, so it stays green either way.

**If you are skipping the SAML host instead (Option B):** comment out `10.80.0.41/32` in
`$LAB/multihost-scan-config.yaml` and remove `saml_targets` from its connector block. Expect
30 targets, not 31. All five CRITICAL findings sit on the expired-certificate hosts
(`.11`, `.101`–`.104`), so 15/100 and 5 CRITICAL should hold — **confirm that in Phase 6
before you rely on it in front of anyone.**

---

## Phase 3 — Start the lab

On **x86_64**, or after doing the in-place one-line edit in 2.3:

```bash
cd "$LAB"
PROFILE_ARGS="--profile multihost" ./lab.sh up
```

On **arm64 with the override file**, you already did this in 2.3.

**Expected:** `✅ Lab started.` followed by a `compose ps` table.

**Verify all 33 containers are up, and nothing is restarting:**

```bash
docker compose -p chaoslab --profile multihost ps
docker compose -p chaoslab --profile multihost ps --filter status=running -q | wc -l   # expect 33
```

**The one container to check by name** — if the arm64 fix did not take, this is where it
shows:

```bash
docker compose -p chaoslab --profile multihost ps mh-saml-idp
docker logs chaoslab-mh-saml-idp-1 2>&1 | tail -20
```

`Restarting`, `Exited`, or `exec format error` means Phase 2 did not apply. Go back.

---

## Phase 4 — Build the prober

Separate from Phase 3 on purpose. `lab.sh up` does not build.

```bash
cd "$LAB"
docker compose -p chaoslab --profile multihost build mh-prober
docker compose -p chaoslab --profile multihost up -d --force-recreate mh-prober
```

`mh-prober` builds from `sensor.Dockerfile` with the repo root as context, so it picks up
whatever is in `quirk/` right now. Runs at `10.80.0.200` with `NET_RAW`, mounts
`$REPO/quirk-output` at `/out` and `multihost-scan-config.yaml` at `/scan-config.yaml`.

**Verify it is alive and can see the subnet:**

```bash
docker exec chaoslab-mh-prober-1 sh -c 'ip -4 addr show | grep 10.80'
docker exec chaoslab-mh-prober-1 sh -c 'ls -la /scan-config.yaml /out'
```

---

## Phase 5 — GATE: verify the scoring model

**Do not skip this. Do not proceed on a wrong answer.**

```bash
docker exec chaoslab-mh-prober-1 \
  python -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"
```

**Required output: `3.0`**

| Output | Meaning | Action |
|---|---|---|
| `3.0` | Correct. Proceed. | — |
| `2.x` | **Stale image.** The scan will report ~91/100 on evidence that scores 15/100. Exit 0, a full set of report files, a confident wrong number, no warning. | Re-run Phase 4. Check you used `-p chaoslab`. |
| error | Prober is not running or the import path changed. | `docker compose -p chaoslab --profile multihost ps mh-prober` |

`Platform version` in the report output is **not** a staleness signal — `pyproject.toml` has
not bumped since the PyPI release, so it reads identically on a stale and a fresh image.

---

## Phase 6 — Rehearsal scan

Run the exact live command once, now, so the live run is the second time you have seen it.

```bash
docker exec chaoslab-mh-prober-1 \
  quirk --config /scan-config.yaml \
        --allow-internal-targets \
        --allow-cleartext-broker-probe
```

Both flags are required: `--config` because there is no `scan` subcommand and no `--targets`
flag (without it you get the interactive wizard), and `--allow-internal-targets` because the
scanner refuses RFC1918 space by default.

**Expected: ~19 seconds wall clock.** Then:

```
400 findings — 5 CRITICAL / 14 HIGH / 33 MEDIUM / 16 LOW / 332 INFO
370 endpoints, 38 assessable
readiness 15/100 POOR  (computed 61, limited to 15 by 5 open CRITICAL findings)
```

**Check the numbers against that, from the host:**

```bash
cd "$REPO"
ls -lt quirk-output/ | head -15

LATEST=$(ls -t quirk-output/findings-*.json | head -1)
echo "$LATEST"
python3 -c "
import json,collections,sys
f=json.load(open('$LATEST'))
rows=f if isinstance(f,list) else f.get('findings',f.get('results',[]))
c=collections.Counter((r.get('severity') or '?').upper() for r in rows)
print('total:', len(rows))
for s in ['CRITICAL','HIGH','MEDIUM','LOW','INFO']:
    print(f'  {s:9} {c.get(s,0)}')
"
```

**If you took Option B (dropped the SAML host), this is the verification step.** CRITICAL
should still be 5 and the score still 15. If it is not, you have a real difference to
understand before you present it.

**Artifacts you should now see in `quirk-output/`:**

| File | What it is |
|---|---|
| `findings-{stamp}.json` | Raw findings — the file the checks above read |
| `intelligence-{stamp}.json` | Scoring evidence, subscores, `evidence_summary` |
| `cbom-{stamp}.cdx.json` / `.cdx.xml` | The CycloneDX CBOM — the deliverable |
| `report-{stamp}.html` / `.pdf` / `.docx` | Client-ready reports |
| `executive-summary-{stamp}.md` | The written narrative |
| `scorecard-{stamp}.md` | Score breakdown — check the rollup arithmetic here |
| `roadmap-{stamp}.md` | Prioritized remediation |
| `technical-findings-{stamp}.md` | Full technical detail |
| `run-stats-{stamp}.json` | Timing and coverage stats |
| `nmap-discovery-{stamp}.xml` / `nmap-liveness-{stamp}.xml` | Discovery evidence |

**Confirm the rollup equation divides correctly** — it printed `= 15` until 2026-09-14:

```bash
grep -n "capped to\|limited to\|/ 1.25" quirk-output/scorecard-*.md | tail -5
```

Expect the form `76 / 1.25 = 61, capped to 15 / 100`.

---

## Phase 7 — Start the web session

From the **repo root**, venv active.

```bash
cd "$REPO"
source .venv/bin/activate
quirk serve --port 8512 --no-open
```

`quirk serve` has **no `--db-path` flag** — its only options are `--port`, `--host`,
`--no-open` and `--insecure`. It discovers `./quirk-output/quirk.db` itself, which is the same
file the prober wrote through its `/out` mount. `--db-path` exits 2 with
`unrecognized arguments`.

Leave it running in its own terminal for the rest of the demo.

Open `http://localhost:8512`. **Hard-refresh with `Ctrl`+`Shift`+`R`** — a cached
`index.html` will serve a stale bundle and a normal reload is not enough.

If you want it reachable from the Mac host rather than only inside the guest:

```bash
quirk serve --host 0.0.0.0 --port 8512 --no-open
ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}'   # the guest IP to browse to
```

**Pre-flight the tabs you will actually show, in order:**

1. Executive Verdict and score
2. Findings, filtered to CRITICAL — the five expired certificates
3. CBOM tab
4. Exposure Map — expect **12 nodes, 19 edges**, three shared keys, three hexagonal CA hubs,
   and a teal crown-jewel ring on `10.80.0.20:443`. If that ring renders black, you are on a
   stale bundle; hard-refresh again.

---

## Phase 8 — Final pre-demo checks

```bash
# 1. Every container still up
docker compose -p chaoslab --profile multihost ps --filter status=running -q | wc -l   # 33

# 2. Scoring model still v3
docker exec chaoslab-mh-prober-1 \
  python -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"

# 3. Dashboard answering
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:8512/

# 4. Note the time of the rehearsal scan — you need >5 minutes before the live run
ls -lt --time-style=+%H:%M:%S "$REPO"/quirk-output/findings-*.json | head -1
date +%H:%M:%S
```

**Step 4 is the one people get wrong.** `SESSION_BRACKET` is 5 minutes: the dashboard's
no-`scan_id` branch resolves endpoints by a time window around `MAX(scanned_at)` with no
`scan_run_id` filter, so two scans under five minutes apart **merge**. Two runs 4m26s apart
produced 34 certificates (17×2) and 14 CRITICAL. The scan takes 19 seconds, so this is
trivially easy to trigger.

Eyeball the print view — this is demo-prep task 4.1, still open:

```bash
xdg-open http://localhost:8512/print 2>/dev/null &
```

---

## Phase 9 — Live demo commands

This is the whole on-stage sequence. Three commands.

```bash
# Segment 5 — the scan. ~19 seconds.
docker exec chaoslab-mh-prober-1 \
  quirk --config /scan-config.yaml \
        --allow-internal-targets \
        --allow-cleartext-broker-probe
```

```bash
# The dashboard is already running from Phase 7. Just hard-refresh the browser.
# If it died, in the second terminal:
cd "$REPO" && source .venv/bin/activate && quirk serve --port 8512 --no-open
```

```bash
# Segment 7 — if you want the artifacts on screen rather than the browser.
ls -lt "$REPO"/quirk-output/ | head -12
```

**Rules for the live window:**

- **Run the scan exactly once.** If you must re-run inside five minutes, pin the dashboard
  with `?scan_id=<id>` instead of letting it resolve the latest.
- **Do not put the CLI output and the dashboard on screen at the same time.** The CLI reports
  15/100 with 5 CRITICAL; the dashboard reports 19/100 with 7 CRITICAL for the same clean
  scan. Known open defect: the dashboard emits the SAML finding twice, the CLI omits it
  entirely. Pick one surface.
- **Hard-refresh** after the scan so the dashboard picks up the new run.

Pin the dashboard to a specific run if you need to:

```bash
python3 -c "
import sqlite3
c=sqlite3.connect('$REPO/quirk-output/quirk.db')
for r in c.execute('SELECT id, scanned_at FROM scan_runs ORDER BY scanned_at DESC LIMIT 5'):
    print(r)
"
# then browse to http://localhost:8512/?scan_id=<id>
```

---

## Phase 10 — Teardown

```bash
# Stop the dashboard: Ctrl-C in its terminal, or
pkill -f "quirk serve"

# Stop the lab. No PROFILE_ARGS needed — `down` uses --profile "*".
cd "$LAB"
./lab.sh down
```

Reclaim disk, and remove the arm64 override if you created one:

```bash
./lab.sh clean                       # removes exited containers, prunes dangling images
rm -f "$LAB/docker-compose.arm64.yml"
git -C "$REPO" status --short        # should be clean
```

Full reset including volumes, if the lab state is ever suspect:

```bash
cd "$LAB"
PROFILE_ARGS="--profile multihost" ./lab.sh reset
```

Bringing the lab back up is roughly 30 seconds, plus a prober rebuild if `quirk/` changed.

---

## Recovery — when something breaks mid-prep

| Symptom | Cause | Fix |
|---|---|---|
| Score reports ~91/100 | Stale prober image, scoring v2 | Phase 4 with `-p chaoslab`, re-verify Phase 5 |
| Rebuild says "Built", nothing changes | Missing `-p chaoslab`; compose tagged a different image | Re-run with `-p chaoslab` |
| `mh-saml-idp` restarting / `exec format error` | amd64-only image on arm64 | Phase 2 |
| Dashboard shows 34 certificates, 14 CRITICAL | Two scans within `SESSION_BRACKET` (5 min) | Wait 5 minutes and scan once, or use `?scan_id=` |
| Exposure Map ring renders black | Cached JS bundle | `Ctrl`+`Shift`+`R` |
| `quirk: command not found` | Venv not active | `source "$REPO/.venv/bin/activate"` |
| `quirk serve: unrecognized arguments: --db-path` | That flag does not exist | Drop it; it finds `./quirk-output/quirk.db` |
| Wizard prompts instead of scanning | `--config` omitted | Add `--config /scan-config.yaml` |
| Scanner refuses the targets | RFC1918 guard | Add `--allow-internal-targets` |
| `externally-managed-environment` on pip | PEP 668 | Use the venv — mandatory on Ubuntu 23.04+ |
| 257 hosts / 2572 findings | Scanned the /24 as a CIDR | Use the shipped 31 explicit /32s |
| PDF export fails | Chromium missing | `playwright install chromium && sudo playwright install-deps chromium` |
| Lab won't start, CHAOS-05 pin violation | An image lost its tag | `git diff docker-compose.yml` |

---

## One-screen cheat sheet

```bash
# ---- setup (once) ----
export REPO=~/QU.I.R.K && export LAB="$REPO/quantum-chaos-enterprise-lab"
cd "$REPO" && source .venv/bin/activate

# ---- arm64 only, once per VM boot ----
docker run --privileged --rm tonistiigi/binfmt --install amd64

# ---- bring up ----
cd "$LAB" && ./lab.sh certs
docker compose -p chaoslab -f docker-compose.yml -f docker-compose.arm64.yml \
  --profile multihost up -d
docker compose -p chaoslab --profile multihost build mh-prober
docker compose -p chaoslab --profile multihost up -d --force-recreate mh-prober

# ---- GATE: must print 3.0 ----
docker exec chaoslab-mh-prober-1 \
  python -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"

# ---- scan (19s) ----
docker exec chaoslab-mh-prober-1 \
  quirk --config /scan-config.yaml --allow-internal-targets --allow-cleartext-broker-probe

# ---- dashboard ----
cd "$REPO" && quirk serve --port 8512 --no-open     # then Ctrl+Shift+R at :8512

# ---- teardown ----
cd "$LAB" && ./lab.sh down
```
