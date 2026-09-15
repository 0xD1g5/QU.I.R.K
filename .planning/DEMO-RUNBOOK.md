---
project: QU.I.R.K.
type: runbook
status: active
audience: presenter (colleague demo)
demo_date: 2026-09-18
duration_target: 30-45 minutes
source_of_truth: .planning/HANDOFF.json -> demo_walkthrough_confirmed
updated: 2026-09-15
---

# Demo Runbook — colleague presentation

Segment structure is the operator-confirmed seven-segment walkthrough recorded in
`HANDOFF.json` (`demo_walkthrough_confirmed`, confirmed 2026-09-14). This file adds
timings, talk tracks, the exact commands, and the hazards that bite during the live
portion. **It does not invent a new path** — rehearse this one.

Segment 1 (intro of self + team) was covered in a prior presentation and is not part of
this slot, so six segments carry the time.

---

## 0. Target environment

Ubuntu guest on VMware Fusion, Apple Silicon MacBook Pro. That guest is **arm64**.
Read §1 before anything else — one lab image has no arm64 build.

Two things are *easier* here than on the macOS Docker Desktop host the chaos-lab docs
were written against:

- Docker runs natively on Linux in the guest, so the `10.80.0.0/24` bridge **is**
  routable from the Ubuntu host. The docs' "not routable from a macOS Docker Desktop
  host" caveat does not apply to you. The scan still runs from inside `mh-prober` —
  that is the documented, measured path and the one the oracle was built from. Do not
  change it for the demo.
- The dashboard and the prober share `./quirk-output` by bind mount either way.

---

## 1. BLOCKER TO CLEAR FIRST — `mh-saml-idp` has no arm64 image

`kenchan0130/simplesamlphp:1.19.7` publishes a **single-architecture manifest,
`linux/amd64` only** (verified against the Docker Hub registry API, 2026-09-15). There
is no arm64 variant under that tag. Every other image in the `multihost` profile is
multi-arch and fine:

| Image | arm64? |
|---|---|
| `nginx:1.28.0` (x16), `httpd:2.4.63` (x7) | yes |
| `postgres:16.6`, `mysql:8.0.40`, `redis:7.4.1-alpine` | yes |
| `osixia/openldap:1.5.0` | yes (`amd64`, `arm`, `arm64`) |
| `smallstep/step-ca:0.28.1` | yes |
| `quay.io/minio/minio`, `quay.io/minio/mc` | yes |
| `lscr.io/linuxserver/openssh-server` | yes |
| `mh-prober` | built from this repo — builds native |
| **`kenchan0130/simplesamlphp:1.19.7`** | **NO — amd64 only** |

### Detect it

```bash
docker compose -p chaoslab --profile multihost ps mh-saml-idp
docker logs chaoslab-mh-saml-idp-1 2>&1 | tail -5
```

A `Restarting` / `Exited` state, or `exec format error`, is this problem.

### Option A (recommended) — emulate, keep the oracle numbers valid

In the Ubuntu guest, once per boot:

```bash
docker run --privileged --rm tonistiigi/binfmt --install amd64
```

Then pin the service in `quantum-chaos-enterprise-lab/docker-compose.yml`:

```yaml
  mh-saml-idp:
    platform: linux/amd64
    image: kenchan0130/simplesamlphp:1.19.7
```

Recreate just that one container. It serves static IdP metadata, so qemu emulation costs
nothing the audience will see. This keeps all 31 targets in the scan, which is what the
measured oracle (400 findings, 5 CRITICAL, 15/100) was derived from.

Note this is **not** Docker Desktop's Rosetta path — that does not exist in a native
Linux guest. `binfmt_misc` + qemu-user-static is the mechanism here.

### Option B — drop the host, know what changes

Remove `10.80.0.41` from `multihost-scan-config.yaml` targets and drop `saml_targets`.
Grounded prediction, **verify before relying on it**:

- The CLI's **5 CRITICAL are the five expired certificates** — `10.80.0.11`,
  `.101`, `.102`, `.103`, `.104` (oracle lines 515, 534-537). SAML is not among them;
  the CLI omits the SAML finding entirely (known defect, §5 hazard 3). So
  **`15/100` and 5 CRITICAL should hold** on 30 hosts.
- The dashboard's extra 2 CRITICAL *are* the duplicated SAML finding. Dropping the host
  would likely close the CLI-vs-dashboard divergence — 19/7 becomes 15/5.

That is a tidier demo but it walks away from the measured oracle and from a talking
point that plays well (§6). Prefer Option A.

### Option C — run the demo on the amd64 machine where the oracle was measured

Zero risk, zero prep. If the Ubuntu-on-Fusion guest is a convenience rather than a
requirement, take this.

---

## 2. Pre-flight — T-60 minutes, not T-5

Run the whole live path once, end to end, on the actual demo machine. Every constraint
below was discovered by something failing, not by prediction.

```bash
cd quantum-chaos-enterprise-lab

# 1. Bring the estate up
PROFILE_ARGS="--profile multihost" ./lab.sh up

# 2. Rebuild the prober. `lab.sh up` runs `compose up -d` with NO --build and
#    silently reuses a stale image. The -p chaoslab is REQUIRED: without it compose
#    derives the project name from the directory, tags a DIFFERENT image, reports
#    "Built", and changes nothing.
docker compose -p chaoslab --profile multihost build mh-prober
docker compose -p chaoslab --profile multihost up -d --force-recreate mh-prober

# 3. GATE: verify the scoring model INSIDE the prober. Must print 3.0.
docker exec chaoslab-mh-prober-1 \
  python -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"

# 4. Confirm the estate — expect 33 containers, mh-saml-idp among them
docker compose -p chaoslab --profile multihost ps
```

**If step 3 prints anything but `3.0`, stop.** A stale prober silently reproduces the
superseded v2 model and reports **91/100** on evidence that scores **15/100** under v3 —
exit 0, eleven report files, a confident wrong number, no warning. `Platform version` is
not a staleness signal. That 76-point gap is also the core of segment 6, so getting it
wrong costs you the best material in the deck.

Then rehearse the scan itself once (§4), read the numbers, and **let the 5-minute clock
run out before the real demo** (§5 hazard 2).

---

## 3. Time budget

| # | Segment | 45-min | 30-min |
|---|---|---|---|
| 2 | What QU.I.R.K. is, why we built it, why open source | 6 | 5 |
| 3 | Key platform features | 6 | 4 |
| 4 | The chaos lab | 5 | 3 |
| 5 | **LIVE: scan + dashboard** | 8 | 7 |
| 6 | **Scoring** | 8 | 6 |
| 7 | Reporting wrap-up | 5 | 4 |
| — | Q&A | 7 | 1 + overflow |
| | **Total** | **45** | **30** |

Segments 5 and 6 are the show. If you are running long, cut segment 3 — the feature list
is in the README and nobody remembers a bulleted capability tour. Do not cut 6 to protect
7; the scoring story is stronger than the report walkthrough.

---

## 4. Segment-by-segment

### Segment 2 — What it is, why we built it, why open source (6 min)

Three beats, in this order.

**The problem.** NIST finalized ML-KEM, ML-DSA and SLH-DSA in August 2024. Every
standards body now says the post-quantum transition starts with a complete cryptographic
inventory. Ask most organizations where they run RSA-2048 and you get silence, or a
spreadsheet that was accurate eighteen months ago.

*Analogy:* there is no migration without a map, and nobody has the map. QU.I.R.K. draws
it automatically.

**Why the clock is already running.** Harvest Now, Decrypt Later. Traffic captured today
gets decrypted when the hardware arrives.

*Analogy:* an adversary photocopying your locked filing cabinet today, betting they'll
have the key in ten years. If the contents still need to be secret in 2036, they are
already compromised.

**Why open source.** A cryptographic inventory tool asks a client to trust it with a map
of their weakest crypto. That trust is easier to earn when the classifier logic, the
scoring model and the chaos lab it was validated against are all readable. It also means
a client can re-run the assessment themselves after remediation without buying anything —
which, in presales, is a feature and not a giveaway.

Have ready: MIT licensed, on PyPI as `quirk-scanner`, GHCR multi-arch image, Sigstore
attestation via PyPI Trusted Publishers. **No `curl | bash` installer** — a deliberate
non-feature, because piping HTTP to a shell defeats the integrity guarantees the
attestation exists to provide. That detail lands well with a security audience.

### Segment 3 — Key platform features (6 min)

A few sentences each, not a tour. Group them so they hold together:

- **Agentless discovery across the whole surface** — TLS endpoints, SSH, JWT/OIDC issuers,
  email (SMTP/IMAP/POP3 incl. STARTTLS stripping), brokers (Kafka/RabbitMQ/Redis),
  container images via Syft, source via Semgrep, and code-signing posture via LDAP+EKU.
  Nothing to install on the target.
- **Cloud and identity** — AWS (ACM, KMS, CloudFront, ELBv2), Azure (Key Vault, App
  Gateway), GCP (Cloud KMS incl. PQC, Cloud SQL, GCS CMEK), HashiCorp Vault (Transit,
  incl. ml-dsa/slh-dsa), Kubernetes.
- **Hardware and OT** — SSH banner -> HTTP management interface -> SNMP cascade classifies
  vendor, model and CNSA 2.0 remediation tier. Crypto-bridge detection flags a device
  whose weak on-device cipher is mitigated by upstream TLS — evidence-backed, and
  deliberately **never scored**.
- **The deliverable** — CycloneDX CBOM in JSON and XML, a 0-100 readiness score with six
  subscores, and PDF / DOCX / HTML / CLI reports from one shared content model.
- **Distributed mode** — on-prem sensors scan isolated segments and push to a central
  console that merges into one CBOM and one score. This is the one that matters for a
  segmented client network.
- **Air-gapped operation** — fully offline. Relevant for exactly the government and
  enterprise engagements where PQC readiness is most urgent.

### Segment 4 — The chaos lab (5 min)

The point of this segment is credibility, not the lab.

*Analogy:* a crash-test facility. You do not trust a car's safety rating because the
manufacturer says so — you trust it because someone drove one into a wall on camera. The
chaos lab is the wall.

- 125 services across a dozen profiles. The `multihost` profile is a **simulated
  enterprise estate**: 33 containers on a dedicated `/24`, each with a static address and
  its own deliberate crypto posture — expired certs, RSA-1024, SHA-1, broken chains,
  plaintext intranet, a no-TLS Postgres and MySQL, an unauthenticated Redis, OpenLDAP on
  389 cleartext, a SAML IdP with an RSA-1024 signing cert, MinIO with one encrypted and
  one deliberately unencrypted bucket, and one genuinely healthy modern-TLS host as the
  contrast case.
- **No published host ports.** Everything is `expose:` only, so the subnet is
  unreachable from outside. Scans run from `mh-prober` at `10.80.0.200`, in-network —
  the same vantage point a real sensor has.
- **It ships in the repo.** Anyone can `./lab.sh up` and reproduce every number you are
  about to show.

**The honesty beat — do not skip this one.** The lab's expected-results oracle records
three classes of *honest gap*: hosts that return INFO only; postures that are scored but
never reported (the unencrypted S3 bucket and the plaintext Postgres both reach
`evidence_summary` and emit no finding); and postures with **no distinguishing
detection** — the SHA-1 and broken-chain hosts are currently indistinguishable from a
generic host, and so is the crown jewel from the legacy-TLS hosts.

Know these cold before a technical audience finds them. A tool that documents what it
cannot see is more credible than one that claims full coverage, and this is the moment to
make that argument on your own terms rather than under cross-examination.

### Segment 5 — LIVE scan (8 min)

Read §5 hazards first. Then:

```bash
docker exec chaoslab-mh-prober-1 \
  quirk --config /scan-config.yaml \
        --allow-internal-targets \
        --allow-cleartext-broker-probe
```

**19 seconds wall clock**, measured, byte-identical findings across three consecutive
runs. Short enough to run live with no dead air — but narrate through it rather than
watching the spinner in silence.

Both flags are required and both are worth one sentence:

- `--config` is required; there is no `scan` subcommand and no `--targets` flag. Without
  it you drop into the interactive wizard on stage.
- `--allow-internal-targets` is required because `10.80.0.0/24` is RFC1918 and **the
  scanner refuses private space by default** — a deliberate SSRF guard. Saying that out
  loud turns a flag into a feature.

Expect: **400 findings — 5 CRITICAL / 14 HIGH / 33 MEDIUM / 16 LOW / 332 INFO** across 37
hosts (31 subnet targets + 6 connector pseudo-hosts), 370 endpoints, 38 assessable,
readiness **15/100 POOR**.

Then the dashboard, from the repo root on the host:

```bash
quirk serve --port 8512 --no-open
```

`quirk serve` has **no `--db-path` flag** — it discovers `./quirk-output/quirk.db`
itself. `--db-path` exits 2 with `unrecognized arguments`.

Dashboard route, in order:
1. **Executive Verdict + score** — the headline.
2. **Findings** — filter to CRITICAL, show the five expired certificates.
3. **CBOM tab** — this is the deliverable. CycloneDX, exportable.
4. **Exposure Map** — 12 nodes, 19 edges, three shared keys, the largest spanning five
   endpoints. The line is: *"one key compromise takes five endpoints with it."* The
   crown-jewel ring and the shared-CA hub nodes both render — this was going to be cut
   and is now showable.

### Segment 6 — Scoring (8 min)

**Strongest material in the deck.** The story is that the tool's own scoring model was
wrong, we found it by measuring, and we fixed it.

Same estate, same evidence, two models:

| Model | Score | Band |
|---|---|---|
| v2 (superseded) | **91/100** | FAIR (capped) |
| **v3 (current)** | **15/100** | **POOR** |

A **76-point** swing on identical evidence. What v2 got wrong was **denominator
blindness** — it divided weakness counts by the total probe count. Five expired
certificates over 370 probed endpoints is `-0.19`, which rounds away to nothing. The same
five over the 17 certificates actually observed is `-4.1`.

*Analogy:* grading a building on a curve that gets more generous the more empty rooms you
add. Under v2, widening the port sweep **raised** the score on infrastructure that had not
changed — 89 with 54 endpoints, 91 with 219. Taking HIGH findings from 3 to 11 moved the
score by zero. v3 grades the rooms that actually have doors.

Then walk the cap, which is where the arithmetic is now visible on the scorecard:

> `76 / 1.25 = 61, capped to 15 / 100`

Five open CRITICAL findings limit the score to 15 regardless of the computed 61. Note
that this line printed `= 15` until 2026-09-14 — it divided wrong on a client-facing
scorecard. A client checking the arithmetic would have caught it. It is fixed across all
five render sites from one shared helper.

Six subscores: Hygiene, Modern TLS, Identity, Agility, Data at Rest, Data in Motion.
Agility carries a `+8.0` PQC-hybrid bonus that anchors the post-quantum ceiling.

**Because scores moved 76 points, scores from v5.20+ are not comparable with pre-5.20
scores.** Say that before anyone asks.

### Segment 7 — Reporting wrap-up (5 min)

One shared content model drives CLI markdown, HTML, PDF and DOCX — so the executive
summary, the scorecard and the finding detail cannot drift between surfaces.

- Show the **written executive narrative**. This is the consultant deliverable: prose a
  client can read, not a finding dump.
- Show the **prioritized remediation roadmap**.
- Show the **CBOM** as compliance evidence — CycloneDX JSON/XML you can attach to an
  audit response against NIST PQC, CNSA 2.0, FIPS 140-3 / CMVP.
- Close on the engagement model: install, configure, scan, hand over a CBOM and a
  readiness report **inside a single working session**. You just did the scan part in 19
  seconds in front of them.

---

## 5. Live-demo hazards

Each of these was found by something actually failing.

**1. Stale prober reports 91/100.** Gate on `SCORING_VERSION == 3.0` inside the container
(§2 step 3). `lab.sh up` passes no `--build`. Rebuild with `-p chaoslab` or compose tags a
different image, says "Built", and changes nothing.

**2. Do not re-scan within 5 minutes.** `SESSION_BRACKET = 5 minutes` in
`quirk/dashboard/api/routes/scan.py`: the no-`scan_id` branch resolves endpoints by a time
window around `MAX(scanned_at)` with **no `scan_run_id` filter**, so two scans under five
minutes apart **merge**. Two runs 4m26s apart produced **34 certificates (17x2) and 14
CRITICAL**. The scan is 19 seconds, so this is trivially easy to trigger by accident —
a single nervous re-run mid-demo doubles your certificate count on screen.

> **Scan once.** If you must re-run, pin the dashboard with `?scan_id=<id>`.

**3. The CLI and the dashboard disagree on the same clean scan.** CLI reports **15/100
with 5 CRITICAL**; dashboard reports **19/100 with 7 CRITICAL**. This is not the merge —
it reproduces on one clean run. The dashboard emits
`Weak SAML signing certificate: RSA-1024` **twice** for the same `10.80.0.41:8080`, and
CRITICAL count drives the cap. The CLI has the opposite bug: it scores the SAML weakness
(`identity_saml_weak_signing_ratio: 0.0054` is in its own `evidence_summary`) and never
reports it. Root cause is architectural — `quirk/engine/findings_evaluator.py` has zero
SAML/Kerberos/DNSSEC rules while the dashboard route has all three.

> **Pick one surface and stay on it.** Do not put the CLI output and the dashboard on
> screen together. If someone catches it: it is a known open defect with a filed root
> cause, the duplicate is a rendering-path bug and not two real certificates, and the
> architectural fix is scoped as its own phase.

**4. Hard-refresh the dashboard (`Ctrl+Shift+R`) after any change.** A cached
`index.html` serves a stale bundle; a normal reload is not enough.

**5. Have the 90.5% answer ready.** The roadmap's NOW item reads *"Stabilize scan
reliability — scan error rate is 90.5%"*, which sounds like the scanner failed on 90% of
what it looked at. It is **335 of 370 probed ports being closed** on an 11-port sweep
across 31 hosts — a closed port counted as an error. If the roadmap is on screen, say it
before someone reads it aloud.

**6. Do not scan `10.80.0.0/24` as a CIDR.** The config targets 31 explicit `/32`s for a
reason: a full subnet sweep reported **257 hosts and 2572 findings** — 254 phantom
addresses at 10 INFO each, plus the Docker bridge gateway at `.1` surfacing a spurious
CRITICAL. It buries the real topology and makes the Exposure Map unreadable.

---

## 6. Questions you should expect

| Question | Answer |
|---|---|
| "Why is the score so low? Is the tool just harsh?" | It is calibrated against this lab, which is deliberately awful. 29% of its certificates are expired. The cap is explicit and shown: 5 open CRITICAL limits the score to 15 regardless of the computed 61. |
| "Did you tune the model to make the lab look bad?" | No, and there is a standing decision against it — never tune to a target. v3 fixed a denominator defect that was found by measurement; the lab happens to be where it was visible. |
| "What does it miss?" | Named, on the record, in the oracle: three INFO-only hosts, two postures scored but not reported, and SHA-1 / broken-chain / crown-jewel hosts with no distinguishing detection today. |
| "Scores across versions?" | Not comparable pre-5.20. v3 moved this estate 76 points. |
| "Can it run in an air-gapped client environment?" | Yes, fully offline, agentless, no client-side install. |
| "How does it handle a segmented network?" | Distributed mode — sensors per segment push to a console that merges into one CBOM and one score. The lab has a `segmented-network` profile and a `distributed` compose file that prove it. |
| "How long on a real client estate?" | 19 seconds for 31 hosts / 370 endpoints here. Real estates are dominated by network round-trips and discovery breadth, not by the scanner. |

---

## 7. Final checklist

- [ ] §1 resolved — `mh-saml-idp` running, or Option B/C chosen deliberately
- [ ] `SCORING_VERSION` prints `3.0` **inside** `chaoslab-mh-prober-1`
- [ ] 33 containers up on the `multihost` profile
- [ ] Full path rehearsed end to end on the demo machine
- [ ] **More than 5 minutes** elapsed between the rehearsal scan and the live scan
- [ ] Dashboard hard-refreshed; Exposure Map renders the crown-jewel ring and CA hubs
- [ ] `/print` PDF eyeballed (carried open from demo-prep task 4.1)
- [ ] Decided which single surface — CLI or dashboard — carries the numbers
- [ ] 90.5% explanation rehearsed in one sentence
- [ ] Laptop on power; VM given enough RAM/CPU for 33 containers plus the dashboard
