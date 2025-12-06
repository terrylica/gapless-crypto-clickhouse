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
        Note: This package never had a CLI (Python API only).

Supported Symbols (715 perpetual symbols - Spot + Futures Aligned):
    Both spot and futures-um support 715 validated perpetual symbols
    sourced from binance-futures-availability package (95%+ SLA, daily S3 Vision probes).

    See get_supported_symbols() for complete list.
    Major pairs: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, and 708 more.
"""

__version__ = "8.0.0"
__author__ = "Eon Labs"
__email__ = "terry@eonlabs.com"

# Core classes (advanced/power-user API)
# Enhanced DataFrame for domain-specific operations
# Convenience functions (simple/intuitive API)
# API-only probe hooks for AI coding agents
from . import __probe__, constants, probe
from .api import (
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

__all__ = [
    # Simple function-based API (recommended for most users)
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
]
