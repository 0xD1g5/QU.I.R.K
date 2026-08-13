"""Phase 150 D-07 CI gate smoke check.

TEMPORARY FILE. This test exists only to prove, via a real GitHub Actions run,
that the `Linux Full Suite` job actually gates on real test failures instead of
being a syntactically-valid-but-disconnected no-op. It is deliberately failing
and is deleted (never merged to main) as part of the same live-fire proof that
introduced it. See .planning/phases/150-test-suite-green-baseline-ci-gate/
150-CI-EVIDENCE.md for the run evidence this test produced.
"""


def test_phase_150_d07_ci_gate_smoke_check_deliberately_fails():
    assert False, "Phase 150 D-07 CI gate smoke check: deliberate failure to prove the gate bites"
