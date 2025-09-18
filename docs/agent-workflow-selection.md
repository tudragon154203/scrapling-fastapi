# Agent workflow selection at runtime

The repository now exposes a single configuration point to decide which
agent-oriented GitHub Actions workflows should execute for an incoming event.
The workflows affected are:

- `.github/workflows/aider.yml`
- `.github/workflows/claude.yml`
- `.github/workflows/gemini.yml`
- `.github/workflows/opencode.yml`

## Controlling the selection

1. Define or update the repository (or environment/organization) variable
   `ACTIVE_BOTS`.
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
   read the value at runtime and only start the jobs whose identifier is
   present in the array.

If the variable is not defined, or it is left blank, all four workflows run as
before because the workflows fall back to the default list shown above.

## Runtime behaviour

- The selection is evaluated for every run. Changing the variable immediately
  affects subsequent workflow executions.
- A workflow that is not selected is skipped entirely, keeping the workflow
  list tidy without consuming runner minutes.
- The configuration works for pull requests as well as comment-triggered
  events because the `vars` context is resolved before the job condition is
  evaluated.

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

