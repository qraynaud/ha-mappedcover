"""Test remapping logic for MappedCover.

This module tests the remap_value function that handles conversion between
user scale (0-100) and source cover's actual range.
"""
import pytest
import pytest_check as check
from custom_components.mappedcover.cover import remap_value, RemapDirection

# Import fixtures
from tests.fixtures import *  # Import all shared fixtures


class TestRemapValueToSource:
    """Test RemapDirection.TO_SOURCE: user values (0-100) to source range."""

    def test_to_source_zero_always_maps_to_zero(self):
        """Test that user value 0 always maps to 0 regardless of min/max."""
        check.equal(remap_value(0, 10, 90, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(0, 25, 75, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(0, 0, 100, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(0, 50, 50, RemapDirection.TO_SOURCE), 0)

    def test_to_source_linear_mapping_basic(self):
        """Test basic linear mapping from 1-100 to min_value-max_value."""
        # Test with range 10-90
        check.equal(remap_value(1, 10, 90, RemapDirection.TO_SOURCE), 10)
        check.equal(remap_value(100, 10, 90, RemapDirection.TO_SOURCE), 90)
        # Middle should be approximately middle
        check.equal(remap_value(50, 10, 90, RemapDirection.TO_SOURCE), 50)

    def test_to_source_linear_mapping_different_ranges(self):
        """Test linear mapping with various min/max ranges."""
        # Test with range 20-80
        check.equal(remap_value(1, 20, 80, RemapDirection.TO_SOURCE), 20)
        check.equal(remap_value(100, 20, 80, RemapDirection.TO_SOURCE), 80)

        # Test with range 0-50
        # Formula: (1-1)*50/99+0 = 0
        check.equal(remap_value(1, 0, 50, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(100, 0, 50, RemapDirection.TO_SOURCE), 50)

        # Test with range 30-100
        check.equal(remap_value(1, 30, 100, RemapDirection.TO_SOURCE), 30)
        check.equal(remap_value(100, 30, 100, RemapDirection.TO_SOURCE), 100)

    def test_to_source_linear_mapping_precision(self):
        """Test precise linear mapping calculations."""
        # Test precise calculations with range 10-90
        # Formula: (value-1)*(max-min)/99+min
        # (25-1)*(90-10)/99+10 = 29.39 -> 29
        check.equal(remap_value(25, 10, 90, RemapDirection.TO_SOURCE), 29)
        # (50-1)*(90-10)/99+10 = 49.60 -> 50
        check.equal(remap_value(50, 10, 90, RemapDirection.TO_SOURCE), 50)
        # (75-1)*(90-10)/99+10 = 69.80 -> 70
        check.equal(remap_value(75, 10, 90, RemapDirection.TO_SOURCE), 70)

    def test_to_source_boundary_values(self):
        """Test boundary values for TO_SOURCE direction."""
        check.equal(remap_value(1, 10, 90, RemapDirection.TO_SOURCE), 10)
        check.equal(remap_value(2, 10, 90, RemapDirection.TO_SOURCE), 11)
        check.equal(remap_value(99, 10, 90, RemapDirection.TO_SOURCE), 89)
        check.equal(remap_value(100, 10, 90, RemapDirection.TO_SOURCE), 90)

    def test_to_source_rounding_behavior(self):
        """Test that results are properly rounded to integers."""
        result = remap_value(33, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(isinstance(result, int))
        result = remap_value(67, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(isinstance(result, int))

    def test_to_source_clamping_behavior(self):
        """Test that results are clamped to valid ranges."""
        result = remap_value(150, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(result <= 90)
        result = remap_value(-10, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(result >= 0)

    def test_to_source_min_equals_max(self):
        """Test edge case where min_value equals max_value."""
        check.equal(remap_value(50, 50, 50, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(1, 25, 25, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(100, 75, 75, RemapDirection.TO_SOURCE), 0)

# Additional tests will be migrated as we continue...


class TestRemapValueFromSource:
    """Test RemapDirection.FROM_SOURCE: source values to user scale (0-100)."""

    def test_from_source_zero_always_maps_to_zero(self):
        """Test that source value 0 always maps to 0 regardless of min/max."""
        check.equal(remap_value(0, 10, 90, RemapDirection.FROM_SOURCE), 0)
        check.equal(remap_value(0, 25, 75, RemapDirection.FROM_SOURCE), 0)
        check.equal(remap_value(0, 0, 100, RemapDirection.FROM_SOURCE), 0)
        check.equal(remap_value(0, 50, 50, RemapDirection.FROM_SOURCE), 0)

    def test_from_source_linear_mapping_basic(self):
        """Test basic linear mapping from min_value-max_value to 1-100."""
        check.equal(remap_value(10, 10, 90, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(90, 10, 90, RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(50, 10, 90, RemapDirection.FROM_SOURCE), 50)

    def test_from_source_linear_mapping_different_ranges(self):
        """Test linear mapping with various min/max ranges."""
        check.equal(remap_value(20, 20, 80, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(80, 20, 80, RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(1, 0, 50, RemapDirection.FROM_SOURCE), 3)
        check.equal(remap_value(50, 0, 50, RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(30, 30, 100, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(100, 30, 100, RemapDirection.FROM_SOURCE), 100)

    def test_from_source_below_minimum_handling(self):
        """Test that source values below min_value map to 1 (not 0)."""
        check.equal(remap_value(5, 10, 90, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(15, 20, 80, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(-10, 10, 90, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(0.5, 5, 95, RemapDirection.FROM_SOURCE), 1)

    def test_from_source_boundary_values(self):
        """Test boundary values for FROM_SOURCE direction."""
        check.equal(remap_value(10, 10, 90, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(90, 10, 90, RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(11, 10, 90, RemapDirection.FROM_SOURCE), 2)
        check.equal(remap_value(89, 10, 90, RemapDirection.FROM_SOURCE), 99)

    def test_from_source_precision_mapping(self):
        """Test precise linear mapping calculations."""
        check.equal(remap_value(50, 10, 90, RemapDirection.FROM_SOURCE), 50)
        check.equal(remap_value(50, 25, 75, RemapDirection.FROM_SOURCE), 50)

    def test_from_source_rounding_behavior(self):
        """Test that results are properly rounded to integers."""
        result = remap_value(33, 10, 90, RemapDirection.FROM_SOURCE)
        check.is_true(isinstance(result, int))
        result = remap_value(67, 10, 90, RemapDirection.FROM_SOURCE)
        check.is_true(isinstance(result, int))

    def test_from_source_clamping_behavior(self):
        """Test that results are clamped to valid ranges (1-100)."""
        result = remap_value(200, 10, 90, RemapDirection.FROM_SOURCE)
        check.is_true(1 <= result <= 100)
        result = remap_value(-50, 10, 90, RemapDirection.FROM_SOURCE)
        check.equal(result, 1)

    def test_from_source_min_equals_max(self):
        """Test edge case where min_value equals max_value."""
        check.equal(remap_value(50, 50, 50, RemapDirection.FROM_SOURCE), 50)
        check.equal(remap_value(25, 25, 25, RemapDirection.FROM_SOURCE), 25)
        check.equal(remap_value(75, 75, 75, RemapDirection.FROM_SOURCE), 75)


class TestRemapValueEdgeCases:
    """Test edge cases and special scenarios for remap_value function."""

    def test_none_input_handling(self):
        """Test that None input returns None."""
        check.is_none(remap_value(None, 10, 90, RemapDirection.TO_SOURCE))
        check.is_none(remap_value(None, 10, 90, RemapDirection.FROM_SOURCE))
        check.is_none(remap_value(None, 0, 100, RemapDirection.TO_SOURCE))
        check.is_none(remap_value(None, 0, 100, RemapDirection.FROM_SOURCE))

    def test_full_range_mapping(self):
        """Test mapping with full 0-100 range."""
        check.equal(remap_value(0, 0, 100, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(1, 0, 100, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(50, 0, 100, RemapDirection.TO_SOURCE), 49)
        check.equal(remap_value(100, 0, 100, RemapDirection.TO_SOURCE), 100)
        check.equal(remap_value(0, 0, 100, RemapDirection.FROM_SOURCE), 0)
        check.equal(remap_value(1, 0, 100, RemapDirection.FROM_SOURCE), 2)
        check.equal(remap_value(50, 0, 100, RemapDirection.FROM_SOURCE), 50)
        check.equal(remap_value(100, 0, 100, RemapDirection.FROM_SOURCE), 100)

    def test_narrow_range_mapping(self):
        """Test mapping with very narrow ranges."""
        check.equal(remap_value(1, 49, 51, RemapDirection.TO_SOURCE), 49)
        check.equal(remap_value(100, 49, 51, RemapDirection.TO_SOURCE), 51)
        check.equal(remap_value(50, 49, 51, RemapDirection.TO_SOURCE), 50)
        check.equal(remap_value(49, 49, 51, RemapDirection.FROM_SOURCE), 1)
        check.equal(remap_value(51, 49, 51, RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(50, 49, 51, RemapDirection.FROM_SOURCE), 50)

    def test_inverted_range_handling(self):
        """Test behavior when min_value > max_value (edge case)."""
        result = remap_value(50, 90, 10, RemapDirection.TO_SOURCE)
        check.is_true(isinstance(result, int))
        result = remap_value(50, 90, 10, RemapDirection.FROM_SOURCE)
        check.is_true(isinstance(result, int))

    def test_single_point_ranges(self):
        """Test various single-point ranges (min == max)."""
        test_values = [0, 25, 50, 75, 100]
        for point in test_values:
            check.equal(remap_value(50, point, point,
                        RemapDirection.TO_SOURCE), 0)
            check.equal(remap_value(50, point, point,
                        RemapDirection.FROM_SOURCE), point)

    def test_extreme_input_values(self):
        """Test with extreme input values."""
        result = remap_value(1000, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(isinstance(result, int))
        check.is_true(result <= 90)
        result = remap_value(1000, 10, 90, RemapDirection.FROM_SOURCE)
        check.is_true(isinstance(result, int))
        check.is_true(1 <= result <= 100)
        result = remap_value(-100, 10, 90, RemapDirection.TO_SOURCE)
        check.is_true(isinstance(result, int))
        result = remap_value(-100, 10, 90, RemapDirection.FROM_SOURCE)
        check.equal(result, 1)


class TestRemapValueSymmetry:
    """Test that TO_SOURCE and FROM_SOURCE are properly inverse operations."""

    def test_round_trip_symmetry_typical_values(self):
        """Test round-trip symmetry for typical values."""
        min_val, max_val = 10, 90
        for user_val in [1, 25, 50, 75, 100]:
            source_val = remap_value(
                user_val, min_val, max_val, RemapDirection.TO_SOURCE)
            back_to_user = remap_value(
                source_val, min_val, max_val, RemapDirection.FROM_SOURCE)
            check.is_true(abs(back_to_user - user_val) <= 2,
                          f"Round trip failed: {user_val} -> {source_val} -> {back_to_user}")

    def test_round_trip_symmetry_various_ranges(self):
        """Test round-trip symmetry for various ranges."""
        test_ranges = [(0, 100), (20, 80), (25, 75), (5, 95)]
        for min_val, max_val in test_ranges:
            for user_val in [1, 33, 67, 100]:
                source_val = remap_value(
                    user_val, min_val, max_val, RemapDirection.TO_SOURCE)
                back_to_user = remap_value(
                    source_val, min_val, max_val, RemapDirection.FROM_SOURCE)
                check.is_true(abs(back_to_user - user_val) <= 2,
                              f"Range {min_val}-{max_val}: {user_val} -> {source_val} -> {back_to_user}")

    def test_zero_symmetry(self):
        """Test that 0 always maps to 0 and back."""
        test_ranges = [(10, 90), (0, 100), (25, 75), (50, 50)]
        for min_val, max_val in test_ranges:
            source_val = remap_value(
                0, min_val, max_val, RemapDirection.TO_SOURCE)
            check.equal(source_val, 0)
            back_to_user = remap_value(
                source_val, min_val, max_val, RemapDirection.FROM_SOURCE)
            check.equal(back_to_user, 0)


class TestRemapValueIntegration:
    """Test remapping integration with typical use cases."""

    def test_typical_blind_configuration(self):
        """Test remapping with typical blind configuration (10-90 range)."""
        min_pos, max_pos = 10, 90
        check.equal(remap_value(100, min_pos, max_pos,
                    RemapDirection.TO_SOURCE), 90)
        check.equal(remap_value(90, min_pos, max_pos,
                    RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(0, min_pos, max_pos,
                    RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(0, min_pos, max_pos,
                    RemapDirection.FROM_SOURCE), 0)

    def test_typical_tilt_configuration(self):
        """Test remapping with typical tilt configuration (5-95 range)."""
        min_tilt, max_tilt = 5, 95
        check.equal(remap_value(100, min_tilt, max_tilt,
                    RemapDirection.TO_SOURCE), 95)
        check.equal(remap_value(95, min_tilt, max_tilt,
                    RemapDirection.FROM_SOURCE), 100)
        check.equal(remap_value(1, min_tilt, max_tilt,
                    RemapDirection.TO_SOURCE), 5)
        check.equal(remap_value(5, min_tilt, max_tilt,
                    RemapDirection.FROM_SOURCE), 1)

    def test_partial_range_positions(self):
        """Test various partial range positions."""
        min_pos, max_pos = 20, 80
        quarter = remap_value(25, min_pos, max_pos, RemapDirection.TO_SOURCE)
        check.is_true(30 <= quarter <= 35)
        half = remap_value(50, min_pos, max_pos, RemapDirection.TO_SOURCE)
        check.is_true(48 <= half <= 52)
        three_quarter = remap_value(
            75, min_pos, max_pos, RemapDirection.TO_SOURCE)
        check.is_true(65 <= three_quarter <= 70)

    def test_default_values_from_constants(self):
        """Test remapping with default values from constants."""
        from custom_components.mappedcover.const import (
            DEFAULT_MIN_POSITION, DEFAULT_MAX_POSITION,
            DEFAULT_MIN_TILT_POSITION, DEFAULT_MAX_TILT_POSITION
        )
        check.equal(remap_value(0, DEFAULT_MIN_POSITION,
                    DEFAULT_MAX_POSITION, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(100, DEFAULT_MIN_POSITION,
                    DEFAULT_MAX_POSITION, RemapDirection.TO_SOURCE), 100)
        check.equal(remap_value(0, DEFAULT_MIN_TILT_POSITION,
                    DEFAULT_MAX_TILT_POSITION, RemapDirection.TO_SOURCE), 0)
        check.equal(remap_value(100, DEFAULT_MIN_TILT_POSITION,
                    DEFAULT_MAX_TILT_POSITION, RemapDirection.TO_SOURCE), 100)
