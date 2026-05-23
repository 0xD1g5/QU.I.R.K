# Phase 90: OQS-nginx PQC-Hybrid - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Give the quantum-readiness scoring model a concrete, demoable **post-quantum ceiling anchor**: a digest-pinned `openquantumsafe/nginx` chaos-lab profile serving an **X25519MLKEM768** hybrid TLS endpoint; the scanner observes and classifies it (genuine `quantum-safe` CBOM component when detectable, scoped advisory otherwise); and the scoring model rewards PQC-hybrid posture with an `agility` bonus so a PQC-hybrid endpoint scores above an equivalent classical-TLS-only target (PQC-01/02/03).

**Not in scope:** full native PQC-hybrid detection via an OQS-compiled sslyze/nassl (deferred to v5.1 per REQUIREMENTS non-goals); a score-engine redesign (the v4.10.1 surgical model holds — PQC-03 adds ONE bonus weight, not a rebalance); PQC **signature** (ML-DSA / certificate) scoring (see Deferred — observed but out of scope).
</domain>

<decisions>
## Implementation Decisions

These decisions are grounded in a **live empirical spike run during this discussion** (2026-05-22) against the pinned OQS-nginx image. The raw observations are recorded under `<code_context>` → "Spike findings (empirical)".

### PQC-02 — Detection strategy (the pre-locked empirical decision)
- **D-01 — Genuine raw `openssl s_client` probe, capability-gated, with an advisory fallback. NOT an sslyze-based detection.**
  - **Why not sslyze:** the project's existing TLS path uses sslyze→nassl, which bundles its **own old OpenSSL**. Against the hybrid endpoint sslyze returns `ServerScanStatusEnum.ERROR_NO_CONNECTIVITY` ("could not find a TLS version and cipher suite supported by the server") — it cannot even complete the handshake. Detection MUST be a **separate probe**, not an sslyze scan-command extension.
  - **The probe:** shell to the host `openssl s_client -connect <host:port> -groups X25519MLKEM768` (TLS 1.3). If the handshake **succeeds**, the server supports the PQC-hybrid group → emit a genuine `quantum-safe` CBOM component and increment `pqc_hybrid_endpoint_count`. Parse `Negotiated TLS1.3 group: X25519MLKEM768` from output to confirm.
  - **False-positive-free discriminator (verified in the spike):** offering ONLY `X25519MLKEM768` succeeds against the PQC server but FAILS against a classical-only server (control: lab `tls-modern:443`). A classical endpoint can never pass this probe, so a success is an unambiguous PQC-hybrid signal.
  - **Capability gate + advisory fallback:** the probe requires host OpenSSL ≥ 3.5 (native ML-KEM). Detect capability first (e.g. `openssl list -kem-algorithms`/group support, or a feature probe). If the host OpenSSL is too old to offer `X25519MLKEM768`, the probe cannot negotiate even against a real PQC server → emit the **scoped ADVISORY** finding documenting that full detection needs OpenSSL ≥3.5 / OQS-compiled tooling, while still incrementing `pqc_hybrid_endpoint_count` so PQC-03 scoring works (see D-05). This is graceful degradation, not a hard dependency.
  - **Do NOT use Python stdlib `ssl.set_ecdh_curve()`** for this — it rejects the hybrid group name ("unknown elliptic curve name 'X25519MLKEM768'") even on OpenSSL 3.6. The `openssl` subprocess is the mechanism.

### PQC-01 — Image, digest, endpoint
- **D-02 — Pin `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870`** (built 2026-05-18). Verified in the spike to serve, on its default config, a TLS 1.3 endpoint negotiating **`X25519MLKEM768` (NamedGroup 4588)** with an **ML-DSA-65 (Dilithium)** certificate. Never `:latest` — group names rename across oqs-provider releases (PQC-01, pre-locked).
  - **Group string target:** `X25519MLKEM768` (the NIST-standardized ML-KEM name, NamedGroup 4588) — NOT the legacy `X25519Kyber768`. The image serves the standardized group out of the box.
  - **CBOM mapping:** `quirk/cbom/classifier.py:66` already has `"mlkem768x25519-sha256": (CryptoPrimitive.KEM, 3, 192)` (KEM, NIST level 3). The detected group `X25519MLKEM768` must map to this existing classifier key — verify/add the alias so the genuine component lands at NIST L3 (no new classifier table churn beyond an alias if needed).
  - **Port:** researcher/planner picks a non-colliding lab port (research draft suggested `25443`; lab convention now trends to the `39xxx` range — grpc-tls=39443, kafka=39093). Confirm no collision against `docker-compose.yml` before assigning.
  - **nginx config:** the default image config already negotiates the hybrid; the lab profile may pin `ssl_ecdh_curve X25519MLKEM768` explicitly in nginx.conf for determinism.

### PQC-03 — Scoring (agility bonus)
- **D-03 — New `pqc_hybrid_endpoint_count` evidence counter (`quirk/intelligence/evidence.py`) + a new `agility` bonus weight in `SCORE_WEIGHTS` (`quirk/intelligence/scoring.py`).**
  - **Magnitude:** make PQC-hybrid the clear **top agility signal** — at least on par with, ideally exceeding, the existing positive bonuses (`agility_has_ecdsa_bonus = 4.0`, `identity_mtls_ratio_bonus = 6.0`). Recommended starting point ≈ **+8.0** so a PQC-hybrid endpoint visibly outscores "good classical TLS" on agility. Planner confirms exact value.
  - **Orthogonal-model constraint (Phase 88):** subscores are orthogonal, capped at `/25` per pillar; the bonus lifts the **agility** subscore toward 25 and MUST be clamped so it cannot push agility > 25. It does not alter the other five pillars.
  - **Invariant gate:** `tests/test_score_weights_invariant.py` asserts BOTH `sum == 275.0` AND `len == 36`. Adding one weight makes it 37 weights / `275.0 + bonus`. **Update both assertions** in the same change (the test is the CI gate that will otherwise fail).

### PQC-02/03 — Demo / oracle framing
- **D-04 — Demoable before/after is the deliverable hook.** `expected_results_v4.md` gets a `## Profile: oqs-nginx` section documenting: pinned digest, group `X25519MLKEM768` (NamedGroup 4588), the ML-DSA-65 cert, the genuine `quantum-safe` CBOM component (or advisory on old-OpenSSL hosts), and the **agility uplift vs. an equivalent classical-TLS-only scan**. CLAUDE.md lab-sync obligations apply in the same commit: `docker-compose.yml` + `lab.sh` (auto-derives — confirmed by Phase 89) + README profile table + `expected_results_v4.md`.

### PQC-02 — Counter semantics under advisory fallback
- **D-05 — `pqc_hybrid_endpoint_count` increments on a confirmed PQC-hybrid endpoint regardless of which surface (genuine component vs advisory) was emitted.** The scoring agility bonus reads the counter, so PQC-03 works on both modern-OpenSSL hosts (genuine component) and old-OpenSSL hosts (advisory). The advisory path documents the detection limitation but still credits the posture.

### Claude's Discretion
- Exact lab port (collision-checked), the precise capability-probe mechanism for "OpenSSL ≥3.5", the exact bonus value (within the D-03 guidance), whether to add an explicit `ssl_ecdh_curve` pin to nginx.conf, and where the raw-probe helper lives (new small module vs. extension of the TLS scanner path, kept OUT of the sslyze flow per D-01).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` — PQC-01, PQC-02, PQC-03 (and the non-goals: OQS-compiled sslyze deferred, no score-engine redesign).
- `.planning/ROADMAP.md` — Phase 90 goal + success criteria; Phase 90 depends on Phase 88 (SCORE_WEIGHTS stability — now satisfied, 88 complete).
- `.planning/research/ARCHITECTURE.md` §"BACK-81 — oqs-nginx PQC-hybrid" (lines ~167–196) and §"OQS-nginx — Last (architectural scope)" (~437) — blast radius + the `agility_pqc_hybrid_bonus` strategy. NOTE: research drafted around `X25519Kyber768`; the empirical spike supersedes that with the standardized `X25519MLKEM768`.

### Code touchpoints
- `quirk/cbom/classifier.py:66` — existing `mlkem768x25519-sha256` KEM/NIST-3 entry (the CBOM mapping target for the detected group).
- `quirk/intelligence/evidence.py` — add `pqc_hybrid_endpoint_count`.
- `quirk/intelligence/scoring.py` — `SCORE_WEIGHTS` (sum invariant 275.0/36; positive bonuses at L30, L57); add the `agility` PQC bonus.
- `tests/test_score_weights_invariant.py` — update BOTH the sum (275.0) and count (36) assertions.
- `quirk/scanner/tls_scanner.py` — existing sslyze path (for context: it CANNOT see the hybrid; the new probe is separate, not an extension of this).

### Rules
- `./CLAUDE.md` — Chaos Lab Maintenance rule (lab.sh + README + expected_results_v4.md in the same change); PEP 8; minimal diffs; `python -m compileall` + tests after changes; staleness rules don't apply here.
</canonical_refs>

<code_context>
## Existing Code Insights

### Spike findings (empirical — 2026-05-22, against the pinned digest)
- **sslyze (nassl bundled OpenSSL):** `ERROR_NO_CONNECTIVITY` — cannot handshake against the hybrid endpoint at all. The genuine-detection path therefore canNOT be sslyze.
- **Host OpenSSL 3.6.2** (`openssl s_client -groups X25519MLKEM768`): SUCCESS — `Negotiated TLS1.3 group: X25519MLKEM768` (NamedGroup 4588), `Peer signature type: mldsa65`, `TLS_AES_256_GCM_SHA384`, TLS 1.3. `-trace` confirms the key_share NamedGroup 4588.
- **Discriminator control:** the hybrid-only probe FAILS against classical lab server `tls-modern:443` → no false positives.
- **Python stdlib `ssl.set_ecdh_curve('X25519MLKEM768')`:** raises "unknown elliptic curve name" even on OpenSSL 3.6 → stdlib `ssl` cannot drive the group; use the `openssl` subprocess.
- **Bonus PQC signal:** the endpoint serves an **ML-DSA-65 (Dilithium)** certificate — independent post-quantum signature signal (see Deferred).

### Reusable Assets
- `quirk/cbom/classifier.py` `_ALGORITHM_TABLE` already maps an MLKEM768x25519 KEM at NIST L3 — reuse, don't re-table.
- The chaos lab's auto-derived `lab.sh profiles` (confirmed Phase 89) — new profile needs no `ALL_PROFILES` edit.
- Existing positive-bonus pattern in `SCORE_WEIGHTS` (`agility_has_ecdsa_bonus`, `identity_mtls_ratio_bonus`) — the PQC bonus follows the same evidence-counter→weight shape.

### Established Patterns
- Forward-locking invariant test (`test_score_weights_invariant.py`) gates any SCORE_WEIGHTS change — update sum + count atomically.
- Phase 88 orthogonal `/25`-per-pillar scoring — the bonus lifts agility, clamped at 25.
- Capability-gated graceful degradation (cf. Phase 89's optional-extra/loopback handling) — probe when the host can, advisory when it can't.

### Integration Points
- New raw-probe helper → `evidence.py` counter → `scoring.py` agility bonus → report surfaces + `expected_results_v4.md` oracle.
</code_context>

<specifics>
## Specific Ideas

- Pinned image: `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870`.
- Target group: `X25519MLKEM768` (NamedGroup 4588), standardized ML-KEM name.
- Probe command shape: `openssl s_client -connect <host:port> -groups X25519MLKEM768` → parse `Negotiated TLS1.3 group:`.
- Demo angle: classical-TLS-only scan vs. oqs-nginx scan → visibly higher agility subscore (consulting deliverable).
</specifics>

<deferred>
## Deferred Ideas

- **PQC certificate-signature scoring (ML-DSA-65 / Dilithium).** The endpoint also presents a PQC-signed cert — a real, separate post-quantum signal. Scoring/cataloguing PQC *signatures* (vs. the KEX group) is a new capability beyond PQC-01/02/03's KEX-group focus → future phase / v5.1.
- **Native OQS-compiled sslyze/nassl detection.** Already a documented non-goal (REQUIREMENTS) — deferred to v5.1; the raw-probe approach (D-01) is the stabilization-milestone-appropriate path.
- **Multiple hybrid groups (e.g., MLKEM1024, P-384 hybrids).** This phase anchors on X25519MLKEM768 as the demoable ceiling; broader group coverage is future work.

### Reviewed Todos (not folded)
None — no matching todos for this phase (`todo.match-phase 90` → 0 matches).
</deferred>

---

*Phase: 90-oqs-nginx-pqc-hybrid*
*Context gathered: 2026-05-22*
