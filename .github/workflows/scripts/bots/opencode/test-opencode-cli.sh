#!/usr/bin/env bash
# Simple test script for run-opencode-cli.sh

set -euo pipefail

# Create a temporary directory for testing
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "Testing run-opencode-cli.sh in $TEMP_DIR"

# Test 1: Missing opencode CLI
echo "Test 1: Missing opencode CLI"
PROMPT_FILE="$TEMP_DIR/prompt.txt"
STDOUT_FILE="$TEMP_DIR/stdout.txt"
STDERR_FILE="$TEMP_DIR/stderr.txt"
OUTPUTS_FILE="$TEMP_DIR/outputs.txt"

echo "Test prompt" > "$PROMPT_FILE"

# Run with PATH that doesn't include opencode
MODEL="test-model" \
PATH="/bin:/usr/bin" \
 ./.github/workflows/scripts/bots/opencode/run-opencode-cli.sh \
  "$PROMPT_FILE" "$STDOUT_FILE" "$STDERR_FILE" "$OUTPUTS_FILE"

echo "Exit code: $?"
echo "Stdout: $(cat "$STDOUT_FILE")"
echo "Stderr: $(cat "$STDERR_FILE")"
echo "Outputs: $(cat "$OUTPUTS_FILE")"
echo

# Test 2: Empty prompt file
echo "Test 2: Empty prompt file"
: > "$PROMPT_FILE"  # Empty the file

# Add a mock opencode to PATH
MOCK_OPENCODE="$TEMP_DIR/opencode"
echo '#!/bin/sh' > "$MOCK_OPENCODE"
echo 'echo "Mock output"' >> "$MOCK_OPENCODE"
chmod +x "$MOCK_OPENCODE"

MODEL="test-model" \
PATH="$TEMP_DIR:/bin:/usr/bin" \
  ./.github/workflows/scripts/bots/opencode/run-opencode-cli.sh \
  "$PROMPT_FILE" "$STDOUT_FILE" "$STDERR_FILE" "$OUTPUTS_FILE"

echo "Exit code: $?"
echo "Outputs: $(cat "$OUTPUTS_FILE")"
echo

# Test 3: Valid prompt file
echo "Test 3: Valid prompt file"
echo "Test prompt content" > "$PROMPT_FILE"

MODEL="test-model" \
PATH="$TEMP_DIR:/bin:/usr/bin" \
  ./.github/workflows/scripts/bots/opencode/run-opencode-cli.sh \
  "$PROMPT_FILE" "$STDOUT_FILE" "$STDERR_FILE" "$OUTPUTS_FILE"

echo "Exit code: $?"
echo "Stdout: $(cat "$STDOUT_FILE")"
echo "Stderr: $(cat "$STDERR_FILE")"
echo "Outputs: $(cat "$OUTPUTS_FILE")"
echo

echo "All tests completed!"