from src.models.execution_context import ExecutionContext

class ExecutionContextService:
    """Service for determining execution context."""
    
    @staticmethod
    def is_test_environment() -> bool:
        """
        Determine if the application is running in a test environment.
        
        Returns:
            bool: True if running in test environment, False otherwise
        """
        return ExecutionContext.is_test_environment()