import pytest_check as check
from typing import Dict


def assert_abort(result: Dict, expected_reason: str) -> None:
    """Assert that a flow result is an abort with expected reason.

    Args:
      result: The flow result to check
      expected_reason: Expected abort reason
    """
    check.equal(result["type"], "abort",
                f"Expected abort, got {result['type']}")
    check.equal(result["reason"], expected_reason,
                f"Expected reason {expected_reason}, got {result['reason']}")
