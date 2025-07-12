import pytest_check as check
from typing import Dict, Optional


def assert_create_entry(result: Dict, expected_title: str, expected_data: Optional[Dict] = None) -> None:
    """Assert that a flow result creates an entry with expected properties.

    Args:
      result: The flow result to check
      expected_title: Expected entry title
      expected_data: Optional dict of expected data fields
    """
    check.equal(result["type"], "create_entry",
                f"Expected create_entry, got {result['type']}")
    check.equal(result["title"], expected_title,
                f"Expected title {expected_title}, got {result['title']}")
    if expected_data:
        data = result["data"]
        for key, value in expected_data.items():
            check.equal(
                data[key],
                value,
                f"Expected {key}={value}, got {data[key]}"
            )
