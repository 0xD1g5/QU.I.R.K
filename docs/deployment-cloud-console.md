# Deploying a cloud-hosted console with internal sensors

*(Audience: operators who want to run the QU.I.R.K. **console** on a cloud VM —
Linode, EC2, GCP, a VPS — while **sensors** run inside customer networks and push
their findings out to it over HTTPS. This is the distributed sensor/console model
from [`architecture-distributed.md`](architecture-distributed.md), deployed with
the console in the cloud instead of on an on-prem jump host.)*

> For the on-prem variant (console and sensors all inside one estate) see
> [`operators-guide.md` §8](operators-guide.md). This guide layers the cloud-exposure
> hardening on top of that model.

---

## 1. Why this works

Sensors are **outbound-only**: each one runs a segment-local scan and pushes a
zstd-compressed envelope *out* to the console. Nothing ever connects *into* the
internal network. That makes "agents inside, server in the cloud" a natural fit —
the sensors phone home, exactly like any agent/EDR model. A segment with no
outbound HTTPS at all (a true air gap) cannot push: it writes a `.qpush` file with
`quirk sensor export-results`, and you load it on the console with
`quirk console import-results`.

```
   Internal segments                          Cloud VM (public IP + DNS)
 ┌────────────────────┐                  ┌───────────────────────────────┐
 │ sensor A (DMZ)     │── HTTPS :443 ───▶│  Caddy / nginx  (TLS, public) │
 │ sensor B (prod)    │── HTTPS :443 ───▶│        │  proxy to loopback    │
 │ sensor C (corp)    │   (per-sensor    │  quirk serve   127.0.0.1:8512 │
 └────────────────────┘    bearer token) │  SQLite + merge → 1 CBOM      │
                                          └───────────────────────────────┘
```

**Three layers protect the console:**

1. **Per-sensor bearer tokens** authenticate every `POST /api/sensor/push`
   (revocable, stored only as SHA-256 hashes).
2. **A TLS-terminating reverse proxy** is the only public listener; the console
   binds `127.0.0.1` and is never directly reachable.
3. **An operator API token** (`QUIRK_API_TOKEN`) gates the dashboard and operator
   API. The console **refuses to start** on a network-reachable interface if no
   operator token is configured (this variable, or `security.api_token` in the
   console's config file; see §6). On a loopback bind the guard does not apply, so
   behind the proxy a missing token leaves the dashboard open — confirm the
   startup summary says `operator auth : ENABLED`.

---

## 2. Prerequisites

- A small VM running **Debian 12 or Ubuntu 24.04, or newer** (the cloud-init file
  is written for Debian/Ubuntu). Older releases do not work with the commands
  below: Debian 11 ships Python 3.9 (below the 3.10 floor), and Ubuntu 22.04's
  pip 22.0.2 rejects the `--break-system-packages` flag that §3, §4.1 and §7 use.
- A DNS name (e.g. `quirk.example.com`) with an **A/AAAA record** pointing at the
  VM's public IP. Automatic TLS needs this resolvable before you start.
- Inbound firewall: **22 (SSH), 80 + 443 (web)**. Nothing else — and in particular
  **never** expose `8512`.
- Each sensor host: Python 3.10+ and `pip install "quirk-scanner[all]"`.

You can deploy two ways:

- **Automated** — paste [`deploy/cloud-init.yaml`](../deploy/cloud-init.yaml) into
  the provider's *user data* when creating the VM (§3).
- **Manual** — follow §4 step by step on an existing VM.

---

## 3. Automated path (cloud-init)

When creating the Linode/VM, paste the contents of
[`deploy/cloud-init.yaml`](../deploy/cloud-init.yaml) into the **user data /
metadata** field. On first boot it will:

- create a sandboxed `quirk` service account,
- install the console (`quirk-scanner[all]`) and Caddy,
- **generate a strong `QUIRK_API_TOKEN`** and write it to `/etc/quirk/console.env`,
- enable a `ufw` firewall (22/80/443 only; `8512` stays loopback),
- start `quirk-console` behind Caddy's automatic HTTPS.

After it boots, finish the three things cloud-init can't know:

```bash
# 1. Point DNS at the VM first (A/AAAA record), then:
sudo sed -i 's/quirk.example.com/YOUR.DOMAIN/' /etc/caddy/Caddyfile
sudo sed -i 's/admin@example.com/you@your.org/' /etc/caddy/Caddyfile
sudo sed -i 's#https://quirk.example.com#https://YOUR.DOMAIN#' /etc/quirk/console.env

# 2. Apply and read your generated operator token:
sudo systemctl reload caddy
sudo systemctl restart quirk-console
sudo grep QUIRK_API_TOKEN /etc/quirk/console.env     # save this — sensors don't need it; operators do
```

Skip to §5 to enroll sensors.

---

## 4. Manual path (step by step)

The `deploy/` files used below are in the repository, not in the PyPI package.
Clone it on the VM first (`git clone https://github.com/0xD1g5/QU.I.R.K` and `cd`
into it) so the `deploy/...` paths in §4.2–§4.4 resolve.

### 4.1 Service account + install

```bash
sudo addgroup --system quirk
sudo adduser  --system --ingroup quirk --no-create-home --shell /usr/sbin/nologin quirk
sudo mkdir -p /etc/quirk /var/lib/quirk
sudo chown -R quirk:quirk /var/lib/quirk
# The console's SQLite DB is created at quirk-output/quirk.db relative to the
# service's working directory, i.e. /var/lib/quirk/quirk-output/quirk.db.

# Console package (entry point: `quirk`)
sudo pip3 install --break-system-packages "quirk-scanner[all]"
```

### 4.2 Environment file (secrets)

```bash
sudo cp deploy/console.env.example /etc/quirk/console.env
# Generate a strong operator token:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
sudoedit /etc/quirk/console.env          # paste the token, set your https origin
sudo chown root:quirk /etc/quirk/console.env
sudo chmod 640 /etc/quirk/console.env    # secrets must not be world-readable
```

Key values (full list in [`deploy/console.env.example`](../deploy/console.env.example)):

| Variable | Set it to | Why |
|----------|-----------|-----|
| `QUIRK_API_TOKEN` | a 32-byte random string | Operator/dashboard auth. **Required** for a public bind unless `security.api_token` is set in the console's config file: with neither, the console refuses to start on a non-loopback address unless you pass `--insecure`. |
| `QUIRK_TRUST_PROXY` | `127.0.0.1` | Proxy is on the same host → console recovers the real sensor IP from `X-Forwarded-For`. `127.0.0.1` is also what the console uses when this is unset. |
| `QUIRK_HSTS` | `1` | TLS is terminated in front, so HSTS is safe. |
| `QUIRK_CORS_ORIGINS` | `https://your.domain` | Restrict the dashboard origin. |
| `QUIRK_SENSOR_IP_ALLOWLIST` | *(optional)* sensor egress IPs/CIDRs | Defense-in-depth on push (see §6). |

### 4.3 systemd unit

```bash
sudo cp deploy/systemd/quirk-console.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now quirk-console
sudo systemctl status quirk-console          # should be active (running)
```

The unit binds **loopback only** (`--host 127.0.0.1`) and runs sandboxed
(`NoNewPrivileges`, `ProtectSystem=strict`, private tmp, state under
`/var/lib/quirk`). The console never listens on a public interface itself.

### 4.4 Reverse proxy + TLS

**Recommended: Caddy (automatic HTTPS).** Caddy fetches and renews the Let's
Encrypt certificate for you — there's no certbot timer to fail.

```bash
# Install Caddy (Debian/Ubuntu) — see https://caddyserver.com/docs/install
sudo cp deploy/caddy/Caddyfile /etc/caddy/Caddyfile
sudoedit /etc/caddy/Caddyfile        # set your domain + ACME email
sudo systemctl reload caddy
```

That's it — visit `https://your.domain` and the dashboard loads over TLS.

<details>
<summary><strong>Alternative: nginx + certbot</strong></summary>

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp deploy/nginx/quirk-console.conf /etc/nginx/sites-available/quirk-console
sudo ln -s /etc/nginx/sites-available/quirk-console /etc/nginx/sites-enabled/
sudoedit /etc/nginx/sites-available/quirk-console     # set server_name to your domain
sudo certbot --nginx -d your.domain                   # provisions + wires up TLS
sudo nginx -t && sudo systemctl reload nginx
# certbot schedules renewal via cron or a systemd timer; if it is a timer, confirm:
systemctl list-timers | grep certbot
```
</details>

### 4.5 Firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose        # 8512 must NOT appear
```

If your provider has a cloud firewall (Linode Cloud Firewall, AWS security
groups), mirror the same allow-list there and restrict SSH to your admin IPs.

---

## 5. Enroll sensors and point them at the cloud console

On the **console host**, mint one per-sensor token per sensor:

```bash
# `console enroll` writes straight to the console database (it makes no network
# call and does not use the operator token), so it must target the same DB file
# the service uses:
sudo -u quirk env QUIRK_DB_PATH=/var/lib/quirk/quirk-output/quirk.db \
  quirk console enroll --segment dmz
# → stdout: Bearer token (copy now — shown once, never recoverable): <per-sensor-token>
# → stderr: sensor_id: <uuid>
```

On each **sensor host** (inside the customer network):

```bash
pip install "quirk-scanner[all]"
# --sensor-id must be the sensor_id that `console enroll` printed; without it
# the sensor invents its own UUID, which the console does not recognize.
quirk sensor enroll https://your.domain --segment dmz --sensor-id <uuid-from-console-enroll>
# Edit the sensor config (on Linux: ~/.config/quirk/sensor.yaml):
#   console_api_token: <per-sensor-token-from-console-enroll>
# (or pass --api-token <per-sensor-token> to `sensor enroll` to write it for you)
quirk sensor push --scan-config /etc/quirk/sensor-scan.yaml
```

The sensor connects **out** to `https://your.domain:443`; the proxy terminates TLS
and forwards to the loopback console. The push client enforces `verify=True`, so the
cloud console **must** present a valid certificate — which the reverse proxy does.

Then merge on the console as usual (against the console's database):

```bash
sudo -u quirk env QUIRK_DB_PATH=/var/lib/quirk/quirk-output/quirk.db quirk sensor merge
# one CBOM + one score across all sensors
```

---

## 6. Hardening checklist

Everything here is enforced or configurable in this release.

- [ ] **Operator token set.** Without `QUIRK_API_TOKEN` (or `security.api_token` in
      the console's config file), the console **refuses to start** on any non-loopback bind. (The `--insecure` flag overrides this only
      for intentionally token-less binds on trusted, firewalled segments — don't use
      it on a public VM.) The refusal does not cover the loopback bind this guide
      uses: with the token missing, the console still starts and serves the
      dashboard unauthenticated through the proxy, so check for
      `operator auth : ENABLED` in the startup summary.
- [ ] **Console binds loopback**, reverse proxy is the only public listener. The
      systemd unit already does this.
- [ ] **`QUIRK_TRUST_PROXY=127.0.0.1`** so the rate limiter, the IP allowlist and the
      request log see the real sensor IP, not the proxy's. This is also the default when the variable
      is unset; setting it just makes the intent explicit. Widen it only if the
      proxy is on a different host.
- [ ] **TLS via Caddy or nginx+certbot**, auto-renewing.
- [ ] **`QUIRK_HSTS=1`** once TLS is live.
- [ ] **`QUIRK_CORS_ORIGINS`** pinned to your real dashboard origin.
- [ ] **Firewall** allows only 22/80/443; `8512` never exposed.
- [ ] *(Optional)* **`QUIRK_SENSOR_IP_ALLOWLIST`** set to your sensors' egress IPs —
      pushes from any other source get `403` before token handling. Per-sensor
      tokens still apply regardless; this is layered defense, not the primary gate.
- [ ] **Security response headers** (`X-Content-Type-Options`, `X-Frame-Options`,
      `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`) are
      added automatically to every response except CORS preflight (`OPTIONS`)
      replies, which the CORS layer answers before the headers middleware runs.
- [ ] **`/etc/quirk/console.env` is `chmod 640`** — secrets not world-readable
      (`root:quirk` on the manual path; the cloud-init file leaves it `quirk:quirk`).

The console prints a short security summary at startup — confirm it on first boot:

```
QU.I.R.K. Dashboard security summary:
  bind            : 127.0.0.1:8512  (loopback only)
  operator auth   : ENABLED
  trusted proxies : 127.0.0.1
```

---

## 7. Operations

**Rotate the operator token:** edit `/etc/quirk/console.env`, then
`sudo systemctl restart quirk-console`.

**Revoke a sensor** (lost token, decommissioned host):

```bash
sudo -u quirk env QUIRK_DB_PATH=/var/lib/quirk/quirk-output/quirk.db \
  quirk console revoke-sensor <sensor_id>     # future pushes from it → 401
```

**Re-enroll a sensor** whose raw token was lost: revoke, then
`quirk console enroll --segment <label>` for a fresh token + sensor_id.

**Upgrade the console:**

```bash
sudo pip3 install --break-system-packages -U "quirk-scanner[all]"
sudo systemctl restart quirk-console
```

**Back up** `/var/lib/quirk/` (it holds the console's SQLite DB under
`quirk-output/`) on your normal schedule.

**Audit trail:** every push attempt that reaches the push handler — success or
rejection — writes an `IntegrationDelivery` row, including the `sensor_ip_not_allowed`
reason when the IP allowlist blocks a source. A request the rate limiter refuses
(more than 60 POSTs a minute from one address, HTTP 429) writes no row. The row
holds the time, status and error summary, not the sensor ID or source address.

---

## 8. What this deployment is *not*

- **Not multi-tenant.** One console per engagement (architecture
  [§9](architecture-distributed.md)). Run a separate console instance/VM per client
  rather than mixing engagements on one box.
- **Not a managed SaaS.** There's no central fleet-management plane; sensors are
  enrolled per console.
- **DNS-rebinding / TOCTOU** on the SSRF guard is documented as an accepted
  residual risk for the on-prem threat model (see the module note in
  `quirk/util/url_allowlist.py`). The cloud console's exposure is governed by the
  token + proxy + firewall layers above.
