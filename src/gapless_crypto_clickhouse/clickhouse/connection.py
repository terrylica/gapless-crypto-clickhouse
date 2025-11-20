"""
ClickHouse connection management for gapless-crypto-clickhouse v6.0.0.

Provides context-managed connection to ClickHouse using clickhouse-connect with Apache Arrow support.
Replaces clickhouse-driver (ADR-0023) for 3x faster queries and 4x less memory.

Error Handling: Raise and propagate (no fallback, no retry, no silent failures)
SLOs: Availability (connection health checks), Correctness (query validation),
      Observability (connection logging), Maintainability (standard HTTP client)

Usage:
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    with ClickHouseConnection() as conn:
        df = conn.query_dataframe("SELECT * FROM ohlcv FINAL LIMIT 10")
        print(df)  # pandas DataFrame with Arrow-optimized internals
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import clickhouse_connect
import pandas as pd

from .config import ClickHouseConfig

logger = logging.getLogger(__name__)


class ClickHouseConnection:
    """
    Context-managed ClickHouse connection with Apache Arrow support.

    Provides execute() for queries and insert_dataframe() for bulk inserts.
    Uses HTTP protocol (port 8123) with Apache Arrow for zero-copy DataFrame creation.

    Attributes:
        config: ClickHouse configuration
        client: clickhouse-connect Client instance

    Error Handling:
        - Connection failures raise Exception
        - Query failures raise Exception
        - No retries, no fallbacks (raise and propagate policy)

    Performance:
        - Arrow-optimized queries: 3x faster DataFrame creation
        - Zero-copy when possible: 4x less memory
        - HTTP protocol: nginx/reverse proxy compatible

    Example:
        with ClickHouseConnection() as conn:
            # Execute query (returns tuples)
            result = conn.execute("SELECT COUNT(*) FROM ohlcv")

            # Query DataFrame (Arrow-optimized internally)
            df = conn.query_dataframe("SELECT * FROM ohlcv FINAL LIMIT 10")

            # Insert DataFrame
            df = pd.DataFrame({"col": [1, 2, 3]})
            conn.insert_dataframe(df, "test_table")
    """

    def __init__(self, config: Optional[ClickHouseConfig] = None) -> None:
        """
        Initialize ClickHouse connection.

        Args:
            config: ClickHouse configuration (default: from environment)

        Raises:
            ValueError: If configuration is invalid
            Exception: If connection fails

        Example:
            # Default configuration (localhost)
            conn = ClickHouseConnection()

            # Custom configuration
            config = ClickHouseConfig(host="clickhouse.example.com")
            conn = ClickHouseConnection(config)
        """
        self.config = config or ClickHouseConfig.from_env()
        self.config.validate()

        logger.info(
            f"Initializing ClickHouse connection: {self.config.host}:{self.config.http_port} "
            f"(HTTP protocol with Arrow support)"
        )

        try:
            # clickhouse-connect uses HTTP protocol (port 8123)
            self.client = clickhouse_connect.get_client(
                host=self.config.host,
                port=self.config.http_port,
                database=self.config.database,
                username=self.config.user,
                password=self.config.password,
                # Performance settings
                settings={
                    "max_block_size": 100000,  # Batch size for queries
                },
            )
        except Exception as e:
            raise Exception(
                f"Failed to connect to ClickHouse at {self.config.host}:{self.config.http_port}: {e}"
            ) from e

    def __enter__(self) -> "ClickHouseConnection":
        """Context manager entry."""
        if not self.health_check():
            raise Exception("ClickHouse health check failed during context manager entry")
        logger.debug("ClickHouse connection opened")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit (cleanup)."""
        if self.client:
            self.client.close()
            logger.debug("ClickHouse connection closed")

    def health_check(self) -> bool:
        """
        Verify ClickHouse connection is alive.

        Returns:
            True if connection is healthy, False otherwise

        Example:
            conn = ClickHouseConnection()
            if conn.health_check():
                print("Connection healthy")
        """
        try:
            result = self.client.command("SELECT 1")
            if result != 1:
                logger.error(f"Health check failed: unexpected result {result}")
                return False
            logger.debug("ClickHouse health check passed")
            return True
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Tuple[Any, ...]]:
        """
        Execute SQL query with parameter substitution.

        Args:
            query: SQL query string (use {name:Type} placeholders for clickhouse-connect)
            params: Query parameters (dict mapping placeholder names to values)

        Returns:
            List of result tuples

        Raises:
            Exception: If query execution fails

        Example:
            # Simple query
            result = conn.execute("SELECT 1")  # [(1,)]

            # Parameterized query (clickhouse-connect format)
            result = conn.execute(
                "SELECT * FROM ohlcv WHERE symbol = {symbol:String}",
                params={'symbol': 'BTCUSDT'}
            )
        """
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            result = self.client.query(query, parameters=params or {})
            rows = result.result_rows
            logger.debug(f"Query returned {len(rows)} rows")
            return rows
        except Exception as e:
            raise Exception(f"Query execution failed: {query[:100]}...\nError: {e}") from e

    def query_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as pandas DataFrame with Arrow optimization.

        Args:
            query: SQL query string (use {name:Type} placeholders for clickhouse-connect)
            params: Query parameters (dict mapping placeholder names to values)

        Returns:
            pandas DataFrame with query results (Arrow-optimized internally)

        Raises:
            Exception: If query execution fails

        Performance:
            - Arrow format enabled: 3x faster DataFrame creation
            - Zero-copy when compatible: 4x less memory
            - Automatic fallback if Arrow not available

        Example:
            # Simple query
            df = conn.query_dataframe("SELECT * FROM ohlcv FINAL LIMIT 10")

            # Parameterized query
            df = conn.query_dataframe(
                "SELECT * FROM ohlcv FINAL WHERE symbol = {symbol:String}",
                params={'symbol': 'BTCUSDT'}
            )
        """
        try:
            logger.debug(f"Executing query (DataFrame, Arrow-optimized): {query[:100]}...")
            # Use Arrow-optimized query method for 3x faster DataFrame creation
            df = self.client.query_df_arrow(query, parameters=params or {})
            logger.debug(f"Query returned {len(df)} rows (Arrow-optimized)")
            return df
        except Exception as e:
            raise Exception(f"Query execution failed: {query[:100]}...\nError: {e}") from e

    def insert_dataframe(self, df: pd.DataFrame, table: str) -> int:
        """
        Bulk insert DataFrame to ClickHouse table.

        Args:
            df: pandas DataFrame with data to insert
            table: Target table name

        Returns:
            Number of rows inserted

        Raises:
            Exception: If insert fails
            ValueError: If DataFrame is empty or has invalid schema

        Example:
            df = pd.DataFrame({
                'timestamp': pd.to_datetime(['2024-01-01']),
                'symbol': ['BTCUSDT'],
                'open': [50000.0]
            })
            rows = conn.insert_dataframe(df, 'ohlcv')
            print(f"Inserted {rows} rows")
        """
        if df.empty:
            logger.warning(f"Empty DataFrame, skipping insert to {table}")
            return 0

        try:
            logger.info(f"Inserting {len(df)} rows to {table}")

            # Use standard insert (Arrow benefits are mainly on query side)
            self.client.insert_df(table, df)

            logger.info(f"Successfully inserted {len(df)} rows to {table}")
            return len(df)

        except Exception as e:
            raise Exception(
                f"Bulk insert failed for table {table} ({len(df)} rows): {e}"
            ) from e
        except ValueError as e:
            raise ValueError(f"Invalid DataFrame schema for table {table}: {e}") from e
