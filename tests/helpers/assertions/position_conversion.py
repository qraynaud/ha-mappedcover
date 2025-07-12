import pytest_check as check
from tests.helpers import convert_user_to_source_position


def assert_position_conversion(user_pos: int, expected_source: int, min_pos: int = 10, max_pos: int = 90) -> None:
    """Assert that position conversion works as expected.

    Args:
      user_pos: Position in user scale
      expected_source: Expected position in source scale
      min_pos: Minimum position in source scale
      max_pos: Maximum position in source scale
    """
    actual = convert_user_to_source_position(user_pos, min_pos, max_pos)
    check.equal(
        actual,
        expected_source,
        f"Position conversion failed: user_pos={user_pos}, min_pos={min_pos}, max_pos={max_pos}, got {actual}, expected {expected_source}"
    )
