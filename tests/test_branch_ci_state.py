"""Phase 220-04 CITRUTH-03 (D-11/D-12): unit tests for scripts/branch_ci_state.py.

`branch_ci_state.py` answers "is this branch's CI green AT HEAD?" through an
injectable `gh_runner` / `git_runner` seam. Every test here drives it with a
FakeRunner that returns canned `gh` JSON / log text using the real field names
(`databaseId`, `headSha`, `status`, `conclusion`, `event`, `createdAt`,
`workflowName`; `jobs[].{databaseId,name,status,conclusion}`), so nothing here
touches the network or GitHub.

The drift guard at the bottom re-derives the gating job set from the live
workflow YAMLs at run time, so the reviewed REQUIRED_JOBS constant cannot drift
silently from `.github/workflows/python-ci.yml` / `dashboard-quality.yml`.

`scripts/` is not an importable package, so the module is loaded via
`importlib.util.spec_from_file_location`.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "branch_ci_state.py"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOW_FILES = ("python-ci.yml", "dashboard-quality.yml")

BRANCH = "phase-x"
HEAD = "a" * 40
OLD = "b" * 40
MAIN_HEAD = "c" * 40

PY_JOBS = (
    "Windows Sensor Smoke",
    "Windows Packaging Spike",
    "Windows Sensor Build",
    "Windows Sensor E2E (frozen -> Linux-built console)",
    "Linux Full Suite",
    "Browser E2E",
)
DQ_JOBS = (
    "Axe + Console Gate",
    "E2E Smoke (real server + committed bundle)",
    "Bundle Freshness Gate",
)

LOG_FAILED = (
    "Linux Full Suite\tUNKNOWN STEP\t2026-10-01T02:48:02.4593090Z FAILED "
    "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[multihost]"
    " - AssertionError: multihost first up failed (rc=1):\n"
    "Linux Full Suite\tUNKNOWN STEP\t2026-10-01T02:48:02.4602492Z FAILED "
    "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[storage-s3]"
    " - AssertionError: storage-s3 first up failed (rc=1):\n"
    "Linux Full Suite\tUNKNOWN STEP\t2026-10-01T02:48:03.0000000Z = 2 failed, 9000 passed =\n"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("branch_ci_state", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def bcs():
    return _load_module()


def _cp(argv, stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess(list(argv), returncode, stdout, stderr)


class FakeRunner:
    """Maps argv prefixes to canned CompletedProcess results; records calls.

    The LONGEST matching prefix wins, so a specific `gh run view ID --job J`
    entry beats a generic `gh run view ID` one.
    """

    def __init__(self, table=None, raise_on=None):
        self.table = dict(table or {})
        self.calls = []
        self.raise_on = raise_on

    def add(self, prefix, stdout="", returncode=0, stderr=""):
        self.table[tuple(prefix)] = (stdout, returncode, stderr)

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        if self.raise_on is not None and argv[0] == self.raise_on:
            raise FileNotFoundError(argv[0])
        best = None
        for prefix, result in self.table.items():
            if tuple(argv[: len(prefix)]) == prefix:
                if best is None or len(prefix) > len(best[0]):
                    best = (prefix, result)
        if best is None:
            return _cp(argv, "", 1, f"FakeRunner: no canned response for {argv}")
        stdout, rc, stderr = best[1]
        return _cp(argv, stdout, rc, stderr)


def _run(run_id, sha, *, event="workflow_dispatch", status="completed",
         conclusion="success", workflow="Python CI",
         created="2026-10-01T00:00:00Z"):
    return {
        "databaseId": run_id,
        "headSha": sha,
        "status": status,
        "conclusion": conclusion if status == "completed" else "",
        "event": event,
        "createdAt": created,
        "workflowName": workflow,
    }


def _jobs(names, overrides=None, base_id=1000):
    overrides = overrides or {}
    out = []
    for i, name in enumerate(names):
        out.append({
            "databaseId": base_id + i,
            "name": name,
            "status": "completed",
            "conclusion": overrides.get(name, "success"),
        })
    return {"jobs": out}


def _git(branch=BRANCH, head=HEAD, remote=HEAD, main_head=MAIN_HEAD):
    g = FakeRunner()
    g.add(["git", "branch", "--show-current"], branch + "\n")
    g.add(["git", "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}"], head + "\n")
    if remote is None:
        g.add(["git", "rev-parse", "--verify", "--quiet",
               f"refs/remotes/origin/{branch}^{{commit}}"], "", 1)
    else:
        g.add(["git", "rev-parse", "--verify", "--quiet",
               f"refs/remotes/origin/{branch}^{{commit}}"], remote + "\n")
    g.add(["git", "rev-parse", "--verify", "--quiet",
           "refs/remotes/origin/main^{commit}"], main_head + "\n")
    return g


def _gh(py_runs, dq_runs, py_jobs=None, dq_jobs=None, *, branch=BRANCH,
        logs=None, main_py_runs=None, main_dq_runs=None, main_py_jobs=None):
    """Build a gh FakeRunner. *_jobs map run_id -> jobs dict."""
    g = FakeRunner()
    g.add(["gh", "auth", "status"], "Logged in\n")
    g.add(["gh", "run", "list", "--branch", branch, "--workflow", "Python CI"],
          json.dumps(py_runs))
    g.add(["gh", "run", "list", "--branch", branch, "--workflow", "Dashboard Quality"],
          json.dumps(dq_runs))
    for rid, jobs in (py_jobs or {}).items():
        g.add(["gh", "run", "view", str(rid), "--json", "jobs"], json.dumps(jobs))
    for rid, jobs in (dq_jobs or {}).items():
        g.add(["gh", "run", "view", str(rid), "--json", "jobs"], json.dumps(jobs))
    for (rid, jid), text in (logs or {}).items():
        g.add(["gh", "run", "view", str(rid), "--job", str(jid), "--log-failed"], text)
    if main_py_runs is not None:
        g.add(["gh", "run", "list", "--branch", "main", "--workflow", "Python CI"],
              json.dumps(main_py_runs))
        g.add(["gh", "run", "list", "--branch", "main", "--workflow", "Dashboard Quality"],
              json.dumps(main_dq_runs or []))
        for rid, jobs in (main_py_jobs or {}).items():
            g.add(["gh", "run", "view", str(rid), "--json", "jobs"], json.dumps(jobs))
    return g


def _green_gh(py_event="workflow_dispatch", py_overrides=None, logs=None):
    return _gh(
        [_run(11, HEAD, event=py_event)],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {11: _jobs(PY_JOBS, py_overrides)},
        {22: _jobs(DQ_JOBS, base_id=2000)},
        logs=logs,
    )


def _main(bcs, gh, git, *extra, capsys=None):
    rc = bcs.main(["--branch", BRANCH, *extra], gh_runner=gh, git_runner=git)
    return rc


def _wf(report, name):
    return next(w for w in report["workflows"] if w["name"] == name)


def _job(wf, name):
    return next(j for j in wf["jobs"] if j["name"] == name)


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------


def test_all_required_green_at_head_exits_0(bcs, capsys):
    rc = _main(bcs, _green_gh(), _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["verdict"] == "green"
    assert report["head_sha"] == HEAD
    assert report["branch"] == BRANCH
    assert "checked_at" in report
    for wf in report["workflows"]:
        assert wf["observed"] is True
        assert wf["head_sha"] == HEAD
        assert wf["conclusion"] == "success"
        assert wf["event"] == "workflow_dispatch"
        assert wf["run_id"] in (11, 22)
        for j in wf["jobs"]:
            assert set(j) >= {"name", "conclusion", "required",
                              "advisory_reason", "failing_nodes"}


def test_successful_run_at_older_sha_is_unobserved_not_green(bcs, capsys):
    gh = _gh(
        [_run(11, OLD, conclusion="success")],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {11: _jobs(PY_JOBS)},
        {22: _jobs(DQ_JOBS, base_id=2000)},
    )
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "unobserved"
    py = _wf(report, "Python CI")
    assert py["observed"] is False
    assert f"gh workflow run 'Python CI' --ref {BRANCH}" in report["dispatch_hints"]
    # The stale success must not be fetched/treated as current.
    assert ["gh", "run", "view", "11", "--json", "jobs"] not in gh.calls


def test_no_runs_at_all_is_unobserved(bcs, capsys):
    gh = _gh([], [])
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "unobserved"
    assert f"gh workflow run 'Dashboard Quality' --ref {BRANCH}" in report["dispatch_hints"]


def test_in_progress_run_at_head_is_unobserved(bcs, capsys):
    gh = _gh(
        [_run(11, HEAD, status="in_progress")],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {11: _jobs(PY_JOBS)},
        {22: _jobs(DQ_JOBS, base_id=2000)},
    )
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "unobserved"
    assert any("in progress" in r for r in report["reasons"])
    assert _wf(report, "Python CI")["observed"] is False


def test_required_job_failure_is_red_with_failing_nodes(bcs, capsys):
    gh = _green_gh(
        py_overrides={"Linux Full Suite": "failure"},
        logs={(11, 1004): LOG_FAILED},
    )
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "red"
    lfs = _job(_wf(report, "Python CI"), "Linux Full Suite")
    assert lfs["required"] is True
    assert lfs["conclusion"] == "failure"
    assert lfs["failing_nodes"] == [
        "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[multihost]",
        "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[storage-s3]",
    ]
    assert ["gh", "run", "view", "11", "--job", "1004", "--log-failed"] in gh.calls


def test_parse_failing_nodes_strips_message_tail_and_dedupes(bcs):
    text = LOG_FAILED + LOG_FAILED + "x FAILED tests/test_a.py::t[at risk] - boom\n"
    nodes = bcs.parse_failing_nodes(text)
    assert nodes == [
        "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[multihost]",
        "tests/test_chaos_lab_idempotency.py::test_profile_re_up_is_idempotent[storage-s3]",
        "tests/test_a.py::t[at risk]",
    ]


def test_advisory_job_failure_does_not_gate(bcs, capsys):
    gh = _green_gh(py_overrides={"Browser E2E": "failure"})
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["verdict"] == "green"
    be = _job(_wf(report, "Python CI"), "Browser E2E")
    assert be["required"] is False
    assert be["conclusion"] == "failure"
    assert "continue-on-error" in be["advisory_reason"]


def test_windows_e2e_failure_on_workflow_dispatch_is_advisory_260929(bcs, capsys):
    name = "Windows Sensor E2E (frozen -> Linux-built console)"
    gh = _green_gh(py_event="workflow_dispatch", py_overrides={name: "failure"})
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    job = _job(_wf(report, "Python CI"), name)
    assert job["required"] is False
    assert job["conclusion"] == "failure"  # still reported
    assert "260929" in job["advisory_reason"]


def test_windows_e2e_failure_on_pull_request_is_red(bcs, capsys):
    name = "Windows Sensor E2E (frozen -> Linux-built console)"
    gh = _green_gh(py_event="pull_request", py_overrides={name: "failure"})
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "red"
    assert _job(_wf(report, "Python CI"), name)["required"] is True


@pytest.mark.parametrize("conclusion", ["skipped", "cancelled"])
def test_required_job_skipped_or_cancelled_is_red(bcs, capsys, conclusion):
    gh = _green_gh(py_overrides={"Windows Sensor Smoke": conclusion})
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "red"


def test_required_job_missing_from_run_is_red(bcs, capsys):
    jobs = _jobs([n for n in PY_JOBS if n != "Linux Full Suite"])
    gh = _gh(
        [_run(11, HEAD)],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {11: jobs},
        {22: _jobs(DQ_JOBS, base_id=2000)},
    )
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert report["verdict"] == "red"
    assert any("required job missing" in r and "Linux Full Suite" in r
               for r in report["reasons"])


def test_latest_run_at_head_wins_over_older_run_at_head(bcs, capsys):
    gh = _gh(
        [_run(12, HEAD, conclusion="success", created="2026-10-01T05:00:00Z"),
         _run(11, HEAD, conclusion="failure", created="2026-10-01T01:00:00Z")],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {12: _jobs(PY_JOBS), 11: _jobs(PY_JOBS, {"Linux Full Suite": "failure"})},
        {22: _jobs(DQ_JOBS, base_id=2000)},
    )
    rc = _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert _wf(report, "Python CI")["run_id"] == 12


# ---------------------------------------------------------------------------
# Exit 2 — fail closed, never "green"
# ---------------------------------------------------------------------------


def test_gh_not_on_path_exits_2_never_green(bcs, capsys):
    gh = FakeRunner(raise_on="gh")
    rc = _main(bcs, gh, _git())
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["verdict"] == "unknown"
    assert "green" not in out


def test_gh_unauthenticated_exits_2_never_green(bcs, capsys):
    gh = _green_gh()
    gh.add(["gh", "auth", "status"], "", 1, "You are not logged into any GitHub hosts")
    rc = _main(bcs, gh, _git())
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["verdict"] == "unknown"
    assert "green" not in out


def test_gh_unparseable_json_exits_2_never_green(bcs, capsys):
    gh = _green_gh()
    gh.add(["gh", "run", "list", "--branch", BRANCH, "--workflow", "Python CI"],
           "<html>502 Bad Gateway</html>")
    rc = _main(bcs, gh, _git())
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["verdict"] == "unknown"
    assert "green" not in out


def test_gh_run_list_nonzero_exits_2(bcs, capsys):
    gh = _green_gh()
    gh.add(["gh", "run", "list", "--branch", BRANCH, "--workflow", "Dashboard Quality"],
           "", 1, "HTTP 503")
    rc = _main(bcs, gh, _git())
    out = capsys.readouterr().out
    assert rc == 2
    assert "green" not in out


def test_git_cannot_resolve_branch_exits_2(bcs, capsys):
    git = FakeRunner()
    git.add(["git", "rev-parse"], "", 128, "fatal: Needed a single revision")
    rc = _main(bcs, _green_gh(), git)
    out = capsys.readouterr().out
    assert rc == 2
    assert json.loads(out)["verdict"] == "unknown"
    assert "green" not in out


# ---------------------------------------------------------------------------
# Hints, compare-main, json-out, purity
# ---------------------------------------------------------------------------


def test_push_first_hint_when_origin_differs_from_local_head(bcs, capsys):
    gh = _gh([_run(11, OLD)], [_run(22, OLD, workflow="Dashboard Quality")])
    rc = _main(bcs, gh, _git(remote=OLD))
    report = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert any("push first" in h for h in report["dispatch_hints"])


def test_push_first_hint_when_origin_branch_absent(bcs, capsys):
    gh = _gh([], [])
    _main(bcs, gh, _git(remote=None))
    report = json.loads(capsys.readouterr().out)
    assert any("push first" in h for h in report["dispatch_hints"])


def test_no_push_first_hint_when_origin_matches(bcs, capsys):
    gh = _gh([], [])
    _main(bcs, gh, _git())
    report = json.loads(capsys.readouterr().out)
    assert not any("push first" in h for h in report["dispatch_hints"])


def test_compare_main_reports_main_failing_nodes(bcs, capsys):
    main_jobs = _jobs(PY_JOBS, {"Linux Full Suite": "failure"}, base_id=5000)
    gh = _gh(
        [_run(11, HEAD)],
        [_run(22, HEAD, workflow="Dashboard Quality")],
        {11: _jobs(PY_JOBS)},
        {22: _jobs(DQ_JOBS, base_id=2000)},
        main_py_runs=[_run(55, MAIN_HEAD, event="push", conclusion="failure")],
        main_dq_runs=[],
        main_py_jobs={55: main_jobs},
        logs={(55, 5004): LOG_FAILED},
    )
    rc = _main(bcs, gh, _git(), "--compare-main")
    report = json.loads(capsys.readouterr().out)
    assert rc == 0  # main's state never changes the branch verdict
    main = report["main"]
    assert main["head_sha"] == MAIN_HEAD
    py = next(w for w in main["workflows"] if w["name"] == "Python CI")
    assert py["run_id"] == 55
    assert py["conclusion"] == "failure"
    assert len(py["failing_nodes"]) == 2
    dq = next(w for w in main["workflows"] if w["name"] == "Dashboard Quality")
    assert dq["observed"] is False  # recorded, not raised


def test_json_out_writes_same_report(bcs, capsys, tmp_path):
    out_path = tmp_path / "nested" / "state.json"
    rc = _main(bcs, _gh([], []), _git(), "--json-out", str(out_path))
    stdout = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert json.loads(out_path.read_text()) == stdout


def test_branch_defaults_to_current_branch(bcs, capsys):
    rc = bcs.main([], gh_runner=_green_gh(), git_runner=_git())
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["branch"] == BRANCH


def test_evaluate_is_pure(bcs):
    gh = _green_gh(py_overrides={"Linux Full Suite": "failure"},
                   logs={(11, 1004): LOG_FAILED})
    raw = bcs.collect(BRANCH, gh_runner=gh, git_runner=_git())
    n_calls = len(gh.calls)
    snapshot = copy.deepcopy(raw)
    rc1, rep1 = bcs.evaluate(raw)
    rc2, rep2 = bcs.evaluate(raw)
    assert len(gh.calls) == n_calls  # evaluate performed no I/O
    assert raw == snapshot  # and did not mutate its input
    rep1.pop("checked_at", None)
    rep2.pop("checked_at", None)
    assert (rc1, rep1) == (rc2, rep2)
    assert rc1 == 1


def test_job_gating_single_source_of_required_ness(bcs):
    e2e = "Windows Sensor E2E (frozen -> Linux-built console)"
    assert bcs.job_gating("Python CI", "Linux Full Suite", "push") == (True, None)
    assert bcs.job_gating("Python CI", e2e, "pull_request") == (True, None)
    req, why = bcs.job_gating("Python CI", e2e, "workflow_dispatch")
    assert req is False and "260929" in why
    req, why = bcs.job_gating("Python CI", "Browser E2E", "pull_request")
    assert req is False and why
    req, why = bcs.job_gating("Dashboard Quality",
                              "Regenerate a11y Baselines (Linux, manual)",
                              "workflow_dispatch")
    assert req is False and why


def test_unclassified_job_fails_closed(bcs):
    # A job nobody reviewed must gate (fail closed), not silently pass.
    req, _why = bcs.job_gating("Python CI", "Some Brand New Job", "push")
    assert req is True


# ---------------------------------------------------------------------------
# Drift guard — re-derive the gating set from the workflow YAMLs at run time
# ---------------------------------------------------------------------------


def _load_workflows():
    out = {}
    for fname in WORKFLOW_FILES:
        doc = yaml.safe_load((WORKFLOWS_DIR / fname).read_text())
        out[doc["name"]] = doc
    return out


def _is_dispatch_only(job):
    cond = str(job.get("if", ""))
    return "workflow_dispatch" in cond and "==" in cond


def test_required_set_matches_workflow_yaml_drift_guard(bcs):
    workflows = _load_workflows()
    assert set(workflows) == set(bcs.REQUIRED_WORKFLOWS)
    assert set(bcs.REQUIRED_JOBS) == set(bcs.REQUIRED_WORKFLOWS)

    gating, non_gating = set(), set()
    for wf_name, doc in workflows.items():
        for _key, job in doc["jobs"].items():
            pair = (wf_name, job.get("name", _key))
            if job.get("continue-on-error") is True or _is_dispatch_only(job):
                non_gating.add(pair)
            else:
                gating.add(pair)

    required = {(wf, j) for wf, jobs in bcs.REQUIRED_JOBS.items() for j in jobs}
    assert gating == required, (
        f"workflow gating jobs drifted from REQUIRED_JOBS: "
        f"unlisted={sorted(gating - required)} stale={sorted(required - gating)}"
    )
    # Every non-gating job is listed explicitly with a reason — nothing silent.
    assert non_gating == set(bcs.ADVISORY_JOBS), (
        f"advisory drift: unlisted={sorted(non_gating - set(bcs.ADVISORY_JOBS))} "
        f"stale={sorted(set(bcs.ADVISORY_JOBS) - non_gating)}"
    )
    assert all(bcs.ADVISORY_JOBS.values())
    # Dispatch-advisory entries must name real, otherwise-required jobs.
    for pair, reason in bcs.DISPATCH_ADVISORY_JOBS.items():
        assert pair in required and reason


def test_required_workflows_are_dispatchable(bcs):
    # The dispatch hint is only honest if the workflow has workflow_dispatch.
    # Note: `on:` loads as Python True under YAML 1.1.
    for name, doc in _load_workflows().items():
        triggers = doc.get(True, doc.get("on"))
        assert "workflow_dispatch" in triggers, name
