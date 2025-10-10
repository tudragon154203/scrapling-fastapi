"""Integration tests for Chromium browse endpoint error handling and enhanced messages.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures("require_scrapling"),
]


class TestChromiumBrowseErrorHandling:
    """Test comprehensive error handling for Chromium browse endpoint."""

    def test_lock_conflict_detailed_error(self, client):
        """Test detailed error message for lock conflicts."""
        import tempfile

        # Create a temporary user data directory
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir) / "chromium_test"

            # Mock the user data manager to simulate lock conflict
            with patch(
                'app.services.browser.browse.ChromiumUserDataManager'
            ) as mock_manager_class:
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager

                # Simulate lock conflict
                mock_manager.get_user_data_context.side_effect = RuntimeError(
                    "Profile already in use by another session"
                )

                response = client.post("/browse", json={
                    "url": "https://example.com",
                    "engine": "chromium"
                })

                assert response.status_code == 409  # Conflict status
                data = response.json()
                assert data["status"] == "failure"

                # Should contain detailed troubleshooting steps
                message = data["message"]
                assert "already in use" in message.lower()
                assert "wait for the current session" in message.lower()
                assert "lock file" in message.lower()
                assert "chromium_user_data_dir" in message.lower()

    def test_disk_space_error_handling(self, client):
        """Test error handling when disk space is exhausted."""
        with patch(
            'app.services.browser.browse.ChromiumUserDataManager'
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # Simulate disk space error
            mock_manager.get_user_data_context.side_effect = OSError(
                "No space left on device"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "failure"

            # Should contain disk space troubleshooting
            message = data["message"]
            assert "disk space" in message.lower() or "no space" in message.lower()

    def test_permission_error_handling(self, client):
        """Test error handling for permission issues."""
        with patch(
            'app.services.browser.browse.ChromiumUserDataManager'
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # Simulate permission error
            mock_manager.get_user_data_context.side_effect = PermissionError(
                "Permission denied"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "failure"

            # Should contain permission troubleshooting
            message = data["message"]
            assert "permission" in message.lower() or "access" in message.lower()

    def test_chromium_specific_engine_validation(self, client):
        """Test that invalid engine values are properly validated."""
        # Test with completely invalid engine
        response = client.post("/browse", json={
            "url": "https://example.com",
            "engine": "invalid_browser"
        })

        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
        assert "engine" in str(error_detail["detail"]).lower()

    def test_camoufox_engine_fallback_works(self, client):
        """Test that Camoufox engine still works when Chromium has issues."""
        with patch(
            'app.services.browser.executors.chromium_browse_executor.DYNAMIC_FETCHER_AVAILABLE',  # noqa: E501
            False,
        ):
            # Camoufox should still work
            with patch('app.services.browser.browse.BrowseCrawler') as mock_crawler:
                mock_instance = MagicMock()
                mock_crawler.return_value = mock_instance
                mock_instance.run.return_value = MagicMock(
                    status="success",
                    message="Camoufox session completed successfully"
                )

                response = client.post("/browse", json={
                    "url": "https://example.com",
                    "engine": "camoufox"
                })

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

    def test_profile_not_found_guidance(self, client):
        """Test helpful guidance when user data directory doesn't exist."""
        with patch(
            'app.services.browser.browse.ChromiumUserDataManager'
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # Simulate missing user data directory
            mock_manager.enabled = False
            mock_manager.get_user_data_context.side_effect = RuntimeError(
                "User data management disabled"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            # Should handle gracefully with fallback to temporary profile
            assert response.status_code in [
                200, 500
            ]  # May succeed with fallback or fail

    def test_network_connectivity_issues(self, client):
        """Test handling of network connectivity issues."""
        with patch(
            'app.services.browser.executors.chromium_browse_executor.ChromiumBrowseExecutor'  # noqa: E501
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Simulate network error
            mock_executor.execute.side_effect = ConnectionError(
                "Network is unreachable"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "failure"

            # Should contain network troubleshooting
            message = data["message"]
            assert "network" in message.lower() or "connection" in message.lower()

    def test_corrupted_profile_recovery_guidance(self, client):
        """Test guidance when profile is corrupted."""
        with patch(
            'app.services.browser.browse.ChromiumUserDataManager'
        ) as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager

            # Simulate corrupted profile
            mock_manager.get_user_data_context.side_effect = RuntimeError(
                "Profile database is corrupted"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "failure"

            # Should contain recovery guidance
            message = data["message"]
            assert "corrupted" in message.lower() or "recovery" in message.lower()

    def test_browser_version_compatibility_error(self, client):
        """Test handling of browser version compatibility issues."""
        with patch(
            'app.services.browser.executors.chromium_browse_executor.ChromiumBrowseExecutor'  # noqa: E501
        ) as mock_executor_class:
            mock_executor = MagicMock()
            mock_executor_class.return_value = mock_executor

            # Simulate version compatibility error
            mock_executor.execute.side_effect = RuntimeError(
                "Browser version incompatible with Playwright"
            )

            response = client.post("/browse", json={
                "url": "https://example.com",
                "engine": "chromium"
            })

            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "failure"

            # Should contain version/compatibility troubleshooting
            message = data["message"]
            assert "version" in message.lower() or "compatib" in message.lower()
            assert "playwright" in message.lower()
