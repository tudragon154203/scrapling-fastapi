#!/bin/bash
set -euo pipefail

key_present=false

while IFS= read -r env_name; do
  if [[ "$env_name" == GEMINI_API_KEY || "$env_name" == GEMINI_API_KEY_* ]]; then
    value="${!env_name:-}"
    if [ -n "$value" ]; then
      key_present=true
      break
    fi
  fi
done < <(compgen -e)

if [ "$key_present" = false ]; then
  echo "key_present=false" >> "$GITHUB_OUTPUT"
  echo "::notice::Skipping because no Gemini API key secret with prefix GEMINI_API_KEY is set."
else
  echo "key_present=true" >> "$GITHUB_OUTPUT"
fi