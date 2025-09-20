"""Integration tests for the opencode CLI."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from pathlib import Path

import pytest
import sys
from pathlib import Path

# Add parent directory to sys.path for import
sys.path.insert(0, str(Path(__file__).parent))

# Try to import the centralized config
try:
    from core.config import config
    HAS_CONFIG = True
    print(f"DEBUG: Import succeeded. HAS_CONFIG={HAS_CONFIG}, config.openrouter_api_key={getattr(config, 'openrouter_api_key', 'N/A')}")
except ImportError as e:
    HAS_CONFIG = False
    config = None
    print(f"DEBUG: Import failed: {e}. HAS_CONFIG={HAS_CONFIG}")
print("Has config:", HAS_CONFIG)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

IS_WINDOWS = platform.system() == "Windows"


def _get_script_path() -> Path:
    """Return the platform-specific path to the runner script."""
    script_dir = Path(__file__).resolve().parents[2] / "scripts/bots/opencode"
    script_name = "run-opencode-cli.ps1" if IS_WINDOWS else "run-opencode-cli.sh"
    script_path = script_dir / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    return script_path



def _run_script(script_path: Path, args: list[str], env: dict) -> subprocess.CompletedProcess:
    """Run a script with appropriate shell settings for the platform."""
    if IS_WINDOWS:
        if script_path.suffix.lower() == ".ps1":
            command = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script_path)] + args
            return subprocess.run(command, env=env, capture_output=True, text=True)
        # Fallback for environments where only bash scripts are available
        try:
            subprocess.run(["bash", "--version"], check=True, capture_output=True)
            cmd = ["bash", str(script_path)] + args
            return subprocess.run(cmd, env=env, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                return subprocess.run([str(script_path)] + args, env=env, capture_output=True, text=True, shell=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                raise FileNotFoundError("Cannot execute shell script on Windows. Please install bash (Git Bash, WSL, or Cygwin).") from exc
    else:
        if script_path.suffix.lower() == ".sh":
            cmd = ["bash", str(script_path)] + args
            return subprocess.run(cmd, env=env, capture_output=True, text=True)
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
        print(f"DEBUG: Using config. api_key={'*' * (len(api_key)-4) + api_key[-4:] if api_key else None}, test_model={test_model}")
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        test_model = os.environ.get("OPENCODE_TEST_MODEL", "openrouter/z-ai/glm-4.5-air:free")
        print(f"DEBUG: Using os.environ. api_key={'*' * (len(api_key)-4) + api_key[-4:] if api_key else None}, test_model={test_model}")
    
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
        try:
            script_path = _get_script_path()
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
        print(f"DEBUG: outputs_content: '{outputs_content}'")
        print(f"DEBUG: runner result: returncode={result.returncode}, stdout='{result.stdout}', stderr='{result.stderr}'")
        print(f"DEBUG: stdout_content: '{stdout_content}'")
        print(f"DEBUG: stderr_content: '{stderr_content}'")
        
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
        print(f"DEBUG: Using config (custom model test). api_key={'*' * (len(api_key)-4) + api_key[-4:] if api_key else None}, test_model={test_model}")
    else:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        test_model = os.environ.get("OPENCODE_TEST_MODEL", "openrouter/z-ai/glm-4.5-air:free")
        print(f"DEBUG: Using os.environ (custom model test). api_key={'*' * (len(api_key)-4) + api_key[-4:] if api_key else None}, test_model={test_model}")
    
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
        try:
            script_path = _get_script_path()
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
        print(f"DEBUG: outputs_content (custom): '{outputs_content}'")
        print(f"DEBUG: runner result (custom): returncode={result.returncode}, stdout='{result.stdout}', stderr='{result.stderr}'")
        print(f"DEBUG: stdout_content (custom): '{stdout_content}'")
        print(f"DEBUG: stderr_content (custom): '{stderr_content}'")
        
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
        try:
            script_path = _get_script_path()
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