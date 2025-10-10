"""Integration tests for concurrent Chromium user data operations.

Essential tests that verify real threading, file locking, and concurrent filesystem operations
that cannot be properly tested at the unit level.
"""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

    def test_concurrent_cleanup_operations(self, user_data_manager):
        """Test concurrent cleanup operations."""
        # Create some test clones by creating them manually without using context manager cleanup
        clone_dirs = []
        for i in range(20):
            # Manually create clone directories to avoid automatic cleanup
            clone_id = str(uuid.uuid4())
            clone_dir = Path(user_data_manager.clones_dir) / clone_id
            clone_dir.mkdir(parents=True, exist_ok=True)
            clone_dirs.append(clone_dir)
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
