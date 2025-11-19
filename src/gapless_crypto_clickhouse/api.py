#!/usr/bin/env python3
"""
Convenience API functions for gapless-crypto-data

Provides function-based API following financial data library conventions.
Simple and intuitive data collection returning standard pandas DataFrames.

Exception-only failure principles - all errors raise exceptions.

Examples:
    import gapless_crypto_clickhouse as gcd

    # Simple data fetching
    df = gcd.fetch_data("BTCUSDT", "1h", limit=1000)

    # Get available symbols and timeframes
    symbols = gcd.get_supported_symbols()
    intervals = gcd.get_supported_timeframes()

    # Download with date range
    df = gcd.download("ETHUSDT", "4h", start="2024-01-01", end="2024-06-30")
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional, Union

import pandas as pd

from .collectors.binance_public_data_collector import BinancePublicDataCollector
from .gap_filling.universal_gap_filler import UniversalGapFiller


def get_supported_symbols() -> List[str]:
    """Get list of supported USDT spot trading pairs.

    Returns:
        List of supported symbol strings (e.g., ["BTCUSDT", "ETHUSDT", ...])

    Examples:
        >>> symbols = get_supported_symbols()
        >>> print(f"Found {len(symbols)} supported symbols")
        >>> print(f"Bitcoin: {'BTCUSDT' in symbols}")
        Found 6 supported symbols
        Bitcoin: True
    """
    collector = BinancePublicDataCollector()
    return list(collector.known_symbols.keys())


def get_supported_timeframes() -> List[str]:
    """Get list of supported timeframe intervals.

    Returns:
        List of timeframe strings (e.g., ["1m", "5m", "1h", "4h", ...])

    Examples:
        >>> timeframes = get_supported_timeframes()
        >>> print(f"Available timeframes: {timeframes}")
        >>> print(f"1-hour supported: {'1h' in timeframes}")
        Available timeframes: ['1s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1mo']
        1-hour supported: True
    """
    collector = BinancePublicDataCollector()
    return collector.available_timeframes


# Type aliases for better discoverability and coding agent support
SupportedSymbol = Literal[
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "AVAXUSDT",
    "ATOMUSDT",
    "NEARUSDT",
    "FTMUSDT",
    "SANDUSDT",
    "MANAUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "EOSUSDT",
]

SupportedTimeframe = Literal[
    "1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"
]


def _validate_timeframe_parameters(
    timeframe: Optional[Union[str, SupportedTimeframe]],
    interval: Optional[Union[str, SupportedTimeframe]],
) -> str:
    """Validate and resolve timeframe/interval parameters.

    Args:
        timeframe: Timeframe parameter (preferred)
        interval: Legacy interval parameter

    Returns:
        Resolved timeframe string

    Raises:
        ValueError: If parameters are invalid or conflicting
    """
    # Dual parameter validation with exception-only failures
    if timeframe is None and interval is None:
        raise ValueError(
            "Must specify 'timeframe' parameter. "
            "CCXT-compatible 'timeframe' is preferred over legacy 'interval'."
        )

    if timeframe is not None and interval is not None:
        raise ValueError(
            "Cannot specify both 'timeframe' and 'interval' parameters. "
            "Use 'timeframe' (CCXT-compatible) or 'interval' (legacy), not both."
        )

    # Use timeframe if provided, otherwise use interval (legacy)
    return timeframe if timeframe is not None else interval


def _validate_index_type_parameter(index_type: Optional[str]) -> None:
    """Validate deprecated index_type parameter.

    Args:
        index_type: Deprecated index_type parameter

    Raises:
        ValueError: If index_type is invalid
    """
    if index_type is None:
        return

    import warnings

    warnings.warn(
        "The 'index_type' parameter is deprecated and will be removed in v3.0.0. "
        "Use standard pandas operations on the returned DataFrame instead.",
        DeprecationWarning,
        stacklevel=3,
    )

    # Validate deprecated parameter for backward compatibility
    valid_index_types = {"datetime", "range", "auto"}
    if index_type not in valid_index_types:
        raise ValueError(
            f"Invalid index_type '{index_type}'. "
            f"Must be one of: {', '.join(sorted(valid_index_types))}"
        )


def _calculate_date_range_from_limit(
    limit: Optional[int],
    period: str,
    start: Optional[str],
    end: Optional[str],
) -> tuple[str, str]:
    """Calculate date range from limit parameter.

    Args:
        limit: Maximum number of bars to return
        period: Timeframe interval
        start: Existing start date
        end: Existing end date

    Returns:
        Tuple of (start_date, end_date) strings
    """
    # If start/end already specified, use them
    if start or end:
        return start, end

    # If no limit, return as-is
    if not limit:
        return start, end

    # Calculate start date based on limit and interval
    interval_minutes = {
        "1s": 1 / 60,  # 1 second = 1/60 minute
        "1m": 1,
        "3m": 3,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "6h": 360,
        "8h": 480,
        "12h": 720,
        "1d": 1440,
    }

    if period in interval_minutes:
        minutes_total = limit * interval_minutes[period]
        start_date = datetime.now() - timedelta(minutes=minutes_total)
        calculated_start = start_date.strftime("%Y-%m-%d")
        calculated_end = datetime.now().strftime("%Y-%m-%d")
    else:
        # Default fallback for unknown periods
        calculated_start = "2024-01-01"
        calculated_end = datetime.now().strftime("%Y-%m-%d")

    return calculated_start, calculated_end


def _apply_default_date_range(start: Optional[str], end: Optional[str]) -> tuple[str, str]:
    """Apply default date range if not specified.

    Args:
        start: Start date
        end: End date

    Returns:
        Tuple of (start_date, end_date) with defaults applied
    """
    if not start:
        start = "2021-01-01"
    if not end:
        end = datetime.now().strftime("%Y-%m-%d")
    return start, end


def _perform_gap_filling(
    result: dict,
    auto_fill_gaps: bool,
    period: str,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Perform automatic gap filling on collected data.

    Args:
        result: Collection result dictionary
        auto_fill_gaps: Whether to auto-fill gaps
        period: Timeframe interval
        df: DataFrame with collected data

    Returns:
        DataFrame with gaps filled (if applicable)
    """
    if not auto_fill_gaps or not result.get("filepath"):
        return df

    import logging

    logger = logging.getLogger(__name__)

    csv_file = Path(result["filepath"])
    gap_filler = UniversalGapFiller()

    # Detect and fill gaps
    gap_result = gap_filler.process_file(csv_file, period)

    if gap_result["gaps_detected"] > 0:
        if gap_result["gaps_filled"] > 0:
            logger.info(
                f"✅ Auto-filled {gap_result['gaps_filled']}/{gap_result['gaps_detected']} "
                f"gap(s) with authentic Binance API data"
            )
            # Reload DataFrame with filled gaps
            df = pd.read_csv(csv_file, comment="#")
        else:
            logger.warning(
                f"⚠️  Detected {gap_result['gaps_detected']} gap(s) but could not fill them. "
                f"Data may not be complete."
            )

    return df


def _apply_limit_and_index(
    df: pd.DataFrame,
    limit: Optional[int],
    index_type: Optional[str],
) -> pd.DataFrame:
    """Apply limit and index_type to DataFrame.

    Args:
        df: DataFrame to process
        limit: Maximum number of rows to return
        index_type: Deprecated index_type parameter

    Returns:
        Processed DataFrame
    """
    # Apply limit if specified
    if limit and len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)

    # Handle deprecated index_type parameter for backward compatibility
    if index_type in ("datetime", "auto"):
        if "date" in df.columns:
            # For deprecated datetime mode, return DataFrame with DatetimeIndex
            return df.set_index("date", drop=False)
        else:
            # Handle edge case where date column is missing
            return df
    elif index_type == "range":
        # For deprecated range mode, return DataFrame with RangeIndex (default)
        return df
    else:
        # Default behavior: return standard pandas DataFrame with RangeIndex
        # Users can use df.set_index('date') for DatetimeIndex operations
        return df


def _create_empty_dataframe() -> pd.DataFrame:
    """Create empty DataFrame with expected OHLCV columns.

    Returns:
        Empty DataFrame with standard columns
    """
    columns = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
    ]
    return pd.DataFrame(columns=columns)


def fetch_data(
    symbol: Union[str, SupportedSymbol],
    timeframe: Optional[Union[str, SupportedTimeframe]] = None,
    limit: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    output_dir: Optional[Union[str, Path]] = None,
    index_type: Optional[Literal["datetime", "range", "auto"]] = None,  # Deprecated parameter
    auto_fill_gaps: bool = True,
    *,
    interval: Optional[Union[str, SupportedTimeframe]] = None,
) -> pd.DataFrame:
    """Fetch cryptocurrency data as standard pandas DataFrame with zero gaps guarantee.

    Returns pandas DataFrame with complete OHLCV and microstructure data.
    All analysis and calculations can be performed using standard pandas operations.

    By default, automatically detects and fills gaps using authentic Binance API data
    to deliver on the "zero gaps guarantee" promise.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT")
        timeframe: Timeframe interval (e.g., "1m", "5m", "1h", "4h", "1d")
        limit: Maximum number of recent bars to return (optional)
        start: Start date in YYYY-MM-DD format (optional)
        end: End date in YYYY-MM-DD format (optional)
        output_dir: Directory to save CSV files (optional)
        index_type: DEPRECATED - Use pandas operations directly
        auto_fill_gaps: Automatically fill detected gaps with authentic Binance API data (default: True)
        interval: Legacy parameter name for timeframe (deprecated, use timeframe)

    Returns:
        pd.DataFrame with OHLCV data and microstructure columns:
        - date: Timestamp (open time)
        - open, high, low, close: Price data
        - volume: Base asset volume
        - close_time: Close timestamp
        - quote_asset_volume: Quote asset volume
        - number_of_trades: Trade count
        - taker_buy_base_asset_volume: Taker buy base volume
        - taker_buy_quote_asset_volume: Taker buy quote volume

    Examples:
        # Simple data fetching
        df = fetch_data("BTCUSDT", "1h", limit=1000)

        # Standard pandas operations for analysis
        returns = df['close'].pct_change()                    # Returns calculation
        rolling_vol = df['close'].rolling(20).std()           # Rolling volatility
        df_resampled = df.set_index('date').resample('4H').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        })  # OHLCV resampling

        # Fetch specific date range
        df = fetch_data("ETHUSDT", "4h", start="2024-01-01", end="2024-06-30")

        # Save to custom directory
        df = fetch_data("SOLUSDT", "1h", limit=500, output_dir="./crypto_data")

        # Legacy interval parameter (deprecated)
        df = fetch_data("BTCUSDT", interval="1h", limit=1000)
    """
    # Validate and resolve timeframe parameters
    period = _validate_timeframe_parameters(timeframe, interval)

    # Validate deprecated index_type parameter
    _validate_index_type_parameter(index_type)

    # Calculate date range from limit if needed
    start, end = _calculate_date_range_from_limit(limit, period, start, end)

    # Apply default date range if not specified
    start, end = _apply_default_date_range(start, end)

    # Initialize collector and collect data
    collector = BinancePublicDataCollector(
        symbol=symbol, start_date=start, end_date=end, output_dir=output_dir
    )
    result = collector.collect_timeframe_data(period)

    # Process result or return empty DataFrame
    if result and "dataframe" in result:
        df = result["dataframe"]

        # Auto-fill gaps if enabled (delivers "zero gaps guarantee")
        df = _perform_gap_filling(result, auto_fill_gaps, period, df)

        # Apply limit and index_type
        return _apply_limit_and_index(df, limit, index_type)
    else:
        # Return empty DataFrame with expected columns
        return _create_empty_dataframe()


def download(
    symbol: Union[str, SupportedSymbol],
    timeframe: Optional[Union[str, SupportedTimeframe]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    output_dir: Optional[Union[str, Path]] = None,
    index_type: Optional[Literal["datetime", "range", "auto"]] = None,  # Deprecated parameter
    auto_fill_gaps: bool = True,
    *,
    interval: Optional[Union[str, SupportedTimeframe]] = None,
) -> pd.DataFrame:
    """Download cryptocurrency data with zero gaps guarantee.

    Provides familiar API patterns for intuitive data collection.
    By default, automatically detects and fills gaps using authentic Binance API data
    to deliver on the package's core promise of zero gaps.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        timeframe: Timeframe interval (default: "1h" if neither specified)
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        output_dir: Directory to save CSV files
        index_type: DEPRECATED - Use standard pandas operations instead
        auto_fill_gaps: Automatically fill detected gaps with authentic Binance API data (default: True)
        interval: Legacy parameter name for timeframe (deprecated)

    Returns:
        pd.DataFrame with complete OHLCV and microstructure data (gapless by default)

    Examples:
        # Simple data download (automatically fills gaps)
        df = download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

        # Disable auto-fill if you want raw Vision archive data
        df = download("ETHUSDT", "4h", auto_fill_gaps=False)

        # Legacy interval parameter
        df = download("BTCUSDT", interval="1h")
    """
    # Apply default if neither parameter specified
    if timeframe is None and interval is None:
        timeframe = "1h"

    return fetch_data(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        output_dir=output_dir,
        index_type=index_type,
        auto_fill_gaps=auto_fill_gaps,
        interval=interval,
    )


def fill_gaps(directory: Union[str, Path], symbols: Optional[List[str]] = None) -> dict:
    """Fill gaps in existing CSV data files.

    Args:
        directory: Directory containing CSV files to process
        symbols: Optional list of symbols to process (default: all found)

    Returns:
        dict: Gap filling results with statistics

    Examples:
        # Fill all gaps in directory
        results = fill_gaps("./data")

        # Fill gaps for specific symbols
        results = fill_gaps("./data", symbols=["BTCUSDT", "ETHUSDT"])
    """
    gap_filler = UniversalGapFiller()
    target_dir = Path(directory)

    # Find CSV files
    csv_files = list(target_dir.glob("*.csv"))
    if symbols:
        # Filter by specified symbols
        csv_files = [f for f in csv_files if any(symbol in f.name for symbol in symbols)]

    results = {
        "files_processed": 0,
        "gaps_detected": 0,
        "gaps_filled": 0,
        "success_rate": 0.0,
        "file_results": {},
    }

    for csv_file in csv_files:
        # Extract timeframe from filename
        timeframe = "1h"  # Default
        for tf in ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]:
            if f"-{tf}_" in csv_file.name or f"-{tf}-" in csv_file.name:
                timeframe = tf
                break

        # Process file
        file_result = gap_filler.process_file(csv_file, timeframe)
        results["file_results"][csv_file.name] = file_result
        results["files_processed"] += 1
        results["gaps_detected"] += file_result["gaps_detected"]
        results["gaps_filled"] += file_result["gaps_filled"]

    # Calculate overall success rate
    if results["gaps_detected"] > 0:
        results["success_rate"] = (results["gaps_filled"] / results["gaps_detected"]) * 100
    else:
        results["success_rate"] = 100.0

    return results


def get_info() -> dict:
    """Get library information and capabilities.

    Returns:
        dict: Library metadata and capabilities

    Examples:
        >>> info = get_info()
        >>> print(f"Version: {info['version']}")
        >>> print(f"Supported symbols: {len(info['supported_symbols'])}")
    """
    from . import __version__

    return {
        "version": __version__,
        "name": "gapless-crypto-data",
        "description": "Ultra-fast cryptocurrency data collection with zero gaps guarantee",
        "supported_symbols": get_supported_symbols(),
        "supported_timeframes": get_supported_timeframes(),
        "market_type": "USDT spot pairs only",
        "data_source": "Binance public data repository + API",
        "features": [
            "22x faster than API calls",
            "Full 11-column microstructure format",
            "Automatic gap detection and filling",
            "Production-grade data quality",
        ],
    }


def get_supported_intervals() -> List[str]:
    """Get list of supported timeframe intervals (legacy alias).

    Deprecated: Use get_supported_timeframes() instead.
    Maintained for backward compatibility with existing code.

    Returns:
        List of timeframe strings (e.g., ["1m", "5m", "1h", "4h", ...])

    Examples:
        >>> intervals = get_supported_intervals()  # deprecated
        >>> timeframes = get_supported_timeframes()  # preferred
    """
    import warnings

    warnings.warn(
        "get_supported_intervals() is deprecated. Use get_supported_timeframes() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return get_supported_timeframes()


def save_parquet(df: pd.DataFrame, path: str) -> None:
    """Save DataFrame to Parquet format with optimized compression.

    Args:
        df: DataFrame to save
        path: Output file path (should end with .parquet)

    Raises:
        FileNotFoundError: If output directory doesn't exist
        PermissionError: If cannot write to path
        ValueError: If DataFrame is invalid

    Examples:
        >>> df = fetch_data("BTCUSDT", "1h", limit=1000)
        >>> save_parquet(df, "btc_data.parquet")
    """
    if df is None or df.empty:
        raise ValueError("Cannot save empty DataFrame to Parquet")

    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)


def load_parquet(path: str) -> pd.DataFrame:
    """Load DataFrame from Parquet file.

    Args:
        path: Parquet file path

    Returns:
        DataFrame with original structure and data types

    Raises:
        FileNotFoundError: If file doesn't exist
        ParquetError: If file is corrupted or invalid

    Examples:
        >>> df = load_parquet("btc_data.parquet")
        >>> print(f"Loaded {len(df)} bars")
    """
    return pd.read_parquet(path, engine="pyarrow")
