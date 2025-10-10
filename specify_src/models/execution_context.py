import os

class ExecutionContext:
    """Represents the context in which the application is running."""
    
    @staticmethod
    def is_test_environment() -> bool:
        """
        Determine if the application is running in a test environment.
        
        Returns:
            bool: True if running in test environment, False otherwise
        """
        # Check for common test environment indicators
        return (
            os.getenv("TESTING", "").lower() == "true" or
            os.getenv("PYTEST_CURRENT_TEST") is not None or
            os.getenv("CI", "").lower() == "true"
        )