"""Unit tests for TikTok download utilities."""


from app.services.tiktok.download.utils.helpers import (
    extract_tiktok_video_id,
    is_valid_tiktok_url,
    sanitize_filename,
    extract_video_metadata_from_url,
    format_file_size,
)
import pytest

pytestmark = [pytest.mark.unit]


class TestTikTokDownloadHelpers:
    """Test cases for TikTok download helper functions."""

    def test_extract_tiktok_video_id_standard_format(self):
        """Test video ID extraction from standard TikTok URLs."""
        url = "https://www.tiktok.com/@username/video/1234567890"
        result = extract_tiktok_video_id(url)
        assert result == "1234567890"

    def test_extract_tiktok_video_id_no_www(self):
        """Test video ID extraction from URL without www."""
        url = "https://tiktok.com/@username/video/9876543210"
        result = extract_tiktok_video_id(url)
        assert result == "9876543210"

    def test_extract_tiktok_video_id_live_format(self):
        """Test video ID extraction from live video URL."""
        url = "https://www.tiktok.com/@username/live/5555555555"
        result = extract_tiktok_video_id(url)
        assert result == "5555555555"

    def test_extract_tiktok_video_id_short_format_vm(self):
        """Test video ID extraction from vm.tiktok.com short URL."""
        url = "https://vm.tiktok.com/ABC123XYZ/"
        result = extract_tiktok_video_id(url)
        assert result == "ABC123XYZ"

    def test_extract_tiktok_video_id_short_format_v(self):
        """Test video ID extraction from v.tiktok.com short URL."""
        url = "https://v.tiktok.com/DEF456UVW/"
        result = extract_tiktok_video_id(url)
        assert result == "DEF456UVW"

    def test_extract_tiktok_video_id_no_match(self):
        """Test video ID extraction when no match is found."""
        url = "https://example.com/not-tiktok/video/123"
        result = extract_tiktok_video_id(url)
        assert result is None

    def test_extract_tiktok_video_id_empty_string(self):
        """Test video ID extraction from empty string."""
        result = extract_tiktok_video_id("")
        assert result is None

    def test_is_valid_tiktok_url_standard(self):
        """Test URL validation for standard TikTok URLs."""
        url = "https://www.tiktok.com/@username/video/1234567890"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_no_www(self):
        """Test URL validation without www."""
        url = "https://tiktok.com/@username/video/1234567890"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_short_vm(self):
        """Test URL validation for vm.tiktok.com short URLs."""
        url = "https://vm.tiktok.com/ABC123XYZ/"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_short_v(self):
        """Test URL validation for v.tiktok.com short URLs."""
        url = "https://v.tiktok.com/DEF456UVW/"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_live(self):
        """Test URL validation for live URLs."""
        url = "https://www.tiktok.com/@username/live/5555555555"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_http(self):
        """Test URL validation for HTTP URLs."""
        url = "http://www.tiktok.com/@username/video/1234567890"
        assert is_valid_tiktok_url(url) is True

    def test_is_valid_tiktok_url_invalid_domain(self):
        """Test URL validation for invalid domains."""
        url = "https://example.com/@username/video/1234567890"
        assert is_valid_tiktok_url(url) is False

    def test_is_valid_tiktok_url_invalid_path(self):
        """Test URL validation for invalid paths."""
        url = "https://www.tiktok.com/@username/profile"
        assert is_valid_tiktok_url(url) is False

    def test_is_valid_tiktok_url_no_scheme(self):
        """Test URL validation for URLs without scheme."""
        url = "www.tiktok.com/@username/video/1234567890"
        assert is_valid_tiktok_url(url) is False

    def test_is_valid_tiktok_url_malformed(self):
        """Test URL validation for malformed URLs."""
        url = "not-a-url"
        assert is_valid_tiktok_url(url) is False

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        filename = "normal_video.mp4"
        result = sanitize_filename(filename)
        assert result == "normal_video.mp4"

    def test_sanitize_filename_invalid_chars(self):
        """Test sanitization of filenames with invalid characters."""
        filename = "video<>:\"/\\|?*.mp4"
        result = sanitize_filename(filename)
        assert result == "video_________.mp4"

    def test_sanitize_filename_control_chars(self):
        """Test sanitization of filenames with control characters."""
        filename = "video\x00\x1f\x7f.mp4"
        result = sanitize_filename(filename)
        assert result == "video.mp4"

    def test_sanitize_filename_leading_trailing_dots(self):
        """Test sanitization of filenames with leading/trailing dots and spaces."""
        filename = "  .video.mp4.  "
        result = sanitize_filename(filename)
        assert result == "video.mp4"

    def test_sanitize_filename_empty_result(self):
        """Test sanitization when result would be empty."""
        filename = "  .  "
        result = sanitize_filename(filename)
        assert result == "video"

    def test_sanitize_filename_long_name(self):
        """Test sanitization of very long filenames."""
        long_name = "a" * 300 + ".mp4"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".mp4")

    def test_sanitize_filename_long_name_with_extension(self):
        """Test sanitization of very long names with extensions."""
        long_name = "a" * 260 + "." + "b" * 50
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_extract_video_metadata_from_url_standard(self):
        """Test metadata extraction from standard URL."""
        url = "https://www.tiktok.com/@username/video/1234567890"
        result = extract_video_metadata_from_url(url)
        expected = {
            'id': '1234567890',
            'username': 'username',
            'url': url,
        }
        assert result == expected

    def test_extract_video_metadata_from_url_no_www(self):
        """Test metadata extraction from URL without www."""
        url = "https://tiktok.com/@testuser/video/9876543210"
        result = extract_video_metadata_from_url(url)
        expected = {
            'id': '9876543210',
            'username': 'testuser',
            'url': url,
        }
        assert result == expected

    def test_extract_video_metadata_from_url_no_username(self):
        """Test metadata extraction from URL without username."""
        url = "https://vm.tiktok.com/ABC123XYZ/"
        result = extract_video_metadata_from_url(url)
        expected = {
            'id': 'ABC123XYZ',
            'username': None,
            'url': url,
        }
        assert result == expected

    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        result = format_file_size(500)
        assert result == "500.0 B"

    def test_format_file_size_kilobytes(self):
        """Test file size formatting for kilobytes."""
        result = format_file_size(1500)
        assert result == "1.5 KB"

    def test_format_file_size_megabytes(self):
        """Test file size formatting for megabytes."""
        result = format_file_size(2_500_000)
        assert result == "2.4 MB"

    def test_format_file_size_gigabytes(self):
        """Test file size formatting for gigabytes."""
        result = format_file_size(3_000_000_000)
        assert result == "2.8 GB"

    def test_format_file_size_none(self):
        """Test file size formatting for None."""
        result = format_file_size(None)
        assert result == "Unknown"

    def test_format_file_size_zero(self):
        """Test file size formatting for zero bytes."""
        result = format_file_size(0)
        assert result == "0.0 B"
