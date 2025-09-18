#!/bin/bash
set -euo pipefail

PR_TITLE=$(echo "$EVENT_PAYLOAD" | python -c "import sys, json; data=json.load(sys.stdin); print(data['pull_request']['title'] if 'pull_request' in data else '')")
PR_URL=$(echo "$EVENT_PAYLOAD" | python -c "import sys, json; data=json.load(sys.stdin); print(data['pull_request']['html_url'] if 'pull_request' in data else '')")
BASE_SHA=$(echo "$EVENT_PAYLOAD" | python -c "import sys, json; data=json.load(sys.stdin); print(data['pull_request']['base']['sha'] if 'pull_request' in data else '')")
BASE_REF=$(echo "$EVENT_PAYLOAD" | python -c "import sys, json; data=json.load(sys.stdin); print(data['pull_request']['base']['ref'] if 'pull_request' in data else '')")
HEAD_SHA=$(echo "$EVENT_PAYLOAD" | python -c "import sys, json; data=json.load(sys.stdin); print(data['pull_request']['head']['sha'] if 'pull_request' in data else '')")

git config --global --add safe.directory "$GITHUB_WORKSPACE"
if ! git cat-file -e "$BASE_SHA^{commit}"; then
  git fetch origin "$BASE_REF" --depth=1
fi
git diff "$BASE_SHA...$HEAD_SHA" > pr.diff || true
diff_bytes=$(wc -c < pr.diff)
echo "diff_bytes=$diff_bytes" >> "$GITHUB_OUTPUT"
if [ "$diff_bytes" -eq 0 ]; then
  echo "no_diff=true" >> "$GITHUB_OUTPUT"
else
  echo "no_diff=false" >> "$GITHUB_OUTPUT"
fi
max_bytes=60000
if [ "$diff_bytes" -gt "$max_bytes" ]; then
  head -c "$max_bytes" pr.diff > pr.truncated.diff
  mv pr.truncated.diff pr.diff
  echo "diff_truncated=true" >> "$GITHUB_OUTPUT"
else
  echo "diff_truncated=false" >> "$GITHUB_OUTPUT"
fi
mkdir -p .github/aider
{
  printf '%s\n' "You are an experienced software engineer performing a thorough code review for the GitHub pull request below."
  printf '%s\n' "This automation only provides read-only feedback, so no code changes are required."
  printf '%s\n' "Do not offer to edit files, apply patches, or ask for confirmation to make changes."
  printf '%s\n' ""
  printf '%s\n' "Respond in Markdown beginning with the heading ### 📝 Aider Review followed by exactly three level-3 headings in this order: ### ✅ Summary, ### ⚠️ Issues, and ### 💡 Suggestions. Do not add any other sections."
  printf '%s\n' "- **✅ Summary**: Provide 1-3 short bullet points covering the most important changes."
  printf '%s\n' "- **⚠️ Issues**: Bullet any bugs, regressions, or risks. Reference files and line numbers when helpful. Write 'None.' if you find no issues."
  printf '%s\n' "- **💡 Suggestions**: Offer actionable improvements, testing ideas, or follow-up work. Write 'None.' if you have no suggestions."
  printf '%s\n' ""
  printf '%s\n' "Keep bullets tight, prefix each bullet with a fitting emoji, and focus on correctness, security, performance, and maintainability. If the diff was truncated for length, mention it explicitly."
  printf '%s\n' ""
  printf '%s\n' "Pull request: $PR_TITLE"
  printf '%s\n' "URL: $PR_URL"
  printf '%s\n' ""
  printf '%s\n' "Diff:"
  printf '%s\n' '```diff'
} > .github/aider/review_prompt.md
cat pr.diff >> .github/aider/review_prompt.md
printf '\n```\n' >> .github/aider/review_prompt.md