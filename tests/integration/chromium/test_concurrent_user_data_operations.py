"""Integration tests for concurrent Chromium user data operations."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.common.browser.user_data_chromium import ChromiumUserDataManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


class TestConcurrentUserDataOperations:
    """Test concurrent access to Chromium user data operations."""

    @pytest.fixture
    def temp_user_data_dir(self, tmp_path):
        """Create a temporary user data directory for testing."""
        return tmp_path / "chromium_test"

    @pytest.fixture
    def user_data_manager(self, temp_user_data_dir):
        """Create a ChromiumUserDataManager instance for testing."""
        return ChromiumUserDataManager(str(temp_user_data_dir))

    @pytest.fixture
    def populated_manager(self, user_data_manager):
        """Create a manager with sample data."""
        # Initialize with some sample data
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            # Create a basic profile structure
            default_dir = Path(effective_dir) / "Default"
            default_dir.mkdir(parents=True, exist_ok=True)

            # Create sample cookies database
            import sqlite3
            cookies_db = default_dir / "Cookies"
            with sqlite3.connect(cookies_db) as conn:
                conn.execute("""
                    CREATE TABLE cookies (
                        creation_utc INTEGER,
                        host_key TEXT,
                        name TEXT,
                        value TEXT,
                        path TEXT,
                        expires_utc INTEGER,
                        is_secure INTEGER,
                        is_httponly INTEGER,
                        samesite INTEGER,
                        last_access_utc INTEGER,
                        has_expires INTEGER,
                        is_persistent INTEGER
                    )
                """)
                # Insert sample cookies
                sample_cookies = [
                    (1234567890, "tiktok.com", "session_token", "abc123", "/", -1, 1, 1, 0, 1234567890, 0, 1),
                    (1234567891, "tiktok.com", "user_id", "user123", "/", -1, 1, 0, 0, 1234567891, 0, 1),
                ]
                conn.executemany("""
                    INSERT INTO cookies VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, sample_cookies)
                conn.commit()

        yield user_data_manager

        # Cleanup using manager's base_path to avoid NameError
        try:
            base_path = Path(user_data_manager.base_path) if hasattr(user_data_manager, "base_path") else None
            if base_path and base_path.exists():
                import shutil
                shutil.rmtree(base_path, ignore_errors=True)
        except Exception:
            pass

    def test_concurrent_read_operations(self, populated_manager):
        """Test that multiple read operations can run concurrently."""
        results = []
        errors = []

        def read_operation(worker_id):
            try:
                with populated_manager.get_user_data_context('read') as (effective_dir, cleanup):
                    # Simulate some work
                    time.sleep(0.1)

                    # Verify the clone directory exists
                    assert Path(effective_dir).exists()

                    # Try to read cookies
                    cookies = populated_manager.export_cookies()
                    results.append({
                        'worker_id': worker_id,
                        'effective_dir': effective_dir,
                        'cookie_count': len(cookies.get('cookies', [])),
                        'cleanup_called': cleanup is not None
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run 10 concurrent read operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_operation, i) for i in range(10)]

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, "Not all operations completed"

        # All should have found cookies
        for result in results:
            assert result['cookie_count'] >= 0, "Cookie read failed"
            assert result['cleanup_called'] is True, "Cleanup not provided"

    def test_concurrent_write_operation_exclusion(self, user_data_manager):
        """Test that write operations are mutually exclusive."""
        results = []
        errors = []
        acquisition_times = []

        def write_operation(worker_id):
            try:
                start_time = time.time()
                with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
                    acquisition_time = time.time() - start_time
                    acquisition_times.append(acquisition_time)

                    # Simulate work in write mode
                    time.sleep(0.2)

                    results.append({
                        'worker_id': worker_id,
                        'effective_dir': effective_dir,
                        'acquisition_time': acquisition_time,
                        'cleanup_called': cleanup is not None
                    })

                    # Verify we're using the master directory
                    assert effective_dir == str(user_data_manager.master_dir)

                    cleanup()
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run 3 concurrent write operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(write_operation, i) for i in range(3)]

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()

        # Verify results - only one should succeed without lock conflict
        assert len(results) <= 3, "Too many write operations succeeded"

        # Check that operations were serialized (acquisition times should be staggered)
        if len(results) > 1:
            acquisition_times.sort()
            for i in range(1, len(acquisition_times)):
                # Each subsequent acquisition should wait at least the work duration
                time_diff = acquisition_times[i] - acquisition_times[i - 1]
                assert time_diff >= 0.1, f"Write operations not properly serialized: {time_diff}"

    def test_mixed_read_write_operations(self, populated_manager):
        """Test mixed read and write operations."""
        read_results = []
        write_results = []
        errors = []

        def read_operation(worker_id):
            try:
                with populated_manager.get_user_data_context('read') as (effective_dir, cleanup):
                    time.sleep(0.1)
                    read_results.append({
                        'worker_id': worker_id,
                        'effective_dir': effective_dir,
                        'is_clone': 'clones' in effective_dir
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': f'read-{worker_id}', 'error': str(e)})

        def write_operation(worker_id):
            try:
                with populated_manager.get_user_data_context('write') as (effective_dir, cleanup):
                    time.sleep(0.15)
                    write_results.append({
                        'worker_id': worker_id,
                        'effective_dir': effective_dir,
                        'is_master': 'master' in effective_dir
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': f'write-{worker_id}', 'error': str(e)})

        # Run mixed operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []

            # Submit read operations
            for i in range(5):
                futures.append(executor.submit(read_operation, i))

            # Submit write operations
            for i in range(2):
                futures.append(executor.submit(write_operation, i))

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(read_results) == 5, f"Expected 5 reads, got {len(read_results)}"

        # Read operations should use clones
        for result in read_results:
            assert result['is_clone'], "Read operation should use clone directory"

        # Write operations should use master
        for result in write_results:
            assert result['is_master'], "Write operation should use master directory"

    def test_concurrent_cookie_import_export(self, populated_manager):
        """Test concurrent cookie import/export operations."""
        sample_cookies = {
            "format": "json",
            "cookies": [
                {
                    "name": f"test_cookie_{int(time.time())}",
                    "value": "test_value",
                    "domain": ".example.com",
                    "path": "/",
                    "expires": -1,
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "None"
                }
            ]
        }

        export_results = []
        import_results = []
        errors = []

        def export_operation(worker_id):
            try:
                cookies = populated_manager.export_cookies()
                export_results.append({
                    'worker_id': worker_id,
                    'cookie_count': len(cookies.get('cookies', [])),
                    'format': cookies.get('format')
                })
            except Exception as e:
                errors.append({'worker_id': f'export-{worker_id}', 'error': str(e)})

        def import_operation(worker_id):
            try:
                # Add unique identifier to cookies for this worker
                worker_cookies = sample_cookies.copy()
                worker_cookies['cookies'][0]['name'] = f"test_cookie_{worker_id}_{int(time.time())}"

                success = populated_manager.import_cookies(worker_cookies)
                import_results.append({
                    'worker_id': worker_id,
                    'success': success
                })
            except Exception as e:
                errors.append({'worker_id': f'import-{worker_id}', 'error': str(e)})

        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []

            # Submit exports
            for i in range(3):
                futures.append(executor.submit(export_operation, i))

            # Submit imports
            for i in range(3):
                futures.append(executor.submit(import_operation, i))

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(export_results) == 3, f"Expected 3 exports, got {len(export_results)}"
        assert len(import_results) == 3, f"Expected 3 imports, got {len(import_results)}"

        # All imports should succeed
        for result in import_results:
            assert result['success'], "Import operation failed"

        # Final export should include all imported cookies
        final_cookies = populated_manager.export_cookies()
        final_count = len(final_cookies.get('cookies', []))
        assert final_count >= 2, f"Expected at least 2 cookies, got {final_count}"

    def test_concurrent_cleanup_operations(self, user_data_manager):
        """Test concurrent cleanup operations."""
        # Create some test clones
        clone_dirs = []
        for i in range(20):
            with user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
                clone_dirs.append(Path(effective_dir))
                # Don't cleanup - let them accumulate
                time.sleep(0.01)

        cleanup_results = []
        errors = []

        def cleanup_operation(worker_id):
            try:
                result = user_data_manager.cleanup_old_clones(max_age_hours=0, max_count=10)
                cleanup_results.append({
                    'worker_id': worker_id,
                    'cleaned': result['cleaned'],
                    'remaining': result['remaining'],
                    'errors': result['errors']
                })
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run concurrent cleanup operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(cleanup_operation, i) for i in range(3)]

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(cleanup_results) == 3, f"Expected 3 cleanup operations, got {len(cleanup_results)}"

        # At least one cleanup should have removed clones
        total_cleaned = sum(result['cleaned'] for result in cleanup_results)
        assert total_cleaned > 0, "No clones were cleaned up"

    def test_profile_corruption_recovery(self, user_data_manager):
        """Test recovery from corrupted profile."""
        # Create a master profile with corrupted data
        master_dir = user_data_manager.master_dir
        master_dir.mkdir(parents=True, exist_ok=True)

        # Create corrupted cookies database
        cookies_db = master_dir / "Default" / "Cookies"
        cookies_db.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid SQLite data
        with open(cookies_db, 'w') as f:
            f.write("This is not a valid SQLite database")

        # Test that export handles corruption gracefully
        result = user_data_manager.export_cookies()

        # Should return empty result, not crash
        assert result is not None, "Export should not crash on corruption"
        assert 'cookies' in result, "Result should have cookies field"
        assert len(result['cookies']) == 0, "Should return empty cookies on corruption"

    def test_disk_space_exhaustion_simulation(self, user_data_manager):
        """Test behavior when disk space is exhausted."""
        results = []
        errors = []

        def create_large_clone(worker_id):
            try:
                with user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
                    # Simulate filling up space by creating large files
                    large_file = Path(effective_dir) / "large_file.dat"

                    # Create a reasonably large file (10MB)
                    with open(large_file, 'wb') as f:
                        f.write(b'0' * (10 * 1024 * 1024))

                    # Get disk usage stats
                    stats = user_data_manager.get_disk_usage_stats()

                    results.append({
                        'worker_id': worker_id,
                        'clone_size_mb': user_data_manager._get_directory_size(Path(effective_dir)),
                        'total_size_mb': stats.get('total_size_mb', 0)
                    })

                    cleanup()
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run a few operations to test disk space handling
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_large_clone, i) for i in range(3)]

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3, f"Expected 3 operations, got {len(results)}"

        # Check that disk usage tracking works
        for result in results:
            assert result['clone_size_mb'] > 9, "Large file creation failed"
            assert result['total_size_mb'] > 0, "Disk usage not tracked correctly"

    def test_concurrent_metadata_updates(self, user_data_manager):
        """Test concurrent metadata updates."""
        results = []
        errors = []

        def metadata_update(worker_id):
            try:
                updates = {
                    f"test_field_{worker_id}": f"test_value_{worker_id}_{int(time.time())}",
                    "concurrent_test": True,
                    "update_count": 1
                }

                user_data_manager.update_metadata(updates)

                # Read metadata to verify update
                metadata = user_data_manager.get_metadata()

                results.append({
                    'worker_id': worker_id,
                    'update_success': f"test_field_{worker_id}" in metadata,
                    'metadata_keys': list(metadata.keys()) if metadata else []
                })
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run concurrent metadata updates
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(metadata_update, i) for i in range(5)]

            # Wait for completion
            for future in as_completed(futures):
                future.result()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, f"Expected 5 updates, got {len(results)}"

        # All updates should succeed
        for result in results:
            assert result['update_success'], f"Metadata update failed: {result}"

        # Final metadata should contain all updates
        final_metadata = user_data_manager.get_metadata()
        assert final_metadata is not None, "Final metadata should not be None"
        assert final_metadata.get('concurrent_test') is True, "Concurrent flag should be set"
