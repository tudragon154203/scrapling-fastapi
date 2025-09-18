#!/bin/bash
set -euo pipefail
: > aider_review_raw.txt

keys=()
if [ -n "$GEMINI_API_KEY_2" ]; then
  keys+=("$GEMINI_API_KEY_2")
fi
if [ -n "$GEMINI_API_KEY" ]; then
  keys+=("$GEMINI_API_KEY")
fi
if [ -n "$GEMINI_API_KEY_LEGACY" ]; then
  keys+=("$GEMINI_API_KEY_LEGACY")
fi

max_attempts=${#keys[@]}
if [ "$max_attempts" -eq 0 ]; then
  echo "::error::No Gemini API keys available despite prior check."
  exit 1
fi
success=false
for index in "${!keys[@]}"; do
  key="${keys[$index]}"
  export GEMINI_API_KEY="$key"
  export AIDER_GEMINI_API_KEY="$key"
  echo "::notice::Starting Gemini credential attempt $((index + 1)) of $max_attempts"
  if aider \
     --model "gemini/${GEMINI_MODEL}" \
     --max-chat-history-tokens 120000 \
     --dry-run \
     --no-auto-commits \
     --no-pretty \
     --no-stream \
     --no-gitignore \
     --no-check-update \
     --no-show-release-notes \
     --disable-playwright \
     --message-file .github/aider/review_prompt.md \
     2>&1 | tee -a aider_review_raw.txt; then
    success=true
    echo "::notice::Aider review completed after $((index + 1)) attempt(s)."
    break
  fi

  status=$?
  echo "::warning::Aider attempt $((index + 1)) failed with status $status"
done

if [ "$success" = "true" ]; then
  echo "success=true" >> "$GITHUB_OUTPUT"
else
  echo "success=false" >> "$GITHUB_OUTPUT"
  exit 0
fi