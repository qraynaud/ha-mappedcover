def convert_user_to_source_tilt(user_tilt: int, min_tilt: int = 5, max_tilt: int = 95) -> int:
    """Convert user scale tilt (0-100) to source scale tilt.

    Args:
      user_tilt: Tilt in user scale (0-100)
      min_tilt: Minimum tilt in source scale
      max_tilt: Maximum tilt in source scale

    Returns:
      int: Tilt in source scale
    """
    if user_tilt == 0:
        return 0
    elif user_tilt == 100:
        return max_tilt
    else:
        # Linear interpolation for tilt
        return int(user_tilt * (max_tilt - min_tilt) / 100 + min_tilt)
