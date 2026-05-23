---
phase: 90
slug: oqs-nginx-pqc-hybrid
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-22
updated: 2026-05-22
---

# Phase 90 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from 90-VERIFICATION.md success signals (verified 2026-05-22, score 9/9).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (venv) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `QUIRK_DB_PATH=/tmp/quirk90.db python -m pytest tests/test_pqc_probe.py tests/test_pqc_cbom_component.py tests/test_pqc_agility_bonus.py tests/test_pqc_discriminator.py tests/test_score_weights_invariant.py -x -q` |
| **Full suite command** | `QUIRK_DB_PATH=/tmp/quirk90.db python -m pytest tests/ -q` |
| **Estimated runtime** | ~30–60 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above.
- **After every plan wave:** Run the full suite command.
- **Before completion:** Full suite green; 9/9 VERIFICATION.md truths verified.

---

## Observable Success Signals

| Signal | Command | Expected |
|--------|---------|----------|
| oqs-nginx chaos lab profile starts | `docker compose --profile oqs-nginx up -d` | Container up, port 39444 accessible |
| X25519MLKEM768 TLS endpoint served | `openssl s_client -groups X25519MLKEM768 -connect localhost:39444` | `Negotiated TLS1.3 group: X25519MLKEM768` |
| CBOM emits KEM component | `pytest tests/test_pqc_cbom_component.py -v` | 11 tests PASS |
| PQC probe unit tests | `pytest tests/test_pqc_probe.py -v` | 19 tests PASS |
| Agility bonus scoring | `pytest tests/test_pqc_agility_bonus.py -v` | PASS |
| Score invariant (sum=283.0, len=37) | `pytest tests/test_score_weights_invariant.py -v` | PASS |
| lab.sh auto-derives oqs-nginx profile | `./lab.sh profiles` | includes `oqs-nginx` |

---

## Per-Task Verification Map

| Task ID | Plan | Requirement | Threat Ref | Automated Command | Status |
|---------|------|-------------|------------|-------------------|--------|
| 90-01-* | 01 (oqs-nginx lab) | PQC-01 | — | `pytest tests/test_pqc_probe.py -v` | complete |
| 90-02-* | 02 (PQC probe) | PQC-02 | — | `pytest tests/test_pqc_probe.py tests/test_pqc_discriminator.py -v` | complete |
| 90-03-* | 03 (CBOM component) | PQC-03 | — | `pytest tests/test_pqc_cbom_component.py -v` | complete |
| 90-04-* | 04 (scoring bonus) | PQC-03 | — | `pytest tests/test_pqc_agility_bonus.py tests/test_score_weights_invariant.py -v` | complete |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify
- [x] Wave 0 gaps resolved (lab profile, probe module, CBOM classifier entry)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] VERIFICATION.md score: 9/9 (re-verified after gap closure commits f861dc6 + ee0e192)

**Approval:** complete (sourced from 90-VERIFICATION.md — verified 2026-05-22)
