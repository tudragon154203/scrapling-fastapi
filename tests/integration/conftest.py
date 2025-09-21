import pytest


@pytest.fixture(scope="session")
def require_scrapling() -> None:
    """Ensure Scrapling and its heavy dependencies are importable when needed.

    The integration test suite depends on the real Scrapling package. Importing
    it eagerly during module collection breaks `pytest -m "not integration"`
    because the modules are still imported even though the tests will be
    deselected. By deferring the import to a fixture we avoid the collection
    error while still failing fast when the integration tests actually run.
    """

    try:  # pragma: no cover - exercised only in integration environments
        import scrapling.fetchers  # noqa: F401
    except Exception as exc:  # pragma: no cover - fail loudly in CI
        pytest.fail(f"scrapling is required for integration tests: {exc}")
