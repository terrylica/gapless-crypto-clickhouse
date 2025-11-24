"""E2E validation primitives for ClickHouse testing and production monitoring.

This module provides reusable validation functions used by both E2E test scripts
and production monitoring workflows. Extracted to eliminate duplication across
validation scripts (ADR-0036).

Functions:
    create_clickhouse_client: Create ClickHouse client with standard configuration
    validate_table_exists: Verify table exists in ClickHouse
    insert_test_data: Insert test data with error handling
    query_with_final: Query data with FINAL deduplication
    cleanup_test_data: Remove test data from table
    log_with_timestamp: Log messages with UTC timestamp
"""

from datetime import datetime, timezone
from typing import Any

import clickhouse_connect
import pandas as pd


def log_with_timestamp(message: str) -> None:
    """Print timestamped log message with UTC timezone.

    Args:
        message: Message to log

    Example:
        >>> log_with_timestamp("Starting validation")
        [2025-01-24 12:34:56 UTC] Starting validation
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def create_clickhouse_client(
    host: str,
    port: int,
    username: str,
    password: str,
    secure: bool = True,
    settings: dict[str, Any] | None = None,
) -> clickhouse_connect.driver.client.Client:
    """Create ClickHouse client with standard configuration.

    Args:
        host: ClickHouse server hostname
        port: ClickHouse server port (typically 8443 for Cloud)
        username: ClickHouse username
        password: ClickHouse password
        secure: Use TLS connection (default: True for Cloud)
        settings: Optional ClickHouse settings dict

    Returns:
        Connected ClickHouse client

    Raises:
        Exception: If connection fails

    Example:
        >>> client = create_clickhouse_client(
        ...     host="cloud.clickhouse.com",
        ...     port=8443,
        ...     username="default",
        ...     password="secret"
        ... )
    """
    client = clickhouse_connect.get_client(
        host=host,
        port=port,
        username=username,
        password=password,
        secure=secure,
        settings=settings or {},
    )
    return client


def validate_table_exists(client: clickhouse_connect.driver.client.Client, table_name: str) -> bool:
    """Verify table exists in ClickHouse.

    Args:
        client: Connected ClickHouse client
        table_name: Name of table to check

    Returns:
        True if table exists, False otherwise

    Example:
        >>> client = create_clickhouse_client(...)
        >>> exists = validate_table_exists(client, "ohlcv")
        >>> assert exists, "Table 'ohlcv' not found"
    """
    tables = client.command("SHOW TABLES")
    return table_name in tables


def insert_test_data(
    client: clickhouse_connect.driver.client.Client,
    table_name: str,
    test_df: pd.DataFrame,
) -> None:
    """Insert test data using pandas DataFrame.

    Uses clickhouse-connect's native DataFrame support (client.insert_df).

    Args:
        client: Connected ClickHouse client
        table_name: Target table name
        test_df: Pandas DataFrame with test data

    Raises:
        Exception: If insert fails

    Example:
        >>> test_df = pd.DataFrame({
        ...     "timestamp": [datetime.now()],
        ...     "symbol": ["TEST"],
        ...     "open": [100.0]
        ... })
        >>> insert_test_data(client, "ohlcv", test_df)
    """
    client.insert_df(table_name, test_df)


def query_with_final(
    client: clickhouse_connect.driver.client.Client,
    table_name: str,
    test_symbol: str,
) -> clickhouse_connect.driver.query.QueryResult:
    """Query data with FINAL deduplication.

    Args:
        client: Connected ClickHouse client
        table_name: Table to query
        test_symbol: Symbol to filter by

    Returns:
        QueryResult object with deduplicated rows

    Example:
        >>> result = query_with_final(client, "ohlcv", "TEST")
        >>> row_count = result.row_count
        >>> print(f"Found {row_count} deduplicated rows")
    """
    query = f"SELECT COUNT(*) as count FROM {table_name} FINAL WHERE symbol = '{test_symbol}'"
    result = client.query(query)
    return result


def cleanup_test_data(
    client: clickhouse_connect.driver.client.Client,
    table_name: str,
    test_symbol: str,
) -> None:
    """Remove test data from table.

    Args:
        client: Connected ClickHouse client
        table_name: Table to clean up
        test_symbol: Symbol to delete

    Raises:
        Exception: If cleanup fails (non-fatal, should be logged as warning)

    Example:
        >>> cleanup_test_data(client, "ohlcv", "TEST")
    """
    delete_query = f"DELETE FROM {table_name} WHERE symbol = '{test_symbol}'"
    client.command(delete_query)
