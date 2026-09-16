# QU.I.R.K. Client Demo — Run of Show

**Date:** 2026-09-18 · **Slot:** 30–45 minutes · **Segments:** 7

Every figure in this document was measured on the rehearsal run of 2026-09-16
(scan stamp `20260916-145333`). Nothing here is estimated.

Follow the order. Most of the ways this demo goes wrong are sequencing
failures, not command failures.

| | |
|---|---|
| Scan wall clock | 18.4s |
| Estate | 37 hosts / 370 ports |
| Headline score | 15 / 100 · POOR |
| Findings | 5 CRITICAL / 14 HIGH / 33 MEDIUM |
| Scoring model | v3.0 |

---

## T−30 — Pre-flight

Run all six before anyone joins. Each has an expected output. If one
disagrees, fix it now rather than discovering it in segment 5. Checks 02 and
05 are the ones that have actually bitten.

### 01 — Lab is up

```bash
docker ps --format '{{.Names}}' | wc -l
```

Expect **42**. If 0, see *If it goes wrong*.

### 02 — Scoring model inside the prober

```bash
docker exec chaoslab-mh-prober-1 python -c \
  "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"
```

Expect **3.0**. Never quote a score before seeing this.

> **Why this check exists.** A stale prober image silently runs superseded
> scoring v2 and reports **91/100** on the same evidence that v3 scores
> 15/100. Exit 0, eleven report files, a confident number, no warning.
> `Platform version` still reads 5.21.0 either way — it is not a staleness
> signal.

### 03 — Dashboard is listening

```bash
lsof -nP -iTCP:8512 -sTCP:LISTEN
```

Expect one `Python … LISTEN` row. If empty, start it detached:

```bash
nohup .venv/bin/python run_scan.py serve --port 8512 > /tmp/quirk-serve.log 2>&1 &
```

### 04 — All five downloads are available

```bash
curl -s http://127.0.0.1:8512/api/reports/latest/manifest
```

Expect `"available": true` on all five formats.

### 05 — Hard-refresh the browser

**Cmd-Shift-R** on every tab you will show.

> **Why this check exists.** A cached `index.html` serves a stale JS bundle.
> This is what made an already-fixed exposure-map defect look still-broken for
> a full round of investigation.

### 06 — Close anything you do not want on screen

Terminal cleared, editor closed, notifications silenced.

---

## Run of show

Clock times are cumulative from the start of your slot. Beats are prompts to
speak around, not a script to read.

### 1 — Intro of self and team · *not in this slot*

Already covered in the earlier presentation. **Do not repeat it.** Open
straight into segment 2.

### 2 — What QU.I.R.K. is, and why it exists · ~5 min · → 0:05

- **The problem:** organisations cannot answer "what cryptography are we
  actually running?" — and post-quantum migration makes that answer mandatory
  rather than nice to have.
- **What it does:** discovers TLS, SSH, JWT/API, container, source-code and
  cloud KMS crypto posture, then produces a CycloneDX CBOM, a quantum-readiness
  score, and a prioritised remediation roadmap.
- **Why open source:** a crypto inventory tool you cannot read the source of is
  asking for a great deal of trust. Auditability is the product.
- Keep this tight. The live scan is the strongest thing you have — do not spend
  its oxygen here.

### 3 — Key platform features · ~7 min · → 0:12

A few sentences each, no deep dives.

- **Discovery across six domains** — not just TLS: identity, data at rest, data
  in motion, agility signals, hardware.
- **CycloneDX CBOM** — a standards-based cryptographic bill of materials, not a
  proprietary report format.
- **Readiness scoring** — a single defensible number with named drivers, which
  segment 6 covers properly.
- **Prioritised roadmap** — NOW / NEXT / LATER with owner placeholders and
  point-lift per item.
- **Compliance mappings with staleness enforcement** — every catalog carries a
  verification date and CI fails when one goes stale.
- **Deliverables** — branded HTML, PDF, DOCX, and CBOM in JSON and XML,
  downloadable straight from the dashboard.

### 4 — The chaos lab · ~6 min · → 0:18

- **What it is:** a deliberately broken enterprise estate in Docker — 42
  containers, 37 hosts on an isolated subnet, known-bad crypto planted
  throughout.
- **Why it exists:** you cannot validate a scanner against an estate whose
  answers you do not already know. The lab is the oracle.
- **Anyone can run it** — ships with the project, one command, no licences.
- The per-host expectations are **generated from measured output**, not
  hand-written — which matters, because hand-written expectations are how
  scanners end up grading their own homework.

> **Know this before a technical audience asks.** The oracle honestly records
> which lab hosts **do not** demonstrate what their names imply: the SHA-1 and
> broken-chain hosts are currently indistinguishable from a generic host, and
> the crown jewel is indistinguishable from the legacy-TLS hosts. If asked, say
> so plainly — it is recorded precisely so nobody is surprised by it.

### 5 — Live scan · ~10 min · → 0:28 · **the centrepiece**

```bash
docker exec chaoslab-mh-prober-1 quirk --config /scan-config.yaml
```

> **⚠ Scan exactly once.** The scan takes 18 seconds and `SESSION_BRACKET`
> merges any two scans less than **5 minutes** apart. A second run makes the
> dashboard read **14 CRITICAL across 34 certificates** instead of 7 across 17,
> and it will look like the scanner is unstable. If you must re-run, wait out
> the five minutes or pin the dashboard with `?scan_id=`.

**They see:** 37 hosts scanned · 5 CRITICAL · 14 HIGH · 33 MEDIUM ·
**15/100** · 12 output files · done in under 20 seconds.

**Say this while it runs:**

- Narrate the phases rather than waiting in silence — it is short enough that
  dead air is the only real risk.
- **Land the finding, not the number:** 5 CRITICAL on an estate a conventional
  vulnerability scanner would call clean, because nothing here is unpatched —
  it is all correctly-configured obsolete cryptography.

**Then show the exposure map:**

- **18 nodes, 34 edges** — 19 shared-key relationships, 15 shared-CA
  dependencies.
- The line to land: **"the largest shared key spans five endpoints — one key
  compromise takes all five with it."**
- **ChaosLab-RootCA carries 10 dependants.** One CA, ten endpoints inheriting
  its fate.
- One node is marked a crown jewel — declared by the operator in config, not
  guessed by the tool.

### 6 — Scoring · ~10 min · → 0:38 · **strongest material**

- **Open with the v2→v3 story.** This same estate scored **91/100** under the
  previous model and **15/100 POOR** under the current one — on byte-identical
  evidence. The old model was flattering and wrong.
- **Why it was wrong:** it diluted real weaknesses across a denominator of
  everything probed, so adding healthy endpoints raised the score. Measuring
  more made you look better. That is a scoring bug, not a posture improvement.
- **Walk the arithmetic.** A client who checks it should find it holds:

  > **Rollup:** 76 ÷ 1.25 = **61**, capped to **15 / 100**
  > **Cap reason:** 5 open CRITICAL findings — score limited to 15 (computed 61)

**The two halves, explained:**

- **The divisor (1.25)** is coverage honesty: 5 of 6 domains were assessable,
  so the score is not allowed to claim full confidence.
- **The cap** is consequence: no estate with 5 open CRITICALs gets to present as
  healthy, whatever the weighted average says.
- **Named drivers**, not a black box: expired certificates −8, assessment
  visibility blockers −5, scan error rate −5 — and positives too, PQC-hybrid key
  exchange +8, ECDSA adoption +4.
- That last pair is worth pointing at: **the tool gives credit for
  X25519MLKEM768 where it finds it.** It is not only looking for bad news.

### 7 — Reporting wrap-up · ~7 min · → 0:45

- On the executive page, use the **five download buttons** — HTML, PDF, DOCX,
  CBOM JSON, CBOM XML.
- Open the **PDF**. This is the consulting-grade deliverable and the artifact a
  client actually receives.
- Show that the same rollup arithmetic from segment 6 appears in the document —
  the report and the dashboard tell one story.
- Close on the CBOM: **CycloneDX, an open standard**, so the inventory outlives
  the tool that produced it.

> **⚠ Do not press Export PDF in this session.** It sits immediately beside the
> five downloads and produces a **different document with a different headline
> score**: 19/100 with 7 CRITICAL, against the consulting report's 15/100 with
> 5 CRITICAL. Same scan. Two finding producers with different rule sets;
> consolidating them is tracked work. Use the five downloads only. If asked why
> both buttons exist, say they are two pipelines and convergence is on the
> roadmap.
>
> A trap if you spot-check under pressure: **76 appears in both surfaces meaning
> different things** — the report's pre-cap value and the dashboard's post-cap
> computed value. It will look like agreement.

---

## Timing budget

| Segment | Target | Cumulative | If short on time |
|---|---|---|---|
| 1 · Intro | — | — | Already done; skip entirely |
| 2 · What it is | 5 min | 0:05 | Trim to 3 — keep "why open source" |
| 3 · Features | 7 min | 0:12 | **Compress here first** — cut to 4 |
| 4 · Chaos lab | 6 min | 0:18 | Trim to 4; keep "the lab is the oracle" |
| 5 · Live scan | 10 min | 0:28 | Scan is 18s; the rest is narration |
| 6 · Scoring | 10 min | 0:38 | **Protect this** |
| 7 · Reporting | 7 min | 0:45 | Downloads + PDF is the minimum |

---

## Q&A prep

### "Your roadmap says 90.5% of the scan failed. Is the scanner unreliable?"

No — that is the sweep finding closed ports. The item is now titled **Increase
scan coverage** and says so explicitly.

Of 370 probed ports: **308 had nothing listening**, 23 needed an optional extra
that was not installed, **4 were genuine probe failures**, and 35 returned
crypto evidence. The real failure rate is **1.1%**.

If pressed on score impact: scoring it at the true 1.1% moves the estate from 15
to 18. Still POOR — the CRITICAL findings are what cap it, not this.

### "Why did the score change so much between versions?"

The previous model divided weaknesses by everything probed, so observing more
healthy endpoints raised the score. An estate could improve its number by
scanning more of itself.

v3 divides each penalty by the population its own numerator is drawn from, and
adds a consequence ceiling so open CRITICALs cap the headline. Same evidence,
91 → 15. The old number was the wrong one.

### "Is 15/100 not alarmist?"

It is a deliberately unflattering number on a deliberately broken estate. The
point of the cap is that a posture with five open CRITICALs should not be able
to average its way to respectable.

Note the score also moves **up** on real evidence — PQC-hybrid key exchange
earns +8 here. It is not a one-way ratchet.

### "How do we know the findings are real and not generated?"

Every expectation in the lab oracle is **generated from measured scanner
output**, and the oracle records the cases where a host does not demonstrate
what its name implies. Where coverage is absent it is recorded as a gap rather
than papered over.

### "Can we run this against our own estate?"

Yes — the scanner takes a config with your CIDRs and credentials; the chaos lab
is only the validation harness. Be ready to talk about scan scoping and the
read-only posture, and do not over-commit on timelines in the room.

---

## If it goes wrong

Three of these four fail silently — exit 0, no error — which is why the
pre-flight checks exist at all.

### The lab is down (`docker ps` returns 0)

Bring it up **with the rebuild flags** — both matter:

```bash
cd quantum-chaos-enterprise-lab
docker compose -p chaoslab -f docker-compose.yml --profile multihost up -d --build
```

Omit `-p chaoslab` and compose builds a differently-tagged image, reports
"Built", and changes nothing. Takes a few minutes — not something to start
mid-demo.

### The scan reports 91/100

You are running a stale prober on scoring v2. **Do not quote the number.**
Rebuild as above, then re-run pre-flight check 02 and confirm it prints `3.0`.

### The dashboard shows old or doubled numbers

Doubled (14 CRITICAL / 34 certificates) means two scans merged inside the
5-minute bracket — wait it out or pin with `?scan_id=`. Merely stale means a
cached bundle — **Cmd-Shift-R**.

### A download 404s or the PDF is missing

Check the manifest (pre-flight 04). A format reporting `available: false`
carries a written reason. Fall back to the HTML report, which has the same
content — do not debug it live.
