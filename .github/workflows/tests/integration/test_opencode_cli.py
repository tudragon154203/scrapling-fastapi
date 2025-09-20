"""Integration tests for the opencode CLI."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from pathlib import Path

import pytest

# Try to import the centralized config
try:
    from ....workflows.scripts.core.config import config
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    config = None

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

def _run_script(script_path: Path, args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Run a script with appropriate shell settings for the platform."""
    if platform.system() == "Windows":
        # On Windows, we need to run shell scripts through bash
        # Check if bash is available
        try:
            subprocess.run(["bash", "--version"], check=True, capture_output=True)
            cmd = ["bash", str(script_path)] + args
            return subprocess.run(cmd, env=env, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # If bash is not available, try to run directly (might work with WSL or git bash)
            try:
                return subprocess.run([str(script_path)] + args, env=env, capture_output=True, text=True, shell=True)
            except FileNotFoundError:
                # If that fails, raise the original error
                raise FileNotFoundError("Cannot execute shell script on Windows. Please install bash (Git Bash, WSL, or Cygwin).")
    else:
        # On Unix-like systems, run directly
        return subprocess.run([str(script_path)] + args, env=env, capture_output=True, text=True)


def test_opencode_cli_integration() -> None:
    """Test opencode CLI with real model and API key.
    
    This test requires:
    1. opencode CLI to be installed and available in PATH
    2. OPENROUTER_API_KEY environment variable to be set
    3. Internet connection to reach the model API
    
    To run this test:
    export OPENROUTER_API_KEY=your_api_key_here
    python -m pytest .github/workflows/tests/integration/test_opencode_cli.py -v -s
    """
    # Use centralized config if available, otherwise fall back to environment variables
    if HAS_CONFIG and config:
        api_key = config.openrouter_api_key
        test_model = config.test_model
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        test_model = os.environ.get("OPENCODE_TEST_MODEL", "openrouter/z-ai/glm-4.5-air:free")
    
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")
    
    # Check if opencode CLI is available
    try:
        subprocess.run(["opencode", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("opencode CLI not found in PATH")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        prompt_file = temp_path / "prompt.txt"
        stdout_file = temp_path / "stdout.txt"
        stderr_file = temp_path / "stderr.txt"
        outputs_file = temp_path / "outputs.txt"
        
        # Create a simple prompt file
        prompt_content = "Say 'Hello, World!' and nothing else."
        prompt_file.write_text(prompt_content)
        
        # Set up environment
        env = os.environ.copy()
        env["MODEL"] = test_model
        env["OPENROUTER_API_KEY"] = api_key
        
        # Run the script
        script_path = Path(__file__).resolve().parents[3] / ".github/workflows/scripts/bots/opencode/run-opencode-cli.sh"
        try:
            result = _run_script(script_path, [str(prompt_file), str(stdout_file), str(stderr_file), str(outputs_file)], env)
        except FileNotFoundError as e:
            pytest.skip(str(e))
        
        # Check that the script exits with code 0 (as designed)
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        
        # Check that output files were created
        assert stdout_file.exists(), "stdout file was not created"
        assert stderr_file.exists(), "stderr file was not created"
        assert outputs_file.exists(), "outputs file was not created"
        
        # Read output files
        stdout_content = stdout_file.read_text()
        stderr_content = stderr_file.read_text()
        outputs_content = outputs_file.read_text()
        
        # Parse outputs
        outputs = {}
        for line in outputs_content.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                outputs[key] = value
        
        # Check exit code
        exit_code = int(outputs.get('exit_code', -1))
        assert exit_code == 0, f"opencode CLI exited with code {exit_code}. Stderr: {stderr_content}"
        
        # Check that we got some output
        assert len(stdout_content.strip()) > 0, "stdout is empty"
        assert "Hello, World!" in stdout_content, f"Expected 'Hello, World!' in output: {stdout_content}"


def test_opencode_cli_with_custom_model() -> None:
    """Test opencode CLI with a custom model specified via environment variable."""
    # Use centralized config if available, otherwise fall back to environment variables
    if HAS_CONFIG and config:
        api_key = config.openrouter_api_key
        test_model = config.test_model
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        test_model = os.environ.get("OPENCODE_TEST_MODEL", "openrouter/z-ai/glm-4.5-air:free")
    
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")
    
    # Check if opencode CLI is available
    try:
        subprocess.run(["opencode", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("opencode CLI not found in PATH")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        prompt_file = temp_path / "prompt.txt"
        stdout_file = temp_path / "stdout.txt"
        stderr_file = temp_path / "stderr.txt"
        outputs_file = temp_path / "outputs.txt"
        
        # Create a simple prompt file
        prompt_content = "What is 2+2? Answer with just the number."
        prompt_file.write_text(prompt_content)
        
        # Set up environment
        env = os.environ.copy()
        env["MODEL"] = test_model
        env["OPENROUTER_API_KEY"] = api_key
        
        # Run the script
        script_path = Path(__file__).resolve().parents[3] / ".github/workflows/scripts/bots/opencode/run-opencode-cli.sh"
        try:
            result = _run_script(script_path, [str(prompt_file), str(stdout_file), str(stderr_file), str(outputs_file)], env)
        except FileNotFoundError as e:
            pytest.skip(str(e))
        
        # Check that the script exits with code 0 (as designed)
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        
        # Check that output files were created
        assert stdout_file.exists(), "stdout file was not created"
        assert stderr_file.exists(), "stderr file was not created"
        assert outputs_file.exists(), "outputs file was not created"
        
        # Read output files
        stdout_content = stdout_file.read_text()
        stderr_content = stderr_file.read_text()
        outputs_content = outputs_file.read_text()
        
        # Parse outputs
        outputs = {}
        for line in outputs_content.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                outputs[key] = value
        
        # Check exit code
        exit_code = int(outputs.get('exit_code', -1))
        assert exit_code == 0, f"opencode CLI exited with code {exit_code}. Stderr: {stderr_content}"
        
        # Check that we got some output
        assert len(stdout_content.strip()) > 0, "stdout is empty"
        assert "4" in stdout_content, f"Expected '4' in output: {stdout_content}"


def test_opencode_cli_error_handling() -> None:
    """Test opencode CLI error handling with invalid API key."""
    # Check if opencode CLI is available
    try:
        subprocess.run(["opencode", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("opencode CLI not found in PATH")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        prompt_file = temp_path / "prompt.txt"
        stdout_file = temp_path / "stdout.txt"
        stderr_file = temp_path / "stderr.txt"
        outputs_file = temp_path / "outputs.txt"
        
        # Create a simple prompt file
        prompt_content = "Say hello"
        prompt_file.write_text(prompt_content)
        
        # Set up environment with invalid API key
        env = os.environ.copy()
        env["MODEL"] = "openrouter/z-ai/glm-4.5-air:free"
        env["OPENROUTER_API_KEY"] = "invalid-api-key"
        
        # Run the script
        script_path = Path(__file__).resolve().parents[3] / ".github/workflows/scripts/bots/opencode/run-opencode-cli.sh"
        try:
            result = _run_script(script_path, [str(prompt_file), str(stdout_file), str(stderr_file), str(outputs_file)], env)
        except FileNotFoundError as e:
            pytest.skip(str(e))
        
        # Check that the script exits with code 0 (as designed)
        assert result.returncode == 0, f"Script failed with stderr: {result.stderr}"
        
        # Check that output files were created
        assert stdout_file.exists(), "stdout file was not created"
        assert stderr_file.exists(), "stderr file was not created"
        assert outputs_file.exists(), "outputs file was not created"
        
        # Read output files
        stdout_content = stdout_file.read_text()
        stderr_content = stderr_file.read_text()
        outputs_content = outputs_file.read_text()
        
        # Parse outputs
        outputs = {}
        for line in outputs_content.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                outputs[key] = value
        
        # Check exit code (should be non-zero for API errors)
        exit_code = int(outputs.get('exit_code', -1))
        assert exit_code != 0, f"Expected non-zero exit code for API error, got {exit_code}"