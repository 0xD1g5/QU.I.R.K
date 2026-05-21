---
phase: 80-windows-adcs-scanner
plan: 01
subsystem: identity / chaos-lab
tags: [adcs, ldap, chaos-lab, foundation]
requires: [phase-77-ensure-columns-helper, phase-79-smime-profile]
provides: [adcs_scan_json-column, adcs-extras-group, adcs-chaos-lab-profile]
affects: [quirk/db.py, pyproject.toml, quantum-chaos-enterprise-lab/]
tech_added: []
key_files_created:
  - quantum-chaos-enterprise-lab/adcs/schema/msPKI-schema.ldif
  - quantum-chaos-enterprise-lab/adcs/ldif/00-base.ldif
  - quantum-chaos-enterprise-lab/adcs/ldif/10-ca.ldif
  - quantum-chaos-enterprise-lab/adcs/ldif/20-templates.ldif
  - quantum-chaos-enterprise-lab/adcs/certs/regen.sh
  - quantum-chaos-enterprise-lab/adcs/certs/ca-weak.der
  - quantum-chaos-enterprise-lab/adcs/Dockerfile
  - quantum-chaos-enterprise-lab/adcs/README.md
key_files_modified:
  - quirk/db.py
  - pyproject.toml
  - quantum-chaos-enterprise-lab/docker-compose.yml
  - quantum-chaos-enterprise-lab/expected_results_v4.md
  - quantum-chaos-enterprise-lab/README.md
decisions:
  - id: PLAN-80-01-D1
    summary: Switched to Bitnami-native `LDAP_CUSTOM_SCHEMA_DIR` env hook for schema loading; both originally planned branches (seed-time `ldapadd cn=config` + Dockerfile copy into `etc/schema/`) rejected at runtime.
  - id: PLAN-80-01-D2
    summary: msPKI overlay uses a private OID arc `1.3.6.1.4.1.99999.80.*` instead of Microsoft's real `1.2.840.113556.1.4.20XX` — the latter collides with the bundled msuser schema. Scanner keys off attribute NAMES, not OIDs.
metrics:
  duration_minutes: 30
  completed: 2026-05-16
requirements:
  - ADCS-03
  - ADCS-07
  - ADCS-08
---

# Phase 80 Plan 01: ADCS Foundation Summary

Adds the `adcs_scan_json` ORM column, declares the `[adcs]` extras group, and stands up a deterministic `adcs` chaos-lab profile (OpenLDAP seeded with an msPKI schema overlay, three certificate template fixtures, and a weak CA cert) — unblocking Plan 80-02 (scanner module) and Plan 80-04 (extras-install matrix).

## Tasks Executed

### Task 1: ORM column + `[adcs]` extras

- Appended `("adcs_scan_json", "TEXT")` to `_IDENTITY_COLUMNS` in `quirk/db.py:81`. Consolidated `_ensure_columns()` migration helper (Phase 77 D-21) picks it up automatically; no breaking schema change.
- Added `[adcs]` extras group in `pyproject.toml` listing **only `ldap3>=2.9.1`** — `impacket` is intentionally excluded so `quirk[adcs]` is safe to include in `[all]` without re-introducing the pyOpenSSL/cryptography downgrade chain (`tests/test_install_all_excludes_impacket.py` invariant preserved).
- Added `"quirk[adcs]"` to the `[all]` aggregate per ADCS-07.
- Verification: `python -m compileall quirk/` clean; tomllib self-check confirmed extras group well-formed and impacket-free.

### Task 2: Chaos-lab `adcs` profile

Created `quantum-chaos-enterprise-lab/adcs/` with:

- **`certs/ca-weak.der`** — RSA-1024, SHA-1 self-signed CA fixture (630 bytes, 100-year validity, `CN=QUIRK-Lab-CA`). Generated via `openssl req -x509 -newkey rsa:1024 -sha1 -outform DER`. Committed as DER blob so the lab works without OpenSSL at runtime.
- **`certs/regen.sh`** — developer-only regeneration script.
- **`schema/msPKI-schema.ldif`** — msPKI overlay declaring four detection-relevant attribute types (`msPKI-Certificate-Name-Flag`, `msPKI-Enrollment-Flag`, `msPKI-RA-Signature`, `msPKI-Certificate-Application-Policy`) and two structural object classes (`pKIEnrollmentService`, `pKICertificateTemplate`). Uses private OID arc `1.3.6.1.4.1.99999.80.*` (see Decision PLAN-80-01-D2).
- **`ldif/00-base.ldif`** — Configuration partition base entries (`cn=Configuration / Services / Public Key Services / Enrollment Services / Certificate Templates`) under base DN `dc=quirk,dc=lab`.
- **`ldif/10-ca.ldif`** — `pKIEnrollmentService` entry `CN=QuirkLabCA` with the weak CA DER inlined as `cACertificate;binary::` base64.
- **`ldif/20-templates.ldif`** — three deterministic fixtures: `BadTemplate-ESC1` (ENROLLEE_SUPPLIES_SUBJECT + client-auth EKU + no RA sig), `BadTemplate-ESC4` (`nTSecurityDescriptor` present, not parsed — emits COVERAGE-GAP per D-80-R8), `SafeTemplate` (benign defaults, email-protection EKU only).
- **`Dockerfile`** — D-80-R7 tertiary fallback (preserved per the plan's "ship both branches" contract; not currently active — see Decision PLAN-80-01-D1).
- **`README.md`** — profile documentation including all three schema-load branches tried.

Added `adcs-openldap` + `adcs-seed` compose services (profile `adcs`, port `38910`) in `docker-compose.yml`. Image: `bitnamilegacy/openldap:2.6.10-debian-12-r4` (parity with smime/ldaps profiles). Seed sidecar uses `ldapadd -c` and explicitly swallows exit 68 for idempotency (mirrors Phase 79 D-79-R2 contract).

`lab.sh` required NO edits — `_derive_all_profiles()` reads `docker-compose.yml` at runtime and `docker compose config --profiles` returns `adcs` automatically.

Live test results (Docker available):

- Run #1 (`PROFILE_ARGS="--profile adcs" ./lab.sh up`): `adcs-openldap` started, `adcs-seed` exit 0. `ldapsearch` against `localhost:38910` returned 3 templates + 1 CA entry with all expected msPKI-* attributes visible.
- Run #2 (immediate re-invocation): seed exit 0, no spurious errors. Compose noticed containers were already running and was a no-op for the running services. Idempotency contract satisfied.

### Task 3: Oracle + Profile Summary

- Appended `## Profile: adcs` section to `expected_results_v4.md` after `## Profile: smime`: bring-up command, findings table (1 HIGH weak-signing, 1 HIGH ESC1, 0 from SafeTemplate, 4 LOW COVERAGE-GAPs), scanner validation command, port note, privacy invariant, schema-load deviation note.
- Appended `| adcs |` row to the Profile Summary table in `quantum-chaos-enterprise-lab/README.md` immediately after the smime row.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Schema-load PRIMARY path rejected with "Insufficient access (50)"**

- **Found during:** Task 2 first live `./lab.sh up` cycle.
- **Issue:** `ldapadd -c -x -H ldap://adcs-openldap:389 -D 'cn=admin,...' -w admin -f /schema/msPKI-schema.ldif` rejects cn=config writes. The OpenLDAP rule is that schema modifications under `cn=schema,cn=config` require EXTERNAL SASL auth on the `ldapi:///` socket, not SIMPLE bind on the network listener (RESEARCH Pitfall 1 already flagged this risk in a different form).
- **Fix attempted #1:** Flipped to the D-80-R7 Dockerfile fallback (`build: ./adcs/` with `COPY schema/msPKI-schema.ldif /opt/bitnami/openldap/etc/schema/msPKI.ldif`). Container built and started, but msPKI was not loaded — Bitnami's entrypoint does NOT auto-include arbitrary files dropped into `/opt/bitnami/openldap/etc/schema/`; it only includes the well-known core/cosine/inetorgperson/nis chain plus `$LDAP_CUSTOM_SCHEMA_FILE`/`_DIR`.
- **Fix attempted #2 (active):** Bitnami-native `LDAP_CUSTOM_SCHEMA_DIR=/schemas` env hook + bind-mounted `adcs/schema/` directory. Bitnami runs `slapadd -F slapd.d -n 0 -l <file>` during initial offline setup (the only window cn=config accepts new schemas).
- **Fix attempted #3 (active, combined):** Initial env-hook attempt failed because msPKI tried to redeclare attributes (`cACertificate`, `nTSecurityDescriptor`, etc.) that were not in the loaded schema set but the OIDs `1.2.840.113556.1.4.20XX` collided with system-internal definitions. Added `msuser` to `LDAP_EXTRA_SCHEMAS` (which provides AD-compatible attributes), removed our duplicate declarations of those attrs, and switched to a private OID arc `1.3.6.1.4.1.99999.80.*` for the four msPKI-* attribute types and two structural classes we still own. Names match Microsoft's real schema verbatim — the scanner keys on names.
- **Files modified:** `quantum-chaos-enterprise-lab/docker-compose.yml` (env vars, no `ldapadd` schema add line in seed), `quantum-chaos-enterprise-lab/adcs/schema/msPKI-schema.ldif` (private OID arc, removed duplicate attrs), `quantum-chaos-enterprise-lab/adcs/README.md` (documented all three branches), `quantum-chaos-enterprise-lab/adcs/Dockerfile` (re-classified as tertiary fallback).
- **Verification:** Live `ldapsearch` confirmed `{5}mspki` is loaded into `cn=schema,cn=config` and all 3 templates + 1 CA entry are queryable. Two consecutive `./lab.sh up --profile adcs` runs both exit 0.

This deviation is consistent with the plan's spirit: D-80-R7 explicitly anticipated runtime rejection and committed both branches so the executor could switch without re-planning. Both originally planned branches turned out to be inadequate against the specific Bitnami image; the env-hook is the cleanest path within Bitnami's design. All three branch artifacts remain on disk per the "ship both branches" contract — the Dockerfile and the original LDIF-via-ldapadd path are documented in `adcs/README.md` as fallbacks for future regressions.

**2. [Rule 1 - Bug] `cACertificate` / `nTSecurityDescriptor` matching rules invalid**

- **Found during:** Slapadd trial run of the schema overlay.
- **Issue:** First draft declared `EQUALITY octetStringMatch` on `cACertificate` (syntax 1.3.6.1.4.1.1466.115.121.1.8 = Certificate) — slapadd rejects with "AttributeType inappropriate matching rule". OpenLDAP accepts no EQUALITY for the Certificate syntax (or requires `certificateExactMatch` which is conditionally compiled).
- **Fix:** Removed the inappropriate EQUALITY clauses. (Subsequently moot — both attributes were dropped entirely once we leaned on msuser's existing definitions; see Deviation #1.)
- **Files modified:** `quantum-chaos-enterprise-lab/adcs/schema/msPKI-schema.ldif`

No architectural deviations (no Rule 4 events).

## Known Stubs

None. Lab fixtures are runtime-functional; scanner module + tests land in subsequent plans 80-02..80-04.

## Self-Check

Verified before writing this Summary:

- **Files created (FOUND):**
  - `quantum-chaos-enterprise-lab/adcs/schema/msPKI-schema.ldif` (3314 bytes)
  - `quantum-chaos-enterprise-lab/adcs/ldif/00-base.ldif` (933 bytes)
  - `quantum-chaos-enterprise-lab/adcs/ldif/10-ca.ldif` (1418 bytes)
  - `quantum-chaos-enterprise-lab/adcs/ldif/20-templates.ldif` (1603 bytes)
  - `quantum-chaos-enterprise-lab/adcs/certs/regen.sh` (executable)
  - `quantum-chaos-enterprise-lab/adcs/certs/ca-weak.der` (630 bytes)
  - `quantum-chaos-enterprise-lab/adcs/Dockerfile` (1464 bytes)
  - `quantum-chaos-enterprise-lab/adcs/README.md` (5102 bytes)
- **Verification commands:**
  - `python -m compileall quirk/` — clean
  - `python -c "import tomllib; ..."` — extras self-check passes
  - `docker compose --profile adcs config` — parses
  - `docker compose config --profiles | grep adcs` — returns `adcs`
  - `grep -c '^## Profile: adcs' expected_results_v4.md` — 1
  - `grep -c '^| adcs |' README.md` — 1
  - Live ldapsearch returned 3 templates + 1 CA
  - Two consecutive `./lab.sh up --profile adcs` runs both exit 0

## Self-Check: PASSED

**Commit SHA:** `9ed0cd0`
