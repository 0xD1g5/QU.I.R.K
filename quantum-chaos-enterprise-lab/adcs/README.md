# AD CS Chaos Lab Profile (Phase 80)

OpenLDAP container seeded with a deliberately misconfigured Active Directory
Certificate Services *Configuration* partition. The QU.I.R.K. ADCS scanner
(Plan 80-02, `quirk/scanner/adcs_scanner.py`) enumerates this lab via
**read-only LDAP** and emits findings for weak CA signing algorithms, ESC1-
category template misconfigurations, and ESC4 coverage gaps.

> **Privacy invariant (ADCS-09).** This profile is observed by the scanner via
> read-only LDAP enumeration. No certificate enrollment, no CSR generation, no
> template creation, no LDAP modify/add/delete operations are performed under
> any code path. AST gate `tests/test_adcs_ast_gate.py` enforces this at CI.

## Bring-up

```bash
PROFILE_ARGS="--profile adcs" ./lab.sh up
```

- Exposes plain LDAP on host port **38910** (no LDAPS — deferred per Phase 80
  CONTEXT; matches the smime profile policy).
- Two services: `adcs-openldap` (Bitnami openldap 2.6.10) and the one-shot
  `adcs-seed` sidecar that loads the msPKI schema + base/CA/template LDIFs
  via `ldapadd -c` (idempotent — re-running the up command must not error).

## Fixtures

| Object | Class | Key attribute | Expected finding | Severity |
|---|---|---|---|---|
| `CN=QuirkLabCA, CN=Enrollment Services, ...` | `pKIEnrollmentService` | `cACertificate;binary::` RSA-1024 SHA-1 | Weak CA signing algorithm | HIGH |
| `CN=BadTemplate-ESC1, CN=Certificate Templates, ...` | `pKICertificateTemplate` | `msPKI-Certificate-Name-Flag: 1` + client-auth EKU + `msPKI-RA-Signature: 0` | ESC1 misconfig | HIGH |
| `CN=BadTemplate-ESC4, CN=Certificate Templates, ...` | `pKICertificateTemplate` | `nTSecurityDescriptor` present (not parsed) | ADCS-COVERAGE-GAP ESC4 | LOW |
| `CN=SafeTemplate, CN=Certificate Templates, ...` | `pKICertificateTemplate` | benign defaults, email-protection EKU only | (none — SAFE) | — |

The CA signing cert fixture (`certs/ca-weak.der`) is a deterministic
RSA-1024 / SHA-1 self-signed cert with a 100-year validity window so the
fixture is non-expired. Regenerate via `certs/regen.sh` (developer tool only,
not runtime).

## Schema loading: branches tried during Plan 80-01 (D-80-R7)

Plan 80-01 documented two schema-load branches (the seed-ldapadd PRIMARY and
the Dockerfile FALLBACK) and instructed the executor to flip without
re-planning if PRIMARY was rejected at runtime. In practice BOTH initial
branches were rejected (deviation Rule 1, 2026-05-16), and the active path
uses Bitnami's NATIVE `LDAP_CUSTOM_SCHEMA_DIR` env hook instead. All three
branches' artifacts are preserved per the "ship both branches" contract:

### Active path: Bitnami native schema dir

`docker-compose.yml` sets:

```yaml
environment:
  LDAP_EXTRA_SCHEMAS: "cosine,inetorgperson,nis,msuser"
  LDAP_CUSTOM_SCHEMA_DIR: "/schemas"
volumes:
  - ./adcs/schema:/schemas:ro
```

Bitnami's entrypoint runs `slapadd -F slapd.d -n 0 -l /schemas/msPKI-schema.ldif`
during initial setup (offline, before slapd starts listening), which is the
only window where new schemas can be added to cn=config. `msuser` is added
to `LDAP_EXTRA_SCHEMAS` so its AD-compatible attribute types (`cACertificate`,
`nTSecurityDescriptor`, `dNSHostName`, `pKIExtendedKeyUsage`, `pKIKeyUsage`)
load BEFORE the msPKI overlay declares the object classes that use them.

The schema overlay uses a private OID arc (`1.3.6.1.4.1.99999.80.*`) rather
than Microsoft's real `1.2.840.113556.1.4.20XX` because the latter is already
claimed by the msuser schema. The scanner keys off attribute NAMES, not OIDs,
so the private arc is functionally equivalent for chaos-lab purposes.

### Rejected: PRIMARY path (`ldapadd` from the seed sidecar)

`ldapadd -Y EXTERNAL -H ldap://adcs-openldap:389 -f /schema/msPKI-schema.ldif`
returns `Insufficient access (50)` — cn=config writes require EXTERNAL on
the container's `ldapi:///` socket, which is not exposed across containers.

### Rejected: D-80-R7 Dockerfile FALLBACK

`COPY schema/msPKI-schema.ldif /opt/bitnami/openldap/etc/schema/msPKI.ldif`
does not auto-load: Bitnami's entrypoint only includes the well-known
core/cosine/inetorgperson/nis chain plus `$LDAP_CUSTOM_SCHEMA_FILE`/`_DIR`.
The Dockerfile is preserved as a tertiary fallback for future Bitnami image
releases that may break the env-hook contract.

## Files

- `schema/msPKI-schema.ldif`  — msPKI-* attribute + objectClass definitions.
- `ldif/00-base.ldif`  — Configuration partition base OUs/CNs.
- `ldif/10-ca.ldif`  — `pKIEnrollmentService` carrying the weak CA cert.
- `ldif/20-templates.ldif` — three deterministic templates (ESC1, ESC4, Safe).
- `certs/ca-weak.der`  — RSA-1024 SHA-1 CA fixture (DER blob, committed).
- `certs/regen.sh`  — developer-only regeneration script.
- `Dockerfile`  — D-80-R7 fallback image that bakes the schema in.

## Cross-references

- Compose blocks: `adcs-openldap`, `adcs-seed` (profile `adcs`) in
  `../docker-compose.yml`.
- Oracle: `## Profile: adcs` in `../expected_results_v4.md`.
- Profile Summary row: `../README.md`.
- ORM column: `quirk/db.py::_IDENTITY_COLUMNS` (`adcs_scan_json`).
