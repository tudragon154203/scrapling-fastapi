#!/bin/bash
set -euo pipefail
: > aider_review_raw.txt

if [ -z "$GEMINI_API_KEY" ]; then
  echo "::error::GEMINI_API_KEY not available despite prior selection."
  exit 1
fi

echo "::notice::Starting Gemini review with selected key"

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
  echo "success=true" >> "$GITHUB_OUTPUT"
  echo "::notice::Aider review completed successfully."
else
  echo "success=false" >> "$GITHUB_OUTPUT"
  echo "::warning::Aider review failed with status $?"
  exit 0
fi