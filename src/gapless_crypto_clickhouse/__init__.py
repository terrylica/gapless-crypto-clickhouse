"""
Gapless Crypto ClickHouse v1.0.0 - ClickHouse-based cryptocurrency data collection with zero-gap guarantee

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
- Complete 13-timeframe support (1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d)
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
    import gapless_crypto_clickhouse as gcd

    # Fetch recent data as standard pandas DataFrame
    df = gcd.fetch_data("BTCUSDT", timeframe="1h", limit=1000)

    # Standard pandas operations for analysis
    returns = df['close'].pct_change()                     # Returns calculation
    rolling_vol = df['close'].rolling(20).std()            # Rolling volatility
    max_drawdown = (df['close'] / df['close'].cummax() - 1).min()  # Drawdown

    # Resampling with pandas
    df_resampled = df.set_index('date').resample('4H').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'volume': 'sum'
    })

    # Backward compatibility (legacy interval parameter)
    df = gcd.fetch_data("BTCUSDT", interval="1h", limit=1000)  # DeprecationWarning

    # Download with date range
    df = gcd.download("ETHUSDT", timeframe="4h", start="2024-01-01", end="2024-06-30")

    # Get available symbols and timeframes
    symbols = gcd.get_supported_symbols()
    timeframes = gcd.get_supported_timeframes()

    # Fill gaps in existing data
    results = gcd.fill_gaps("./data")

    # Class-based API (for complex workflows)
    from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller

    collector = BinancePublicDataCollector()
    result = collector.collect_timeframe_data("1h")
    df = result["dataframe"]

CLI Removed in v4.0.0:
    ⚠️  The CLI was removed in v4.0.0. Please use the Python API instead (see above).

    For v3.x users upgrading:
        See docs/development/CLI_MIGRATION_GUIDE.md for migration instructions.
        All CLI functionality is available through the Python API.

Supported Symbols (USDT Spot Only):
    BTCUSDT, ETHUSDT, SOLUSDT, ADAUSDT, DOTUSDT, LINKUSDT, MATICUSDT,
    AVAXUSDT, ATOMUSDT, NEARUSDT, FTMUSDT, SANDUSDT, MANAUSDT, etc.
"""

__version__ = "1.0.0"
__author__ = "Eon Labs"
__email__ = "terry@eonlabs.com"

# Core classes (advanced/power-user API)
# Enhanced DataFrame for domain-specific operations
# Convenience functions (simple/intuitive API)
# API-only probe hooks for AI coding agents
from . import __probe__
from .api import (
    download,
    fetch_data,
    fill_gaps,
    get_info,
    get_supported_intervals,
    get_supported_symbols,
    get_supported_timeframes,
    load_parquet,
    save_parquet,
)
from .collectors.binance_public_data_collector import BinancePublicDataCollector
from .exceptions import (
    DataCollectionError,
    GapFillingError,
    GaplessCryptoDataError,
    NetworkError,
    ValidationError,
)
from .gap_filling.safe_file_operations import AtomicCSVOperations, SafeCSVMerger
from .gap_filling.universal_gap_filler import UniversalGapFiller

__all__ = [
    # Simple function-based API (recommended for most users)
    "fetch_data",
    "download",
    "get_supported_symbols",
    "get_supported_timeframes",
    "get_supported_intervals",  # Legacy compatibility
    "fill_gaps",
    "get_info",
    "save_parquet",
    "load_parquet",
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
    # AI agent probe hooks
    "__probe__",
]
