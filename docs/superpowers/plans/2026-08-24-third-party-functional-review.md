# Third-Party Functional Review — Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an evidence-backed independent assessment of whether QU.I.R.K.'s shipped
code performs as its development documents define, plus a trackable action plan for every
gap found.

**Architecture:** Three passes. Pass 1 (Tasks 1–4) mechanically traces all 460 requirement
IDs to evidence and assigns a tier-stamped verdict, producing a traceability matrix. Pass 2
(Tasks 5–9) executes the real system — backend suite, frontend suite, chaos lab, live
browser walkthrough — and records actual output including failures. Pass 3 (Tasks 10–11)
converts everything into a findings report and a checkbox action plan.

**Tech Stack:** Python 3.14 (`.venv`), pytest 9.0.2, Node 26 / vitest / puppeteer-core,
Docker Compose v5.1.4, Chrome via claude-in-chrome MCP.

**Spec:** `docs/superpowers/specs/2026-08-24-third-party-functional-review-design.md`

## Global Constraints

- **Findings only. No fixes.** Not one defect is repaired in this plan, including trivial
  ones. A task that discovers a one-character bug records it and moves on.
- **No product code is written.** Analysis scripts live in the scratchpad directory
  `/private/tmp/claude-501/-Volumes-Digs-1TB-Development-quantum-apps-QUIRK/fc96b817-2a8d-49f3-83b4-dd937e0a38b9/scratchpad`
  and are never committed. Only the two Pass-3 deliverables are committed to the repo.
- **Never tune a result until it is green.** Actual output is the deliverable. A failing
  test is data, not a problem to solve.
- **Every verdict carries its evidence tier** (A/B/C/D as defined in spec §3).
- **Reviewed commit:** HEAD as of review start. Record the SHA in every artifact.
- Scratchpad shorthand below: `$SP` = the scratchpad path above. `$REPO` =
  `/Volumes/Digs-1TB/Development/quantum-apps/QUIRK`.

---

## File Structure

**Scratchpad (throwaway review tooling, never committed):**

| File | Responsibility |
|---|---|
| `$SP/parse_requirements.py` | Extract every requirement ID, milestone, claim state, and description text from all requirements documents → `requirements.json` |
| `$SP/parse_evidence.py` | Build Tier A/B/C/D evidence links → `evidence.json` |
| `$SP/build_matrix.py` | Join the two, assign verdicts → `matrix.json` + `matrix.md` |
| `$SP/evidence/` | Raw captured output from every executed command (pytest log, npm logs, lab output, API responses) |

**Committed deliverables (Pass 3 only):**

| File | Responsibility |
|---|---|
| `docs/reviews/2026-08-24-functional-review-findings.md` | The reviewer's report |
| `docs/reviews/2026-08-24-functional-review-action-plan.md` | Checkbox action plan |

---

## Task 1: Requirement Inventory

**Files:**
- Create: `$SP/parse_requirements.py`
- Output: `$SP/requirements.json`
- Read: `$REPO/.planning/REQUIREMENTS.md`, `$REPO/.planning/milestones/*-REQUIREMENTS.md`

**Interfaces:**
- Produces: `requirements.json` — a list of objects with keys `req_id` (str, e.g.
  `"HWLC-01"`), `milestone` (str, e.g. `"v5.13"`), `claimed_complete` (bool), `text`
  (str, the requirement's description), `source_file` (str).

- [ ] **Step 1: Confirm the parse format holds across all 27 documents**

Requirements are declared as markdown checkboxes with a bolded ID:

```
- [x] **HWLC-14**: Consultant can opt in to email/webhook notification when...
- [ ] **HWLC-20**: Consultant can schedule HWLC-13's on-demand `--check-in`...
```

Run this to confirm the pattern matches everywhere and to find any document using a
different shape:

```bash
cd "$REPO"
for f in .planning/REQUIREMENTS.md .planning/milestones/*-REQUIREMENTS.md; do
  n=$(grep -cE '^\s*-\s*\[[ x]\]\s*\*\*[A-Z]{2,6}-[0-9]{1,3}\*\*' "$f")
  echo "$n  $f"
done
```

Expected: a non-zero count for every file. Any file reporting `0` uses a different format
and its shape must be inspected with `head -40` and handled explicitly in Step 2. **Record
any such file — an inconsistently formatted requirements document is itself a finding.**

- [ ] **Step 2: Write the parser**

```python
#!/usr/bin/env python3
"""Pass 1a: extract every requirement ID from every requirements document."""
import json, re, sys
from pathlib import Path

REPO = Path("/Volumes/Digs-1TB/Development/quantum-apps/QUIRK")
OUT = Path(__file__).parent / "requirements.json"

# - [x] **HWLC-14**: description text...
LINE = re.compile(r"^\s*-\s*\[([ xX])\]\s*\*\*([A-Z]{2,6}-[0-9]{1,3})\*\*\s*:?\s*(.*)$")

def milestone_of(path: Path) -> str:
    if path.parent.name == ".planning":
        return "current"
    m = re.match(r"(v[0-9.]+)-REQUIREMENTS\.md", path.name)
    return m.group(1) if m else path.stem

def parse(path: Path) -> list[dict]:
    rows, cur = [], None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw)
        if m:
            cur = {
                "req_id": m.group(2),
                "milestone": milestone_of(path),
                "claimed_complete": m.group(1).lower() == "x",
                "text": m.group(3).strip(),
                "source_file": str(path.relative_to(REPO)),
            }
            rows.append(cur)
        elif cur is not None and raw.strip() and raw.startswith("  "):
            cur["text"] += " " + raw.strip()   # continuation line
        elif not raw.strip():
            cur = None
    return rows

def main() -> int:
    files = [REPO / ".planning/REQUIREMENTS.md"]
    files += sorted((REPO / ".planning/milestones").glob("*-REQUIREMENTS.md"))
    rows = []
    for f in files:
        if not f.exists():
            print(f"MISSING: {f}", file=sys.stderr)
            continue
        got = parse(f)
        print(f"{len(got):4d}  {f.name}")
        rows.extend(got)
    OUT.write_text(json.dumps(rows, indent=2))
    ids = {r["req_id"] for r in rows}
    print(f"\ntotal rows: {len(rows)}   distinct req_ids: {len(ids)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run it and sanity-check the count**

```bash
python3 "$SP/parse_requirements.py"
```

Expected: `distinct req_ids` close to **460** (the count measured during charter design via
`grep -rhoE '\*\*[A-Z]{2,6}-[0-9]{1,3}\*\*' .planning/milestones/*REQUIREMENTS.md | sort -u | wc -l`).

If the parser finds materially fewer than 460, it is dropping requirements — diff the two
ID sets before proceeding:

```bash
cd "$REPO"
grep -rhoE '\*\*[A-Z]{2,6}-[0-9]{1,3}\*\*' .planning/REQUIREMENTS.md .planning/milestones/*-REQUIREMENTS.md \
  | tr -d '*' | sort -u > "$SP/ids_grep.txt"
python3 -c "
import json,pathlib
sp=pathlib.Path('$SP')
ids={r['req_id'] for r in json.loads((sp/'requirements.json').read_text())}
grep=set(sp.joinpath('ids_grep.txt').read_text().split())
print('parser missed:', sorted(grep-ids))
print('parser invented:', sorted(ids-grep))
"
```

Expected: both lists empty. Do not proceed to Task 2 until they are, or until each
difference is understood and recorded.

- [ ] **Step 4: Record duplicate-ID collisions**

The same ID may legitimately appear in two milestones (a carry-forward). Capture these —
they matter later because a carry-forward marked `[x]` in an old milestone but `[ ]` in a
new one is a documentation contradiction worth reporting:

```bash
python3 -c "
import json,collections,pathlib
rows=json.loads(pathlib.Path('$SP/requirements.json').read_text())
c=collections.Counter(r['req_id'] for r in rows)
dupes={k:v for k,v in c.items() if v>1}
print('ids appearing in >1 document:', len(dupes))
for k in sorted(dupes):
    states=[(r['milestone'], r['claimed_complete']) for r in rows if r['req_id']==k]
    if len({s[1] for s in states})>1:
        print('  CONFLICT', k, states)
"
```

Save the output to `$SP/evidence/duplicate-req-ids.txt`. Every `CONFLICT` line is a
candidate finding.

---

## Task 2: Evidence Extraction (Tiers A–D)

**Files:**
- Create: `$SP/parse_evidence.py`
- Output: `$SP/evidence.json`
- Read: `.planning/**/*SUMMARY*.md`, `docs/UAT-SERIES.md`, `.planning/**/ROADMAP.md`, `tests/`

**Interfaces:**
- Consumes: nothing from Task 1 (runs independently; joined in Task 3).
- Produces: `evidence.json` — `{req_id: {"tier_a": [...], "tier_b": [...], "tier_c": [...],
  "tier_d": [...]}}` where each tier value is a list of evidence objects described below.

- [ ] **Step 1: Write the Tier-A extractor (summary frontmatter)**

Tier A is the strongest evidence: YAML frontmatter in plan summaries that names both the
requirements closed and the files touched. Confirmed format:

```yaml
key-files:
  created: []
  modified:
    - quirk/models.py
    - tests/test_hardware_device_model.py
requirements-completed: [HWLC-01, HWLC-02, HWLC-03]
```

```python
#!/usr/bin/env python3
"""Pass 1b: build tiered evidence links for every requirement ID."""
import json, re, subprocess
from collections import defaultdict
from pathlib import Path

REPO = Path("/Volumes/Digs-1TB/Development/quantum-apps/QUIRK")
OUT = Path(__file__).parent / "evidence.json"
ev = defaultdict(lambda: {"tier_a": [], "tier_b": [], "tier_c": [], "tier_d": []})

REQ = re.compile(r"[A-Z]{2,6}-[0-9]{1,3}")

def tier_a() -> None:
    """SUMMARY.md frontmatter: requirements-completed + key-files."""
    for path in REPO.glob(".planning/**/*SUMMARY*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"requirements-completed:\s*\[([^\]]*)\]", text)
        if not m:
            continue
        reqs = REQ.findall(m.group(1))
        if not reqs:
            continue
        files = re.findall(r"^\s+-\s+([A-Za-z0-9_./-]+\.(?:py|tsx|ts|md|yml|yaml|sh))\s*$",
                           text, re.MULTILINE)
        tests = sorted({f for f in files if "test" in f.lower()})
        for r in reqs:
            ev[r]["tier_a"].append({
                "summary": str(path.relative_to(REPO)),
                "files": sorted(set(files)),
                "test_files": tests,
            })

def tier_b() -> None:
    """UAT-SERIES.md: '### UAT-160-01: Title (HWLC-17)' + '**Result:** - [x] PASS'."""
    text = (REPO / "docs/UAT-SERIES.md").read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"^###\s+", text, flags=re.MULTILINE)[1:]
    for b in blocks:
        head = b.splitlines()[0]
        cm = re.match(r"(UAT-[0-9]+-[0-9]+)\s*:\s*(.*)", head)
        if not cm:
            continue
        case_id, title = cm.group(1), cm.group(2)
        reqs = REQ.findall(title)
        human = "HUMAN-UAT" in b[:600]
        rm = re.search(r"\*\*Result:\*\*\s*-\s*\[([ xX])\]\s*PASS\s*-\s*\[([ xX])\]\s*FAIL"
                       r"\s*-\s*\[([ xX])\]\s*SKIP", b)
        if rm:
            result = ("PASS" if rm.group(1).lower() == "x" else
                      "FAIL" if rm.group(2).lower() == "x" else
                      "SKIP" if rm.group(3).lower() == "x" else "UNMARKED")
        else:
            result = "NO-RESULT-LINE"
        for r in reqs:
            if r.startswith("UAT-"):
                continue
            ev[r]["tier_b"].append({"uat_case": case_id, "result": result, "human": human})

def tier_c() -> None:
    """ROADMAP files: phase headings listing requirement IDs."""
    roadmaps = [REPO / ".planning/ROADMAP.md"]
    roadmaps += sorted((REPO / ".planning/milestones").glob("*-ROADMAP.md"))
    for path in roadmaps:
        if not path.exists():
            continue
        cur_phase = None
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            pm = re.search(r"Phase\s+([0-9]+(?:\.[0-9]+)?)", line)
            if pm and line.lstrip().startswith(("#", "-", "*", "|")):
                cur_phase = pm.group(1)
            for r in REQ.findall(line):
                if r.startswith("UAT-") or not cur_phase:
                    continue
                ev[r]["tier_c"].append({
                    "phase": cur_phase, "roadmap": str(path.relative_to(REPO)),
                })

def tier_d() -> None:
    """Requirement ID appearing literally inside tests/."""
    res = subprocess.run(
        ["grep", "-rnoE", r"\b[A-Z]{2,6}-[0-9]{1,3}\b", str(REPO / "tests")],
        capture_output=True, text=True,
    )
    for line in res.stdout.splitlines():
        try:
            fpath, lineno, rid = line.split(":", 2)
        except ValueError:
            continue
        rid = rid.strip()
        if not REQ.fullmatch(rid) or rid.startswith("UAT-"):
            continue
        ev[rid]["tier_d"].append({
            "file": str(Path(fpath).relative_to(REPO)), "line": int(lineno),
        })

def main() -> int:
    tier_a(); tier_b(); tier_c(); tier_d()
    OUT.write_text(json.dumps(ev, indent=2, sort_keys=True))
    for t in ("tier_a", "tier_b", "tier_c", "tier_d"):
        print(f"{t}: {sum(1 for v in ev.values() if v[t])} requirements")
    print(f"total requirements with any evidence: {len(ev)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it and check the tier counts against the charter's measurements**

```bash
python3 "$SP/parse_evidence.py"
```

Expected, from measurements taken during charter design:
- `tier_a` ≈ **107** requirements
- `tier_d` — derived from 89 test files carrying an ID
- `tier_b` and `tier_c` — unmeasured; record whatever they are

A `tier_a` count wildly below 107 means the frontmatter regex is wrong. Verify against a
known-good file before continuing:

```bash
grep -A3 'requirements-completed' \
  "$REPO/.planning/milestones/v5.13-phases/154-identity-data-model-foundation/154-01-SUMMARY.md"
```

- [ ] **Step 3: Verify Tier-A named test files still exist**

This is what makes `STALE-EVIDENCE` detectable — the highest-value finding class.

```bash
python3 -c "
import json,pathlib
REPO=pathlib.Path('$REPO')
ev=json.loads(pathlib.Path('$SP/evidence.json').read_text())
missing={}
for rid,tiers in ev.items():
    for a in tiers['tier_a']:
        gone=[f for f in a['files'] if not (REPO/f).exists()]
        if gone: missing.setdefault(rid,[]).extend(gone)
print('requirements whose Tier-A files are partly missing:', len(missing))
for k in sorted(missing): print(' ',k,sorted(set(missing[k])))
" | tee "$SP/evidence/tier-a-missing-files.txt"
```

Record the output. Every line is a candidate `STALE-EVIDENCE` finding, subject to Task 3's
check that the file was not merely *renamed* (a renamed file that still tests the same
behaviour is a documentation defect, not a coverage defect — the report must distinguish
these).

- [ ] **Step 4: Capture UAT result distribution**

```bash
python3 -c "
import json,collections,pathlib
ev=json.loads(pathlib.Path('$SP/evidence.json').read_text())
c=collections.Counter()
h=0
for rid,t in ev.items():
    for b in t['tier_b']:
        c[b['result']]+=1
        h+=bool(b['human'])
print('UAT result distribution:',dict(c))
print('HUMAN-UAT-linked entries:',h)
" | tee "$SP/evidence/uat-result-distribution.txt"
```

Any `FAIL`, `UNMARKED`, or `NO-RESULT-LINE` count above zero is a direct finding: the
project's own gating document contains unproven or unrecorded cases.

---

## Task 3: Verdict Assignment and Traceability Matrix

**Files:**
- Create: `$SP/build_matrix.py`
- Output: `$SP/matrix.json`, `$SP/matrix.md`
- Consumes: `$SP/requirements.json`, `$SP/evidence.json`

**Interfaces:**
- Produces: `matrix.json` — one row per distinct `req_id` with keys `req_id`, `milestone`,
  `claimed_complete`, `text`, `verdict`, `tier`, `test_files`, `uat_cases`, `phases`,
  `notes`. `verdict` is one of the eight values defined in spec §4.

- [ ] **Step 1: Write the verdict assigner**

```python
#!/usr/bin/env python3
"""Pass 1c: join requirements to evidence and assign a tier-stamped verdict."""
import json
from pathlib import Path

SP = Path(__file__).parent
REPO = Path("/Volumes/Digs-1TB/Development/quantum-apps/QUIRK")
reqs = json.loads((SP / "requirements.json").read_text())
ev = json.loads((SP / "evidence.json").read_text())

# Collapse duplicate IDs: newest milestone's claim state wins, evidence unions.
by_id = {}
for r in reqs:
    prev = by_id.get(r["req_id"])
    if prev is None or r["milestone"] == "current":
        by_id[r["req_id"]] = r

rows = []
for rid, r in sorted(by_id.items()):
    t = ev.get(rid, {"tier_a": [], "tier_b": [], "tier_c": [], "tier_d": []})
    tests = sorted({f for a in t["tier_a"] for f in a["test_files"]})
    tests_exist = [f for f in tests if (REPO / f).exists()]
    tests_gone = [f for f in tests if not (REPO / f).exists()]
    uats = t["tier_b"]
    human = any(u["human"] for u in uats)

    if not r["claimed_complete"]:
        verdict, tier = "OPEN", "-"
    elif human and not tests_exist:
        verdict, tier = "HUMAN-PENDING", "B"
    elif tests_gone and not tests_exist:
        verdict, tier = "STALE-EVIDENCE", "A"
    elif tests_exist:
        verdict, tier = "PROVEN?", "A"        # confirmed by execution in Task 5
    elif uats:
        verdict, tier = "UAT-ONLY", "B"
    elif t["tier_d"]:
        verdict, tier = "UAT-ONLY", "D"
    elif t["tier_c"]:
        verdict, tier = "PHASE-ONLY", "C"
    else:
        verdict, tier = "UNTRACED", "-"

    rows.append({
        "req_id": rid, "milestone": r["milestone"],
        "claimed_complete": r["claimed_complete"], "text": r["text"][:300],
        "verdict": verdict, "tier": tier,
        "test_files": tests_exist, "missing_test_files": tests_gone,
        "uat_cases": [u["uat_case"] for u in uats],
        "uat_results": sorted({u["result"] for u in uats}),
        "phases": sorted({c["phase"] for c in t["tier_c"]}),
    })

# ORPHAN detection: evidence referencing an ID no requirements document defines.
defined = set(by_id)
orphans = sorted(set(ev) - defined)

(SP / "matrix.json").write_text(json.dumps(
    {"rows": rows, "orphans": orphans}, indent=2))

import collections
c = collections.Counter(r["verdict"] for r in rows)
lines = ["# Traceability Matrix", "", "## Verdict summary", "",
         "| Verdict | Count |", "|---|---|"]
lines += [f"| {k} | {v} |" for k, v in c.most_common()]
lines += ["", f"Orphaned IDs referenced by evidence but never defined: {len(orphans)}",
          "", "  " + ", ".join(orphans) if orphans else "", "",
          "## Full matrix", "",
          "| Req | Milestone | Claim | Verdict | Tier | Tests | UAT | Phases |",
          "|---|---|---|---|---|---|---|---|"]
for r in rows:
    lines.append(
        f"| {r['req_id']} | {r['milestone']} | "
        f"{'[x]' if r['claimed_complete'] else '[ ]'} | {r['verdict']} | {r['tier']} | "
        f"{len(r['test_files'])} | {','.join(r['uat_cases']) or '—'} | "
        f"{','.join(r['phases']) or '—'} |")
(SP / "matrix.md").write_text("\n".join(lines))
print("\n".join(lines[:20]))
print(f"\nrows: {len(rows)}  orphans: {len(orphans)}")
```

- [ ] **Step 2: Run it and review the verdict distribution**

```bash
python3 "$SP/build_matrix.py"
```

Expected shape based on the charter's evidence measurements: a large `PHASE-ONLY` /
`UNTRACED` mass from pre-v5.x milestones, roughly 107 requirements at Tier A. **Do not
treat a large untraced count as a parser bug without checking.** Spot-check five
`UNTRACED` requirements by hand:

```bash
python3 -c "
import json,pathlib,random
m=json.loads(pathlib.Path('$SP/matrix.json').read_text())
u=[r for r in m['rows'] if r['verdict']=='UNTRACED']
random.seed(0)
for r in random.sample(u,min(5,len(u))): print(r['req_id'],'|',r['milestone'],'|',r['text'][:110])
"
```

For each, grep the repo by hand for its subject matter. If evidence exists that the parser
missed, fix the parser and re-run. If not, the verdict stands.

- [ ] **Step 3: Save the matrix as review evidence**

```bash
cp "$SP/matrix.md" "$SP/evidence/traceability-matrix.md"
wc -l "$SP/evidence/traceability-matrix.md"
```

---

## Task 4: Documentation Self-Consistency Audit

**Files:**
- Read: `docs/UAT-SERIES.md`, `README.md`, `docs/getting-started.md`, `.planning/ROADMAP.md`,
  `CLAUDE.md`
- Output: `$SP/evidence/doc-consistency.md`

**Interfaces:**
- Consumes: `$SP/matrix.json` (for orphan list).
- Produces: `$SP/evidence/doc-consistency.md` — findings where documents contradict each
  other or themselves.

- [ ] **Step 1: Version drift check**

`CLAUDE.md` defines a milestone-boundary version audit. Verify it was actually performed —
the version string must match across every file that declares one:

```bash
cd "$REPO"
echo "--- README badge/heading ---";      grep -nE 'v?5\.[0-9]+\.[0-9]+' README.md | head -5
echo "--- getting-started ---";           grep -nE 'v?5\.[0-9]+\.[0-9]+' docs/getting-started.md | head -5
echo "--- UAT-SERIES header ---";         sed -n '1,6p' docs/UAT-SERIES.md
echo "--- pyproject ---";                 grep -nE '^version' pyproject.toml
echo "--- CHANGELOG latest ---";          grep -nE '^#+ +\[?v?5\.' CHANGELOG.md | head -3
```

`UAT-SERIES.md` currently declares `**Version:** 5.12.0` while the roadmap shows v5.15 in
progress and v5.14 shipped. Confirm whether that is stale, and record the exact expected
value. **This is a live candidate finding — do not assume it is intentional.**

- [ ] **Step 2: Requirement claim vs. roadmap claim contradiction check**

```bash
python3 -c "
import json,pathlib,re
REPO=pathlib.Path('$REPO')
m=json.loads(pathlib.Path('$SP/matrix.json').read_text())
road=(REPO/'.planning/ROADMAP.md').read_text()
# Milestones the roadmap marks shipped
shipped=set(re.findall(r'✅ \*\*(v[0-9.]+)',road))
bad=[r for r in m['rows']
     if r['milestone'] in shipped and not r['claimed_complete']]
print('requirements still open inside a SHIPPED milestone:',len(bad))
for r in bad: print(' ',r['req_id'],r['milestone'],'|',r['text'][:100])
" | tee "$SP/evidence/open-reqs-in-shipped-milestones.txt"
```

Any result here is a direct finding: a milestone declared shipped while carrying an
unfinished requirement.

- [ ] **Step 3: Orphan and dangling-reference check**

```bash
python3 -c "
import json,pathlib
m=json.loads(pathlib.Path('$SP/matrix.json').read_text())
print('ORPHANS (referenced by UAT/roadmap/tests, never defined as a requirement):')
for o in m['orphans']: print('  ',o)
" | tee "$SP/evidence/orphan-ids.txt"
```

Note: this list will contain false positives — strings like `CVE-2024` or `RFC-8446`
match the ID shape. Manually classify each into *genuine orphan requirement* vs. *not a
requirement ID at all*, and record the classification. Only genuine orphans become
findings.

- [ ] **Step 4: CLAUDE.md process-rule compliance**

`CLAUDE.md` mandates staleness cadences on four catalogs. Verify each is within cadence:

```bash
cd "$REPO"
for f in quirk/qramm/model_meta.py quirk/compliance/__init__.py quirk/scanner/hw_cve.py \
         quirk/scanner/bacnet_vendors.py quirk/scanner/hardware_eol.py; do
  echo "--- $f"; grep -nE 'last_verified|STALENESS_THRESHOLD_DAYS|source_url' "$f" | head -4
done
```

Compute days elapsed against today (2026-08-24) versus each declared threshold. Any
catalog past its threshold is a finding — and note that CI is supposed to catch this, so
an over-cadence catalog also implies the CI gate is not running or not enforcing.

- [ ] **Step 5: Write the consolidated consistency evidence file**

Collect Steps 1–4 into `$SP/evidence/doc-consistency.md` with one section per check,
each stating: what was checked, the command, the actual output, and whether it is a
finding. No conclusions yet — Task 10 does the writing up.

---

## Task 5: Backend Execution Evidence

**Files:**
- Read: `tests/`, `tests/skip_registry.py`
- Output: `$SP/evidence/pytest-full.log`, `$SP/evidence/backend-summary.md`

**Interfaces:**
- Consumes: `$SP/matrix.json` (`test_files` per requirement).
- Produces: `$SP/evidence/pytest-results.json` — `{nodeid: outcome}` for every test, used
  by Task 9 to confirm or downgrade every `PROVEN?` verdict.

- [ ] **Step 1: Record the reviewed commit**

```bash
cd "$REPO" && git rev-parse HEAD | tee "$SP/evidence/reviewed-commit.txt" && git status --porcelain
```

A dirty working tree at review time must be recorded — the review assesses a specific
state.

- [ ] **Step 2: Run the full backend suite, capturing everything**

Docker is running, so live-infra tests that were previously skipped may now execute. Run
without `-x` so one failure does not hide the rest:

```bash
cd "$REPO"
.venv/bin/python -m pytest tests/ -q --tb=short -p no:randomly \
  --junitxml="$SP/evidence/pytest-junit.xml" 2>&1 | tee "$SP/evidence/pytest-full.log"
echo "exit=${PIPESTATUS[0]}"
```

This may take a long time (369 test files). Do not abort on failures — failures are the
deliverable. Record the exit code.

- [ ] **Step 3: Extract per-test outcomes**

```bash
python3 -c "
import json,pathlib,xml.etree.ElementTree as ET
t=ET.parse('$SP/evidence/pytest-junit.xml'); r={}
for tc in t.iter('testcase'):
    nid=f\"{tc.get('classname')}::{tc.get('name')}\"
    out='passed'
    for ch in tc:
        if ch.tag in ('failure','error','skipped'):
            out={'failure':'failed','error':'error','skipped':'skipped'}[ch.tag]; break
    r[nid]=out
pathlib.Path('$SP/evidence/pytest-results.json').write_text(json.dumps(r,indent=2))
import collections; print(collections.Counter(r.values()))
"
```

- [ ] **Step 4: Audit the skip registry**

`tests/skip_registry.py` is an allowlist of deliberate skips with `(file, line, category,
reason)` tuples. Two questions matter, and both are findings if answered badly:

1. Are there skips in the suite that are *not* registered? (`test_skip_registry.py` is the
   meta-gate — confirm it ran and passed.)
2. Are registered skips still accurate? A skip whose line number has drifted, or whose
   reason says "Requires Docker" while Docker is now running, is stale.

```bash
cd "$REPO"
.venv/bin/python -m pytest tests/test_skip_registry.py -v 2>&1 | tee "$SP/evidence/skip-registry-gate.log"
grep -c '^    (' tests/skip_registry.py
python3 -c "
import re,pathlib
REPO=pathlib.Path('$REPO')
src=(REPO/'tests/skip_registry.py').read_text()
for f,ln,cat,reason in re.findall(r'\(\s*\"([^\"]+)\",\s*(\d+),\s*\"([^\"]+)\",\s*\"([^\"]+)\"',src):
    p=REPO/'tests'/f
    if not p.exists(): print('MISSING FILE',f); continue
    lines=p.read_text().splitlines()
    n=int(ln)
    ctx=lines[n-1] if 0<n<=len(lines) else '<out of range>'
    ok='skip' in ctx.lower()
    print(('OK  ' if ok else 'DRIFT'),f,n,cat,'|',ctx.strip()[:70])
" | tee "$SP/evidence/skip-registry-drift.txt"
grep -c DRIFT "$SP/evidence/skip-registry-drift.txt" || true
```

Every `DRIFT` line means the registry points at a line that is no longer a skip — the
allowlist has rotted and the meta-gate may be validating nothing.

- [ ] **Step 5: Confirm live-infra skips now that Docker is up**

```bash
grep -E 'live_infra' "$REPO/tests/skip_registry.py" | wc -l
grep -cE 'SKIPPED' "$SP/evidence/pytest-full.log"
```

Record how many tests skipped despite Docker being available. A test registered as
"Requires Docker + MinIO" that still skips with Docker running means the skip condition
does not actually detect Docker — the capability is never tested in any environment.
That is a HIGH-severity class of finding.

- [ ] **Step 6: Write `$SP/evidence/backend-summary.md`**

State: reviewed commit, total collected, passed / failed / error / skipped counts, exit
code, the full list of failing node IDs, skip-registry drift count, and the live-infra
skip analysis. Facts only.

---

## Task 6: Frontend Execution Evidence

**Files:**
- Read: `src/dashboard/`
- Output: `$SP/evidence/frontend-*.log`, `$SP/evidence/frontend-summary.md`

**Interfaces:**
- Produces: `$SP/evidence/frontend-summary.md` and a definitive answer on committed-bundle
  freshness, consumed by Task 8 (the browser walkthrough drives the committed bundle).

- [ ] **Step 1: Lint**

```bash
cd "$REPO/src/dashboard"
npm run lint 2>&1 | tee "$SP/evidence/frontend-lint.log"; echo "exit=${PIPESTATUS[0]}"
```

Note `lint` also runs `lint:hooks` → `scripts/check-cancelled-guards.sh`, a project-specific
guard. Record whether it passed.

- [ ] **Step 2: Component tests**

```bash
cd "$REPO/src/dashboard"
npm test 2>&1 | tee "$SP/evidence/frontend-vitest.log"; echo "exit=${PIPESTATUS[0]}"
```

- [ ] **Step 3: Accessibility baselines**

```bash
cd "$REPO/src/dashboard"
npm run a11y:check 2>&1 | tee "$SP/evidence/frontend-a11y.log"; echo "exit=${PIPESTATUS[0]}"
```

The harness compares against committed `baseline-*.json` files. A pass means "no new
violations", **not** "no violations". Extract the absolute violation count from the
baselines — a large accepted-violation baseline is itself a finding:

```bash
cd "$REPO/src/dashboard/tests/a11y"
python3 -c "
import json,glob
for f in sorted(glob.glob('baseline-*.json')):
    d=json.load(open(f))
    n=len(d) if isinstance(d,list) else len(d.get('violations',d))
    print(f'{n:4d}  {f}')
"
```

- [ ] **Step 4: Committed-bundle freshness — does shipped JS match current source?**

FastAPI serves a pre-built bundle. If the committed bundle is stale, the E2E suite and the
browser walkthrough both validate a frontend that is not the one in source.

```bash
cd "$REPO"
git status --porcelain src/dashboard/output | tee "$SP/evidence/bundle-git-status-before.txt"
shasum -a 256 src/dashboard/output/assets/*.js 2>/dev/null | sort > "$SP/evidence/bundle-before.txt"
cd src/dashboard && npm run build 2>&1 | tail -20 | tee "$SP/evidence/frontend-build.log"
cd "$REPO"
shasum -a 256 src/dashboard/output/assets/*.js 2>/dev/null | sort > "$SP/evidence/bundle-after.txt"
git status --porcelain src/dashboard/output | tee "$SP/evidence/bundle-git-status-after.txt"
```

Hashes will differ if filenames are content-hashed; the decisive signal is
`bundle-git-status-after.txt`. If it shows modifications where
`bundle-git-status-before.txt` was clean, **the committed bundle was stale — a HIGH
finding.** Record it, then restore the tree so the review does not mutate the repo:

```bash
cd "$REPO" && git checkout -- src/dashboard/output && git status --porcelain src/dashboard/output
```

Expected after restore: empty output. The review must leave no changes behind.

- [ ] **Step 5: End-to-end smoke**

```bash
cd "$REPO/src/dashboard"
npm run e2e:smoke 2>&1 | tee "$SP/evidence/frontend-e2e.log"; echo "exit=${PIPESTATUS[0]}"
```

- [ ] **Step 6: Assess what the E2E suite does NOT cover**

Read `src/dashboard/tests/e2e/run-e2e.mjs` and `src/dashboard/tests/console-allowlist.json`.
Record explicitly: which of the 15 routes get value assertions versus render-only checks,
and every allowlisted console-error pattern. A broad allowlist silently converts real
errors into passes — enumerate each entry and judge whether it is justified.

- [ ] **Step 7: Write `$SP/evidence/frontend-summary.md`** with all six results, exit codes,
the a11y baseline violation totals, the bundle-freshness verdict, and the E2E coverage gap
analysis.

---

## Task 7: Chaos Lab Verification

**Files:**
- Read: `quantum-chaos-enterprise-lab/docker-compose.yml`, `lab.sh`, `expected_results_*.md`
- Output: `$SP/evidence/chaos-lab.md`

**Interfaces:**
- Produces: scan output from at least one live lab profile compared against its oracle.

- [ ] **Step 1: Audit the `lab.sh` no-drift rule from CLAUDE.md**

`CLAUDE.md` requires every compose profile to appear in `lab.sh`'s profile list. Measured
during charter design: **29 profiles in `docker-compose.yml`**. Verify `lab.sh` matches:

```bash
cd "$REPO/quantum-chaos-enterprise-lab"
python3 -c "
import re
t=open('docker-compose.yml').read()
p=set()
for m in re.findall(r'profiles:\s*\[([^\]]*)\]',t):
    p|={x.strip().strip('\"') for x in m.split(',')}
print('compose profiles (%d):'%len(p)); print(sorted(p))
" | tee "$SP/evidence/compose-profiles.txt"
grep -nE '_profiles=\(' -A 12 lab.sh | tee "$SP/evidence/labsh-profiles.txt"
```

Diff the two sets by hand. Any compose profile absent from `lab.sh` violates a documented
project rule and is a finding.

- [ ] **Step 2: Confirm every profile has oracle coverage**

Six oracle files exist: `expected_results_{distributed,hwcompat,otics,segmented_network,v3,v4}.md`.
For each of the 29 profiles, find which oracle documents it:

```bash
cd "$REPO/quantum-chaos-enterprise-lab"
for p in $(python3 -c "
import re
t=open('docker-compose.yml').read()
p=set()
for m in re.findall(r'profiles:\s*\[([^\]]*)\]',t): p|={x.strip().strip('\"') for x in m.split(',')}
print(' '.join(sorted(p)))"); do
  hits=$(grep -l -- "$p" expected_results_*.md 2>/dev/null | tr '\n' ' ')
  [ -z "$hits" ] && echo "NO ORACLE: $p" || echo "ok: $p -> $hits"
done | tee "$SP/evidence/profile-oracle-coverage.txt"
grep -c 'NO ORACLE' "$SP/evidence/profile-oracle-coverage.txt" || true
```

- [ ] **Step 3: Bring up one representative profile and scan it**

Choose `tls-cert-defects` — it exercises the core TLS discovery path the product's value
claim rests on, and its expected findings are documented.

```bash
cd "$REPO/quantum-chaos-enterprise-lab"
PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up 2>&1 | tail -30 | tee "$SP/evidence/lab-up.log"
./lab.sh status 2>&1 | tee "$SP/evidence/lab-status.log"
```

If `lab.sh up` fails, record the failure verbatim and continue — a lab that does not start
from its documented command is itself a significant finding.

- [ ] **Step 4: Scan the running lab and compare to the oracle**

```bash
cd "$REPO"
.venv/bin/quirk scan --help 2>&1 | head -40 | tee "$SP/evidence/quirk-scan-help.txt"
```

Read the help output, then run the scan against the lab's documented ports (from
`expected_results_v4.md`), writing output to a temp directory outside the repo. Compare
the findings against the oracle's expected findings line by line. Record every expected
finding the scanner missed (false negative) and every finding not in the oracle (false
positive or undocumented detection).

- [ ] **Step 5: Tear down**

```bash
cd "$REPO/quantum-chaos-enterprise-lab" && ./lab.sh down 2>&1 | tail -10
```

- [ ] **Step 6: Write `$SP/evidence/chaos-lab.md`** with the profile drift audit, oracle
coverage gaps, and the scan-versus-oracle comparison.

---

## Task 8: Live Full-Stack Walkthrough (Chrome)

**Files:**
- Output: `$SP/evidence/walkthrough.md`, `$SP/evidence/api-vs-ui.md`

**Interfaces:**
- Consumes: Task 6's bundle-freshness verdict (determines whether the UI under test is the
  shipped one).
- Produces: the evidence for the product's central value claim.

This task tests what no existing suite tests: **that the values rendered in the dashboard
match the values the API computed.** The existing E2E smoke proves pages render without
console errors; it does not compare a single number.

- [ ] **Step 1: Boot the server in an isolated workspace**

Never point the review at the developer's real `quirk.db`.

```bash
cd "$REPO"
export QUIRK_REVIEW_DIR=$(mktemp -d)
echo "$QUIRK_REVIEW_DIR" | tee "$SP/evidence/review-workspace.txt"
```

Read `src/dashboard/tests/e2e/run-e2e.mjs` (it already solves isolated-workspace startup)
and reuse its exact env-var and CLI invocation rather than inventing one. Start
`quirk serve` on port 8518 in the background, logging to `$SP/evidence/serve.log`.

- [ ] **Step 2: Run a scan producing real data**

Scan a target that works without the lab — `127.0.0.1` with the lab profile from Task 7 up,
or `scanme.nmap.org` only if the project's own docs sanction it. Prefer the local lab.
Capture the CLI output to `$SP/evidence/review-scan.log`.

- [ ] **Step 3: Capture API ground truth**

```bash
for ep in /api/scan/latest /api/qramm /api/hardware/vendor-trends /api/config; do
  echo "=== $ep"; curl -s "http://127.0.0.1:8518$ep" | head -c 3000; echo
done | tee "$SP/evidence/api-responses.txt"
```

Record the readiness score, finding counts, and CBOM component count as the numbers the UI
must agree with.

- [ ] **Step 4: Drive the dashboard in Chrome**

Load the claude-in-chrome tools in a single ToolSearch call, then walk all 15 routes:
`/`, `/findings`, `/identity`, `/motion`, `/data-at-rest`, `/certificates`, `/cbom`,
`/roadmap`, `/trends`, `/scans`, `/sensors`, `/schedules`, `/qramm`, `/hardware`, `/compare`.

For each route record: does it render, does it show data or an empty state, and **do the
displayed numbers match Step 3's API values**. Read console messages per route. Capture a
GIF of the core path (`/` → `/findings` → `/cbom` → `/qramm`) named
`quirk-review-walkthrough.gif` for the report.

- [ ] **Step 5: Verify the CBOM deliverable**

The product's core claim is a CycloneDX CBOM a consultant can hand to a client. Export it
and validate it against the schema — the repo already has schema validation tests
(`tests/test_cbom_schema_validation.py`), so reuse their validation approach:

```bash
cd "$REPO"
.venv/bin/quirk --help 2>&1 | tee "$SP/evidence/quirk-help.txt"
```

Find the export/report command, produce the CBOM and the HTML/DOCX report, and confirm:
the CBOM validates, the component count matches the API, and the report renders with the
score. Record file sizes and any generation errors.

- [ ] **Step 6: Time the core value claim**

`PROJECT.md` claims a consultant can go from zero to client-ready deliverable in under two
hours. Record actual elapsed wall-clock for scan → CBOM → score → report on the lab
target. This is a single data point on a small target, and the report must say so — but a
result of minutes versus hours is still meaningful evidence.

- [ ] **Step 7: Shut down and clean up**

Kill the server, remove `$QUIRK_REVIEW_DIR`, and confirm `git status --porcelain` in the
repo is unchanged from Task 5 Step 1.

- [ ] **Step 8: Write `$SP/evidence/walkthrough.md` and `$SP/evidence/api-vs-ui.md`**

The second file is a table: metric, API value, UI value, match yes/no. Every mismatch is a
finding.

---

## Task 9: Targeted Deep-Dive on Flagged Requirements

**Files:**
- Read: `quirk/`, `src/dashboard/src/`
- Output: `$SP/evidence/deep-dive.md`

**Interfaces:**
- Consumes: `$SP/matrix.json`, `$SP/evidence/pytest-results.json`.
- Produces: final verdicts, resolving every `PROVEN?` to `PROVEN` or downgrading it.

- [ ] **Step 1: Resolve every `PROVEN?` verdict against actual test results**

```bash
python3 -c "
import json,pathlib
m=json.loads(pathlib.Path('$SP/matrix.json').read_text())
res=json.loads(pathlib.Path('$SP/evidence/pytest-results.json').read_text())
def outcomes(f):
    stem=f.replace('/','.').removesuffix('.py')
    return [v for k,v in res.items() if stem in k]
for r in m['rows']:
    if r['verdict']!='PROVEN?': continue
    o=[x for f in r['test_files'] for x in outcomes(f)]
    if not o: v='PROVEN-NO-TESTS-RAN'
    elif 'failed' in o or 'error' in o: v='FAILING'
    elif all(x=='skipped' for x in o): v='ALL-SKIPPED'
    else: v='PROVEN'
    r['verdict']=v
pathlib.Path('$SP/matrix.json').write_text(json.dumps(m,indent=2))
import collections; print(collections.Counter(r['verdict'] for r in m['rows']))
" | tee "$SP/evidence/final-verdicts.txt"
```

`PROVEN-NO-TESTS-RAN` and `ALL-SKIPPED` are important: a requirement whose only evidence is
a test file that never actually executes is not proven, regardless of what the summary
claims.

- [ ] **Step 2: Deep-dive the current milestone's requirements**

v5.15 is in progress with HWLC-14 `[x]`, HWLC-19 `[x]`, HWLC-20 `[ ]`. For each marked
complete, read the implementation and judge it against the verbatim requirement text.
HWLC-19 in particular claims the vendor-trends endpoint now has "a first user-facing home"
— verify the dashboard actually consumes it (recent commits added `VendorTrendList` /
`VendorTrendRow` and a `useVendorPqcTrends` hook):

```bash
cd "$REPO"
grep -rn 'vendor-trends\|useVendorPqcTrends\|VendorTrendList' src/dashboard/src/ | head -20
grep -rn 'vendor-trends\|vendor_trends' quirk/ | head -20
```

Confirm in Task 8's walkthrough that `/hardware` renders it with real data.

- [ ] **Step 3: Deep-dive every `FAILING`, `STALE-EVIDENCE`, and `ALL-SKIPPED` requirement**

For each, read the code and determine whether the requirement's behaviour actually works
despite the evidence problem. Distinguish three outcomes and label each explicitly:
*works but unproven* (documentation/test debt), *does not work* (a real defect), and
*cannot determine* (say so rather than guessing).

- [ ] **Step 4: Sample-audit ten `PHASE-ONLY` / `UNTRACED` requirements from older milestones**

A full deep-dive of ~350 requirements is out of proportion. Take a stratified sample of ten
across different milestones and prefixes, and determine for each whether the capability
exists in the code at all. The sample's hit rate is the report's basis for characterising
the whole untraced population — and the report must state it is an extrapolation from a
sample of ten, not a census.

- [ ] **Step 5: Write `$SP/evidence/deep-dive.md`** — one section per requirement examined,
with the quoted requirement text, what the code does, and the labelled outcome.

---

## Task 10: Findings Report

**Files:**
- Create: `docs/reviews/2026-08-24-functional-review-findings.md`
- Consumes: every file in `$SP/evidence/`

- [ ] **Step 1: Assign stable finding IDs and severities**

Walk all evidence and enumerate findings as `RVW-001`, `RVW-002`, … ordered by severity.
Severity is impact on the documented promise:

| Severity | Meaning |
|---|---|
| `CRITICAL` | The product does not do something the documents say it does, in the core value path. |
| `HIGH` | A documented capability is unverifiable or verifiably broken outside the core path; or a verification mechanism does not actually verify (stale bundle, non-firing skip, rotted allowlist). |
| `MEDIUM` | Requirement marked complete with no traceable evidence; documents contradict each other. |
| `LOW` | Cosmetic doc drift, stale version strings, minor inconsistency. |
| `OBSERVATION` | No defect; a risk or improvement opportunity found by reading. |

- [ ] **Step 2: Write the report**

Structure:
1. **Executive summary** — what was reviewed, headline verdict, finding counts by severity.
2. **What works** — reported as prominently as what does not. A codebase with 369 test
   files, an a11y baseline harness, and CI staleness gates has genuine strengths and a
   review that omits them is not credible.
3. **Method and evidence model** — the tier table, so readers can weigh each verdict.
4. **Findings** — one subsection per `RVW-NNN` with: severity, affected requirement IDs,
   the **verbatim quoted** document claim, what the code actually does, the exact command
   or artifact that is the evidence, evidence tier, and verdict.
5. **Traceability matrix** — the verdict-distribution table plus a link to the full matrix
   appended verbatim.
6. **The 28 HUMAN-UAT items** — enumerated explicitly by ID and title, never folded into
   prose.
7. **Limitations** — spec §6 verbatim, plus anything discovered during execution (Docker
   profiles not exercised, cloud connectors not credentialed, the sample-of-ten
   extrapolation).

- [ ] **Step 3: Verify every finding has evidence**

Re-read the report and confirm no finding rests on reading code alone unless labelled
`OBSERVATION`. Any finding failing this check is either downgraded to `OBSERVATION` or
given real evidence.

- [ ] **Step 4: Commit**

```bash
cd "$REPO"
mkdir -p docs/reviews
git add docs/reviews/2026-08-24-functional-review-findings.md
git commit -m "docs(review): third-party functional review findings"
```

---

## Task 11: Action Plan and Publication

**Files:**
- Create: `docs/reviews/2026-08-24-functional-review-action-plan.md`
- Consumes: the findings report

- [ ] **Step 1: Write the action plan**

A checkbox table, ordered by severity, one row per finding, designed to be worked through
and checked off directly:

```markdown
| ☐ | ID | Sev | Finding | Affects | Suggested remediation | Effort | Status |
|---|----|-----|---------|---------|----------------------|--------|--------|
| ☐ | RVW-001 | CRITICAL | <one line> | HWLC-14 | <what to do> | S/M/L | Open |
```

Group by theme (verification debt, documentation drift, functional defects, coverage gaps)
so related work can be batched into a milestone. Follow with a **Suggested sequencing**
section proposing which findings belong in which milestone, phrased as a recommendation
the owner may reject — the reviewer proposes, the owner disposes.

Per the charter, the plan must be promotable into `.planning/` as a milestone requirement
set without rewriting: use requirement-style phrasing ("Consultant can…" / "The scanner
must…") in the remediation column.

- [ ] **Step 2: Confirm no fixes were made**

```bash
cd "$REPO"
git diff --stat HEAD~2..HEAD -- . ':(exclude)docs/reviews' ':(exclude)docs/superpowers'
```

Expected: empty. The review must have changed nothing but its own deliverables. If
anything else appears, revert it — the findings-only mandate is absolute.

- [ ] **Step 3: Commit**

```bash
cd "$REPO"
git add docs/reviews/2026-08-24-functional-review-action-plan.md
git commit -m "docs(review): third-party functional review action plan"
```

- [ ] **Step 4: Publish the findings report as an Artifact**

Load the `artifact-design` skill, build an HTML page from the findings report — severity
counts, the verdict-distribution table, and the findings list — and publish it with the
walkthrough GIF embedded. Hand the URL back to the user.

---

## Self-Review

**Spec coverage:**

| Spec section | Covered by |
|---|---|
| §1 scope / findings-only | Global Constraints; Task 11 Step 2 verifies |
| §2 source-of-truth hierarchy | Task 4 (contradiction checks resolve in charter order) |
| §3 evidence model / tiers | Tasks 2, 3 |
| §4 Pass 1 sweep + all 8 verdicts | Tasks 1–3, resolved in Task 9 Step 1 |
| §4 Pass 2 backend | Task 5 |
| §4 Pass 2 frontend | Task 6 |
| §4 Pass 2 full-stack browser | Task 8 |
| §4 Pass 2 chaos lab | Task 7 |
| §4 Pass 2 code reading | Task 9 |
| §4 Pass 3 findings report | Task 10 |
| §4 Pass 3 action plan | Task 11 |
| §5 reporting standards | Task 10 Steps 1–3 |
| §6 limitations | Task 10 Step 2 item 7 |

No gaps.

**Placeholder scan:** every step carries an exact command or complete code. Task 7 Step 4
and Task 8 Steps 1–2 direct the executor to read a named file to derive the exact
invocation rather than guessing a CLI signature — deliberate, because inventing an
unverified command would be worse than reading the file that already contains the correct
one.

**Type consistency:** `requirements.json` keys (`req_id`, `milestone`, `claimed_complete`,
`text`) are produced in Task 1 and consumed under the same names in Task 3.
`evidence.json`'s `tier_a`/`tier_b`/`tier_c`/`tier_d` structure is produced in Task 2 and
consumed under the same names in Tasks 3 and 4. `matrix.json`'s `rows`/`orphans` and each
row's `verdict`/`test_files`/`uat_cases` are produced in Task 3 and consumed in Tasks 4, 9.
`pytest-results.json`'s `{nodeid: outcome}` is produced in Task 5 Step 3 and consumed in
Task 9 Step 1. Consistent throughout.
