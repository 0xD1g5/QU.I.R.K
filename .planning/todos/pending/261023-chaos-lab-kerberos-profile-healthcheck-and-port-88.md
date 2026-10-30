---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02 live KDC measurement)
priority: medium
area: quantum-chaos-enterprise-lab/docker-compose.yml (samba-dc, mh-kdc), quantum-chaos-enterprise-lab/lab.sh
status: pending
resolves_phase: null
owner: "999.119"
---

# Chaos-lab Kerberos profile: the samba-dc container is never healthy, and host port 88 collides on macOS

Found live by plan 230-02 on 2026-10-23 (Docker 29.8.2, Compose v5.6.0). Neither is fixed in Phase 230 (the lab
profile, ports and services were not changed; the docs record both as open defects).

1. **Healthcheck uses a tool the image lacks.** The `samba-dc` healthcheck is
   `smbclient -L localhost -N 2>/dev/null | grep -q QUIRK || exit 1`
   (`quantum-chaos-enterprise-lab/docker-compose.yml:948`; the same command is repeated for `mh-kdc` at `:2088`).
   `smbclient` is not installed in the image, so the container reported **unhealthy** although provisioning completed
   ("Provisioning complete", `samba-tool user list` showed Guest, Administrator, krbtgt) and the KDC answered.
   Any `depends_on: condition: service_healthy` on it would never be satisfied.
2. **Host port 88 collides with the macOS KDC.** The published port `"88:88"` (`:945`) fails on a macOS host
   (`listen tcp 0.0.0.0:88: bind: address already in use`; the macOS KDC holds `*.88`), so
   `PROFILE_ARGS='--profile kerberos' ./lab.sh up` fails on the default path. The 230-02 measurement used a scratch
   override mapping `127.0.0.1:18088:88` and `127.0.0.1:13389:389`.
3. (Related, recorded for the owner) The Samba KDC closes about one in three TCP connections with no reply;
   see `261023-detect-kerberos-udp-failure-reads-as-no-preauth`.

Per CLAUDE.md Chaos Lab Maintenance, any fix must update `lab.sh`, the lab README, `docs/chaos-lab.md` and
`expected_results_v4.md` together.

- [ ] Replace the healthcheck with a probe the image has (for example `samba-tool domain info 127.0.0.1` or a TCP check on 88).
- [ ] Make the host port for the Kerberos profile overridable (for example `${KDC_HOST_PORT:-88}:88`) and document the macOS workaround in `lab.sh` and the README.
- [ ] Re-run the Kerberos profile end to end and update the oracle.

## Feasibility & Effort

- **CONFIRMED** live in 230-02 (verbatim error and `smbclient: not found`); lines above.
- **LIKELY** effort **S**.
- **UNKNOWN**: which command in the image is a reliable readiness signal (`samba-tool` presence was observed, a healthy-state run was not).
- **Spike**: no. Owner 999.119 ("CI and chaos-lab hygiene", the row that already holds the chaos-lab todos) is OPEN (read 2026-10-23).
