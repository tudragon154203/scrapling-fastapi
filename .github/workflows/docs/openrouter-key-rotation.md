# OpenRouter API Key Rotation

The `rotate_openrouter_key.py` helper script rotates between multiple
`OPENROUTER_API_KEY` secrets before the Claude router boots.  It scans the job
environment for variables named `OPENROUTER_API_KEY`, `OPENROUTER_API_KEY_2`,
`OPENROUTER_API_KEY_3`, and so on.  The script chooses one value using a
rotation seed derived from the GitHub Actions run metadata and exports it to the
shared environment for subsequent steps.

## Usage in Workflows

Add a step before starting the Claude router that invokes the script:

```yaml
    - name: Select OpenRouter API key
      id: select_openrouter_key
      run: python .github/workflows/scripts/rotate_openrouter_key.py \
        --output-selected-name openrouter_secret_name
      env:
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        OPENROUTER_API_KEY_2: ${{ secrets.OPENROUTER_API_KEY_2 }}
        OPENROUTER_API_KEY_3: ${{ secrets.OPENROUTER_API_KEY_3 }}
```

The script exports the chosen key through `$GITHUB_ENV`, so later steps (such as
`setup_router.sh`) automatically receive the rotated value without additional
configuration.

The action output `openrouter_secret_name` records which environment variable
supplied the key, making it easier to audit runs in workflow logs.

## Adding More Keys

1. Create additional repository or organization secrets named
   `OPENROUTER_API_KEY_2`, `OPENROUTER_API_KEY_3`, etc.
2. Expose those secrets to the rotation step using the `env` block shown above.
   Empty or undefined secrets are ignored automatically, so you can safely list
   more slots than you currently use.
3. Repeat the same step in any other workflow that needs rotating access to the
   OpenRouter API.

## Customizing the Rotation

- Provide a custom seed by setting the `ROTATION_SEED` environment variable or
  passing `--seed` to the script.  This is helpful when you want coordinated key
  selection across parallel jobs.
- Override the exported variable name via `--export-name` if the receiving step
  expects a different environment variable.
