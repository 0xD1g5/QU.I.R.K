# Phase 32: Email Scanner - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver `quirk/scanner/email_scanner.py` — auditing TLS posture across the 7 standard email protocol ports (SMTP 25 / SMTPS 465 / SMTP submission 587 / IMAP 143 / IMAPS 993 / POP3 110 / POP3S 995). Persists results to a new `email_scan_json` SQLite column, surfaces a static `starttls-downgrade-risk` MEDIUM finding on port 25, and ships a `labs/email/` Postfix+Dovecot chaos lab profile. Broker scanning (Kafka/RabbitMQ/Redis) is **Phase 33** and explicitly out of scope here. Motion subscore wiring is **Phase 34**; CBOM integration is **Phase 35**; dashboard tab is **Phase 36**.

</domain>

<decisions>
## Implementation Decisions

### Target input UX
- **D-01:** Reuse the existing TLS target list verbatim — every host already passed via `--target` / target file is also probed on the 7 email ports.
- **D-02:** No new CLI flag for email targets. Scanner consumes the same target iterator that `scan_tls_targets` consumes, mirroring the v4.2 dnssec_scanner integration pattern.
- **D-03:** `CONNECTION_REFUSED` per port is non-fatal and silent (logged at DEBUG only) — port 25 egress is commonly blocked on cloud VMs (carry-forward from v4.2 / EMAIL-01 acceptance criterion).
- **D-04 (deferred):** MX autodiscovery (resolve `example.com` → MX hosts) is not in scope for Phase 32. If added later, it lives in `target_expander.py`, not in `email_scanner.py` — keeps DNS logic out of the scanner.

### Default profile inclusion
- **D-05:** Email scanning runs by default in the `standard` and `deep` profiles only. Excluded from `quick`.
- **D-06:** `quirk/engine/profiles.py:apply_profile()` must flip a config flag (e.g., `cfg.scanners.email_enabled = True`) for `standard` and `deep`. `quick` keeps it False to preserve fast triage time.
- **D-07:** Adding `--include-email` / `--no-email` override flags is **Claude's discretion** during planning — wire them only if the existing `apply_profile` pattern already exposes scanner-level overrides.

### Stdlib fallback trigger (EMAIL-07)
- **D-08:** Fallback to `smtplib` / `imaplib` / `poplib` is triggered when ANY of:
  1. sslyze raises an uncaught exception.
  2. `ServerScanResult.scan_status` is `ServerScanStatusEnum.ERROR_*`.
  3. Every `ScanCommandAttempt` in the result reports `ScanCommandAttemptStatusEnum.ERROR_*`.
- **D-09:** Empty/None cipher results without an explicit error status are interpreted as "TLS not supported on this port" and **do not** trigger fallback. This avoids redundant work on ports that legitimately have no STARTTLS (e.g., a hardened server returning a clean refusal at the protocol layer).
- **D-10:** Fallback function follows `tls_scanner.py:329 _scan_one_fallback` shape — extract TLS version + cipher + cert via `getpeercert(binary_form=True)` + existing `_pubkey_info()` helper. Reuse, do not re-implement.

### Findings composition
- **D-11:** Findings are **layered**, not merged. A port-25 endpoint with weak RSA cipher emits BOTH:
  - `starttls-downgrade-risk` MEDIUM (always on port 25 STARTTLS, regardless of cipher) — per EMAIL-08.
  - `weak-cipher` HIGH for `TLS_RSA_WITH_*` / 3DES / RC4 — per EMAIL-09.
- **D-12:** Each finding carries its own `finding_id` and remediation guidance. Dashboard de-duplication happens by `finding_id`, not by endpoint. Rationale: "enforce TLS" and "rotate ciphers" are distinct remediations consultants quote separately.
- **D-13:** Non-PFS ECDHE without TLS 1.3 = MEDIUM (per EMAIL-09 verbatim). No reclassification.

### Chaos lab layout
- **D-14:** New `labs/email/` directory — matches the v4.3 convention (`labs/storage/`, `labs/kubernetes/`, `labs/vault/`).
- **D-15:** Each service (Postfix, Dovecot) gets its own freshly generated self-signed RSA-2048 cert under `labs/email/certs/`. **Do not** reuse `certs/scenarios/` fixtures — keep the chaos lab decoupled from the legacy scenarios CA.
- **D-16:** Cert generation is reproducible from scratch: `labs/email/Makefile` (or the existing labs Makefile pattern) gains a `certs` target. CI / fresh checkouts can regenerate without a manual openssl invocation.
- **D-17:** Compose profile name = `email` (per EMAIL-11). Lives in the existing `labs/` compose structure used by `docker compose --profile {profile} up`.

### Claude's Discretion
- Exact internal helper organization inside `email_scanner.py` (one function per protocol vs. shared dispatcher); planner decides based on `tls_scanner.py` parallel structure.
- Logging verbosity per port-refused / per-fallback event — follow existing scanner logging conventions.
- `pyproject.toml [motion]` extras content for Phase 32: only `sslyze` (already present) and stdlib modules — no new direct deps required for email-only work. STRUCT-02 still requires the empty `[motion]` group be declared.
- Whether `email_scan_json` payload uses the same JSON shape as `tls_scan_json` or introduces a per-port nested structure — planner decides based on dashboard query needs (DASH-02 lives in Phase 36).

</decisions>

<specifics>
## Specific Ideas

- Mirror `tls_scanner.py` exactly — 4-function shape (`_scan_one_sslyze` → `_scan_one_fallback` → `scan_one` → `scan_email_targets`). User has explicitly carried this pattern forward across every scanner phase since v3.7.
- STARTTLS-stripping cannot be detected agentlessly — the port-25 `starttls-downgrade-risk` finding is *informational + advisory*, not a TLS-level test result. Make this explicit in the finding's `description` field so consultants can quote it correctly to clients.
- Postfix + Dovecot chaos-lab base = `ubuntu:22.04` (per EMAIL-11). Avoid `docker-mailserver` / `mailcow` — the user has explicitly excluded them as too heavy for our use case.
- Self-signed cert weakness profile (carry-forward from EMAIL-11): TLS 1.1 minimum, non-PFS RSA cipher suites (`AES128-SHA`, `AES256-SHA`), RSA-2048 key.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (locked)
- `.planning/REQUIREMENTS.md` §"Email Protocol Scanning" — EMAIL-00 through EMAIL-12 are LOCKED. Do not redefine.
- `.planning/REQUIREMENTS.md` §"Structural Requirements" — STRUCT-01 (`session_start` parameter), STRUCT-02 (`[motion]` extras at plan time), STRUCT-03 (`pyproject.toml` diff in PLAN.md).
- `.planning/ROADMAP.md` lines 487–498 — Phase 32 goal + 6 success criteria.

### Research (validated 2026-04-27)
- `.planning/research/email-tls-research.md` — sslyze `ProtocolWithOpportunisticTlsEnum` API, port conventions, chaos-lab Postfix+Dovecot rationale, classifier integration.
- `.planning/research/SUMMARY.md` — milestone-level synthesis covering the email + broker surfaces.

### Pattern templates (read before writing scanner code)
- `quirk/scanner/tls_scanner.py` — canonical 4-function shape. `_scan_one_sslyze` (line 103), `_scan_one_fallback` (line 329), `scan_one` (line 427), `scan_tls_targets` (line 452).
- `quirk/scanner/dnssec_scanner.py` — most recent scanner added under the v4.2 pattern; reference for `session_start` plumbing and target-list reuse.
- `run_scan.py` lines 395 (TLS) + 628 (DNSSEC) + 656 (Kerberos) — integration call site pattern that `scan_email_targets()` will mirror.
- `quirk/engine/profiles.py:apply_profile()` — where D-05/D-06 profile-toggle logic lands.

### Carry-forward decisions (from prior phases)
- v4.3 ISSUE-2 / ISSUE-3 patterns: STRUCT-01–03 are non-negotiable structural requirements. PLAN.md MUST include `pyproject.toml` diff.
- v4.2 dnssec_scanner integration pattern: scanner consumes shared target iterator; CONNECTION_REFUSED is silent.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/tls_scanner.py:_pubkey_info()` — extracts `(algorithm, key_size, modulus)` from a cert. Email scanner's stdlib fallback path (D-10) calls this directly on the SSLSocket peer cert.
- `sslyze.ProtocolWithOpportunisticTlsEnum.{SMTP, IMAP, POP3}` — research-confirmed, no subprocess/wrapper needed.
- `_scan_one_fallback` raw-socket pattern (tls_scanner.py:329) — port the structure to email; only the protocol-handshake step changes (`smtplib.starttls()` etc.).

### Established Patterns
- **Scanner shape:** `_scan_one_<api>` → `_scan_one_fallback` → `scan_one` → `scan_<surface>_targets`. Every scanner since v3.7 follows this. Email scanner MUST follow it.
- **`session_start` plumbing (STRUCT-01):** The shared `datetime` flows from `run_scan.py` → `scan_email_targets(targets, session_start, ...)` → all per-target work. No `datetime.now()` calls inside the scanner module.
- **Profile toggling:** `quirk/engine/profiles.py:apply_profile(cfg, profile, safe_mode)` mutates `cfg.scanners.*` flags. Add `email_enabled` flag, set True for standard/deep, False for quick.
- **Chaos lab layout:** `labs/<surface>/{docker-compose.yml | Dockerfile | certs/ | expected_results.md}`. Match this layout for `labs/email/`.

### Integration Points
- `run_scan.py` ~line 400 (after the existing `scan_tls_targets` call site) — new `scan_email_targets` call gated on `cfg.scanners.email_enabled`.
- `quirk/db/models.py` — add `email_scan_json` TEXT NULL column on the `Scan` model, mirroring `kerberos_scan_json` / `dat_scan_json` declarations.
- `quirk/cbom/classifier.py` — Phase 35 consumes `ep.protocol` labels (`SMTP-STARTTLS`, `SMTPS`, `IMAPS`, `POP3S`) from the endpoints we emit. Phase 32 must produce them in the format EMAIL-10 specifies; no Phase 32 changes to classifier.py.
- `quirk/engine/findings.py` (or equivalent) — register `starttls-downgrade-risk` and `weak-cipher` finding IDs.

</code_context>

<deferred>
## Deferred Ideas

- **MX autodiscovery from a domain** — would let `quirk scan example.com` automatically resolve and probe mail servers. Belongs in `target_expander.py` and likely a future v4.5 phase. Capture as a backlog idea.
- **`--include-email` / `--no-email` opt-in/opt-out CLI flags** — Claude's discretion during planning. If profiles cleanly express the same intent, skip the flags.
- **Active STARTTLS-stripping detection** — would require an in-path agent or a controlled MITM, which QU.I.R.K. is explicitly not (consulting-grade agentless scanner). Document as out-of-scope in the finding's description; never implement.
- **Per-broker scanning (Kafka / RabbitMQ / Redis / Azure Service Bus / AWS SQS)** — Phase 33.
- **`motion_` evidence counters and scoring** — Phase 34.
- **CBOM integration for email/broker endpoints** — Phase 35.
- **Dashboard `/motion` tab** — Phase 36.

</deferred>

---

*Phase: 32-email-scanner*
*Context gathered: 2026-04-27*
