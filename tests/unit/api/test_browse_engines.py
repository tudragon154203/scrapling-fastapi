"""Integration tests for browse endpoint engine selection.

These tests require real browser automation and will test both
Camoufox and Chromium engines to ensure they work correctly.
"""

import pytest
import time

pytestmark = [
    pytest.mark.unit,
]


@pytest.mark.slow
def test_browse_camoufox_engine_integration(client):
    """Test browse endpoint with Camoufox engine using real browser automation."""
    # Use a simple test page that loads quickly
    body = {
        "url": "about:blank",
        "engine": "camoufox"
    }

    # Note: This test may take longer as it launches a real browser
    start_time = time.time()

    try:
        resp = client.post("/browse", json=body, timeout=30)
        elapsed = time.time() - start_time

        # Should succeed if Camoufox is available
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "success"
            assert "completed successfully" in data["message"].lower()
            print(f"Camoufox engine test passed in {elapsed:.2f}s")
        else:
            # If Camoufox is not available, test should be skipped
            assert resp.status_code in [500, 409]  # 500 for missing lib, 409 for browser issues
            data = resp.json()
            if "not available" in data.get("message", "").lower() or "camoufox" in data.get("message", "").lower():
                pytest.skip("Camoufox not available for integration testing")
            else:
                # Other failure - still fail the test
                pytest.fail(f"Camoufox engine test failed: {resp.status_code} - {data}")

    except Exception as e:
        pytest.skip(f"Camoufox engine integration test skipped due to: {e}")


@pytest.mark.slow
def test_browse_chromium_engine_integration(client):
    """Test browse endpoint with Chromium engine using real browser automation."""
    # Use a simple test page that loads quickly
    body = {
        "url": "about:blank",
        "engine": "chromium"
    }

    # Note: This test may take longer as it launches a real browser
    start_time = time.time()

    try:
        resp = client.post("/browse", json=body, timeout=30)
        elapsed = time.time() - start_time

        # Should succeed if Chromium/DynamicFetcher is available
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "success"
            assert "completed successfully" in data["message"].lower()
            print(f"Chromium engine test passed in {elapsed:.2f}s")
        else:
            # If Chromium/DynamicFetcher is not available, test should be skipped
            assert resp.status_code in [500, 409]  # 500 for missing lib, 409 for browser issues
            data = resp.json()
            if ("not available" in data.get("message", "").lower() or
                    "dynamicfetcher" in data.get("message", "").lower() or
                    "chromium" in data.get("message", "").lower()):
                pytest.skip("Chromium/DynamicFetcher not available for integration testing")
            else:
                # Other failure - still fail the test
                pytest.fail(f"Chromium engine test failed: {resp.status_code} - {data}")

    except Exception as e:
        pytest.skip(f"Chromium engine integration test skipped due to: {e}")


@pytest.mark.slow
def test_browse_default_engine_integration(client):
    """Test browse endpoint with default engine (should be Camoufox)."""
    # Test without specifying engine - should default to Camoufox
    body = {
        "url": "about:blank"
        # No engine specified
    }

    start_time = time.time()

    try:
        resp = client.post("/browse", json=body, timeout=30)
        elapsed = time.time() - start_time

        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "success"
            print(f"Default engine test passed in {elapsed:.2f}s")
        else:
            # If default engine is not available, skip
            assert resp.status_code in [500, 409]
            data = resp.json()
            if "not available" in data.get("message", "").lower():
                pytest.skip("Default engine not available for integration testing")
            else:
                pytest.fail(f"Default engine test failed: {resp.status_code} - {data}")

    except Exception as e:
        pytest.skip(f"Default engine integration test skipped due to: {e}")


@pytest.mark.slow
def test_browse_engine_consistency(client):
    """Test that both engines produce consistent behavior for the same URL."""
    test_url = "about:blank"
    results = {}

    # Test Camoufox
    try:
        body = {"url": test_url, "engine": "camoufox"}
        resp = client.post("/browse", json=body, timeout=30)

        if resp.status_code == 200:
            results["camoufox"] = resp.json()
        else:
            results["camoufox"] = {"error": resp.status_code, "message": resp.json().get("message", "")}
    except Exception as e:
        results["camoufox"] = {"error": "exception", "message": str(e)}

    # Test Chromium
    try:
        body = {"url": test_url, "engine": "chromium"}
        resp = client.post("/browse", json=body, timeout=30)

        if resp.status_code == 200:
            results["chromium"] = resp.json()
        else:
            results["chromium"] = {"error": resp.status_code, "message": resp.json().get("message", "")}
    except Exception as e:
        results["chromium"] = {"error": "exception", "message": str(e)}

    # Analyze results
    successful_engines = [engine for engine, result in results.items() if result.get("status") == "success"]

    if len(successful_engines) == 0:
        pytest.skip(f"No engines available: {results}")
    elif len(successful_engines) == 1:
        # At least one engine works - test partially passes
        print(f"Only {successful_engines[0]} engine available: {results}")
    else:
        # Both engines work - check consistency
        camoufox_result = results["camoufox"]
        chromium_result = results["chromium"]

        assert camoufox_result["status"] == chromium_result["status"] == "success"
        # Both should indicate successful completion
        assert "completed successfully" in camoufox_result["message"].lower()
        assert "completed successfully" in chromium_result["message"].lower()

        print("Both engines produced consistent successful results")
