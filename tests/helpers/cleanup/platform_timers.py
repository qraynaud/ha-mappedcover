async def cleanup_platform_timers(hass):
    """Clean up any lingering platform timers to avoid test warnings.

    Args:
      hass: The HomeAssistant instance to clean up.
    """
    all_platforms = hass.data.get("entity_platform", {})

    for _, platforms in all_platforms.items():
        for platform in platforms:
            if hasattr(platform, '_async_polling_timer') and platform._async_polling_timer:
                platform._async_polling_timer.cancel()
                platform._async_polling_timer = None
