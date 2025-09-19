"""Gemini API key rotation implementation."""

from __future__ import annotations

import argparse
import pathlib
import sys
from typing import List

if __package__ in {None, ''}:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from base_rotator import BaseKeyRotator  # type: ignore
else:
    from .base_rotator import BaseKeyRotator


class GeminiKeyRotator(BaseKeyRotator):
    """Gemini API key rotator implementation."""

    @property
    def default_prefix(self) -> str:
        """Return the default environment variable prefix for Gemini API keys."""
        return "GEMINI_API_KEY"

    @property
    def error_message(self) -> str:
        """Return the error message when no Gemini keys are found."""
        return "No Gemini API keys were provided via the environment."

    @property
    def success_message(self) -> str:
        """Return the success message format for Gemini key selection."""
        return "Selected Gemini key from {} -> {}"

    def _get_additional_arguments(self) -> List[tuple]:
        """Return additional command line arguments for Gemini implementation."""
        return []

    def _process_additional_outputs(self, args: argparse.Namespace, selected) -> None:
        """Process additional outputs specific to Gemini implementation."""
        # The presence output is handled in the base class
        pass


if __name__ == "__main__":
    rotator = GeminiKeyRotator()
    rotator.run()
