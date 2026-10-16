---
type: todo
created: 2026-10-15
source: Phase 229 (Finding & State Correctness) D-06
priority: medium
area: quirk/intelligence/scope_signature.py (tls family disabled_extra)
status: pending
resolves_phase: null
owner: "999.138"
---

# Fast-mode scans cannot close any TLS finding

**Owner:** 999.138 (Fast-mode TLS closure evidence)

`quirk/intelligence/scope_signature.py:293` disables the tls probe family unless `tls_enum_mode == "deep"`, so a fast-mode rescan reports the family as not run and a TLS finding on that endpoint stays open. `tests/test_closure_state_model_e2e.py::test_tls_fast_mode_refuses_fixed_host` pins this. Plaintext HTTP findings can close.

- [ ] Decide which fast-mode handshake evidence may count as a TLS recheck (operator decision).

## Feasibility & Effort

- **CONFIRMED** by scope_signature.py:293 and the e2e test above. Effort **M**. Unknown: which fast-mode fields prove a cipher or version finding fixed. Spike: yes, compare fast and deep on the chaos lab.
