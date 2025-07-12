from .assert_abort import assert_abort
from typing import Dict


def assert_reconfigure_successful(result: Dict) -> None:
    """Assert that a reconfigure flow completed successfully.

    Args:
      result: The flow result to check
    """
    assert_abort(result, "reconfigure_successful")
