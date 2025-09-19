#!/bin/bash
set -euo pipefail
version="$(opencode --version | tr -d '\n')"
echo "version=${version}" >> "$GITHUB_OUTPUT"
