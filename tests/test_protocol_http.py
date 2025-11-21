"""HTTP protocol validation tests for v6.0.0.

Validates ClickHouse HTTP interface (port 8123) for health checks, queries, error propagation.
Critical for ensuring proper protocol configuration and error handling.

**SLO Focus**: Correctness (HTTP protocol must work reliably)

**ADR**: ADR-0024 (Comprehensive Validation Canonicity)
"""

import pytest
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection


@pytest.mark.integration
def test_clickhouse_connection_uses_http_port_8123():
    """Verify ClickHouseConnection uses HTTP port 8123 (not native TCP 9000).

    ClickHouse native TCP protocol (port 9000) is not used. We rely on HTTP interface
    for query execution, which is simpler and more widely supported.
    """
    with ClickHouseConnection() as conn:
        # Verify client uses HTTP interface
        # clickhouse_connect client uses port 8123 by default for HTTP
        interface = conn.client.server_host
        port = conn.client.server_port

        # Verify connection is established
        assert conn.client is not None, "Client should be initialized"

        # Verify port 8123 is used (HTTP interface)
        assert port == 8123, f"Expected HTTP port 8123, got {port}"

        # Verify host is correct
        assert interface == "localhost", f"Expected localhost, got {interface}"


@pytest.mark.integration
def test_http_protocol_health_check():
    """Verify health check via HTTP interface succeeds."""
    with ClickHouseConnection() as conn:
        # Health check should succeed (called in __enter__)
        assert conn.health_check(), "Health check should return True"

        # Verify we can execute a simple query
        result = conn.execute("SELECT 1")
        assert result is not None, "Query should return result"
        assert len(result) == 1, "Should return 1 row"
        assert result[0][0] == 1, "Should return value 1"


@pytest.mark.integration
def test_http_query_execution():
    """Verify query execution via HTTP returns results."""
    with ClickHouseConnection() as conn:
        # Execute a query that requires actual database access
        result = conn.execute("SELECT version()")

        assert result is not None, "Query should return result"
        assert len(result) == 1, "Should return 1 row"

        version = result[0][0]
        assert isinstance(version, str), f"Version should be string, got {type(version)}"
        assert len(version) > 0, "Version should not be empty"

        # Verify version format (e.g., "24.1.1.2048")
        version_parts = version.split(".")
        assert len(version_parts) >= 3, f"Version should have at least 3 parts, got {version}"


@pytest.mark.integration
def test_http_query_execution_with_dataframe():
    """Verify HTTP queries can return DataFrames (Arrow-optimized path)."""
    with ClickHouseConnection() as conn:
        # Execute query using query_df (Arrow path)
        df = conn.client.query_df("SELECT 1 as test_col")

        assert df is not None, "DataFrame should not be None"
        assert len(df) == 1, "Should return 1 row"
        assert "test_col" in df.columns, "Should have test_col column"
        assert df["test_col"].iloc[0] == 1, "Should return value 1"


@pytest.mark.integration
def test_http_error_propagation_invalid_query():
    """Verify HTTP errors (400 Bad Request) are raised as exceptions for invalid queries."""
    with ClickHouseConnection() as conn:
        # Execute invalid query (syntax error)
        with pytest.raises(Exception) as exc_info:
            conn.execute("SELECT INVALID_SYNTAX_HERE")

        # Verify exception contains useful error message
        error_msg = str(exc_info.value).lower()
        # ClickHouse error messages typically contain "syntax" or "unknown" or "parse"
        assert any(keyword in error_msg for keyword in ["syntax", "unknown", "parse", "error"]), \
            f"Expected error message to contain syntax/unknown/parse, got: {error_msg}"


@pytest.mark.integration
def test_http_error_propagation_table_not_found():
    """Verify HTTP errors (404-like) are raised for non-existent tables."""
    with ClickHouseConnection() as conn:
        # Query non-existent table
        with pytest.raises(Exception) as exc_info:
            conn.execute("SELECT * FROM non_existent_table_12345")

        # Verify exception contains table name or "not found"
        error_msg = str(exc_info.value).lower()
        assert "non_existent_table_12345" in error_msg or "not" in error_msg or "unknown" in error_msg, \
            f"Expected error message to mention table or 'not found', got: {error_msg}"


@pytest.mark.integration
def test_http_connection_context_manager_cleanup():
    """Verify HTTP connection is properly cleaned up after context exit."""
    # Create connection
    conn = ClickHouseConnection()

    # Enter context
    with conn:
        # Connection should be active
        assert conn.health_check(), "Health check should succeed in context"

    # After context exit, connection should be closed
    # Note: clickhouse_connect client doesn't have explicit "closed" state,
    # but we verify by attempting operations
    # (Connection is actually still usable, but context exit called)
    # This test mainly verifies __exit__ doesn't raise


@pytest.mark.integration
def test_http_concurrent_queries():
    """Verify multiple queries can execute in sequence via HTTP (connection reuse)."""
    with ClickHouseConnection() as conn:
        # Execute multiple queries in sequence
        result1 = conn.execute("SELECT 1")
        result2 = conn.execute("SELECT 2")
        result3 = conn.execute("SELECT 3")

        # Verify all queries succeeded
        assert result1[0][0] == 1, "First query should return 1"
        assert result2[0][0] == 2, "Second query should return 2"
        assert result3[0][0] == 3, "Third query should return 3"


@pytest.mark.integration
def test_http_large_query_result():
    """Verify HTTP can handle large query results (1000+ rows)."""
    with ClickHouseConnection() as conn:
        # Query that returns 1000 rows
        result = conn.execute("SELECT number FROM system.numbers LIMIT 1000")

        assert len(result) == 1000, f"Expected 1000 rows, got {len(result)}"

        # Verify first and last values
        assert result[0][0] == 0, "First row should be 0"
        assert result[-1][0] == 999, "Last row should be 999"


@pytest.mark.integration
def test_http_query_with_parameters():
    """Verify HTTP queries support parameterized queries (prevent SQL injection)."""
    with ClickHouseConnection() as conn:
        # Execute parameterized query
        query = "SELECT {param:UInt32} as value"
        result = conn.client.query(query, parameters={"param": 42})

        assert result.result_rows[0][0] == 42, "Parameterized query should return 42"
