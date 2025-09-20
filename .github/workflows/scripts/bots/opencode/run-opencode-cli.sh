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

if ! command -v opencode >/dev/null 2>&1; then
  message="opencode CLI is not available on the PATH."
  echo "::error::$message" >&2
  printf '%s\n' "$message" >"$STDERR_FILE"
  printf '%s\n' "exit_code=127" >>"$OUTPUTS_FILE"
  printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
  printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
  exit 0
fi

CONFIG_ROOT="${RUNNER_TEMP:-$(mktemp -d)}"
CONFIG_HOME="$CONFIG_ROOT/opencode-config"
DATA_HOME="$CONFIG_ROOT/opencode-data"
mkdir -p "$CONFIG_HOME" "$DATA_HOME"

if [[ ! -s "$PROMPT_FILE" ]]; then
  echo "::error::Prompt content is empty." >&2
  printf '%s\n' "exit_code=1" >>"$OUTPUTS_FILE"
  printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
  printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
  exit 0
fi

PROMPT_CONTENT=$(<"$PROMPT_FILE")

set +e
# The opencode CLI accepts the prompt as the final positional argument.
NO_COLOR=1 \
  XDG_CONFIG_HOME="$CONFIG_HOME" \
  XDG_DATA_HOME="$DATA_HOME" \
  opencode run --model "$MODEL" "$PROMPT_CONTENT" \
  >"$STDOUT_FILE" 2>"$STDERR_FILE"
EXIT_CODE=$?
set -e

printf 'stdout_file=%s\n' "$STDOUT_FILE" >>"$OUTPUTS_FILE"
printf 'stderr_file=%s\n' "$STDERR_FILE" >>"$OUTPUTS_FILE"
printf 'exit_code=%s\n' "$EXIT_CODE" >>"$OUTPUTS_FILE"
printf 'model=%s\n' "$MODEL" >>"$OUTPUTS_FILE"

exit 0
