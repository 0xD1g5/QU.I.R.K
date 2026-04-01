# AGENTS Instructions

- Follow PEP 8 coding style for all Python changes.
- Keep changes as minimal diffs; avoid unnecessary refactors.
- After making changes, always run the test suite: `.venv/bin/python -m pytest tests/ -q`
- If detection logic is changed, update `quantum-chaos-enterprise-lab/expected_results_v3.md` accordingly.
- The package is `quirk` — all imports use `from quirk.x import y`.
- Entry point is `run_scan.py`, wired via `pyproject.toml` as `quirk = "run_scan:main"`.
- Dashboard backend lives in `quirk/dashboard/`; frontend source in `src/dashboard/`.
- Dependencies are defined in `pyproject.toml` — do not use `requirements.txt`.
