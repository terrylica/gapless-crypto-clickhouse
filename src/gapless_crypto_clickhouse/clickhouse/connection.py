"""
ClickHouse connection management for gapless-crypto-data v4.0.0.

Provides context-managed connection to ClickHouse using clickhouse-driver.
Replaces QuestDBConnection (ADR-0003) for future-proofing and ecosystem maturity.

Error Handling: Raise and propagate (no fallback, no retry, no silent failures)
SLOs: Availability (connection health checks), Correctness (query validation),
      Observability (connection logging), Maintainability (standard client)

Usage:
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    with ClickHouseConnection() as conn:
        result = conn.execute("SELECT 1")
        print(result)  # [(1,)]
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from clickhouse_driver import Client
from clickhouse_driver.errors import Error as ClickHouseError

from .config import ClickHouseConfig

logger = logging.getLogger(__name__)


class ClickHouseConnection:
    """
    Context-managed ClickHouse connection.

    Provides execute() for queries and insert_dataframe() for bulk inserts.
    Follows same pattern as QuestDBConnection for consistency.

    Attributes:
        config: ClickHouse configuration
        client: clickhouse-driver Client instance

    Error Handling:
        - Connection failures raise ClickHouseError
        - Query failures raise ClickHouseError
        - No retries, no fallbacks (raise and propagate policy)

    Example:
        with ClickHouseConnection() as conn:
            # Execute query
            result = conn.execute("SELECT * FROM ohlcv LIMIT 10")

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
            ClickHouseError: If connection fails

        Example:
            # Default configuration (localhost)
            conn = ClickHouseConnection()

            # Custom configuration
            config = ClickHouseConfig(host="clickhouse.example.com")
            conn = ClickHouseConnection(config)
        """
        self.config = config or ClickHouseConfig.from_env()
        self.config.validate()

        logger.info(f"Initializing ClickHouse connection: {self.config.host}:{self.config.port}")

        try:
            self.client = Client(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                # Performance settings
                settings={
                    "use_numpy": True,  # Optimize for pandas integration
                    "max_block_size": 100000,  # Batch size for queries
                },
            )
        except ClickHouseError as e:
            raise ClickHouseError(
                f"Failed to connect to ClickHouse at {self.config.host}:{self.config.port}: {e}"
            ) from e

    def __enter__(self) -> "ClickHouseConnection":
        """Context manager entry."""
        self.health_check()
        logger.debug("ClickHouse connection opened")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit (cleanup)."""
        if self.client:
            self.client.disconnect()
            logger.debug("ClickHouse connection closed")

    def health_check(self) -> None:
        """
        Verify ClickHouse connection is alive.

        Raises:
            ClickHouseError: If health check fails

        Example:
            conn = ClickHouseConnection()
            conn.health_check()  # Raises if connection dead
        """
        try:
            result = self.client.execute("SELECT 1")
            if result != [(1,)]:
                raise ClickHouseError(f"Health check failed: unexpected result {result}")
            logger.debug("ClickHouse health check passed")
        except ClickHouseError as e:
            raise ClickHouseError(f"ClickHouse health check failed: {e}") from e

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Tuple[Any, ...]]:
        """
        Execute SQL query with parameter substitution.

        Args:
            query: SQL query string (use %(name)s placeholders)
            params: Query parameters (dict mapping placeholder names to values)

        Returns:
            List of result tuples

        Raises:
            ClickHouseError: If query execution fails

        Example:
            # Simple query
            result = conn.execute("SELECT 1")  # [(1,)]

            # Parameterized query
            result = conn.execute(
                "SELECT * FROM ohlcv WHERE symbol = %(symbol)s",
                params={'symbol': 'BTCUSDT'}
            )
        """
        try:
            logger.debug(f"Executing query: {query[:100]}...")
            result = self.client.execute(query, params or {})
            logger.debug(f"Query returned {len(result)} rows")
            return result
        except ClickHouseError as e:
            raise ClickHouseError(f"Query execution failed: {query[:100]}...\nError: {e}") from e

    def query_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """
        Execute SQL query and return results as pandas DataFrame.

        Args:
            query: SQL query string (use %(name)s placeholders)
            params: Query parameters (dict mapping placeholder names to values)

        Returns:
            pandas DataFrame with query results

        Raises:
            ClickHouseError: If query execution fails

        Example:
            # Simple query
            df = conn.query_dataframe("SELECT * FROM ohlcv FINAL LIMIT 10")

            # Parameterized query
            df = conn.query_dataframe(
                "SELECT * FROM ohlcv FINAL WHERE symbol = %(symbol)s",
                params={'symbol': 'BTCUSDT'}
            )
        """
        try:
            logger.debug(f"Executing query (DataFrame): {query[:100]}...")
            df = self.client.query_dataframe(query, params or {})
            logger.debug(f"Query returned {len(df)} rows")
            return df
        except ClickHouseError as e:
            raise ClickHouseError(f"Query execution failed: {query[:100]}...\\nError: {e}") from e

    def insert_dataframe(self, df: pd.DataFrame, table: str) -> int:
        """
        Bulk insert DataFrame to ClickHouse table.

        Args:
            df: pandas DataFrame with data to insert
            table: Target table name

        Returns:
            Number of rows inserted

        Raises:
            ClickHouseError: If insert fails
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

            # ClickHouse driver expects DataFrame columns to match table schema
            # Use INSERT INTO table VALUES format
            query = f"INSERT INTO {table} VALUES"

            self.client.insert_dataframe(query, df)

            logger.info(f"Successfully inserted {len(df)} rows to {table}")
            return len(df)

        except ClickHouseError as e:
            raise ClickHouseError(
                f"Bulk insert failed for table {table} ({len(df)} rows): {e}"
            ) from e
        except ValueError as e:
            raise ValueError(f"Invalid DataFrame schema for table {table}: {e}") from e
