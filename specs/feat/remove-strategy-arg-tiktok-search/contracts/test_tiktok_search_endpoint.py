"""
Contract tests for TikTok search endpoint.
Tests API contract compliance and validation behavior.
"""

import pytest
import json
from typing import Dict, Any


class TestTikTokSearchContract:
    """Test suite for TikTok search endpoint contract compliance."""

    @pytest.mark.integration
    def test_endpoint_exists_and_responds(self, api_client):
        """Test that the TikTok search endpoint exists and responds to basic requests."""
        # This test should fail initially as endpoint needs implementation
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": False
        })
        assert response.status_code == 200, "Endpoint should exist and accept valid requests"

    @pytest.mark.integration
    def test_valid_request_structure(self, api_client):
        """Test valid request body structure and response format."""
        response = api_client.post("/tiktok/search", json={
            "query": "funny cats",
            "force_headful": False
        })
        assert response.status_code == 200

        data = response.json()
        assert "results" in data, "Response must contain results array"
        assert "total_count" in data, "Response must contain total_count"
        assert "search_metadata" in data, "Response must contain search_metadata"
        assert data["search_metadata"]["executed_path"] in ["browser-based", "headless"]
        assert "request_hash" in data["search_metadata"]

    @pytest.mark.integration
    def test_strategy_field_rejection(self, api_client):
        """Test that strategy field is rejected with appropriate error."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True,
            "strategy": "browser"  # This should be rejected
        })
        assert response.status_code == 400

        data = response.json()
        assert "error" in data, "Response must contain error field"
        assert "message" in data, "Response must contain message field"
        assert "strategy" in str(data["message"]).lower(), "Error should mention strategy parameter"

    @pytest.mark.integration
    def test_force_headful_boolean_parsing(self, api_client):
        """Test lenient force_headful parameter parsing."""
        test_cases = [
            (True, True),
            ("true", True),
            ("TRUE", True),
            ("1", True),
            (False, False),
            ("false", False),
            ("FALSE", False),
            ("0", False)
        ]

        for input_value, expected_execution in test_cases:
            response = api_client.post("/tiktok/search", json={
                "query": "test",
                "force_headful": input_value
            })
            assert response.status_code == 200, f"Should accept {input_value}"

            data = response.json()
            if expected_execution:
                assert data["search_metadata"]["executed_path"] == "browser-based"
            else:
                assert data["search_metadata"]["executed_path"] == "headless"

    @pytest.mark.integration
    def test_force_headful_invalid_values(self, api_client):
        """Test invalid force_headful parameter values are rejected."""
        invalid_values = ["yes", "no", "maybe", 2, -1, "random string"]

        for invalid_value in invalid_values:
            response = api_client.post("/tiktok/search", json={
                "query": "test",
                "force_headful": invalid_value
            })
            assert response.status_code in [400, 422], f"Should reject invalid value {invalid_value}"

    @pytest.mark.integration
    def test_missing_required_parameters(self, api_client):
        """Test validation of required parameters."""
        # Missing query
        response = api_client.post("/tiktok/search", json={
            "force_headful": True
        })
        assert response.status_code == 422

        # Missing force_headful
        response = api_client.post("/tiktok/search", json={
            "query": "test"
        })
        assert response.status_code == 422

    @pytest.mark.integration
    def test_optional_parameters_valid_values(self, api_client):
        """Test validation of optional parameters."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": False,
            "limit": 10,
            "offset": 5
        })
        assert response.status_code == 200

    @pytest.mark.integration
    def test_limit_parameter_bounds(self, api_client):
        """Test limit parameter validation - should reject values outside 1-100 range."""
        invalid_limits = [-1, 0, 101, 1000]

        for limit in invalid_limits:
            response = api_client.post("/tiktok/search", json={
                "query": "test",
                "force_headful": False,
                "limit": limit
            })
            assert response.status_code == 422, f"Should reject limit {limit}"

    @pytest.mark.integration
    def test_offset_parameter_bounds(self, api_client):
        """Test offset parameter validation - should reject negative values."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": False,
            "offset": -1
        })
        assert response.status_code == 422

    @pytest.mark.integration
    def test_browser_search_path(self, api_client):
        """Test that force_headful=True triggers browser-based search."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True
        })
        assert response.status_code == 200

        data = response.json()
        assert data["search_metadata"]["executed_path"] == "browser-based"

    @pytest.mark.integration
    def test_headless_search_path(self, api_client):
        """Test that force_headful=False triggers headless search."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": False
        })
        assert response.status_code == 200

        data = response.json()
        assert data["search_metadata"]["executed_path"] == "headless"

    @pytest.mark.integration
    def test_additional_parameters_rejection(self, api_client):
        """Test that unknown parameters are rejected."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True,
            "unknown_param": "should_reject"
        })
        assert response.status_code == 400

    @pytest.mark.integration
    def test_response_schema_compliance(self, api_client):
        """Test that response schema matches contract definition."""
        response = api_client.post("/tiktok/search", json={
            "query": "test video",
            "force_headful": True
        })
        assert response.status_code == 200

        data = response.json()

        # Validate required fields
        required_fields = ["results", "total_count", "search_metadata"]
        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Validate search_metadata structure
        metadata = data["search_metadata"]
        assert "executed_path" in metadata
        assert "execution_time" in metadata
        assert "request_hash" in metadata

        # Validate results array
        assert isinstance(data["results"], list)

        # Validate optional content structure if results exist
        if data["results"]:
            result = data["results"][0]
            result_keys = ["id", "title", "url", "author", "thumbnail_url"]
            for key in result_keys:
                assert key in result, f"Result missing required field: {key}"

    @pytest.mark.integration
    def test_error_response_format(self, api_client):
        """Test error response format matches contract."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True,
            "strategy": "rejected"
        })
        assert response.status_code == 400

        data = response.json()
        assert "error" in data
        assert "message" in data
        assert isinstance(data["error"], str)
        assert isinstance(data["message"], str)


class TestTikTokSearchIntegration:
    """Integration tests focusing on user scenarios from feature specification."""

    @pytest.mark.integration
    def test_scenario_1_browser_based_search(self, api_client):
        """Scenario 1: Given a TikTok search request with force_headful=True,
                      When the API is called, Then the system should execute
                      the browser-based multistep search path automatically."""
        response = api_client.post("/tiktok/search", json={
            "query": "funny videos",
            "force_headful": True
        })

        assert response.status_code == 200
        data = response.json()
        assert data["search_metadata"]["executed_path"] == "browser-based"

    @pytest.mark.integration
    def test_scenario_2_headless_search(self, api_client):
        """Scenario 2: Given a TikTok search request with force_headful=False,
                      When the API is called, Then the system should execute
                      the headless url param search path automatically."""
        response = api_client.post("/tiktok/search", json={
            "query": "music videos",
            "force_headful": False
        })

        assert response.status_code == 200
        data = response.json()
        assert data["search_metadata"]["executed_path"] == "headless"

    @pytest.mark.integration
    def test_scenario_3_no_strategy_field_in_schemas(self, api_client):
        """Scenario 3: Given a TikTok search request, When the request is processed,
                      Then no strategy field should be present in the request or response schemas."""
        # Test request rejection of strategy field
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True,
            "strategy": "any_value"
        })
        assert response.status_code == 400
        assert "strategy" in response.json()["message"].lower()

        # Test that successful responses don't contain strategy references
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True
        })
        assert response.status_code == 200
        data = response.json()
        assert "strategy" not in str(data).lower()

    @pytest.mark.integration
    def test_scenario_4_backwards_compatibility_error_handling(self, api_client):
        """Scenario 4: Test error handling for strategy field rejection."""
        response = api_client.post("/tiktok/search", json={
            "query": "test",
            "force_headful": True,
            "strategy": "old_method"
        })
        assert response.status_code == 400
        error_data = response.json()
        assert "strategy" in error_data["message"]
        assert "not supported" in error_data["message"].lower()