# Agent workflow selection at runtime

Incoming pull-request and comment events now land in a single dispatcher
workflow that decides which agent-oriented GitHub Actions should execute. The
dispatcher lives in `.github/workflows/main.yml` (named **🤖 Main (Dispatcher)**)
and calls the
following reusable workflows:

- `.github/workflows/aider.yml`
- `.github/workflows/claude.yml`
- `.github/workflows/gemini.yml`
- `.github/workflows/opencode.yml`

## Controlling the selection

1. Define or update the repository (or environment/organization) variable
   `ACTIVE_BOTS`. Alternatively, export the same JSON array through an
   environment variable named `ACTIVE_BOTS` on the workflow, repository, or
   organization.
2. Give the variable a JSON array that lists the workflows you would like to
   execute. Use the lowercase identifiers shown below:

   ```json
   ["aider", "claude", "gemini", "opencode"]
   ```

   Any subset works, for example:

   ```json
   ["gemini", "opencode"]
   ```

3. Save the variable. No code change is required. The next workflow run will
   read the value at runtime and only call the reusable workflows whose
   identifier is present in the array.

If neither the variable nor the environment variable is defined (or they are
left blank), all four workflows run as before because the workflows fall back
to the default list shown above.

## Runtime behaviour

- The selection is evaluated for every run. Changing the variable immediately
  affects subsequent workflow executions.
- A workflow that is not selected is skipped entirely, so the dispatcher keeps
  the workflow list tidy without consuming runner minutes.
- The configuration works for pull requests as well as comment-triggered events
  because the dispatcher evaluates the JSON list against the original event
  payload before deciding which reusable workflows to invoke.

## Standardised bot triggers

All four bots now follow the same triggering rules, modelled after the
Opencode workflow. The dispatcher enforces the following behaviour:

- **Pull requests:** a workflow only runs when the pull-request author has the
  `OWNER`, `COLLABORATOR`, or `MEMBER` association.
- **Interactive events** (`issue_comment`, `pull_request_review_comment`,
  `pull_request_review`, and `issues`): trusted members can trigger a workflow
  by using the bot-specific prefixes listed below.
- **Command handling:** comments and reviews must start with the prefix
  (for example, `@claude`), while issues trigger when the prefix appears in the
  title or the body.

| Bot      | Accepted prefixes                         |
|----------|-------------------------------------------|
| Aider    | `@aider`, `AIDER`, `/aider`               |
| Claude   | `@claude`, `CLAUDE`, `/claude`            |
| Gemini   | `@gemini`, `@gemini-cli`, `GEMINI`, `/gemini` |
| Opencode | `@opencode`, `OPENCODE`, `/opencode`      |

These rules ensure consistent expectations for contributors regardless of the
agent they choose.

## Troubleshooting

- Make sure the value is valid JSON. Invalid JSON causes GitHub Actions to
  fail while parsing the list. Provide the array exactly as shown above without
  additional escaping.
- Remember that the identifiers are lowercase (`"aider"`, `"claude"`,
  `"gemini"`, `"opencode"`).
- Repository variables can be set through the **Settings → Variables** UI or by
  using the GitHub CLI:

  ```bash
  gh variable set ACTIVE_BOTS --body='["gemini","opencode"]'
  ```

- Environment variables can be exported at different scopes (workflow, job, or
  organization environment). The dispatcher prefers repository variables when
  present and falls back to `env.ACTIVE_BOTS` when that is the only
  configuration provided.

