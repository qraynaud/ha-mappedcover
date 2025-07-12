from typing import Callable, Dict
from homeassistant.core import HomeAssistant
from tests.helpers.entities.create_command_test_environment import create_command_test_environment
import pytest_check as check


async def command_with_target_validation(
    hass: HomeAssistant,
    command_func: Callable,
    expected_targets: Dict[str, int],
    should_converge: bool = True,
    **env_kwargs
) -> bool:
    """Test a command and validate that it sets the expected targets.

    Args:
      hass: HomeAssistant instance
      command_func: Async function that executes the command
      expected_targets: Dict with 'position' and/or 'tilt' expected values
      should_converge: Whether convergence should be triggered
      **env_kwargs: Arguments passed to create_command_test_environment

    Returns:
      bool: True if all validations passed
    """
    env = await create_command_test_environment(hass, **env_kwargs)
    mapped_cover = env["entity"]
    convergence_mock = env.get("convergence_mock")
    await command_func(mapped_cover)
    if "position" in expected_targets:
        check.equal(
            mapped_cover._target_position,
            expected_targets["position"],
            f"Expected position target {expected_targets['position']}, got {mapped_cover._target_position}"
        )
    if "tilt" in expected_targets:
        check.equal(
            mapped_cover._target_tilt,
            expected_targets["tilt"],
            f"Expected tilt target {expected_targets['tilt']}, got {mapped_cover._target_tilt}"
        )
    if should_converge and convergence_mock:
        convergence_mock.assert_called_once()
    elif not should_converge and convergence_mock:
        convergence_mock.assert_not_called()
    return True
