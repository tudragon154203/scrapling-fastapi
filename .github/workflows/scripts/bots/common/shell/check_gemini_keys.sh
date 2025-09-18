#!/bin/bash
set -euo pipefail

if [ -z "${GEMINI_API_KEY:-}" ] && [ -z "${GEMINI_API_KEY_2:-}" ] && [ -z "${GEMINI_API_KEY_LEGACY:-}" ]; then
  echo "key_present=false" >> "$GITHUB_OUTPUT"
  echo "::notice::Skipping because no Gemini API key secret (GEMINI_API_KEY, GEMINI_API_KEY_2, or legacy GEMINI_API_KEY_LEGACY) is set."
else
  echo "key_present=true" >> "$GITHUB_OUTPUT"
fi