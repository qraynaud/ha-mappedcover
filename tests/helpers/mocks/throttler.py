class MockThrottler:
    """Mock Throttler class for testing."""

    def __init__(self, *args, **kwargs):
        """Initialize the mock throttler."""
        pass

    async def __aenter__(self):
        """Enter context."""
        return self

    async def __aexit__(self, *args, **kwargs):
        """Exit context."""
        pass
