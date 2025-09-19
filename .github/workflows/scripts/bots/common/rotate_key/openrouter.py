"""OpenRouter API key rotation implementation."""

from __future__ import annotations

import pathlib
import sys

if __package__ in {None, ''}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from base_rotator import BaseKeyRotator  # type: ignore
else:
    from .base_rotator import BaseKeyRotator


class OpenRouterKeyRotator(BaseKeyRotator):
    """OpenRouter API key rotator implementation."""

    @property
    def default_prefix(self) -> str:
        """Return the default environment variable prefix for OpenRouter API keys."""
        return "OPENROUTER_API_KEY"

    @property
    def error_message(self) -> str:
        """Return the error message when no OpenRouter keys are found."""
        return "No OpenRouter API keys were provided via the environment."

    @property
    def success_message(self) -> str:
        """Return the success message format for OpenRouter key selection."""
        return "Selected OpenRouter key from {} -> {}"


if __name__ == "__main__":
    rotator = OpenRouterKeyRotator()
    rotator.run()
