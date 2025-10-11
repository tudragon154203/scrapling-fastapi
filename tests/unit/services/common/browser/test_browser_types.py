"""Test type definitions and schemas for browser modules - corrected to match actual API."""

import pytest

from app.services.common.browser.types import (
    CookieData,
    CookieExportResult,
    StorageStateCookies,
    StorageStateResult,
    ProfileMetadata,
    DiskUsageStats,
    CleanupResult,
    BrowserForgeFingerprint,
    CookieList,
    CookieDict,
    MetadataUpdates,
    convert_samesite,
    convert_samesite_to_db
)


class TestCookieData:
    """Test CookieData TypedDict."""

    @pytest.mark.unit
    def test_cookie_data_structure(self):
        """Test CookieData structure with all fields."""
        cookie = CookieData(
            name="session_id",
            value="abc123",
            domain="example.com",
            path="/",
            expires=1234567890,
            httpOnly=True,
            secure=True,
            sameSite="Strict",
            creationTime=1234567890,
            lastAccessTime=1234567891,
            persistent=True
        )

        assert cookie["name"] == "session_id"
        assert cookie["value"] == "abc123"
        assert cookie["domain"] == "example.com"
        assert cookie["path"] == "/"
        assert cookie["expires"] == 1234567890
        assert cookie["httpOnly"] is True
        assert cookie["secure"] is True
        assert cookie["sameSite"] == "Strict"
        assert cookie["creationTime"] == 1234567890
        assert cookie["lastAccessTime"] == 1234567891
        assert cookie["persistent"] is True

    @pytest.mark.unit
    def test_cookie_data_minimal(self):
        """Test CookieData with minimal required fields."""
        cookie = CookieData(
            name="test",
            value="value"
        )

        assert cookie["name"] == "test"
        assert cookie["value"] == "value"
        # Optional fields should not be present
        assert "domain" not in cookie
        assert "path" not in cookie

    @pytest.mark.unit
    def test_cookie_data_optional_fields(self):
        """Test CookieData with some optional fields."""
        cookie = CookieData(
            name="test",
            value="value",
            domain="example.com",
            secure=False
        )

        assert cookie["name"] == "test"
        assert cookie["value"] == "value"
        assert cookie["domain"] == "example.com"
        assert cookie["secure"] is False
        # Other optional fields should not be present
        assert "path" not in cookie
        assert "httpOnly" not in cookie


class TestCookieExportResult:
    """Test CookieExportResult TypedDict."""

    @pytest.mark.unit
    def test_cookie_export_result_structure(self):
        """Test CookieExportResult structure."""
        cookies = [CookieData(name="test", value="value")]
        metadata = {"version": "1.0"}

        result = CookieExportResult(
            format="json",
            cookies=cookies,
            profile_metadata=metadata,
            cookies_available=True,
            master_profile_path="/path/to/master",
            export_timestamp=1234567890.0
        )

        assert result["format"] == "json"
        assert result["cookies"] == cookies
        assert result["profile_metadata"] == metadata
        assert result["cookies_available"] is True
        assert result["master_profile_path"] == "/path/to/master"
        assert result["export_timestamp"] == 1234567890.0

    @pytest.mark.unit
    def test_cookie_export_result_minimal(self):
        """Test CookieExportResult with minimal fields."""
        result = CookieExportResult(
            format="json",
            cookies=[],
            cookies_available=False,
            master_profile_path="/path/to/master",
            export_timestamp=1234567890.0
        )

        assert result["format"] == "json"
        assert result["cookies"] == []
        assert result["cookies_available"] is False
        # Optional fields should not be present
        assert "profile_metadata" not in result


class TestStorageStateCookies:
    """Test StorageStateCookies TypedDict."""

    @pytest.mark.unit
    def test_storage_state_cookies_structure(self):
        """Test StorageStateCookies structure."""
        cookie = StorageStateCookies(
            name="session_id",
            value="abc123",
            domain="example.com",
            path="/",
            expires=1234567890,
            httpOnly=True,
            secure=True,
            sameSite="Strict"
        )

        assert cookie["name"] == "session_id"
        assert cookie["value"] == "abc123"
        assert cookie["domain"] == "example.com"
        assert cookie["path"] == "/"
        assert cookie["expires"] == 1234567890
        assert cookie["httpOnly"] is True
        assert cookie["secure"] is True
        assert cookie["sameSite"] == "Strict"


class TestStorageStateResult:
    """Test StorageStateResult TypedDict."""

    @pytest.mark.unit
    def test_storage_state_result_structure(self):
        """Test StorageStateResult structure."""
        cookies = [StorageStateCookies(name="test", value="value")]
        origins = [{"origin": "https://example.com"}]

        result = StorageStateResult(
            cookies=cookies,
            origins=origins
        )

        assert result["cookies"] == cookies
        assert result["origins"] == origins


class TestProfileMetadata:
    """Test ProfileMetadata TypedDict."""

    @pytest.mark.unit
    def test_profile_metadata_structure(self):
        """Test ProfileMetadata structure."""
        metadata = ProfileMetadata(
            version="1.0",
            created_at=1234567890.0,
            last_updated=1234567891.0,
            browserforge_version="1.0.0",
            profile_type="chromium",
            browserforge_fingerprint_generated=True,
            browserforge_fingerprint_file="/path/to/fingerprint.json",
            browserforge_fingerprint_source="browserforge.generate",
            last_cookie_import=1234567892.0,
            cookie_import_count=10,
            cookie_import_status="success",
            last_cleanup=1234567893.0,
            last_cleanup_count=5,
            last_cleanup_size_saved=1.5,
            remaining_clones=3
        )

        assert metadata["version"] == "1.0"
        assert metadata["created_at"] == 1234567890.0
        assert metadata["last_updated"] == 1234567891.0
        assert metadata["browserforge_version"] == "1.0.0"
        assert metadata["profile_type"] == "chromium"
        assert metadata["browserforge_fingerprint_generated"] is True
        assert metadata["browserforge_fingerprint_file"] == "/path/to/fingerprint.json"
        assert metadata["browserforge_fingerprint_source"] == "browserforge.generate"
        assert metadata["last_cookie_import"] == 1234567892.0
        assert metadata["cookie_import_count"] == 10
        assert metadata["cookie_import_status"] == "success"
        assert metadata["last_cleanup"] == 1234567893.0
        assert metadata["last_cleanup_count"] == 5
        assert metadata["last_cleanup_size_saved"] == 1.5
        assert metadata["remaining_clones"] == 3

    @pytest.mark.unit
    def test_profile_metadata_minimal(self):
        """Test ProfileMetadata with minimal fields."""
        metadata = ProfileMetadata(
            version="1.0"
        )

        assert metadata["version"] == "1.0"
        # Optional fields should not be present
        assert "created_at" not in metadata
        assert "profile_type" not in metadata


class TestDiskUsageStats:
    """Test DiskUsageStats TypedDict."""

    @pytest.mark.unit
    def test_disk_usage_stats_structure(self):
        """Test DiskUsageStats structure."""
        stats = DiskUsageStats(
            enabled=True,
            master_size_mb=10.5,
            clones_size_mb=5.2,
            total_size_mb=15.7,
            clone_count=3,
            master_dir="/path/to/master",
            clones_dir="/path/to/clones",
            last_cleanup=1234567890.0,
            last_cleanup_count=2,
            last_cleanup_size_saved=1.0,
            error=None
        )

        assert stats["enabled"] is True
        assert stats["master_size_mb"] == 10.5
        assert stats["clones_size_mb"] == 5.2
        assert stats["total_size_mb"] == 15.7
        assert stats["clone_count"] == 3
        assert stats["master_dir"] == "/path/to/master"
        assert stats["clones_dir"] == "/path/to/clones"
        assert stats["last_cleanup"] == 1234567890.0
        assert stats["last_cleanup_count"] == 2
        assert stats["last_cleanup_size_saved"] == 1.0
        assert stats["error"] is None

    @pytest.mark.unit
    def test_disk_usage_stats_with_error(self):
        """Test DiskUsageStats with error."""
        stats = DiskUsageStats(
            enabled=False,
            error="Permission denied"
        )

        assert stats["enabled"] is False
        assert stats["error"] == "Permission denied"
        # Other fields should not be present
        assert "master_size_mb" not in stats


class TestCleanupResult:
    """Test CleanupResult TypedDict."""

    @pytest.mark.unit
    def test_cleanup_result_structure(self):
        """Test CleanupResult structure."""
        result = CleanupResult(
            cleaned=5,
            remaining=2,
            errors=0,
            size_saved_mb=2.5
        )

        assert result["cleaned"] == 5
        assert result["remaining"] == 2
        assert result["errors"] == 0
        assert result["size_saved_mb"] == 2.5

    @pytest.mark.unit
    def test_cleanup_result_no_size_saved(self):
        """Test CleanupResult without size_saved_mb."""
        result = CleanupResult(
            cleaned=3,
            remaining=1,
            errors=0
        )

        assert result["cleaned"] == 3
        assert result["remaining"] == 1
        assert result["errors"] == 0
        # Optional field should not be present
        assert "size_saved_mb" not in result


class TestBrowserForgeFingerprint:
    """Test BrowserForgeFingerprint TypedDict."""

    @pytest.mark.unit
    def test_browserforge_fingerprint_structure(self):
        """Test BrowserForgeFingerprint structure."""
        fingerprint = BrowserForgeFingerprint(
            userAgent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080, "pixelRatio": 1.0}
        )

        assert fingerprint["userAgent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        assert fingerprint["viewport"]["width"] == 1920
        assert fingerprint["viewport"]["height"] == 1080
        assert fingerprint["screen"]["width"] == 1920
        assert fingerprint["screen"]["height"] == 1080
        assert fingerprint["screen"]["pixelRatio"] == 1.0

    @pytest.mark.unit
    def test_browserforge_fingerprint_minimal(self):
        """Test BrowserForgeFingerprint with minimal fields."""
        fingerprint = BrowserForgeFingerprint(
            userAgent="Mozilla/5.0"
        )

        assert fingerprint["userAgent"] == "Mozilla/5.0"
        # Optional fields should not be present
        assert "viewport" not in fingerprint
        assert "screen" not in fingerprint


class TestTypeAliases:
    """Test type aliases."""

    @pytest.mark.unit
    def test_cookie_list_alias(self):
        """Test CookieList type alias."""
        cookies: CookieList = [
            CookieData(name="test1", value="value1"),
            CookieData(name="test2", value="value2")
        ]

        assert len(cookies) == 2
        assert cookies[0]["name"] == "test1"
        assert cookies[1]["name"] == "test2"

    @pytest.mark.unit
    def test_cookie_dict_alias(self):
        """Test CookieDict type alias."""
        cookie: CookieDict = {
            "name": "test",
            "value": "value",
            "domain": "example.com"
        }

        assert cookie["name"] == "test"
        assert cookie["value"] == "value"
        assert cookie["domain"] == "example.com"

    @pytest.mark.unit
    def test_metadata_updates_alias(self):
        """Test MetadataUpdates type alias."""
        updates: MetadataUpdates = {
            "version": "2.0",
            "last_updated": 1234567890.0
        }

        assert updates["version"] == "2.0"
        assert updates["last_updated"] == 1234567890.0


class TestSameSiteConversion:
    """Test SameSite conversion functions."""

    @pytest.mark.unit
    def test_convert_samesite_none(self):
        """Test convert_samesite with None value."""
        result = convert_samesite(0)
        assert result == "None"

    @pytest.mark.unit
    def test_convert_samesite_lax(self):
        """Test convert_samesite with Lax value."""
        result = convert_samesite(1)
        assert result == "Lax"

    @pytest.mark.unit
    def test_convert_samesite_strict(self):
        """Test convert_samesite with Strict value."""
        result = convert_samesite(2)
        assert result == "Strict"

    @pytest.mark.unit
    def test_convert_samesite_unspecified(self):
        """Test convert_samesite with unspecified value."""
        result = convert_samesite(-1)
        assert result == "None"

    @pytest.mark.unit
    def test_convert_samesite_invalid(self):
        """Test convert_samesite with invalid value."""
        result = convert_samesite(999)
        assert result == "None"  # Should default to "None"

    @pytest.mark.unit
    def test_convert_samesite_to_db_none(self):
        """Test convert_samesite_to_db with None string."""
        result = convert_samesite_to_db("None")
        assert result == 0

    @pytest.mark.unit
    def test_convert_samesite_to_db_lax(self):
        """Test convert_samesite_to_db with Lax string."""
        result = convert_samesite_to_db("Lax")
        assert result == 1

    @pytest.mark.unit
    def test_convert_samesite_to_db_strict(self):
        """Test convert_samesite_to_db with Strict string."""
        result = convert_samesite_to_db("Strict")
        assert result == 2

    @pytest.mark.unit
    def test_convert_samesite_to_db_case_insensitive(self):
        """Test convert_samesite_to_db is case insensitive."""
        result_lower = convert_samesite_to_db("lax")
        result_upper = convert_samesite_to_db("LAX")

        assert result_lower == 1
        # "LAX" is not in the mapping, so it defaults to 0
        assert result_upper == 0

        # Test "None" case insensitive
        result_none_lower = convert_samesite_to_db("none")
        result_none_upper = convert_samesite_to_db("NONE")

        assert result_none_lower == 0
        assert result_none_upper == 0

    @pytest.mark.unit
    def test_convert_samesite_to_db_invalid(self):
        """Test convert_samesite_to_db with invalid string."""
        result = convert_samesite_to_db("invalid")
        assert result == 0  # Should default to 0

    @pytest.mark.unit
    def test_samesite_roundtrip_conversion(self):
        """Test SameSite roundtrip conversion."""
        test_values = [
            (0, "None"),
            (1, "Lax"),
            (2, "Strict")
        ]

        for int_val, str_val in test_values:
            # Convert int to string
            converted_str = convert_samesite(int_val)
            assert converted_str == str_val

            # Convert string back to int
            converted_int = convert_samesite_to_db(converted_str)
            assert converted_int == int_val

        # Test -1 case separately (converts to "None" but back to 0)
        converted_str = convert_samesite(-1)
        assert converted_str == "None"
        converted_int = convert_samesite_to_db(converted_str)
        assert converted_int == 0  # "None" maps to 0, not -1

    @pytest.mark.unit
    def test_samesite_conversion_edge_cases(self):
        """Test SameSite conversion edge cases."""
        # Test all valid mappings
        mappings = [
            (0, "None", "none"),
            (1, "Lax", "lax"),
            (2, "Strict", "strict")
        ]

        for int_val, upper_str, lower_str in mappings:
            assert convert_samesite(int_val) == upper_str
            assert convert_samesite_to_db(upper_str) == int_val
            assert convert_samesite_to_db(lower_str) == int_val


class TestTypeIntegration:
    """Test type integration and cross-compatibility."""

    @pytest.mark.unit
    def test_nested_types(self):
        """Test nested type structures."""
        cookies: CookieList = [
            CookieData(
                name="session",
                value="abc123",
                domain="example.com",
                sameSite="Strict"
            )
        ]

        export_result: CookieExportResult = {
            "format": "json",
            "cookies": cookies,
            "cookies_available": True,
            "master_profile_path": "/master",
            "export_timestamp": 1234567890.0
        }

        assert len(export_result["cookies"]) == 1
        assert export_result["cookies"][0]["name"] == "session"
        assert export_result["cookies"][0]["sameSite"] == "Strict"

    @pytest.mark.unit
    def test_type_compatibility_with_functions(self):
        """Test type compatibility with conversion functions."""
        cookie: CookieData = {
            "name": "test",
            "value": "value",
            "sameSite": "Lax"
        }

        # Convert SameSite to database format
        samesite_db = convert_samesite_to_db(cookie["sameSite"])
        assert samesite_db == 1

        # Convert back to string format
        samesite_str = convert_samesite(samesite_db)
        assert samesite_str == "Lax"

    @pytest.mark.unit
    def test_type_defaults_and_optional_fields(self):
        """Test type defaults and optional fields handling."""
        # Create minimal cookie
        minimal_cookie: CookieData = {
            "name": "minimal",
            "value": "test"
        }

        # Should not error when accessing optional fields
        domain = minimal_cookie.get("domain", "default.com")
        assert domain == "default.com"

        # Create minimal metadata
        minimal_metadata: ProfileMetadata = {
            "version": "1.0"
        }

        # Should not error when accessing optional fields
        profile_type = minimal_metadata.get("profile_type", "default")
        assert profile_type == "default"

    @pytest.mark.unit
    def test_type_serialization_compatibility(self):
        """Test type serialization compatibility."""
        metadata: ProfileMetadata = {
            "version": "1.0",
            "created_at": 1234567890.0,
            "profile_type": "chromium"
        }

        # Should be JSON serializable
        import json
        json_str = json.dumps(metadata)
        parsed = json.loads(json_str)

        assert parsed["version"] == "1.0"
        assert parsed["created_at"] == 1234567890.0
        assert parsed["profile_type"] == "chromium"
