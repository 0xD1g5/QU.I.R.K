#!/usr/bin/env bash
# check-cancelled-guards.sh — Heuristic CI guard for HOOK-04.
#
# Scope: src/dashboard/src/hooks/*.ts and *.tsx (only).
# Rule: if a hook file contains an `await` followed somewhere later by a state
#       setter (setError, setData, setLoading, setSession, setSessions) and the
#       file does NOT contain at least one `if (!cancelled)` block, fail.
#       Lines with `// eslint-disable-line` are stripped before counting setters,
#       allowing explicit in-code acknowledgment of intentional unguarded setters.
#
# This is a heuristic — it does not parse the AST. It catches the regression
# class observed in audit (Pattern C): error-branch setters without a guard
# in a hook that performs async work.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/src/dashboard/src/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "check-cancelled-guards: hooks dir not found: $HOOKS_DIR" >&2
  exit 2
fi

violations=0

# Iterate hook files (skip __tests__ subdirs)
while IFS= read -r -d '' file; do
  # Skip test files
  case "$file" in
    */__tests__/*) continue ;;
  esac

  # Strip eslint-disable-line annotated lines before counting
  stripped="$(grep -v 'eslint-disable-line' "$file" || true)"

  # Does this file do any async work?
  has_await="$(printf '%s\n' "$stripped" | grep -cE '^\s*[^/]*\bawait\b' || true)"
  if [ "${has_await:-0}" -eq 0 ]; then
    continue
  fi

  # Does this file call any state setter?
  has_setter="$(printf '%s\n' "$stripped" | grep -cE '\b(setError|setData|setLoading|setSession|setSessions)\(' || true)"
  if [ "${has_setter:-0}" -eq 0 ]; then
    continue
  fi

  # Does this file contain at least one cancellation guard?
  has_guard="$(printf '%s\n' "$stripped" | grep -cE 'if \(!cancelled\)' || true)"
  if [ "${has_guard:-0}" -eq 0 ]; then
    echo "FAIL: $file — async setters without any 'if (!cancelled)' guard" >&2
    violations=$((violations + 1))
  fi
done < <(find "$HOOKS_DIR" -type f \( -name '*.ts' -o -name '*.tsx' \) -print0)

if [ "$violations" -gt 0 ]; then
  echo "check-cancelled-guards: $violations file(s) failed the cancellation-guard check" >&2
  exit 1
fi

echo "check-cancelled-guards: OK (all hook files conform)"
exit 0
