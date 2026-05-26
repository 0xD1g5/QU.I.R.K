# Phase 112: Distributed Chaos-Lab + Stabilization - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

The final v5.4 phase. It (1) builds a **multi-segment chaos-lab topology** that validates the
distributed flow end-to-end (enroll → scan-local → push → merge → one CBOM + one score) and
physically reproduces the same-IP-in-two-segments scenario (LAB-01/02); (2) keeps the lab tooling
drift-free per the CLAUDE.md chaos-lab rule (lab.sh + README + expected-results oracle, LAB-03);
and (3) closes out v5.4 stabilization — the operators-guide distributed workflow + Windows install
(STAB-01) and dependency hygiene + complete UAT-SERIES coverage for phases 106–112 (STAB-03).

**Note on verification:** LAB-01/LAB-02 require *running* a multi-container Docker stack with two
networks — that live run is **human-UAT** (this phase produces everything runnable; the operator
executes the live E2E). Automated coverage = `docker compose config` validation + a static topology
test + the existing Phase 110 unit MERGE-03 regression.

</domain>

<decisions>
## Implementation Decisions

### Distributed Lab Topology (LAB-01 / LAB-02)
- **Separate `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`** — the explicit-network /
  overlapping-subnet topology is structurally different from the existing port-mapped single-network
  lab; keeping it separate avoids polluting the main compose and its `ALL_PROFILES` sweep.
- **Two explicit bridge networks** `segment-a` and `segment-b`, **each with the SAME subnet
  `10.10.0.0/24`** (overlapping RFC1918) — this is what makes MERGE-03 reproducible.
- **Same static IP (e.g. `10.10.0.10`) assigned to a crypto target in BOTH networks**, so the two
  per-segment sensors report an identical `host:port` that must yield two distinct CBOM components.
- Crypto targets reuse the existing nginx TLS images; at least one target per segment.
- **One sensor container per segment** (installs the repo via `pip install`, runs
  `quirk sensor enroll`/`push`) + **one console container** running `quirk serve`.

### E2E Orchestration & Oracle (LAB-03)
- **`quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`** orchestrates
  enroll → scan-local → push → merge, invoked via a new **`lab.sh distributed`** command pointing at
  the separate compose file.
- **No drift (CLAUDE.md rule):** `ALL_PROFILES` continues to cover every profile in the MAIN
  `docker-compose.yml`; the distributed topology is its own `lab.sh distributed` command (separate
  file) and is documented as such — `lab.sh status`/`logs` must work cleanly against it.
- **New `expected_results_distributed.md` oracle** documenting the two networks, services/ports,
  the same-IP→two-components expectation, and the one-CBOM/one-score outcome.
- **Update the chaos-lab `README.md`** with the distributed profile (networks, services, expected
  findings).

### Verification Approach
- The phase delivers everything runnable; the **live multi-container `enroll→push→merge` run
  (LAB-01/02) is human-UAT** — consistent with the deferred live items from Phases 108/110/111.
- **Automated coverage:** `docker compose -f docker-compose.distributed.yml config` validates the
  topology; a static test asserts the two networks share a subnet AND the same-IP target is assigned
  in both; the Phase 110 unit MERGE-03 regression already proves the merge logic.

### Docs & Dependency Hygiene (STAB-01 / STAB-03)
- **`docs/operators-guide.md`:** add the full distributed workflow (enroll → push → merge) +
  **Windows sensor installation steps**; close the all-configurations/settings coverage gap (backlog
  999.59).
- **`docs/UAT-SERIES.md`:** ensure series cover **all v5.4 phases 106–112** (108–111 were added during
  their phases; add 106/107/112).
- **Dependency hygiene:** audit `pyproject.toml` — confirm `platformdirs`, `tenacity`, `zstandard`
  are pinned and in the correct dependency group; **resolve the `datetime.utcnow()` deprecation
  warnings** flagged across `sensor_cmd.py` (and any sibling sensor/merge modules) — replace with
  `datetime.now(timezone.utc)`.
- **Obsidian sync** of operators-guide + UAT-SERIES + the final Phase 112 note.

### Claude's Discretion
- Exact subnet/IP numbers, container image base, and how the sensor container installs the repo
  (editable install vs wheel) — as long as two networks overlap and a target shares an IP across them.
- Whether `distributed-e2e.sh` polls for readiness or uses fixed sleeps; the precise `lab.sh`
  subcommand surface.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quantum-chaos-enterprise-lab/docker-compose.yml` (1315 lines, port-mapped nginx TLS services, no
  explicit networks) — reuse the nginx TLS service definitions as the per-segment crypto targets.
- `quantum-chaos-enterprise-lab/lab.sh` — `_profiles`/`ALL_PROFILES` build (~L131-157); add a
  `distributed` command. Darwin Kerberos-skip pattern shows how commands branch.
- `quantum-chaos-enterprise-lab/expected_results_v4.md` — the oracle format to mirror for
  `expected_results_distributed.md`.
- `quantum-chaos-enterprise-lab/scripts/` — where `distributed-e2e.sh` lives.
- `quirk sensor enroll/push/merge` (Phases 108/110) + `quirk console enroll` + `POST /api/sensor/push`
  (Phase 109) + `quirk serve` — the binaries the containers run.
- `docs/operators-guide.md`, `docs/UAT-SERIES.md` — the docs to extend.

### Established Patterns
- CLAUDE.md chaos-lab maintenance rule: any profile/port/service change updates lab.sh ALL_PROFILES
  + README + expected_results oracle in the same change.
- Phase 110 unit MERGE-03 regression (`tests/test_cbom_builder.py` two-sensor test) is the logic proof;
  this phase adds the physical reproduction.

### Integration Points
- Sensor containers hit the console container's `POST /api/sensor/push` over the lab network; console
  runs the Phase 110 `quirk sensor merge`.
- `quirk console enroll` (Phase 109) provisions each sensor before it can push (the e2e script must
  enroll first).

</code_context>

<specifics>
## Specific Ideas

- LAB-02 is the headline: two real Docker networks with the SAME subnet and a target at the SAME IP
  in each, proving MERGE-03 emits two distinct components under real networking — not just the unit test.
- This is the milestone close-out: after this phase, the autonomous lifecycle runs audit → complete →
  cleanup for v5.4.

</specifics>

<deferred>
## Deferred Ideas

- Windows-runner execution of the distributed lab (the Linux topology satisfies LAB-01/02; Windows
  sensor correctness is already gated by the Phase 108 windows-latest CI smoke job).
- Automatic merge trigger / polling (v5.5, D-06).

## FLAGGED FOR RESEARCH/PLANNING

- **Live-run vs CI feasibility.** Confirm during research whether the distributed Docker stack can be
  built/validated in CI at all (image build + `docker compose config`) vs requiring a human operator.
  Determine the strongest AUTOMATED assertion possible without a full live run (compose-config schema
  validation, a parser test that the two networks share a subnet and the same IP is bound in both,
  and that the e2e script references enroll→push→merge in order). The live functional E2E remains
  human-UAT; make the automated floor as high as practical.
- **Sensor container repo install.** Determine the lightest reliable way for the sensor/console
  containers to get `quirk` (editable mount of the repo vs building a wheel vs pip install .) given
  the lab runs from the repo checkout — pick the approach with the fewest moving parts.

</deferred>
