# Emoji reactions in agent workflows

The reusable agent workflows post emoji reactions on the triggering pull request,
issue, or comment when they start running. The reactions are added through the
shared helper script at `.github/workflows/scripts/bots/common/javascript/react_with_emoji.cjs`,
which inspects the original event payload and attaches the configured emoji to the
appropriate object. When no explicit emoji is supplied, the helper falls back to 👀
(`eyes`).

## Workflow overview

| Workflow | Emoji | Reaction content | Purpose |
| --- | --- | --- | --- |
| `.github/workflows/aider.yml` | ❤️ | `heart` | Signals that the Aider reviewer picked up the event. |
| `.github/workflows/claude.yml` | 👀 | `eyes` | Highlights that the Claude Code workflow is now watching the thread. |
| `.github/workflows/gemini.yml` | 😄 | `laugh` | Indicates that the Gemini workflow has started processing. |
| `.github/workflows/opencode.yml` | 🎉 | `hooray` | Shows that the Opencode CLI workflow is running. |
| `codex` (planned) | 👀 / 👍 | `eyes` while the Codex workflow runs. Switch to `+1` ("like") when the PR is ready to merge. | Signals how a future Codex workflow should communicate its status even though it is not yet in the repository. |

## Adding or updating reactions

1. Decide which emoji should represent the workflow. Consult the
   [supported reaction content values](https://docs.github.com/en/rest/reactions/reactions?apiVersion=2022-11-28#create-reaction-for-an-issue)
   to ensure the selection is valid.
2. Update the relevant workflow step by passing the desired reaction name to
   `reactWithEmoji`. If you omit the `reaction` argument, the helper defaults to 👀.
3. When introducing a brand-new workflow, reuse the helper script to keep the
   behaviour consistent. If you need multi-stage reactions (such as Codex's
   planned switch from 👀 to 👍 once a PR looks good), extend the helper to apply
   the follow-up reaction when the success condition is met.

These reactions provide a lightweight status signal for maintainers and
contributors who watch the repository activity feed. They also help distinguish
which automation responded to a given event when multiple bots operate in the
same thread.
