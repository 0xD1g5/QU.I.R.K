# Decision: P2b scan-depth fix (scoring 4.0) and ladder re-measurement (SCORE-09)

**Status: RECORDED 2026-10-27; updated the same day after the code review (D-27..D-31, §13).**
This is the Phase 234 D-16 record for SCORE-09. It sets the
re-measured calibration ladder beside Phase 233's pre-change values
(`.planning/decisions/233-p2b-third-instrument-measurement.md` §4, §5 and §9).

Every number in this record was transcribed from instrument or script output produced at the
measured commit (§2). The provenance appendix lists those outputs. Where RESEARCH predicted a value,
the prediction appears beside the measurement and is labelled as a prediction. Nothing was tuned
toward a prediction.

## 1. Status and outcome

**SCORE-09 is fixed by scoring 4.0.** Within an already-assessed domain, adding healthy endpoints
no longer raises the readiness score. Under operator decision O-1, the gate is the Phase 233
instrument, `python -m scripts.p2b_instrument`, run across all five rungs (R1-R5), all five readings
(rows_ecdsa, rows_rsa, rows_certless, rows_mtls, mutator_212) and four points (+0, +20, +100, +500).
The single xfail is not the gate. `rows_mtls` was added by the code review (D-28, §13): the first
four readings could not see the mTLS channel. At the measured commit:

- **0 rising series** over 25 (rung, reading) groups (233: 28 over 20). See §5.
- **100/100** sweep cells agree with the independent spec-first closed form (80/80 before the
  review added `rows_mtls`).
- **647/647** term and branch probes agree (644 before the review's three new branch probes).
- `KNOWN_DISAGREEMENTS` is empty.

**999.120 is closed by this change.** The scoring-4.0 commit is
**`23ef422875071113ca33e81c9eb63ce35d2db4de`** (`SHA_03_40`, "feat(234): scoring 4.0 —
absolute-count curve, classical-key rule, PQC cert bucket, Kerberos placeholder (SCORE-09)"). It
also removed the `xfail(strict=True)` on
`tests/test_score_properties.py::test_p2b_score_does_not_improve_by_observing_more_healthy_endpoints`
and its `known_open_defect` row in `tests/skip_registry.py`. The commits that complete it:

| Role | SHA |
|------|-----|
| Spec-first 4.0 closed form (D-06) | `474c93ebfc4ba5364917673a1bd4fdbe5a8fe1f5` |
| P2b gate nodes, red against 3.0 (D-07, D-03, D-08) | `80f20e4292c3205df9f80864d97085cad3ce0b7a` |
| Red-first PQC bucket, classical key rule, Kerberos placeholder, O-6 pin | `f87efc34da4719173c6a13d02b0c50fe39cd4a30` |
| **Scoring 4.0** | **`23ef422875071113ca33e81c9eb63ce35d2db4de`** |
| O-4 roadmap/lift retarget; scan-coverage lift zeroes count (D-03) | `fab63af453e93dc21d109a408a902ed34465f0de` |
| Re-pins, same property with a new number (D-10) | `0abc928182229026007af38e59b9287c11a65c90` |
| Semantic rewrites (D-10, D-26) | `1f4b988bb9970f0f2f531696b27e1a9eab216c9a` |
| 999.113 closed as moot (D-12) | `f2379a8428a87ca7b21463b968c29dacc7f672af` |
| Review: spec-first closed form for D-28/D-29/D-30 + `rows_mtls` reading (red) | `55ce5d18c8ca1cd3f36279022129d7222be96dc0` |
| Review: mTLS presence credit (D-28) | `e987c1e092db2033a9f2d37628d9affbeb8b302c` |
| Review: undetermined-key -8 independent of PQC (D-29) | `0c51d456dd5d4b06300a207c71367681f3385200` |
| Review: Kerberos scan-error rows not identity evidence (D-30) | `53c8a46096b6143745ed15a4220a38ecdb84bc2e` |

**Scoring version 3.0 -> 4.0 (D-05).** `SCORING_VERSION = "4.0"`, with the note "scoring v4 — not
comparable with v3 or earlier scores". Trends and compare re-score stored endpoints live, so they
read 4.0 throughout. Persisted values keep the version they were recorded with. For example,
`quirk-output/intelligence-20260914-142606.json` still records `scoring_version: "3.0"` with total
15 (computed 61). The same scan re-scored live reads 18 on 4.0 (§8).

## 2. Measured at

| Field | Value |
|-------|-------|
| Measured commit (after the code review, `SHA_REVIEW_MEASURED`) | `7d9594633579549058e18a6ca07f45816b4c48de` (branch `v528-open`) |
| First measured commit (`SHA_06_MEASURED`) | `f2379a8428a87ca7b21463b968c29dacc7f672af`; every value it measured is reproduced at `7d959463` (§13) |
| Tree state | `provenance.dirty: false`; `git status --porcelain -- quirk scripts tests` was empty |
| `scoring_blob` | `b00b6f6f3f3004e3ec48f7c332c8add64d2c7ded` (pre-review 234: `2291239ee9271beac8b3ad5adee6a2f4bfa8a392`; 233: `25f0f7912202dd5192a5634ac3b2f04578608912`) |
| `evidence_blob` | `3c85314c08fd75d08c5b8302be1424cc9409479e` (pre-review 234: `8f2edfa1336b490aa8a4ed161c537d5939df155a`) |
| Python | 3.14.10 (local `.venv`; CI runs 3.11, and the scratch scripts are 3.11-safe) |
| Date | 2026-10-27 |
| 233 baseline | head `2571917018452c10d595d35700b830a7678d0438`, `233-measurement.json` |

## 3. The model change

These are D-01..D-04 and D-11, as committed in `23ef4228`.

- **D-01, the count curve.** All 35 former `_ratio(num, den)` sites now use a curve of the
  weakness count alone, with no denominator:

  `penalty = w * min(1, count / N_REF) ** 0.5`, with **`N_REF = 40`** for both the endpoint and the
  certificate families.

  The exponent (0.5) and the curve family carry over from 999.115. Every `*_ratio` weight key name
  is kept, because `calibration_overrides` addresses weights by name. `_ratio` is deleted.
- **N_REF = 40 is a continuity anchor, not a fit (O-3).** 40 is the ladder skeleton population, so
  R1-R4 score exactly what they scored before at their own size, and only the dependence on estate
  size is removed. The research probe found that every N_ref from 5 to 100 passes the bands,
  because ceilings dominate the emitted scores. The bands therefore cannot select N_ref, and 40 is
  an operator choice. The consequence is small-estate lenience (§10).
- **D-02, mTLS, corrected by D-28.** D-02 made the +6 mTLS bonus the same curve with a positive
  sign (an absolute count that saturates at N_REF). The code review showed that this kept a
  scan-depth reward: every further mTLS-enforcing endpoint raised identity_trust. Under **D-28** it
  is a **presence credit**: +6 once when any mTLS endpoint is observed, the same single-step shape
  as the PQC credit. The 35 count sites became 34 count terms plus one presence term (§13).
  **Operator-ratified 2026-10-28:** D-28 was an orchestrator call made at code review; the operator
  reviewed it after the close and kept it ("keep mtls, that is a fair call to make"). It is no
  longer open for overrule before 4.0 ships.
- **D-03, scan errors.** The two scan-error sites (hygiene w6, modern_tls w5) used to read
  `scan_error.rate = scan_error_count / total_endpoints`. They now read `scan_error.count` through
  the curve. A non-comment `get("rate"` appears 0 times in `scoring.py`.
- **D-04, the key-type rule.**
  - Any classical certificate key (RSA, ECDSA, EdDSA): flat −8, not count-based.
  - Certificates observed with no determined key type: also −8. The rule was written
    `elif C > 0 and PQC == 0` (RESEARCH D-06 step 5). **D-29 corrected it** to `elif C > PQC`,
    independent of PQC, because one PQC certificate exempted every undetermined one beside it
    (§13).
  - The ECDSA +4 bonus is removed (O-2: classical ≠ ready).
  - A PQC or hybrid certificate key, from the new evidence bucket `cert_key_type_counts.PQC`
    (O-4), earns the existing PQC credit. That credit is +8, granted **once**, when
    `pqc_hybrid_endpoint_count > 0` or `cert_key_type_counts.PQC > 0`.
- **D-04's single-PQC-observation step is deliberate, sanctioned credit (O-2).** The first PQC
  observation adds +8, and a PQC key-exchange observation also lifts the 84 ceiling. That step is
  the purpose of the rule, not dilution.
- **The PQC certificate credit does not lift the 84 KEX ceiling (A2).** That ceiling stays keyed
  on `pqc_hybrid_endpoint_count` only. This is pinned by
  `tests/test_pqc_agility_bonus.py::test_pqc_cert_does_not_lift_pqc_readiness_ceiling`.
- **D-11, Kerberos placeholders.** A KERBEROS row with no `scan_error` and no `etype:` in
  `service_detail` is a placeholder. Evidence counts it in `kerberos_placeholder_count`, and the
  identity gate uses `max(0, KERBEROS - kerberos_placeholder_count)`. So a placeholder alone no
  longer marks identity as assessed. Todo `261023-detect-kerberos-placeholder-rows-count-as-assessed`
  was closed in `23ef4228`. The evidence schema went to 1.3.0.
- **D-30 (code review), Kerberos scan-error rows.** A KERBEROS row that carries a `scan_error`
  (unreachable or never-probed KDC, unrecognised reply, KRB-ERROR) is not identity evidence either.
  Evidence counts it in `kerberos_scan_error_count` (schema 1.4.0), and the identity gate subtracts
  it with the placeholders.

`SCORE_WEIGHTS` has 40 keys summing to 293.0, pinned by `tests/test_score_weights_invariant.py`.

## 4. Before / after: ladder at +0

Source: `ladder_at_zero` in `233-measurement.json` (3.0) and `234-measurement.json` (4.0). Subscores
are listed in the order hygiene / modern_tls / identity_trust / agility_signals / data_at_rest /
data_in_motion.

| Rung | 233 emitted/computed | 233 ceiling | 233 subscores | 234 emitted/computed | 234 ceiling | 234 subscores | 234 losing ceilings |
|------|----------------------|-------------|---------------|----------------------|-------------|---------------|---------------------|
| R1 | 100/100 | none | 25/25/25/25/25/25 | **100/100** | none | 25/25/25/25/25/25 | — |
| R2 | 78/93 | pqc_readiness 84 | 25/25/23/17/25/25 | **78/93** | pqc_readiness 84 | 25/25/23/17/25/25 | — |
| R3 | 46/85 | consequence 54 | 22/23/16/17/25/25 | **46/85** | consequence 54 | 22/23/16/17/25/25 | (84, pqc_readiness) |
| R4 | 24/72 | consequence 34 | 15/18/11/16/23/25 | **24/72** | consequence 34 | 15/18/11/16/23/25 | (84, pqc_readiness) |
| R5 | 18/71 | consequence 25 | 13/15/12/16/25/25 | **18/74** | consequence 25 | 14/15/16/16/25/25 | (84, pqc_readiness) |

Re-measured at `7d959463` after the code-review fixes: every field of every rung is identical to the
`f2379a84` measurement above. No rung carries mTLS between 1 and 39 endpoints, a PQC certificate
beside undetermined ones, or a Kerberos scan-error row, so D-28/D-29/D-30 cannot move them.

R1-R4 are identical to 233 in every field. That is the O-3 anchor working as intended: each rung's
skeleton population is 40. R5's computed score rises 71 -> 74 (hygiene +1, identity +4), while its
emitted score stays at 18, because 25 × 74 / 100 = 18.5 rounds half-to-even to 18 (§12, RESEARCH
Pitfall 1).

**Prediction vs measurement.** RESEARCH predicted R1-R4 unchanged and R5 at 18/74 with subscores
14/15/16/16/25/25. The measurement matches.

## 5. Before / after: sweep tables

Source: `results[]` in both instrument files. Each cell is emitted/computed at +0 / +20 / +100 /
+500 healthy endpoints. The full 80-cell table, with ceilings and subscores, is in
`234-measurement-diff.md`.

### rows_ecdsa (primary)

| Rung | 233 (3.0) | 234 (4.0) |
|------|-----------|-----------|
| R1 | 100/100 · 100/100 · 100/100 · 100/100 | 100/100 · 100/100 · 100/100 · 100/100 |
| R2 | 78/93 · 83/99 · 83/99 · 84/100 | 78/93 · 78/93 · 78/93 · 78/93 |
| R3 | 46/85 · 50/93 · 51/95 · 52/97 | 46/85 · 46/85 · 46/85 · 46/85 |
| R4 | 24/72 · 28/82 · 30/89 · 32/93 | 24/72 · 24/72 · 24/72 · 24/72 |
| R5 | 18/71 · 21/83 · 22/89 · 24/95 | 18/74 · 18/74 · 18/74 · 18/74 |

### rows_rsa

| Rung | 233 (3.0) | 234 (4.0) |
|------|-----------|-----------|
| R1 | 100/100 · 100/100 · 100/100 · 100/100 | 100/100 · 100/100 · 100/100 · 100/100 |
| R2 | 78/93 · 79/94 · 79/94 · 80/95 | 78/93 · 78/93 · 78/93 · 78/93 |
| R3 | 46/85 · 47/87 · 48/89 · 50/92 | 46/85 · 46/85 · 46/85 · 46/85 |
| R4 | 24/72 · 26/76 · 28/83 · 30/88 | 24/72 · 24/72 · 24/72 · 24/72 |
| R5 | 18/71 · 19/77 · 21/83 · 22/89 | 18/74 · 18/74 · 18/74 · 18/74 |

### rows_certless

| Rung | 233 (3.0) | 234 (4.0) |
|------|-----------|-----------|
| R1 | 100/100 · 100/100 · 100/100 · 100/100 | 100/100 · 100/100 · 100/100 · 100/100 |
| R2 | 78/93 · 78/93 · 78/93 · 78/93 | 78/93 · 78/93 · 78/93 · 78/93 |
| R3 | 46/85 · 46/86 · 47/87 · 47/87 | 46/85 · 46/85 · 46/85 · 46/85 |
| R4 | 24/72 · 25/74 · 27/78 · 28/81 | 24/72 · 24/72 · 24/72 · 24/72 |
| R5 | 18/71 · 18/74 · 20/78 · 20/82 | 18/74 · 18/74 · 18/74 · 18/74 |

### mutator_212 (continuity)

| Rung | 233 (3.0) | 234 (4.0) |
|------|-----------|-----------|
| R1 | 100/100 · 100/100 · 100/100 · 100/100 | 100/100 · 100/100 · 100/100 · 100/100 |
| R2 | 78/93 · 78/93 · 78/93 · 78/93 | 78/93 · 78/93 · 78/93 · 78/93 |
| R3 | 46/85 · 46/86 · 47/87 · 47/87 | 46/85 · 46/85 · 46/85 · 46/85 |
| R4 | 24/72 · 25/74 · 27/78 · 28/81 | 24/72 · 24/72 · 24/72 · 24/72 |
| R5 | 18/71 · 18/74 · 20/78 · 20/82 | 18/74 · 18/74 · 18/74 · 18/74 |

### rows_mtls (code review, D-28)

Certless TLS 1.3 rows that enforce mTLS (`tls_blocker_reason` `MTLS_REQUIRED`, no scan error), on
top of the rung plus a one-row seed, so +N is the rung plus 1 + N mTLS rows. The first mTLS
observation is the sanctioned presence step (pinned by
`tests/test_score_mtls_presence_credit.py`); this reading measures depth after it. 233 has no
such reading.

| Rung | pre-review 4.0 (count curve, 55ce5d18 red run) | 4.0 after D-28 (`7d959463`) |
|------|-----------------------------------------------|-----------------------------|
| R1 | 100/100 · 100/100 · 100/100 · 100/100 | 100/100 · 100/100 · 100/100 · 100/100 |
| R2 | 79/94 · 80/95 · 80/95 · 80/95 | 80/95 · 80/95 · 80/95 · 80/95 |
| R3 | 46/86 · 48/89 · 48/89 · 48/89 | 48/89 · 48/89 · 48/89 · 48/89 |
| R4 | 25/73 · 26/75 · 26/76 · 26/76 | 26/76 · 26/76 · 26/76 · 26/76 |
| R5 | 19/75 · 19/77 · 20/78 · 20/78 | 20/78 · 20/78 · 20/78 · 20/78 |

Identity at every point after D-28: R1 25, R2 25, R3 22, R4 17, R5 22.

### Gate figures (criterion 4)

- **Rising (rung, reading, emitted|computed) series: 233 = 28, 234 = 0.** After the code review the
  count is over 25 groups, `rows_mtls` included: still 0. On the pre-review scorer `rows_mtls` gave 8
  rising series (10 rising transitions, §13). The 28 is recomputed here
  from `233-measurement.json` by `diff233.py`, and it matches 234-01's independent count on the
  3.0 baseline. The plan's verify assertion (80 results, all agree, no disagreement, 0 rising)
  exited 0.
- 46 of 80 cells changed between 233 and 234. Every changed cell is a former rise that is now flat,
  or an R5 cell whose computed score moved 71 -> 74 at +0.
- **Closed-form agreement: 80/80** sweep cells (instrument `agreement {'agree': 80, 'total': 80}`)
  and **644/644** term and branch probes (`tests/test_p2b_instrument.py::_all_probes`, 0
  `_differs`), at `f2379a84`. At `7d959463`: **100/100** cells and **647/647** probes.
- Gate nodes at `f2379a84`: `tests/test_p2b_instrument.py` (15 nodes), the P2b property
  ×3 (no xfail) and the O-6 pin ×3 gave **21 passed**. At `7d959463` the same set plus the mTLS
  presence pin gave **22 passed**.
- `projection_gaps` are unchanged in kind: `protocol_counts.TLS` and `totals.endpoints` differ
  between the dict ladder and the row skeleton, as in 233 §8.

## 6. Scan-error dilution (D-03)

Under 3.0, the two scan-error sites read `scan_error.rate`, a share of **all** endpoints. They are
outside the 35 ratio terms, and the 233 instrument's weakness skeletons carry no scan-error rows,
so its sweep could not see them. Adding healthy rows lowered the rate, so the score rose. 234-01
measured this on 3.0 with four `timeout` rows on each rung: 42 rises, the first being R1
99 -> 100, with R1 hygiene 24 -> 25 and R3 hygiene 22 -> 23 -> 24. The committed node
`tests/test_p2b_instrument.py::test_scan_error_rows_do_not_dilute` was red on 3.0 and is green on
4.0. Mutation M3 (re-reading `rate`) turns it red again (§11).

On 4.0, each rung plus 4 `scan_error="timeout"` TLS rows, with the healthy ECDSA sweep, gives
(source: `234-residuals.md` §1):

| Rung | scan_error.count | +0 / +20 / +100 / +500 emitted/computed | hygiene | modern_tls | RESEARCH prediction |
|------|------------------|-----------------------------------------|---------|------------|---------------------|
| R1 | 4 | 97/97 at every point | 23 | 23 | 97 |
| R2 | 4 | 76/91 at every point | 23 | 23 | 76/91 |
| R3 | 4 | 45/83 at every point | 20 | 21 | 45/83 |
| R4 | 4 | 24/70 at every point | 13 | 17 | 24/70 |
| R5 | 4 | 18/71 at every point | 12 | 13 | 18/71 |

All five series are flat in emitted, computed, hygiene and modern_tls. The measurement matches the
prediction.

**Residual (a) is fixed by the code review (D-31, `f48862da`).** The roadmap item "Increase scan
coverage" used to trigger on `scan_error.rate >= 0.2` while 4.0 scores `scan_error.count`. It now
triggers on `scan_error.count > 0`, the scorer's input; the rate stays in the why text only. The
hygiene driver label "Scan error rate" is now "Scan errors". Probe (R3 with 40 scan errors among
250 endpoints, rate 0.16): the item was absent; now it is present with a +4 lift (42 -> 46), equal
to an independent rescore with the count zeroed.

## 7. Real estate (local-only)

Inputs: `--real-db quirk-output/quirk.db --real-json quirk-output/intelligence-20260914-142606.json`.
The run is `2026-09-14T14:25:49.899977+00:00` (370 rows, reference_utc `2026-09-14T14:26:06.389430`).
The instrument reads the DB only through `scripts.p2b_instrument.snapshot_db`, which opens it with
a `mode=ro` URI and copies it via `Connection.backup` into a `mkdtemp` directory. It never uses
`cp` and never serves the file.

| Reading | 233 §9 (3.0) +0 / +20 / +100 / +500 | 234 (4.0) +0 / +20 / +100 / +500 |
|---------|--------------------------------------|----------------------------------|
| recorded_json + mutator_212 | 15/61 · 16/65 · 18/71 · 19/76 | **16/64 · 16/64 · 16/64 · 16/64** |
| snapshot_rows + rows_ecdsa | 17/69 · 19/75 · 21/83 · 23/91 | **18/71 · 18/71 · 18/71 · 18/71** |

4.0 subscores at every point:

- snapshot_rows: hygiene 10, modern_tls 19, identity 15, agility 24, DAR 21, motion None.
  The cap is "7 open CRITICAL findings".
- recorded_json: hygiene 10, modern_tls 10, identity 15, agility 24, DAR 21, motion None.
  The cap is "5 open CRITICAL findings".

**Prediction vs measurement.** RESEARCH predicted snapshot_rows 18/71 flat and recorded_json +
mutator 16/64 flat. The measurement matches.

**Re-measured after the code review (`7d959463`):** identical at every point, with the same
subscores and cap reasons. The estate has no mTLS endpoint, no KERBEROS row and RSA keys present,
so D-28/D-29/D-30 do not reach it (§13). Because the real-estate score did not move, the D-13
CLI-vs-dashboard check below (18 on both surfaces) was not re-run: both surfaces call the same
`compute_readiness_score`, and its result for this scan is unchanged.

**Canonical DB integrity**, for `quirk-output/quirk.db`:

| When | sha256 | size (bytes) | mtime (epoch / local) |
|------|--------|--------------|------------------------|
| Before the real-estate run | `990366f8346a644bd576ef6543376d7d647fa783a3d5cf78ff13cca79677b946` | 5849088 | 1791847042 / Oct 12 19:17:22 2026 |
| After the real-estate run | `990366f8346a644bd576ef6543376d7d647fa783a3d5cf78ff13cca79677b946` | 5849088 | 1791847042 / Oct 12 19:17:22 2026 |
| After the D-13 check (§8) | `990366f8346a644bd576ef6543376d7d647fa783a3d5cf78ff13cca79677b946` | 5849088 | 1791847042 / Oct 12 19:17:22 2026 |

The hash is the same one 233 recorded, so the canonical DB has not changed since Phase 233. There
is no `-wal` or `-journal` sidecar. The instrument's temporary directory, under a dedicated
`TMPDIR`, was empty afterwards.

## 8. CLI vs dashboard (D-13, criterion 3)

**Scan run:** `2026-09-14T14:25:49.899977+00:00`, 370 endpoint rows.

**Snapshot.** `snapshot_db("quirk-output/quirk.db", "/Volumes/Digs-1TB/tmp-pytest-234/06-live/uat234/")`
returned `quirk-snapshot.db`. It was renamed to `uat234/quirk.db`. The backup API rewrites the
header, so the snapshot's sha256 (`0ff22cb0c87098cbb0c6cb29c6b879dc403bb3a9975a9ebe6f2b6cb0d6887307`)
differs from the source's. Its `PRAGMA integrity_check` returned `ok`, and it holds the 370 rows.

**The canonical DB predates a column migration.** The ORM's first read of the unmigrated snapshot
failed with `no such column: crypto_endpoints.cert_eku_oids`. The dashboard's boot migrated **the
snapshot only**, and the snapshot hash then changed to
`2f1f4a73b6770745638e84aca3efc51354105c4e06e2c18418bab50dd75ba4b4`. The canonical file was never
opened by the app: `lsof` on the server PID showed only the snapshot path, and the canonical hash is
unchanged (§7). This is the same hazard as memory
`feedback_capture_scripts_must_not_serve_canonical_db`: serving the canonical file would have
migrated it.

**Report side.** This surface is the report/CLI pipeline: XSURF-04 surface A,
`tests/test_cross_surface_parity.py:571-584`. It takes the snapshot `CryptoEndpoint` rows for the
run, then applies `derive_report_findings`, `build_evidence_summary`, and
`compute_readiness_score(evidence, profile=None)`. It is the same scorer `run_scan.py` calls for a
scan's report.

No `quirk` / `run_scan.py` subcommand re-scores a stored scan read-only. `report` manages branding
profiles, and `export` pushes findings JSON to a SIEM. So the pipeline script stands in for the CLI
here, as the plan specifies.

**Dashboard side.** The server was started as:

```
env -u QUIRK_API_TOKEN HOME=<scratch>/home QUIRK_DB_PATH=<scratch>/uat234/quirk.db \
  .venv/bin/python run_scan.py serve --host 127.0.0.1 --port 8634 --no-open
```

It ran with cwd in the scratch directory, so no relative fallback could resolve to
`./quirk-output/quirk.db`. The request was:

```
curl -s -H "X-Quirk-Request: 1" ".../api/scan/latest?scan_id=2026-09-14T14:25:49.899977%2B00:00"
```

The fields were read from the response's `score` object; `meta.scan_id` echoes the run id, and
`meta.total_endpoints` is 370.

| Field | Report / CLI pipeline | Dashboard `/api/scan/latest` (`score.*`) | Equal |
|-------|-----------------------|------------------------------------------|-------|
| score | **18** | **18** | yes |
| rating | POOR | POOR | yes |
| rating_cap_reason | 7 open CRITICAL findings — score limited to 18 (computed 71) | 7 open CRITICAL findings — score limited to 18 (computed 71) | yes |
| subscores (hyg/tls/id/agi/dar/mot) | 10/19/15/24/21/None | 10/19/15/24/21/None | yes |
| domains_assessed | 5 | 5 | yes |
| scoring_version | **"4.0"** | **"4.0"** | yes |
| product version | QU.I.R.K. v5.27.0 (`run_scan.py --version`; `quirk.__version__` 5.27.0) | no version field in `/api/scan/latest`; `/api/config` returns only `{"vertical":"general"}` | — |

**Verdict: the two surfaces agree on every compared field, with scoring_version "4.0" on both.**
The live score (18/71) equals the instrument's real-estate `snapshot_rows` +0 cell (§7). It differs
from the persisted 3.0 intelligence JSON for the same scan (15, computed 61), as D-05 intends.

**Server lifecycle.** The server bound `127.0.0.1:8634` over IPv4 (`lsof`:
`TCP 127.0.0.1:8634 (LISTEN)`), with operator auth disabled and loopback only. It answered 200
within 3 s. It was stopped with `kill` on its PID. Afterwards:

- `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8634/` printed `000`;
- `lsof -iTCP:8634 -sTCP:LISTEN` returned nothing;
- `ps aux | grep "run_scan.py serve"` returned nothing.

## 9. Test changes (D-10)

**All nine semantic changes** (six from plans 234-01..05, three from the code review), each with
its one-line justification and owning commit:

1. **`tests/test_p2b_instrument.py::test_continuity_reproduces_212`** — flat (D-08). Under 3.0 this
   node pinned 212's rising continuity reading, 71 -> 74 -> 78 -> 82, which was the defect itself.
   It now asserts the reading is flat (R5 74 at every point), and the 3.0 sequence is kept as
   history in its docstring. The name is kept because UAT-233-04 cites it.
   Commit `80f20e4292c3205df9f80864d97085cad3ce0b7a` (234-01).
2. **Kerberos pin renamed `test_principal_unknown_placeholder_row_is_not_assessed`**
   (`tests/test_kerberos_probe_principal_config.py`; D-11 / D-26). The old pin asserted that the
   placeholder row counted as assessed. That assertion inverts under D-11, so the test was renamed
   to state the new property. Commit `23ef422875071113ca33e81c9eb63ce35d2db4de` (234-03).
3. **`tests/test_score_lift.py::test_clamp_binding_fixture_actually_binds`** — the 3.0 share
   formula (2/2 -> 37 > 25) no longer exists. The fixture counts rise to N_REF (plaintext 40,
   http-on-tls 40, scan_error.count 20), so the hygiene clamp still binds: the unclamped penalty is
   38.24 > 25 and hygiene is 0. Commit `1f4b988bb9970f0f2f531696b27e1a9eab216c9a` (234-05).
4. **`tests/test_score_clamp_property.py::test_agility_ceiling_saturates_on_reference_estate`,
   renamed `test_agility_stays_below_cap_on_reference_estate`** (D-26). The saturation came from
   the ECDSA +4 that D-04/O-2 removed. Pre-clamp agility goes 36.5918 -> 24.0513, and emitted goes
   25 -> 24, so the estate now sits below the cap. The skip_registry row was renamed in the same
   commit. Commit `1f4b988b…` (234-05).
5. **`tests/test_scoring_normalization.py::test_overall_score_zero_when_all_subscores_zero`** —
   under O-3 the maximum penalty is reached at an absolute count, not at a share. Every weakness
   counter therefore goes 1 -> 40, including the four agility counters the fixture never set, so
   every subscore is still 0 and the result is still POOR. Commit `1f4b988b…` (234-05).
6. **`tests/test_score_coverage_disclosure.py::test_adcs_only_identity_evidence_marks_identity_assessed`**
   — the fixture goes from 1 ADCS row to 3 ESC1 rows. The penalty is 2 × √(n/40) < 0.5 for
   n ≤ 2, so it rounds away (O-3 small-estate lenience). Measured identity: 25 at n = 1 and 2, 24
   at n = 3 and 4. A one-row "is assessed" assertion was added. Commit `1f4b988b…` (234-05).
7. **`tests/test_qramm_scoring.py::test_maturity_label_no_gaps_no_overlaps`** (code review D-31,
   WR-05) — the valid label set gains "Below Basic", because 0.0 and 0.5 sit below CSNP's Basic
   floor of 1.0. The property, every score maps to exactly one label, is unchanged. Commit
   `6e865f5f08ae1613348859577d817deb81ffb6c4`.
8. **`tests/test_qramm_scoring.py::test_maturity_label_covers_all_five_levels`** (D-31) — still
   requires all five CSNP labels, and now also requires that the only other label the sweep sees is
   "Below Basic". The name is kept: it is still true, and UAT-SERIES cites it. Commit `6e865f5f…`.
9. **`tests/test_qramm_scoring.py::test_overall_mean_over_assessed_dimensions_only`** (D-31) — the
   0.6667 mean's maturity is "Below Basic", not "Basic". Commit `6e865f5f…`.

**Re-pins from the code review: none.** D-28, D-29 and D-30 moved no pinned value: the 134
score-adjacent test files (every test file importing the scorer, evidence, roadmap, score lift or
the instrument) gave 1910 passed, 22 skipped, 1 xfailed with no edit after `53c8a460`.

**Code-review shape changes (not re-pins, not semantic):** `tests/test_p2b_instrument.py` asserts
34 `COUNT_TERMS` plus one `PRESENCE_TERMS` row (was 35 count terms), 5 readings and 50 D-10 cells
(was 4 and 40), 25 non-increase groups (was 20), and has three new branch probes
(`kerberos-scan-error-only`, `undetermined-39-with-pqc-1`, `all-certs-pqc`; the last two carry two
saturated agility penalties so the -8 is not hidden by the clamp). Commit `55ce5d18`.

**Re-pins: 9** (same property, new number). They are rows 8-16 of 234-05's D-10 table: XSURF
0508 73 -> 76, XSURF07 trend/merge 32 -> 33, XSURF07 compare 31 -> 30, evidence-coverage
regression 76 -> 72, legacy-TLS vocabulary modern_tls 18 -> 22, trends/merge/notify critical
ceiling 27 -> 31 ×3, motion refused-email 73 -> 81.

The evidence-coverage regression row moves **76 -> 72**, the opposite direction from RESEARCH's
label "72 -> 76". The fixture holds 1 RSA and 1 ECDSA key, so its 3.0 +4 became a 4.0 −8. Every
cross-surface equality passed unchanged; only the expected literals moved. Commit
`0abc928182229026007af38e59b9287c11a65c90`.

**Other committed shape changes:**

- `test_closed_form_term_probes` (234-01): the denominator assertion became COUNT_TERMS shape
  asserts, and `PROBE_VALUES` widened to `(1, 3, 7, 13, 20, 39, 40, 41, 80)`.
- `tests/test_score_weights_invariant.py`: the sum moved to 293.0 (234-03).

**SCORE-10 shape re-pins (234-02, `f56ae61f0f9f77310df02e6a0791b72553b62a2c`)** — each is the same
property with a new call shape or field set:

- `tests/test_qramm_scoring.py`: 4 calls gain `assessed=_ALL_DIMS`.
- `test_qramm_score_response_has_canonical_fields`: the field set gains 4 fields.
- `tests/test_qramm_compliance_map.py::_rows` stamps `answered_by_dimension`, so its hand-built
  score is a current score rather than a legacy one. No assertion changed.

## 10. Properties this change does NOT claim

- **D-25: legacy QRAMM overalls.** A QRAMM overall saved before this phase (its `score_json` has no
  `answered_by_dimension`) still averages a Not-assessed dimension in as 0 in its stored blob. No
  surface shows that number as a maturity level. The overall reads **"Recalculate to apply the
  updated overall"**, and every answered dimension of that session reads "Stale — recalculate"
  until the session is re-scored. The reason is that without saved counts, newer answers cannot be
  ruled out (D-25 revision 2). Pinned by the contract fixture's `legacy_score_json` case (pytest
  and vitest halves).
- **Residual (b): the scorecard's legacy branch is unreachable in the live UI.** `QRAMMProvider`
  initialises `scoreResult` to null, and only a fresh POST /score sets it. A fresh POST always
  returns a current score. So the dashboard scorecard's Recalculate branch is pinned by the TS twin
  and vitest only, and is not reachable live today. **Print is the only live surface that reads
  the saved score** (from the session detail's persisted `score_json`), so print is where a legacy
  overall actually shows "Recalculate to apply the updated overall". This was found in 234-04 and
  is disclosed here, not fixed. Follow-up todo:
  `.planning/todos/pending/261027-qramm-scorecard-legacy-recalculate-branch-unreachable.md`.
- **O-6: newly-assessed-domain coverage credit (deliberate).** SCORE-09 covers more endpoints in
  domains that are already assessed. The first clean row of a domain that is not yet assessed
  still raises the headline, through Phase 188's exclude-and-rescale: the domain enters at 25/25.
  That is coverage credit, not dilution. Measured on 4.0 with one clean SMTP-STARTTLS row
  (`234-residuals.md` §2):

  | Rung | before (domains) | after (domains) | RESEARCH prediction |
  |------|------------------|-----------------|---------------------|
  | R2 | 77/92 (5) | 78/93 (6) | 77/92 -> 78/93 |
  | R3 | 44/82 (5) | 46/85 (6) | 44/82 -> 46/85 |
  | R4 | **22/66** (5) | **24/72** (6) | 23/67 -> 25/73 (prediction; the measured value differs) |

  The 3.0 scorer gives the same numbers, so the step predates 4.0. Pinned by
  `tests/test_score_newly_assessed_domain.py`. Follow-up todo:
  `.planning/todos/pending/261027-score-newly-assessed-domain-step-is-coverage-credit.md`.
- **D-19: closed-port scan errors lower the score (pre-existing).** `scan_error_count` includes
  CLOSED and ADVISORY rows, so probing more empty ports lowers the score. Measured on R3 plus N
  `protocol="CLOSED"`, `scan_error="connection refused"` rows (`234-residuals.md` §3):

  | +closed | scan_error.count | 4.0 emitted/computed (hygiene) | 3.0 emitted/computed (hygiene) |
  |---------|------------------|--------------------------------|--------------------------------|
  | 0 | 0 | 46/85 (22) | 46/85 (22) |
  | 20 | 20 | 43/80 (18) | 45/83 (20) |
  | 100 | 100 | 42/78 (16) | 43/80 (18) |
  | 300 | 300 | 42/78 (16) | 43/79 (17) |

  The 3.0 column is the 3.0 scorer loaded read-only from `git show c1714353:quirk/intelligence/scoring.py`
  (no checkout), run over the same evidence. The fall exists under 3.0 too (by rate), so D-03 did
  not cause it. 4.0 falls a little further at each point, because `count / 40` exceeds the 3.0
  rate. For example, at +20 the 4.0 input is 20/40 = 0.5 while the 3.0 rate is 0.3333, and from 40
  rows on, the 4.0 curve is saturated. The measured values match RESEARCH's prediction. Follow-up todo:
  `.planning/todos/pending/261027-scan-error-count-includes-closed-and-advisory-rows.md`.
- **D-20: ML-DSA leaf certificates cannot reach evidence yet.** `cryptography` raises "Unknown key
  type" in `tls_scanner._pubkey_info` for ML-DSA leaves (OIDs **2.16.840.1.101.3.4.3.17**,
  2.16.840.1.101.3.4.3.18 and 2.16.840.1.101.3.4.3.19; RFC 9881). Until the deferred scanner work
  lands, the O-4 `cert_key_type_counts.PQC` bucket stays dormant on real scans. The bucket is unit-
  and mutation-tested (M6, §11). Follow-up todo:
  `.planning/todos/pending/261027-tls-scanner-ml-dsa-leaf-raises-unknown-key-type.md`.
- **D-21: QRAMM stale detection compares counts, not values.** Re-answering an answered question
  with a different value is not flagged as stale. Follow-up todo (answers digest):
  `.planning/todos/pending/261027-qramm-stale-detection-compares-counts-not-values.md`.
- **RESEARCH Pitfall 8: the legacy-TLS lift is 0 on live evidence.** Already owned by an earlier
  todo, so no new one was filed: `.planning/todos/pending/261012-doc224-legacy-tls-roadmap-and-lift-still-use-low-severity-proxy.md`
  (owner HORIZON 999.131, filed by Phase 224), which records the same defect with a live
  `compute_item_lifts` reproduction.
- **O-3: small-estate lenience (accepted by the operator).** Because N_REF is an absolute anchor,
  a weakness on a tiny estate costs less than its share would imply. Measured with one endpoint
  that is one plaintext HTTP row (`totals.endpoints` 1, assessable 1, `plaintext_http_count` 1,
  finding "Plaintext HTTP service detected"; `234-residuals.md` §4):

  | | 4.0 | 3.0 |
  |---|-----|-----|
  | hygiene subscore (scorer) | **22** | **7** |
  | total, emitted/computed | 66/96 | 52/76 |
  | plaintext term by hand | 25 − 18·min(1, 1/40)^0.5 = 22.15 | 25 − 18·(1/1)^0.5 = 7.00 |

  The 3.0 total is from the read-only 3.0 scorer. The hand formula follows the plan. The
  measurement matches the prediction (22 vs 7). Related: semantic change 6 in §9.
- **Remediated multihost moves 84 -> 80.** `compute_readiness_score(_remediated_multihost_evidence())`
  gives **80/95** on 4.0, capped by "no post-quantum key exchange observed — score limited to 80
  (computed 95)". 233/999.115 recorded 84, and the 3.0 scorer reproduces 84/100. The cause is
  D-04: the remediated estate keeps 17 ECDSA certificate keys (`cert_key_type_counts`
  `{RSA: 0, ECDSA: 17}`), so it takes the flat −8 ("Quantum-vulnerable certificate keys
  (RSA/ECDSA/EdDSA)", agility 17) where 3.0 awarded the ECDSA +4. The PQC ceiling then scales the lower computed score. This matches
  RESEARCH's 84 -> 80.

The follow-up todos above were filed by plan 234-08 (2026-10-27) under the successor HORIZON row
999.139, five of them from this section: O-6, D-19, D-20, D-21 and residual (b)
(`261027-score-newly-assessed-domain-step-is-coverage-credit.md`,
`261027-scan-error-count-includes-closed-and-advisory-rows.md`,
`261027-tls-scanner-ml-dsa-leaf-raises-unknown-key-type.md`,
`261027-qramm-stale-detection-compares-counts-not-values.md`,
`261027-qramm-scorecard-legacy-recalculate-branch-unreachable.md`). A sixth 999.139 member,
`261027-doc-claim-ledger-source-line-cites-drift.md`, records the stale source-line cites in
doc-claim-ledger evidence that 234-07 reported. Pitfall 8 is owned by the existing 999.131 todo
named above, so the separate legacy-TLS todo this record first planned was not filed (it would
have duplicated that one). Residual (a), the roadmap-trigger rate, is **fixed** (D-31, §6, §13),
so it needs no todo; nor does the mTLS depth channel (D-28, below). Code review IN-07 confirmed
residual (b) and required no fix in Phase 234.

- **Removed by the code review: the mTLS depth channel.** Under D-02 the mTLS bonus was a count
  curve, so healthy mTLS-enforcing endpoints raised identity_trust up to N_REF; this record's
  earlier "0 rising series" did not name that channel because no reading carried mTLS. D-28 made it
  a presence credit and `rows_mtls` gates it (§5, §13). The first mTLS observation remains a
  deliberate single step, like the PQC credit and O-6.

## 11. Mutation evidence

Each mutation was applied to the committed file, the node was run alone, and the file was
reverted. After every revert, the scoped porcelain was empty.

| Plan | Mutation | Node | Result |
|------|----------|------|--------|
| 234-01 | all 41 3.0 `SCORE_WEIGHTS` set to 0 (plugin, repo untouched) | `test_p2b_weakness_rows_lower_the_score` (D-07b) | RED (R1 stays 100) |
| 234-02 | M1 `score_session` passes all dimensions as assessed | `test_endpoint_overall_matches_contract` | RED (0.5 vs 0.6667) |
| 234-02 | M2 delete the count-mismatch -> stale branch | `test_stale_case_rows_and_session_flag_match_contract` | RED |
| 234-02 | M3 `overall_state` returns current without counts | `test_legacy_score_json_rows_and_overall_read_recalculate` | RED |
| 234-02 | M4 `row_coverage_status` ignores `score_has_counts` | same legacy node | RED |
| 234-02 | M5 legacy -> stale checked before pending | same legacy node | RED |
| 234-03 | M1 curve divides by `endpoint_denom` (re-introduces dilution) | D-07a non-increase; P2b property; `test_closed_form_agrees` | RED ×3 |
| 234-03 | M2 ECDSA +4 bonus re-added | D-07a; `test_closed_form_agrees`; weights invariant; `test_ecdsa_cert_keys_take_the_classical_penalty` | RED ×4 |
| 234-03 | M3 scan error reads `rate` | `test_scan_error_rows_do_not_dilute`; `test_closed_form_term_probes` | RED ×2 |
| 234-03 | M4 `_count_curve` returns 0 | `test_p2b_weakness_rows_lower_the_score` | RED |
| 234-03 | M5 `N_REF = 39` in the closed form only | `test_closed_form_term_probes` | RED (39 probes) |
| 234-03 | M6 PQC branch after the classical prefixes | `test_pqc_composite_name_counts_pqc_not_ecdsa` | RED |
| 234-04 | M3-TS / M3a-TS remove stale mapping | "a stale saved score reads Stale on every QRAMM surface, never Self-assessed" | RED |
| 234-04 | M4-TS / M5-TS legacy reads current | "a score saved before the upgrade shows Recalculate instead of an overall maturity level" | RED |
| 234-04 | M6-TS stale checked before not-assessed | same legacy test | first run **SURVIVED**, which exposed a real gap; fixed in `279c1088`; RED after the fix |
| 234-04 | M7-TS drop the per-dimension missing-count guard | "a saved score missing one dimension's count reads that dimension Stale, never Self-assessed" | RED |
| Review | M1-PY `overall_state` ignores `stale` | `tests/test_qramm_assessment_parity.py::test_stale_case_rows_and_session_flag_match_contract` | RED (`'current' == 'stale'`) |
| Review | M2-TS `overallDisplayState` ignores `stale` | vitest "a stale saved score reads Stale on every QRAMM surface, never Self-assessed" | RED (scorecard "0.67 / Basic / 3 of 4 dimensions assessed") |
| Review | M3-TS print suppresses only `recalculate` | same vitest case | RED (print "Overall maturity: Basic (0.67) — 3 of 4 dimensions assessed") |
| Review | M4-PY drop the "Below Basic" row from `OVERALL_MATURITY_LEVELS` | `tests/test_qramm_assessment_parity.py::test_overall_maturity_mapping_matches_contract` | RED (table differs from the contract) |
| Review | M5-TS drop the "Below Basic" row from the TS twin | vitest "the overall maturity label comes from the shared mapping, so a mean below 1.0 never reads Basic" | RED (received "Basic") |

The scorer changes D-28, D-29 and D-30 were each red first against a dedicated node (and the
closed form disagreed with the scorer until each landed, §13), so they need no separate mutation.

234-05 recorded no mutation table of its own. Its semantic rewrites were checked by assertion
counts: 3 assertions removed and 4 added, so none was dropped.

## 12. What would falsify this record

- **A rising series** on any (rung, reading) at any point, in emitted or computed, when
  `python -m scripts.p2b_instrument --json` is re-run on a later commit with
  `scoring_blob b00b6f6f…` unchanged (`rows_mtls` included). `test_p2b_non_increase_all_rungs_all_readings`
  would fail.
- **A closed-form disagreement**: a sweep cell or one of the 647 probes where `scripts/p2b_closed_form.py`
  and `compute_readiness_score` differ, or a non-empty `KNOWN_DISAGREEMENTS`.
- **CLI != dashboard** on this run or any other: the report pipeline and `/api/scan/latest`
  differing on score, cap reason, subscores or scoring_version for the same `scan_id`.
- **R5 computed 75.** The emitted score would then round to 19 (25 × 75 / 100 = 18.75), because
  R5's emitted 18 rests on half-to-even rounding of exactly 18.5 (Pitfall 1). Measured: R5 computed
  74, 25 × 74 / 100 = 18.50, `round()` = 18.
- **R1-R4 at +0 differing from 233 §4.** That would mean N_REF no longer anchors the skeleton
  population.
- **A canonical DB hash other than `990366f8…b946`** with no recorded scan in between. That would
  mean a measurement wrote to it.
- **A scan-error row raising any rung** under a healthy sweep (D-03 regressed).

## 13. Review fixes D-27..D-31

The code review (`234-REVIEW.md`, 1 critical, 5 warnings, 7 info) was dispositioned by the operator
as D-27..D-31 (`234-CONTEXT.md`, "Locked after code review"). Every scorer change went spec-first:
`scripts/p2b_closed_form.py` was updated from the decision text in `55ce5d18`, committed red, and
only then was `quirk/intelligence/scoring.py` changed.

**SCORING_VERSION stays "4.0".** D-28, D-29 and D-30 change three 4.0 rules. Scoring 4.0 has not
been released (Phase 235 releases v5.28.0), so these are corrections inside 4.0, not a 4.1. Any 4.0
value persisted on a development machine before `53c8a460` used the pre-review rules; no released
artifact carries one.

### Spec-first red run (`55ce5d18`, unchanged scorer)

- `test_p2b_non_increase_all_rungs_all_readings`: RED, 10 rising transitions over 8 series, all
  `rows_mtls` (R2 79/94 -> 80/95; R3 46/86 -> 48/89; R4 25/73 -> 26/75 -> 26/76;
  R5 19/75 -> 19/77 -> 20/78).
- `test_closed_form_agrees`: RED. Sweep agreement 93/100; the 7 disagreeing cells are `rows_mtls`
  R2-R5 at +0 and R3-R5 at +20. First: R2|rows_mtls|0, closed form 80/95 (identity 25), code 79/94
  (identity 24).
- `test_closed_form_term_probes`: RED (`kerberos_scan_error_count` absent from the empty evidence
  summary). Behind it, 12 of 647 probes disagreed: `mtls_present_count` ×10 (values below N_REF on
  R3 and R5), `kerberos-scan-error-only`, `undetermined-39-with-pqc-1`.
- `test_healthy_rows_survive_a_later_clock`: RED (R3|rows_mtls|20 disagrees).

Agreement then rose with each scorer commit: after D-28 (`e987c1e0`) 100/100 cells and 645/647
probes; after D-29 (`0c51d456`) 646/647; after D-30 (`53c8a460`) **647/647**. No disagreement
remained to diagnose, and `KNOWN_DISAGREEMENTS` stayed empty.

### The fixes

| Decision | Finding | Change | Red first (own invocation) | Commit |
|----------|---------|--------|----------------------------|--------|
| D-27 | CR-01 | A stale current-format QRAMM score shows its overall as "Stale — recalculate" on the scorecard and print; API `score_overall_state` gains `"stale"`; print consumes the server field | pytest stale-case parity `'current' == 'stale'`; pytest `overall_state(..., stale=)` TypeError; vitest stale case (scorecard "0.67 / Basic / 3 of 4 dimensions assessed") | `b92535d9` red, `831d76a3` fix, `747e3ec5` bundle |
| D-28 | WR-03 | mTLS bonus = +6 once on presence | `test_first_mtls_endpoint_earns_the_presence_credit_once`: identity 11 -> 12 (expected 17) | `e987c1e0` |
| D-29 | WR-02 | undetermined -8 when `C > PQC`, independent of PQC; roadmap trigger follows | `test_undetermined_keys_with_one_pqc_cert_never_beat_classical_keys`: agility 25 > 19; roadmap item absent for 39 undetermined + 1 PQC | `0c51d456` |
| D-30 | WR-01 | `kerberos_scan_error_count` (schema 1.4.0) subtracted in the identity gate | evidence KeyError; `_not_probed_row` + 40 legacy-TLS rows made identity 25 | `53c8a460` |
| D-31 | WR-04, IN-02 | "Increase scan coverage" fires on `scan_error.count > 0`; label "Scan errors"; comment corrected | R3 + 40/250 scan errors: item absent | `f48862da` |
| D-31 | WR-05 | One overall maturity mapping (Python `OVERALL_MATURITY_LEVELS`, TS twin, contract `overall_maturity_levels`); a mean below 1.0 reads "Below Basic" | pytest ImportError and `'Basic' == 'Below Basic'`; vitest twin undefined and scorecard "Basic" | `c4754ac7` red, `6e865f5f` fix, `a8420515` bundle |
| D-31 | IN-01 | skip-registry reason names the agility-below-cap test | — (text) | `e84e67be` |
| D-31 | IN-03 | print consumes `scoreOverallState` | covered by D-27's vitest case | `831d76a3` |
| D-31 | IN-04 | Python drops non-integer persisted counts (keeps integral floats, as JSON/JS cannot tell 3.0 from 3) | API parity case: SGRM/DPE read self-assessed | `c3c3e77d` |
| D-31 | IN-05, IN-06 | PQC aliases DILITHIUM, FALCON, FN-DSA, FNDSA, SPHINCS; a PQC/composite name on a certless row lands in no bucket | 9 names PQC 0; certless composites RSA 1 / ECDSA 1 | `7d959463` |

### What moved, measured

- **Ladder (+0) and every pre-review sweep cell: nothing moved.** All 80 cells of the four original
  readings, and all five dict rungs, are identical at `7d959463` to `f2379a84`.
- **Real estate: nothing moved.** snapshot_rows + rows_ecdsa 18/71 and recorded_json + mutator_212
  16/64 at every point, with the same subscores and cap reasons. The real estate has
  `mtls_present_count` 0, no KERBEROS row, and 18 RSA keys, so none of D-28/D-29/D-30 applies.
- **The review's own probes, pre-review 4.0 (scorer read-only from `git show cfde8c90`) vs now:**

  | Probe | pre-review | now |
  |-------|------------|-----|
  | WR-03, dict R3 + 0/5/20/40 mTLS endpoints | 46/85, 47/87, 48/89, 48/89 | 46/85, 48/89, 48/89, 48/89 |
  | WR-03, dict R4 + 0/5/20/40 | 24/72, 25/73, 26/75, 26/76 | 24/72, 26/76, 26/76, 26/76 |
  | WR-03, dict R5 + 0/5/20/40 | 18/74, 19/76, 19/77, 20/78 | 18/74, 20/78, 20/78, 20/78 |
  | WR-02, 40 certs + 40 UNKNOWN: 39 RSA + 1 PQC | 74 (agility 19) | 74 (agility 19) |
  | WR-02, same: 39 undetermined + 1 PQC | **79 (agility 25)** | **74 (agility 19)** |
  | WR-01, 40 legacy TLS | 68 (3 domains) | 68 (3 domains) |
  | WR-01, same + `_not_probed_row` | **71 (4 domains, identity 25)** | **66 (3 domains, identity None)** |
  | WR-04, R3 + 40 scan errors / 250 endpoints | 42, no item | 42, item with lift +4 |

  The WR-03 rows now step once (0 -> first mTLS) and stay flat; the step is the sanctioned presence
  credit. In the WR-01 row the remaining 68 -> 66 comes from the Kerberos row's own scan error (the
  D-19 scan-error class), not from identity.
- **QRAMM contract session:** overall 0.6667 now reads "Below Basic" (was "Basic"). In the stale
  case the overall reads "Stale — recalculate" (was "0.67 · Basic · 3 of 4 dimensions assessed").

## Provenance appendix

Untracked phase artifacts (local only), in `.planning/phases/234-p2b-scan-depth-fix-ladder-re-measurement/`:

- `234-measurement.json` and `234-measurement.md`: the instrument at `7d959463` (overwritten after
  the code review; the `f2379a84` copies are kept in scratch as
  `/Volumes/Digs-1TB/tmp-pytest-234/fix-measure/*.pre-review.json`).
- `234-measurement-diff.md`: all 80 cells, 233 vs 234, with the +0 ladder and the rising-series
  counts.
- `234-real-estate.json` and `234-real-estate.md`: the instrument with `--real-db` and
  `--real-json`, at `7d959463`. `234-measurement-diff.md` still compares 233 with the `f2379a84`
  80-cell measurement, which `7d959463` reproduces cell for cell.
- `234-residuals.md`: D-03, O-6, D-19, O-3, remediated multihost, R5 rounding.
- `234-06-SUMMARY.md`.

Phase 233 baselines, in `.planning/phases/233-p2b-measurement-instrument/`: `233-measurement.json`
and `233-real-estate.json`.

Scratch, in `/Volumes/Digs-1TB/tmp-pytest-234/06-live/`:

- `diff233.py`: the 233 vs 234 diff.
- `residuals.py`: the residual readings.
- `scoring30.py`: a read-only `git show c1714353:quirk/intelligence/scoring.py`, used only for the
  3.0 columns.
- `report_side.py` and `report_side.json`: D-13 report side.
- `dashboard_side.json`: the `/api/scan/latest` response.
- `serve.log` and `serve.pid`.
- `uat234/quirk.db`: the migrated snapshot.

Phase 234 commits: see the table in §1. Earlier plan commits: SCORE-10
`d56af77f`, `f56ae61f`, `486e0052`, `9dda7bfd`, `dd79fa28`, `279c1088`, `3fc322f7`.

Canonical DB: `quirk-output/quirk.db`, sha256
`990366f8346a644bd576ef6543376d7d647fa783a3d5cf78ff13cca79677b946`, the same before and after
every read in this plan, and again before and after the code-review re-measurement (size 5849088,
mtime 1791847042, no sidecar; the instrument's temp directory was empty afterwards).
