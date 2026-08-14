# Phase 152: Discovery Empirical Closure - Context

**Gathered:** 2026-08-13
**Status:** Ready for planning
**Mode:** Autonomous smart-discuss (batch proposals, all accepted as recommended)

<domain>
## Phase Boundary

The Phase 144 nmap adaptive RTT/timing-engine artifact (an accepted VERIFICATION override from
v5.11 — real open ports possibly suppressed on a mostly-silent host batch) is settled empirically
against a realistic segmented network, instead of remaining an open question forever. A new chaos
lab profile provides that realistic segment. Interactive setup's nmap-discovery prompt defaults to
Yes so users get the recommended discovery path without opting in explicitly. Out of scope:
rewriting `nmap_provider.py`'s adaptive timing engine wholesale, real physical hardware testing,
and any change to the chunked-discovery architecture itself (Phase 144/145/146 territory, already
shipped).

</domain>

<decisions>
## Implementation Decisions

### Segmented-Network Lab Profile Design
- Two-subnet routed topology: a "live" subnet with real services and a "dead" subnet behind a
  gateway container that REJECTs TCP (RST) and answers ICMP-unreachable for dead hosts, built via
  a custom Docker bridge + iptables rules — genuinely reproduces routed-segment RST/ICMP-unreachable
  behavior, unlike unassigned loopback aliases.
- Host count: a scaled-but-representative segment (~50-100 hosts) — enough to trigger nmap's
  adaptive RTT/timing engine without an impractical container count. Document explicitly as a
  scaled reproduction of the original ~1024-host batch, not a 1:1 replica.
- Profile name: `segmented-network` — matches `lab.sh`'s existing single-word profile naming
  convention (`tls-modern`, `otics`, etc.).
- Live-side services: reuse existing lab services (e.g. `tls-modern`, an ssh profile container) on
  the live subnet so discovery has real ports to find, rather than inventing new dummy services.

### Timing-Artifact Resolution Methodology
- "Reproduces" is defined strictly as the same failure mode as the original: real open ports on
  live hosts missed/suppressed by adaptive RTT/timing throttling during chunked discovery,
  confirmed by diffing chunked-discovery output against a direct nmap run of the same segment.
  Any other kind of missed port does not count as reproduction.
- The finding is written to a dedicated `152-DISC09-FINDING.md` in the phase directory, plus a
  cross-reference update in `.planning/STATE.md`'s deferred-items ledger and
  `.planning/milestones/v5.11-MILESTONE-AUDIT.md`'s tech-debt block — closing the loop explicitly
  rather than leaving it only in a phase-local file.
- Run the verification scenario at least 3 times before declaring closed or confirmed, to rule out
  timing-variance flakiness.
- Test environment is the Docker Compose chaos lab (today's oracle standard for this project) —
  Docker bridge networking + iptables REJECT genuinely produces RST/ICMP-unreachable behavior.
  Real hardware/VM testing is explicitly out of scope for this phase (the audit flagged it as
  ideal-but-not-required; Docker bridge networking is judged sufficient to settle the question).

### Mitigation Scope (conditional on reproduction)
- If the artifact reproduces: implement the timing-template/RTT-bound tuning already flagged as
  the known alternative in `nmap_provider.py`, scoped conservatively to the silent-batch detection
  heuristic — NOT a blanket global timing-engine change — to avoid the false-negative tradeoff on
  slow real networks that the v5.11 audit explicitly called out as a risk.
- If the artifact does NOT reproduce: close the deferred item outright with a written closure
  note; remove the override-acceptance framing from STATE.md/audit references since it is no
  longer an open risk, rather than leaving stale "accepted override" language in place.

### Interactive Default Flip Scope
- Flip `_prompt_bool("Run nmap port discovery first? (recommended for >10 hosts)",
  default=False)` in `quirk/interactive.py` (~line 176) to `default=True`. Preserve the existing
  single global toggle behavior (D-06, already locked: one global y/N prompt, NOT per-target) —
  this phase does not reopen that architecture decision.
- No prompt copy change — "(recommended for >10 hosts)" already exists and now matches the new
  default; no redundant wording to clean up.
- No UI-SPEC / `ui-phase` needed — this is a CLI prompt-default change, not a dashboard/GUI
  component. The phase's "UI hint" refers to the CLI interactive flow, not a web UI surface.
- Add or update an `interactive.py` unit test asserting the new `default=True` value directly, so
  a future edit can't silently flip it back without a test failure.

### Claude's Discretion
- Exact Docker Compose service/network naming inside the `segmented-network` profile (container
  names, subnet CIDRs, iptables rule specifics) — follow existing lab conventions, check
  `docker-compose.yml` for naming patterns before choosing.
- Exact diffing mechanism for comparing chunked-discovery output against a direct nmap run (script
  vs. manual comparison) — whichever produces the clearest evidence for `152-DISC09-FINDING.md`.
- Whether the RTT-bound tuning mitigation (if needed) lives in `nmap_provider.py` directly or as a
  new small helper — follow existing code organization in that file.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quantum-chaos-enterprise-lab/lab.sh` — existing profile registration pattern
  (`ALL_PROFILES`/`PROFILE_ARGS`) to extend for the new `segmented-network` profile.
- `quantum-chaos-enterprise-lab/docker-compose.yml` — existing service definitions (e.g.
  `tls-modern`) to reuse on the live subnet rather than inventing new dummy services.
- `quirk/interactive.py` — existing `_prompt_bool()` helper and D-06's single global toggle
  pattern at the nmap-discovery prompt (~line 176-179).

### Established Patterns
- Chaos lab profiles are documented in three places per `CLAUDE.md`'s Chaos Lab Maintenance rule:
  `lab.sh` (`ALL_PROFILES`), `docs/chaos-lab.md` (new section), and an `expected_results_*.md`
  oracle file — all three must be updated in the same change.
- `.planning/STATE.md` "Deferred Items" section is the existing ledger pattern for tracking
  accepted-but-unresolved items like the Phase 144 nmap timing artifact.

### Integration Points
- `nmap_provider.py` — where the adaptive RTT/timing engine lives; the conditional mitigation (if
  the artifact reproduces) integrates here.
- `docs/chaos-lab.md`, `README.md`, `expected_results_*.md` — must all reflect the new
  `segmented-network` profile in the same change per CLAUDE.md.

</code_context>

<specifics>
## Specific Ideas

No specific implementation references beyond the recommended package above — all four grey areas
were accepted as proposed with no user modifications.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Real hardware/VM testing was explicitly considered
and deliberately deferred as out of scope for this phase (Docker bridge networking judged
sufficient), not deferred as a future phase idea.

</deferred>
