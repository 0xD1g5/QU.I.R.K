# Phase 108: Sensor Push CLI + Windows CI - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **sensor-side runtime and CLI** for the distributed scanner:
`quirk sensor enroll`, `quirk sensor push`, `quirk sensor export-results`, and
`quirk console import-results`. A consultant can enroll a sensor against a console
(binding console URL + segment + UUID, receiving a one-time token), run a local scan
(reusing `run_scan.py` unchanged) and push results over authenticated HTTPS with
`tenacity` retry, spool-and-forward when offline, and move results by sneakernet for
air-gapped segments. It also lands the cross-OS prerequisites: a POSIX-ism audit so the
sensor runs identically on Windows and POSIX, `platformdirs`-resolved config/data dirs,
the `_NoRedirectHandler` extraction to `quirk/util/no_redirect.py` (STAB-02), and a
hard-gated `windows-latest` CI smoke job.

**Out of scope (downstream):** the console ingestion endpoint that *receives* pushes
(Phase 109), cross-sensor merge & scoring (Phase 110), dashboard sensor awareness
(Phase 111). This phase defines and *tests* the wire format; Phase 109 consumes it.

</domain>

<decisions>
## Implementation Decisions

### Pre-locked from Phase 106/107 (carried forward — do NOT re-litigate)
- **(106 D-02 / 107):** Enrollment tokens are **one-time-use** — `secrets.token_urlsafe(32)`,
  SHA-256 hash stored in `sensor_tokens`; raw token never persisted. Mirrors `token_cmd.py`.
- **(106 D-13):** Bound config carries `sensor_id` (UUID), `segment`, `engagement` (nullable),
  `sensor_version`; the console-side `sensors` table holds `enrolled_at`, `last_push_at`,
  `expected_cadence_minutes`.
- **(106 D-15):** Air-gap export writes the **identical wire payload** (same `payload_id`,
  `schema_version`, `pushed_at`, zstd compression, HMAC) to a file; import runs it through the
  **same ingest + dedup path**. Replay-window check is **transport-conditional**: ±15-min window
  applies to HTTPS push only; air-gap import skips the window but keeps `payload_id` dedup.
- **(106 D-05):** Windows = **floor in v5.4** — OS-agnostic wire contract, `pip install` on
  Python 3.11+ with no POSIX deps, POSIX-ism audit (`scheduler_cmd.py:136` relative path →
  `cfg.output_root`-anchored; `:258-259` SIGTERM → `sys.platform != 'win32'`-guarded),
  `platformdirs` for dirs, `windows-latest` CI smoke job as a **hard gate** (no
  `continue-on-error`). PyInstaller EXE + Scheduled Task + `pywin32` are v5.5/out.
- **(STAB-02):** `_NoRedirectHandler` (currently duplicated in `notify/channels/webhook.py`
  and `ticketing/servicenow.py`) is extracted to `quirk/util/no_redirect.py`; the sensor push
  client imports from there. Treat as a sensor-phase prerequisite.

### Sensor Config File (written by `enroll`)
- **Format:** YAML — mirrors `config.yaml` and the `token_cmd.py` full-file round-trip pattern.
- **Location:** `platformdirs.user_config_dir("quirk")/sensor.yaml` (cross-OS; SENSOR-05).
- **Fields:** `console_url`, `sensor_id` (UUID), `segment`, `engagement`, `sensor_version`.
  The one-time enrollment token is **NOT** stored (consumed at enroll).
- **Write safety:** atomic (tempfile + `os.replace`), reusing the
  `token_cmd._write_token_to_config` idiom so a mid-write crash cannot corrupt the file.

### Store-and-Forward Spool (SENSOR-03)
- **Location:** `platformdirs.user_data_dir("quirk")/spool/`, file-per-payload.
- **Naming:** `{payload_id}.json.zst` (`payload_id` is already a unique UUID).
- **Bound policy:** max file count (default 100) **and** a max total-bytes cap; when full,
  **oldest-evicted with a warning** (bounded directory per SENSOR-03 — never unbounded growth).
- **Retry order & cleanup:** FIFO by mtime on the next `quirk sensor push`; delete the spooled
  file on HTTP 200 **or** 409 (409 = already accepted by console = success).

### Air-Gap Export/Import File (SENSOR-04)
- **Contents:** identical wire payload (zstd-compressed JSON + HMAC) — "push-to-file" per D-15.
- **Naming:** `{sensor_id}-{payload_id}.qpush`.
- **Import validation:** `quirk console import-results` runs the **same ingest + dedup path**;
  skips the ±15-min replay window (D-15 transport carve-out) but keeps `payload_id` dedup (→ 409
  on replay).
- **Payloads per file:** one payload per file (mirrors a single push).

### CLI Ergonomics & Windows Contract
- **Command structure:** parent-subcommand groups —
  `quirk sensor <enroll|push|export-results>` and `quirk console import-results` — matching the
  existing `compliance`/`cmvp` subparser pattern in `run_scan.py:main()`.
- **Token display:** `enroll` prints the one-time token once to stdout with a clear
  "won't be shown again" warning (not written to a file).
- **`verify=True` enforcement:** hardcoded, with **no CLI flag** to disable; a CI grep gate
  asserts the push client contains no `verify=False`.
- **Retry tuning:** `tenacity` — 5 attempts, exponential backoff 2s→60s cap, retry on
  connection errors and 5xx **only** (never 4xx — a 4xx is a permanent client/auth error).

### Claude's Discretion
- Exact `platformdirs` app author/name args, spool default byte cap value, and `.qpush`
  internal envelope layout (as long as it is byte-identical to the HTTPS push body).
- Module organization of `sensor_cmd.py` / `console_cmd.py` and helper factoring.
- Precise CI grep-gate expression and whether the Windows smoke job runs a stub console or
  asserts on serialized payload bytes directly.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/cli/token_cmd.py` — `_write_token_to_config()` shows the atomic full-file YAML
  round-trip (tempfile + `os.replace`) and `secrets.token_urlsafe`/SHA-256 token idiom.
- `quirk/notify/channels/webhook.py` + `quirk/ticketing/servicenow.py` — the duplicated
  `_NoRedirectHandler` (urllib redirect-blocking SSRF guard) to extract to
  `quirk/util/no_redirect.py`.
- `quirk/util/url_allowlist.py::validate_external_url` — pre-connection SSRF allowlist used
  alongside `_NoRedirectHandler`; the push client should validate the console URL the same way.
- `run_scan.py` — reused **unchanged** for the local scan that `quirk sensor push` runs.

### Established Patterns
- **CLI dispatch:** `run_scan.py:main()` switches on `_sys.argv[1]` and lazily imports a
  `run_X` entry from `quirk/cli/X_cmd.py` (e.g. `run_token`, `run_schedule`). New `sensor`
  and `console` commands follow this exact pattern (`run_sensor`, `run_console`).
- **Subparser grouping:** `compliance` builds nested `add_subparsers` — model for
  `sensor enroll|push|export-results`.
- **Entry point:** `pyproject.toml [project.scripts] quirk = "run_scan:_run_main_with_job_guard"`.

### Integration Points
- New deps `platformdirs` and `tenacity` are required (not yet vendored) — declare in
  `pyproject.toml`. Both are permitted (explicitly named in SENSOR-02/05); not on the D-04
  forbidden list.
- `quirk/models.py` `sensors` / `sensor_tokens` / `sensor_pushes` tables (Phase 107) — the
  enroll/push flow writes against these on the console side; the wire payload this phase
  defines must carry the columns Phase 109 will ingest.

</code_context>

<specifics>
## Specific Ideas

- The wire payload produced by `quirk sensor push` and by `quirk sensor export-results` must be
  **byte-identical** — export is literally "push to a file." This is the single most important
  invariant to preserve for Phase 109/110 to have one ingest path.
- Windows correctness is validated on a **real `windows-latest` runner** as a hard CI gate; the
  Linux chaos lab does not satisfy SENSOR-06. The smoke job must catch backslash paths in the
  serialized payload and confirm clean process shutdown.

</specifics>

<deferred>
## Deferred Ideas

- PyInstaller frozen EXE, Windows Scheduled Task registration, and signed packaging — v5.5
  ceiling per 106 D-05.
- Automatic merge trigger (poll-on-full-check-in) — v5.5 per 106 D-06; merge stays manual.
- Spooled-payload TTL/cleanup job — none in v5.4 per 106 D-10 (low single-tenant volume).

</deferred>
