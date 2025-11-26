"""Unit tests for OHLCVQuery class.

Tests query interface validation and SQL construction without database connection.
All tests use mocks - no ClickHouse Cloud connection required.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery


class TestOHLCVQueryInit:
    """Test OHLCVQuery initialization."""

    def test_init_with_valid_connection(self):
        """Initialize with valid ClickHouseConnection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        query = OHLCVQuery(mock_conn)
        assert query.connection is mock_conn

    def test_init_with_invalid_connection_raises(self):
        """Initialize with invalid connection raises ValueError."""
        with pytest.raises(ValueError, match="Expected ClickHouseConnection"):
            OHLCVQuery("not a connection")

    def test_init_with_none_raises(self):
        """Initialize with None raises ValueError."""
        with pytest.raises(ValueError, match="Expected ClickHouseConnection"):
            OHLCVQuery(None)


class TestGetLatestValidation:
    """Test get_latest() parameter validation."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        mock_conn.query_dataframe.return_value = pd.DataFrame()
        return OHLCVQuery(mock_conn)

    def test_empty_symbol_raises(self, mock_query):
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            mock_query.get_latest("", "1h")

    def test_none_symbol_raises(self, mock_query):
        """None symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            mock_query.get_latest(None, "1h")

    def test_empty_timeframe_raises(self, mock_query):
        """Empty timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Timeframe cannot be empty"):
            mock_query.get_latest("BTCUSDT", "")

    def test_zero_limit_raises(self, mock_query):
        """Zero limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            mock_query.get_latest("BTCUSDT", "1h", limit=0)

    def test_negative_limit_raises(self, mock_query):
        """Negative limit raises ValueError."""
        with pytest.raises(ValueError, match="Limit must be positive"):
            mock_query.get_latest("BTCUSDT", "1h", limit=-10)

    def test_invalid_instrument_type_raises(self, mock_query):
        """Invalid instrument_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid instrument_type"):
            mock_query.get_latest("BTCUSDT", "1h", instrument_type="invalid")

    def test_symbol_uppercased(self, mock_query):
        """Symbol is automatically uppercased."""
        mock_query.get_latest("btcusdt", "1h")
        call_args = mock_query.connection.query_dataframe.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params["symbol"] == "BTCUSDT"


class TestGetRangeValidation:
    """Test get_range() parameter validation."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        mock_conn.query_dataframe.return_value = pd.DataFrame()
        return OHLCVQuery(mock_conn)

    def test_empty_symbol_raises(self, mock_query):
        """Empty symbol raises ValueError."""
        with pytest.raises(ValueError, match="Symbol cannot be empty"):
            mock_query.get_range("", "1h", start="2024-01-01", end="2024-01-02")

    def test_empty_timeframe_raises(self, mock_query):
        """Empty timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Timeframe cannot be empty"):
            mock_query.get_range("BTCUSDT", "", start="2024-01-01", end="2024-01-02")

    def test_invalid_start_date_format_raises(self, mock_query):
        """Invalid start date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            mock_query.get_range("BTCUSDT", "1h", start="not-a-date", end="2024-01-02")

    def test_invalid_end_date_format_raises(self, mock_query):
        """Invalid end date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            mock_query.get_range("BTCUSDT", "1h", start="2024-01-01", end="not-a-date")

    def test_start_after_end_raises(self, mock_query):
        """Start date after end date raises ValueError."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            mock_query.get_range("BTCUSDT", "1h", start="2024-12-31", end="2024-01-01")

    def test_start_equals_end_raises(self, mock_query):
        """Start date equals end date raises ValueError."""
        with pytest.raises(ValueError, match="Start date must be before end date"):
            mock_query.get_range("BTCUSDT", "1h", start="2024-01-01", end="2024-01-01")

    def test_invalid_instrument_type_raises(self, mock_query):
        """Invalid instrument_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid instrument_type"):
            mock_query.get_range(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", instrument_type="um"
            )


class TestGetMultiSymbolValidation:
    """Test get_multi_symbol() parameter validation."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        mock_conn.query_dataframe.return_value = pd.DataFrame()
        return OHLCVQuery(mock_conn)

    def test_empty_symbols_list_raises(self, mock_query):
        """Empty symbols list raises ValueError."""
        with pytest.raises(ValueError, match="Symbols list cannot be empty"):
            mock_query.get_multi_symbol([], "1h", start="2024-01-01", end="2024-01-02")

    def test_empty_timeframe_raises(self, mock_query):
        """Empty timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Timeframe cannot be empty"):
            mock_query.get_multi_symbol(
                ["BTCUSDT"], "", start="2024-01-01", end="2024-01-02"
            )

    def test_invalid_instrument_type_raises(self, mock_query):
        """Invalid instrument_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid instrument_type"):
            mock_query.get_multi_symbol(
                ["BTCUSDT"], "1h", start="2024-01-01", end="2024-01-02", instrument_type="cm"
            )

    def test_symbols_uppercased(self, mock_query):
        """Symbols are automatically uppercased."""
        mock_query.get_multi_symbol(
            ["btcusdt", "ethusdt"], "1h", start="2024-01-01", end="2024-01-02"
        )
        call_args = mock_query.connection.query_dataframe.call_args
        params = call_args.kwargs.get("params", call_args[1].get("params", {}))
        assert params["symbols"] == ["BTCUSDT", "ETHUSDT"]


class TestExecuteSqlValidation:
    """Test execute_sql() parameter validation."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        mock_conn.query_dataframe.return_value = pd.DataFrame()
        return OHLCVQuery(mock_conn)

    def test_empty_sql_raises(self, mock_query):
        """Empty SQL raises ValueError."""
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            mock_query.execute_sql("")

    def test_whitespace_sql_raises(self, mock_query):
        """Whitespace-only SQL raises ValueError."""
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            mock_query.execute_sql("   ")

    def test_none_sql_raises(self, mock_query):
        """None SQL raises ValueError."""
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            mock_query.execute_sql(None)


class TestDetectGapsValidation:
    """Test detect_gaps() parameter validation."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        mock_conn.query_dataframe.return_value = pd.DataFrame()
        return OHLCVQuery(mock_conn)

    def test_unsupported_timeframe_raises(self, mock_query):
        """Unsupported timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            mock_query.detect_gaps("BTCUSDT", "7h", start="2024-01-01", end="2024-01-02")

    def test_invalid_instrument_type_raises(self, mock_query):
        """Invalid instrument_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid instrument_type"):
            mock_query.detect_gaps(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", instrument_type="um"
            )

    def test_supported_timeframes(self, mock_query):
        """All standard timeframes are supported."""
        supported = ["1s", "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d"]
        for tf in supported:
            # Should not raise
            mock_query.detect_gaps("BTCUSDT", tf, start="2024-01-01", end="2024-01-02")


class TestQueryResults:
    """Test query result handling."""

    @pytest.fixture
    def mock_query(self):
        """Create OHLCVQuery with mocked connection."""
        from gapless_crypto_clickhouse.clickhouse.connection import ClickHouseConnection

        mock_conn = MagicMock(spec=ClickHouseConnection)
        return OHLCVQuery(mock_conn)

    def test_get_latest_reverses_order(self, mock_query):
        """get_latest reverses results to chronological order."""
        # Mock returns descending order (newest first)
        mock_df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="1h")[::-1],
            "close": [103, 102, 101],
        })
        mock_query.connection.query_dataframe.return_value = mock_df

        result = mock_query.get_latest("BTCUSDT", "1h", limit=3)

        # Result should be ascending (oldest first)
        assert result["close"].tolist() == [101, 102, 103]

    def test_get_range_returns_empty_dataframe(self, mock_query):
        """get_range returns empty DataFrame when no data."""
        mock_query.connection.query_dataframe.return_value = pd.DataFrame()

        result = mock_query.get_range("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
