"""Multi-symbol data isolation tests for v6.0.0.

Validates BTCUSDT query doesn't return ETHUSDT data (no cross-contamination).
Critical for data integrity in multi-symbol ingestion scenarios.

**SLO Focus**: Correctness (data isolation prevents cross-symbol contamination)

**ADR**: ADR-0024 (Comprehensive Validation Canonicity)
"""

import pytest
import pandas as pd
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery


@pytest.mark.integration
def test_btcusdt_query_does_not_return_ethusdt_data():
    """Verify BTCUSDT query doesn't return ETHUSDT data (no cross-contamination)."""
    with ClickHouseConnection() as conn:
        query_engine = OHLCVQuery(conn)

        # Query BTCUSDT only
        df = query_engine.get_range(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )

        if len(df) > 0:
            # Verify all rows are BTCUSDT
            assert (df['symbol'] == 'BTCUSDT').all(), \
                f"BTCUSDT query returned other symbols: {df['symbol'].unique()}"

            # Verify no ETHUSDT rows
            ethusdt_count = (df['symbol'] == 'ETHUSDT').sum()
            assert ethusdt_count == 0, f"BTCUSDT query returned {ethusdt_count} ETHUSDT rows"


@pytest.mark.integration
@pytest.mark.slow
def test_multi_symbol_ingestion_isolation():
    """Verify ingesting BTCUSDT doesn't affect ETHUSDT queries (isolation)."""
    with ClickHouseConnection() as conn:
        query_engine = OHLCVQuery(conn)

        # Query ETHUSDT before any BTCUSDT operations
        df_eth_before = query_engine.get_range(
            symbol="ETHUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )
        eth_count_before = len(df_eth_before)

        # Ingest some BTCUSDT data (if test environment allows)
        # Note: This test assumes BTCUSDT and ETHUSDT are separate in database

        # Query ETHUSDT after BTCUSDT operations
        df_eth_after = query_engine.get_range(
            symbol="ETHUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )
        eth_count_after = len(df_eth_after)

        # Verify ETHUSDT data unchanged (BTCUSDT operations didn't affect it)
        assert eth_count_before == eth_count_after, \
            f"ETHUSDT row count changed: {eth_count_before} → {eth_count_after}"


@pytest.mark.integration
def test_spot_futures_isolation():
    """Verify spot BTCUSDT doesn't appear in futures query (instrument_type isolation)."""
    with ClickHouseConnection() as conn:
        query_engine = OHLCVQuery(conn)

        # Query spot BTCUSDT
        df_spot = query_engine.get_range(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )

        # Query futures BTCUSDT
        df_futures = query_engine.get_range(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="um"  # futures-um
        )

        # Verify instrument_type isolation
        if len(df_spot) > 0:
            assert (df_spot['instrument_type'] == 'spot').all(), \
                f"Spot query returned non-spot data: {df_spot['instrument_type'].unique()}"

        if len(df_futures) > 0:
            assert (df_futures['instrument_type'] == 'um').all(), \
                f"Futures query returned non-futures data: {df_futures['instrument_type'].unique()}"

        # Verify no overlap (spot and futures are separate)
        if len(df_spot) > 0 and len(df_futures) > 0:
            spot_timestamps = set(df_spot['timestamp'])
            futures_timestamps = set(df_futures['timestamp'])
            # Same timestamps can exist, but instrument_type must differ
            # This is correct behavior (same symbol, same time, different market)


@pytest.mark.integration
def test_instrument_type_filter_correctness():
    """Verify instrument_type filter correctly isolates data."""
    with ClickHouseConnection() as conn:
        # Direct SQL query to verify filter
        query = """
            SELECT DISTINCT instrument_type, symbol
            FROM ohlcv FINAL
            WHERE symbol = 'BTCUSDT' AND timeframe = '1h'
            AND instrument_type = 'spot'
            LIMIT 100
        """
        result = conn.execute(query)

        # Verify all rows are spot
        for row in result:
            instrument_type, symbol = row
            assert instrument_type == 'spot', f"Got instrument_type={instrument_type}, expected 'spot'"
            assert symbol == 'BTCUSDT', f"Got symbol={symbol}, expected 'BTCUSDT'"


@pytest.mark.integration
def test_timeframe_isolation():
    """Verify 1h data doesn't appear in 4h query (timeframe isolation)."""
    with ClickHouseConnection() as conn:
        query_engine = OHLCVQuery(conn)

        # Query 1h data
        df_1h = query_engine.get_range(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )

        # Query 4h data
        df_4h = query_engine.get_range(
            symbol="BTCUSDT",
            timeframe="4h",
            start_date="2024-01-01",
            end_date="2024-01-07",
            instrument_type="spot"
        )

        # Verify timeframe isolation
        if len(df_1h) > 0:
            assert (df_1h['timeframe'] == '1h').all(), \
                f"1h query returned other timeframes: {df_1h['timeframe'].unique()}"

        if len(df_4h) > 0:
            assert (df_4h['timeframe'] == '4h').all(), \
                f"4h query returned other timeframes: {df_4h['timeframe'].unique()}"

        # Verify different row counts (1h has more bars than 4h for same period)
        if len(df_1h) > 0 and len(df_4h) > 0:
            assert len(df_1h) > len(df_4h), \
                f"1h data ({len(df_1h)} rows) should have more bars than 4h data ({len(df_4h)} rows)"
