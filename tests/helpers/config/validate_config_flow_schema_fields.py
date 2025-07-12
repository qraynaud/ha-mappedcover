from typing import Dict, List
import pytest_check as check


async def validate_config_flow_schema_fields(
    hass,
    step_result: Dict,
    expected_basic_fields: List[str],
    expected_tilt_fields: List[str] = None,
    covers_with_tilt: List[str] = None
) -> None:
    """Validate that a config flow schema contains expected fields based on cover capabilities."""
    check.equal(step_result["type"], "form",
                f"Expected form step, got {step_result['type']}")
    check.equal(step_result["step_id"], "configure",
                f"Expected step_id configure, got {step_result['step_id']}")

    schema_str = str(step_result["data_schema"]).lower()

    # Check basic fields are always present
    for field in expected_basic_fields:
        check.is_true(
            field.lower() in schema_str,
            f"Expected basic field '{field}' not found"
        )

    # Check tilt fields only if covers support tilt
    if expected_tilt_fields and covers_with_tilt:
        from custom_components.mappedcover.config_flow import supports_tilt
        has_tilt_support = any(supports_tilt(hass, cover)
                               for cover in covers_with_tilt)

        for field in expected_tilt_fields:
            if has_tilt_support:
                check.is_true(
                    field.lower() in schema_str,
                    f"Expected tilt field '{field}' not found when tilt is supported"
                )
            else:
                check.is_true(
                    field.lower() not in schema_str,
                    f"Unexpected tilt field '{field}' found when tilt not supported"
                )
