import pytest_check as check
from typing import Dict, List, Optional


def assert_form_step(result: Dict, step_id: str, expected_fields: Optional[List[str]] = None) -> None:
    """Assert that a flow result is a form step with expected properties.

    Args:
      result: The flow result to check
      step_id: Expected step ID
      expected_fields: Optional list of field names expected in schema
    """
    check.equal(result["type"], "form",
                f"Expected form step, got {result['type']}")
    check.equal(result["step_id"], step_id,
                f"Expected step_id {step_id}, got {result['step_id']}")
    check.is_not_none(result["data_schema"], "Data schema should not be None")
    if expected_fields:
        schema_str = str(result["data_schema"]).lower()
        for field in expected_fields:
            check.is_true(
                field.lower() in schema_str,
                f"Expected field '{field}' not found in schema"
            )
