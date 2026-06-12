#!/usr/bin/env bash
# post-go-public-protect.sh — apply main-branch protection immediately after
# Plan 120-05 visibility flip. Locked ruleset per
# .planning/phases/120-go-public-remediation/120-CONTEXT.md.
#
# Modes:
#   --dry-run   Print the protection payload and the would-PUT URL. Exit 0.
#   --apply     PUT the payload to GitHub. Exit 0 on success, 1 on failure.
#   --verify    GET current protection and assert the locked invariants.
#
# Exit codes:
#   0  success / all assertions passed
#   1  apply or verify failure
#   2  usage error (no mode arg / unknown arg)
set -euo pipefail

MODE="${1:-}"

usage() {
  cat >&2 <<USAGE
Usage: $0 (--dry-run | --apply | --verify)

  --dry-run   Print the payload and the target URL; do not modify anything.
  --apply     Apply locked branch-protection ruleset to main.
  --verify    Assert current protection matches the locked invariants.

Run --dry-run first to confirm payload; --apply only immediately after
the gh repo edit --visibility public flip; --verify any time after apply.
USAGE
}

if [ -z "$MODE" ] || [ "$MODE" = "-h" ] || [ "$MODE" = "--help" ]; then
  usage
  exit 2
fi

# Resolve owner/repo from gh's view of the current working directory.
OWNER_REPO=$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')
OWNER=$(printf '%s' "$OWNER_REPO" | cut -d/ -f1)
REPO=$(printf '%s' "$OWNER_REPO" | cut -d/ -f2)

# Locked protection payload (Phase 120 CONTEXT — Post-flip branch-protection script).
# enforce_admins=false is the documented solo-dev convenience override (T-120-20 accepted).
PAYLOAD=$(cat <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Windows Sensor Smoke"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false,
  "required_conversation_resolution": false
}
JSON
)

case "$MODE" in
  --dry-run)
    echo "$PAYLOAD" | jq .
    echo "Would PUT repos/$OWNER/$REPO/branches/main/protection"
    exit 0
    ;;

  --apply)
    if ! echo "$PAYLOAD" | gh api -X PUT "repos/$OWNER/$REPO/branches/main/protection" --input -; then
      echo "ERROR: gh api PUT failed for repos/$OWNER/$REPO/branches/main/protection" >&2
      exit 1
    fi
    echo "applied: repos/$OWNER/$REPO/branches/main/protection"
    exit 0
    ;;

  --verify)
    CURRENT=$(gh api "repos/$OWNER/$REPO/branches/main/protection")
    echo "$CURRENT" | jq .

    FAILED=0
    assert() {
      local label="$1"
      local jq_expr="$2"
      local got
      got=$(echo "$CURRENT" | jq -r "$jq_expr")
      if [ "$got" != "true" ]; then
        echo "FAIL: $label  (got: $got)" >&2
        FAILED=1
      else
        echo "PASS: $label"
      fi
    }

    assert "required_status_checks.contexts includes Windows Sensor Smoke" \
      '(.required_status_checks.contexts | index("Windows Sensor Smoke")) != null'
    assert "enforce_admins.enabled == false" \
      '.enforce_admins.enabled == false'
    assert "allow_force_pushes.enabled == false" \
      '.allow_force_pushes.enabled == false'
    assert "allow_deletions.enabled == false" \
      '.allow_deletions.enabled == false'
    assert "required_pull_request_reviews is non-null" \
      '.required_pull_request_reviews != null'

    if [ "$FAILED" -ne 0 ]; then
      echo "VERIFY FAILED" >&2
      exit 1
    fi
    echo "OK"
    exit 0
    ;;

  *)
    echo "ERROR: unknown mode '$MODE'" >&2
    usage
    exit 2
    ;;
esac
