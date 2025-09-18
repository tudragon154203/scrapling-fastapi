#!/bin/bash
set -euo pipefail
runner_dir=".github/opencode-runner"
rm -rf "$runner_dir"
mkdir -p "$runner_dir"
base_url="https://raw.githubusercontent.com/sst/opencode/v${OPC_VERSION}/github"
curl -fsSL "${base_url}/package.json" -o "$runner_dir/package.json"
curl -fsSL "${base_url}/bun.lock" -o "$runner_dir/bun.lock"
curl -fsSL "${base_url}/index.ts" -o "$runner_dir/index.ts"
if jq -e '.devDependencies["@types/bun"] == "catalog:"' "$runner_dir/package.json" > /dev/null; then
  temp_file=$(mktemp)
  jq '.devDependencies["@types/bun"] = "^1.2.21"' "$runner_dir/package.json" > "$temp_file"
  jq -S . "$temp_file" > "$runner_dir/package.json"
  rm "$temp_file"
fi
echo "RUNNER_DIR=$runner_dir" >> "$GITHUB_ENV"