"""
Unit tests for gap filling functions in query_api.py (ADR-0041, ADR-0048).

Tests cover:
- _convert_api_data_to_dataframe(): Column order, data_source tagging, naive UTC timestamps
- _fill_gaps_from_api(): Empty gaps handling, API failure handling

ADR-0048: _version and _sign computed by ClickHouse DEFAULT expressions,
not in Python. DataFrame has 16 columns instead of 18.

All tests use mocked dependencies for isolated, fast execution (<5s total).
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestConvertApiDataToDataframe:
    """Tests for _convert_api_data_to_dataframe() function.

    ADR-0048: _version and _sign computed by ClickHouse DEFAULT expressions.
    DataFrame now has 16 columns (not 18).
    """

    def test_correct_column_count(self, sample_api_candle_dicts):
        """DataFrame has exactly 16 columns (ADR-0048: _version/_sign computed by ClickHouse)."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert len(df.columns) == 16, f"Expected 16 columns, got {len(df.columns)}"

    def test_correct_column_order(self, sample_api_candle_dicts):
        """Columns are in correct order for ClickHouse schema (ADR-0048)."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        # ADR-0048: _version and _sign omitted - computed by ClickHouse DEFAULT
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

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert list(df.columns) == expected_columns

    def test_data_source_is_rest_api(self, sample_api_candle_dicts):
        """All rows have data_source='rest_api'."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert (df["data_source"] == "rest_api").all()

    def test_timestamps_are_naive_utc(self, sample_api_candle_dicts):
        """Timestamps are naive UTC (codebase convention per connection.py:205)."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        # Naive UTC convention - no timezone info
        assert df["timestamp"].dt.tz is None, "timestamp should be naive UTC"
        assert df["close_time"].dt.tz is None, "close_time should be naive UTC"

    def test_number_of_trades_is_int64(self, sample_api_candle_dicts):
        """number_of_trades column is int64 dtype."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert df["number_of_trades"].dtype == "int64"

    def test_funding_rate_is_null(self, sample_api_candle_dicts):
        """funding_rate is NULL for gap-filled data."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert df["funding_rate"].isna().all()

    def test_raises_on_empty_data(self):
        """Raises ValueError for empty api_data."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        with pytest.raises(ValueError, match="api_data cannot be empty"):
            _convert_api_data_to_dataframe([], "BTCUSDT", "1h", "spot")

    def test_metadata_columns_propagated(self, sample_api_candle_dicts):
        """Symbol, timeframe, instrument_type are correctly set."""
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "ETHUSDT", "4h", "futures-um")

        assert (df["symbol"] == "ETHUSDT").all()
        assert (df["timeframe"] == "4h").all()
        assert (df["instrument_type"] == "futures-um").all()

    def test_unique_timestamps_per_row(self, sample_api_candle_dicts):
        """Each row has unique timestamp (deduplication key).

        ADR-0048: With _version computed by ClickHouse, timestamp uniqueness
        is the primary deduplication key within symbol/timeframe/instrument_type.
        """
        from gapless_crypto_clickhouse.query_api import _convert_api_data_to_dataframe

        df = _convert_api_data_to_dataframe(sample_api_candle_dicts, "BTCUSDT", "1h", "spot")

        assert df["timestamp"].nunique() == len(df), "All timestamps must be unique"


class TestFillGapsFromApi:
    """Tests for _fill_gaps_from_api() function with mocked dependencies."""

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_empty_gaps_no_api_calls(self, mock_fetch):
        """Empty gaps DataFrame triggers no API calls."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        empty_gaps = pd.DataFrame(columns=["gap_start", "gap_end", "missing_rows"])
        mock_connection = MagicMock()

        rows = _fill_gaps_from_api(mock_connection, empty_gaps, "BTCUSDT", "1h", "spot")

        mock_fetch.assert_not_called()
        assert rows == 0

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_api_returns_none_skips_gap(self, mock_fetch, sample_gap_dataframe):
        """API returning None skips gap without exception."""
        from gapless_crypto_clickhouse.query_api import _fill_gaps_from_api

        mock_fetch.return_value = None
        mock_connection = MagicMock()

        # Should not raise, just skip
        rows = _fill_gaps_from_api(mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot")

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

        rows = _fill_gaps_from_api(mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot")

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

        _fill_gaps_from_api(mock_connection, sample_gap_dataframe, "BTCUSDT", "1h", "spot")

        # Verify table name in call
        call_args = mock_connection.insert_dataframe.call_args
        assert call_args.kwargs.get("table") == "ohlcv"


# =============================================================================
# Recent Month Detection Tests (ADR: 2025-12-27-cache-first-recent-data-fallback)
# =============================================================================


class TestIsRecentMonth:
    """Tests for _is_recent_month() function.

    ADR: 2025-12-27-cache-first-recent-data-fallback
    Detects months within CDN publication lag window for REST API fallback.
    """

    def test_current_month_is_recent(self):
        """Current month should always be detected as recent."""
        from datetime import datetime

        from gapless_crypto_clickhouse.query_api import _is_recent_month

        now = datetime.now()
        assert _is_recent_month(now.year, now.month) is True

    def test_old_month_not_recent(self):
        """Month from a year ago should not be detected as recent."""
        from datetime import datetime

        from gapless_crypto_clickhouse.query_api import _is_recent_month

        now = datetime.now()
        old_year = now.year - 1
        assert _is_recent_month(old_year, now.month) is False

    def test_historical_month_not_recent(self):
        """Fixed historical month should not be recent."""
        from gapless_crypto_clickhouse.query_api import _is_recent_month

        # January 2020 - definitely not recent
        assert _is_recent_month(2020, 1) is False

    def test_lookback_parameter(self):
        """Lookback parameter should affect detection threshold."""
        from datetime import datetime

        from gapless_crypto_clickhouse.query_api import _is_recent_month

        now = datetime.now()
        # With 30 day lookback, previous month should be recent
        if now.month == 1:
            prev_year, prev_month = now.year - 1, 12
        else:
            prev_year, prev_month = now.year, now.month - 1

        # With large lookback, previous month is recent
        assert _is_recent_month(prev_year, prev_month, lookback_days=60) is True


class TestIngestRecentFromApi:
    """Tests for _ingest_recent_from_api() function.

    ADR: 2025-12-27-cache-first-recent-data-fallback
    Ingests data via REST API when CDN archives unavailable.
    """

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    @patch("gapless_crypto_clickhouse.query_api._convert_api_data_to_dataframe")
    def test_calls_fetch_gap_data(self, mock_convert, mock_fetch, sample_api_candle_dicts):
        """Calls fetch_gap_data with correct parameters."""
        from gapless_crypto_clickhouse.query_api import _ingest_recent_from_api

        mock_fetch.return_value = sample_api_candle_dicts
        mock_connection = MagicMock()
        mock_connection.insert_dataframe.return_value = 3
        mock_convert.return_value = pd.DataFrame(sample_api_candle_dicts)

        _ingest_recent_from_api(mock_connection, "BTCUSDT", "1h", 2024, 11, "spot")

        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args.kwargs
        assert call_kwargs["symbol"] == "BTCUSDT"
        assert call_kwargs["timeframe"] == "1h"
        assert call_kwargs["instrument_type"] == "spot"

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    def test_returns_zero_for_empty_api_response(self, mock_fetch):
        """Returns 0 when API returns no data."""
        from gapless_crypto_clickhouse.query_api import _ingest_recent_from_api

        mock_fetch.return_value = None
        mock_connection = MagicMock()

        rows = _ingest_recent_from_api(mock_connection, "BTCUSDT", "1h", 2024, 11, "spot")

        assert rows == 0
        mock_connection.insert_dataframe.assert_not_called()

    @patch("gapless_crypto_clickhouse.query_api.fetch_gap_data")
    @patch("gapless_crypto_clickhouse.query_api._convert_api_data_to_dataframe")
    def test_inserts_to_ohlcv_table(self, mock_convert, mock_fetch, sample_api_candle_dicts):
        """Inserts data to ohlcv table."""
        from gapless_crypto_clickhouse.query_api import _ingest_recent_from_api

        mock_fetch.return_value = sample_api_candle_dicts
        mock_connection = MagicMock()
        mock_connection.insert_dataframe.return_value = 3
        mock_convert.return_value = pd.DataFrame(sample_api_candle_dicts)

        rows = _ingest_recent_from_api(mock_connection, "BTCUSDT", "1h", 2024, 11, "spot")

        assert rows == 3
        call_args = mock_connection.insert_dataframe.call_args
        assert call_args.kwargs.get("table") == "ohlcv"


class TestAutoIngestDateRangeCdnFallback:
    """Tests for _auto_ingest_date_range() CDN → REST API fallback.

    ADR: 2025-12-27-cache-first-recent-data-fallback
    When CDN returns HTTP 404 for recent months, falls back to REST API.
    """

    @patch("gapless_crypto_clickhouse.query_api._ingest_recent_from_api")
    @patch("gapless_crypto_clickhouse.query_api._is_recent_month")
    def test_cdn_404_triggers_rest_fallback(self, mock_is_recent, mock_ingest_api):
        """HTTP 404 on recent month triggers REST API fallback."""
        from datetime import datetime
        from urllib.error import HTTPError

        from gapless_crypto_clickhouse.query_api import _auto_ingest_date_range

        # Mock CDN to return 404
        mock_loader = MagicMock()
        mock_loader.ingest_month.side_effect = HTTPError(
            None, 404, "Not Found", {}, None
        )

        # Mock recent month detection
        mock_is_recent.return_value = True

        # Mock REST API ingest
        mock_ingest_api.return_value = 100

        mock_connection = MagicMock()

        now = datetime.now()
        start_date = f"{now.year}-{now.month:02d}-01"
        end_date = f"{now.year}-{now.month:02d}-15"

        rows = _auto_ingest_date_range(
            mock_loader, mock_connection, "BTCUSDT", "1h",
            start_date, end_date, "spot"
        )

        # Verify REST API fallback was called
        mock_ingest_api.assert_called_once()
        assert rows == 100

    @patch("gapless_crypto_clickhouse.query_api._ingest_recent_from_api")
    @patch("gapless_crypto_clickhouse.query_api._is_recent_month")
    def test_cdn_404_historical_no_fallback(self, mock_is_recent, mock_ingest_api):
        """HTTP 404 on historical month does NOT trigger REST API fallback."""
        from urllib.error import HTTPError

        from gapless_crypto_clickhouse.query_api import _auto_ingest_date_range

        # Mock CDN to return 404
        mock_loader = MagicMock()
        mock_loader.ingest_month.side_effect = HTTPError(
            None, 404, "Not Found", {}, None
        )

        # Mock: NOT a recent month
        mock_is_recent.return_value = False

        mock_connection = MagicMock()

        # Historical date - January 2020
        rows = _auto_ingest_date_range(
            mock_loader, mock_connection, "BTCUSDT", "1h",
            "2020-01-01", "2020-01-15", "spot"
        )

        # REST API should NOT be called for historical data
        mock_ingest_api.assert_not_called()
        assert rows == 0  # No rows ingested

    def test_cdn_success_no_fallback(self):
        """Successful CDN ingest does not trigger REST API fallback."""
        from gapless_crypto_clickhouse.query_api import _auto_ingest_date_range

        mock_loader = MagicMock()
        mock_loader.ingest_month.return_value = 500  # CDN success

        mock_connection = MagicMock()

        rows = _auto_ingest_date_range(
            mock_loader, mock_connection, "BTCUSDT", "1h",
            "2024-01-01", "2024-01-15", "spot"
        )

        # Only CDN called, no REST API
        mock_loader.ingest_month.assert_called_once()
        assert rows == 500
