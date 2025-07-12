from typing import Callable
from homeassistant.core import HomeAssistant
from tests.helpers.entities.create_command_test_environment import create_command_test_environment


async def verify_command_skips_convergence(
    hass: HomeAssistant,
    command_func: Callable,
    condition: str,
    **env_kwargs
) -> bool:
    """Verify that a command skips convergence under specific conditions.

    Args:
      hass: HomeAssistant instance
      command_func: Async function that executes the command
      condition: Description of the condition being tested
      **env_kwargs: Arguments passed to create_command_test_environment

    Returns:
      bool: True if convergence was properly skipped
    """
    env = await create_command_test_environment(hass, **env_kwargs)
    mapped_cover = env["entity"]
    convergence_mock = env.get("convergence_mock")
    await command_func(mapped_cover)
    if convergence_mock:
        convergence_mock.assert_not_called()
    return True
