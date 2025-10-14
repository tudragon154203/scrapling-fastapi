"""Shared fixtures for Chromium browser unit tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest


@pytest.fixture
def temp_data_dir() -> Iterator[Path]:
    """Provide a temporary directory for filesystem-heavy tests."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
