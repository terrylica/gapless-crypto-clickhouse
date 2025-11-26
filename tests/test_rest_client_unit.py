"""
Unit tests for REST client functions in gap_filling/rest_client.py (ADR-0041).

Tests cover:
- get_interval_ms(): Timeframe to milliseconds conversion
- calculate_chunks(): Time range chunking for API limits
- fetch_klines_with_retry(): HTTP retry logic (mocked)
- fetch_gap_data(): High-level gap fetching (mocked)

All tests use mocked httpx for isolated, fast execution (<5s total).
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from tenacity import RetryError


class TestGetIntervalMs:
    """Tests for get_interval_ms() function."""

    def test_1s_interval(self):
        """1s timeframe returns 1000ms."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        assert get_interval_ms("1s") == 1000

    def test_1m_interval(self):
        """1m timeframe returns 60000ms."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        assert get_interval_ms("1m") == 60 * 1000

    def test_1h_interval(self):
        """1h timeframe returns 3600000ms."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        assert get_interval_ms("1h") == 60 * 60 * 1000

    def test_1d_interval(self):
        """1d timeframe returns 86400000ms."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        assert get_interval_ms("1d") == 24 * 60 * 60 * 1000

    def test_all_16_timeframes_supported(self):
        """All 16 supported timeframes return valid values."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        timeframes = [
            "1s",
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
            "1M",
        ]

        for tf in timeframes:
            result = get_interval_ms(tf)
            assert result > 0, f"Timeframe {tf} must return positive value"

    def test_invalid_timeframe_raises_valueerror(self):
        """Invalid timeframe raises ValueError."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import get_interval_ms

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            get_interval_ms("2m")

        with pytest.raises(ValueError, match="Unsupported timeframe"):
            get_interval_ms("invalid")


class TestCalculateChunks:
    """Tests for calculate_chunks() function."""

    def test_single_chunk_small_range(self):
        """Small range fits in single chunk."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        # 24 hours at 1h interval = 24 rows (fits in 1000 limit)
        hour_ms = 3600 * 1000
        start_ms = 0
        end_ms = 24 * hour_ms

        chunks = calculate_chunks(start_ms, end_ms, hour_ms)

        assert len(chunks) == 1
        assert chunks[0] == (start_ms, end_ms)

    def test_multiple_chunks_large_range(self):
        """Large range splits into multiple chunks."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        # 2000 hours at 1h interval = 2000 rows (needs 2 chunks of 1000)
        hour_ms = 3600 * 1000
        start_ms = 0
        end_ms = 2000 * hour_ms

        chunks = calculate_chunks(start_ms, end_ms, hour_ms)

        assert len(chunks) == 2
        # First chunk covers 1000 intervals
        assert chunks[0][1] - chunks[0][0] == 1000 * hour_ms
        # Second chunk covers remaining
        assert chunks[1][0] == 1000 * hour_ms

    def test_custom_chunk_size(self):
        """Custom chunk_size is respected."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        hour_ms = 3600 * 1000
        start_ms = 0
        end_ms = 500 * hour_ms

        # With chunk_size=100, need 5 chunks
        chunks = calculate_chunks(start_ms, end_ms, hour_ms, chunk_size=100)

        assert len(chunks) == 5

    def test_max_chunks_limit(self):
        """max_chunks parameter limits total chunks."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        hour_ms = 3600 * 1000
        start_ms = 0
        end_ms = 100000 * hour_ms  # Would need 100 chunks

        # Limit to 10 chunks
        chunks = calculate_chunks(start_ms, end_ms, hour_ms, max_chunks=10)

        assert len(chunks) == 10

    def test_chunk_boundaries_contiguous(self):
        """Chunk boundaries are contiguous (no gaps or overlaps)."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        hour_ms = 3600 * 1000
        start_ms = 0
        end_ms = 3000 * hour_ms

        chunks = calculate_chunks(start_ms, end_ms, hour_ms)

        # Each chunk end equals next chunk start
        for i in range(len(chunks) - 1):
            assert chunks[i][1] == chunks[i + 1][0], "Chunks must be contiguous"

        # First chunk starts at start_ms
        assert chunks[0][0] == start_ms
        # Last chunk ends at or before end_ms
        assert chunks[-1][1] <= end_ms

    def test_empty_range(self):
        """Empty range (start >= end) returns empty list."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import calculate_chunks

        chunks = calculate_chunks(1000, 1000, 1000)
        assert len(chunks) == 0

        chunks = calculate_chunks(2000, 1000, 1000)
        assert len(chunks) == 0


class TestFetchKlinesWithRetry:
    """Tests for fetch_klines_with_retry() function with mocked httpx."""

    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.httpx.get")
    def test_successful_fetch(self, mock_get, sample_api_kline_response):
        """Successful API response returns kline data."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            fetch_klines_with_retry,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_api_kline_response
        mock_get.return_value = mock_response

        result = fetch_klines_with_retry(
            "https://api.binance.com/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": "1h"},
        )

        assert result == sample_api_kline_response
        mock_get.assert_called_once()

    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.time.sleep")
    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.httpx.get")
    def test_rate_limit_429_raises(self, mock_get, mock_sleep):
        """HTTP 429 raises RetryError wrapping RateLimitError after retries exhaust."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            fetch_klines_with_retry,
        )

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "1"}
        mock_get.return_value = mock_response

        # RateLimitError is raised but retried by tenacity
        # After max retries, tenacity wraps it in RetryError
        with pytest.raises(RetryError):
            fetch_klines_with_retry(
                "https://api.binance.com/api/v3/klines",
                {"symbol": "BTCUSDT", "interval": "1h"},
            )

    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.time.sleep")
    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.httpx.get")
    def test_rate_limit_418_raises(self, mock_get, mock_sleep):
        """HTTP 418 (IP ban) raises RetryError wrapping RateLimitError after retries exhaust."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            fetch_klines_with_retry,
        )

        mock_response = MagicMock()
        mock_response.status_code = 418
        mock_response.headers = {"retry-after": "1"}
        mock_get.return_value = mock_response

        with pytest.raises(RetryError):
            fetch_klines_with_retry(
                "https://api.binance.com/api/v3/klines",
                {"symbol": "BTCUSDT", "interval": "1h"},
            )

    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.httpx.get")
    def test_api_error_raises(self, mock_get):
        """Non-200 response raises APIError."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            APIError,
            fetch_klines_with_retry,
        )

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        with pytest.raises(APIError):
            fetch_klines_with_retry(
                "https://api.binance.com/api/v3/klines",
                {"symbol": "BTCUSDT", "interval": "1h"},
            )

    @patch("gapless_crypto_clickhouse.gap_filling.rest_client.httpx.get")
    def test_api_error_in_json_response(self, mock_get):
        """API error in JSON response raises APIError."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            APIError,
            fetch_klines_with_retry,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": -1121, "msg": "Invalid symbol"}
        mock_get.return_value = mock_response

        with pytest.raises(APIError, match="Invalid symbol"):
            fetch_klines_with_retry(
                "https://api.binance.com/api/v3/klines",
                {"symbol": "INVALID", "interval": "1h"},
            )


class TestFetchGapData:
    """Tests for fetch_gap_data() high-level function."""

    @patch(
        "gapless_crypto_clickhouse.gap_filling.rest_client.fetch_klines_with_retry"
    )
    def test_spot_uses_correct_endpoint(self, mock_fetch, sample_api_kline_response):
        """Spot instrument uses api.binance.com endpoint."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            SPOT_API_URL,
            fetch_gap_data,
        )

        mock_fetch.return_value = sample_api_kline_response

        fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        call_args = mock_fetch.call_args
        assert call_args.args[0] == SPOT_API_URL

    @patch(
        "gapless_crypto_clickhouse.gap_filling.rest_client.fetch_klines_with_retry"
    )
    def test_futures_uses_correct_endpoint(self, mock_fetch, sample_api_kline_response):
        """Futures instrument uses fapi.binance.com endpoint."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import (
            FUTURES_API_URL,
            fetch_gap_data,
        )

        mock_fetch.return_value = sample_api_kline_response

        fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="futures-um",
        )

        call_args = mock_fetch.call_args
        assert call_args.args[0] == FUTURES_API_URL

    def test_invalid_instrument_type_raises(self):
        """Invalid instrument_type raises ValueError."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        with pytest.raises(ValueError, match="Invalid instrument_type"):
            fetch_gap_data(
                symbol="BTCUSDT",
                timeframe="1h",
                start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
                instrument_type="invalid",
            )

    @patch(
        "gapless_crypto_clickhouse.gap_filling.rest_client.fetch_klines_with_retry"
    )
    def test_boundary_filtering(self, mock_fetch):
        """Only candles within requested range are returned."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        # API returns data outside requested range (common with Binance)
        base_time = int(
            datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000
        )
        hour_ms = 3600 * 1000

        # Return 5 hours of data (00:00 to 04:00)
        mock_fetch.return_value = [
            [
                base_time + i * hour_ms,
                "95000.00",
                "95500.00",
                "94800.00",
                "95200.00",
                "1234.567",
                base_time + (i + 1) * hour_ms - 1,
                "117300000.00",
                50000,
                "600.123",
                "57000000.00",
                "0",
            ]
            for i in range(5)
        ]

        # Request only 3 hours (00:00 to 03:00)
        result = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        # Should only get 3 candles (00:00, 01:00, 02:00)
        assert len(result) == 3

    @patch(
        "gapless_crypto_clickhouse.gap_filling.rest_client.fetch_klines_with_retry"
    )
    def test_returns_none_on_empty_response(self, mock_fetch):
        """Returns None when API returns no data."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        mock_fetch.return_value = []

        result = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        assert result is None

    @patch(
        "gapless_crypto_clickhouse.gap_filling.rest_client.fetch_klines_with_retry"
    )
    def test_candle_dict_structure(self, mock_fetch, sample_api_kline_response):
        """Returned candle dictionaries have correct structure."""
        from gapless_crypto_clickhouse.gap_filling.rest_client import fetch_gap_data

        mock_fetch.return_value = sample_api_kline_response

        result = fetch_gap_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 11, 1, 3, 0, 0, tzinfo=timezone.utc),
            instrument_type="spot",
        )

        expected_keys = {
            "timestamp",
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
        }

        assert result is not None
        for candle in result:
            assert set(candle.keys()) == expected_keys
            assert isinstance(candle["timestamp"], datetime)
            assert isinstance(candle["close_time"], datetime)
