# API Key Rotation

The `openrouter.py` and `gemini.py` helper scripts rotate between multiple API keys before the respective routers boot. They scan the job environment for variables named with the key prefixes and choose one value using a rotation seed derived from the GitHub Actions run metadata and job name.

## Usage in Workflows

### OpenRouter Keys

Add a step before starting the Claude router that invokes the script:

```yaml
    - name: Select OpenRouter API key
      id: select_openrouter_key
      run: python .github/workflows/scripts/bots/common/rotate_key/openrouter.py \
        --output-selected-name openrouter_secret_name
      env:
        OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        OPENROUTER_API_KEY_2: ${{ secrets.OPENROUTER_API_KEY_2 }}
        OPENROUTER_API_KEY_3: ${{ secrets.OPENROUTER_API_KEY_3 }}
```

### Gemini Keys

Add a step before starting any workflow that uses the Gemini API:

```yaml
    - name: Select Gemini API key
      id: select_gemini_key
      run: python .github/workflows/scripts/bots/common/rotate_key/gemini.py \
        --output-selected-name gemini_secret_name \
      env:
        GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        GEMINI_API_KEY_2: ${{ secrets.GEMINI_API_KEY_2 }}
        GEMINI_API_KEY_3: ${{ secrets.GEMINI_API_KEY_3 }}
```

The scripts export the chosen key through `$GITHUB_ENV`, so later steps automatically receive the rotated value without additional configuration.

The action outputs (`openrouter_secret_name` or `gemini_secret_name`) record which environment variable supplied the key, making it easier to audit runs in workflow logs.

## Adding More Keys

1. Create additional repository organization secrets named with the appropriate prefixes:
   - `OPENROUTER_API_KEY_2`, `OPENROUTER_API_KEY_3`, etc.
   - `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`, etc.
2. Expose those secrets to the rotation step using the `env` block shown above.
   Empty or undefined secrets are ignored automatically, so you can safely list
   more slots than you currently use.
3. Repeat the same step in any other workflow that needs rotating access to the APIs.

## Customizing the Rotation

- Provide a custom seed by setting the `ROTATION_SEED` environment variable or
  passing `--seed` to the script. This is helpful when you want coordinated key
  selection across parallel jobs.
- Override the exported variable name via `--export-name` if the receiving step
  expects a different environment variable.