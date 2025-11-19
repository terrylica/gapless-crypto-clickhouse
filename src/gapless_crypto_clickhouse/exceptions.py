"""Structured exception hierarchy for gapless-crypto-data.

Provides machine-parseable error details via .details dict attribute,
enabling AI agents and downstream packages to programmatically handle errors.

Exception Hierarchy:
    GaplessCryptoDataError (base)
    ├── DataCollectionError - Binance data collection failures
    ├── ValidationError - Input validation failures
    ├── NetworkError - Network operation failures
    └── GapFillingError - Gap detection/filling failures

Version: 3.2.0
"""

from typing import Any


class GaplessCryptoDataError(Exception):
    """Base exception for all gapless-crypto-data errors.

    Provides structured error details via .details dict for machine-parseable
    error handling by AI agents and downstream packages.

    Attributes:
        message: Human-readable error message
        details: Machine-parseable error context (dict)

    Examples:
        >>> try:
        ...     raise DataCollectionError(
        ...         "Failed to collect BTCUSDT data",
        ...         details={"symbol": "BTCUSDT", "timeframe": "1h", "status_code": 404}
        ...     )
        ... except GaplessCryptoDataError as e:
        ...     print(e.details)
        {'symbol': 'BTCUSDT', 'timeframe': '1h', 'status_code': 404}
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize exception with message and optional structured details.

        Args:
            message: Human-readable error description
            details: Machine-parseable context (symbol, timeframe, status_code, etc.)
        """
        super().__init__(message)
        self.details = details or {}


class DataCollectionError(GaplessCryptoDataError):
    """Raised when Binance data collection fails.

    Common scenarios:
    - Missing monthly ZIP files on Binance public repository
    - ZIP extraction failures
    - CSV parsing errors
    - Timeframe not available for symbol/date range

    Example:
        >>> raise DataCollectionError(
        ...     "Monthly ZIP file not found",
        ...     details={
        ...         "symbol": "BTCUSDT",
        ...         "timeframe": "1s",
        ...         "year_month": "2020-01",
        ...         "url": "https://data.binance.vision/...",
        ...         "status_code": 404
        ...     }
        ... )
    """

    pass


class ValidationError(GaplessCryptoDataError):
    """Raised when input validation fails.

    Common scenarios:
    - Invalid symbol format
    - Invalid timeframe (not in supported set)
    - Invalid date range
    - Malformed CSV data
    - OHLCV constraint violations (high < low, etc.)

    Example:
        >>> raise ValidationError(
        ...     "Invalid timeframe",
        ...     details={
        ...         "provided_timeframe": "2h30m",
        ...         "supported_timeframes": ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
        ...     }
        ... )
    """

    pass


class NetworkError(GaplessCryptoDataError):
    """Raised when network operations fail.

    Common scenarios:
    - HTTP request timeouts
    - Connection failures
    - Rate limiting (429 status)
    - Server errors (5xx status)

    Example:
        >>> raise NetworkError(
        ...     "Binance API rate limit exceeded",
        ...     details={
        ...         "endpoint": "https://api.binance.com/api/v3/klines",
        ...         "status_code": 429,
        ...         "retry_after": 60,
        ...         "request_count": 1200
        ...     }
        ... )
    """

    pass


class GapFillingError(GaplessCryptoDataError):
    """Raised when gap detection or filling fails.

    Common scenarios:
    - Gap detection algorithm failures
    - API data unavailable for gap period
    - Merge conflicts during gap filling
    - Atomic operation failures

    Example:
        >>> raise GapFillingError(
        ...     "Cannot fill gap: API data unavailable",
        ...     details={
        ...         "gap_start": "2024-01-01T00:00:00",
        ...         "gap_end": "2024-01-01T06:00:00",
        ...         "gap_size_hours": 6,
        ...         "api_response": "No data returned",
        ...         "csv_file": "/path/to/BTCUSDT_1h.csv"
        ...     }
        ... )
    """

    pass
