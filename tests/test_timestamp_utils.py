"""Tests for timestamp utility functions.

Tests timestamp format detection and normalization for Binance's 2025-01-01
format transition (spot→microseconds, futures→milliseconds).
"""

import pytest

from gapless_crypto_clickhouse.utils.timestamp_utils import (
    detect_timestamp_precision,
    normalize_timestamp_to_microseconds,
    normalize_timestamp_auto,
)


class TestDetectTimestampPrecision:
    """Test timestamp precision detection."""

    def test_detect_microseconds_16_digits(self):
        """Test detection of microsecond timestamps (16 digits)."""
        # 2024-01-01 00:00:00.000000
        timestamp = 1704067200000000
        assert detect_timestamp_precision(timestamp) == "microseconds"

    def test_detect_microseconds_17_digits(self):
        """Test detection of microsecond timestamps (17 digits)."""
        # Future timestamp with 17 digits
        timestamp = 17040672000000000
        assert detect_timestamp_precision(timestamp) == "microseconds"

    def test_detect_milliseconds_13_digits(self):
        """Test detection of millisecond timestamps (13 digits)."""
        # 2024-01-01 00:00:00.000
        timestamp = 1704067200000
        assert detect_timestamp_precision(timestamp) == "milliseconds"

    def test_detect_milliseconds_10_digits(self):
        """Test detection of millisecond timestamps (10 digits minimum)."""
        # 2001-09-09 01:46:40 (10 digits)
        timestamp = 1000000000
        assert detect_timestamp_precision(timestamp) == "milliseconds"

    def test_detect_milliseconds_15_digits(self):
        """Test detection of millisecond timestamps (15 digits maximum)."""
        # Edge case: 15 digits still counts as milliseconds
        timestamp = 170406720000000
        assert detect_timestamp_precision(timestamp) == "milliseconds"

    def test_invalid_timestamp_too_short(self):
        """Test error handling for timestamps with <10 digits."""
        timestamp = 123456789  # 9 digits
        with pytest.raises(ValueError, match="Invalid timestamp.*expected 10\\+ digits"):
            detect_timestamp_precision(timestamp)

    def test_invalid_timestamp_very_short(self):
        """Test error handling for very short timestamps."""
        timestamp = 123  # 3 digits
        with pytest.raises(ValueError, match="Invalid timestamp 123.*got 3"):
            detect_timestamp_precision(timestamp)


class TestNormalizeTimestampToMicroseconds:
    """Test timestamp normalization to microseconds."""

    def test_normalize_milliseconds_to_microseconds(self):
        """Test conversion from milliseconds to microseconds."""
        timestamp_ms = 1704067200000  # 13 digits
        expected_us = 1704067200000000  # 16 digits
        result = normalize_timestamp_to_microseconds(timestamp_ms, "milliseconds")
        assert result == expected_us
        assert len(str(result)) == 16

    def test_normalize_microseconds_passthrough(self):
        """Test microsecond timestamps pass through unchanged."""
        timestamp_us = 1704067200000000  # 16 digits
        result = normalize_timestamp_to_microseconds(timestamp_us, "microseconds")
        assert result == timestamp_us
        assert len(str(result)) == 16

    def test_normalize_zero_milliseconds(self):
        """Test edge case: zero timestamp in milliseconds."""
        timestamp_ms = 0
        expected_us = 0
        result = normalize_timestamp_to_microseconds(timestamp_ms, "milliseconds")
        assert result == expected_us

    def test_normalize_zero_microseconds(self):
        """Test edge case: zero timestamp in microseconds."""
        timestamp_us = 0
        result = normalize_timestamp_to_microseconds(timestamp_us, "microseconds")
        assert result == timestamp_us

    def test_normalize_large_milliseconds(self):
        """Test conversion of large millisecond timestamp."""
        # Year 2030 in milliseconds
        timestamp_ms = 1893456000000
        expected_us = 1893456000000000
        result = normalize_timestamp_to_microseconds(timestamp_ms, "milliseconds")
        assert result == expected_us

    def test_normalize_invalid_precision(self):
        """Test error handling for invalid precision parameter."""
        timestamp = 1704067200000
        with pytest.raises(ValueError, match="Unknown precision: seconds"):
            normalize_timestamp_to_microseconds(timestamp, "seconds")

    def test_normalize_invalid_precision_empty(self):
        """Test error handling for empty precision parameter."""
        timestamp = 1704067200000
        with pytest.raises(ValueError, match="Unknown precision.*Must be"):
            normalize_timestamp_to_microseconds(timestamp, "")

    def test_normalize_invalid_precision_typo(self):
        """Test error handling for typo in precision parameter."""
        timestamp = 1704067200000
        with pytest.raises(ValueError, match="Unknown precision: miliseconds"):
            normalize_timestamp_to_microseconds(timestamp, "miliseconds")  # Missing 'l'


class TestNormalizeTimestampAuto:
    """Test automatic timestamp detection and normalization."""

    def test_auto_normalize_milliseconds(self):
        """Test auto-detection and conversion of milliseconds."""
        timestamp_ms = 1704067200000  # 13 digits
        expected_us = 1704067200000000  # 16 digits
        result = normalize_timestamp_auto(timestamp_ms)
        assert result == expected_us

    def test_auto_normalize_microseconds(self):
        """Test auto-detection and passthrough of microseconds."""
        timestamp_us = 1704067200000000  # 16 digits
        result = normalize_timestamp_auto(timestamp_us)
        assert result == timestamp_us

    def test_auto_normalize_invalid_timestamp(self):
        """Test auto-detection error handling for invalid timestamps."""
        timestamp = 123  # Too short
        with pytest.raises(ValueError, match="Invalid timestamp"):
            normalize_timestamp_auto(timestamp)

    def test_auto_normalize_realistic_spot_data_post_2025(self):
        """Test realistic spot data scenario (post-2025-01-01)."""
        # Spot data after 2025-01-01 comes in microseconds
        timestamp_us = 1735689600000000  # 2025-01-01 in microseconds
        result = normalize_timestamp_auto(timestamp_us)
        assert result == timestamp_us  # Should pass through unchanged

    def test_auto_normalize_realistic_futures_data(self):
        """Test realistic futures data scenario (always milliseconds)."""
        # Futures data comes in milliseconds, needs conversion
        timestamp_ms = 1735689600000  # 2025-01-01 in milliseconds
        expected_us = 1735689600000000
        result = normalize_timestamp_auto(timestamp_ms)
        assert result == expected_us  # Should be converted to microseconds


class TestTimestampConversionConsistency:
    """Test consistency between detection and normalization."""

    def test_round_trip_milliseconds(self):
        """Test detection and normalization round-trip for milliseconds."""
        timestamp_ms = 1704067200000
        precision = detect_timestamp_precision(timestamp_ms)
        assert precision == "milliseconds"

        result = normalize_timestamp_to_microseconds(timestamp_ms, precision)
        expected = 1704067200000000
        assert result == expected

    def test_round_trip_microseconds(self):
        """Test detection and normalization round-trip for microseconds."""
        timestamp_us = 1704067200000000
        precision = detect_timestamp_precision(timestamp_us)
        assert precision == "microseconds"

        result = normalize_timestamp_to_microseconds(timestamp_us, precision)
        assert result == timestamp_us  # No change

    def test_auto_normalize_matches_manual(self):
        """Test auto-normalize produces same result as manual detection+normalize."""
        timestamp = 1704067200000  # Milliseconds

        # Manual approach
        precision = detect_timestamp_precision(timestamp)
        manual_result = normalize_timestamp_to_microseconds(timestamp, precision)

        # Auto approach
        auto_result = normalize_timestamp_auto(timestamp)

        assert manual_result == auto_result

    def test_multiple_timestamps_batch(self):
        """Test batch processing of mixed precision timestamps."""
        timestamps = [
            1704067200000,      # Milliseconds
            1704067200000000,   # Microseconds
            1735689600000,      # Milliseconds (2025)
            1735689600000000,   # Microseconds (2025)
        ]

        expected_results = [
            1704067200000000,   # Converted
            1704067200000000,   # Passthrough
            1735689600000000,   # Converted
            1735689600000000,   # Passthrough
        ]

        results = [normalize_timestamp_auto(ts) for ts in timestamps]
        assert results == expected_results

        # All results should be in microseconds (16 digits)
        for result in results:
            assert len(str(result)) == 16


class TestBinanceFormatTransition:
    """Test handling of Binance's 2025-01-01 format transition."""

    def test_spot_data_pre_2025(self):
        """Test spot data before 2025-01-01 (milliseconds)."""
        # 2024-12-31 23:59:59 in milliseconds
        timestamp_ms = 1735689599000
        result = normalize_timestamp_auto(timestamp_ms)
        assert result == 1735689599000000

    def test_spot_data_post_2025(self):
        """Test spot data after 2025-01-01 (microseconds)."""
        # 2025-01-01 00:00:00 in microseconds
        timestamp_us = 1735689600000000
        result = normalize_timestamp_auto(timestamp_us)
        assert result == 1735689600000000  # Passthrough

    def test_futures_data_always_milliseconds(self):
        """Test futures data (always milliseconds, even post-2025)."""
        # Futures data in 2025, still milliseconds
        timestamp_ms = 1735689600000
        result = normalize_timestamp_auto(timestamp_ms)
        assert result == 1735689600000000  # Converted

    def test_transition_boundary(self):
        """Test timestamps around 2025-01-01 transition boundary."""
        # Last millisecond of 2024
        ms_2024 = 1735689599999
        result_2024 = normalize_timestamp_auto(ms_2024)
        assert result_2024 == 1735689599999000

        # First microsecond of 2025 (spot data)
        us_2025 = 1735689600000000
        result_2025 = normalize_timestamp_auto(us_2025)
        assert result_2025 == 1735689600000000
