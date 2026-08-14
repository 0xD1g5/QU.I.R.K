# Phase 150: Test Suite Green Baseline + CI Gate - Pattern Map

**Mapped:** 2026-08-12
**Files analyzed:** 6 (modified) + 1 (new)
**Analogs found:** 6 / 6 (1 new file has a house-style analog, not a direct-role analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `.github/workflows/python-ci.yml` (new job, D-02) | CI config | event-driven (workflow trigger → batch pytest run) | `windows-sensor-e2e` job in the same file (lines 207-227 header) + `staleness` job in `python-staleness.yml` (whole file) | exact (staleness job is same role+platform: ubuntu-latest pytest gate) |
| `quirk/scanner/kerberos_scanner.py::_build_as_req` (D-05 bug fix) | scanner/utility (protocol builder) | transform (build ASN.1 request object) | same file's own adjacent `try/except ImportError` fallback pattern (lines 6-13, `MethodData`/`METHOD_DATA` rename fix) | exact — same file, same defect class (impacket 0.13.0 API-shape drift), already-applied sibling fix |
| `tests/test_identity_scanner_hardening.py` (remove 2 xfail markers) | test | request-response (unit test) | itself — the xfail decorator blocks at lines 85-94 and 114-119 are the exact edit targets | exact |
| `tests/skip_registry.py` (remove 2 ALLOWED_SKIPS entries) | config/registry | CRUD (list of tuples) | itself — existing entry rows are the shape to delete; module docstring (lines 1-13) documents the "stale skips are deleted" rule | exact |
| `docs/test-triage-149.md` (update ledger rows) | documentation | transform (ledger update) | itself — table rows at lines 163-164 (Cluster disposition table) + narrative at lines 449-464 (Reconciliation section) | exact |
| `CONTRIBUTING.md` (new, D-08) | documentation | N/A (static doc) | `README.md` (root doc, badge/heading/fenced-command style) + `docs/test-triage-149.md`'s "how to reproduce" fenced-command convention | role-match (no CONTRIBUTING.md exists; closest analog is the repo's existing root-doc voice/format) |

## Pattern Assignments

### `.github/workflows/python-ci.yml` — new Linux/pytest job (D-02)

**Primary analog:** `.github/workflows/python-staleness.yml` (whole file, 41 lines) — same `ubuntu-latest` + Python 3.11 + pinned-SHA-actions + pytest-invocation shape as the job this phase needs, just narrower in scope (staleness-only vs full suite).

**Secondary analog (house style for job block shape/triggers/permissions):** `.github/workflows/python-ci.yml`'s existing Windows jobs (same file, lines 1-33 for triggers/permissions, lines 14-32 for the simplest job `windows-sensor-smoke`).

**Top-of-file triggers + permissions to preserve exactly** (`python-ci.yml` lines 1-11):
```yaml
name: Python CI

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

# IN-01: Least-privilege token — this workflow only needs to check out code.
permissions:
  contents: read

jobs:
```
Do not modify this block — the new job is additive under `jobs:`.

**Simplest existing job as structural template** (`python-ci.yml` lines 14-32, `windows-sensor-smoke`):
```yaml
  windows-sensor-smoke:
    name: Windows Sensor Smoke
    runs-on: windows-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1

      - name: Setup Python 3.11
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.11'

      - name: Install project (editable) and pytest
        run: |
          pip install -e .
          pip install pytest

      - name: Run Windows sensor smoke tests
        run: pytest tests/test_sensor_windows_smoke.py tests/test_sensor_no_verify_false.py -v
```
Note the **identical pinned SHAs** for `actions/checkout` (`34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1`) and `actions/setup-python` (`a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0`) are reused verbatim in `python-staleness.yml` too — these are the pinned versions to reuse for the new job, not re-resolve.

**`ubuntu-latest` pytest gate to mirror directly** (`python-staleness.yml`, full file — this is the closest role+platform match: a Linux, pip-install, pytest-invocation CI job):
```yaml
name: Python Staleness Gate

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: '0 9 * * 1'  # Mondays 09:00 UTC

jobs:
  staleness:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1

      - name: Setup Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
        with:
          python-version: '3.11'

      - name: Install project (editable) and pytest
        run: |
          pip install -e .
          pip install pytest

      - name: Run staleness gates
        run: |
          pytest \
            tests/test_qramm_staleness.py \
            tests/test_compliance_freshness.py \
            ...
            -v -k "staleness or freshness"
```

**What the new job must change vs. this template:**
- `runs-on: ubuntu-latest` (same as staleness job — reuse directly, per D-02).
- Install step must be `pip install -e ".[all]"` (D-01 — quote the extras, per README.md's own zsh-glob warning: `Keep the quotes around 'quirk-scanner[all]'`), NOT the bare `pip install -e .` + `pip install pytest` two-liner used by the smoke/staleness jobs — those jobs run a narrow test subset that doesn't need the full extras surface; this new job runs the whole suite and needs `.[all]`'s dashboard/cbom/db/motion/redis/adcs/docx/notify/tickets extras (`pyproject.toml` lines 117-128) plus pytest itself. `pytest` is not in base deps, so add `pip install pytest` (or bundle via a dev extra) after the `.[all]` install.
- Run step must be `pytest -q -m ""` (D-04 — the CI invocation explicitly overrides `pyproject.toml`'s default `addopts = "-m 'not slow'"` at `pyproject.toml` line 157; do not rely on the default).
- Job name/key: e.g. `linux-full-suite` / `Linux Full Suite` (or similar) — executor's discretion per CONTEXT.md, follow the `name:`/job-key-under-`name:` convention visible in every existing job (`windows-sensor-smoke` → `name: Windows Sensor Smoke`, `windows-packaging-spike` → `name: Windows Packaging Spike`, etc.).
- No `continue-on-error: true` — unlike `windows-packaging-spike` (spike, explicitly non-blocking) this new job **must gate** the same way `windows-sensor-e2e` does (`python-ci.yml` line 211 comment: `# No continue-on-error — this job must gate (WINBUILD-04 acceptance criterion)`). Copy that same "must gate" posture/comment convention for this job.

**Job docstring/comment convention to copy** (`python-ci.yml` line 211):
```yaml
    # No continue-on-error — this job must gate (WINBUILD-04 acceptance criterion)
```
Use an equivalent comment referencing SUITE-02/SUITE-03 for the new job.

---

### `quirk/scanner/kerberos_scanner.py::_build_as_req` (D-05 bug fix)

**Analog:** the file's own already-applied sibling fix for the same defect class, immediately above in the same file (lines 6-13):
```python
    try:
        # impacket>=0.13.0 (current pin) renamed MethodData -> METHOD_DATA.
        # Phase 149-11 reconciliation: the un-guarded name broke the whole
        # try/except import block, silently disabling IMPACKET_AVAILABLE and
        # every Kerberos scan even with a correctly-pinned impacket installed.
        from impacket.krb5.asn1 import METHOD_DATA as MethodData
    except ImportError:
        from impacket.krb5.asn1 import MethodData  # impacket <0.13.0 fallback
```

**Bug location** (lines 85-98, `_build_as_req`):
```python
def _build_as_req(client_name, server_name, realm: str):
    """Build an unauthenticated AS-REQ advertising all known etypes.

    Returns an AS_REQ ASN.1 object ready for encoding and transmission.
    Per D-01, D-03: advertises ALL_ETYPES so the KDC returns its full support list.
    """
    as_req = AS_REQ()
    as_req['pvno'] = 5
    as_req['msg-type'] = int(constants.ApplicationTagNumbers.AS_REQ.value)

    req_body = as_req['req-body']
    req_body['kdc-options'] = constants.KDCOptions(
        constants.KDCOptions.forwardable
    )
```

**Root cause (from `docs/test-triage-149.md` reconciliation, lines 449-458 and the `ALLOWED_SKIPS` reason strings):** impacket `>=0.13.0,<0.14` changed `constants.KDCOptions` from a bit-flag helper class to a plain `enum.Enum`. The old call site treats `KDCOptions(...)` as constructing a pyasn1 BitString from a bit-flag name, which now raises `KeyError('Bad BitString initializer type')` because `constants.KDCOptions.forwardable` is now a bare enum member, not a bit-flag object the BitString constructor understands.

**Fix pattern to follow:** same "detect impacket API shape, branch accordingly" posture as the `MethodData`/`METHOD_DATA` fix above — either (a) construct the pyasn1 `KDCOptions` BitString directly from the enum member's `.value`/name rather than calling the class as a bit-flag constructor, or (b) add a version-shape try/except mirroring the import-time guard's structure. Concrete fix code is a scanner-internals decision for the plan/executor, not this pattern map — but the **house pattern is**: guard with a comment citing the phase/decision (`# Phase 150 D-05: impacket 0.13.0 changed KDCOptions from ... `) exactly like the existing comment block does, so a future reader immediately understands why the code branches.

---

### `tests/test_identity_scanner_hardening.py` — remove 2 xfail markers (D-05)

**Exact blocks to edit** (lines 85-95 and 114-120):
```python
@pytest.mark.xfail(
    strict=False,
    reason="Phase 149-11: impacket 0.13.0 (current pin) changed constants.KDCOptions "
    "from a bit-flag helper class to a plain enum.Enum; _build_as_req's "
    "constants.KDCOptions(constants.KDCOptions.forwardable) call now raises "
    "pyasn1 KeyError('Bad BitString initializer type'). The MethodData/METHOD_DATA "
    "import rename (also 0.13.0) was fixed in this reconciliation plan, restoring "
    "IMPACKET_AVAILABLE; this residual KDCOptions incompatibility is a distinct, "
    "deeper impacket 0.13.0 API-shape change flagged for a dedicated Phase 150 fix.",
)
def test_kdc_udp_decode_failure_logs(_kerb_mod, caplog):
    ...

@pytest.mark.xfail(
    strict=False,
    reason="Phase 149-11: same impacket 0.13.0 KDCOptions enum incompatibility as "
    "test_kdc_udp_decode_failure_logs — _build_as_req raises before the nonce "
    "assertion is ever reached. See that test's xfail reason for detail.",
)
def test_build_as_req_nonce_uses_secrets(_kerb_mod):
    ...
```
**Action:** delete both `@pytest.mark.xfail(...)` decorator blocks entirely (the `def` lines and test bodies stay unchanged) so both tests become plain, permanently-enforced passes once the `_build_as_req` fix lands. Import of `pytest` at the top of the file may still be needed for other markers/fixtures in the file — verify before removing any import.

---

### `tests/skip_registry.py` — remove 2 ALLOWED_SKIPS entries (D-05)

**Exact rows to delete** (lines 202-203):
```python
    ("test_identity_scanner_hardening.py", 85, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): impacket 0.13.0 (current pin) changed constants.KDCOptions from a bit-flag helper class to a plain enum.Enum; _build_as_req's constants.KDCOptions(constants.KDCOptions.forwardable) call raises pyasn1 KeyError('Bad BitString initializer type'). The separate MethodData/METHOD_DATA import rename (also 0.13.0) was fixed in quirk/scanner/kerberos_scanner.py by this plan, restoring IMPACKET_AVAILABLE=True; this residual KDCOptions incompatibility is a distinct, deeper impacket 0.13.0 API-shape change flagged for a dedicated Phase 150 fix; see docs/test-triage-149.md#reconciliation-impacket-kdcoptions-enum"),
    ("test_identity_scanner_hardening.py", 114, "pre_existing_triage_149", "TRIAGE-149 (Plan 11): same impacket 0.13.0 KDCOptions enum incompatibility as test_kdc_udp_decode_failure_logs; see docs/test-triage-149.md#reconciliation-impacket-kdcoptions-enum"),
```
**Action:** delete both tuple rows entirely. Do NOT touch the unrelated entry at line 55 (`("test_identity_scanner_hardening.py", 80, "optional_extra", "impacket not installed")`) — that guards the `pytest.importorskip("impacket")` fixture skip and stays regardless of the xfail fix, since D-01 means the new CI job still won't have impacket installed.

**Registry docstring convention** (lines 1-13) reaffirms the exact intent of this removal:
```python
"""Phase 41 D-02: Central allowed-skip registry.

Each entry: (file_relative_to_tests_dir, line_number, category, reason)
category in {"optional_extra", "live_infra", "pre_existing_triage_149"}

Per CONTEXT.md D-01..D-05: stale skips are deleted; optional-extra and
live-infra skips are registered here so the meta-test gate (test_skip_registry.py)
can validate that no NEW unregistered skip slips into the suite.
```
**Caveat:** the `line_number` field in each tuple is the source-line number in the target test file. Since deleting the 2 xfail decorator blocks in `test_identity_scanner_hardening.py` shifts subsequent line numbers, verify `tests/test_skip_registry.py::test_no_unregistered_skips` (the AST-walking meta-gate cited in CONTEXT.md canonical_refs) still passes after both edits — any remaining/unrelated `ALLOWED_SKIPS` rows referencing line numbers below the deleted blocks in the same file (none currently exist per the grep above — only lines 202/203 reference this file besides the unrelated line-55/80 entry) need their line numbers re-verified if they shift.

---

### `docs/test-triage-149.md` — update ledger rows (D-05)

**Cluster disposition table rows to update** (lines 163-164):
```
| `tests/test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs` | **superseded by Plan 11** — partially fixed, residual quarantined-xfail | genuine impacket 0.13.0 API drift ... | ... yes (tests/skip_registry.py, `test_identity_scanner_hardening.py:85`) |
| `tests/test_identity_scanner_hardening.py::test_build_as_req_nonce_uses_secrets` | **superseded by Plan 11** — quarantined-xfail | same impacket 0.13.0 `KDCOptions` enum incompatibility | ... yes (tests/skip_registry.py, `test_identity_scanner_hardening.py:114`) |
```
**Action:** change the Disposition column from "quarantined-xfail" to something like "**fixed in Phase 150 (D-05)**" and the last column ("Registered in skip_registry.py?") from "yes ..." to "no — fix landed, xfail/registry entries removed"; do not delete the row/history, since it documents provenance.

**Reconciliation narrative to update** (lines 455-464, within the `### What changed` section):
```
   This uncovered a **second, deeper** impacket 0.13.0 incompatibility — `KDCOptions`
   changed from a bit-flag helper class to a plain `enum.Enum`, breaking
   `_build_as_req`'s pyasn1 BitString construction — which is quarantined (not fixed)
   below as out of scope for a one-line import fix; flagged for a dedicated Phase 150 fix.
...
- **impacket 0.13.0 `KDCOptions` enum incompatibility (2 tests)** —
  `test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs` and
  `::test_build_as_req_nonce_uses_secrets`. See fix #2 above.
```
**Action:** append a short addendum (new subsection or inline note, e.g. `### Phase 150 follow-up: KDCOptions fixed`) stating the `KDCOptions` enum incompatibility was fixed in Phase 150 D-05, both tests' xfail markers and skip_registry entries were removed, and they are now permanently CI-enforced passes (with the D-01 caveat that they still skip in the new CI job itself since `[all]` excludes `identity` extras — this nuance from CONTEXT.md's D-05 note is important to carry into the doc so a future reader doesn't wonder why the CI job doesn't exercise them). Do not rewrite the historical Phase 149 narrative — add, don't overwrite, per the doc's existing "ledger integrity" convention (lines 496+ describe mechanical row-count/no-duplicate verification, implying the ledger is treated as an append-safe audit trail).

---

### `CONTRIBUTING.md` — new file at repo root (D-08)

**No direct analog** (first file of its kind in the repo). Closest style/tone/structure reference: `README.md`'s root-doc conventions — badges/heading style is not needed here, but the **fenced-command + explanatory-callout voice** is worth mirroring, e.g. `README.md`'s Quick Start section:
```markdown
From a virtual environment (recommended on every platform, **required** on Debian/Ubuntu/Kali/Parrot — see note below):

\`\`\`bash
python3 -m venv .venv && source .venv/bin/activate
pip install 'quirk-scanner[all]'
quirk init
quirk --config config.yaml
\`\`\`

> **Use a venv.** Modern Debian-based distros ... Keep the quotes around `'quirk-scanner[all]'` — zsh ... otherwise treats `[all]` as a glob and fails with `no matches found`.
```

**Content requirements per D-08 (Success Criterion 4):**
1. The exact command to run the full suite locally to match CI: `pytest -q -m ""` (quote it in a fenced code block, same style as above).
2. What "green" means: 0 failed; skips/xfails are expected and fine (this is the standard `docs/test-triage-149.md`'s own "Reconciliation" section states in prose — reuse that framing, e.g. paraphrase the "fresh `pytest -q -m ""` is 0 failed (3088 passed, 42 skipped, 81 xfailed)" framing from `149-11-SUMMARY.md`/`docs/test-triage-149.md`, without hardcoding stale numbers that will drift).
3. A pointer to `docs/test-triage-149.md` for why specific tests are quarantined — use a relative Markdown link `[docs/test-triage-149.md](docs/test-triage-149.md)`, matching `README.md`'s own relative-link convention (e.g. `[Getting Started guide](docs/getting-started.md)`).
4. No Obsidian sync needed (per D-08 explicit note) and no CLAUDE.md doc-checklist row change needed.

**Format convention to copy from `README.md`:** relative markdown links to `docs/*.md` files use bare relative paths without a leading `./`, e.g. `[Installation → Parrot OS / Kali / Debian](docs/installation.md#parrot-os--kali--debian-pep-668)`. Anchors use GitHub's auto-slug convention (lowercase, spaces→hyphens, punctuation stripped).

---

## Shared Patterns

### Pinned GitHub Actions SHAs
**Source:** `.github/workflows/python-ci.yml` and `.github/workflows/python-staleness.yml` (identical values in both)
**Apply to:** the new CI job in `python-ci.yml`
```yaml
uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5  # v4.3.1
uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065  # v5.6.0
```
Reuse these exact pins — do not re-resolve or bump versions as part of this phase.

### `permissions: contents: read` top-level block
**Source:** `.github/workflows/python-ci.yml` lines 9-11 (comment cites `IN-01`)
**Apply to:** no change needed — the new job inherits the existing workflow-level `permissions:` block; do not add a job-level override unless the new job needs write access (it doesn't).

### Extras-quoting convention (`.[all]` vs `[all]`)
**Source:** `README.md` Quick Start callout — `pip install 'quirk-scanner[all]'` with the explicit warning about zsh glob expansion.
**Apply to:** the new CI job's install step. Since GitHub Actions runners use `bash` by default (not zsh) this specific footgun likely doesn't reproduce, but quoting `".[all]"` defensively is still the established repo convention and should be followed for consistency, e.g. `pip install -e ".[all]"`.

### "Documented exclusion + guard test" posture for extras groups
**Source:** `pyproject.toml` lines 60-66 (pysnmp), 74-78 (schemathesis), 129-132 (impacket) — each exclusion from `[all]` has an inline comment citing the phase/decision and the guard test file.
**Apply to:** D-01's CI job install step — no code change needed here (the job just installs `.[all]` as-is), but if a plan-level comment is added near the CI job's install step explaining why `identity`/`hw` aren't installed, follow this exact citation style: `# D-01: quirk[all] intentionally excludes identity/hw — see pyproject.toml lines 60-66, 129-132`.

### Skip-registry entry-removal shape
**Source:** `tests/skip_registry.py` module docstring, lines 6-8: "Per CONTEXT.md D-01..D-05: stale skips are deleted; optional-extra and live-infra skips are registered here."
**Apply to:** D-05's registry edit — this is a **deletion**, not a category change; the file's own convention (established in Phase 41, reused in Phase 149) is that a skip becomes un-registered by removing its tuple row entirely, not by changing its category string.

## No Analog Found

None of the 7 target files lack an analog outright. `CONTRIBUTING.md` is a genuinely new file type (no other root-level contribution-guide doc exists), but README.md's voice/link/fenced-command conventions provide sufficient style grounding — see the Pattern Assignments section above.

## Metadata

**Analog search scope:** `.github/workflows/`, `quirk/scanner/kerberos_scanner.py`, `tests/test_identity_scanner_hardening.py`, `tests/skip_registry.py`, `docs/test-triage-149.md`, `README.md`, `pyproject.toml`.
**Files scanned:** 7 read directly (2 workflow YAMLs in full, kerberos_scanner.py imports+`_build_as_req` region, test file's Kerberos test block, skip_registry.py header+matching rows, test-triage-149.md's Cluster-9 table rows + Reconciliation section, README.md's top ~40 lines, pyproject.toml's optional-dependencies + pytest.ini_options sections).
**Pattern extraction date:** 2026-08-12
