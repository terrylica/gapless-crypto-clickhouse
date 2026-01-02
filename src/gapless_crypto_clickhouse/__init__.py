"""
Gapless Crypto ClickHouse - ClickHouse-based cryptocurrency data collection with zero-gap guarantee

Market Compatibility:
- USDT SPOT PAIRS (BTCUSDT, ETHUSDT, SOLUSDT, etc.)
- USDT-margined PERPETUAL FUTURES (BTCUSDT perps, ETHUSDT perps, etc.)
- Instrument type distinction via `instrument_type` column ('spot' or 'futures')
- NO delivery futures, NO coin-margined futures

Core Features:
- Data collection via Binance public data repository (22x performance vs API calls)
- Full 11-column microstructure format with order flow and liquidity metrics
- Zero gaps guarantee through authentic API-first validation
- UV-based Python tooling
- Atomic file operations
- Complete 16-timeframe support (13 standard: 1s-1d + 3 exotic: 3d, 1w, 1mo)
- Ultra-high frequency (1s) to daily (1d) data collection
- Intelligent monthly-to-daily fallback for seamless recent data access
- Gap detection and filling with authentic data only
- CCXT-compatible dual parameter support (timeframe/interval)
- Backward compatibility with 5-year deprecation period

Data Source:
    Binance Spot Market: https://data.binance.vision/data/spot/monthly/klines/
    Market Type: SPOT only (no futures/derivatives)
    Supported Pairs: USDT-quoted spot pairs exclusively

Usage:
    # Function-based API
    import gapless_crypto_clickhouse as gcch

    # Fetch recent data as standard pandas DataFrame
    df = gcch.fetch_data("BTCUSDT", timeframe="1h", limit=1000)

    # Standard pandas operations for analysis
    returns = df['close'].pct_change()                     # Returns calculation
    rolling_vol = df['close'].rolling(20).std()            # Rolling volatility
    max_drawdown = (df['close'] / df['close'].cummax() - 1).min()  # Drawdown

    # Resampling with pandas
    df_resampled = df.set_index('timestamp').resample('4H').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    })

    # Backward compatibility (legacy interval parameter)
    df = gcch.fetch_data("BTCUSDT", interval="1h", limit=1000)  # DeprecationWarning

    # Download with date range
    df = gcch.download("ETHUSDT", timeframe="4h", start="2024-01-01", end="2024-06-30")

    # Get available symbols and timeframes
    symbols = gcch.get_supported_symbols()
    timeframes = gcch.get_supported_timeframes()

    # Fill gaps in existing data
    results = gcch.fill_gaps("./data")

    # Class-based API (for complex workflows)
    from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller

    collector = BinancePublicDataCollector()
    result = collector.collect_timeframe_data("1h")
    df = result["dataframe"]

Package Relationship:
    This package is a fork of gapless-crypto-data focused on ClickHouse database workflows.

    For file-based workflows (CSV/Parquet only):
        See https://pypi.org/project/gapless-crypto-data/

    Migrating from gapless-crypto-data:
        See docs/development/CLI_MIGRATION_GUIDE.md for migration guide.

    CLI Commands:
        gcch init    - Deploy ClickHouse schema
        gcch status  - Check ClickHouse connectivity
        gcch check   - Validate complete setup

Supported Symbols (715 perpetual symbols - Spot + Futures Aligned):
    Both spot and futures-um support 715 validated perpetual symbols
    sourced from binance-futures-availability package (95%+ SLA, daily S3 Vision probes).

    See get_supported_symbols() for complete list.
    Major pairs: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, and 708 more.
"""

# ADR: 2025-12-27-importlib-metadata-version-management
# Read version from package metadata at runtime (single source of truth: pyproject.toml)
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gapless-crypto-clickhouse")
except PackageNotFoundError:
    # Development mode or editable install without metadata
    __version__ = "0.0.0+dev"

__author__ = "Eon Labs"
__email__ = "terry@eonlabs.com"

# Core classes (advanced/power-user API)
# Enhanced DataFrame for domain-specific operations
# Convenience functions (simple/intuitive API)
# API-only probe hooks for AI coding agents
from . import __probe__, constants, probe
from .api import (
    BINANCE_COLUMN_MAP,  # v17.3.0: Column name mappings
    PACKAGE_COLUMN_MAP,  # v17.3.0: Reverse column name mappings
    InstrumentType,  # ADR-0021: Type alias for instrument type hints
    download,
    download_multiple,
    fetch_data,
    fill_gaps,
    get_info,
    get_supported_intervals,
    get_supported_symbols,
    get_supported_timeframes,
    load_parquet,
    save_parquet,
    to_binance_columns,  # v17.3.0: Convert timestamp → open_time
    to_package_columns,  # v17.3.0: Convert open_time → timestamp
)
from .collectors.binance_public_data_collector import BinancePublicDataCollector

# Export key constants at top level (ADR-0046)
from .constants import (
    MODE_AUTO,
    MODE_CLOUD,
    MODE_LOCAL,
    PORT_CLOUD_HTTP,
    PORT_LOCAL_HTTP,
    DeploymentMode,
)
from .exceptions import (
    DataCollectionError,
    GapFillingError,
    GaplessCryptoDataError,
    NetworkError,
    ValidationError,
)
from .gap_filling.safe_file_operations import AtomicCSVOperations, SafeCSVMerger
from .gap_filling.universal_gap_filler import UniversalGapFiller
from .query_api import query_ohlcv  # v6.0.0: Unified query API with auto-ingestion (ADR-0023)

# =============================================================================
# BACKWARD-COMPATIBLE ALIASES (v17.3.0)
# =============================================================================
# These aliases exist for discoverability - users who expect these names based on
# package naming patterns or other crypto data libraries. Native names are preferred.
#
# ADR: 2025-12-31-api-discoverability-aliases


def _create_deprecated_alias(native_class, alias_name: str, native_name: str):
    """Create a class alias that warns on first instantiation."""
    import warnings

    class AliasClass(native_class):
        _warned = False

        def __new__(cls, *args, **kwargs):
            if not cls._warned:
                warnings.warn(
                    f"{alias_name} is a deprecated alias. Use {native_name} instead. "
                    f"Example: from gapless_crypto_clickhouse import {native_name}",
                    DeprecationWarning,
                    stacklevel=2,
                )
                cls._warned = True
            return super().__new__(cls)

    AliasClass.__name__ = alias_name
    AliasClass.__qualname__ = alias_name
    AliasClass.__doc__ = f"""Deprecated alias for {native_name}.

    .. deprecated:: 17.3.0
        Use :class:`{native_name}` instead.

    This alias exists for discoverability. Users expecting class names based on
    package naming patterns (e.g., "GaplessCollector") are guided to the native API.
    """
    return AliasClass


# GaplessCollector → BinancePublicDataCollector
# Users expect "Gapless*" classes based on package name "gapless-crypto-clickhouse"
GaplessCollector = _create_deprecated_alias(
    BinancePublicDataCollector, "GaplessCollector", "BinancePublicDataCollector"
)

# BinanceSpotData → BinancePublicDataCollector
# Users from other crypto libraries expect "*SpotData" pattern
BinanceSpotData = _create_deprecated_alias(
    BinancePublicDataCollector, "BinanceSpotData", "BinancePublicDataCollector"
)


def check_setup() -> dict:
    """Verify SDK is ready to use.

    ADR: 2025-12-21-sdk-first-run-experience

    Single function that validates all prerequisites for using gapless-crypto-clickhouse.
    Call this before your first query to catch configuration issues early.

    Returns:
        dict with keys:
            - ready (bool): True if all checks pass
            - mode (str): "local" or "cloud"
            - clickhouse_running (bool): ClickHouse server reachable
            - schema_exists (bool): ohlcv table exists
            - data_count (int): Number of rows in ohlcv table
            - issues (list): List of {"message": str, "fix": str} dicts

    Example:
        >>> import gapless_crypto_clickhouse as gcch
        >>> status = gcch.check_setup()
        >>> if not status["ready"]:
        ...     for issue in status["issues"]:
        ...         print(f"Issue: {issue['message']}")
        ...         print(f"Fix: {issue['fix']}")
    """
    from .clickhouse import ClickHouseConfig, ClickHouseConnection

    result: dict = {
        "ready": True,
        "mode": probe.get_current_mode(),
        "clickhouse_running": False,
        "schema_exists": False,
        "data_count": 0,
        "issues": [],
    }

    # Check connectivity
    try:
        config = ClickHouseConfig.from_env()
        conn = ClickHouseConnection(config)

        if conn.health_check():
            result["clickhouse_running"] = True

            # Check schema
            if conn._table_exists("ohlcv"):
                result["schema_exists"] = True
                # Check data count
                rows = conn.execute("SELECT COUNT(*) FROM ohlcv")
                result["data_count"] = rows[0][0] if rows else 0
            else:
                result["ready"] = False
                result["issues"].append(
                    {
                        "message": "ohlcv table not found",
                        "fix": "Run: gcch init (CLI) or use auto_ingest=True in query_ohlcv()",
                    }
                )
        else:
            result["ready"] = False
            result["issues"].append(
                {
                    "message": "ClickHouse health check failed",
                    "fix": "Check ClickHouse server status and connectivity",
                }
            )

        conn.client.close()

    except Exception as e:
        result["ready"] = False
        result["clickhouse_running"] = False

        # Provide specific guidance based on error type
        error_str = str(e)
        if "CLICKHOUSE_HOST" in error_str:
            result["issues"].append(
                {
                    "message": "ClickHouse credentials not configured",
                    "fix": "Set CLICKHOUSE_HOST and CLICKHOUSE_PASSWORD env vars, or use GCCH_MODE=local",
                }
            )
        elif "NameResolutionError" in error_str or "Max retries" in error_str:
            result["issues"].append(
                {
                    "message": "Cannot reach ClickHouse server",
                    "fix": "Start ClickHouse: clickhouse server --daemon (local) or check Cloud credentials",
                }
            )
        else:
            result["issues"].append(
                {
                    "message": f"Connection failed: {e}",
                    "fix": "Check probe.check_local_clickhouse() and probe.get_deployment_modes()",
                }
            )

    return result


__all__ = [
    # Simple function-based API (recommended for most users)
    "check_setup",  # v17.1.0: Unified setup check (ADR: 2025-12-21-sdk-first-run-experience)
    "query_ohlcv",  # v6.0.0: Unified query API with auto-ingestion (ADR-0023)
    "fetch_data",
    "download",
    "download_multiple",
    "get_supported_symbols",
    "get_supported_timeframes",
    "get_supported_intervals",  # Legacy compatibility
    "fill_gaps",
    "get_info",
    "save_parquet",
    "load_parquet",
    # Column naming utilities (v17.3.0)
    "to_binance_columns",  # timestamp → open_time
    "to_package_columns",  # open_time → timestamp
    "BINANCE_COLUMN_MAP",
    "PACKAGE_COLUMN_MAP",
    # Type aliases (v3.2.0 - ADR-0021, ADR-0046)
    "InstrumentType",  # Literal["spot", "futures-um"]
    "DeploymentMode",  # Literal["local", "cloud", "auto"]
    # Constants (ADR-0046)
    "constants",  # Full constants module
    "MODE_LOCAL",
    "MODE_CLOUD",
    "MODE_AUTO",
    "PORT_LOCAL_HTTP",
    "PORT_CLOUD_HTTP",
    # Advanced class-based API (for complex workflows)
    "BinancePublicDataCollector",
    "UniversalGapFiller",
    "AtomicCSVOperations",
    "SafeCSVMerger",
    # Structured exception hierarchy (v3.2.0)
    "GaplessCryptoDataError",
    "DataCollectionError",
    "ValidationError",
    "NetworkError",
    "GapFillingError",
    # AI agent probe hooks (v6.0.0)
    "__probe__",
    "probe",
    # Discoverability aliases (v17.3.0 - deprecated, use native names)
    "GaplessCollector",  # → BinancePublicDataCollector
    "BinanceSpotData",  # → BinancePublicDataCollector
]
