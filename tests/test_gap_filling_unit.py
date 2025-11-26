"""
Unit tests for gap filling functions in query_api.py (ADR-0041).

Tests cover:
- _compute_version_hash(): Determinism, uniqueness, UInt64 range
- _convert_api_data_to_dataframe(): Column order, data_source tagging, UTC timestamps
- _fill_gaps_from_api(): Empty gaps handling, API failure handling

All tests use mocked dependencies for isolated, fast execution (<5s total).
"""

import hashlib
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestComputeVersionHash:
    """Tests for _compute_version_hash() function."""

    def test_hash_determinism_same_input(self, sample_api_candle_dicts):
        """Same data produces identical hash (deterministic)."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row = pd.Series(sample_api_candle_dicts[0])
        hash1 = _compute_version_hash(row, "BTCUSDT", "1h", "spot")
        hash2 = _compute_version_hash(row, "BTCUSDT", "1h", "spot")

        assert hash1 == hash2, "Same input must produce same hash"

    def test_hash_differs_for_different_ohlcv(self, sample_api_candle_dicts):
        """Different OHLCV data produces different hash."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row1 = pd.Series(sample_api_candle_dicts[0])
        row2 = pd.Series(sample_api_candle_dicts[1])

        hash1 = _compute_version_hash(row1, "BTCUSDT", "1h", "spot")
        hash2 = _compute_version_hash(row2, "BTCUSDT", "1h", "spot")

        assert hash1 != hash2, "Different data must produce different hashes"

    def test_hash_differs_for_different_symbol(self, sample_api_candle_dicts):
        """Different symbol produces different hash."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row = pd.Series(sample_api_candle_dicts[0])
        hash1 = _compute_version_hash(row, "BTCUSDT", "1h", "spot")
        hash2 = _compute_version_hash(row, "ETHUSDT", "1h", "spot")

        assert hash1 != hash2, "Different symbols must produce different hashes"

    def test_hash_differs_for_different_timeframe(self, sample_api_candle_dicts):
        """Different timeframe produces different hash."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row = pd.Series(sample_api_candle_dicts[0])
        hash1 = _compute_version_hash(row, "BTCUSDT", "1h", "spot")
        hash2 = _compute_version_hash(row, "BTCUSDT", "4h", "spot")

        assert hash1 != hash2, "Different timeframes must produce different hashes"

    def test_hash_differs_for_different_instrument_type(self, sample_api_candle_dicts):
        """Different instrument type produces different hash."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row = pd.Series(sample_api_candle_dicts[0])
        hash1 = _compute_version_hash(row, "BTCUSDT", "1h", "spot")
        hash2 = _compute_version_hash(row, "BTCUSDT", "1h", "futures-um")

        assert hash1 != hash2, "Different instrument types must produce different hashes"

    def test_hash_is_uint64_range(self, sample_api_candle_dicts):
        """Hash value falls within UInt64 range (0 to 2^64-1)."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        row = pd.Series(sample_api_candle_dicts[0])
        hash_value = _compute_version_hash(row, "BTCUSDT", "1h", "spot")

        assert hash_value >= 0, "Hash must be non-negative"
        assert hash_value <= 2**64 - 1, "Hash must fit in UInt64"

    def test_hash_uniqueness_across_dataset(self, sample_api_candle_dicts):
        """All rows in sample data produce unique hashes."""
        from gapless_crypto_clickhouse.query_api import _compute_version_hash

        hashes = []
        for candle in sample_api_candle_dicts:
            row = pd.Series(candle)
            h = _compute_version_hash(row, "BTCUSDT", "1h", "spot")
            hashes.append(h)

        assert len(hashes) == len(set(hashes)), "All hashes must be unique"


class TestConvertApiDataToDataframe:
    """Tests for _convert_api_data_to_dataframe() function."""

    def test_correct_column_count(self, sample_api_candle_dicts):
        """DataFrame has exactly 18 columns matching ClickHouse schema."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert len(df.columns) == 18, f"Expected 18 columns, got {len(df.columns)}"

    def test_correct_column_order(self, sample_api_candle_dicts):
        """Columns are in correct order for ClickHouse schema."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

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
            "_version",
            "_sign",
        ]

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert list(df.columns) == expected_columns

    def test_data_source_is_rest_api(self, sample_api_candle_dicts):
        """All rows have data_source='rest_api'."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert (df["data_source"] == "rest_api").all()

    def test_timestamps_are_utc(self, sample_api_candle_dicts):
        """Timestamps are UTC-aware."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert df["timestamp"].dt.tz is not None, "timestamp must be timezone-aware"
        assert str(df["timestamp"].dt.tz) == "UTC", "timestamp must be UTC"
        assert df["close_time"].dt.tz is not None, "close_time must be timezone-aware"
        assert str(df["close_time"].dt.tz) == "UTC", "close_time must be UTC"

    def test_number_of_trades_is_int64(self, sample_api_candle_dicts):
        """number_of_trades column is int64 dtype."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert df["number_of_trades"].dtype == "int64"

    def test_version_hashes_are_unique(self, sample_api_candle_dicts):
        """Each row has unique _version hash."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert df["_version"].nunique() == len(df), "All _version hashes must be unique"

    def test_sign_column_is_one(self, sample_api_candle_dicts):
        """All rows have _sign=1 (active rows)."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert (df["_sign"] == 1).all()

    def test_funding_rate_is_null(self, sample_api_candle_dicts):
        """funding_rate is NULL for gap-filled data."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "BTCUSDT", "1h", "spot"
        )

        assert df["funding_rate"].isna().all()

    def test_raises_on_empty_data(self):
        """Raises ValueError for empty api_data."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        with pytest.raises(ValueError, match="api_data cannot be empty"):
            _convert_api_data_to_dataframe([], "BTCUSDT", "1h", "spot")

    def test_metadata_columns_propagated(self, sample_api_candle_dicts):
        """Symbol, timeframe, instrument_type are correctly set."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(
            sample_api_candle_dicts, "ETHUSDT", "4h", "futures-um"
        )

        assert (df["symbol"] == "ETHUSDT").all()
        assert (df["timeframe"] == "4h").all()
        assert (df["instrument_type"] == "futures-um").all()


class TestFillGapsFromApi:
    """Tests for _fill_gaps_from_api() function with mocked dependencies."""

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_empty_gaps_no_api_calls(self, mock_fetch):
        """Empty gaps DataFrame triggers no API calls."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        empty_gaps = pd.DataFrame(columns=["gap_start", "gap_end", "missing_rows"])
        mock_connection = MagicMock()

        rows = _fill_gaps_from_api(
            mock_connection, empty_gaps, "BTCUSDT", "1h", "spot"
        )

        mock_fetch.assert_not_called()
        assert rows == 0

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_api_returns_none_skips_gap(self, mock_fetch, sample_gap_dataframe):
        """API returning None skips gap without exception."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        mock_fetch.return_value = None
        mock_connection = MagicMock()

        # Should not raise, just skip
        rows = _fill_gaps_from_api(
            mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot"
        )

        assert rows == 0
        assert mock_fetch.call_count == 2  # Called for each gap

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_multiple_gaps_accumulate_rows(
        self, mock_fetch, sample_gap_dataframe, sample_api_candle_dicts
    ):
        """Multiple gaps accumulate total inserted rows."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        mock_fetch.return_value = sample_api_candle_dicts
        mock_connection = MagicMock()
        mock_connection.insert_dataframe.return_value = 3  # 3 rows per insert

        rows = _fill_gaps_from_api(
            mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot"
        )

        assert rows == 6  # 3 rows x 2 gaps
        assert mock_connection.insert_dataframe.call_count == 2

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_insert_uses_correct_table(
        self, mock_fetch, sample_gap_dataframe, sample_api_candle_dicts
    ):
        """Insert uses 'ohlcv' table."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        mock_fetch.return_value = sample_api_candle_dicts
        mock_connection = MagicMock()
        mock_connection.insert_dataframe.return_value = 3

        _fill_gaps_from_api(
            mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot"
        )

        # Verify table name in call
        call_args = mock_connection.insert_dataframe.call_args
        assert call_args.kwargs.get("table") == "ohlcv"
