---
phase: 46-tls-finding-gaps
plan: 03
subsystem: chaos-lab
tags: [chaos-lab, docker, certs, nginx, tls-cert-defects]
requires: [46-01]
provides:
  - tls-cert-defects-profile
  - untrusted-ca-cert-fixture
  - cert-defect-nginx-confs
affects:
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/scripts/gen_phaseA_certs.sh
  - quantum-chaos-enterprise-lab/expected_results_v4.md
  - quantum-chaos-enterprise-lab/README.md
tech-stack:
  added: []
  patterns:
    - issue_leaf helper extended with untrusted-ca scenario (RSA-2048, signed by scenario-root)
    - tls-cert-defects compose profile follows existing tls-rsa1024 / tls-missing-intermediate phaseA pattern
    - OPENSSL_CONF + openssl-legacy.cnf bind-mount required for RSA-1024 nginx (Pitfall 3)
    - lab.sh _derive_all_profiles auto-discovers new profile at runtime — no manual ALL_PROFILES edit
key-files:
  created:
    - quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.crt
    - quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.key
    - quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.csr
    - quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.ext
    - quantum-chaos-enterprise-lab/nginx/cert-defects/expired/nginx.conf
    - quantum-chaos-enterprise-lab/nginx/cert-defects/selfsigned/nginx.conf
    - quantum-chaos-enterprise-lab/nginx/cert-defects/untrusted-ca/nginx.conf
    - quantum-chaos-enterprise-lab/nginx/cert-defects/rsa1024/nginx.conf
  modified:
    - quantum-chaos-enterprise-lab/scripts/gen_phaseA_certs.sh
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - "Ports 13444-13447 (NOT 13443-13446 — 13443 already taken by phaseA tls-missing-intermediate)"
  - "Untrusted-CA leaf is RSA-2048 (strong key) — isolates the untrusted-CA finding from the RSA-1024 finding (no double-fire on port 13446)"
  - "tls-cert-rsa1024 includes OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf + legacy.cnf volume mount per Pitfall 3 (nginx 3.x rejects RSA-1024 without legacy provider)"
  - "lab.sh ALL_PROFILES NOT touched — _derive_all_profiles() reads compose at runtime (verified via ./lab.sh profiles output)"
  - "Existing tls-expired (port 9443) and tls-selfsigned (port 10443) profiles unchanged for back-compat (D-03)"
metrics:
  duration_minutes: ~10
  completed_date: 2026-05-03
---

# Phase 46 Plan 03: TLS Cert-Defects Chaos Lab Profile — Summary

**One-liner:** Added `tls-cert-defects` Docker Compose profile with 4 nginx services (ports 13444-13447) covering all four cert-defect finding classes (expired, self-signed, untrusted-CA, RSA-1024); generated a new untrusted-CA leaf cert (RSA-2048, signed by off-trust-store `scenario-root` CA); updated chaos lab oracle docs and README per the CLAUDE.md chaos-lab maintenance rule. `lab.sh` required no edits — `_derive_all_profiles()` auto-discovers the new profile at runtime.

## What Was Built

### Cert fixture: untrusted-CA leaf

```
$ openssl x509 -in certs/scenarios/untrusted-ca/leaf.crt -noout -subject -issuer
subject=C=US, ST=NY, L=Lab, O=ChaosLab, OU=Server, CN=untrusted-ca.chaos.local
issuer= C=US, ST=NY, L=Lab, O=ChaosLab, OU=CA, CN=scenario-root-CA

$ openssl x509 -in certs/scenarios/untrusted-ca/leaf.crt -noout -text | grep "Public-Key"
                Public-Key: (2048 bit)
```

- `subject != issuer` ✅ (correct for D-04 untrusted-CA branch)
- `scenario-root-CA` is NOT in the host trust store (verified: `security find-certificate -c "scenario-root-CA" /Library/Keychains/System.keychain` returns "could not be found")
- RSA-2048 key (strong) — isolates the untrusted-CA finding from the RSA-1024 finding when scanned at port 13446

Generation: `quantum-chaos-enterprise-lab/scripts/gen_phaseA_certs.sh` extended with one `issue_leaf` call (idempotent — re-running the script regenerates all scenario certs).

### Docker Compose service block

`quantum-chaos-enterprise-lab/docker-compose.yml` — appended a new "PHASE 46 — TLS CERT DEFECTS PROFILE" block before `volumes:` (4 services, 47 new lines):

| Service | Profile | Host port | Cert mount | Notes |
|---------|---------|-----------|------------|-------|
| tls-cert-expired      | tls-cert-defects | 13444 | `./certs:/etc/nginx/certs:ro` | reuses existing `expired.{crt,key}` |
| tls-cert-selfsigned   | tls-cert-defects | 13445 | `./certs:/etc/nginx/certs:ro` | reuses existing `selfsigned.{crt,key}` |
| tls-cert-untrusted-ca | tls-cert-defects | 13446 | `./certs/scenarios:/etc/nginx/scenarios:ro` | new `untrusted-ca/leaf.{crt,key}` |
| tls-cert-rsa1024      | tls-cert-defects | 13447 | `./certs/scenarios:/etc/nginx/scenarios:ro` + `./nginx/openssl-legacy.cnf` | reuses `scenarios/rsa1024/leaf.{crt,key}`; `OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf` env var |

**Validation:** `docker compose --profile tls-cert-defects config` exits 0; `compose --profile tls-cert-defects config --services` lists exactly the 4 services.

### nginx confs

4 minimal nginx confs at `nginx/cert-defects/{expired,selfsigned,untrusted-ca,rsa1024}/nginx.conf`, following the existing `nginx/selfsigned/nginx.conf` pattern (`listen 443 ssl;`, TLSv1.2/1.3, `location / { return 200 ... }`).

### expected_results_v4.md

Appended `## Profile: tls-cert-defects` H2 section (last in the file, after `## Profile: broker`). Lists the 4 endpoints with their cert source, expected scanner finding title, severity (CRITICAL / HIGH / MEDIUM / HIGH), and TLS-FIND-NN requirement ID. Includes the live-fire smoke command and notes covering D-04 mutual exclusivity, D-02 (one finding per class, no rollup), Pitfall 3 (legacy.cnf), and the lab.sh auto-discovery pattern.

### README.md

Added one row to the Profile Summary table (immediately after the `broker` row): `tls-cert-defects` with its 4 services, ports 13444-13447, expected-findings link to the new oracle anchor, and a note tagging it `v4.6 (Phase 46)`.

### lab.sh — NO EDIT NEEDED

`./lab.sh profiles` (which invokes `_derive_all_profiles()`) now lists `tls-cert-defects` from runtime parsing of docker-compose.yml — verified during this plan. Confirms the Phase 40 D-14 design.

## Verification Run

Performed in working directory `quantum-chaos-enterprise-lab/`:

| Check | Result |
|-------|--------|
| `bash scripts/gen_phaseA_certs.sh` | Generates all scenario certs including untrusted-ca/leaf.{crt,key} cleanly. |
| `openssl x509 -in certs/scenarios/untrusted-ca/leaf.crt -noout -subject -issuer` | subject=CN=untrusted-ca.chaos.local; issuer=CN=scenario-root-CA (different from subject) |
| `openssl x509` Public-Key inspection | RSA-2048 ✅ (strong, isolates untrusted-CA finding from RSA-1024) |
| `docker compose --profile tls-cert-defects config` | Exit 0 (valid YAML, valid profile) |
| `grep -c 'tls-cert-defects' docker-compose.yml` | 5 (≥ 4 required: 1 comment block ref + 4 profile tags) |
| `grep -c 'tls-cert-defects' expected_results_v4.md` | 2 (section heading + smoke-command line) |
| `grep -c 'tls-cert-defects' README.md` | 1 (profile-table row) |
| `grep -c '13447:443' docker-compose.yml` | 1 (RSA-1024 service only) |
| `./lab.sh profiles \| grep tls-cert-defects` | Outputs `tls-cert-defects` (auto-discovered) |
| `./lab.sh status` | Lists running containers cleanly (no broken references) |
| Existing `tls-expired` / `tls-selfsigned` services in compose | Byte-identical to pre-change (back-compat per D-03) |
| Host trust-store check for scenario-root-CA | Not present (untrusted-CA finding will fire correctly) |

`docker compose up` was deliberately NOT run — left to the user for the Task 3 human-verify checkpoint per orchestrator instructions.

## Commits

- `9562e30` — `feat(46-03): generate untrusted-ca leaf cert + 4 cert-defect nginx confs` (Task 1)
- `386e1bd` — `feat(46-03): add tls-cert-defects compose profile + oracle/README updates` (Task 2)

## Deviations from Plan

None — plan executed exactly as written. All four cert-defect services on the planned ports (13444-13447), Pitfall 3 honored for RSA-1024, untrusted-CA cert generated with the exact `issue_leaf` invocation specified by the plan.

## Outstanding — Task 3 (human-verify checkpoint)

Per orchestrator instructions, I did NOT bring the chaos lab up. Task 3 is a live-fire smoke check requiring the operator to:

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up
./lab.sh status            # expect 4 services Up on 13444-13447
for p in 13444 13445 13446 13447; do
  echo "--- port $p ---"
  curl -k --max-time 5 https://localhost:$p/
done
./lab.sh down              # expect clean teardown, no `tls-cert-*` containers remaining
```

Expected curl output: `OK - tls-cert-expired`, `OK - tls-cert-selfsigned`, `OK - tls-cert-untrusted-ca`, `OK - tls-cert-rsa1024` from each respective port. Any failure (container not reaching `Up`, curl not returning 200) is a regression to investigate before Plan 46-04.

## Self-Check: PASSED

Files verified to exist:
- ✅ quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.crt
- ✅ quantum-chaos-enterprise-lab/certs/scenarios/untrusted-ca/leaf.key
- ✅ quantum-chaos-enterprise-lab/nginx/cert-defects/{expired,selfsigned,untrusted-ca,rsa1024}/nginx.conf

Commits verified to exist:
- ✅ 9562e30 in `git log`
- ✅ 386e1bd in `git log`
