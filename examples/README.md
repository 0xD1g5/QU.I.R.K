# QU.I.R.K. Sample CBOMs

This directory holds four canonical [CycloneDX 1.6](https://cyclonedx.org/specification/overview/)
Cryptography Bill of Materials (CBOM) outputs produced by QU.I.R.K. against
representative [chaos lab](../quantum-chaos-enterprise-lab/README.md) profiles.

These fixtures are **the v4.10 "what does QU.I.R.K. output actually look
like?" reference** — point your colleagues at them when you need to show the
shape of a CBOM without standing up a scan. They are checked in as
deterministic, diff-friendly artifacts. They are NOT live network captures,
NOT real customer data, and NOT a substitute for running the scanner against
your own infrastructure.

## Fixtures

| File | Source profile(s) | What it demonstrates | Size |
| --- | --- | --- | --- |
| [`cbom/tls-only.cbom.json`](cbom/tls-only.cbom.json) | `phaseA` | Weak transport crypto: legacy ciphersuites, sub-2048 RSA keys, expired / missing-intermediate certificates, plus a baseline of modern TLS for contrast. | ~10 KB |
| [`cbom/identity.cbom.json`](cbom/identity.cbom.json) | `identity` + `pki` | Identity-plane crypto: S/MIME-bearing certificates discovered over LDAP, AD CS / Step CA template enumeration, plus the in-tree PKI hierarchy. | ~8.5 KB |
| [`cbom/data-at-rest.cbom.json`](cbom/data-at-rest.cbom.json) | `database` | Data-at-rest disposition for a PostgreSQL target — narrow fixture showing how the scanner records "unable to introspect at-rest crypto from outside the DB" as an advisory finding. | ~1.2 KB |
| [`cbom/data-in-motion.cbom.json`](cbom/data-in-motion.cbom.json) | `phaseA` + `email` + `broker` | Data-in-motion crypto: TLS (HTTPS), SMTP STARTTLS, IMAP/POP3 STARTTLS, AMQP-over-TLS, and Kafka-TLS — the densest fixture, covering most of the motion classifier. | ~26 KB |

All four files are pretty-printed CycloneDX 1.6 JSON with a trailing newline,
suitable for line-by-line diffing.

## Regeneration

To rebuild the four fixtures from source (after a synthesizer change in
`tests/_cbom_profiles.py`, a builder change in `quirk/cbom/builder.py`, or a
CycloneDX library bump):

```bash
# 1. From the repo root, with the project venv active (pip install -e .)
./scripts/generate_cbom_fixtures.sh

# 2. Verify the four files parse and contain at least one crypto component
for f in examples/cbom/*.cbom.json; do
  jq empty "$f" || exit 1
  jq -e '.components[]? | select(.type=="cryptographic-asset")' "$f" >/dev/null
done

# 3. (Optional) Confirm determinism — rerun the generator and diff
md5 -q examples/cbom/*.cbom.json    # macOS
# or
md5sum  examples/cbom/*.cbom.json    # Linux
```

The generator script is `scripts/generate_cbom_fixtures.sh`. It does NOT need
docker-compose running — it invokes `build_cbom()` in-process against the
per-profile `CryptoEndpoint` synthesizers in `tests/_cbom_profiles.py`. Those
synthesizers are kept drift-locked with the live `docker-compose.yml` profile
set by `tests/test_cbom_schema_validation.py`, so the fixtures here always
reflect the same crypto findings a real scan against the chaos lab would
produce.

If you would rather drive the full scanner end-to-end against the actual
chaos lab containers, follow [`docs/getting-started.md`](../docs/getting-started.md)
for the broader scanner setup, then bring up the relevant profile via
`./lab.sh up --profile <name>` from `quantum-chaos-enterprise-lab/`. The
fixtures here will then match (modulo timestamps / UUIDs — see below).

## Determinism

QU.I.R.K.'s scan path emits three fields that change every run:

- `metadata.timestamp` — wall-clock `datetime.now()` at scan time
- `serialNumber` — fresh `urn:uuid` per scan
- one auto-generated `BomRef.<rand>.<rand>` on `metadata.component`

The regeneration script post-processes the raw `build_cbom()` output with
`jq` to normalize all three to fixed placeholder values:

- `metadata.timestamp` → `"2026-01-01T00:00:00+00:00"`
- `serialNumber` → `"urn:uuid:00000000-0000-0000-0000-000000000000"`
- the metadata-component BomRef → `"BomRef.fixture.metadata-component"`

All other fields (algorithm components, certificate / protocol assets,
dependency graph, properties) are content-addressed by `bom-ref` strings
that hash directly from the input data and are therefore stable run-over-run.

Why check fixtures in?

1. **Diff-friendly review.** Schema and classifier changes show up as PR
   diffs against these files — no need to read into a binary database.
2. **Offline evaluation.** A prospective adopter can `cat
   examples/cbom/tls-only.cbom.json` and see the output shape without
   installing the project or standing up Docker.
3. **Integration-test ballast.** Downstream tooling (CBOM diff viewers,
   compliance mappers) can pin against these fixtures.

These fixtures are NOT a substitute for running the scanner against your own
infrastructure. They are illustrative — not a security claim about your
environment.

## Cross-references

- [CBOM Guide](../docs/cbom-guide.md) — full CycloneDX schema reference and
  how QU.I.R.K. populates each field
- [Getting Started](../docs/getting-started.md) — install + first scan
- [Chaos Lab Operator Guide](../docs/chaos-lab.md) — bringing up the
  source profiles for end-to-end scans
