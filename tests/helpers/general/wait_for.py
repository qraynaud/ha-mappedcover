import time
import asyncio
from typing import Callable


async def wait_for(
    condition: Callable[[], bool],
    timeout: float = 0.1,
    interval: float = 0.001,
    error_message: str = None
) -> None:
    """
    Wait for a condition to become true, polling every interval, up to timeout seconds.
    Raises AssertionError if the condition is not met in time.

    Args:
      condition: A zero-argument callable returning a bool.
      timeout: Maximum time to wait in seconds (default 0.1).
      interval: Polling interval in seconds (default 0.001).
      error_message: Optional error message for AssertionError if condition is not met.

    Raises:
      AssertionError: If the condition does not become true within the timeout.
    """
    start = time.time()
    while not condition():
        if time.time() - start > timeout:
            raise AssertionError(
                error_message or f"Condition was not met within {timeout} seconds.")
        await asyncio.sleep(interval)
