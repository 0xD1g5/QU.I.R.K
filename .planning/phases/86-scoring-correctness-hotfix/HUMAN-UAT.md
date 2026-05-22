# HUMAN-UAT-86: Scoring Correctness Hotfix — Operator Dashboard Walkthrough

**Phase:** 86 — Scoring Correctness Hotfix
**Plan:** 86-03 (Wave 3: Release Engineering + Operator UAT)
**Date:** 2026-05-22
**Version under test:** v4.10.1
**Author:** gsd-executor (operator fills Result field below)

---

## Context

Phase 86 corrects a triple-layer bug that caused the overall readiness score to always
display `100 / EXCELLENT` regardless of actual posture:

1. **Backend** (`quirk/intelligence/scoring.py`): The aggregator `_clamp(sum, 0, 100)` was
   replaced with `int(round(sum / 1.5))`. Canonical test case:
   subscores 25+25+23+3+25+19 = 120 → before: **100 EXCELLENT** / after: **80 GOOD**.

2. **Frontend** (`ScoreGauge.tsx`): Added `maxValue?: number` prop (default 100) and
   rewrote `_gaugeColor` to operate on a normalized fraction. Six executive-page subscore
   gauges now pass `maxValue={25}`; the standalone Data at Rest tab gauge (data-at-rest.tsx)
   also passes `maxValue={25}`.

Plan 01 commit: `7d0f71e` — backend fix
Plan 02 commits: `fad2ced` (gauge), `620e5db` (wiring), `b9bab9e` (tests)
Dashboard rebuilt: `quirk/dashboard/static/` mtime 2026-05-22 07:58

---

## Pre-Flight Checklist (verify before starting UAT)

> **IMPORTANT — Browser cache:** If a dashboard tab is already open against an earlier
> revision of `quirk/dashboard/static/`, the browser will keep serving the stale bundle
> even after `quirk serve` restarts. **Close any existing dashboard tab AND open the new
> tab with a hard refresh (Cmd+Shift+R on macOS / Ctrl+Shift+R on Linux/Windows)** before
> running the visual walkthrough below. Encountered in Phase 86 first attempt — initial
> screenshot showed pre-fix gauges; hard refresh produced the post-fix screenshot.


Run each command from the QUIRK project root:

```bash
# 1. Confirm scoring formula is fixed
grep -n "int(round" quirk/intelligence/scoring.py
# Expected: line ~255 shows:  total_score = int(round(

# 2. Confirm six executive subscore gauges use maxValue={25}
grep -c "maxValue={25}" src/dashboard/src/pages/executive.tsx
# Expected: 6

# 3. Confirm Data at Rest tab gauge uses maxValue={25}
grep -c "maxValue={25}" src/dashboard/src/pages/data-at-rest.tsx
# Expected: 1

# 4. Confirm version
python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
# Expected: 4.10.1
```

---

## Step 1: Start the chaos lab

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up
./lab.sh status
cd ..
```

Wait until all four services are healthy:
- `tls-cert-expired` on port 13444
- `tls-cert-selfsigned` on port 13445
- `tls-cert-untrusted-ca` on port 13446
- `tls-cert-rsa1024` on port 13447

---

## Step 2: Run the scan

```bash
python run_scan.py \
  --targets-file quantum-chaos-enterprise-lab/uat-targets-86.txt \
  --allow-internal-targets \
  --config /dev/null \
  --db-path /tmp/uat-86.db \
  --quiet
```

**Note on `--config /dev/null`:** If the scanner rejects `/dev/null` as a config path, generate
a minimal config first:

```bash
python run_scan.py init --output /tmp/uat-86-config.yaml
# edit /tmp/uat-86-config.yaml if needed — set targets to the four localhost:1344x addresses
python run_scan.py --config /tmp/uat-86-config.yaml --db-path /tmp/uat-86.db --allow-internal-targets --quiet
```

Capture the scan run ID from the output (look for `Scan run ID:` or `scan_run_id =`).

---

## Step 3: Verify CLI output

```bash
python run_scan.py report --db-path /tmp/uat-86.db --format json 2>/dev/null | \
  python -c "import sys,json; d=json.load(sys.stdin); s=d.get('score',{}); print('overall:', s.get('score')); print('rating:', s.get('rating')); print('subscores:', s.get('subscores'))"
```

**Expected:**
- `overall` < 100 (should be approximately 80 for a canonical tls-cert-defects scan)
- `rating` NOT "EXCELLENT" — should be GOOD, MODERATE, or FAIR
- `subscores` shows individual 0-25 values

**Pre-flight evidence** (fill in after running):

```
overall:   ___
rating:    ___
subscores: hygiene=___ modern_tls=___ identity=___ agility=___ data_at_rest=___ data_in_motion=___
sum:       ___  (should equal sum of above six values; divided by 1.5 should equal overall)
```

---

## Step 4: Start the dashboard

```bash
QUIRK_DB_PATH=/tmp/uat-86.db python run_scan.py serve --no-open
```

Dashboard will start at `http://127.0.0.1:8512/`.

Wait for the uvicorn startup message: `Application startup complete.`

---

## Step 5: Operator Visual Walkthrough

Open `http://127.0.0.1:8512/` in a browser and navigate to the most recent scan.

### Pass Criterion 1 — Executive Summary: Overall gauge

- [ ] The large central gauge shows an overall readiness number **less than 100**
      (should match the CLI output from Step 3)
- [ ] The rating badge (EXCELLENT / GOOD / MODERATE / FAIR / POOR) is **NOT "EXCELLENT"**
- [ ] The arc color reflects the standard 0-100 thresholds (overall gauge keeps default maxValue)

**Operator observation:**

```
Overall value seen:   ___
Rating badge seen:    ___
Arc color:            ___ (green / amber / red)
PASS / FAIL:          ___
```

---

### Pass Criterion 2 — Executive Summary: Six subscore radials

For each of the six subscore radials, confirm the color matches the fraction `value / 25`:

| Subscore | Threshold → Color | Expected color (given value) | Operator: value seen | Operator: color seen | P/F |
|----------|-------------------|------------------------------|----------------------|-----------------------|-----|
| Hygiene | ≥ 20/25 (≥ 80%) → **green** / 12.5–19 → **amber** / < 12.5 → **red** | ___ (fill from CLI output) | ___ | ___ | ___ |
| Modern TLS | same thresholds | ___ | ___ | ___ | ___ |
| Identity | same thresholds | ___ | ___ | ___ | ___ |
| Agility | same thresholds | ___ | ___ | ___ | ___ |
| Data at Rest | same thresholds | ___ | ___ | ___ | ___ |
| Data in Motion | same thresholds | ___ | ___ | ___ | ___ |

**Canonical reference values from trigger scan (2026-05-22):**
- Hygiene 25 → fraction 25/25 = 1.0 → **green** (before fix: always red regardless of value)
- Agility 3 → fraction 3/25 = 0.12 → **red**
- Data in Motion 19 → fraction 19/25 = 0.76 → **amber**

> If the scan against `tls-cert-defects` returns different subscore values, look up the
> expected color using the thresholds above (≥ 20 = green, 12.5–19 = amber, < 12.5 = red).

---

### Pass Criterion 3 — Data at Rest tab: Standalone gauge parity

Navigate to the **Data at Rest** tab in the sidebar.

- [ ] The large standalone ScoreGauge at the top of the Data at Rest page shows the
      **same numeric value** as the Data at Rest subscore radial on the Executive Summary page
- [ ] Its color matches the same fraction-of-25 thresholds:
      - value ≥ 20 → green
      - value 12.5–19 → amber
      - value < 12.5 → red
- [ ] If Data at Rest = 25 (perfect): gauge MUST be **green** (before fix it was always red,
      because 25 was interpreted against a 0-100 scale)

**Operator observation:**

```
Data at Rest value on Executive Summary:    ___
Data at Rest value on Data at Rest tab:     ___  (must match)
Color on Data at Rest tab gauge:            ___ (green / amber / red)
Expected color given fraction of 25:        ___
PASS / FAIL:                                ___
```

---

### Pass Criterion 4 — Screenshot

Take a screenshot of:
1. The Executive Summary view showing the corrected overall gauge and six colored subscore radials
2. The Data at Rest tab showing the standalone gauge with correct color

Save as:
- `.planning/phases/86-scoring-correctness-hotfix/uat-86-executive.png`
- `.planning/phases/86-scoring-correctness-hotfix/uat-86-data-at-rest.png`

(Or a single stitched image: `.planning/phases/86-scoring-correctness-hotfix/uat-86-dashboard.png`)

---

## Out of Scope

The CLI HTML report (`quirk/reports/html_renderer.py`) and PDF report (`quirk/reports/executive.py`)
are **deferred to v5.0** per D-14 / RENDER-CLI-01 / RENDER-PDF-01. Mismatch between the dashboard
and the HTML/PDF renderers is **expected** in v4.10.1. Do NOT fail this UAT on their behalf.

---

## Overall Result

```
Date completed:      2026-05-22
Operator:            Digs
Scan ID:             (tls-cert-defects live scan)
DB path:             /tmp/uat-86.db
Dashboard URL:       http://127.0.0.1:8512/

Pass Criterion 1 (Overall gauge < 100, non-EXCELLENT):    PASS
Pass Criterion 2 (Six subscore radials correct colors):   PASS (after hard-refresh)
Pass Criterion 3 (Data at Rest tab parity):               PASS
Pass Criterion 4 (Screenshots captured):                  PASS — uat-86-hf2.png (post-hard-refresh)
```

**Result:** PASS

Notes:
- Initial screenshot `uat-86-hf1.png` showed subscore radials still rendering with the old (red) color logic — diagnosed live as a stale browser bundle: the dashboard tab was open against the pre-rebuild static assets even though `quirk/dashboard/static/` had been refreshed by commit `620e5db`.
- After a hard browser refresh (Cmd+Shift+R), all four pass criteria held: overall < 100 / not EXCELLENT, subscore radials correctly colored per fraction-of-25 (Hygiene=25 green, Agility=3 red, etc.), Data at Rest standalone tab gauge matches the Executive Summary radial value AND color.
- Evidence file: `uat-86-hf2.png` (the canonical "fix verified" screenshot).
- Follow-up captured into durable memory: the `npm run build` rebuild trap (already in `feedback_dashboard_build_required.md`) has a sibling — already-open browser tabs hold the prior bundle. Future UAT walkthroughs should start with a hard refresh as step 1.

---

*This UAT walkthrough was authored by gsd-executor as part of Phase 86 plan 86-03.*
*CLI HTML/PDF renderers deferred to v5.0 Phase 01 (D-14, RENDER-CLI-01, RENDER-PDF-01).*
