import unittest
from datetime import datetime
from unittest import mock

from basic_example import clamp, format_with_timestamp, safe_divide, StringFormatter


class TestSafeDivide(unittest.TestCase):
    """Tests for safe_divide."""

    def test_safe_divide_positive_numbers(self):
        # Basic division should return correct quotient.
        self.assertEqual(safe_divide(10, 2), 5)

    def test_safe_divide_negative_divisor(self):
        # Division should handle negative divisor correctly.
        self.assertEqual(safe_divide(9, -3), -3)

    def test_safe_divide_zero_divisor_raises(self):
        # Division by zero should raise a ValueError.
        with self.assertRaises(ValueError):
            safe_divide(1, 0)


class TestClamp(unittest.TestCase):
    """Tests for clamp."""

    def test_clamp_within_range(self):
        # Values inside the range should remain unchanged.
        self.assertEqual(clamp(5, 1, 10), 5)

    def test_clamp_below_minimum(self):
        # Values below the minimum should be clamped to minimum.
        self.assertEqual(clamp(-1, 0, 10), 0)

    def test_clamp_above_maximum(self):
        # Values above the maximum should be clamped to maximum.
        self.assertEqual(clamp(11, 0, 10), 10)

    def test_clamp_at_boundaries(self):
        # Boundary values should return the exact boundary.
        self.assertEqual(clamp(0, 0, 10), 0)
        self.assertEqual(clamp(10, 0, 10), 10)

    def test_clamp_invalid_range_raises(self):
        # Invalid range where minimum > maximum should raise a ValueError.
        with self.assertRaises(ValueError):
            clamp(5, 10, 1)


class TestStringFormatter(unittest.TestCase):
    """Tests for StringFormatter."""

    def test_truncate_without_suffix(self):
        # Truncation without suffix should return the truncated text.
        formatter = StringFormatter()
        self.assertEqual(formatter.truncate("hello", 3), "hel")

    def test_truncate_with_suffix(self):
        # Truncation with suffix should append the suffix.
        formatter = StringFormatter(suffix="...")
        self.assertEqual(formatter.truncate("hello", 2), "he...")

    def test_truncate_no_truncation_needed(self):
        # Text shorter than max_length should be unchanged.
        formatter = StringFormatter(suffix="!")
        self.assertEqual(formatter.truncate("hi", 5), "hi")

    def test_truncate_negative_length_raises(self):
        # Negative max_length should raise a ValueError.
        formatter = StringFormatter()
        with self.assertRaises(ValueError):
            formatter.truncate("hello", -1)

    def test_pad_with_default_fill(self):
        # Padding should extend text to the desired width.
        formatter = StringFormatter()
        self.assertEqual(formatter.pad("hi", 4), "hi  ")

    def test_pad_with_custom_fill(self):
        # Padding should use the specified fill character.
        formatter = StringFormatter()
        self.assertEqual(formatter.pad("hi", 5, fill="."), "hi...")

    def test_pad_no_padding_needed(self):
        # Width less than or equal to length should return original text.
        formatter = StringFormatter()
        self.assertEqual(formatter.pad("hello", 5, fill="."), "hello")

    def test_pad_invalid_fill_raises(self):
        # Fill must be a single character or a ValueError is raised.
        formatter = StringFormatter()
        with self.assertRaises(ValueError):
            formatter.pad("hello", 6, fill="**")


class TestFormatWithTimestamp(unittest.TestCase):
    """Tests for format_with_timestamp."""

    def test_format_with_timestamp_uses_now_fn(self):
        # Timestamp should be derived from the injected now_fn.
        fixed_time = datetime(2024, 1, 1, 12, 30, 15)
        now_fn = mock.Mock(return_value=fixed_time)

        result = format_with_timestamp("hello", now_fn=now_fn)

        now_fn.assert_called_once_with()
        self.assertEqual(result, "[2024-01-01 12:30:15] hello")


if __name__ == "__main__":
    unittest.main()
