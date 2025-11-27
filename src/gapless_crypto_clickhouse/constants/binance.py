"""Binance API and CDN constants (ADR-0046).

Single source of truth for Binance data source URLs, API limits,
and instrument type definitions.

Data Sources:
    - CDN (data.binance.vision): Historical data repository via CloudFront
    - REST API (api.binance.com): Real-time and gap-filling queries

Usage:
    from gapless_crypto_clickhouse.constants.binance import (
        InstrumentType,
        BINANCE_CDN_SPOT,
        BINANCE_API_SPOT,
        API_CHUNK_SIZE,
    )
"""

from typing import Dict, Final, FrozenSet, Literal

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

InstrumentType = Literal["spot", "futures-um"]
"""Type alias for valid instrument types (spot or USDT-margined futures)."""

# =============================================================================
# INSTRUMENT TYPE CONSTANTS (ADR-0050)
# =============================================================================

INSTRUMENT_SPOT: Final[str] = "spot"
"""Spot market instrument type."""

INSTRUMENT_FUTURES_UM: Final[str] = "futures-um"
"""USDT-margined perpetual futures instrument type."""

INSTRUMENT_FUTURES_CM: Final[str] = "futures-cm"
"""COIN-margined perpetual futures instrument type (reserved for future use)."""

VALID_INSTRUMENT_TYPES: Final[FrozenSet[str]] = frozenset({
    INSTRUMENT_SPOT,
    INSTRUMENT_FUTURES_UM,
})
"""Valid instrument types for API validation (O(1) membership testing)."""

IMPLEMENTED_INSTRUMENT_TYPES: Final[FrozenSet[str]] = frozenset({
    INSTRUMENT_SPOT,
    INSTRUMENT_FUTURES_UM,
})
"""Currently implemented instrument types with working pipelines."""

# =============================================================================
# CDN BASE URLS (data.binance.vision)
# =============================================================================

BINANCE_CDN_BASE: Final[str] = "https://data.binance.vision"
"""Binance Public Data Repository base URL (CloudFront CDN)."""

BINANCE_CDN_SPOT: Final[str] = f"{BINANCE_CDN_BASE}/data/spot"
"""Spot market historical data CDN path."""

BINANCE_CDN_FUTURES_UM: Final[str] = f"{BINANCE_CDN_BASE}/data/futures/um"
"""USDT-margined futures historical data CDN path."""

# =============================================================================
# REST API URLS
# =============================================================================

BINANCE_API_SPOT: Final[str] = "https://api.binance.com/api/v3/klines"
"""Spot market klines REST API endpoint."""

BINANCE_API_FUTURES: Final[str] = "https://fapi.binance.com/fapi/v1/klines"
"""USDT-margined futures klines REST API endpoint."""

# =============================================================================
# API LIMITS
# =============================================================================

API_CHUNK_SIZE: Final[int] = 1000
"""Maximum records per Binance API request (klines endpoint limit)."""

API_MAX_CHUNKS: Final[int] = 100
"""Safety limit for chunked requests to prevent runaway loops."""

# =============================================================================
# CSV FORMAT CONSTANTS
# =============================================================================

CSV_COLUMNS_SPOT_OUTPUT: Final[int] = 11
"""Spot market CSV columns after processing (OHLCV + microstructure metrics)."""

CSV_COLUMNS_BINANCE_RAW: Final[int] = 12
"""Raw Binance CSV columns (includes header for futures, ignore column for spot)."""

CSV_COLUMNS_MINIMUM_OHLCV: Final[int] = 6
"""Minimum required columns for OHLCV validation (timestamp + OHLC + volume)."""

DATE_STRING_LENGTH: Final[int] = 10
"""Expected length of date strings in YYYY-MM-DD format."""

# =============================================================================
# TIMESTAMP CONSTANTS
# =============================================================================

TIMESTAMP_MILLISECONDS_MIN: Final[int] = 1000000000000
"""Unix epoch milliseconds minimum boundary (2001-09-09, 13-digit timestamp)."""

TIMESTAMP_MILLISECONDS_MAX: Final[int] = 9999999999999
"""Unix epoch milliseconds maximum boundary (2286-11-20, 13-digit timestamp)."""

TIMESTAMP_MICROSECONDS_MIN: Final[int] = 1000000000000000
"""Unix epoch microseconds minimum boundary (2001-09-09, 16-digit timestamp)."""

TIMESTAMP_MICROSECONDS_MAX: Final[int] = 9999999999999999
"""Unix epoch microseconds maximum boundary (2286-11-20, 16-digit timestamp)."""

TIMESTAMP_MICROSECONDS_DIGIT_COUNT: Final[int] = 16
"""Number of digits in microsecond-resolution Unix timestamps."""

MICROSECONDS_PER_MILLISECOND: Final[int] = 1000000
"""Conversion factor from microseconds to milliseconds (10^6)."""

MILLISECONDS_PER_SECOND: Final[int] = 1000
"""Conversion factor from milliseconds to seconds (10^3)."""

# =============================================================================
# CSV COLUMN INDICES (for positional access)
# =============================================================================

CSV_INDEX_TIMESTAMP: Final[int] = 0
"""Index of open_time / timestamp column."""

CSV_INDEX_OPEN: Final[int] = 1
"""Index of open price column."""

CSV_INDEX_HIGH: Final[int] = 2
"""Index of high price column."""

CSV_INDEX_LOW: Final[int] = 3
"""Index of low price column."""

CSV_INDEX_CLOSE: Final[int] = 4
"""Index of close price column."""

CSV_INDEX_VOLUME: Final[int] = 5
"""Index of base asset volume column."""

CSV_INDEX_CLOSE_TIME: Final[int] = 6
"""Index of close_time column."""

CSV_INDEX_QUOTE_VOLUME: Final[int] = 7
"""Index of quote asset volume column."""

CSV_INDEX_TRADE_COUNT: Final[int] = 8
"""Index of number_of_trades column."""

CSV_INDEX_TAKER_BUY_BASE: Final[int] = 9
"""Index of taker_buy_base_asset_volume column."""

CSV_INDEX_TAKER_BUY_QUOTE: Final[int] = 10
"""Index of taker_buy_quote_asset_volume column."""

# =============================================================================
# DERIVED MAPPINGS
# =============================================================================

CDN_URL_BY_INSTRUMENT: Final[Dict[str, str]] = {
    "spot": BINANCE_CDN_SPOT,
    "futures-um": BINANCE_CDN_FUTURES_UM,
}
"""CDN base URL lookup by instrument type."""

API_URL_BY_INSTRUMENT: Final[Dict[str, str]] = {
    "spot": BINANCE_API_SPOT,
    "futures-um": BINANCE_API_FUTURES,
}
"""REST API URL lookup by instrument type."""

# =============================================================================
# SELF-VALIDATING ASSERTIONS
# =============================================================================

# Verify URL mappings cover all implemented instrument types
assert set(CDN_URL_BY_INSTRUMENT.keys()) == VALID_INSTRUMENT_TYPES, (
    f"CDN_URL_BY_INSTRUMENT missing instruments: "
    f"{VALID_INSTRUMENT_TYPES - set(CDN_URL_BY_INSTRUMENT.keys())}"
)
assert set(API_URL_BY_INSTRUMENT.keys()) == VALID_INSTRUMENT_TYPES, (
    f"API_URL_BY_INSTRUMENT missing instruments: "
    f"{VALID_INSTRUMENT_TYPES - set(API_URL_BY_INSTRUMENT.keys())}"
)

# Verify API limits are sane
assert API_CHUNK_SIZE > 0, f"API_CHUNK_SIZE must be positive: {API_CHUNK_SIZE}"
assert API_CHUNK_SIZE <= 1000, f"API_CHUNK_SIZE exceeds Binance limit: {API_CHUNK_SIZE}"
assert API_MAX_CHUNKS > 0, f"API_MAX_CHUNKS must be positive: {API_MAX_CHUNKS}"

# Verify URLs are properly formatted
assert BINANCE_CDN_BASE.startswith("https://"), "CDN URL must use HTTPS"
assert BINANCE_API_SPOT.startswith("https://"), "API URL must use HTTPS"
assert BINANCE_API_FUTURES.startswith("https://"), "Futures API URL must use HTTPS"

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Type definitions
    "InstrumentType",
    # Instrument type constants (ADR-0050)
    "INSTRUMENT_SPOT",
    "INSTRUMENT_FUTURES_UM",
    "INSTRUMENT_FUTURES_CM",
    "VALID_INSTRUMENT_TYPES",
    "IMPLEMENTED_INSTRUMENT_TYPES",
    # CDN URLs
    "BINANCE_CDN_BASE",
    "BINANCE_CDN_SPOT",
    "BINANCE_CDN_FUTURES_UM",
    # REST API URLs
    "BINANCE_API_SPOT",
    "BINANCE_API_FUTURES",
    # API limits
    "API_CHUNK_SIZE",
    "API_MAX_CHUNKS",
    # CSV format constants
    "CSV_COLUMNS_SPOT_OUTPUT",
    "CSV_COLUMNS_BINANCE_RAW",
    "CSV_COLUMNS_MINIMUM_OHLCV",
    "DATE_STRING_LENGTH",
    # Timestamp constants
    "TIMESTAMP_MILLISECONDS_MIN",
    "TIMESTAMP_MILLISECONDS_MAX",
    "TIMESTAMP_MICROSECONDS_MIN",
    "TIMESTAMP_MICROSECONDS_MAX",
    "TIMESTAMP_MICROSECONDS_DIGIT_COUNT",
    "MICROSECONDS_PER_MILLISECOND",
    "MILLISECONDS_PER_SECOND",
    # CSV column indices
    "CSV_INDEX_TIMESTAMP",
    "CSV_INDEX_OPEN",
    "CSV_INDEX_HIGH",
    "CSV_INDEX_LOW",
    "CSV_INDEX_CLOSE",
    "CSV_INDEX_VOLUME",
    "CSV_INDEX_CLOSE_TIME",
    "CSV_INDEX_QUOTE_VOLUME",
    "CSV_INDEX_TRADE_COUNT",
    "CSV_INDEX_TAKER_BUY_BASE",
    "CSV_INDEX_TAKER_BUY_QUOTE",
    # Derived mappings
    "CDN_URL_BY_INSTRUMENT",
    "API_URL_BY_INSTRUMENT",
]
