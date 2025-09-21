#!/usr/bin/env bash
# Install the opencode CLI with retry logic to handle intermittent network issues.

set -euo pipefail

MAX_ATTEMPTS=${OPENCODE_INSTALL_ATTEMPTS:-5}
RETRY_DELAY=${OPENCODE_INSTALL_RETRY_DELAY:-10}
INSTALL_URL=${OPENCODE_INSTALL_URL:-https://opencode.ai/install}

if [[ "$MAX_ATTEMPTS" =~ ^[0-9]+$ ]] && (( MAX_ATTEMPTS > 0 )); then
  :
else
  echo "::error::OPENCODE_INSTALL_ATTEMPTS must be a positive integer." >&2
  exit 2
fi

if [[ "$RETRY_DELAY" =~ ^[0-9]+$ ]] && (( RETRY_DELAY >= 0 )); then
  :
else
  echo "::error::OPENCODE_INSTALL_RETRY_DELAY must be a non-negative integer." >&2
  exit 2
fi

for (( attempt = 1; attempt <= MAX_ATTEMPTS; attempt++ )); do
  if curl -fsSL "$INSTALL_URL" | bash; then
    exit 0
  fi

  if (( attempt < MAX_ATTEMPTS )); then
    echo "::warning::Failed to install opencode CLI (attempt ${attempt}). Retrying in ${RETRY_DELAY} seconds..." >&2
    sleep "$RETRY_DELAY"
  fi

done

echo "::error::Failed to install opencode CLI after ${MAX_ATTEMPTS} attempts." >&2
exit 1
