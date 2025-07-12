class MockedCoverManager:
    """Manager for mapped covers created during tests with automatic cleanup."""

    def __init__(self):
        self.mapped_covers = []

    def add_cover(self, mapped_cover):
        """Add a mapped cover for tracking."""
        self.mapped_covers.append(mapped_cover)
        return mapped_cover

    def cleanup_all(self):
        """Clean up all tracked mapped covers."""
        for mapped_cover in self.mapped_covers:
            try:
                # Cancel any running tasks
                for task in list(mapped_cover._running_tasks):
                    if not task.done():
                        task.cancel()
                mapped_cover._running_tasks.clear()
                # Remove any state listeners
                for remove_func in list(mapped_cover._state_listeners):
                    try:
                        remove_func()
                    except Exception:
                        pass
                mapped_cover._state_listeners.clear()
            except Exception:
                pass
        self.mapped_covers.clear()
