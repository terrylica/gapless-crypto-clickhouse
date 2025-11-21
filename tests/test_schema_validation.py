"""Schema validation tests for ClickHouse v6.0.0.

Validates SchemaValidator detects schema drift and raises exceptions.

ADR: ADR-0024 (Comprehensive Validation Canonicity)
"""

import pytest

from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse.schema_validator import (
    SchemaValidationError,
    SchemaValidator,
)


@pytest.mark.integration
def test_schema_validation_passes_on_correct_schema():
    """Verify schema validator accepts correct schema.sql."""
    with ClickHouseConnection() as conn:
        validator = SchemaValidator(conn)
        report = validator.validate_schema()
        assert report["status"] == "valid"
        assert len(report["errors"]) == 0


@pytest.mark.integration
def test_schema_validation_detects_missing_column():
    """Verify schema validator detects missing columns."""
    with ClickHouseConnection() as conn:
        # Drop funding_rate column (simulate schema drift)
        conn.execute("ALTER TABLE ohlcv DROP COLUMN IF EXISTS funding_rate")

        try:
            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError, match="Missing column: funding_rate"):
                validator.validate_schema()
        finally:
            # Cleanup: restore column
            conn.execute("ALTER TABLE ohlcv ADD COLUMN IF NOT EXISTS funding_rate Nullable(Float64)")


@pytest.mark.integration
def test_schema_validation_detects_wrong_type():
    """Verify schema validator detects type mismatches (DateTime64(3) vs DateTime64(6))."""
    with ClickHouseConnection() as conn:
        # Get current timestamp type
        result = conn.execute(
            "SELECT type FROM system.columns "
            "WHERE database = 'default' AND table = 'ohlcv' AND name = 'timestamp'"
        )
        original_type = result[0][0] if result else 'DateTime64(6)'

        # Change timestamp to DateTime64(3) (simulate old schema)
        conn.execute("ALTER TABLE ohlcv MODIFY COLUMN timestamp DateTime64(3)")

        try:
            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError) as exc_info:
                validator.validate_schema()

            error_msg = str(exc_info.value)
            assert "Type mismatch: timestamp" in error_msg
            assert "DateTime64(6)" in error_msg  # Expected
            assert "DateTime64(3)" in error_msg  # Actual
            assert "CRITICAL" in error_msg or "1000x data loss" in error_msg
        finally:
            # Cleanup: restore correct type
            conn.execute(f"ALTER TABLE ohlcv MODIFY COLUMN timestamp {original_type}")


@pytest.mark.integration
def test_schema_validation_detects_wrong_engine():
    """Verify schema validator detects wrong engine (MergeTree vs ReplacingMergeTree).

    Note: This test recreates the table, so it's destructive.
    Skip in CI if database has important data.
    """
    pytest.skip("Destructive test - requires table recreation")

    with ClickHouseConnection() as conn:
        # Backup current table
        conn.execute("CREATE TABLE ohlcv_backup AS ohlcv")

        try:
            # Drop and recreate with wrong engine
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("""
                CREATE TABLE ohlcv (
                    timestamp DateTime64(6),
                    symbol String,
                    timeframe String,
                    instrument_type String,
                    data_source String,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume Float64,
                    close_time DateTime64(6),
                    quote_asset_volume Float64,
                    number_of_trades Int64,
                    taker_buy_base_asset_volume Float64,
                    taker_buy_quote_asset_volume Float64,
                    funding_rate Nullable(Float64),
                    _version UInt64,
                    _sign Int8
                ) ENGINE = MergeTree()
                PARTITION BY toYYYYMMDD(timestamp)
                ORDER BY (timestamp, symbol, timeframe, instrument_type)
            """)

            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError, match="Wrong engine"):
                validator.validate_schema()
        finally:
            # Cleanup: restore original table
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("RENAME TABLE ohlcv_backup TO ohlcv")


@pytest.mark.integration
def test_schema_validation_detects_missing_version_column():
    """Verify schema validator detects missing _version in ReplacingMergeTree.

    Note: This test recreates the table, so it's destructive.
    Skip in CI if database has important data.
    """
    pytest.skip("Destructive test - requires table recreation")

    with ClickHouseConnection() as conn:
        # Backup current table
        conn.execute("CREATE TABLE ohlcv_backup AS ohlcv")

        try:
            # Drop and recreate with ReplacingMergeTree but no version column
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("""
                CREATE TABLE ohlcv (
                    timestamp DateTime64(6),
                    symbol String,
                    timeframe String,
                    instrument_type String,
                    data_source String,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume Float64,
                    close_time DateTime64(6),
                    quote_asset_volume Float64,
                    number_of_trades Int64,
                    taker_buy_base_asset_volume Float64,
                    taker_buy_quote_asset_volume Float64,
                    funding_rate Nullable(Float64),
                    _version UInt64,
                    _sign Int8
                ) ENGINE = ReplacingMergeTree()
                PARTITION BY toYYYYMMDD(timestamp)
                ORDER BY (timestamp, symbol, timeframe, instrument_type)
            """)

            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError, match="version column missing"):
                validator.validate_schema()
        finally:
            # Cleanup: restore original table
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("RENAME TABLE ohlcv_backup TO ohlcv")


@pytest.mark.integration
def test_schema_validation_detects_wrong_partition_key():
    """Verify schema validator detects wrong partitioning.

    Note: This test recreates the table, so it's destructive.
    Skip in CI if database has important data.
    """
    pytest.skip("Destructive test - requires table recreation")

    with ClickHouseConnection() as conn:
        # Backup current table
        conn.execute("CREATE TABLE ohlcv_backup AS ohlcv")

        try:
            # Drop and recreate with wrong partition key
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("""
                CREATE TABLE ohlcv (
                    timestamp DateTime64(6),
                    symbol String,
                    timeframe String,
                    instrument_type String,
                    data_source String,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume Float64,
                    close_time DateTime64(6),
                    quote_asset_volume Float64,
                    number_of_trades Int64,
                    taker_buy_base_asset_volume Float64,
                    taker_buy_quote_asset_volume Float64,
                    funding_rate Nullable(Float64),
                    _version UInt64,
                    _sign Int8
                ) ENGINE = ReplacingMergeTree(_version)
                PARTITION BY toYYYYMM(timestamp)  -- Wrong: monthly instead of daily
                ORDER BY (timestamp, symbol, timeframe, instrument_type)
            """)

            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError, match="Partition key mismatch"):
                validator.validate_schema()
        finally:
            # Cleanup: restore original table
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("RENAME TABLE ohlcv_backup TO ohlcv")


@pytest.mark.integration
def test_schema_validation_detects_wrong_sorting_key():
    """Verify schema validator detects wrong ORDER BY clause.

    Note: This test recreates the table, so it's destructive.
    Skip in CI if database has important data.
    """
    pytest.skip("Destructive test - requires table recreation")

    with ClickHouseConnection() as conn:
        # Backup current table
        conn.execute("CREATE TABLE ohlcv_backup AS ohlcv")

        try:
            # Drop and recreate with wrong sorting key
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("""
                CREATE TABLE ohlcv (
                    timestamp DateTime64(6),
                    symbol String,
                    timeframe String,
                    instrument_type String,
                    data_source String,
                    open Float64,
                    high Float64,
                    low Float64,
                    close Float64,
                    volume Float64,
                    close_time DateTime64(6),
                    quote_asset_volume Float64,
                    number_of_trades Int64,
                    taker_buy_base_asset_volume Float64,
                    taker_buy_quote_asset_volume Float64,
                    funding_rate Nullable(Float64),
                    _version UInt64,
                    _sign Int8
                ) ENGINE = ReplacingMergeTree(_version)
                PARTITION BY toYYYYMMDD(timestamp)
                ORDER BY (symbol, timestamp)  -- Wrong order
            """)

            validator = SchemaValidator(conn)
            with pytest.raises(SchemaValidationError, match="Sorting key mismatch"):
                validator.validate_schema()
        finally:
            # Cleanup: restore original table
            conn.execute("DROP TABLE IF EXISTS ohlcv")
            conn.execute("RENAME TABLE ohlcv_backup TO ohlcv")


@pytest.mark.integration
def test_schema_validation_exception_propagation():
    """Verify SchemaValidationError propagates correctly (no silent failures)."""
    with ClickHouseConnection() as conn:
        # Drop funding_rate column to trigger validation error
        conn.execute("ALTER TABLE ohlcv DROP COLUMN IF EXISTS funding_rate")

        try:
            validator = SchemaValidator(conn)
            # Should raise, not return error dict
            with pytest.raises(SchemaValidationError):
                validator.validate_schema()

            # Verify exception type is correct
            try:
                validator.validate_schema()
            except SchemaValidationError as e:
                assert "Schema validation failed" in str(e)
                assert "funding_rate" in str(e)
            except Exception:
                pytest.fail("Should raise SchemaValidationError, not generic Exception")
        finally:
            # Cleanup: restore column
            conn.execute("ALTER TABLE ohlcv ADD COLUMN IF NOT EXISTS funding_rate Nullable(Float64)")
