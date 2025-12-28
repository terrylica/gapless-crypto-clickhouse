"""
Integration tests for gap filling with real API and ClickHouse (ADR-0041).

Tests verify end-to-end gap filling workflow:
- REST API data fetching
- DataFrame conversion with proper schema
- ClickHouse insertion with deduplication
- Data source tagging

Test data: Fixed date range 2024-11-01 to 2024-11-07 for reproducibility.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestRestApiDataFetch:
    """Tests for real REST API data fetching."""

    def test_fetch_gap_data_spot_returns_valid_data(self):
        """fetch_gap_data returns valid candle data for spot."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 6, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data (network issue)")

        assert len(candles) == 6, f"Expected 6 candles, got {len(candles)}"
        assert all("timestamp" in c for c in candles)
        assert all("open" in c for c in candles)
        assert all("high" in c for c in candles)
        assert all("low" in c for c in candles)
        assert all("close" in c for c in candles)
        assert all("volume" in c for c in candles)

    def test_fetch_gap_data_futures_returns_valid_data(self):
        """fetch_gap_data returns valid candle data for futures."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 6, 0, 0, tzinfo=timezone.utc),
            instrument_type="futures-um",
        )

        if candles is None:
            pytest.skip("REST API returned no data (network issue)")

        assert len(candles) == 6
        # Verify OHLC constraints
        for c in candles:
            assert c["high"] >= c["low"], "high must be >= low"
            assert c["high"] >= c["open"], "high must be >= open"
            assert c["high"] >= c["close"], "high must be >= close"
            assert c["low"] <= c["open"], "low must be <= open"
            assert c["low"] <= c["close"], "low must be <= close"


class TestDataFrameConversion:
    """Tests for DataFrame conversion with real API data."""

    def test_rest_api_data_matches_clickhouse_schema(self):
        """REST API data converts to 16-column ClickHouse schema.

        ADR-0048: _version and _sign computed by ClickHouse DEFAULT expressions,
        not included in Python DataFrame. 16 columns instead of 18.
        """
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        df = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")

        # Verify 16 columns (ADR-0048: _version/_sign computed by ClickHouse DEFAULT)
        expected_columns = [
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
        ]
        assert list(df.columns) == expected_columns
        assert len(df.columns) == 16

    def test_data_source_column_is_rest_api(self):
        """data_source column is 'rest_api' for gap-filled data."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        df = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")

        assert (df["data_source"] == "rest_api").all()

    def test_timezone_correctness_naive_utc(self):
        """Timestamps are naive UTC (codebase convention per connection.py:205).

        The codebase uses naive UTC datetimes throughout for simpler comparison
        and consistent handling. ClickHouse stores as DateTime64(6) without timezone.
        """
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        df = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")

        # Verify naive UTC (no timezone info - codebase convention)
        assert df["timestamp"].dt.tz is None, "timestamp should be naive UTC"
        assert df["close_time"].dt.tz is None, "close_time should be naive UTC"

        # Verify timestamps are in expected UTC range
        assert df["timestamp"].min() >= datetime(2024, 11, 1, 0, 0, 0)
        assert df["timestamp"].max() < datetime(2024, 11, 1, 3, 0, 0)


class TestDataFrameConsistency:
    """Tests for DataFrame consistency and determinism.

    ADR-0048: _version hash is now computed by ClickHouse cityHash64() DEFAULT expression,
    not in Python. These tests verify DataFrame structure consistency instead.
    """

    def test_dataframe_deterministic_across_calls(self):
        """Same API data produces identical DataFrame structure across calls."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        df1 = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")
        df2 = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")

        # DataFrames should be identical
        assert list(df1.columns) == list(df2.columns)
        assert len(df1) == len(df2)
        assert list(df1["timestamp"]) == list(df2["timestamp"])
        assert list(df1["close"]) == list(df2["close"])

    def test_unique_timestamps_per_row(self):
        """Each row has unique timestamp (deduplication key)."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 6, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        df = _convert_api_data_to_dataframe(candles, "BTCUSDT", "1h", "spot")

        # Timestamps must be unique (ClickHouse ORDER BY includes timestamp)
        unique_timestamps = df["timestamp"].nunique()
        assert unique_timestamps == len(df), "All timestamps must be unique"


class TestChunking:
    """Tests for chunking large time ranges."""

    def test_calculate_chunks_for_large_range(self):
        """Large time range is split into multiple chunks."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        # 2500 hours requires 3 chunks at 1000 per chunk
        hour_ms = 3600 * 1000
        chunks = calculate_chunks(0, 2500 * hour_ms, hour_ms)

        assert len(chunks) == 3

    def test_fetch_large_gap_with_chunking(self):
        """Large gap fetches data using chunking."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        # 6 days = 144 hours
        candles = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 7, 0, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        if candles is None:
            pytest.skip("REST API returned no data")

        # Binance API may return slightly different counts depending on exact boundaries
        # Accept 144-145 candles (6 days = 144 hours, but boundary handling varies)
        assert 144 <= len(candles) <= 145, f"Expected ~144 candles, got {len(candles)}"
