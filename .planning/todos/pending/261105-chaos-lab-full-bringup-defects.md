---
type: todo
created: 2026-11-05
source: 2026-11-05 full chaos-lab bring-up (all 30 profiles in four waves, 115 containers) for the 5.28.1 GUI scan walkthrough
priority: medium
area: quantum-chaos-enterprise-lab/docker-compose.yml, quantum-chaos-enterprise-lab/lab.sh, labs/postgres-tls/Makefile, labs/{postgres-tls,redis-tls,kafka-tls}
status: pending
resolves_phase: null
owner: "999.119"
---

# Chaos lab: four defects that stop a full bring-up from coming up clean

Found bringing every profile up on macOS (Docker Desktop, 5 CPUs, 9.7 GiB). Each was worked around locally
that night; none is fixed in the repo. Per CLAUDE.md Chaos Lab Maintenance, a fix that changes profiles or
services must update `lab.sh`, the lab README, `docs/chaos-lab.md` and the `expected_results_*.md` oracle together.

1. **Cert files become empty directories.** `lab.sh` does not generate the `broker`, `postgres-tls`,
   `redis-tls` or `kafka-tls` certs (documented in `docs/chaos-lab.md` §2). If one of those profiles is ever
   `up`'d before `make -C labs/<p> certs`, Docker creates each missing bind-mount source as an **empty
   directory**, and it persists. On 2026-11-05 `labs/{postgres,redis,kafka}-tls/certs/*.{crt,key}` were all
   directories dated 2026-09-14. Symptoms: `postgres-tls` "could not load server certificate file ... no start
   line", `redis-tls` "Failed to load certificate ... no start line"; `make certs` then cannot write over them.
   `kafka-tls` started anyway, but after the fix its recreate failed ("not a directory: Are you trying to mount
   a directory onto a file") because the image's anonymous `/etc/kafka/secrets` volume kept the stray directory;
   it needed `docker compose rm -sfv kafka-tls`.
   - [ ] Generate these certs from `ensure_profile_certs` in `lab.sh` (as it does for email/grpc-tls), or have
         `lab.sh up` refuse with a clear message when a cert source path is a directory.
   - [ ] PR #68 (2026-11-05) gitignores the generated files but keeps the `.gitkeep`s; it does not prevent this.

2. **`labs/postgres-tls/Makefile` sets the key to 640** (`chmod 640 $(CERTS_DIR)/postgres-tls.key`, line 16).
   Postgres accepts 0640 only for a root-owned key; through Docker Desktop's file sharing it is not, and the
   server exits: "private key file ... has group or world access". `chmod 600` fixed it.
   (`labs/redis-tls/Makefile` already uses 600.)
   - [ ] Change the Makefile to 600; re-check on Linux Docker, where ownership maps differently.

3. **A failed first start leaves `postgres-tls` half-initialised, and the healthcheck hides it.** The image
   creates `POSTGRES_DB: chaos` only on the first init of an empty data volume. The cert failure in (1) killed
   that first start after `initdb` but before the database was created, and every later start reused the
   anonymous volume and skipped init. Result: no `chaos` database, and the healthcheck
   `pg_isready -U chaos` (no `-d`, so it targets database `chaos`) logged `FATAL: database "chaos" does not
   exist` every 10 s (398 times) while still reporting **healthy**, because `pg_isready` only checks that the
   server accepts connections. Fixed by `docker compose -p chaoslab --profile postgres-tls rm -sfv postgres-tls`
   and `up` (anonymous volume, lab data only).
   - [ ] Healthcheck: `pg_isready -U chaos -d chaos` plus a query that proves the database exists
         (for example `psql -U chaos -d chaos -c 'select 1'`).
   - [ ] Document the `rm -sfv` reset in the profile's section of `docs/chaos-lab.md`.

4. **`mtls-stepca-gateway` (profile `pki`) depends on a service `pki` never starts.** Its nginx config proxies
   to `whoami:80` (`docker-compose.yml:507`), and `whoami` is in profiles `identity` and `phaseA` only
   (`:473`). Started with `pki` alone, nginx exits 1: `host not found in upstream "whoami:80"`. It came up once
   `identity` was running and the container was started again.
   - [ ] Add `pki` to `whoami`'s profiles (or give the gateway its own upstream), and add
         `depends_on: [whoami]`.

Also seen, already tracked: the standalone `kerberos` profile cannot bind host :88 on macOS, and `mh-kdc`'s
healthcheck calls a missing `smbclient` (`261023-chaos-lab-kerberos-profile-healthcheck-and-port-88.md`).
`lsof` run without root does not show the macOS KDC on :88, so a non-root preflight check cannot see the
collision either.

## Feasibility & Effort

**CONFIRMED**: all four reproduced live on 2026-11-05, with the error text quoted above. **Effort S** for
(2) and (4), which are one line each plus the oracle and README checks. **Effort S-M** for (1) and (3),
which touch `lab.sh` cert generation and the postgres healthcheck and need a clean-volume re-run of each
affected profile. Owner 999.119 (CI and chaos-lab hygiene) already holds the other chaos-lab todos.
