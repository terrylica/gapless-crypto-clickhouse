"""Centralized constants for gapless-crypto-clickhouse (ADR-0046).

Re-exports all constants from domain modules for convenient access.

Domain Modules:
    - deployment: Modes, env vars, hosts, ports (ADR-0044)
    - network: Timeouts, concurrency, HTTP status codes
    - binance: API URLs, chunk sizes, rate limits

Usage:
    # Import specific constants
    from gapless_crypto_clickhouse.constants import MODE_LOCAL, PORT_LOCAL_HTTP

    # Import type aliases
    from gapless_crypto_clickhouse.constants import DeploymentMode, InstrumentType

    # Namespace import
    from gapless_crypto_clickhouse import constants
    if mode == constants.MODE_LOCAL:
        ...
"""

# =============================================================================
# DEPLOYMENT CONSTANTS (ADR-0044)
# =============================================================================

# =============================================================================
# BINANCE CONSTANTS
# =============================================================================
from .binance import (
    # API limits
    API_CHUNK_SIZE,
    API_MAX_CHUNKS,
    API_URL_BY_INSTRUMENT,
    BINANCE_API_FUTURES,
    # REST API URLs
    BINANCE_API_SPOT,
    # CDN URLs
    BINANCE_CDN_BASE,
    BINANCE_CDN_FUTURES_UM,
    BINANCE_CDN_SPOT,
    # Derived mappings
    CDN_URL_BY_INSTRUMENT,
    # Instrument type constants (ADR-0050)
    IMPLEMENTED_INSTRUMENT_TYPES,
    INSTRUMENT_FUTURES_CM,
    INSTRUMENT_FUTURES_UM,
    INSTRUMENT_SPOT,
    VALID_INSTRUMENT_TYPES,
    # Type definitions
    InstrumentType,
    # CSV format constants
    CSV_COLUMNS_BINANCE_RAW,
    CSV_COLUMNS_MINIMUM_OHLCV,
    CSV_COLUMNS_SPOT_OUTPUT,
    CSV_INDEX_CLOSE,
    CSV_INDEX_CLOSE_TIME,
    CSV_INDEX_HIGH,
    CSV_INDEX_LOW,
    CSV_INDEX_OPEN,
    CSV_INDEX_QUOTE_VOLUME,
    CSV_INDEX_TAKER_BUY_BASE,
    CSV_INDEX_TAKER_BUY_QUOTE,
    CSV_INDEX_TIMESTAMP,
    CSV_INDEX_TRADE_COUNT,
    CSV_INDEX_VOLUME,
    DATE_STRING_LENGTH,
    # Timestamp constants
    MICROSECONDS_PER_MILLISECOND,
    MILLISECONDS_PER_SECOND,
    TIMESTAMP_MICROSECONDS_DIGIT_COUNT,
    TIMESTAMP_MICROSECONDS_MAX,
    TIMESTAMP_MICROSECONDS_MIN,
    TIMESTAMP_MILLISECONDS_MAX,
    TIMESTAMP_MILLISECONDS_MIN,
)
from .deployment import (
    CLICKHOUSE_ENV_VARS,
    DEFAULT_DATABASE,
    # Defaults
    DEFAULT_HOST,
    DEFAULT_USER,
    ENV_CLICKHOUSE_DATABASE,
    ENV_CLICKHOUSE_HOST,
    ENV_CLICKHOUSE_HTTP_PORT,
    ENV_CLICKHOUSE_PASSWORD,
    ENV_CLICKHOUSE_PORT,
    ENV_CLICKHOUSE_SECURE,
    ENV_CLICKHOUSE_USER,
    # Environment variables
    ENV_GCCH_MODE,
    # Local host detection
    LOCAL_HOSTS,
    MODE_AUTO,
    MODE_CLOUD,
    # Deployment modes
    MODE_LOCAL,
    PORT_CLOUD_HTTP,
    PORT_CLOUD_NATIVE,
    # Ports
    PORT_LOCAL_HTTP,
    PORT_LOCAL_NATIVE,
    PORT_MAX,
    PORT_MIN,
    VALID_MODES,
    # Type definitions
    DeploymentMode,
)

# =============================================================================
# NETWORK CONSTANTS
# =============================================================================
from .network import (
    CONNECTION_POOL_HEADROOM,
    CONNECTION_POOL_SIZE,
    DEFAULT_RETRY_AFTER,
    HTTP_IP_BANNED,
    HTTP_NOT_MODIFIED,
    # HTTP status codes
    HTTP_OK,
    HTTP_RATE_LIMIT_CODES,
    HTTP_RATE_LIMITED,
    KEEPALIVE_EXPIRY,
    # Connection pool
    MAX_CONCURRENT_DOWNLOADS,
    RETRY_BASE_DELAY,
    # Retry configuration
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY,
    RETRY_MULTIPLIER,
    TIMEOUT_API,
    TIMEOUT_CDN,
    # Timeouts
    TIMEOUT_CONNECT,
    TIMEOUT_POOL,
    TIMEOUT_READ,
    TIMEOUT_WRITE,
)

# =============================================================================
# TIMEFRAME CONSTANTS (ADR-0048)
# =============================================================================
from .timeframes import (
    EXOTIC_TIMEFRAMES,
    STANDARD_TIMEFRAMES,
    # Type definitions
    Timeframe,
    # Primary mappings
    TIMEFRAME_TO_BINANCE_INTERVAL,
    TIMEFRAME_TO_MILLISECONDS,
    TIMEFRAME_TO_MINUTES,
    TIMEFRAME_TO_PYTHON_TIMEDELTA,
    # Derived mappings
    TIMEFRAME_TO_SECONDS,
    TIMEFRAME_TO_TIMEDELTA,
    # Validation sets
    VALID_TIMEFRAMES,
)

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # === Deployment ===
    # Type definitions
    "DeploymentMode",
    # Deployment modes
    "MODE_LOCAL",
    "MODE_CLOUD",
    "MODE_AUTO",
    "VALID_MODES",
    # Local host detection
    "LOCAL_HOSTS",
    # Environment variables
    "ENV_GCCH_MODE",
    "ENV_CLICKHOUSE_HOST",
    "ENV_CLICKHOUSE_PORT",
    "ENV_CLICKHOUSE_HTTP_PORT",
    "ENV_CLICKHOUSE_DATABASE",
    "ENV_CLICKHOUSE_USER",
    "ENV_CLICKHOUSE_PASSWORD",
    "ENV_CLICKHOUSE_SECURE",
    "CLICKHOUSE_ENV_VARS",
    # Ports
    "PORT_LOCAL_HTTP",
    "PORT_LOCAL_NATIVE",
    "PORT_CLOUD_HTTP",
    "PORT_CLOUD_NATIVE",
    "PORT_MIN",
    "PORT_MAX",
    # Defaults
    "DEFAULT_HOST",
    "DEFAULT_DATABASE",
    "DEFAULT_USER",
    # === Network ===
    # Timeouts
    "TIMEOUT_CONNECT",
    "TIMEOUT_READ",
    "TIMEOUT_WRITE",
    "TIMEOUT_POOL",
    "TIMEOUT_API",
    "TIMEOUT_CDN",
    # Connection pool
    "MAX_CONCURRENT_DOWNLOADS",
    "CONNECTION_POOL_SIZE",
    "CONNECTION_POOL_HEADROOM",
    "KEEPALIVE_EXPIRY",
    # HTTP status codes
    "HTTP_OK",
    "HTTP_NOT_MODIFIED",
    "HTTP_IP_BANNED",
    "HTTP_RATE_LIMITED",
    "HTTP_RATE_LIMIT_CODES",
    # Retry configuration
    "RETRY_MAX_ATTEMPTS",
    "RETRY_BASE_DELAY",
    "RETRY_MULTIPLIER",
    "RETRY_MAX_DELAY",
    "DEFAULT_RETRY_AFTER",
    # === Binance ===
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
    # Derived mappings
    "CDN_URL_BY_INSTRUMENT",
    "API_URL_BY_INSTRUMENT",
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
    # === Timeframes ===
    # Type definitions
    "Timeframe",
    # Primary mappings
    "TIMEFRAME_TO_MINUTES",
    "TIMEFRAME_TO_BINANCE_INTERVAL",
    # Derived mappings
    "TIMEFRAME_TO_MILLISECONDS",
    "TIMEFRAME_TO_SECONDS",
    "TIMEFRAME_TO_TIMEDELTA",
    "TIMEFRAME_TO_PYTHON_TIMEDELTA",
    # Validation sets
    "VALID_TIMEFRAMES",
    "STANDARD_TIMEFRAMES",
    "EXOTIC_TIMEFRAMES",
]
