# 209-07 — Manual Verification Record

Recorded evidence for the two Manual-Only Verifications in `209-VALIDATION.md`
(ROADMAP criteria 3 and 4). Per plan `209-07`, the pre-flight ground truth below was
recorded BEFORE any human observation, so the human check compares against fixed facts
rather than confirming its own expectation.

---

## Task 1 — Pre-flight ground truth

### Environment staged

- Dashboard bundle build: `quirk/dashboard/static/index.html` last-modified
  `Mon Sep 14 19:27:02 2026` (per `Last-Modified` response header), which is NEWER than
  `src/dashboard/src/pages/executive.tsx` source mtime (`Sep 14 15:26:44 2026`). Build is
  fresh — no `npm run build` was needed.
- Output directory resolved from `./config.yaml` `output.directory: "output"` →
  `./output/` (repo-root relative), confirmed live via the manifest response below.
- **Stamp re-derivation finding:** research's sampled stamp `20260914-041322` is **no longer
  the newest** — a scan ran since. The current newest `run-stats-*.json` group, and the one
  actually served, is **`20260914-194719`** (`run-stats-20260914-194719.json`, `ended_utc:
  2026-09-14T19:47:19.492308+00:00`). All five artifacts are present in this stamp group.
- A stale `quirk serve` process (PID 97183) was found already running on port 8512, started
  `12:20PM` — **before** this phase's `reports.py` route file existed (file mtime
  `14:44:13`, git commit `14:47:33`). That process was serving old code: a probe request to
  `/api/reports/latest/manifest` fell through to the SPA catch-all and returned `index.html`
  (200, `content-type: text/html`) instead of JSON. It was killed and the server was
  restarted from current code before recording anything below.
- No `QUIRK_API_TOKEN` env var is set and `config.yaml` has no `security.api_token` — per
  `quirk/dashboard/api/middleware/auth.py` `_get_configured_token()`, **auth is disabled on
  this machine** (`require_auth` passes through with an empty configured token). No
  `X-API-Key` header or bearer token is required for the curl probe below or for the
  operator's browser session.

### Pre-flight artifact table (on-disk ground truth, stamp `20260914-194719`)

| # | Filename | Byte size | sha256 (full) |
|---|----------|-----------|----------------|
| 1 | `report-20260914-194719.html` | 40337 | `5dcbacadb16638410e80d97f992562c90e14397e686f9bad5ac75919cb90c575` |
| 2 | `report-20260914-194719.pdf` | 331202 | `7485c9188ca9d43b9209b82f40f391c5af879ff6607893c0fa8d6051e1b0ae88` |
| 3 | `report-20260914-194719.docx` | 39651 | `41b14d0a470bdbad2da58a2985e476e44330a85a5237d36bf672fe3f85d404f1` |
| 4 | `cbom-20260914-194719.cdx.json` | 4577 | `45c28eb39aa2867554f71ec68c1f84f52156709a5c4302a1f729d41d029c6baa` |
| 5 | `cbom-20260914-194719.cdx.xml` | 5099 | `b4161c2079f7652b91e4bf3b052501b50f1a0c1e887b8883a0aa71625b8b5d2c` |

These sizes/hashes are what the five downloaded files in Task 2 must match. A mismatch —
especially a download of only a few hundred bytes — indicates a saved error body, not a real
artifact.

### Live manifest response (verbatim)

Command run (no auth header needed — auth disabled on this machine, see above):

```
curl -s -i http://127.0.0.1:8512/api/reports/latest/manifest
```

Response:

```json
{"scan_time":"2026-09-14T19:47:19.492308+00:00","stamp":"20260914-194719","formats":{"html":{"available":true,"reason":null},"pdf":{"available":true,"reason":null},"docx":{"available":true,"reason":null},"cbom-json":{"available":true,"reason":null},"cbom-xml":{"available":true,"reason":null}}}
```

**Stamp match check:** manifest `stamp` = `20260914-194719`, matches the independently
derived newest `run-stats-*.json` stamp from the filesystem listing above. MATCH — no
discrepancy to report.

### Server details for the human operator

- Server process: `.venv/bin/quirk serve --port 8512 --no-open`, started fresh from current
  code at `2026-09-14 20:02:xx UTC` (PID recorded in `/tmp/quirk-serve-209-07.log`).
- URL: **http://127.0.0.1:8512/** — Executive page is the dashboard's default/primary page
  reachable from the left nav.
- Auth: **disabled** on this machine (no token/header required in the browser).
- Server left running for Task 2 / Task 3 observation.

---

## Task 2 — Human verification: download and open all five formats

**Status: PENDING — not yet performed. Requires the operator.**

_(To be appended by the operator: a 5-row observed table — downloaded filename, observed
byte size, open/parse outcome — compared against the Task 1 pre-flight table above, with
any mismatch flagged as FAIL.)_

---

## Task 3 — Human verification: DOCX-unavailable reason against a genuinely missing extra

**Status: PENDING — human observation not yet performed. Requires the operator.**

`python-docx` IS importable on the primary machine environment (confirmed by the manifest
above: `"docx":{"available":true,...}`), so the primary environment cannot produce the
extra-missing branch. A separate isolated environment was therefore staged.

### Task 3 pre-flight (staged 2026-09-15, BEFORE any human observation)

Recorded to the same standard as Task 1: the environment facts and the API-level response are
written down first, so the operator's UI observation compares against fixed facts. **This
pre-flight is NOT a substitute for the human check** — the checkpoint requires the reason
string to be observed as *displayed in the UI*, and the automated/monkeypatched test is
explicitly forbidden as evidence for this row (T-209-13).

**Isolated environment:**

- Location: `$CLAUDE_JOB_DIR/tmp/209-task3/` (venv + output dir + config)
- Python: **3.14.7**
- Install: `pip install .` then `pip install ".[dashboard]"` from this source tree —
  **`[docx]` extra deliberately NOT installed**; `[all]` was avoided because it bundles
  `[docx]` (`pyproject.toml:125`).
- `import docx` result: **`ModuleNotFoundError: No module named 'docx'`** — verified twice,
  after each install step. The extra is genuinely absent, not monkeypatched.
- Installed wheel verified self-contained: `dashboard/static/index.html` sha256
  `3b40cd6e…60836`, **identical to the source-tree build**, so the operator sees the current
  bundle and not a stale one; `dashboard/api/routes/reports.py` present in the wheel.
- Output directory: staged copy of stamp group `20260914-194719` containing **four** artifacts
  (`.html`, `.pdf`, `.cdx.json`, `.cdx.xml`) plus `run-stats-20260914-194719.json` —
  **`report-20260914-194719.docx` deliberately absent.**

Both branch conditions in `_format_availability` (`reports.py:197-211`) therefore hold at once:
the `.docx` file is absent AND `_docx_extra_available()` is False. With the file absent but the
extra present, the code would return `REASON_RENDER_FAILED` instead — the confusable string
this row exists to distinguish.

**Staging error found and corrected before the operator was involved:** the first staged
`config.yaml` was a minimal `output.directory`-only stub. `load_config` raised
`KeyError: 'assessment'`, and `_output_directory()`'s documented broad-except degraded it to
`None`, producing a plausible-looking all-formats `"No scan has run yet."` manifest. Had this
been handed to the operator unprobed, they would have verified the wrong branch entirely. The
config was rebuilt from the repo's real `config.yaml` with only `output.directory` overridden.

**Live manifest response from the isolated environment (verbatim):**

```
curl -s http://127.0.0.1:8513/api/reports/latest/manifest
```

```json
{"scan_time":"2026-09-14T19:47:19.492308+00:00","stamp":"20260914-194719","formats":{"html":{"available":true,"reason":null},"pdf":{"available":true,"reason":null},"docx":{"available":false,"reason":"DOCX requires the optional extra: pip install quirk[docx]"},"cbom-json":{"available":true,"reason":null},"cbom-xml":{"available":true,"reason":null}}}
```

At the API level the reason string matches `REASON_DOCX_EXTRA_MISSING` (`reports.py:109`)
exactly, and the other four formats remain `available: true`. **What remains for the operator
is whether the UI displays that string on a disabled DOCX button with the other four enabled.**

- Server for the operator: **http://127.0.0.1:8513/** (isolated env), left running.
- Auth: disabled, same as the primary environment.

_(To be appended by the operator: the environment used, whether `import docx` failed, and
the verbatim displayed reason string — or an explicit "not executed" result with reason. No
automated/monkeypatched test result may be substituted here.)_
