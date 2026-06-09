# `deploy/` — cloud console deployment artifacts

Ready-to-use files for running the QU.I.R.K. **console** on a cloud VM (Linode,
EC2, GCP, …) with internal-network **sensors** pushing findings in over HTTPS.

The full step-by-step walkthrough lives in
[`docs/deployment-cloud-console.md`](../docs/deployment-cloud-console.md). This
directory just holds the files that guide references.

| File | Purpose |
|------|---------|
| `cloud-init.yaml` | One-shot provisioning for a fresh Debian/Ubuntu VM: installs the console + Caddy, generates an operator token, locks the firewall. Paste into the provider's *user data* field. |
| `console.env.example` | Template for `/etc/quirk/console.env` — operator token, proxy trust, HSTS, CORS, optional sensor IP allowlist. |
| `systemd/quirk-console.service` | systemd unit running the console as a sandboxed, loopback-only service. |
| `caddy/Caddyfile` | **Recommended** reverse proxy — automatic Let's Encrypt HTTPS, ~3 lines. |
| `nginx/quirk-console.conf` | Enterprise alternative — nginx + certbot TLS termination. |

## Topology

```
   Internal segments                         Cloud VM (e.g. Linode)
 ┌───────────────────┐                  ┌──────────────────────────────┐
 │ sensor (outbound) │── HTTPS :443 ───▶│ Caddy / nginx  (TLS, public) │
 └───────────────────┘                  │      │ proxy → 127.0.0.1:8512 │
                                         │ quirk console (loopback only)│
                                         └──────────────────────────────┘
```

Sensors only ever connect **outbound** to the console — no inbound port is
opened on the internal network. The console's `:8512` is never exposed; the
reverse proxy on `:443` is the only public listener.
