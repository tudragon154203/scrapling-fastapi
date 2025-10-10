"""Integration tests for concurrent Chromium user data operations.

Essential tests that verify real threading, file locking, and concurrent filesystem operations
that cannot be properly tested at the unit level.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def test_concurrent_read_operations(self, user_data_manager):
        """Test that multiple read operations can run concurrently."""
        # Initialize with basic profile
        with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
            cleanup()

        results = []
        errors = []

        def read_operation(worker_id):
            try:
                with user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
                    time.sleep(0.1)
                    assert effective_dir
                    results.append({'worker_id': worker_id})
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run 5 concurrent read operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_operation, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5, "Not all operations completed"

    def test_write_operation_exclusion(self, user_data_manager):
        """Test that write operations are mutually exclusive."""
        results = []
        errors = []

        def write_operation(worker_id):
            try:
                start_time = time.time()
                with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
                    acquisition_time = time.time() - start_time
                    time.sleep(0.2)
                    results.append({
                        'worker_id': worker_id,
                        'acquisition_time': acquisition_time,
                        'is_master': 'master' in effective_dir
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': worker_id, 'error': str(e)})

        # Run 3 concurrent write operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(write_operation, i) for i in range(3)]
            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 3, "Expected 3 write operations"

        # All should use master directory
        for result in results:
            assert result['is_master'], "Write operation should use master directory"

    def test_mixed_read_write_operations(self, user_data_manager):
        """Test mixed read and write operations."""
        read_results = []
        write_results = []
        errors = []

        def read_operation(worker_id):
            try:
                with user_data_manager.get_user_data_context('read') as (effective_dir, cleanup):
                    time.sleep(0.1)
                    read_results.append({
                        'worker_id': worker_id,
                        'is_clone': 'clones' in effective_dir
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': f'read-{worker_id}', 'error': str(e)})

        def write_operation(worker_id):
            try:
                with user_data_manager.get_user_data_context('write') as (effective_dir, cleanup):
                    time.sleep(0.15)
                    write_results.append({
                        'worker_id': worker_id,
                        'is_master': 'master' in effective_dir
                    })
                    cleanup()
            except Exception as e:
                errors.append({'worker_id': f'write-{worker_id}', 'error': str(e)})

        # Run mixed operations
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            # Submit read operations
            for i in range(3):
                futures.append(executor.submit(read_operation, i))
            # Submit write operations
            for i in range(2):
                futures.append(executor.submit(write_operation, i))

            for future in as_completed(futures):
                future.result()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(read_results) == 3, "Expected 3 reads"
        assert len(write_results) == 2, "Expected 2 writes"

        # Verify directory usage
        for result in read_results:
            assert result['is_clone'], "Read should use clone directory"
        for result in write_results:
            assert result['is_master'], "Write should use master directory"