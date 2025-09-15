import pytest

from app.services.common.browser.camoufox import CamoufoxArgsBuilder


@pytest.mark.parametrize(
    "value, expected",
    [
        ("1280x720", (1280, 720)),
        ("800,600", (800, 600)),
        ("1920x1080", (1920, 1080)),
        ("2560x1440", (2560, 1440)),
        ("3840x2160", (3840, 2160)),
    ],
)
def test_parse_window_size_valid(value, expected):
    """Valid window size strings should parse to integer tuples."""
    assert CamoufoxArgsBuilder._parse_window_size(value) == expected


@pytest.mark.parametrize("value", ["abc", "100", ""])
def test_parse_window_size_invalid(value):
    """Invalid window size strings should return None."""
    assert CamoufoxArgsBuilder._parse_window_size(value) is None
