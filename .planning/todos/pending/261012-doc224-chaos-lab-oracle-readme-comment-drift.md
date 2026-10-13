# Chaos-lab oracle, README and compose-comment drift found by the docs/chaos-lab.md audit

**Filed:** 2026-10-12 (Phase 224 plan 06). Plan 06 may not edit `quantum-chaos-enterprise-lab/**`, so these
lab-side defects are recorded here; `docs/chaos-lab.md` was corrected to the checked truth in each case.
**Priority:** P3 — lab files that disagree with the code and with each other
**Status:** open

## Drift found (each verified against code or compose at the time of the audit)

1. `expected_results_hwcompat.md` records `confidence=unknown` for the SSH-banner path and
   `confidence=high` for the SNMP path. The code returns `low` (`hardware_scanner.py:411-412`) and `medium`
   (`_apply_entry` on the lab sysDescr, run offline). The SNMP vendor comes from sysDescr text; sysObjectID
   is stored but not used for the match.
2. `expected_results_v4.md` uses finding wording the evaluator does not emit: "Kafka plaintext listener
   detected" / "AMQP plaintext listener detected" / "Redis plaintext listener (no authentication)" (code:
   "Plaintext Kafka listener detected", "Plaintext AMQP listener detected", "Plaintext Redis listener (no
   auth)") and the fuzz-target tags `HSTS_MISSING`/`HTTP_ONLY_CRED`/`ALG_CONFUSION`
   (code: `hsts_missing`, `http_creds`, `alg_confusion`). It also lists a `TLS_DOWNGRADE` finding for a
   plain-HTTP service in the fuzz-target table (its own note says the probe fires only if TLS is later
   configured; the TLS-handshake probe cannot produce it today), and postgres-tls findings
   ("Weak cipher suite on database TLS endpoint", protocol `POSTGRES-TLS`) that no scanner code emits.
3. `quantum-chaos-enterprise-lab/README.md` and the oracle's multihost section say "33 `mh-*` services" /
   "31 targets"; compose defines 42 `mh-*` services and `multihost-scan-config.yaml` lists 39 `/32` targets.
   The oracle also lists 11 `ports_tls` where the config carries 14.
4. Dovecot: `docker-compose.yml` sets `OPENSSL_CONF` to a TLS 1.2 cap for `dovecot-email`, while
   `labs/email/expected_results.md` records TLS 1.3 on the Dovecot ports. They cannot both describe the
   current image; a live re-capture decides which is stale.
5. Compose comments tell the reader to scan with `python run_scan.py --target 127.0.0.1 ...`
   (`docker-compose.yml` hwcompat-snmp and otics blocks); `--target`, `--ports` and `--snmp-community` are not
   CLI flags (`quirk: error: unrecognized arguments`). `multihost-scan-config.yaml` carries a header comment
   with `quirk serve --db-path ...`, which also exits 2.
6. A compose comment says the `storage` profile "already serves vault/localstack-kms/pgcrypto"; that
   profile was removed in `a690e625`.

## Fix

Update each lab file to the code's behaviour (or, for item 4, re-capture live first). CLAUDE.md requires the
README and the `expected_results_*.md` oracle to move in the same change as any profile edit.

## Feasibility & Effort

- Feasibility: CONFIRMED for items 1, 2, 3, 5, 6 (each reproduced from source or an offline run). LIKELY
  for item 4 (the conflict is certain, which side is stale is not).
- Effort: S for items 1, 2, 3, 5, 6 (text edits in three lab files); item 4 needs a live Docker run.
- Unknowns: item 4's winning side.
- Spike needed: only for item 4 (one `--profile email` bring-up and `openssl s_client -tls1_2/-tls1_3`).
