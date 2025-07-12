import pytest_check as check
from tests.helpers import convert_user_to_source_tilt


def assert_tilt_conversion(user_tilt: int, expected_source: int, min_tilt: int = 5, max_tilt: int = 95) -> None:
    """Assert that tilt conversion works as expected.

    Args:
      user_tilt: Tilt in user scale
      expected_source: Expected tilt in source scale
      min_tilt: Minimum tilt in source scale
      max_tilt: Maximum tilt in source scale
    """
    actual = convert_user_to_source_tilt(user_tilt, min_tilt, max_tilt)
    check.equal(
        actual,
        expected_source,
        f"Tilt conversion failed: {user_tilt} user -> expected {expected_source}, got {actual}"
    )
