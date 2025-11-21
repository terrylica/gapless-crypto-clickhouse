"""Arrow query equivalence tests for v6.0.0.

Validates Arrow-optimized queries return identical results to standard queries.
Critical for proving v6.0.0 correctness (ADR-0023 performance optimization).

**SLO Focus**: Correctness (Arrow optimization must not change query results)

**ADR**: ADR-0024 (Comprehensive Validation Canonicity)
"""

import pandas as pd
import pytest

from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection


@pytest.mark.integration
def test_arrow_standard_query_equivalence_simple():
    """Verify Arrow and standard queries return identical data for simple query."""
    query = "SELECT * FROM ohlcv FINAL WHERE symbol = 'BTCUSDT' AND timeframe = '1h' LIMIT 100"

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify data equivalence
    pd.testing.assert_frame_equal(
        df_arrow.reset_index(drop=True),
        df_standard.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,  # Allow floating point tolerance
        rtol=1e-10
    )


@pytest.mark.integration
def test_arrow_standard_query_equivalence_large():
    """Verify Arrow and standard queries return identical data for large dataset (10K rows)."""
    query = """
        SELECT * FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
        ORDER BY timestamp DESC
        LIMIT 10000
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify row count
    assert len(df_arrow) == len(df_standard), f"Row count mismatch: Arrow={len(df_arrow)}, Standard={len(df_standard)}"

    # Verify data equivalence
    pd.testing.assert_frame_equal(
        df_arrow.reset_index(drop=True),
        df_standard.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-10
    )


@pytest.mark.integration
def test_arrow_standard_column_order_preserved():
    """Verify Arrow preserves column ordering."""
    query = """
        SELECT timestamp, symbol, timeframe, open, high, low, close, volume
        FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
        LIMIT 100
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify column names match exactly
    assert list(df_arrow.columns) == list(df_standard.columns), \
        f"Column order mismatch: Arrow={list(df_arrow.columns)}, Standard={list(df_standard.columns)}"


@pytest.mark.integration
def test_arrow_standard_data_types_match():
    """Verify Arrow and standard queries return same data types (especially DateTime64(6))."""
    query = """
        SELECT timestamp, close_time, symbol, open, high, low, close, volume, number_of_trades
        FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
        LIMIT 100
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify data types match
    for col in df_arrow.columns:
        arrow_dtype = df_arrow[col].dtype
        standard_dtype = df_standard[col].dtype

        # Allow minor type variations (e.g., datetime64[ns] vs datetime64[us])
        if pd.api.types.is_datetime64_any_dtype(arrow_dtype):
            assert pd.api.types.is_datetime64_any_dtype(standard_dtype), \
                f"Column {col}: Arrow is datetime but Standard is {standard_dtype}"
        elif pd.api.types.is_numeric_dtype(arrow_dtype):
            assert pd.api.types.is_numeric_dtype(standard_dtype), \
                f"Column {col}: Arrow is numeric but Standard is {standard_dtype}"
        else:
            assert arrow_dtype == standard_dtype, \
                f"Column {col}: dtype mismatch (Arrow={arrow_dtype}, Standard={standard_dtype})"


@pytest.mark.integration
def test_arrow_standard_null_handling():
    """Verify Arrow and standard handle NULL values identically (funding_rate for spot)."""
    query = """
        SELECT symbol, timeframe, instrument_type, funding_rate
        FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h' AND instrument_type = 'spot'
        LIMIT 100
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify funding_rate is NULL for spot
    assert df_arrow['funding_rate'].isna().all(), "Arrow: funding_rate should be NULL for spot"
    assert df_standard['funding_rate'].isna().all(), "Standard: funding_rate should be NULL for spot"

    # Verify NULL counts match
    for col in df_arrow.columns:
        arrow_nulls = df_arrow[col].isna().sum()
        standard_nulls = df_standard[col].isna().sum()
        assert arrow_nulls == standard_nulls, \
            f"Column {col}: NULL count mismatch (Arrow={arrow_nulls}, Standard={standard_nulls})"


@pytest.mark.integration
def test_arrow_standard_empty_result_set():
    """Verify Arrow and standard handle empty result sets identically."""
    query = """
        SELECT * FROM ohlcv FINAL
        WHERE symbol = 'FAKESYMBOL_DOES_NOT_EXIST'
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify both are empty
    assert len(df_arrow) == 0, f"Arrow returned {len(df_arrow)} rows, expected 0"
    assert len(df_standard) == 0, f"Standard returned {len(df_standard)} rows, expected 0"

    # Verify column names match (even for empty result)
    assert list(df_arrow.columns) == list(df_standard.columns)


@pytest.mark.integration
def test_arrow_standard_single_row():
    """Verify Arrow and standard handle single-row result sets identically (edge case)."""
    query = """
        SELECT * FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
        ORDER BY timestamp DESC
        LIMIT 1
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify both return exactly 1 row
    assert len(df_arrow) == 1, f"Arrow returned {len(df_arrow)} rows, expected 1"
    assert len(df_standard) == 1, f"Standard returned {len(df_standard)} rows, expected 1"

    # Verify data equivalence
    pd.testing.assert_frame_equal(
        df_arrow.reset_index(drop=True),
        df_standard.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-10
    )


@pytest.mark.integration
def test_arrow_standard_special_characters():
    """Verify Arrow and standard handle special characters identically (Unicode symbols)."""
    # Query with symbol that might have special handling
    query = """
        SELECT symbol, timeframe, timestamp, close
        FROM ohlcv FINAL
        WHERE symbol IN ('BTCUSDT', 'ETHUSDT', '1000SHIBUSDT')
        AND timeframe = '1h'
        ORDER BY timestamp DESC, symbol ASC
        LIMIT 100
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify data equivalence
    pd.testing.assert_frame_equal(
        df_arrow.reset_index(drop=True),
        df_standard.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-10
    )

    # Verify symbol values are correct
    unique_symbols_arrow = set(df_arrow['symbol'].unique())
    unique_symbols_standard = set(df_standard['symbol'].unique())
    assert unique_symbols_arrow == unique_symbols_standard, \
        f"Symbol mismatch: Arrow={unique_symbols_arrow}, Standard={unique_symbols_standard}"


@pytest.mark.integration
def test_arrow_standard_aggregation_equivalence():
    """Verify Arrow and standard return identical aggregation results."""
    query = """
        SELECT
            symbol,
            timeframe,
            COUNT(*) as row_count,
            AVG(close) as avg_close,
            MIN(low) as min_low,
            MAX(high) as max_high,
            SUM(volume) as total_volume
        FROM ohlcv FINAL
        WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
        GROUP BY symbol, timeframe
    """

    with ClickHouseConnection() as conn:
        df_arrow = conn.client.query_df(query, use_arrow=True)
        df_standard = conn.client.query_df(query, use_arrow=False)

    # Verify aggregation results match
    pd.testing.assert_frame_equal(
        df_arrow.reset_index(drop=True),
        df_standard.reset_index(drop=True),
        check_dtype=True,
        check_exact=False,
        rtol=1e-8  # Allow slightly higher tolerance for aggregations
    )
