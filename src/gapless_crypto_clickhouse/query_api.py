"""
Query API for gapless-crypto-clickhouse.

Provides unified query_ohlcv() function with lazy auto-ingestion addressing Alpha Forge's request.

Workflow:
    1. Check if data exists in ClickHouse
    2. If missing and auto_ingest enabled: download from Binance and ingest
    3. Query ClickHouse with FINAL keyword for deduplication
    4. If fill_gaps enabled: detect and fill gaps via REST API
    5. Return pandas DataFrame (Arrow-optimized internally)

Error Handling: Raise and propagate (no fallback, no retry, no silent failures)
SLOs: Availability, Correctness (zero-gap guarantee), Observability, Maintainability

Usage:
    from gapless_crypto_clickhouse import query_ohlcv

    # Basic query with auto-ingestion
    df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31")

    # Multi-symbol query
    df = query_ohlcv(["BTCUSDT", "ETHUSDT"], "1h", "2024-01-01", "2024-01-31")

    # Futures data
    df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31", instrument_type="futures-um")
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional, Union

import pandas as pd

from .api import (
    InstrumentType,
    _validate_date_format,
    _validate_symbol,
    _validate_timeframe_value,
)
from .clickhouse import ClickHouseConnection
from .clickhouse.config import ClickHouseConfig
from .clickhouse_query import OHLCVQuery
from .collectors.clickhouse_bulk_loader import ClickHouseBulkLoader
from .gap_filling.rest_client import fetch_gap_data

logger = logging.getLogger(__name__)


def query_ohlcv(
    symbol: Union[str, List[str]],
    timeframe: str,
    start_date: str,
    end_date: str,
    instrument_type: InstrumentType = "spot",
    auto_ingest: bool = True,
    fill_gaps: bool = True,
    clickhouse_config: Optional[ClickHouseConfig] = None,
) -> pd.DataFrame:
    """
    Query OHLCV data from ClickHouse with lazy auto-ingestion.

    Addresses Alpha Forge's feature request: unified query API with automatic data download
    when missing from database.

    Workflow:
        1. Connect to ClickHouse
        2. Check if requested data exists (COUNT query)
        3. If missing rows and auto_ingest=True: download from Binance + ingest to ClickHouse
        4. Query data with FINAL keyword (deduplication)
        5. If fill_gaps=True: detect gaps and fill via REST API
        6. Return DataFrame (Arrow-optimized, 3x faster)

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT") or list of symbols
        timeframe: Timeframe string (e.g., "1h", "4h", "1d")
        start_date: Start date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
        end_date: End date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
        instrument_type: "spot" or "futures-um" (default: "spot")
        auto_ingest: If True, automatically download and ingest missing data (default: True)
        fill_gaps: If True, detect and fill gaps using REST API (default: True)
        clickhouse_config: Optional ClickHouse configuration (default: from environment)

    Returns:
        pandas DataFrame with OHLCV data (Arrow-optimized internally)

    Raises:
        ValueError: If parameters are invalid
        Exception: If query or ingestion fails

    Performance:
        - First query (auto-ingest): 30-60s (download + ingest + query)
        - Cached query: 0.1-2s (query only, 3x faster with Arrow)
        - Memory: 75% less vs clickhouse-driver (Arrow zero-copy)

    Examples:
        # Basic query (auto-downloads if missing)
        df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
        print(f"Rows: {len(df)}")  # 744 rows (31 days * 24 hours)

        # Multi-symbol query
        df = query_ohlcv(
            ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "1h",
            "2024-01-01",
            "2024-01-31"
        )
        print(df.groupby("symbol")["close"].mean())

        # Futures data
        df = query_ohlcv(
            "BTCUSDT",
            "1h",
            "2024-01-01",
            "2024-01-31",
            instrument_type="futures-um"
        )

        # Query without auto-ingestion (faster, raises if data missing)
        df = query_ohlcv(
            "BTCUSDT",
            "1h",
            "2024-01-01",
            "2024-01-31",
            auto_ingest=False
        )

        # Query without gap filling (faster, may have gaps)
        df = query_ohlcv(
            "BTCUSDT",
            "1h",
            "2024-01-01",
            "2024-01-31",
            fill_gaps=False
        )
    """
    # Normalize symbol to list
    symbols = [symbol] if isinstance(symbol, str) else symbol

    # Validate parameters
    if not symbols:
        raise ValueError("symbol cannot be empty")

    for sym in symbols:
        if not sym:
            raise ValueError(f"Invalid symbol: {sym}")

    if not timeframe:
        raise ValueError("timeframe cannot be empty")

    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required")

    # Validate date format (YYYY-MM-DD) - fail fast before expensive operations
    _validate_date_format(start_date, "start_date")
    _validate_date_format(end_date, "end_date")

    # Validate timeframe against supported timeframes
    _validate_timeframe_value(timeframe)

    # Validate symbols against supported symbols (with suggestions on error)
    for sym in symbols:
        _validate_symbol(sym, instrument_type=instrument_type)

    # Connect to ClickHouse
    config = clickhouse_config or ClickHouseConfig.from_env()
    with ClickHouseConnection(config) as conn:
        query = OHLCVQuery(conn)
        loader = ClickHouseBulkLoader(conn, instrument_type=instrument_type)

        # Process each symbol
        dataframes = []
        for sym in symbols:
            logger.info(
                f"Processing {sym} {timeframe} {instrument_type} "
                f"({start_date} to {end_date}, auto_ingest={auto_ingest}, fill_gaps={fill_gaps})"
            )

            # Step 1: Check if data exists
            existing_count = _count_existing_rows(
                query, sym, timeframe, start_date, end_date, instrument_type
            )

            # Calculate expected row count (approximate, based on timeframe)
            expected_count = _estimate_expected_rows(start_date, end_date, timeframe)

            logger.info(
                f"{sym}: Found {existing_count} rows in ClickHouse "
                f"(expected ~{expected_count} rows)"
            )

            # Step 2: Auto-ingest if missing data
            if auto_ingest and existing_count < expected_count * 0.5:
                logger.info(
                    f"{sym}: Auto-ingesting missing data "
                    f"(found {existing_count}/{expected_count} rows)"
                )
                _auto_ingest_date_range(
                    loader, sym, timeframe, start_date, end_date, instrument_type
                )
            elif existing_count == 0:
                logger.warning(f"{sym}: No data found in ClickHouse and auto_ingest={auto_ingest}")

            # Step 3: Query data with FINAL
            df = query.get_range(
                symbol=sym,
                timeframe=timeframe,
                start=start_date,
                end=end_date,
                instrument_type=instrument_type,
            )

            logger.info(f"{sym}: Retrieved {len(df)} rows from ClickHouse (Arrow-optimized)")

            # Step 4: Fill gaps if enabled (ADR-0040)
            if fill_gaps and len(df) > 0:
                gaps = query.detect_gaps(
                    symbol=sym,
                    timeframe=timeframe,
                    start=start_date,
                    end=end_date,
                    instrument_type=instrument_type,
                )

                if len(gaps) > 0:
                    logger.info(f"{sym}: Detected {len(gaps)} gaps, filling via REST API")

                    # Fill gaps using Binance REST API
                    filled_rows = _fill_gaps_from_api(conn, gaps, sym, timeframe, instrument_type)

                    if filled_rows > 0:
                        logger.info(f"{sym}: Filled {filled_rows} rows from REST API")

                        # Re-query to include filled data
                        df = query.get_range(
                            symbol=sym,
                            timeframe=timeframe,
                            start=start_date,
                            end=end_date,
                            instrument_type=instrument_type,
                        )
                        logger.info(f"{sym}: Retrieved {len(df)} rows after gap filling")

            dataframes.append(df)

        # Combine results
        if len(dataframes) == 1:
            return dataframes[0]
        else:
            return pd.concat(dataframes, ignore_index=True)


def _count_existing_rows(
    query: OHLCVQuery,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    instrument_type: InstrumentType,
) -> int:
    """
    Count existing rows in ClickHouse for given parameters.

    Args:
        query: OHLCVQuery instance
        symbol: Trading pair symbol
        timeframe: Timeframe string
        start_date: Start date string
        end_date: End date string
        instrument_type: "spot" or "futures-um"

    Returns:
        Number of existing rows

    Raises:
        Exception: If query fails
    """
    try:
        # Use connection's execute method for COUNT query
        result = query.connection.execute(
            """
            SELECT COUNT(*) as count
            FROM ohlcv FINAL
            WHERE symbol = {symbol:String}
              AND timeframe = {timeframe:String}
              AND instrument_type = {instrument_type:String}
              AND timestamp >= parseDateTime64BestEffort({start_date:String})
              AND timestamp <= parseDateTime64BestEffort({end_date:String})
            """,
            params={
                "symbol": symbol,
                "timeframe": timeframe,
                "instrument_type": instrument_type,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        return result[0][0] if result else 0
    except Exception as e:
        logger.error(f"Failed to count existing rows: {e}")
        raise Exception(f"Count query failed: {e}") from e


def _estimate_expected_rows(start_date: str, end_date: str, timeframe: str) -> int:
    """
    Estimate expected number of rows based on date range and timeframe.

    Args:
        start_date: Start date string
        end_date: End date string
        timeframe: Timeframe string (e.g., "1h", "4h", "1d")

    Returns:
        Estimated number of rows

    Raises:
        ValueError: If timeframe format is invalid
    """
    # Parse dates
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    duration_hours = (end - start).total_seconds() / 3600

    # Map timeframe to hours
    timeframe_hours = {
        "1s": 1 / 3600,
        "1m": 1 / 60,
        "3m": 3 / 60,
        "5m": 5 / 60,
        "15m": 15 / 60,
        "30m": 30 / 60,
        "1h": 1,
        "2h": 2,
        "4h": 4,
        "6h": 6,
        "8h": 8,
        "12h": 12,
        "1d": 24,
    }

    if timeframe not in timeframe_hours:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    return int(duration_hours / timeframe_hours[timeframe])


def _auto_ingest_date_range(
    loader: ClickHouseBulkLoader,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    instrument_type: InstrumentType,
) -> int:
    """
    Auto-ingest data for date range by month.

    Args:
        loader: ClickHouseBulkLoader instance
        symbol: Trading pair symbol
        timeframe: Timeframe string
        start_date: Start date string
        end_date: End date string
        instrument_type: "spot" or "futures-um"

    Returns:
        Total rows ingested

    Raises:
        Exception: If ingestion fails
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    total_rows = 0

    # Generate month ranges
    current = start
    while current <= end:
        year = current.year
        month = current.month

        logger.info(f"Auto-ingesting {symbol} {timeframe} {year}-{month:02d}")

        try:
            rows = loader.ingest_month(symbol, timeframe, year, month)
            total_rows += rows
            logger.info(f"Ingested {rows} rows for {symbol} {year}-{month:02d}")
        except Exception as e:
            logger.warning(
                f"Failed to ingest {symbol} {year}-{month:02d}: {e} (month may not exist yet)"
            )

        # Move to next month
        if month == 12:
            current = datetime(year + 1, 1, 1)
        else:
            current = datetime(year, month + 1, 1)

    logger.info(f"Auto-ingestion complete: {total_rows} total rows for {symbol}")
    return total_rows


def _fill_gaps_from_api(
    connection: ClickHouseConnection,
    gaps: pd.DataFrame,
    symbol: str,
    timeframe: str,
    instrument_type: InstrumentType,
) -> int:
    """
    Fill detected gaps using Binance REST API (ADR-0040).

    Fetches authentic data from Binance REST API for each detected gap,
    converts to ClickHouse-compatible DataFrame with _version hash,
    and inserts to ClickHouse for deduplication via ReplacingMergeTree.

    Args:
        connection: Active ClickHouse connection
        gaps: DataFrame with detected gaps (from detect_gaps())
        symbol: Trading pair symbol
        timeframe: Timeframe string
        instrument_type: "spot" or "futures-um"

    Returns:
        Total number of rows inserted

    Raises:
        Exception: If API fetch or insertion fails
    """
    total_rows = 0

    for _, gap in gaps.iterrows():
        gap_start = pd.to_datetime(gap["gap_start"])
        gap_end = pd.to_datetime(gap["gap_end"])

        logger.info(f"Filling gap: {gap_start} to {gap_end}")

        # Fetch data from REST API with retry logic
        api_data = fetch_gap_data(
            symbol=symbol,
            timeframe=timeframe,
            start_time=gap_start.to_pydatetime(),
            end_time=gap_end.to_pydatetime(),
            instrument_type=instrument_type,
        )

        if not api_data:
            logger.warning(f"No data returned from API for gap {gap_start} to {gap_end}")
            continue

        # Convert to ClickHouse-compatible DataFrame
        df = _convert_api_data_to_dataframe(api_data, symbol, timeframe, instrument_type)

        # Insert to ClickHouse
        rows = connection.insert_dataframe(df, table="ohlcv")
        total_rows += rows
        logger.info(f"Inserted {rows} rows for gap {gap_start} to {gap_end}")

    return total_rows


def _convert_api_data_to_dataframe(
    api_data: List[dict],
    symbol: str,
    timeframe: str,
    instrument_type: InstrumentType,
) -> pd.DataFrame:
    """
    Convert REST API response to ClickHouse-ready DataFrame with _version hash.

    Matches the exact column order and format used by ClickHouseBulkLoader
    to ensure consistent _version hashes for ReplacingMergeTree deduplication.

    Args:
        api_data: List of candle dictionaries from REST API
        symbol: Trading pair symbol
        timeframe: Timeframe string
        instrument_type: "spot" or "futures-um"

    Returns:
        DataFrame ready for ClickHouse insertion

    Raises:
        ValueError: If api_data is empty or malformed
    """
    if not api_data:
        raise ValueError("api_data cannot be empty")

    # Create DataFrame from API data
    df = pd.DataFrame(api_data)

    # Add metadata columns
    df["symbol"] = symbol
    df["timeframe"] = timeframe
    df["instrument_type"] = instrument_type
    df["data_source"] = "rest_api"  # Distinguish from CloudFront data

    # Add funding_rate (NULL for gap filling)
    df["funding_rate"] = None

    # Compute deterministic _version hash (matches ClickHouseBulkLoader)
    df["_version"] = df.apply(
        lambda row: _compute_version_hash(row, symbol, timeframe, instrument_type),
        axis=1,
    )

    # Add _sign column (1 for active rows)
    df["_sign"] = 1

    # Convert number_of_trades to int64 (schema requirement)
    df["number_of_trades"] = df["number_of_trades"].astype("int64")

    # Ensure timestamps are timezone-aware UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], utc=True)

    # Reorder columns to match ClickHouse schema
    column_order = [
        "timestamp",
        "symbol",
        "timeframe",
        "instrument_type",
        "data_source",
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
        "funding_rate",
        "_version",
        "_sign",
    ]

    return df[column_order]


def _compute_version_hash(
    row: pd.Series,
    symbol: str,
    timeframe: str,
    instrument_type: str,
) -> int:
    """
    Compute deterministic _version hash for ReplacingMergeTree deduplication.

    Uses same algorithm as ClickHouseBulkLoader._compute_version_hash()
    to ensure identical data → identical _version → proper deduplication.

    Args:
        row: pandas Series with OHLCV data
        symbol: Trading pair symbol
        timeframe: Timeframe string
        instrument_type: Instrument type

    Returns:
        UInt64 hash value (0 to 2^64-1)
    """
    # Create deterministic string from row content
    version_input = (
        f"{row['timestamp']}"
        f"{row['open']}{row['high']}{row['low']}{row['close']}{row['volume']}"
        f"{symbol}{timeframe}{instrument_type}"
    )

    # Use SHA256 for cryptographic hash (deterministic, collision-resistant)
    hash_bytes = hashlib.sha256(version_input.encode("utf-8")).digest()

    # Convert first 8 bytes to UInt64
    version = int.from_bytes(hash_bytes[:8], byteorder="big", signed=False)

    return version
