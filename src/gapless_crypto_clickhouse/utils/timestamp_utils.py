"""Simple timestamp utility functions for Binance data format conversions.

This module provides lightweight utility functions for timestamp format detection
and normalization, complementing the comprehensive TimestampFormatAnalyzer class.

Binance Vision API Format Transition (2025-01-01):
    - Spot data: Transitioned to microseconds (16 digits)
    - Futures data: Remains milliseconds (13 digits)
    - Target: Universal microsecond precision (DateTime64(6))

Functions:
    detect_timestamp_precision: Quick format detection (milliseconds vs microseconds)
    normalize_timestamp_to_microseconds: Convert timestamps to microsecond precision

SLO Targets:
    Correctness: 100% - accurate conversion with no data loss
    Maintainability: Simple functions for inline use throughout codebase
"""


def detect_timestamp_precision(timestamp: int) -> str:
    """Detect timestamp precision from magnitude.

    Args:
        timestamp: Raw timestamp from Binance CSV (integer)

    Returns:
        str: "microseconds" (16+ digits) or "milliseconds" (10-15 digits)

    Raises:
        ValueError: If timestamp has unexpected digit count (<10 digits)

    Examples:
        >>> detect_timestamp_precision(1704067200000000)  # 16 digits
        'microseconds'

        >>> detect_timestamp_precision(1704067200000)  # 13 digits
        'milliseconds'

        >>> detect_timestamp_precision(123)  # Too short
        Traceback (most recent call last):
            ...
        ValueError: Invalid timestamp 123: expected 10+ digits, got 3

    SLO: Correctness - accurate detection for all valid Binance timestamps
    """
    digit_count = len(str(timestamp))

    if digit_count >= 16:  # Microseconds (2025+ spot data)
        return "microseconds"
    elif digit_count >= 10:  # Milliseconds (legacy spot, all futures)
        return "milliseconds"
    else:
        raise ValueError(
            f"Invalid timestamp {timestamp}: expected 10+ digits, got {digit_count}. "
            f"Valid formats: milliseconds (10-15 digits) or microseconds (16+ digits)."
        )


def normalize_timestamp_to_microseconds(timestamp: int, source_precision: str) -> int:
    """Normalize timestamp to microsecond precision.

    Converts millisecond timestamps to microseconds for uniform DateTime64(6) storage.
    Microsecond timestamps are passed through unchanged.

    Args:
        timestamp: Raw timestamp from Binance CSV
        source_precision: Detected precision ("milliseconds" or "microseconds")

    Returns:
        int: Timestamp in microseconds (DateTime64(6) compatible)

    Raises:
        ValueError: If source_precision is not "milliseconds" or "microseconds"

    Examples:
        >>> # Milliseconds → Microseconds (multiply by 1000)
        >>> normalize_timestamp_to_microseconds(1704067200000, "milliseconds")
        1704067200000000

        >>> # Microseconds → Microseconds (no change)
        >>> normalize_timestamp_to_microseconds(1704067200000000, "microseconds")
        1704067200000000

        >>> # Invalid precision
        >>> normalize_timestamp_to_microseconds(1704067200, "seconds")
        Traceback (most recent call last):
            ...
        ValueError: Unknown precision: seconds. Must be 'milliseconds' or 'microseconds'.

    SLO: Correctness - lossless conversion with validation
    """
    if source_precision == "microseconds":
        return timestamp  # Already correct precision
    elif source_precision == "milliseconds":
        return timestamp * 1000  # Convert ms → μs
    else:
        raise ValueError(
            f"Unknown precision: {source_precision}. "
            f"Must be 'milliseconds' or 'microseconds'."
        )


def normalize_timestamp_auto(timestamp: int) -> int:
    """Auto-detect and normalize timestamp to microseconds.

    Convenience function combining detection and normalization in one call.
    Useful for inline conversions without explicit precision tracking.

    Args:
        timestamp: Raw timestamp from Binance CSV

    Returns:
        int: Timestamp normalized to microseconds

    Raises:
        ValueError: If timestamp is invalid (<10 digits)

    Examples:
        >>> # Auto-detect milliseconds and convert
        >>> normalize_timestamp_auto(1704067200000)
        1704067200000000

        >>> # Auto-detect microseconds and pass through
        >>> normalize_timestamp_auto(1704067200000000)
        1704067200000000

    SLO: Correctness - accurate auto-detection and conversion
    """
    precision = detect_timestamp_precision(timestamp)
    return normalize_timestamp_to_microseconds(timestamp, precision)
