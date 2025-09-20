#!/usr/bin/env bash
# Run the opencode CLI with a prompt streamed from a file.

set -euo pipefail

PROMPT_FILE=${1:?"Missing prompt file argument."}
STDOUT_FILE=${2:?"Missing stdout file argument."}
STDERR_FILE=${3:?"Missing stderr file argument."}
OUTPUTS_FILE=${4:?"Missing outputs file argument."}

if [[ -z "${MODEL:-}" ]]; then
  echo "::error::MODEL environment variable is not set." >&2
  exit 1
fi

mkdir -p "$(dirname "$STDOUT_FILE")" "$(dirname "$STDERR_FILE")"
: >"$STDOUT_FILE"
: >"$STDERR_FILE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v opencode >/dev/null 2>&1; then
  message="opencode CLI is not available on the PATH."
  echo "::error::$message" >&2
  printf '%s\n' "$message" >"$STDERR_FILE"
  printf '%s\n' "exit_code=127" >>"$OUTPUTS_FILE"
  printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
  printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
  exit 0
fi

if ! CANONICAL_MODEL="$(python "$SCRIPT_DIR/canonicalize-model.py" "$MODEL")"; then
  echo "::error::Failed to canonicalize model identifier '$MODEL'." >&2
  printf '%s\n' "exit_code=1" >>"$OUTPUTS_FILE"
  printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
  printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
  exit 0
fi

if [[ -z "$CANONICAL_MODEL" ]]; then
  echo "::error::Canonical model identifier resolved to an empty string." >&2
  printf '%s\n' "exit_code=1" >>"$OUTPUTS_FILE"
  printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
  printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
  exit 0
fi

CONFIG_ROOT="${RUNNER_TEMP:-$(mktemp -d)}"
CONFIG_HOME="$CONFIG_ROOT/opencode-config"
DATA_HOME="$CONFIG_ROOT/opencode-data"
mkdir -p "$CONFIG_HOME/opencode" "$DATA_HOME"
CONFIG_FILE="$CONFIG_HOME/opencode/.opencode.json"

cat >"$CONFIG_FILE" <<JSON
{
  "agents": {
    "coder": {"model": "$CANONICAL_MODEL"},
    "summarizer": {"model": "$CANONICAL_MODEL"},
    "task": {"model": "$CANONICAL_MODEL"},
    "title": {"model": "$CANONICAL_MODEL"}
  }
}
JSON

PROMPT_CONTENT=$(<"$PROMPT_FILE")

set +e
XDG_CONFIG_HOME="$CONFIG_HOME" \
  XDG_DATA_HOME="$DATA_HOME" \
  opencode \
    --prompt "$PROMPT_CONTENT" \
    --output-format text \
    --quiet \
    >"$STDOUT_FILE" 2>"$STDERR_FILE"
EXIT_CODE=$?
set -e

printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
printf 'exit_code=%s\n' "$EXIT_CODE" >>"$OUTPUTS_FILE"
printf 'model=%s\n' "$CANONICAL_MODEL" >>"$OUTPUTS_FILE"

exit 0
