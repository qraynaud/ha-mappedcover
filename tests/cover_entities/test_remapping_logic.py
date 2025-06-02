"""Test remapping logic for MappedCover."""
import pytest
from custom_components.mappedcover.cover import remap_value, RemapDirection

# Direct imports - conftest.py handles the Python path setup
from tests.fixtures import *  # Import all shared fixtures


class TestRemapValueToSource:
  """Test RemapDirection.TO_SOURCE: user values (0-100) to source range."""

  def test_to_source_zero_always_maps_to_zero(self):
    """Test that user value 0 always maps to 0 regardless of min/max."""
    assert remap_value(0, 10, 90, RemapDirection.TO_SOURCE) == 0
    assert remap_value(0, 25, 75, RemapDirection.TO_SOURCE) == 0
    assert remap_value(0, 0, 100, RemapDirection.TO_SOURCE) == 0
    assert remap_value(0, 50, 50, RemapDirection.TO_SOURCE) == 0

  def test_to_source_linear_mapping_basic(self):
    """Test basic linear mapping from 1-100 to min_value-max_value."""
    # Test with range 10-90
    assert remap_value(1, 10, 90, RemapDirection.TO_SOURCE) == 10
    assert remap_value(100, 10, 90, RemapDirection.TO_SOURCE) == 90
    assert remap_value(50, 10, 90, RemapDirection.TO_SOURCE) == 50  # Middle should be approximately middle

  def test_to_source_linear_mapping_different_ranges(self):
    """Test linear mapping with various min/max ranges."""
    # Test with range 20-80
    assert remap_value(1, 20, 80, RemapDirection.TO_SOURCE) == 20
    assert remap_value(100, 20, 80, RemapDirection.TO_SOURCE) == 80

    # Test with range 0-50
    assert remap_value(1, 0, 50, RemapDirection.TO_SOURCE) == 0  # Formula: (1-1)*50/99+0 = 0
    assert remap_value(100, 0, 50, RemapDirection.TO_SOURCE) == 50

    # Test with range 30-100
    assert remap_value(1, 30, 100, RemapDirection.TO_SOURCE) == 30
    assert remap_value(100, 30, 100, RemapDirection.TO_SOURCE) == 100

  def test_to_source_linear_mapping_precision(self):
    """Test precise linear mapping calculations."""
    # With range 10-90 (span of 80), user 50 should map to 49.19... ≈ 50 (rounds to 50)
    result = remap_value(50, 10, 90, RemapDirection.TO_SOURCE)
    assert result == 50

    # With range 25-75 (span of 50), user 25 should map to ~37
    result = remap_value(25, 25, 75, RemapDirection.TO_SOURCE)
    assert result == 37

  def test_to_source_boundary_values(self):
    """Test boundary values for TO_SOURCE direction."""
    # Test values just above 0
    assert remap_value(1, 10, 90, RemapDirection.TO_SOURCE) == 10
    assert remap_value(2, 10, 90, RemapDirection.TO_SOURCE) == 11

    # Test values just below 100
    assert remap_value(99, 10, 90, RemapDirection.TO_SOURCE) == 89
    assert remap_value(100, 10, 90, RemapDirection.TO_SOURCE) == 90

  def test_to_source_rounding_behavior(self):
    """Test that results are properly rounded to integers."""
    # These should test rounding behavior
    result = remap_value(33, 10, 90, RemapDirection.TO_SOURCE)
    assert isinstance(result, int)

    result = remap_value(67, 10, 90, RemapDirection.TO_SOURCE)
    assert isinstance(result, int)

  def test_to_source_clamping_behavior(self):
    """Test that results are clamped to valid ranges."""
    # Values outside 0-100 should be clamped
    result = remap_value(150, 10, 90, RemapDirection.TO_SOURCE)
    assert result <= 90

    result = remap_value(-10, 10, 90, RemapDirection.TO_SOURCE)
    assert result >= 0  # Should handle gracefully

  def test_to_source_min_equals_max(self):
    """Test edge case where min_value equals max_value."""
    # When min_value == max_value, TO_SOURCE should return 0
    assert remap_value(50, 50, 50, RemapDirection.TO_SOURCE) == 0
    assert remap_value(1, 25, 25, RemapDirection.TO_SOURCE) == 0
    assert remap_value(100, 75, 75, RemapDirection.TO_SOURCE) == 0


class TestRemapValueFromSource:
  """Test RemapDirection.FROM_SOURCE: source values to user scale (0-100)."""

  def test_from_source_zero_always_maps_to_zero(self):
    """Test that source value 0 always maps to 0 regardless of min/max."""
    assert remap_value(0, 10, 90, RemapDirection.FROM_SOURCE) == 0
    assert remap_value(0, 25, 75, RemapDirection.FROM_SOURCE) == 0
    assert remap_value(0, 0, 100, RemapDirection.FROM_SOURCE) == 0
    assert remap_value(0, 50, 50, RemapDirection.FROM_SOURCE) == 0

  def test_from_source_linear_mapping_basic(self):
    """Test basic linear mapping from min_value-max_value to 1-100."""
    # Test with range 10-90
    assert remap_value(10, 10, 90, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(90, 10, 90, RemapDirection.FROM_SOURCE) == 100
    assert remap_value(50, 10, 90, RemapDirection.FROM_SOURCE) == 50  # Middle should be approximately middle

  def test_from_source_linear_mapping_different_ranges(self):
    """Test linear mapping with various min/max ranges."""
    # Test with range 20-80
    assert remap_value(20, 20, 80, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(80, 20, 80, RemapDirection.FROM_SOURCE) == 100

    # Test with range 0-50
    assert remap_value(1, 0, 50, RemapDirection.FROM_SOURCE) == 3  # Should map to ~3
    assert remap_value(50, 0, 50, RemapDirection.FROM_SOURCE) == 100

    # Test with range 30-100
    assert remap_value(30, 30, 100, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(100, 30, 100, RemapDirection.FROM_SOURCE) == 100

  def test_from_source_below_minimum_handling(self):
    """Test that source values below min_value map to 1 (not 0)."""
    # This is a key requirement: below min_value should return 1, not 0
    assert remap_value(5, 10, 90, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(15, 20, 80, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(-10, 10, 90, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(0.5, 5, 95, RemapDirection.FROM_SOURCE) == 1

  def test_from_source_boundary_values(self):
    """Test boundary values for FROM_SOURCE direction."""
    # Test min_value and max_value exactly
    assert remap_value(10, 10, 90, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(90, 10, 90, RemapDirection.FROM_SOURCE) == 100

    # Test values just above min_value
    assert remap_value(11, 10, 90, RemapDirection.FROM_SOURCE) == 2

    # Test values just below max_value
    assert remap_value(89, 10, 90, RemapDirection.FROM_SOURCE) == 99

  def test_from_source_precision_mapping(self):
    """Test precise linear mapping calculations."""
    # With range 10-90 (span of 80), source 50 should map to ~50
    result = remap_value(50, 10, 90, RemapDirection.FROM_SOURCE)
    assert result == 50

    # With range 25-75 (span of 50), source 50 should map to ~50
    result = remap_value(50, 25, 75, RemapDirection.FROM_SOURCE)
    assert result == 50

  def test_from_source_rounding_behavior(self):
    """Test that results are properly rounded to integers."""
    result = remap_value(33, 10, 90, RemapDirection.FROM_SOURCE)
    assert isinstance(result, int)

    result = remap_value(67, 10, 90, RemapDirection.FROM_SOURCE)
    assert isinstance(result, int)

  def test_from_source_clamping_behavior(self):
    """Test that results are clamped to valid ranges (1-100)."""
    # Results should be clamped between 1-100
    result = remap_value(200, 10, 90, RemapDirection.FROM_SOURCE)
    assert 1 <= result <= 100

    # Below min_value should return 1
    result = remap_value(-50, 10, 90, RemapDirection.FROM_SOURCE)
    assert result == 1

  def test_from_source_min_equals_max(self):
    """Test edge case where min_value equals max_value."""
    # When min_value == max_value, FROM_SOURCE should return min_value
    assert remap_value(50, 50, 50, RemapDirection.FROM_SOURCE) == 50
    assert remap_value(25, 25, 25, RemapDirection.FROM_SOURCE) == 25
    assert remap_value(75, 75, 75, RemapDirection.FROM_SOURCE) == 75


class TestRemapValueEdgeCases:
  """Test edge cases and special scenarios for remap_value function."""

  def test_none_input_handling(self):
    """Test that None input returns None."""
    assert remap_value(None, 10, 90, RemapDirection.TO_SOURCE) is None
    assert remap_value(None, 10, 90, RemapDirection.FROM_SOURCE) is None
    assert remap_value(None, 0, 100, RemapDirection.TO_SOURCE) is None
    assert remap_value(None, 0, 100, RemapDirection.FROM_SOURCE) is None

  def test_full_range_mapping(self):
    """Test mapping with full 0-100 range."""
    # When min=0, max=100, values should pass through mostly unchanged
    assert remap_value(0, 0, 100, RemapDirection.TO_SOURCE) == 0
    assert remap_value(1, 0, 100, RemapDirection.TO_SOURCE) == 0  # Formula: (1-1)*100/99 + 0 = 0
    assert remap_value(50, 0, 100, RemapDirection.TO_SOURCE) == 49  # Formula: (50-1)*100/99 + 0 ≈ 49
    assert remap_value(100, 0, 100, RemapDirection.TO_SOURCE) == 100

    assert remap_value(0, 0, 100, RemapDirection.FROM_SOURCE) == 0
    assert remap_value(1, 0, 100, RemapDirection.FROM_SOURCE) == 2  # 1->2 due to linear mapping
    assert remap_value(50, 0, 100, RemapDirection.FROM_SOURCE) == 50  # 50->50 due to linear mapping
    assert remap_value(100, 0, 100, RemapDirection.FROM_SOURCE) == 100

  def test_narrow_range_mapping(self):
    """Test mapping with very narrow ranges."""
    # Test with narrow range like 49-51
    assert remap_value(1, 49, 51, RemapDirection.TO_SOURCE) == 49
    assert remap_value(100, 49, 51, RemapDirection.TO_SOURCE) == 51
    assert remap_value(50, 49, 51, RemapDirection.TO_SOURCE) == 50

    assert remap_value(49, 49, 51, RemapDirection.FROM_SOURCE) == 1
    assert remap_value(51, 49, 51, RemapDirection.FROM_SOURCE) == 100
    assert remap_value(50, 49, 51, RemapDirection.FROM_SOURCE) == 50

  def test_inverted_range_handling(self):
    """Test behavior when min_value > max_value (edge case)."""
    # This might be an error condition, but test graceful handling
    # The function should handle this gracefully due to clamping
    result = remap_value(50, 90, 10, RemapDirection.TO_SOURCE)
    assert isinstance(result, int)

    result = remap_value(50, 90, 10, RemapDirection.FROM_SOURCE)
    assert isinstance(result, int)

  def test_single_point_ranges(self):
    """Test various single-point ranges (min == max)."""
    test_values = [0, 25, 50, 75, 100]
    for point in test_values:
      # TO_SOURCE should return 0 when min == max
      assert remap_value(50, point, point, RemapDirection.TO_SOURCE) == 0

      # FROM_SOURCE should return the point value when min == max
      assert remap_value(50, point, point, RemapDirection.FROM_SOURCE) == point

  def test_extreme_input_values(self):
    """Test with extreme input values."""
    # Very large values
    result = remap_value(1000, 10, 90, RemapDirection.TO_SOURCE)
    assert isinstance(result, int)
    assert result <= 90

    result = remap_value(1000, 10, 90, RemapDirection.FROM_SOURCE)
    assert isinstance(result, int)
    assert 1 <= result <= 100

    # Negative values
    result = remap_value(-100, 10, 90, RemapDirection.TO_SOURCE)
    assert isinstance(result, int)

    result = remap_value(-100, 10, 90, RemapDirection.FROM_SOURCE)
    assert result == 1  # Below min_value should return 1


class TestRemapValueSymmetry:
  """Test that TO_SOURCE and FROM_SOURCE are properly inverse operations."""

  def test_round_trip_symmetry_typical_values(self):
    """Test round-trip symmetry for typical values."""
    min_val, max_val = 10, 90

    # Test that TO_SOURCE followed by FROM_SOURCE gets back close to original
    for user_val in [1, 25, 50, 75, 100]:
      source_val = remap_value(user_val, min_val, max_val, RemapDirection.TO_SOURCE)
      back_to_user = remap_value(source_val, min_val, max_val, RemapDirection.FROM_SOURCE)

      # Should be within 1-2 units due to rounding
      assert abs(back_to_user - user_val) <= 2, f"Round trip failed: {user_val} -> {source_val} -> {back_to_user}"

  def test_round_trip_symmetry_various_ranges(self):
    """Test round-trip symmetry for various ranges."""
    test_ranges = [(0, 100), (20, 80), (25, 75), (5, 95)]

    for min_val, max_val in test_ranges:
      for user_val in [1, 33, 67, 100]:
        source_val = remap_value(user_val, min_val, max_val, RemapDirection.TO_SOURCE)
        back_to_user = remap_value(source_val, min_val, max_val, RemapDirection.FROM_SOURCE)

        # Should be within 2 units due to rounding
        assert abs(back_to_user - user_val) <= 2, f"Range {min_val}-{max_val}: {user_val} -> {source_val} -> {back_to_user}"

  def test_zero_symmetry(self):
    """Test that 0 always maps to 0 and back."""
    test_ranges = [(10, 90), (0, 100), (25, 75), (50, 50)]

    for min_val, max_val in test_ranges:
      # 0 -> 0 -> 0
      source_val = remap_value(0, min_val, max_val, RemapDirection.TO_SOURCE)
      assert source_val == 0

      back_to_user = remap_value(source_val, min_val, max_val, RemapDirection.FROM_SOURCE)
      assert back_to_user == 0


class TestRemapValueIntegration:
  """Test remapping integration with typical use cases."""

  def test_typical_blind_configuration(self):
    """Test remapping with typical blind configuration (10-90 range)."""
    min_pos, max_pos = 10, 90

    # User sets to fully open (100) -> should map to 90
    assert remap_value(100, min_pos, max_pos, RemapDirection.TO_SOURCE) == 90

    # Source reports 90 -> should show as fully open (100)
    assert remap_value(90, min_pos, max_pos, RemapDirection.FROM_SOURCE) == 100

    # User sets to fully closed (0) -> should map to 0
    assert remap_value(0, min_pos, max_pos, RemapDirection.TO_SOURCE) == 0

    # Source reports 0 -> should show as fully closed (0)
    assert remap_value(0, min_pos, max_pos, RemapDirection.FROM_SOURCE) == 0

  def test_typical_tilt_configuration(self):
    """Test remapping with typical tilt configuration (5-95 range)."""
    min_tilt, max_tilt = 5, 95

    # User sets to maximum tilt (100) -> should map to 95
    assert remap_value(100, min_tilt, max_tilt, RemapDirection.TO_SOURCE) == 95

    # Source reports 95 -> should show as maximum tilt (100)
    assert remap_value(95, min_tilt, max_tilt, RemapDirection.FROM_SOURCE) == 100

    # User sets minimum tilt (1) -> should map to 5
    assert remap_value(1, min_tilt, max_tilt, RemapDirection.TO_SOURCE) == 5

    # Source reports 5 -> should show as minimum tilt (1)
    assert remap_value(5, min_tilt, max_tilt, RemapDirection.FROM_SOURCE) == 1

  def test_partial_range_positions(self):
    """Test various partial range positions."""
    min_pos, max_pos = 20, 80

    # Test quarter positions
    quarter = remap_value(25, min_pos, max_pos, RemapDirection.TO_SOURCE)
    assert 30 <= quarter <= 35  # Should be roughly 1/4 of the way

    half = remap_value(50, min_pos, max_pos, RemapDirection.TO_SOURCE)
    assert 48 <= half <= 52  # Should be roughly middle

    three_quarter = remap_value(75, min_pos, max_pos, RemapDirection.TO_SOURCE)
    assert 65 <= three_quarter <= 70  # Should be roughly 3/4 of the way

  def test_default_values_from_constants(self):
    """Test remapping with default values from constants."""
    # Test with default ranges from the constants file
    from custom_components.mappedcover.const import (
      DEFAULT_MIN_POSITION, DEFAULT_MAX_POSITION,
      DEFAULT_MIN_TILT_POSITION, DEFAULT_MAX_TILT_POSITION
    )

    # Default position range is 0-100, so should be pass-through mostly
    assert remap_value(0, DEFAULT_MIN_POSITION, DEFAULT_MAX_POSITION, RemapDirection.TO_SOURCE) == 0
    assert remap_value(100, DEFAULT_MIN_POSITION, DEFAULT_MAX_POSITION, RemapDirection.TO_SOURCE) == 100

    # Default tilt range is also 0-100
    assert remap_value(0, DEFAULT_MIN_TILT_POSITION, DEFAULT_MAX_TILT_POSITION, RemapDirection.TO_SOURCE) == 0
    assert remap_value(100, DEFAULT_MIN_TILT_POSITION, DEFAULT_MAX_TILT_POSITION, RemapDirection.TO_SOURCE) == 100
