import pytest_check as check
from typing import List


def assert_service_called(call_tracker: List, service_name: str, **kwargs) -> None:
    """Assert that a service was called, optionally with specific parameters.

    Args:
      call_tracker: List of service calls to check (tuples or dicts)
      service_name: Name of service that should have been called
      **kwargs: Optional service data to verify
    """
    found = False
    matching_calls = []
    for call in call_tracker:
        if isinstance(call, dict):
            if call['service'] == service_name:
                found = True
                matching_calls.append(call)
        elif isinstance(call, tuple):
            svc, data = call
            if svc == service_name:
                found = True
                if kwargs:
                    if data and all(data.get(k) == v for k, v in kwargs.items()):
                        matching_calls.append(call)
                else:
                    matching_calls.append(call)
        else:
            if call == service_name:
                found = True
                matching_calls.append(call)
    check.is_true(found, f"Service {service_name} was not called")
    if kwargs:
        check.is_true(
            len(matching_calls) > 0,
            f"Service '{service_name}' was called but not with expected data {kwargs}. Actual calls: {call_tracker}"
        )
