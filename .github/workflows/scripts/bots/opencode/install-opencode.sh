#!/bin/bash
set -euo pipefail
curl -fsSL https://opencode.ai/install | bash
echo "$HOME/.opencode/bin" >> "$GITHUB_PATH"
