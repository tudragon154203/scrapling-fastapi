#!/usr/bin/env bash
# Post the generated comment to the appropriate GitHub target.

set -euo pipefail

TARGET_TYPE=${1:-}
TARGET_ID=${2:-}
COMMENT_FILE=${3:?"Missing comment file argument."}

if [[ -z "$TARGET_ID" ]]; then
  echo "No target ID provided; skipping comment post."
  exit 0
fi

if [[ ! -f "$COMMENT_FILE" ]]; then
  echo "::error::Comment body file '$COMMENT_FILE' does not exist." >&2
  exit 1
fi

if [[ "$TARGET_TYPE" == "pull_request" ]]; then
  echo "Posting comment to pull request #$TARGET_ID..."
  gh pr comment "$TARGET_ID" --body-file "$COMMENT_FILE"
else
  local_type=${TARGET_TYPE:-issue}
  echo "Posting comment to ${local_type} #$TARGET_ID..."
  gh issue comment "$TARGET_ID" --body-file "$COMMENT_FILE"
fi
