#!/usr/bin/env bash
set -euo pipefail

# Load environment variables from .claude/mcp.env if present
if [ -f "$(dirname "$0")/../.claude/mcp.env" ]; then
  # shellcheck disable=SC1091
  set -a
  source "$(dirname "$0")/../.claude/mcp.env"
  set +a
fi

if [ -z "${BRAVE_API_KEY:-}" ]; then
  echo "Error: BRAVE_API_KEY is not set. Set it in your environment or in .claude/mcp.env." >&2
  exit 1
fi

exec npx -y @modelcontextprotocol/server-brave-search "$@"
