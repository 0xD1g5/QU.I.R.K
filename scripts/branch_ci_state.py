#!/usr/bin/env python3
"""Honest branch CI verdict at HEAD (Phase 220, CITRUTH-03 / D-11 / D-12).

Why this exists: five v5.25 phases were verified ``passed`` while ``main``'s
CI was failing. Phase branches never trigger CI on push (both workflows run on
``pull_request`` / ``push: main`` / ``workflow_dispatch`` only), so the
easiest false reassurance is a green run at an OLDER commit, or a run-level
summary that hides a red required job. This script answers exactly one
question, "is this branch's CI green AT ITS HEAD COMMIT?", and lives in the
repo so it survives ``/gsd-update`` and npx cache churn (D-11, TOOL-05).

D-12: a run whose ``headSha`` differs from the branch HEAD is **unobserved**,
never green, even if it succeeded. An unobserved verdict carries dispatch
hints (``gh workflow run '<workflow>' --ref <branch>``) plus a "push first"
hint when ``origin/<branch>`` differs from the local HEAD (a dispatch runs the
REMOTE branch tip, not your local commit).

Why the required set is a constant here and NOT GitHub branch protection:
branch protection on ``main`` requires only "Windows Sensor Smoke". Deriving
from it would bless a branch whose Linux Full Suite is red. The reviewed
required set is ``REQUIRED_JOBS``; every non-required job is listed with a
reason in ``ADVISORY_JOBS`` / ``DISPATCH_ADVISORY_JOBS``, and
``tests/test_branch_ci_state.py`` re-derives the gating set from the workflow
YAMLs at run time so this constant cannot drift silently. A job present in a
run but in neither list fails CLOSED (treated as required).

Exit-code contract:
    0  every required workflow has a completed run AT the branch HEAD sha
       whose every required job concluded ``success`` (verdict ``green``)
    1  red, missing, or in progress (verdict ``red`` or ``unobserved``)
    2  gh missing / unauthenticated / unparseable output, or git cannot
       resolve the branch (verdict ``unknown``). Exit 2 never says green.

No retries beyond gh's own: a transient gh failure is exit 2, never green.

Usage:
    python3 scripts/branch_ci_state.py [--branch B] [--compare-main] [--json-out PATH]

JSON report goes to stdout; human hints and errors go to stderr. Stdlib only:
220-05's pre-commit hook imports ``evaluate`` / ``job_gating`` from this
module under system ``python3``. The script never reads or prints the gh
token; it relies on gh's own credential store, list-argv subprocess only.

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Callable

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

Runner = Callable[[list], subprocess.CompletedProcess]

REQUIRED_WORKFLOWS: tuple[str, ...] = ("Python CI", "Dashboard Quality")

REQUIRED_JOBS: dict[str, tuple[str, ...]] = {
    "Python CI": (
        "Linux Full Suite",
        "Windows Sensor Smoke",
        "Windows Sensor Build",
        "Windows Sensor E2E (frozen -> Linux-built console)",
    ),
    # Required because STATE.md's own close evidence treats it as gating
    # ("Dashboard Quality 4/4 green"); an a11y-red branch verifying `passed`
    # is the same defect class Phase 220 closes.
    "Dashboard Quality": (
        "Axe + Console Gate",
        "E2E Smoke (real server + committed bundle)",
        "Bundle Freshness Gate",
    ),
}

ADVISORY_JOBS: dict[tuple[str, str], str] = {
    ("Python CI", "Windows Packaging Spike"):
        "workflow declares continue-on-error: true",
    ("Python CI", "Browser E2E"):
        "workflow declares continue-on-error: true",
    ("Dashboard Quality", "Regenerate a11y Baselines (Linux, manual)"):
        "dispatch-only maintenance job (if: github.event_name == 'workflow_dispatch')",
}

# Applies ONLY when the run's event == "workflow_dispatch"; the job's
# conclusion is still reported.
DISPATCH_ADVISORY_JOBS: dict[tuple[str, str], str] = {
    ("Python CI", "Windows Sensor E2E (frozen -> Linux-built console)"):
        "todo 260929: empty --api-token on branch workflow_dispatch; still "
        "REQUIRED on pull_request/push; re-promote when 260929 closes",
}

# Documentation only: workflows deliberately not tracked by this script.
NOT_TRACKED_WORKFLOWS: dict[str, str] = {
    "Python Staleness Gate":
        "no workflow_dispatch trigger, cannot run on a phase branch; "
        "observed on the PR run",
    "Release": "tag-triggered release pipeline, not branch CI",
    "release-container": "tag-triggered container publish, not branch CI",
    "Release Tag Hygiene": "tag-hygiene check, not branch CI",
}

RUN_FIELDS = "databaseId,headSha,status,conclusion,event,createdAt,workflowName"

# `FAILED <nodeid>[ - message]`; a parametrize id may contain spaces inside
# its brackets, so allow one bracketed suffix before the " - " tail.
_FAILED_RE = re.compile(r"FAILED (tests/\S+?(?:\[[^\]]*\])?)(?:\s+-\s|\s*$)")


class CIStateError(Exception):
    """A gh/git failure that makes the verdict unknowable (exit 2)."""


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(cmd), check=False, capture_output=True, text=True, cwd=REPO_ROOT
    )


def _call(runner: Runner, argv: list) -> subprocess.CompletedProcess:
    try:
        return runner(list(argv))
    except OSError as exc:  # FileNotFoundError when gh/git is not on PATH
        raise CIStateError(f"{argv[0]} could not be executed: {exc}") from exc


def _gh_json(gh_runner: Runner, argv: list):
    cp = _call(gh_runner, argv)
    if cp.returncode != 0:
        raise CIStateError(
            f"{' '.join(argv[:4])} exited {cp.returncode}: {(cp.stderr or '').strip()[:300]}"
        )
    try:
        return json.loads(cp.stdout)
    except (TypeError, ValueError) as exc:
        raise CIStateError(f"{' '.join(argv[:4])} returned unparseable JSON") from exc


def _git_sha(git_runner: Runner, ref: str) -> str | None:
    cp = _call(git_runner, ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    sha = (cp.stdout or "").strip()
    if cp.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        return None
    return sha


def parse_failing_nodes(log_text: str) -> list[str]:
    """Extract pytest node ids from `gh run view --log-failed` text, deduped in order."""
    seen: dict[str, None] = {}
    for line in (log_text or "").splitlines():
        m = _FAILED_RE.search(line)
        if m:
            seen.setdefault(m.group(1), None)
    return list(seen)


def job_gating(workflow: str, job: str, event: str) -> tuple[bool, str | None]:
    """Return (required, advisory_reason). The ONE place required-ness is decided."""
    pair = (workflow, job)
    if event == "workflow_dispatch" and pair in DISPATCH_ADVISORY_JOBS:
        return False, DISPATCH_ADVISORY_JOBS[pair]
    if job in REQUIRED_JOBS.get(workflow, ()):
        return True, None
    if pair in ADVISORY_JOBS:
        return False, ADVISORY_JOBS[pair]
    # Unclassified: nobody reviewed it, so fail closed.
    return True, None


def _latest(runs: list) -> dict | None:
    return max(runs, key=lambda r: r.get("createdAt") or "") if runs else None


def _collect_workflow(gh_runner: Runner, branch: str, workflow: str,
                      head_sha: str) -> dict:
    runs = _gh_json(gh_runner, [
        "gh", "run", "list", "--branch", branch, "--workflow", workflow,
        "--limit", "20", "--json", RUN_FIELDS,
    ])
    if not isinstance(runs, list):
        raise CIStateError(f"gh run list for {workflow!r} did not return a list")
    at_head = [r for r in runs if isinstance(r, dict) and r.get("headSha") == head_sha]
    run = _latest(at_head)
    entry = {"name": workflow, "latest_run": _latest(runs), "run": None}
    if run is None:
        return entry
    run = dict(run)
    if run.get("status") == "completed":
        view = _gh_json(gh_runner, [
            "gh", "run", "view", str(run["databaseId"]), "--json", "jobs",
        ])
        jobs = view.get("jobs") if isinstance(view, dict) else None
        if not isinstance(jobs, list):
            raise CIStateError(f"gh run view {run['databaseId']} returned no jobs list")
        out_jobs = []
        for job in jobs:
            job = dict(job)
            if job.get("conclusion") == "failure":
                cp = _call(gh_runner, [
                    "gh", "run", "view", str(run["databaseId"]),
                    "--job", str(job.get("databaseId")), "--log-failed",
                ])
                # A missing log is not fatal: the job is already red.
                job["log_failed"] = cp.stdout if cp.returncode == 0 else ""
            out_jobs.append(job)
        run["jobs"] = out_jobs
    entry["run"] = run
    return entry


def collect(branch: str, *, gh_runner: Runner, git_runner: Runner,
            compare_main: bool = False) -> dict:
    """All I/O lives here. Raises CIStateError on any gh/git failure."""
    auth = _call(gh_runner, ["gh", "auth", "status"])
    if auth.returncode != 0:
        raise CIStateError("gh is not authenticated (`gh auth status` failed)")
    head_sha = _git_sha(git_runner, branch)
    if head_sha is None:
        raise CIStateError(f"git cannot resolve branch {branch!r}")
    raw = {
        "branch": branch,
        "head_sha": head_sha,
        "remote_sha": _git_sha(git_runner, f"refs/remotes/origin/{branch}"),
        "workflows": [
            _collect_workflow(gh_runner, branch, wf, head_sha)
            for wf in REQUIRED_WORKFLOWS
        ],
    }
    if compare_main:
        main_sha = _git_sha(git_runner, "refs/remotes/origin/main") or _git_sha(
            git_runner, "main")
        if main_sha is None:
            raise CIStateError("git cannot resolve main for --compare-main")
        raw["main"] = {
            "head_sha": main_sha,
            "workflows": [
                _collect_workflow(gh_runner, "main", wf, main_sha)
                for wf in REQUIRED_WORKFLOWS
            ],
        }
    return raw


def _evaluate_workflow(entry: dict, reasons: list) -> dict:
    name = entry["name"]
    run = entry.get("run")
    out = {"name": name, "run_id": None, "head_sha": None, "event": None,
           "conclusion": None, "observed": False, "state": "unobserved", "jobs": []}
    if run is None:
        latest = entry.get("latest_run")
        if latest:
            reasons.append(
                f"{name}: no run at HEAD (latest run {latest.get('databaseId')} is at "
                f"{str(latest.get('headSha'))[:12]}, concluded {latest.get('conclusion')})"
            )
        else:
            reasons.append(f"{name}: no run found for this branch")
        return out
    event = run.get("event") or ""
    out.update(run_id=run.get("databaseId"), head_sha=run.get("headSha"),
               event=event, conclusion=run.get("conclusion") or None)
    if run.get("status") != "completed":
        reasons.append(f"{name}: run {run.get('databaseId')} at HEAD is in progress "
                       f"(status {run.get('status')})")
        return out
    out["observed"] = True
    red = False
    seen = set()
    for job in run.get("jobs", []):
        jname = job.get("name", "")
        seen.add(jname)
        required, why = job_gating(name, jname, event)
        conclusion = job.get("conclusion")
        out["jobs"].append({
            "name": jname,
            "conclusion": conclusion,
            "required": required,
            "advisory_reason": why,
            "failing_nodes": parse_failing_nodes(job.get("log_failed", "")),
        })
        if required and conclusion != "success":
            red = True
            reasons.append(f"{name}: required job {jname!r} concluded {conclusion}")
    for jname in REQUIRED_JOBS.get(name, ()):
        if jname not in seen and job_gating(name, jname, event)[0]:
            red = True
            reasons.append(f"{name}: required job missing from run "
                           f"{run.get('databaseId')}: {jname!r}")
    out["state"] = "red" if red else "green"
    return out


def _evaluate_main(main_raw: dict) -> dict:
    workflows = []
    for entry in main_raw.get("workflows", []):
        run = entry.get("run")
        if run is None:
            workflows.append({"name": entry["name"], "run_id": None, "observed": False,
                              "conclusion": None, "failing_nodes": []})
            continue
        nodes: dict[str, None] = {}
        for job in run.get("jobs", []):
            for node in parse_failing_nodes(job.get("log_failed", "")):
                nodes.setdefault(node, None)
        workflows.append({
            "name": entry["name"],
            "run_id": run.get("databaseId"),
            "observed": run.get("status") == "completed",
            "conclusion": run.get("conclusion") or run.get("status"),
            "failing_nodes": list(nodes),
        })
    return {"head_sha": main_raw.get("head_sha"), "workflows": workflows}


def evaluate(raw: dict) -> tuple[int, dict]:
    """PURE: collected data -> (exit_code, report). No I/O, input not mutated."""
    branch = raw["branch"]
    head_sha = raw["head_sha"]
    reasons: list[str] = []
    hints: list[str] = []
    workflows = [_evaluate_workflow(e, reasons) for e in raw.get("workflows", [])]
    states = {w["state"] for w in workflows}
    if "red" in states:
        verdict = "red"
    elif "unobserved" in states or not workflows:
        verdict = "unobserved"
    else:
        verdict = "green"
    for w in workflows:
        if w["run_id"] is None:
            hints.append(f"gh workflow run '{w['name']}' --ref {branch}")
    remote = raw.get("remote_sha")
    if remote != head_sha:
        where = f"at {remote[:12]}" if remote else "does not exist"
        hints.insert(0, f"push first: origin/{branch} {where}, local HEAD is "
                        f"{head_sha[:12]} (a dispatch runs the remote tip)")
    report = {
        "checked_at": raw.get("checked_at") or "",
        "branch": branch,
        "head_sha": head_sha,
        "verdict": verdict,
        "reasons": reasons,
        "dispatch_hints": hints,
        "workflows": workflows,
    }
    if "main" in raw:
        report["main"] = _evaluate_main(raw["main"])
    return (0 if verdict == "green" else 1), report


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")


def _emit(report: dict, json_out: str | None) -> None:
    text = json.dumps(report, indent=2)
    print(text)
    if json_out:
        path = pathlib.Path(json_out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n")


def main(argv=None, *, gh_runner: Runner | None = None,
         git_runner: Runner | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report whether a branch's required CI is green AT its HEAD sha.")
    parser.add_argument("--branch", help="branch to check (default: current branch)")
    parser.add_argument("--compare-main", action="store_true",
                        help="also report main's latest run at main HEAD")
    parser.add_argument("--json-out", help="also write the JSON report to this path")
    args = parser.parse_args(argv)

    git_runner = git_runner or _run
    if gh_runner is None:
        gh_runner = _run
        if shutil.which("gh") is None:
            gh_runner = _missing_gh

    branch = args.branch
    report: dict
    try:
        if not branch:
            cp = _call(git_runner, ["git", "branch", "--show-current"])
            branch = (cp.stdout or "").strip()
            if cp.returncode != 0 or not branch:
                raise CIStateError("cannot determine current branch (detached HEAD?); "
                                   "pass --branch")
        raw = collect(branch, gh_runner=gh_runner, git_runner=git_runner,
                      compare_main=args.compare_main)
        raw["checked_at"] = _now()
        code, report = evaluate(raw)
    except CIStateError as exc:
        report = {"checked_at": _now(), "branch": branch, "head_sha": None,
                  "verdict": "unknown", "reasons": [str(exc)],
                  "dispatch_hints": [], "workflows": []}
        _emit(report, args.json_out)
        print(f"branch_ci_state: verdict unknown (exit 2): {exc}", file=sys.stderr)
        return 2

    _emit(report, args.json_out)
    print(f"branch_ci_state: {branch} @ {report['head_sha'][:12]}: verdict "
          f"{report['verdict']} (exit {code})", file=sys.stderr)
    for reason in report["reasons"]:
        print(f"  - {reason}", file=sys.stderr)
    for hint in report["dispatch_hints"]:
        print(f"  hint: {hint}", file=sys.stderr)
    return code


def _missing_gh(argv: list) -> subprocess.CompletedProcess:
    raise FileNotFoundError("gh is not on PATH")


if __name__ == "__main__":
    sys.exit(main())
