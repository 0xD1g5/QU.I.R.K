# QU.I.R.K. Administrator Guide

This guide covers deploying a multi-sensor QUIRK console, enrolling sensors using the
two-step workflow, managing per-sensor authentication (issuance, revocation, rotation,
and compromise response), and configuring SNMP hardware scanning with a troubleshooting
checklist. It is intended for IT administrators responsible for day-to-day QUIRK
operations on enterprise deployments.

## Prerequisites

Before following this guide, confirm the following:

- **(a) QUIRK is installed.** If this is a first-time setup, follow
  [Getting Started](getting-started.md) to install and configure QUIRK before proceeding.
- **(b) `[hw]` extras installed** (hardware scanning only). SNMP hardware scanning
  requires `pip install 'quirk-scanner[hw]'`. This extra is **not included** in `[all]`
  due to the size of the pysnmp dependency. See
  [Operator's Guide §2.2](operators-guide.md#22-optional-extras-matrix) for the full
  optional extras matrix and the install command.
- **(c) Port 8512 connectivity.** The console host must be reachable from each sensor
  host on port 8512 (the default QUIRK console API port). Sensors push scan results
  to the console over this port.
- **(d) Python 3.11+.** This guide assumes a Python 3.11 or higher environment on all
  hosts.

---

## 1. Deploy the Console

Install QU.I.R.K. on the console host. Use `pip install quirk-scanner` for the core
scanner, or `pip install 'quirk-scanner[all]'` for full scanner coverage including
optional extras (excludes `[identity]` and `[hw]`):

```bash
pip install 'quirk-scanner[all]'
```

Start the server. The console binds loopback only by default; pass `--host 0.0.0.0`
to make it reachable over the network from sensor hosts:

```bash
quirk serve --host 0.0.0.0 --port 8512
```

The default port is 8512. QUIRK refuses to start on a network-reachable interface
when no `QUIRK_API_TOKEN` environment variable is set, unless you pass `--insecure`
to explicitly acknowledge a token-less bind on a trusted, firewalled segment. For
reverse-proxy and cloud-hosted console deployments, see
[Operator's Guide §8.1](operators-guide.md#81-provision-the-console).

**Verify reachability.** From a sensor host, confirm the console is accessible:

```bash
curl http://<console-host>:8512/api/health
```

Expect an HTTP 200 response. You can also open the URL in a browser. If the health
check fails, confirm port 8512 is permitted between the sensor and console hosts.

**Fields the sensor operator needs.** When you enroll a sensor (§2), the sensor's
`sensor.yaml` will contain two key fields required for push authentication:

- `console_url` — the base URL of the console (e.g. `https://console.corp:8512`)
- `console_api_token` — the per-sensor push credential minted by `quirk console enroll`

---

## 2. Enroll Sensors

Sensor enrollment is a two-step process: first provision the sensor on the **console
host**, then register the sensor configuration on the **sensor host**.

### Step 1 — Console host: mint the sensor token

On the console host, run `quirk console enroll` with a segment label. This provisions
the sensor rows in the console database and prints the per-sensor bearer token to
stdout:

```bash
quirk console enroll --segment <label>
# e.g.:
quirk console enroll --segment segment-a
```

The output looks like:

```text
Bearer token (copy now — shown once, never recoverable):
<per-sensor-token>
```

> **WARNING:** This bearer token is shown **once** and is never recoverable. Copy it
> immediately. Only a SHA-256 hash of the token is stored on the console — the raw
> value is gone after this terminal session. If the token is lost, you must revoke
> the sensor and re-enroll (see §3.2 and §3.3).

The `sensor_id` (a UUID) for this sensor is printed to stderr and will also be stored
in the sensor's `sensor.yaml` after Step 2.

### Step 2 — Sensor host: write the sensor configuration

On the sensor host, run `quirk sensor enroll` with the console URL, the matching
segment label, and the bearer token from Step 1:

```bash
quirk sensor enroll https://<console-host>:8512 \
  --segment <label> \
  --api-token <bearer-token-from-step-1>
```

The `--api-token` flag writes the console-minted token directly to the
`console_api_token` field in `sensor.yaml`. If you omit `--api-token`, that field is
written as empty and must be set manually before the sensor can push results.

**On-prem and RFC1918 console URLs:** Pass `--allow-internal-console` when the console
URL is a private or RFC1918 address:

```bash
quirk sensor enroll https://10.0.0.5:8512 \
  --segment segment-a \
  --api-token <bearer-token-from-step-1> \
  --allow-internal-console
```

**`sensor.yaml` default location:**
- Linux / macOS: `~/.config/quirk/sensor.yaml`
- Windows: `%APPDATA%\quirk\sensor.yaml`

Use `--config <path>` to write `sensor.yaml` to a custom location (useful in CI or
when running multiple sensors on the same host). After enrollment, the sensor is ready
to push scan results with `quirk sensor push`.

---

## 3. Manage Sensor Auth

### 3.1 Token Issuance

Each sensor authenticates push requests with its own per-sensor bearer token, issued
at enrollment by `quirk console enroll --segment <label>`. The console stores only the
SHA-256 hash of the raw token in the `sensor_tokens` table — the raw token itself is
never persisted anywhere on the console. The only live copy of the raw token is the
`console_api_token` value in the sensor's `sensor.yaml`.

This model means:
- A sensor can be revoked independently without affecting other enrolled sensors.
- If the raw token is lost (e.g. `sensor.yaml` is deleted), the sensor cannot push
  until it is revoked and re-enrolled.

### 3.2 Revoking a Sensor

To revoke a sensor's push access, run on the **console host**:

```bash
quirk console revoke-sensor <sensor_id>
```

`sensor_id` is a positional UUID argument (not a flag). The command stamps
`revoked_at = now` on all active token rows for that sensor and prints:

```text
Revoked token(s) for sensor_id: <sensor_id>
```

The command exits with an error if no active token exists for the given sensor ID.

**Finding the sensor_id:** The sensor_id is printed to stderr at enrollment time.
It is also stored in the sensor's `sensor.yaml` under the `sensor_id` key.

Once revoked, the sensor cannot push results to the console until it is re-enrolled
with a new token (see §3.3).

### 3.3 Rotating a Token

Token rotation is a routine, non-alarming procedure. Use it when cycling credentials
on a scheduled basis or after a token has been inadvertently exposed. The procedure
has three steps:

1. **Revoke the old token** (console host):
   ```bash
   quirk console revoke-sensor <sensor_id>
   ```

2. **Mint a new token** (console host):
   ```bash
   quirk console enroll --segment <original-label>
   ```
   Copy the new bearer token printed to stdout. A new `sensor_id` is also issued and
   printed to stderr.

3. **Re-enroll the sensor** (sensor host):
   ```bash
   quirk sensor enroll https://<console-host>:8512 \
     --segment <original-label> \
     --api-token <new-bearer-token>
   ```
   This overwrites `sensor.yaml` with the new `sensor_id` and `console_api_token`.

### 3.4 Responding to a Suspected Compromise

If a sensor token is suspected to have been compromised (for example, if `sensor.yaml`
was accessed by an unauthorised party), the response adds a log-review step to the
standard rotation procedure:

1. **Immediately revoke** (console host):
   ```bash
   quirk console revoke-sensor <sensor_id>
   ```
   Revocation takes effect immediately — the sensor cannot push as of this command.

2. **Treat the sensor as untrusted** until re-enrolled with a new token. Do not rely
   on scan results from the compromised `sensor_id`.

3. **Review scan/push logs** for anomalous pushes from that `sensor_id` in the time
   window before revocation. Look for unexpected push timing, unusual finding volumes,
   or pushes from unexpected IP addresses.

4. **Re-enroll with a new token** following the same three steps as §3.3.

The difference between routine rotation (§3.3) and compromise response is step 3 —
the log review. If no anomalies are found in the push history, re-enrollment completes
the response.

---

## 4. SNMP Setup

### 4.1 Network Requirements

SNMP hardware scanning requires the `[hw]` extras package, which is **not included**
in `[all]`:

```bash
pip install 'quirk-scanner[hw]'
```

Once installed, enable SNMP scanning and configure the community string in your
`config.yaml`. For the full config key reference including `enable_snmp` and
`snmp_community` defaults, placement under the `scan:` block, and sample output,
see [Operator's Guide §9.1](operators-guide.md#91-enable-snmp-scanning).

**Network prerequisites:**

- **UDP 161** must be permitted inbound from the QUIRK console/scan host to each
  scan target. SNMP uses UDP — not TCP — so standard TCP firewall rules do not cover
  it.
- **Community string hygiene:** The default `snmp_community` value is `"public"`.
  Change this to match the read-only community string configured on your devices.
  Using `"public"` on networks with a custom community string will cause all probes
  to fail silently.

QUIRK uses SNMPv2c read-only probes. SNMPv3 authentication is not currently supported.

### 4.2 Troubleshooting SNMP Probes

SNMP uses UDP — a connectionless protocol that fails silently. When a probe does not
reach a device, or a device does not respond, no error is raised and no exception
appears in the QUIRK output. Instead, hardware devices either appear with
`vendor: unknown` / `model: unknown` in the HardwareInventory section of the
dashboard CBOM tab, or are absent from the output entirely. Hardware rows appear after
the full scan completes, not incrementally — if you check the dashboard mid-scan,
hardware results will not yet be present.

Use the checklist below to diagnose a missing or incomplete hardware inventory.

| Symptom | Check | Fix |
|---------|-------|-----|
| No hardware rows appear at all | Verify `[hw]` extras are installed: `pip show pysnmp` | Run `pip install 'quirk-scanner[hw]'` |
| Devices appear with `vendor: unknown` / `model: unknown` | UDP 161 may be blocked between the QUIRK host and scan targets | Open a firewall rule permitting UDP 161 from the QUIRK scan host to each scan target |
| Devices missing despite reachable network | Wrong community string — probes reach devices but are rejected | Set `snmp_community` to the device's configured read-only community (see [operators-guide.md §9.1](operators-guide.md#91-enable-snmp-scanning)) |
| Probes fail on SNMPv3-only devices | QUIRK speaks only SNMPv2c — SNMPv3 devices will not respond to v2c probes | Enable an SNMPv2c read-only community on the device (SNMPv3 is not supported) |
| Target absent entirely from hardware results | Scan target is unreachable at layer 3 | Verify routing and confirm the host is reachable from the QUIRK scan host, and that the host is included in the configured scan scope |
