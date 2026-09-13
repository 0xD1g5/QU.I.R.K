---
type: todo
created: 2026-09-12
source: phase-202 operator walkthrough on the live dashboard (real-data observation)
priority: medium
requirement: none (copy/honesty refinement on a shipped, operator-approved surface)
---

# Absence case A1's copy asserts a property of the FINDING ("not mapped to a remediation theme") where for an *unbridged* title the honest statement is about our JOIN ("we cannot determine its theme")

**Found 2026-09-12** during the phase 202 operator walkthrough against the canonical DB. The operator
read the live drawer and reported seeing:

> SCORE-LIFT ATTRIBUTION
> Not mapped to a remediation theme — no score-lift attribution exists for this finding.

That string is correct for the state the code is in, and it reads as intentional rather than broken
(which is what the walkthrough was verifying — it passed). The nuance is that **A1 is currently used for
two materially different facts**:

1. **The title bridges fine, but `slug_for_title()` returns `None`** → the finding genuinely belongs to
   no remediation theme. "Not mapped to a remediation theme" is exactly true.
2. **The title is `unbridged`** (in `UNBRIDGED_DASHBOARD_TITLES`) → the dashboard's title has no 1:1 CLI
   counterpart, so the join is never attempted at all. 202-05 proved `compute_fingerprint` is never
   called in this branch. Here we have **not established** that the finding lacks a theme — we have
   established that we cannot resolve which theme it would be.

Saying "not mapped to a remediation theme" in case 2 makes a claim about the finding that the system has
not earned. It is the same conflate-two-facts-into-one-string pattern the UI checker caught twice while
reviewing `202-UI-SPEC.md` (the position/closure line, and the counts-unavailable copy reusing A2's
string) — caught there before shipping, missed here.

## Why this is worth acting on rather than filing and forgetting

It is not a rare edge case on real data. On the canonical DB (`./quirk-output/quirk.db`, 4 findings) at
the time of the walkthrough, **every finding hit this path**:

- `Weak cipher suites enabled` ×2 — `unbridged` (fires on `ep.tls_weak_ciphers_present`; the CLI's
  nearest title fires on `tls_legacy_suites_present` — not 1:1, so deliberately unbridged by 202-01)
- `Quantum-vulnerable algorithm: ECDSA` — the `Quantum-` dynamic family, also `unbridged`

So the operator's whole real-data experience of this feature is a string that slightly overclaims. That
is the opposite of the D-07 posture the phase adopted everywhere else.

## Fix shape

Split A1 into two states with distinct copy, the way A2/A3 were already split:

- **A1a — no theme (join succeeded, no match):** keep the current sentence; it is accurate.
- **A1b — theme undeterminable (title unbridged):** say so, e.g. *"This finding's type isn't linked to a
  remediation theme in this build, so no score-lift can be attributed to it."* — a statement about the
  linkage, not about the finding.

The backend already distinguishes the two cases (an unbridged title short-circuits before
`compute_fingerprint`), so this needs a new response discriminator rather than new inference — likely one
extra nullable field, not a logic change. Add the state to `202-UI-SPEC.md`'s State Matrix so the
precedence is contract rather than accident, and pin it with a test per the phase's existing pattern.

## Acceptance

- The two cases render distinguishable copy, both greppable.
- The State Matrix documents the new state and its precedence against A2/A3.
- A test seeds an unbridged title and asserts the A1b string, and another seeds a bridged-but-unmatched
  title and asserts the A1a string — neither passes if the discriminator is dropped.
- No new inference: the discriminator comes from the existing short-circuit, not from guessing.
