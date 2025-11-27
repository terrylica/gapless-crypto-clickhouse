#!/usr/bin/env python3
"""
Convenience API functions for gapless-crypto-clickhouse

Provides function-based API following financial data library conventions.
Simple and intuitive data collection returning standard pandas DataFrames.

Exception-only failure principles - all errors raise exceptions.

Examples:
    import gapless_crypto_clickhouse as gcch

    # Simple data fetching
    df = gcch.fetch_data("BTCUSDT", "1h", limit=1000)

    # Get available symbols and timeframes
    symbols = gcch.get_supported_symbols()
    intervals = gcch.get_supported_timeframes()

    # Download with date range
    df = gcch.download("ETHUSDT", "4h", start="2024-01-01", end="2024-06-30")
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional, Union

import pandas as pd

from .collectors.binance_public_data_collector import BinancePublicDataCollector
from .constants import TIMEFRAME_TO_MINUTES, VALID_INSTRUMENT_TYPES, InstrumentType
from .gap_filling.universal_gap_filler import UniversalGapFiller


def get_supported_symbols(instrument_type: InstrumentType = "spot") -> List[str]:
    """Get list of supported trading pairs for the specified instrument type.

    Returns 715 validated perpetual symbols for both spot and futures.
    Symbol list sourced from binance-futures-availability package
    (validated daily via S3 Vision probes, 95%+ SLA).

    Note: The instrument_type parameter is retained for API compatibility,
    but both "spot" and "futures-um" return the same 715-symbol list.
    Rationale: Binance markets are aligned - perpetual futures symbols
    correspond to spot pairs. See ADR-0022 for complete alignment rationale.

    Args:
        instrument_type: Type of instrument ("spot" or "futures-um"). Default: "spot"

    Returns:
        List of 713 supported perpetual symbols (same for both spot and futures)

    Raises:
        ValueError: If instrument_type is invalid

    Examples:
        >>> # Get spot symbols (default) - returns 715 symbols
        >>> symbols = get_supported_symbols()
        >>> print(f"Found {len(symbols)} spot symbols")
        Found 713 spot symbols

        >>> # Get futures symbols - returns same 715 symbols
        >>> futures = get_supported_symbols(instrument_type="futures-um")
        >>> print(f"Found {len(futures)} futures symbols")
        Found 713 futures symbols

        >>> # Verify alignment
        >>> get_supported_symbols("spot") == get_supported_symbols("futures-um")
        True

        >>> # Check symbol availability
        >>> print(f"Bitcoin supported: {'BTCUSDT' in symbols}")
        Bitcoin supported: True
    """
    from binance_futures_availability.config.symbol_loader import load_symbols

    # Validate parameter (fail fast on invalid types)
    _validate_instrument_type(instrument_type)

    # Return same 715 symbols for both types (ADR-0022)
    return load_symbols("perpetual")


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


# DEPRECATED in v4.1.0: SupportedSymbol type alias removed (ADR-0022)
# Reason: 715-symbol Literal exceeds practical type checker limits
# Migration: Use `str` for symbol parameters, validate via get_supported_symbols()
#
# Before (v4.0.0):
#   def my_function(symbol: SupportedSymbol) -> None: ...
#
# After (v4.1.0):
#   def my_function(symbol: str) -> None:
#       if symbol not in get_supported_symbols():
#           raise ValueError(f"Unsupported symbol: {symbol}")
#
# Note: Spot and futures now both support 715 symbols (up from 20 spot symbols)

SupportedTimeframe = Literal[
    "1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"
]


def _validate_instrument_type(instrument_type: str) -> None:
    """Validate instrument_type parameter (ADR-0050).

    Args:
        instrument_type: Instrument type to validate

    Raises:
        ValueError: If instrument_type is not supported

    Examples:
        >>> _validate_instrument_type("spot")  # Valid
        >>> _validate_instrument_type("futures-um")  # Valid
        >>> _validate_instrument_type("futures")  # Invalid
        Traceback (most recent call last):
            ...
        ValueError: Invalid instrument_type 'futures'. Must be one of: ['futures-um', 'spot']
    """
    if instrument_type not in VALID_INSTRUMENT_TYPES:
        raise ValueError(
            f"Invalid instrument_type '{instrument_type}'. "
            f"Must be one of: {sorted(VALID_INSTRUMENT_TYPES)}. "
            f"Use 'futures-um' for USDT-margined perpetual futures (715 symbols). "
            f"See get_supported_symbols(instrument_type='{instrument_type}') for available symbols."
        )


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


def _validate_symbol(symbol: str, instrument_type: str = "spot") -> None:
    """Validate symbol against known supported symbols for instrument type.

    Args:
        symbol: Trading pair symbol to validate
        instrument_type: Instrument type context for validation

    Raises:
        ValueError: If symbol is not supported, with suggestions
    """
    from gapless_crypto_clickhouse import get_supported_symbols

    supported = get_supported_symbols(instrument_type=instrument_type)

    if symbol not in supported:
        # Find close matches (simple prefix matching)
        symbol_upper = symbol.upper()
        close_matches = [s for s in supported if s.startswith(symbol_upper[:3])]

        if close_matches:
            raise ValueError(
                f"Invalid symbol '{symbol}' for instrument_type='{instrument_type}'. "
                f"Did you mean '{close_matches[0]}'? "
                f"Supported {instrument_type} symbols: {', '.join(supported[:5])}, ... "
                f"(see get_supported_symbols(instrument_type='{instrument_type}') for full list)"
            )
        else:
            raise ValueError(
                f"Invalid symbol '{symbol}' for instrument_type='{instrument_type}'. "
                f"Supported {instrument_type} symbols: {', '.join(supported[:10])}, ... "
                f"(see get_supported_symbols(instrument_type='{instrument_type}') for full list of {len(supported)} symbols)"
            )


def _validate_timeframe_value(timeframe: str) -> None:
    """Validate timeframe against supported timeframes.

    Args:
        timeframe: Timeframe interval to validate

    Raises:
        ValueError: If timeframe is not supported
    """
    from gapless_crypto_clickhouse import get_supported_timeframes

    supported = get_supported_timeframes()

    if timeframe not in supported:
        raise ValueError(
            f"Invalid timeframe '{timeframe}'. "
            f"Supported timeframes: {', '.join(supported)} "
            f"(see get_supported_timeframes() for details)"
        )


def _validate_date_format(date_str: Optional[str], param_name: str) -> None:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate
        param_name: Parameter name for error context

    Raises:
        ValueError: If date format is invalid
    """
    if date_str is None:
        return

    import re

    # Check YYYY-MM-DD format
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(
            f"Invalid {param_name} format '{date_str}'. "
            f"Expected format: YYYY-MM-DD (e.g., '2024-01-01')"
        )

    # Validate date is parseable
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid {param_name} date '{date_str}': {str(e)}") from e


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

    # Calculate start date based on limit and interval (ADR-0048)
    if period in TIMEFRAME_TO_MINUTES:
        minutes_total = limit * TIMEFRAME_TO_MINUTES[period]
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
    instrument_type: str = "spot",  # ADR-0021
) -> pd.DataFrame:
    """Perform automatic gap filling on collected data.

    Args:
        result: Collection result dictionary
        auto_fill_gaps: Whether to auto-fill gaps
        period: Timeframe interval
        df: DataFrame with collected data
        instrument_type: Instrument type for API endpoint selection

    Returns:
        DataFrame with gaps filled (if applicable)
    """
    if not auto_fill_gaps or not result.get("filepath"):
        return df

    import logging

    logger = logging.getLogger(__name__)

    csv_file = Path(result["filepath"])
    gap_filler = UniversalGapFiller(
        instrument_type=instrument_type
    )  # ADR-0021: Pass instrument type for API endpoint

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
    symbol: str,
    timeframe: Optional[Union[str, SupportedTimeframe]] = None,
    limit: Optional[int] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # Alias for start
    end_date: Optional[str] = None,  # Alias for end
    output_dir: Optional[Union[str, Path]] = None,
    index_type: Optional[Literal["datetime", "range", "auto"]] = None,  # Deprecated parameter
    auto_fill_gaps: bool = True,
    instrument_type: InstrumentType = "spot",  # ADR-0021: UM futures support
    *,
    interval: Optional[Union[str, SupportedTimeframe]] = None,
) -> pd.DataFrame:
    """Fetch cryptocurrency data as standard pandas DataFrame with zero gaps guarantee.

    Returns pandas DataFrame with complete OHLCV and microstructure data.
    All analysis and calculations can be performed using standard pandas operations.

    By default, automatically detects and fills gaps using authentic Binance API data
    to deliver on the "zero gaps guarantee" promise.

    **⚠️ IMPORTANT - funding_rate Column (v3.2.0+)**:
    The DataFrame includes a `funding_rate` column for futures data, but it is **NULL**
    in v3.2.0 (not yet populated). Funding rate collection will be implemented in v3.3.0
    via a separate `/fapi/v1/fundingRate` API endpoint. Do not use this column for
    calculations until it is populated.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT")
        timeframe: Timeframe interval (e.g., "1m", "5m", "1h", "4h", "1d")
        limit: Maximum number of recent bars to return (optional)
        start: Start date in YYYY-MM-DD format (optional). Alias: start_date
        end: End date in YYYY-MM-DD format (optional). Alias: end_date
        start_date: Alias for start (recommended for clarity)
        end_date: Alias for end (recommended for clarity)
        output_dir: Directory to save CSV files (optional)
        index_type: DEPRECATED - Use pandas operations directly
        auto_fill_gaps: Automatically fill detected gaps with authentic Binance API data (default: True)
        instrument_type: Instrument type - "spot" or "futures-um" (both support 715 symbols, default: "spot")
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
        - funding_rate: Funding rate (⚠️ NULL in v3.2.0, will be populated in v3.3.0)

    Raises:
        ValueError: If both 'start' and 'start_date' specified, or both 'end' and 'end_date' specified
        ValueError: If symbol is not supported (with suggestions for correction)
        ValueError: If timeframe is not supported (with list of supported timeframes)
        ValueError: If date format is invalid (expected YYYY-MM-DD)
        ValueError: If instrument_type is invalid (must be "spot" or "futures-um")

    Examples:
        # Simple spot data fetching (default)
        df = fetch_data("BTCUSDT", "1h", limit=1000)

        # Fetch futures data (715 symbols available)
        df = fetch_data("BTCUSDT", "1h", limit=1000, instrument_type="futures-um")

        # Standard pandas operations for analysis
        returns = df['close'].pct_change()                    # Returns calculation
        rolling_vol = df['close'].rolling(20).std()           # Rolling volatility
        df_resampled = df.set_index('date').resample('4H').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum'
        })  # OHLCV resampling

        # Fetch specific date range (explicit form - recommended)
        df = fetch_data("ETHUSDT", "4h", start_date="2024-01-01", end_date="2024-06-30")

        # Fetch futures with date range
        df = fetch_data("SOLUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30",
                        instrument_type="futures-um")
    """
    # Validate and resolve timeframe parameters
    period = _validate_timeframe_parameters(timeframe, interval)

    # Validate deprecated index_type parameter
    _validate_index_type_parameter(index_type)

    # Validate and normalize date range parameters
    if start is not None and start_date is not None:
        raise ValueError(
            "Cannot specify both 'start' and 'start_date'. "
            "Use either 'start' OR 'start_date', not both."
        )
    if end is not None and end_date is not None:
        raise ValueError(
            "Cannot specify both 'end' and 'end_date'. Use either 'end' OR 'end_date', not both."
        )

    # Normalize: prefer explicit _date parameters
    start = start_date if start_date is not None else start
    end = end_date if end_date is not None else end

    # Validate symbol parameter (None check)
    if symbol is None:
        raise ValueError(
            "symbol parameter is required (cannot be None). "
            "Specify a trading pair (e.g., symbol='BTCUSDT')"
        )

    # Normalize symbol case (auto-uppercase for user convenience)
    symbol = symbol.upper()

    # Calculate date range from limit if needed
    start, end = _calculate_date_range_from_limit(limit, period, start, end)

    # Apply default date range if not specified
    start, end = _apply_default_date_range(start, end)

    # Upfront input validation (fast failure before expensive operations)
    _validate_instrument_type(instrument_type)  # ADR-0021: Validate instrument type first
    _validate_symbol(
        symbol, instrument_type=instrument_type
    )  # ADR-0021: Pass instrument type for context-aware validation
    _validate_timeframe_value(period)
    _validate_date_format(start, "start/start_date")
    _validate_date_format(end, "end/end_date")

    # Initialize collector and collect data
    collector = BinancePublicDataCollector(
        symbol=symbol,
        start_date=start,
        end_date=end,
        output_dir=output_dir,
        instrument_type=instrument_type,  # ADR-0021: Pass instrument type for URL routing
    )
    result = collector.collect_timeframe_data(period)

    # Process result or return empty DataFrame
    if result and "dataframe" in result:
        df = result["dataframe"]

        # Auto-fill gaps if enabled (delivers "zero gaps guarantee")
        df = _perform_gap_filling(result, auto_fill_gaps, period, df, instrument_type)

        # Apply limit and index_type
        return _apply_limit_and_index(df, limit, index_type)
    else:
        # Return empty DataFrame with expected columns
        return _create_empty_dataframe()


def download(
    symbol: str,
    timeframe: Optional[Union[str, SupportedTimeframe]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # Alias for start
    end_date: Optional[str] = None,  # Alias for end
    output_dir: Optional[Union[str, Path]] = None,
    index_type: Optional[Literal["datetime", "range", "auto"]] = None,  # Deprecated parameter
    auto_fill_gaps: bool = True,
    instrument_type: InstrumentType = "spot",  # ADR-0021: UM futures support
    *,
    interval: Optional[Union[str, SupportedTimeframe]] = None,
) -> pd.DataFrame:
    """Download cryptocurrency data with zero gaps guarantee.

    Provides familiar API patterns for intuitive data collection.
    By default, automatically detects and fills gaps using authentic Binance API data
    to deliver on the package's core promise of zero gaps.

    **NEW in v3.2.0**: USDT-margined perpetual futures support (715 symbols).

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        timeframe: Timeframe interval (default: "1h" if neither specified)
        start: Start date in YYYY-MM-DD format. Alias: start_date
        end: End date in YYYY-MM-DD format. Alias: end_date
        start_date: Alias for start (recommended for clarity)
        end_date: Alias for end (recommended for clarity)
        output_dir: Directory to save CSV files
        index_type: DEPRECATED - Use standard pandas operations instead
        auto_fill_gaps: Automatically fill detected gaps with authentic Binance API data (default: True)
        instrument_type: Instrument type - "spot" or "futures-um" (both support 715 symbols, default: "spot")
        interval: Legacy parameter name for timeframe (deprecated)

    Returns:
        pd.DataFrame with complete OHLCV and microstructure data (gapless by default).
        Includes funding_rate column (⚠️ NULL in v3.2.0, populated in future release).

    Raises:
        ValueError: If instrument_type is invalid (must be "spot" or "futures-um")
        ValueError: If both 'start' and 'start_date' specified, or both 'end' and 'end_date' specified
        ValueError: If symbol is not supported (with suggestions for correction)
        ValueError: If timeframe is not supported (with list of supported timeframes)
        ValueError: If date format is invalid (expected YYYY-MM-DD)

    Warning:
        The funding_rate column exists but is NULL for all rows in v3.2.0.
        Funding rate data requires separate API endpoint (/fapi/v1/fundingRate)
        and will be implemented in v3.3.0. Do not rely on funding_rate values.

    Examples:
        # Simple spot data download (default)
        df = download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

        # Futures data download (NEW in v3.2.0)
        df = download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30",
                     instrument_type="futures-um")

        # Explicit form (recommended)
        df = download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")

        # Disable auto-fill if you want raw Vision archive data
        df = download("ETHUSDT", "4h", auto_fill_gaps=False)

        # Legacy interval parameter
        df = download("BTCUSDT", interval="1h")
    """
    # Apply default if neither parameter specified
    if timeframe is None and interval is None:
        timeframe = "1h"

    # Validate and normalize date range parameters
    if start is not None and start_date is not None:
        raise ValueError(
            "Cannot specify both 'start' and 'start_date'. "
            "Use either 'start' OR 'start_date', not both."
        )
    if end is not None and end_date is not None:
        raise ValueError(
            "Cannot specify both 'end' and 'end_date'. Use either 'end' OR 'end_date', not both."
        )

    # Normalize: prefer explicit _date parameters
    start = start_date if start_date is not None else start
    end = end_date if end_date is not None else end

    # Validate symbol parameter (None check)
    if symbol is None:
        raise ValueError(
            "symbol parameter is required (cannot be None). "
            "Specify a trading pair (e.g., symbol='BTCUSDT')"
        )

    # Normalize symbol case (auto-uppercase for user convenience)
    symbol = symbol.upper()

    return fetch_data(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        output_dir=output_dir,
        index_type=index_type,
        auto_fill_gaps=auto_fill_gaps,
        instrument_type=instrument_type,  # ADR-0021
        interval=interval,
    )


def download_multiple(
    symbols: List[str],
    timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    max_workers: int = 5,
    raise_on_partial_failure: bool = False,
    instrument_type: InstrumentType = "spot",  # ADR-0021
    **kwargs,
) -> dict[str, pd.DataFrame]:
    """Download historical data for multiple symbols concurrently.

    Executes concurrent downloads using ThreadPoolExecutor for network-bound
    operations. Returns dict mapping symbol → DataFrame.

    **NEW in v3.2.0**: Supports USDT-margined perpetual futures (715 symbols).

    Args:
        symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"])
        timeframe: Candle interval (e.g., "1h", "4h", "1d")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum bars per symbol
        max_workers: Maximum concurrent downloads (default: 5)
        raise_on_partial_failure: Raise error if any symbol fails (default: False)
        instrument_type: Instrument type - "spot" or "futures-um" (both support 715 symbols, default: "spot")
        **kwargs: Additional parameters passed to download()

    Returns:
        dict[str, pd.DataFrame]: Mapping of symbol → DataFrame
        Only includes successful downloads (failed symbols omitted unless raise_on_partial_failure=True)
        Each DataFrame includes funding_rate column (⚠️ NULL in v3.2.0, populated in future release)

    Raises:
        ValueError: If instrument_type is invalid
        ValueError: If symbols list is empty
        ValueError: If max_workers < 1
        ValueError: If all symbols fail
        ValueError: If raise_on_partial_failure=True and any symbol fails

    Warning:
        The funding_rate column exists but is NULL for all rows in v3.2.0.

    Examples:
        >>> # Download multiple spot symbols concurrently (default)
        >>> results = download_multiple(
        ...     symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01",
        ...     end_date="2024-06-30"
        ... )
        >>> len(results)
        3

        >>> # Download multiple futures symbols concurrently (NEW in v3.2.0)
        >>> futures = download_multiple(
        ...     symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01",
        ...     instrument_type="futures-um"
        ... )
        >>> len(futures)
        3

        >>> # With error handling (partial failure - some succeed)
        >>> results = download_multiple(
        ...     symbols=["BTCUSDT", "INVALID", "ETHUSDT"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01"
        ... )
        >>> len(results)
        2  # Only BTCUSDT and ETHUSDT succeeded

        >>> # Strict mode (fail fast on any error)
        >>> results = download_multiple(
        ...     symbols=["BTCUSDT", "INVALID"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01",
        ...     raise_on_partial_failure=True
        ... )
        # → Raises ValueError immediately on first failure
    """
    import warnings
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Input validation
    if not symbols:
        raise ValueError("symbols list cannot be empty")

    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    results: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    # Concurrent execution with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_symbol = {
            executor.submit(
                download,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                instrument_type=instrument_type,  # ADR-0021
                **kwargs,
            ): symbol
            for symbol in symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                errors[symbol] = str(e)

                # Fail fast mode
                if raise_on_partial_failure:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise ValueError(f"Download failed for {symbol}: {e}") from e

    # Handle complete failure
    if not results and errors:
        raise ValueError(f"All {len(symbols)} symbols failed. Errors: {errors}")

    # Log warnings for partial failures
    if errors:
        warnings.warn(
            f"Failed to download {len(errors)} symbols: {list(errors.keys())}. Errors: {errors}",
            UserWarning,
            stacklevel=2,
        )

    return results


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
        "name": "gapless-crypto-clickhouse",
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
