"""
ClickHouse query interface for gapless-crypto-data v4.0.0.

SQL query abstraction returning pandas DataFrames for backward compatibility.
Provides high-level methods for common OHLCV queries with automatic connection management.

Architecture:
- ClickHouse native protocol (port 9000) for queries
- pandas DataFrame return type for compatibility with v3.x API
- SQL-based filtering and aggregation with FINAL keyword for deduplication

Error Handling:
- Raise and propagate query failures (no fallbacks)
- Raise and propagate connection failures (no retries)
- Invalid parameters raise ValueError

SLOs:
- Availability: Query failures propagate to caller
- Correctness: Zero-gap guarantee via deterministic versioning + FINAL keyword
- Observability: Query execution logged at DEBUG level
- Maintainability: Standard SQL queries, pandas DataFrame output

Usage:
    from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    with ClickHouseConnection() as conn:
        query = OHLCVQuery(conn)

        # Get latest 100 bars
        df = query.get_latest("BTCUSDT", "1h", limit=100)

        # Get date range
        df = query.get_range(
            "ETHUSDT", "1h",
            start="2024-01-01",
            end="2024-12-31"
        )

        # Multi-symbol comparison
        df = query.get_multi_symbol(
            ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "1h",
            start="2024-01-01",
            end="2024-01-31"
        )
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from clickhouse_driver.errors import Error as ClickHouseError

from .clickhouse.connection import ClickHouseConnection

logger = logging.getLogger(__name__)


class OHLCVQuery:
    """
    High-level query interface for OHLCV data in ClickHouse.

    Provides pandas DataFrame-based API for querying time-series OHLCV data
    with automatic connection management and SQL query construction.

    Attributes:
        connection: ClickHouse connection for native protocol queries

    Error Handling:
        - Connection failures raise ConnectionError
        - Query failures raise ClickHouseError
        - Invalid parameters raise ValueError
        - No retries, no fallbacks

    Performance:
        - Query latency: <1s for typical OHLCV ranges (1M rows)
        - FINAL keyword overhead: 10-30% (required for deduplication)
        - Result set: Materialized to pandas DataFrame
        - Memory: Entire result loaded into memory

    Examples:
        # Get latest data
        with ClickHouseConnection() as conn:
            query = OHLCVQuery(conn)
            df = query.get_latest("BTCUSDT", "1h", limit=1000)
            print(f"Latest close: {df.iloc[-1]['close']}")

        # Date range query
        with ClickHouseConnection() as conn:
            query = OHLCVQuery(conn)
            df = query.get_range(
                "ETHUSDT", "1h",
                start="2024-01-01",
                end="2024-12-31"
            )
            print(f"Total bars: {len(df)}")

        # Multi-symbol query
        with ClickHouseConnection() as conn:
            query = OHLCVQuery(conn)
            df = query.get_multi_symbol(
                ["BTCUSDT", "ETHUSDT"],
                "1h",
                start="2024-01-01",
                end="2024-01-31"
            )
            print(df.groupby("symbol")["close"].mean())
    """

    def __init__(self, connection: ClickHouseConnection) -> None:
        """
        Initialize OHLCV query interface.

        Args:
            connection: Active ClickHouse connection

        Raises:
            ValueError: If connection is invalid
        """
        if not isinstance(connection, ClickHouseConnection):
            raise ValueError(f"Expected ClickHouseConnection, got {type(connection).__name__}")

        self.connection = connection
        logger.debug("OHLCVQuery interface initialized")

    def get_latest(
        self, symbol: str, timeframe: str, limit: int = 1000, instrument_type: str = "spot"
    ) -> pd.DataFrame:
        """
        Get latest N bars for a symbol and timeframe.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "1h")
            limit: Number of bars to retrieve (default: 1000)
            instrument_type: Instrument type ("spot" or "futures"), defaults to "spot"

        Returns:
            pandas DataFrame with OHLCV data, sorted by timestamp (oldest first)

        Raises:
            ValueError: If parameters are invalid
            ClickHouseError: If query fails
            ConnectionError: If database connection fails

        Example:
            # Spot data (default)
            df = query.get_latest("BTCUSDT", "1h", limit=100)

            # Futures data
            df = query.get_latest("BTCUSDT", "1h", limit=100, instrument_type="futures")

            print(df.columns)
            # ['timestamp', 'symbol', 'timeframe', 'instrument_type', 'open', 'high', 'low',
            #  'close', 'volume', 'close_time', 'quote_asset_volume',
            #  'number_of_trades', 'taker_buy_base_asset_volume',
            #  'taker_buy_quote_asset_volume', 'data_source']
        """
        # Validate inputs
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        if not timeframe:
            raise ValueError("Timeframe cannot be empty")
        if limit <= 0:
            raise ValueError(f"Limit must be positive, got {limit}")
        if instrument_type not in ("spot", "futures"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. Must be 'spot' or 'futures'"
            )

        symbol = symbol.upper()

        sql = """
            SELECT
                timestamp,
                symbol,
                timeframe,
                instrument_type,
                open,
                high,
                low,
                close,
                volume,
                close_time,
                quote_asset_volume,
                number_of_trades,
                taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume,
                data_source
            FROM ohlcv FINAL
            WHERE symbol = %(symbol)s
              AND timeframe = %(timeframe)s
              AND instrument_type = %(instrument_type)s
            ORDER BY timestamp DESC
            LIMIT %(limit)s
        """

        logger.debug(f"Querying latest {limit} bars for {symbol} {timeframe} ({instrument_type})")

        try:
            # Execute query
            df = self.connection.query_dataframe(
                sql,
                params={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "instrument_type": instrument_type,
                    "limit": limit,
                },
            )

            # Reverse to chronological order (oldest first)
            df = df.iloc[::-1].reset_index(drop=True)

            logger.info(f"Retrieved {len(df)} bars for {symbol} {timeframe} ({instrument_type})")
            return df

        except ClickHouseError as e:
            raise ClickHouseError(
                f"Query failed for {symbol} {timeframe} ({instrument_type}): {e}"
            ) from e

    def get_range(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        instrument_type: str = "spot",
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a specific date range.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "1h")
            start: Start date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
            end: End date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
            instrument_type: Instrument type ("spot" or "futures"), defaults to "spot"

        Returns:
            pandas DataFrame with OHLCV data, sorted by timestamp

        Raises:
            ValueError: If parameters are invalid
            ClickHouseError: If query fails
            ConnectionError: If database connection fails

        Example:
            # Spot data (default)
            df = query.get_range(
                "ETHUSDT", "1h",
                start="2024-01-01",
                end="2024-01-31"
            )

            # Futures data
            df = query.get_range(
                "BTCUSDT", "1h",
                start="2024-01-01",
                end="2024-01-31",
                instrument_type="futures"
            )

            print(f"Total bars: {len(df)}")
            print(f"First: {df.iloc[0]['timestamp']}")
            print(f"Last: {df.iloc[-1]['timestamp']}")
        """
        # Validate inputs
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        if not timeframe:
            raise ValueError("Timeframe cannot be empty")
        if instrument_type not in ("spot", "futures"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. Must be 'spot' or 'futures'"
            )

        symbol = symbol.upper()

        # Parse dates (validate format)
        try:
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
        except Exception as e:
            raise ValueError(
                f"Invalid date format. Expected 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS', got start='{start}', end='{end}'"
            ) from e

        if start_dt >= end_dt:
            raise ValueError(f"Start date must be before end date, got start={start}, end={end}")

        sql = """
            SELECT
                timestamp,
                symbol,
                timeframe,
                instrument_type,
                open,
                high,
                low,
                close,
                volume,
                close_time,
                quote_asset_volume,
                number_of_trades,
                taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume,
                data_source
            FROM ohlcv FINAL
            WHERE symbol = %(symbol)s
              AND timeframe = %(timeframe)s
              AND instrument_type = %(instrument_type)s
              AND timestamp >= toDateTime(%(start)s)
              AND timestamp <= toDateTime(%(end)s)
            ORDER BY timestamp ASC
        """

        logger.debug(f"Querying {symbol} {timeframe} ({instrument_type}) from {start} to {end}")

        try:
            df = self.connection.query_dataframe(
                sql,
                params={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "instrument_type": instrument_type,
                    "start": start,
                    "end": end,
                },
            )

            logger.info(
                f"Retrieved {len(df)} bars for {symbol} {timeframe} ({instrument_type}) ({start} to {end})"
            )
            return df

        except ClickHouseError as e:
            raise ClickHouseError(
                f"Query failed for {symbol} {timeframe} ({instrument_type}) {start} to {end}: {e}"
            ) from e

    def get_multi_symbol(
        self,
        symbols: List[str],
        timeframe: str,
        start: str,
        end: str,
        instrument_type: str = "spot",
    ) -> pd.DataFrame:
        """
        Get OHLCV data for multiple symbols in a date range.

        Useful for multi-symbol analysis and comparison.

        Args:
            symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframe: Timeframe string (e.g., "1h")
            start: Start date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
            end: End date in "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS" format
            instrument_type: Instrument type ("spot" or "futures"), defaults to "spot"

        Returns:
            pandas DataFrame with OHLCV data for all symbols, sorted by symbol then timestamp

        Raises:
            ValueError: If parameters are invalid
            ClickHouseError: If query fails
            ConnectionError: If database connection fails

        Example:
            # Spot data (default)
            df = query.get_multi_symbol(
                ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
                "1h",
                start="2024-01-01",
                end="2024-01-31"
            )

            # Futures data
            df = query.get_multi_symbol(
                ["BTCUSDT", "ETHUSDT"],
                "1h",
                start="2024-01-01",
                end="2024-01-31",
                instrument_type="futures"
            )

            # Group by symbol for analysis
            summary = df.groupby("symbol").agg({
                "close": ["mean", "min", "max"],
                "volume": "sum"
            })
            print(summary)
        """
        # Validate inputs
        if not symbols:
            raise ValueError("Symbols list cannot be empty")
        if not timeframe:
            raise ValueError("Timeframe cannot be empty")
        if instrument_type not in ("spot", "futures"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. Must be 'spot' or 'futures'"
            )

        symbols = [s.upper() for s in symbols]

        # Parse dates
        try:
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
        except Exception as e:
            raise ValueError(
                f"Invalid date format. Expected 'YYYY-MM-DD', got start='{start}', end='{end}'"
            ) from e

        if start_dt >= end_dt:
            raise ValueError(f"Start date must be before end date, got start={start}, end={end}")

        # ClickHouse IN clause with array parameter
        sql = """
            SELECT
                timestamp,
                symbol,
                timeframe,
                instrument_type,
                open,
                high,
                low,
                close,
                volume,
                close_time,
                quote_asset_volume,
                number_of_trades,
                taker_buy_base_asset_volume,
                taker_buy_quote_asset_volume,
                data_source
            FROM ohlcv FINAL
            WHERE symbol IN %(symbols)s
              AND timeframe = %(timeframe)s
              AND instrument_type = %(instrument_type)s
              AND timestamp >= toDateTime(%(start)s)
              AND timestamp <= toDateTime(%(end)s)
            ORDER BY symbol ASC, timestamp ASC
        """

        logger.debug(
            f"Querying {len(symbols)} symbols ({', '.join(symbols)}) {timeframe} ({instrument_type}) from {start} to {end}"
        )

        try:
            df = self.connection.query_dataframe(
                sql,
                params={
                    "symbols": symbols,
                    "timeframe": timeframe,
                    "instrument_type": instrument_type,
                    "start": start,
                    "end": end,
                },
            )

            logger.info(
                f"Retrieved {len(df)} bars for {len(symbols)} symbols ({instrument_type}) ({start} to {end})"
            )
            return df

        except ClickHouseError as e:
            raise ClickHouseError(
                f"Multi-symbol query failed for {timeframe} ({instrument_type}) {start} to {end}: {e}"
            ) from e

    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute raw SQL query and return results as DataFrame.

        For advanced queries not covered by high-level methods.

        Args:
            sql: SQL query string (use %(name)s placeholders for parameters)
            params: Query parameters dict (optional)

        Returns:
            pandas DataFrame with query results

        Raises:
            ValueError: If SQL is empty
            ClickHouseError: If query fails
            ConnectionError: If database connection fails

        Security:
            Always use parameterized queries (%(name)s placeholders) to prevent SQL injection.
            NEVER concatenate user input directly into SQL strings.

        Example:
            # Parameterized query (SAFE)
            df = query.execute_sql(
                "SELECT * FROM ohlcv FINAL WHERE symbol = %(symbol)s AND close > %(price)s LIMIT 10",
                {"symbol": "BTCUSDT", "price": 50000.0}
            )

            # Direct string concatenation (UNSAFE - don't do this)
            # df = query.execute_sql(f"SELECT * FROM ohlcv WHERE symbol = '{user_input}'")
        """
        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")

        logger.debug(f"Executing raw SQL query: {sql[:100]}...")

        try:
            df = self.connection.query_dataframe(sql, params)

            logger.info(f"Raw SQL query returned {len(df)} rows")
            return df

        except ClickHouseError as e:
            raise ClickHouseError(f"Raw SQL query failed: {e}") from e

    def detect_gaps(
        self, symbol: str, timeframe: str, start: str, end: str, instrument_type: str = "spot"
    ) -> pd.DataFrame:
        """
        Detect timestamp gaps in OHLCV data using SQL sequence analysis.

        Uses ClickHouse window functions to find missing bars based on
        expected timeframe intervals.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Timeframe string (e.g., "1h")
            start: Start date in "YYYY-MM-DD" format
            end: End date in "YYYY-MM-DD" format
            instrument_type: Instrument type ("spot" or "futures"), defaults to "spot"

        Returns:
            pandas DataFrame with gap information:
            - gap_start: Timestamp where gap starts
            - gap_end: Timestamp where gap ends
            - expected_bars: Number of missing bars in gap

        Raises:
            ValueError: If parameters are invalid
            ClickHouseError: If query fails

        Example:
            gaps = query.detect_gaps("BTCUSDT", "1h", "2024-01-01", "2024-12-31")
            if gaps.empty:
                print("No gaps found!")
            else:
                print(f"Found {len(gaps)} gaps:")
                print(gaps)
        """
        # Map timeframe to seconds for gap detection
        timeframe_to_seconds = {
            "1s": 1,
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
            "6h": 21600,
            "8h": 28800,
            "12h": 43200,
            "1d": 86400,
            "3d": 259200,
            "1w": 604800,
            "1mo": 2592000,  # Approximate: 30 days
        }

        if timeframe not in timeframe_to_seconds:
            raise ValueError(f"Unsupported timeframe for gap detection: {timeframe}")
        if instrument_type not in ("spot", "futures"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. Must be 'spot' or 'futures'"
            )

        interval_seconds = timeframe_to_seconds[timeframe]
        symbol = symbol.upper()

        # SQL to detect gaps using lagInFrame window function
        sql = """
            WITH lagged AS (
                SELECT
                    timestamp,
                    lagInFrame(timestamp) OVER (ORDER BY timestamp) AS prev_timestamp
                FROM ohlcv FINAL
                WHERE symbol = %(symbol)s
                  AND timeframe = %(timeframe)s
                  AND instrument_type = %(instrument_type)s
                  AND timestamp >= toDateTime(%(start)s)
                  AND timestamp <= toDateTime(%(end)s)
            ),
            gaps AS (
                SELECT
                    prev_timestamp AS gap_start,
                    timestamp AS gap_end,
                    toFloat64(dateDiff('second', prev_timestamp, timestamp)) / %(interval_seconds)s AS bars_diff
                FROM lagged
                WHERE prev_timestamp != toDateTime(0)
            )
            SELECT
                gap_start,
                gap_end,
                bars_diff - 1 AS expected_bars
            FROM gaps
            WHERE bars_diff > 1
        """

        logger.debug(
            f"Detecting gaps for {symbol} {timeframe} ({instrument_type}) from {start} to {end}"
        )

        try:
            df = self.connection.query_dataframe(
                sql,
                params={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "instrument_type": instrument_type,
                    "start": start,
                    "end": end,
                    "interval_seconds": interval_seconds,
                },
            )

            if df.empty:
                logger.info(f"No gaps found for {symbol} {timeframe} ({instrument_type})")
            else:
                logger.warning(
                    f"Found {len(df)} gaps for {symbol} {timeframe} ({instrument_type}) "
                    f"(total missing bars: {df['expected_bars'].sum()})"
                )

            return df

        except ClickHouseError as e:
            raise ClickHouseError(
                f"Gap detection query failed for {symbol} {timeframe} ({instrument_type}): {e}"
            ) from e
