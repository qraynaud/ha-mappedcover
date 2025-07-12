import pytest_check as check
from typing import List


def assert_service_not_called(call_tracker: List, service_name: str, **kwargs) -> None:
    """Assert that a service was not called, optionally with specific parameters.

    Args:
      call_tracker: List of service calls to check (tuples or dicts)
      service_name: Name of service that should not have been called
      **kwargs: Optional service data to verify
    """
    for call in call_tracker:
        if isinstance(call, dict):
            if call['service'] == service_name:
                if not kwargs or all(call['data'].get(k) == v for k, v in kwargs.items()):
                    check.is_false(
                        True, f"Service {service_name} was called when it should not have been")
        elif isinstance(call, tuple):
            svc, data = call
            if svc == service_name:
                if not kwargs or (data and all(data.get(k) == v for k, v in kwargs.items())):
                    check.is_false(
                        True, f"Service {service_name} was called when it should not have been")
        else:
            if call == service_name:
                check.is_false(
                    True, f"Service {service_name} was called when it should not have been")
    # If we get here, the service was not called as required
    check.is_true(True)
