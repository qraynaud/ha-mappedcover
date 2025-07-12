def convert_user_to_source_position(user_pos: int, min_pos: int = 10, max_pos: int = 90) -> int:
    """Convert user scale position (0-100) to source scale position.

    Args:
      user_pos: Position in user scale (0-100)
      min_pos: Minimum position in source scale
      max_pos: Maximum position in source scale

    Returns:
      int: Position in source scale
    """
    if user_pos == 0:
        return 0
    elif user_pos == 100:
        return max_pos
    else:
        # Linear interpolation: user_pos/100 * (max_pos - min_pos) + min_pos
        return int(user_pos * (max_pos - min_pos) / 100 + min_pos)
