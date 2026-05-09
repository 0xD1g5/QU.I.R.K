---
phase: audit-2026-05-08-cbom-intel-reports
reviewed: 2026-05-08T00:00:00Z
depth: deep
files_reviewed: 13
files_reviewed_list:
  - quirk/cbom/classifier.py
  - quirk/cbom/builder.py
  - quirk/cbom/writer.py
  - quirk/intelligence/roadmap.py
  - quirk/intelligence/confidence.py
  - quirk/intelligence/scoring.py
  - quirk/intelligence/trends.py
  - quirk/intelligence/evidence.py
  - quirk/intelligence/schema.py
  - quirk/reports/html_renderer.py
  - quirk/reports/technical.py
  - quirk/reports/executive.py
  - quirk/reports/writer.py
findings:
  critical: 7
  warning: 14
  info: 9
  total: 30
status: issues_found
---

# CBOM + Intelligence + Reports — Adversarial Audit (2026-05-08)

**Depth:** deep
**Files:** 13
**Status:** issues_found

## Summary

Findings span all three subsystems. The flagship CBOM concern (Phase 42 OBS-1) is **confirmed and broader than memorialized**: `cbom/builder.py` Pass-1 explicitly emits no algorithm components for **POSTGRESQL, MYSQL, RDS, S3, AZURE_BLOB, KUBERNETES, VAULT, CLOUD_SQL, CONTAINER, KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN** — that is at least 12 protocol families, not the 5 named in OBS-1. Pass-2 also short-circuits the same buckets, and Pass-3 protocol components are skipped for everything except SSH and TLS. CBOMs for these profiles will pass schema validation but be cryptographically empty (zero crypto signal).

Score arithmetic has multiple correctness defects: `agility_score` shares its 25-point cap with both penalties and the ECDSA bonus, so well-postured estimates over-clamp; `motion_broker_weak_tls_count` uses uppercase token "TLSV1.0" that **cannot match** the value `tls_v` produces (uppercase of "TLSv1.0" → "TLSV1.0", true, but uppercase of "TLSv1" → "TLSV1" — the predicate looks fine *but* TLS-1.0 negotiation typically reports literal "TLSv1.0" or "TLSv1"; both match). However, the `cert_pubkey_alg` startswith("ECDSA") branch in `evidence.py` cannot match because the cloud KMS normalizer outputs "ECDSA" but TLS scan output emits "EC" — see WR-04. Confidence calculation has a silent integer-division bug when `tls_count == 0` and `tls_enum_coverage_ratio` falls through to a default (CR-04).

Reports HTML renderer **does not** auto-escape — actually, it does (`autoescape=select_autoescape(["html", "j2"])`), so the obvious XSS is closed. However, `score_color` is interpolated raw into a CSS context and is selected from a closed dict so it's safe; `findings`, `endpoints`, `roadmap_items` are passed through and the template (verified absent of `|safe`) auto-escapes. **However**, `cfg.assessment.name` becomes the HTML `<title>` and runs through Jinja autoescape — safe. PDF export catches `Exception` blanket-style, hiding programmer errors (WR-09).

The technical Markdown writer interpolates user-controlled fields (host, cipher_suite, scan_error notes, cert_subject) directly into a Markdown table without escaping `|` or newlines (CR-07). Adversary-controlled subject CN can break the pipe-table rendering and inject arbitrary content.

Trend analysis has a **race-condition / data-loss risk**: `_fetch_session_endpoints` uses a 1-second window which can mis-bracket scans that span a clock second (BLOCKER CR-05). Two scans started within the same second cannot be disambiguated — both will be merged.

---

## Critical Issues

### CR-01: CBOM Pass-1 emits zero algorithm components for 12 protocol families (Phase 42 OBS-1 confirmed and undercounted)

**File:** `quirk/cbom/builder.py:421-446`
**Issue:** OBS-1 was filed for 5 profiles (database, registry, source, ssh-weak, storage-s3), but the source confirms the gap is wider:
- `CLOUD_SQL` branch (line 421) explicitly `pass` — no algorithm registered
- `POSTGRESQL`, `MYSQL`, `RDS`, `S3`, `AZURE_BLOB`, `KUBERNETES` (line 443) — `pass`
- `CONTAINER` (line 393) — `pass`
- `SOURCE` (line 398) — only registers if `_extract_algo_from_rule_id` matches (the algo_hints list misses common rules like `weak-cipher`, `insecure-prng`, `cbc-mode-without-mac`, `ecb-mode`)
- `VAULT` is not handled in any branch — falls through to the `else` (TLS) clause at line 448, where `cipher_suite` for VAULT findings is the severity tag, not a TLS suite, so `_decompose_cipher_suite` either returns nothing or returns garbage parts
- The plaintext motion buckets (`KAFKA-PLAIN`, `AMQP-PLAIN`, `REDIS-PLAIN`) are not handled in Pass-1 either; they fall through to the `else` (TLS) clause and similarly produce no useful algo registrations.

The result: CBOMs for any scan whose footprint is dominated by these protocols are cryptographically empty — zero algorithm components — yet they pass schema validation. The CBOM is the flagship deliverable; an empty-but-valid CBOM is a silent quality failure to a consultant.
**Fix:** For each protocol family, define a minimum-viable cryptographic catalog entry. Examples:
- `POSTGRESQL` ssl-off / `MYSQL` ssl-off / `RDS/none` / `KAFKA-PLAIN` etc. should register a synthetic "plaintext" component with `CryptoPrimitive.UNKNOWN` and `nist_quantum_security_level=0` so that the absence-of-encryption is visible in CBOM as a finding.
- `S3/sse-s3`, `S3/sse-kms-aws`, `BLOB/platform-managed`, `EKS/encrypted` should register `AES-256-GCM` (the documented platform default) so Pass-1 emits a real algo.
- `VAULT` should be added as an explicit branch matching the per-detail algorithms encoded in `service_detail` (e.g., transit cipher, PKI key alg).
- `CONTAINER` should register the library's bundled crypto (e.g., openssl 1.0.2 → register the legacy default suite). At minimum, classify the container as `CryptoPrimitive.UNKNOWN` with `parameter_set_identifier=library_version`.
- Add VAULT to `DAR_SKIP_PROTOCOLS` only after Pass-1 emits real algorithms for it.

---

### CR-02: VAULT protocol falls through to TLS branch in Pass-1 / Pass-2 / Pass-3

**File:** `quirk/cbom/builder.py:443, 448-463, 552-560`
**Issue:** `VAULT` is in `DAR_SKIP_PROTOCOLS` (line 52), which excludes it from Pass-2 (cert) and Pass-3 (protocol). But Pass-1's chain of `elif` clauses does **not** mention `VAULT`. The `elif ep.protocol in ("POSTGRESQL", "MYSQL", "RDS", "S3", "AZURE_BLOB", "KUBERNETES")` at line 443 omits VAULT. So a VAULT row falls into the `else` branch (line 448, "TLS default") and:
1. `ep.cipher_suite` may be None or a Vault-specific identifier; `_decompose_cipher_suite` will return `[]` or wrong tokens.
2. `ep.cert_pubkey_alg` if set is registered as an algorithm — accidentally correct for some Vault PKI rows but an undocumented coincidence.
3. The same row is later excluded from Pass-2/3.
This is incoherent: Pass-1 partially treats VAULT as TLS while Pass-2/3 skip it.
**Fix:** Add `"VAULT"` to the same line-443 tuple that contains POSTGRESQL/MYSQL/etc., or build a dedicated VAULT branch that registers Vault crypto explicitly (preferred — see CR-01).

---

### CR-03: SOURCE algorithm hint extraction has misordered/buggy patterns — DSA matches before ECDSA reliably, but DES → "3DES" (wrong)

**File:** `quirk/cbom/builder.py:72-82`
**Issue:** The `algo_hints` list contains the entry `("des", "3DES")` *after* `("3des", "3DES")`. The comment claims "longer/more-specific patterns checked first to avoid false positives", but this entry maps **bare DES → "3DES"** (different cipher). A semgrep rule containing the substring `des-cbc` (single DES, not 3DES) will be falsely classified as 3DES. Single DES has 56-bit effective security; 3DES has 112-bit; misclassifying as the stronger algorithm understates risk.

Also, `("aes", "AES-256-GCM")` — every semgrep rule mentioning AES (including AES-128, AES-CBC, AES-ECB) will be canonicalised to AES-256-GCM, the strongest mode. This **understates** risk for ECB/CBC/short-key findings.
**Fix:** Map `"des"` to a canonical `"DES"` entry (add to classifier table) rather than aliasing it to 3DES; do not collapse all AES variants to AES-256-GCM. Distinguish at minimum AES-{128,256}-{GCM,CBC,ECB}.

---

### CR-04: Confidence score returns misleading 100% TLS-enum coverage when no TLS endpoints were scanned

**File:** `quirk/intelligence/confidence.py:82-83`
**Issue:**
```python
if tls_enum_coverage_ratio < 0.0:
    tls_enum_coverage_ratio = 1.0 if tls_count == 0 else 0.0
```
When `tls_count == 0` (e.g., a database-only scan), `tls_enum_coverage_ratio` defaults to `1.0`. Then `points_tls_enum = 100.0 * 0.20 * 1.0 = 20.0` is added to the confidence score. So a scan that contained zero TLS endpoints earns a **20-point confidence bonus for "perfect TLS enum coverage"** — meaningless, and inflates confidence on out-of-scope-TLS engagements.
**Fix:** When `tls_count == 0`, exclude `tls_enum_coverage_ratio` from the weighting entirely and renormalise the remaining weights to 1.0, or set the factor's contribution to 0 (not 1).

---

### CR-05: Trend analysis 1-second session window cannot disambiguate two scans in the same second

**File:** `quirk/intelligence/trends.py:84-99`
**Issue:** `_fetch_session_endpoints` filters `scanned_at >= target_ts AND scanned_at < target_ts + 1 second`. If a scan starts and another scan starts within 1 second, both populate the same window. Worse — if a single scan straddles a second boundary (rows in second N and second N+1), only one half is fetched. The docstring acknowledges the second-truncation grouping but the actual fetch is microsecond-strict against `target_ts`. If the caller passes `target_ts` truncated to the second but the rows have non-zero microseconds, those rows match — fine — but rows from the *next* whole second from the same logical scan will NOT match.

This violates the "one logical session per run" invariant for any scan that takes longer than ~1 second to commit endpoints (essentially every real scan).
**Fix:** Use `session_start` from `run_stats` or persist a `scan_id` foreign key on `CryptoEndpoint` so trend analysis groups by an explicit identifier rather than a temporal window. Short-term mitigation: store `session_start` as a field on every endpoint at insert time (already done as `scanned_at`) and group by `MIN(scanned_at)` per scan via a stored `session_id`.

---

### CR-06: Score subscores can sum > 100 because `agility_score` is computed independently and added unbounded

**File:** `quirk/intelligence/scoring.py:219`
**Issue:** `total_score = int(hygiene_score + modern_tls_score + identity_trust_score + agility_score + dar_score + motion_score)` — six subscores, each clamped to `[0, 25]`, sum max = 150. There is no clamp on the total. With ECDSA bonuses pushing agility_score back up to 25 and other subscores not penalized, the total can exceed 100.

Concretely: in a clean environment, each subscore = 25, total = 150. The `_rating` function classifies anything ≥ 85 as EXCELLENT, but the score itself is shown as "150/100" in `executive.py:158` and `report.html.j2` as "**150/100**". Consultant-grade output cannot ship a score > 100.
**Fix:** Either (a) clamp `total_score = min(100, max(0, total_score))`, or (b) renormalize subscores so their cap-sum is 100 (5 subscores × 20 each, or similar). Option (a) is the minimal fix; option (b) is the correct one and matches what the score band thresholds (85/70/55/35) imply.

---

### CR-07: Markdown injection / table-break in `technical.py` finding rows (and Vault subject CNs)

**File:** `quirk/reports/technical.py:40-44, 79-82, 90-97`
**Issue:** Every Markdown table row interpolates user-controlled fields (`e.host`, `cipher_suite`, `tls_supported_ciphers_sample`, `tls_enum_notes`, `f.get("description")`, `f.get("recommendation")`) directly into pipe-delimited table rows without escaping the `|` character or newlines.

A scan of a target whose certificate subject CN, server banner, or finding description contains `|` or `\n` will:
1. Break the table layout — downstream Markdown→PDF tooling will render misaligned rows.
2. Allow an attacker controlling a scanned target's banner/cert subject to inject arbitrary Markdown into the consultant deliverable. Combined with `markdown` → HTML conversion in any downstream tool, this becomes an XSS vector.

The same applies in `executive.py:215-217` where `item['title']` and `item['why']` are interpolated.
**Fix:** Add a `_md_cell(s)` helper that calls `s.replace("|", "\\|").replace("\n", " ")` before every cell interpolation. Apply at every row append.

---

## Warnings

### WR-01: PDF render uses blanket `except Exception` — silently masks programmer errors

**File:** `quirk/reports/html_renderer.py:127-128`
**Issue:** `render_pdf_report` returns `False` on any exception. This swallows out-of-disk, permission, browser-launch failures, and bugs identical-to-the-good-path. The caller (`writer.py:184-185`) treats this as "Playwright unavailable", but the cause may be a bug worth surfacing.
**Fix:** Catch only `(ImportError, playwright._impl._api_types.Error, OSError)` and log the exception cause via `logging.warning("PDF render failed: %s", exc)` so test logs show why.

### WR-02: PDF render does not clean up Playwright resources on inner-exception

**File:** `quirk/reports/html_renderer.py:115-126`
**Issue:** If `page.goto` or `page.pdf` raises, `browser.close()` is never called. The `with sync_playwright() as p:` context manager closes the playwright runtime but does not auto-close the browser. Each failed render leaks a Chromium process until the parent Python interpreter exits.
**Fix:** Wrap `page.pdf(...)` in a `try/finally` calling `browser.close()`, or use `with p.chromium.launch() as browser:` (Playwright 1.30+ supports this).

### WR-03: `motion_broker_weak_tls_count` predicate uses inconsistent uppercase tokens

**File:** `quirk/intelligence/evidence.py:241`
**Issue:** `if tls_v in {"TLSV1", "TLSV1.0", "TLSV1.1", "SSLV3"}:` — `tls_v = str(getattr(ep, "tls_version", "") or "").upper()`. The OpenSSL/sslyze conventions emit `"TLSv1"`, `"TLSv1.0"`, `"TLSv1.1"`, `"TLSv1.2"`, `"TLSv1.3"`, `"SSLv3"`. Uppercased these become `"TLSV1"`, `"TLSV1.0"`, `"TLSV1.1"`, `"SSLV3"` — match. However, some scanner backends emit `"TLS 1.0"` (with space) or `"TLS_1_0"`; these will not match. There is no normalization layer.
**Fix:** Normalize `tls_version` once at scanner ingestion to a canonical form (e.g., `TLSv1.0`), document the contract, and add a regression test parametrising over the dialect variants.

### WR-04: ECDSA detection in evidence.py mismatches cert_pubkey_alg conventions

**File:** `quirk/intelligence/evidence.py:127-131`
**Issue:** `key_alg.startswith("RSA")` and `key_alg.startswith("ECDSA")`. But cert_pubkey_alg from openssl X.509 typically reports `"id-ecPublicKey"`, `"EC"`, or `"prime256v1"` — not `"ECDSA"`. The cloud KMS normalizer in builder.py emits `"ECDSA"`, but TLS-derived rows do not. So `cert_key_type_counts["ECDSA"]` will undercount real EC certs from TLS scans, which then triggers `agility_rsa_only_penalty` when ECDSA is in fact deployed.
**Fix:** Add aliases: `key_alg.startswith(("ECDSA", "EC", "ID-ECPUBLICKEY", "PRIME256V1", "SECP"))`. Or normalize cert_pubkey_alg at scanner ingestion.

### WR-05: `_apply_weighted_impacts` uses fixed `score_cap=25.0` — not configurable per subscore

**File:** `quirk/intelligence/scoring.py:81-89`
**Issue:** Every subscore caps at 25. With 6 subscores × 25 = 150 (see CR-06). Also, the function rounds *individual* impact points to integers before summing the visible drivers, but uses unrounded floats for the score. Drivers shown to consultants (`-3, -2, -1`) may sum to a different total than the displayed score change. This is a transparency hole — BACK-63 was deferred.
**Fix:** Make `score_cap` derive from a `SUBSCORE_CAPS` dict (or compute as `100 / N_subscores` to guarantee additive normalisation). Recompute total as `sum(round(impact) for impact in ...)` so drivers reconcile.

### WR-06: SCORE_WEIGHTS sum is 261, not normalized

**File:** `quirk/intelligence/scoring.py:5-36`
**Issue:** Audit prompt expected SCORE_WEIGHTS to sum to 1.0; actual sum is 261.0. They are *absolute* per-ratio coefficients, not probabilities. This is a documentation gap (BACK-63), not a correctness defect by itself, but combined with CR-06 means the score's mathematical model has no documented invariant. Any future contributor adding a new ratio without understanding the cap-sharing in `_apply_weighted_impacts` will silently shift all scores.
**Fix:** Document the model (each subscore has a 25-point cap; impacts are negative ratios × weight; weights are calibrated heuristically; total_score = sum of subscores **clamped to 100**). Add a unit test that asserts `total_score <= 100` on a randomized evidence corpus.

### WR-07: Roadmap _why string-format produces double-period artifacts

**File:** `quirk/intelligence/roadmap.py:48-51`
**Issue:** `f"{base} Driver: {hint}."` — but `base` strings already end in periods (e.g., line 152: "...endpoint(s)."), and `hint` may also end in a period. Output: `"Plaintext HTTP signals were observed on 4 endpoint(s). Driver: Plaintext HTTP exposure.."`
**Fix:** `hint = hint.rstrip(".")` and assemble cleanly: `f"{base} Driver: {hint}."`.

### WR-08: Roadmap mutation-after-yield bug in `_add_candidate`

**File:** `quirk/intelligence/roadmap.py:54-80`
**Issue:** When a candidate with the same title already exists, the merge compares `_priority` and `phase` keys but the comparison key uses `existing["_priority"]` (could be int, but frozen as str via `int(...)`). The internal `_priority` field is never stripped from the public output (line 378-386: `final_items.append({...})` — verified, it IS stripped). OK, false alarm. But the helper writes a `_priority` key into the dict in `final_items` only via the explicit drop-set at line 378-386. The internal dict carries `_priority` until the explicit copy. Acceptable; downgrading to INFO. (Removing.)

Actually, the real issue: when two candidates collide, the comparison `new_key < old_key` chooses the lexically smaller phase-priority-title tuple — but `_PHASE_ORDER` maps NOW→0, NEXT→1, LATER→2. Adding a NOW with priority 10 over a NEXT priority 5 will replace the NEXT (correct). However, if two candidates share the same title across different code paths (e.g., a baseline item's title matches a custom item — unlikely but uncaught), the baseline (priority 900+) loses to the custom one. Probably intentional, but undocumented.
**Fix:** Add a docstring noting the "smaller key wins" merge rule and that titles are global keys.

### WR-09: `executive.py:_build_interpretation` accesses `score['score']` without KeyError protection

**File:** `quirk/reports/executive.py:30`
**Issue:** `f"Quantum Readiness Score is **{score['score']}/100** (**{score['rating']}**)."` — direct dict subscript. If `compute_readiness_score` ever returns a malformed dict (e.g., during a future refactor), this raises KeyError and the entire executive Markdown render fails. Other accesses use `.get(...)` defensively.
**Fix:** `score.get('score', 0)` and `score.get('rating', 'UNKNOWN')`.

### WR-10: `evidence.py` SAML weak detection uses startswith/equality on uppercased "SHA1" — fragile

**File:** `quirk/intelligence/evidence.py:158-161`
**Issue:** `if _saml_alg == "SHA1":` — strict equality on uppercase. The classifier table normalises to `"sha1"` (lowercase) but `cert_pubkey_alg` from the SAML scanner may emit `"SHA-1"`, `"http://www.w3.org/2000/09/xmldsig#rsa-sha1"`, or other forms. Single-form match means weakness goes uncounted.
**Fix:** `if "SHA1" in _saml_alg or "SHA-1" in _saml_alg:` and document the canonical form expected from the SAML connector.

### WR-11: `evidence.py` motion email weak-cipher predicate diverges from broker predicate (DES-CBC missing)

**File:** `quirk/intelligence/evidence.py:263-266 vs 244-250`
**Issue:** Broker predicate flags `3DES, RC4, DES-CBC, AES128-SHA, AES256-SHA` (sans ECDHE/DHE). Email predicate flags only `TLS_RSA_WITH_*, 3DES, RC4`. DES-CBC and the static-RSA AES-CBC-SHA suites are missed for email. Inconsistency means an SMTP server with `AES128-SHA` is "fine" but a Kafka broker with the same is "weak". Unjustified.
**Fix:** Define a single `_HIGH_RISK_CIPHER_PATTERNS` constant and use it from both call sites.

### WR-12: `_decompose_cipher_suite` returns wrong KEX for `RSA` non-PFS suites in TLS 1.2

**File:** `quirk/cbom/builder.py:136-142, 209-217`
**Issue:** `_KEX_MAP["RSA"] = "RSA"` is matched **after** ECDHE/ECDH/DHE/DH on line 212 (`first match wins`). For `TLS_RSA_WITH_AES_256_GCM_SHA384`, pre_tokens = `["RSA"]`, KEX="RSA", then auth-loop skips that token — but the auth-loop's logic relies on `kex_token_used` matching the same token, leaving auth empty. So a static-RSA suite emits one component (RSA-as-KEX) but no RSA-as-AUTH — it should ideally emit RSA twice (once each role) or annotate the dual role. Minor.
**Fix:** When KEX == AUTH (RSA), emit explicit `(KEX:RSA, AUTH:RSA)` or accept current behavior and document it.

### WR-13: `confidence.py` weight overrides bypass clamp and validation

**File:** `quirk/intelligence/confidence.py:46-49`
**Issue:** `weights` parameter accepts any float, including negatives or values > 1. A malicious config could set `coverage_ratio = -10.0` and produce a negative confidence score (clamp at line 91 saves the final score, but the factor_breakdown shows `points: -1000.0`). The breakdown is reported in JSON output.
**Fix:** `w[key] = max(0.0, min(1.0, _as_float(value)))` to bound weights.

### WR-14: `writer.py` PDF graceful degradation prints no warning to user

**File:** `quirk/reports/writer.py:183-185`
**Issue:** When `pdf_ok = False`, `pdf_path = None` silently; the user sees "Output files (10):" instead of 11 with no explanation. A consultant expecting a PDF wonders if the run failed.
**Fix:** Print a Rich-styled warning row in the summary table or emit `[yellow]PDF render skipped: Playwright not installed[/yellow]` after the file list.

---

## Info

### IN-01: Hardcoded `PLATFORM_VERSION = "4.4.0"` duplicated across modules

**Files:** `quirk/cbom/builder.py:127`, `quirk/reports/writer.py:23`
**Issue:** The comment in builder.py says "duplicated here to avoid circular imports". Two sources of truth invite drift. Project is currently at v4.7+ per planning artifacts. Both strings still say 4.4.0.
**Fix:** Move to `quirk/__init__.py` or `quirk/version.py` and import. Also bump to actual current version.

### IN-02: `_extract_ssh_algorithms` swallows JSONDecodeError silently

**File:** `quirk/cbom/builder.py:323-325`
**Issue:** Returns empty dict — caller cannot distinguish "no SSH data" from "corrupt SSH data". Coverage_gap finding would be appropriate.
**Fix:** Log a debug message; optionally append a coverage_gap advisory finding.

### IN-03: Trend analysis fetches all endpoints into memory per session

**File:** `quirk/intelligence/trends.py:90-99`
**Issue:** `.all()` on potentially-large session result. Out of v1 scope (perf), noted for awareness.

### IN-04: `evidence.py` _PROTOCOL_KEYS missing CONTAINER, SOURCE, AWS, AZURE, GCP, JWT, motion brokers

**File:** `quirk/intelligence/evidence.py:9-10`
**Issue:** `protocol_counts` dict has 14 keys; many real protocols (CONTAINER, SOURCE, AWS, AZURE, GCP, JWT, KAFKA-PLAIN, AMQP-PLAIN, REDIS-PLAIN, KAFKA-TLS, AMQPS, SMTPS, IMAPS, POP3S, *-STARTTLS, etc.) are not counted. The `if proto in protocol_counts` filter at line 114 silently drops them. Consultant-facing protocol counts under-represent scope.
**Fix:** Use a Counter (no whitelist) or expand the whitelist to cover every emitted protocol literal.

### IN-05: `roadmap.py` baseline items always include "Establish crypto governance review" but only when `len < min_items`

**File:** `quirk/intelligence/roadmap.py:323-362`
**Issue:** Baseline items act as filler when the evidence-driven candidates are thin. A scan with rich findings (≥ 6 candidates) never sees the governance review item, even though it's universally good advice. Probably intentional, undocumented.
**Fix:** Document or add a flag.

### IN-06: `executive.py` truncates "Recommended Migration Paths" at 10 with no "...and N more" indicator

**File:** `quirk/reports/executive.py:226-233`
**Issue:** Silent truncation. Consultants reading the markdown have no signal that more recs were available.
**Fix:** After loop: if `len(recs) > 10: lines.append(f"- _...and {len(recs)-10} more migration recommendations omitted; see findings.json_")`.

### IN-07: `html_renderer.py` `roadmap_section` matches both timeframe AND phase — title collision possible

**File:** `quirk/reports/html_renderer.py:79-80`
**Issue:** `r.get("timeframe") == tf or r.get("phase") == tf` — for tf="NOW", a roadmap item where timeframe="NOW" or phase="NOW" matches. But timeframe values are `"0-30 days"`, `"31-90 days"`, `"90+ days"` — they are never literally `"NOW"`. The OR branch is dead code.
**Fix:** Remove the timeframe comparison or align `_TIMEFRAME_BY_PHASE` values with phase keys.

### IN-08: `writer.py` `hosts_count` set comprehension uses `getattr(ep, "host", None) or getattr(ep, "target", "")` — falsy hosts collapse to single ""

**File:** `quirk/reports/writer.py:220`
**Issue:** Endpoints with `host = None` and no `target` attribute produce `""` and merge into one bucket; `hosts_count` undercounts. Also "target" attribute does not exist on `CryptoEndpoint`. Defensive-but-misleading.
**Fix:** `set(filter(None, (getattr(ep, "host", None) for ep in (endpoints or []))))`.

### IN-09: Schema dataclass `IntelligenceReport` defined but unused

**File:** `quirk/intelligence/schema.py` (entire file)
**Issue:** None of `writer.py`, `executive.py`, or downstream consumers import `IntelligenceReport`, `ScoreInputs`, `ScoreResult`, or `ConfidenceResult`. The actual JSON shape produced by `writer.py:138-158` is hand-rolled and does not match `IntelligenceReport.to_dict()`. Dead code or an aspirational type-stub. Either way, a maintainer reading `schema.py` will get a wrong picture of the on-disk format.
**Fix:** Either delete `schema.py` or wire `writer.py` to construct `IntelligenceReport` from the computed values and call `.to_json()`. Currently a documentation lie.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
