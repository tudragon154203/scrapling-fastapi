# Stable AI Workflows for GitHub Actions

This directory contains stable, production-ready GitHub Actions workflows for AI-assisted code reviews, issue triage, and interactive responses in pull requests (PRs) and issues. These workflows leverage AI models like Aider, Claude, and Gemini to automate feedback, analysis, and assistance.

The workflows are designed to be modular:

- **Standalone workflows** in the `standalone/` subdirectory can be copied directly to `.github/workflows/` and run independently.
- The `dispatcher_stable_v1.zip` provides a composite dispatcher that orchestrates multiple AI agents based on events.

All workflows require an environment named `Agents/Bots` (create it in your repository settings if needed) and specific API secrets for the AI providers.

## Standalone Workflows

These YAML files are self-contained and can be copied to `.github/workflows/` to enable AI automation. They trigger on PRs, issues, or comments and post responses via GitHub comments.

### 📝 Aider Review (`aider-stable.yml`)

**Purpose**: Performs automated code reviews on pull requests using the Aider tool powered by Google's Gemini model. It analyzes diffs, identifies issues, and provides structured feedback without making changes.

**Triggers**:

- Pull request: `opened`, `synchronize`, `reopened`, `ready_for_review`

**Requirements**:

- **Secrets**: At least one of `GEMINI_API_KEY`, `GEMINI_API_KEY_2`
- **Environment**: `Agents/Bots`
- **Permissions**: `contents: read`, `pull-requests: write`, `issues: write`
- **Runtime**: Ubuntu Latest, Python 3.11, Aider installed via pip

**How it Works**:

1. Checks for Gemini API keys.
2. Generates a PR diff (truncated if >60KB).
3. Creates a review prompt including the diff and instructions for structured output.
4. Runs Aider in dry-run mode to generate the review.
5. Formats and posts the review as a PR comment with sections: `### ✅ Summary`, `### ⚠️ Issues`, `### 💡 Suggestions`.
6. Retries with alternate keys if needed; skips if no keys or no diff.

**Output**: A Markdown comment on the PR with emoji-prefixed bullets. If diff truncated, it's noted. Skips non-contributor PRs.

**Customization**: Edit the prompt in the workflow script for review style. Timeout: 30 minutes.

### 🤖 Claude Assistant (`claude-stable.yml`)

**Purpose**: Acts as an interactive AI assistant (Claude) that responds to mentions in issues, PRs, comments, and reviews. It uses a code router for multi-provider support and GitHub tools for interactions like commenting or inline suggestions.

**Triggers**:

- Pull requests: `opened`, `synchronize`, `reopened`
- Issue comments: `created`, `edited` (if starts with `@claude`, `CLAUDE`, or `/claude`)
- PR review comments: `created`, `edited` (same triggers)
- Issues: `opened`, `assigned`, `reopened` (if body/title contains triggers)
- PR reviews: `submitted`, `edited` (if body starts with triggers)

**Requirements**:

- **Secrets**: `OPENROUTER_API_KEY` (primary), `GEMINI_API_KEY` (fallback)
- **Environment**: `Agents/Bots`
- **Permissions**: `contents: write`, `pull-requests: write`, `issues: write`, `id-token: write`, `actions: read`
- **Runtime**: Ubuntu 22.04, Bun runtime for the code router

**How it Works**:

1. Checks author association (OWNER/COLLABORATOR/MEMBER).
2. Sets up Claude Code Router with config for OpenRouter (free models like Qwen, GLM, Kimi, DeepSeek) and Gemini fallback.
3. Starts the router server locally.
4. Runs Claude Code Action with a prompt for GitHub assistance (review PRs, triage issues, respond to requests).
5. Allows tools like `gh pr comment`, inline comments on diffs, and GitHub CLI commands.

**Output**: Posts comments or inline suggestions based on the interaction. Uses router for load balancing across models.

**Customization**: Modify the router config.json for models/providers. Supports long context with Gemini. API timeout: 60s.

### 🪐 Gemini Reviewer v1.1 (`gemini-stable-v1.1.yml`)

**Purpose**: Provides advanced, structured PR reviews using Google's Gemini CLI. Includes detailed context (files, diffs, commits) and responds to mentions in comments. Reacts with 👀 to indicate activity.

**Triggers**:

- Pull requests: `opened`, `reopened`, `synchronize`
- Issue/PR review comments: `created`, `edited` (if starts with `Gemini`, `GEMINI`, `@gemini`, `@gemini-cli`, or `/gemini`)

**Requirements**:

- **Secrets**: `GEMINI_API_KEY`
- **Variables**: `GEMINI_MODEL` (default: `gemini-2.5-flash`)
- **Environment**: `Agents/Bots`
- **Permissions**: `id-token: write`, `contents: write`, `pull-requests: write`, `issues: write`
- **Runtime**: Ubuntu Latest, Node.js 20

**How it Works**:

1. Adds 👀 reaction to the PR/issue/comment.
2. Skips if no API key.
3. Prepares a detailed prompt: loads PR context (title, description, files with patches truncated at 1.5KB, commits), user request from comment.
4. Runs Gemini CLI with the prompt, enforcing a response template (Summary, Tests & Coverage, Risks, Suggestions, Follow-ups, Blocking Issues).
5. Posts the formatted response as a comment, including errors if any.

**Output**: Structured Markdown comment with sections. Handles errors gracefully. Fails workflow only if CLI step fails.

**Customization**: Adjust model via repo variable. Prompt emphasizes tests, risks, and blockers. Use for thorough reviews.

### 🪐 Gemini Reviewer v1 (`gemini-stable-v1.yml`) - Legacy

**Purpose**: Simpler version for basic PR summaries and responses to Gemini mentions. Less detailed than v1.1 (no file diffs/commits).

**Triggers**: Same as v1.1.

**Requirements**: Identical to v1.1.

**How it Works**:

1. Prepares basic prompt with PR title, description, or comment body.
2. Runs Gemini CLI for concise summary/risks/follow-ups.
3. Posts response if successful.

**Note**: Prefer v1.1 for richer context. This is maintained for backward compatibility.

## Dispatcher Workflow (`dispatcher_stable_v1.zip`)

**Purpose**: A composite workflow that dispatches events to the appropriate standalone AI workflow (Aider, Claude, Gemini) based on configuration. Ensures coordinated AI responses without duplication.

**Usage**:

- Extract the ZIP to `.github/workflows/` (overwrites if exists).
- Ensure standalone YAMLs are in place or referenced.
- Triggers: Configurable, typically on PR/issue events.
- Requirements: Same as standalones (secrets, environment).
- The ZIP includes a main dispatcher YAML and supporting scripts/filters (e.g., for bot dispatching).

**How it Works**:

- Uses event filters to route to specific agents.
- Extracts together as a set; do not use individually from ZIP.

**Customization**: Edit the dispatcher YAML for routing logic. See extracted files for details.

### dispatcher_stable_v1.1.zip vs dispatcher_stable_v1.zip

Use v1.1 when you need the richer automation shipped after v1. Key upgrades include:

- **Key rotation & secrets handling**: v1.1 replaces the shell-based `check_gemini_keys.sh` with the reusable Python rotators in `scripts/bots/common/rotate_key/`, unlocks up to five Gemini/OpenRouter keys, and propagates the chosen secret name to downstream steps.
- **Dispatcher insights**: v1.1 extends `dispatcher_filter.py` to parse CSV/JSON inputs, exports the active filter as text/JSON, captures the target ID/type, and feeds a new `dispatcher_summary.py` job summary so you can see which bots triggered.
- **Default dispatch behaviour**: v1.1 sets the default `ACTIVE_BOTS_VAR` to `["aider", "gemini", "claude"]`, refines Opencode pull-request rules to rely on author trust, and adds emoji reactions that surface when a bot picks up the event.
- **Workflow coverage**: v1.1 bundles fresh `ci-pull-request.yml` and `ci-push.yml` entry points, refreshes `ci-workflows.yml`, and adds authored docs under `docs/` for agent-selection, API key rotation, and emoji conventions.
- **Opencode agent overhaul**: v1.1 introduces a Python prompt builder, CLI runner wrappers, comment formatter, and cross-platform launchers under `scripts/bots/opencode/`; v1 only shipped installer/runner shell scripts.
- **Quality checks**: v1.1 ships Jest/pytest suites in `tests/` (JavaScript emoji helpers and prompt generators, Python dispatchers/key rotators/opencode formatters, CLI integration harness stubs) that were absent from v1.
- v.1.2: improve build_comment of opencode

## Setup Instructions

1. **Copy Standalone Workflows**:

   - Navigate to `.github/workflows/stable/standalone/`.
   - Copy desired `.yml` files (e.g., `cp aider-stable.yml ../../`).
   - Commit and push to enable.
2. **Configure Secrets**:

   - Go to repo Settings > Secrets and variables > Actions.
   - Add API keys: `GEMINI_API_KEY` (required for Aider/Gemini), `OPENROUTER_API_KEY` (for Claude).
   - Optional: Multiple Gemini keys for failover.
3. **Set Up Environment**:

   - Settings > Environments > New environment: `Agents/Bots`.
   - Add protection rules if needed (e.g., required reviewers).
4. **Dispatcher Setup**:

   - Unzip `dispatcher_stable_v1.zip` to `.github/workflows/`.
   - Verify extracted files (e.g., main dispatcher YAML, scripts).
   - Configure any variables/secrets.
5. **Test**:

   - Create a test PR or comment `@gemini review this` / `@claude help`.
   - Check Actions tab for logs; monitor API costs.
6. **Permissions**:

   - Workflows request minimal scopes; approve if prompted.

## Best Practices and Notes

- **Cost Management**: AI calls incur API fees (e.g., Gemini ~$0.0001/1K tokens). Use free tiers where possible (OpenRouter free models).
- **Rate Limits**: Workflows include retries/timeouts; monitor GitHub Actions minutes.
- **Security**: Secrets are environment-protected. Avoid logging sensitive data.
- **Customization**: Edit prompts in YAMLs for domain-specific feedback (e.g., add security checks).
- **Troubleshooting**:
  - No response? Check secrets/environment approval.
  - Errors? View workflow logs; common issues: invalid API keys, large diffs.
  - Update models: Change via variables (e.g., `GEMINI_MODEL=gemini-2.0-pro`).
- **External Resources**:
  - [Aider Docs](https://aider.chat/)
  - [Claude Code Action](https://github.com/anthropics/claude-code-action)
  - [Gemini CLI Action](https://github.com/google-github-actions/run-gemini-cli)
  - GitHub Environments: [Docs](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)

These workflows enhance collaboration with AI while maintaining control. For issues, open a GitHub issue mentioning the bot (e.g., `@claude bug`).
