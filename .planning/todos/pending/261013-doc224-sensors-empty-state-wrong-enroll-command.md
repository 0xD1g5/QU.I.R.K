---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-MISC; found while re-auditing docs/deployment-cloud-console.md sensor enrollment rows
priority: low
area: src/dashboard/src/pages/sensors.tsx (empty state), src/dashboard/src/pages/__tests__/sensors-loading.test.tsx
status: pending
resolves_phase: null
---

# Sensors page empty state tells users to run an enroll command that fails

The Sensors page empty state (`src/dashboard/src/pages/sensors.tsx:126`) says:

> No sensors enrolled. Run: quirk sensor enroll --console <url> to register a sensor.

That command fails as written, and it is the wrong side of the enrollment anyway:

1. **There is no `--console` flag.** The console URL is positional: `quirk/cli/sensor_cmd.py:85`
   `enroll_p.add_argument("console_url", help="Console base URL (https://...)")`, and `--segment` is required.
   Probe in an isolated HOME (fresh `mktemp -d`, XDG_* redirected, no QUIRK_* set):
   - `quirk sensor enroll --help` -> `usage: quirk sensor enroll [-h] --segment SEGMENT [--sensor-id SENSOR_ID] ... console_url`
   - `quirk sensor enroll --segment s --console https://x.example` -> `quirk sensor: error: unrecognized arguments: --console`
2. **`sensor enroll` does not register anything on the console.** `_cmd_enroll` (`quirk/cli/sensor_cmd.py:206-289`)
   only writes a local `sensor.yaml` (`_write_sensor_config`, `:289`); it makes no network call. The page lists
   rows from `GET /api/sensor/registry` (`quirk/dashboard/api/routes/sensor.py:283-293`, `db.query(Sensor)`), and
   those rows are written by `quirk console enroll` (`quirk/cli/console_cmd.py:136`, `Sensor(` insert at `:216`).
   So the command that makes this page non-empty is `quirk console enroll --segment <label>`, run on the console.

The vitest `src/dashboard/src/pages/__tests__/sensors-loading.test.tsx:46` pins the wrong text
(`/No sensors enrolled\. Run: quirk sensor enroll --console/i`), so it must change with the fix.

- [ ] Change the empty-state message to point at `quirk console enroll --segment <label>` (console side), and
      optionally mention that the sensor host then runs `quirk sensor enroll <console-url> --segment <label> --sensor-id <id>`.
- [ ] Update `sensors-loading.test.tsx:46` to the new text.
- [ ] `npm run build` + `npm run lint` in `src/dashboard/` (statics under `quirk/dashboard/static` are committed).

## Feasibility & Effort

- **CONFIRMED** the bad flag: `quirk/cli/sensor_cmd.py:85` declares `console_url` positional; the isolated-HOME
  probe above returns `unrecognized arguments: --console`.
- **CONFIRMED** the registry source: `quirk/dashboard/api/routes/sensor.py:292` reads `Sensor` rows;
  `quirk/cli/console_cmd.py:216` is where `quirk console enroll` creates them; `quirk/cli/sensor_cmd.py:289` shows
  sensor-side enroll only writes `sensor.yaml`.
- **CONFIRMED** effort **S**: one string in `sensors.tsx:126`, one regex in `sensors-loading.test.tsx:46`, a rebuild.
- **UNKNOWN**: whether the copy should name both halves of the two-step enrollment or only the console step. A
  wording decision, no spike needed.
