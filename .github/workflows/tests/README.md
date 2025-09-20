# Opencode Workflow Tests

This directory contains tests for the opencode GitHub workflow scripts.

## Test Structure

- `python/` - Python unit tests
  - `bots/` - Tests for workflow bot helpers, grouped by dispatcher, formatter, and opencode utilities
  - `rotate_key/` - Tests for the shared rotate_key helpers and rotation scripts
- `js/` - JavaScript unit tests
- `integration/` - Integration tests that require external services

## Configuration

The tests can be configured using environment variables or a `.env` file.

### Environment Variables

- `OPENROUTER_API_KEY` - API key for OpenRouter models (required for integration tests)
- `OPENCODE_TEST_MODEL` - Model to use for testing (default: `openrouter/z-ai/glm-4.5-air:free`)

### Configuration File

Set your API keys in `.github/workflows/scripts/core/.env`:

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENCODE_TEST_MODEL=openrouter/nousresearch/hermes-3-llama-3.1-405b
```

The configuration system will automatically load this file if it exists.

## Running Tests

### Unit Tests

Run the unit tests with pytest:

```bash
python -m pytest .github/workflows/tests/python/ .github/workflows/tests/js/ -v
```

### Integration Tests

Integration tests are marked with `@pytest.mark.integration` and are not run by default.

The integration tests require:

1. The opencode CLI to be installed
2. API keys for the model providers
3. Internet connectivity

#### Installing opencode CLI

```bash
curl -fsSL https://opencode.ai/install | bash
```

#### Running Integration Tests

To run the integration tests, you need to set the required environment variables or configure `.github/workflows/scripts/core/.env`:

```bash
export OPENROUTER_API_KEY=your_openrouter_api_key_here
python -m pytest .github/workflows/tests/integration/ -v -s
```

Or set your API key in `.github/workflows/scripts/core/.env` and run:

```bash
python -m pytest .github/workflows/tests/integration/ -v -s
```

#### Testing with Custom Models

You can test with different models by setting the `OPENCODE_TEST_MODEL` environment variable or adding it to `.env`:

```bash
export OPENROUTER_API_KEY=your_openrouter_api_key_here
export OPENCODE_TEST_MODEL=openrouter/nousresearch/hermes-3-llama-3.1-405b
python -m pytest .github/workflows/tests/integration/test_opencode_cli.py::test_opencode_cli_with_custom_model -v -s
```

Alternatively, add the model to `.github/workflows/scripts/core/.env`:

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENCODE_TEST_MODEL=openrouter/nousresearch/hermes-3-llama-3.1-405b
```

Then run:

```bash
python -m pytest .github/workflows/tests/integration/test_opencode_cli.py::test_opencode_cli_with_custom_model -v -s
```

#### Running Specific Tests

Run only the main integration test:

```bash
python -m pytest .github/workflows/tests/integration/test_opencode_cli.py::test_opencode_cli_integration -v -s
```

Run the error handling test:

```bash
python -m pytest .github/workflows/tests/integration/test_opencode_cli.py::test_opencode_cli_error_handling -v -s
```

## Test Descriptions

### Unit Tests

Unit tests are in the `python/` and `js/` directories and test individual components in isolation.

### Integration Tests

Integration tests in the `integration/` directory test real interactions with external services:

- `test_opencode_cli.py` - Real tests that call the opencode CLI with actual models:
  - `test_opencode_cli_integration` - Basic test with a simple prompt
  - `test_opencode_cli_with_custom_model` - Test with configurable model
  - `test_opencode_cli_error_handling` - Test error handling with invalid API key

## Skipping Tests

Tests will be automatically skipped if:
- Required environment variables are not set
- opencode CLI is not installed or not in PATH