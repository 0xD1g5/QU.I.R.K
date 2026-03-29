---
phase: 01-foundation-fixes
plan: 04
type: execute
wave: 3
depends_on: [01, 02, 03]
files_modified:
  - qcscan/ (renamed to quirk/)
  - pyproject.toml
  - run_scan.py
  - tests/*.py
  - config.yaml
autonomous: true
requirements: [CORE-03]

must_haves:
  truths:
    - "All CLI commands, output strings, config keys, file paths, and module names read 'quirk' or 'QU.I.R.K.' — zero remaining 'qcscan' references in .py files"
    - "python -c 'import quirk' succeeds"
    - "The validate.py QuRisk reference is updated to QU.I.R.K."
    - "Report headers say QU.I.R.K. not QuRisk or qcscan"
  artifacts:
    - path: "quirk/"
      provides: "Renamed package directory (was qcscan/)"
    - path: "pyproject.toml"
      provides: "Package metadata with name=quirk and console_scripts entry point"
      contains: 'name = "quirk"'
    - path: "quirk/__init__.py"
      provides: "Package init with __version__"
  key_links:
    - from: "run_scan.py"
      to: "quirk/"
      via: "all imports use from quirk.xxx"
      pattern: "from quirk\\."
    - from: "pyproject.toml"
      to: "run_scan.py"
      via: "console_scripts entry point"
      pattern: "quirk.*run_scan:main"
---

<objective>
Rename the package from qcscan to quirk across the entire codebase, create pyproject.toml,
and update all user-facing strings to QU.I.R.K.

Purpose: Brand identity — the product is QU.I.R.K. (Quantum Infrastructure Readiness Kit),
not qcscan or QuRisk. This is the last plan in the phase because it touches every file
and must run after all logic changes are stable.

Output: qcscan/ directory renamed to quirk/, all imports updated, pyproject.toml created,
user-facing strings updated, zero remaining qcscan/QuRisk references in Python files.
</objective>

<execution_context>
@/Users/digs/.claude/get-shit-done/workflows/execute-plan.md
@/Users/digs/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-fixes/01-CONTEXT.md
@.planning/phases/01-foundation-fixes/01-RESEARCH.md
@.planning/phases/01-foundation-fixes/01-01-SUMMARY.md
@.planning/phases/01-foundation-fixes/01-02-SUMMARY.md
@.planning/phases/01-foundation-fixes/01-03-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Rename qcscan directory to quirk and update all imports</name>
  <files>qcscan/ (renamed to quirk/), run_scan.py, tests/*.py</files>
  <read_first>
    - run_scan.py (all import lines referencing qcscan)
    - qcscan/__init__.py (if exists — needs to become quirk/__init__.py)
    - .planning/phases/01-foundation-fixes/01-RESEARCH.md (section 4 — rename scope, sed commands, file counts)
  </read_first>
  <action>
    Per D-13, D-15, D-16, D-17:

    **Step 1: Rename the directory:**
    ```bash
    mv qcscan quirk
    ```

    **Step 2: Update all Python imports across the codebase:**
    Run sed sweep on all .py files (excluding .venv):
    ```bash
    find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*" | xargs sed -i '' 's/from qcscan\./from quirk./g; s/import qcscan\./import quirk./g; s/import qcscan$/import quirk/g'
    ```

    **Step 3: Update string references in Python files:**
    ```bash
    find . -name "*.py" -not -path "./.venv/*" -not -path "./.git/*" | xargs sed -i '' "s/'qcscan'/'quirk'/g; s/\"qcscan\"/\"quirk\"/g"
    ```

    **Step 4: Update run_scan.py user-facing strings (D-16):**
    - Line 75: Change `"Quantum Crypto Scanner (qcscan)"` to `"QU.I.R.K. -- Quantum Infrastructure Readiness Kit"`
    - Any other user-facing strings containing "qcscan"

    **Step 5: Update validate.py QuRisk reference (D-17):**
    - Change "QuRisk" to "QU.I.R.K." in quirk/validate.py (was qcscan/validate.py)

    **Step 6: Update report headers (D-16):**
    - In quirk/reports/writer.py: product name strings in print output should say "QU.I.R.K."
    - PLATFORM_VERSION stays "3.9" (D-16 — keep version number)
    - Console output lines with emoji + labels: update any "qcscan" references

    **Step 7: Ensure quirk/__init__.py exists:**
    If qcscan/__init__.py existed, it was renamed. If it didn't exist, create:
    ```python
    """QU.I.R.K. -- Quantum Infrastructure Readiness Kit"""
    __version__ = "3.9.0"
    ```

    **Step 8: Update config.yaml references (if any):**
    ```bash
    find . -name "*.yaml" -name "*.yml" -not -path "./.venv/*" | xargs grep -l "qcscan" 2>/dev/null
    ```
    Replace any `qcscan:` keys with `quirk:`.

    **Step 9: Verify no remaining references:**
    ```bash
    grep -rn "qcscan" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning
    grep -rn "QuRisk" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning
    ```
    Fix any stragglers found. Common hiding spots:
    - Comments mentioning qcscan
    - Docstrings
    - Logger format strings
    - Error messages
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && grep -rn "from qcscan\." . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning | wc -l | xargs test 0 -eq && echo "OK: zero qcscan import references" || echo "FAIL: qcscan references remain"</automated>
  </verify>
  <acceptance_criteria>
    - ls quirk/ shows the renamed package directory
    - ls qcscan/ fails (directory no longer exists)
    - grep -rn "from qcscan\." . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning returns NO matches
    - grep -rn "import qcscan" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning returns NO matches
    - grep -rn "QuRisk" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning returns NO matches
    - python -c "import quirk; print(quirk.__version__)" prints "3.9.0"
    - python -c "from quirk.reports.writer import write_reports; print('OK')" succeeds
  </acceptance_criteria>
  <done>qcscan/ renamed to quirk/, all imports updated, all user-facing strings updated, zero remaining qcscan/QuRisk references in .py files</done>
</task>

<task type="auto">
  <name>Task 2: Create pyproject.toml and verify full test suite</name>
  <files>pyproject.toml</files>
  <read_first>
    - run_scan.py (confirm main() function exists and is the entry point)
    - quirk/__init__.py (confirm __version__ exists after Task 1)
    - .planning/phases/01-foundation-fixes/01-RESEARCH.md (section 4.4 — pyproject.toml structure)
  </read_first>
  <action>
    Per D-14: Create pyproject.toml at the project root. There is no existing pyproject.toml
    or setup.py (RESEARCH.md section 4.1 confirms this).

    Create pyproject.toml:
    ```toml
    [build-system]
    requires = ["setuptools>=68"]
    build-backend = "setuptools.backends._legacy:_Backend"

    [project]
    name = "quirk"
    version = "3.9.0"
    description = "QU.I.R.K. -- Quantum Infrastructure Readiness Kit"
    requires-python = ">=3.10"
    license = {text = "Proprietary"}

    [project.scripts]
    quirk = "run_scan:main"

    [tool.setuptools.packages.find]
    include = ["quirk*"]
    ```

    Note: The entry point `quirk = "run_scan:main"` means after `pip install -e .`,
    the `quirk` command will be available in the venv. The `run_scan.py` file stays
    at the project root as the actual implementation.

    Then run the full test suite to verify nothing is broken by the rename:
    ```bash
    python -m pytest tests/ -v
    ```

    If any tests fail due to import issues from the rename, fix them (likely just
    updating import paths that the sed sweep missed).
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -m pytest tests/ -x -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - test -f pyproject.toml succeeds
    - grep 'name = "quirk"' pyproject.toml returns a match
    - grep 'quirk = "run_scan:main"' pyproject.toml returns a match
    - python -m pytest tests/ -x -v passes all tests
    - python -c "import quirk; print(quirk.__version__)" prints "3.9.0"
  </acceptance_criteria>
  <done>pyproject.toml created with quirk package name and entry point, full test suite passes after rename</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/ -x -q` passes all tests
- `grep -rn "qcscan" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning | wc -l` returns 0
- `grep -rn "QuRisk" . --include="*.py" --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.planning | wc -l` returns 0
- `python -c "import quirk; print(quirk.__version__)"` prints "3.9.0"
- `python -c "from quirk.scanner.tls_scanner import scan_one; print('OK')"` succeeds
- `python -c "from quirk.scanner.ssh_scanner import scan_ssh_targets; print('OK')"` succeeds
- `python -c "from quirk.reports.writer import write_reports; print('OK')"` succeeds
- `cat pyproject.toml | grep 'name = "quirk"'` returns a match
</verification>

<success_criteria>
- All module names, CLI commands, output strings, config keys read "quirk" or "QU.I.R.K." (CORE-03)
- Zero remaining "qcscan" or "QuRisk" references in .py files
- pyproject.toml exists with proper package metadata and entry point (D-14)
- Full test suite passes after rename
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-fixes/01-04-SUMMARY.md`
</output>
