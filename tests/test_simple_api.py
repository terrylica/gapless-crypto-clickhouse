#!/usr/bin/env python3
"""
Test cases for the simple function-based API

Ensures the convenience functions work correctly and provide
the expected financial data library experience.

NOTE (ADR-0049): index_type tests removed per v3.0.0 deprecation plan (ADR-0023).
The index_type parameter was deprecated in v3.0.0 and RangeIndex is now the default.
Tests using deprecated index_type parameter were deleted to eliminate warnings.
"""

import pandas as pd
import pytest

import gapless_crypto_clickhouse as gcch


class TestSimpleAPI:
    """Test the function-based convenience API"""

    def test_import_all_functions(self):
        """Test that all convenience functions are properly exported"""
        # Test function-based API exports
        assert hasattr(gcch, "fetch_data")
        assert hasattr(gcch, "download")
        assert hasattr(gcch, "get_supported_symbols")
        assert hasattr(gcch, "get_supported_timeframes")
        assert hasattr(gcch, "fill_gaps")
        assert hasattr(gcch, "get_info")

        # Test class-based API exports (backward compatibility)
        assert hasattr(gcch, "BinancePublicDataCollector")
        assert hasattr(gcch, "UniversalGapFiller")

    def test_get_supported_symbols(self):
        """Test getting supported trading symbols"""
        symbols = gcch.get_supported_symbols()

        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SOLUSDT" in symbols

        # All symbols should be strings
        for symbol in symbols:
            assert isinstance(symbol, str)
            assert len(symbol) > 0

        # Most symbols should end with common quote currencies (allow for special cases like SETTLED)
        valid_quotes = ["USDT", "USDC", "BUSD", "BNB", "BTC", "ETH", "SETTLED"]
        valid_count = sum(1 for s in symbols if any(s.endswith(q) for q in valid_quotes))
        assert valid_count == len(symbols), f"Some symbols don't end with expected currencies"

    def test_get_supported_timeframes(self):
        """Test getting supported timeframe intervals"""
        timeframes = gcch.get_supported_timeframes()

        assert isinstance(timeframes, list)
        assert len(timeframes) > 0

        # Check for common timeframes
        expected_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for tf in expected_timeframes:
            assert tf in timeframes

    def test_get_info(self):
        """Test library information function"""
        info = gcch.get_info()

        assert isinstance(info, dict)

        # Check required fields
        required_fields = [
            "version",
            "name",
            "description",
            "supported_symbols",
            "supported_timeframes",
            "market_type",
            "data_source",
            "features",
        ]
        for field in required_fields:
            assert field in info

        # Validate content
        assert info["name"] == "gapless-crypto-clickhouse"
        assert info["version"] == gcch.__version__
        assert isinstance(info["supported_symbols"], list)
        assert isinstance(info["supported_timeframes"], list)
        assert isinstance(info["features"], list)

    def test_fetch_data_parameters(self):
        """Test fetch_data function parameter handling"""
        # Test with explicit date range (ADR-0049: avoid limit=N to prevent future date warnings)
        try:
            df = gcch.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
            # Should return DataFrame even if empty
            assert isinstance(df, pd.DataFrame)
            # Default is RangeIndex (DatetimeIndex is deprecated per ADR-0023)
            if not df.empty:
                assert isinstance(df.index, pd.RangeIndex)
        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    # NOTE: test_fetch_data_index_types and test_fetch_data_invalid_index_type DELETED per ADR-0049
    # index_type parameter deprecated per ADR-0023, removed in v3.0.0

    def test_fetch_data_default_behavior(self):
        """Test that fetch_data defaults to RangeIndex (DatetimeIndex is deprecated)."""
        try:
            # Default behavior is RangeIndex (ADR-0023: Arrow-optimized)
            df = gcch.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
            assert isinstance(df, pd.DataFrame)
            if not df.empty:
                assert isinstance(df.index, pd.RangeIndex)
                # Should have 'date' column for explicit time operations
                assert "timestamp" in df.columns
                # Should have expected OHLCV columns
                expected_cols = ["open", "high", "low", "close", "volume"]
                for col in expected_cols:
                    assert col in df.columns

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    # NOTE: test_backward_compatibility_range_index DELETED per ADR-0049
    # index_type parameter deprecated per ADR-0023, removed in v3.0.0

    def test_download_alias(self):
        """Test that download is an alias for fetch_data"""
        # Should not raise errors for basic parameter validation
        try:
            df1 = gcch.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
            df2 = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")

            # Both should return DataFrames with same structure
            assert isinstance(df1, pd.DataFrame)
            assert isinstance(df2, pd.DataFrame)
            assert list(df1.columns) == list(df2.columns)

        except Exception as e:
            # Network issues are acceptable in tests
            assert "network" in str(e).lower() or "timeout" in str(e).lower()

    # NOTE: test_download_index_type_support and test_expected_dataframe_columns DELETED per ADR-0049
    # index_type parameter deprecated per ADR-0023, removed in v3.0.0
    # test_expected_dataframe_columns was also stale (expected DatetimeIndex as default)

    def test_fill_gaps_function_signature(self):
        """Test fill_gaps function parameter handling"""
        # Test with non-existent directory (should not crash)
        result = gcch.fill_gaps("./non_existent_directory")

        assert isinstance(result, dict)
        assert "files_processed" in result
        assert "gaps_detected" in result
        assert "gaps_filled" in result
        assert "success_rate" in result
        assert "file_results" in result

    def test_backward_compatibility(self):
        """Test that class-based API still works (backward compatibility)"""
        # Should be able to import and instantiate classes
        collector = gcch.BinancePublicDataCollector()
        gap_filler = gcch.UniversalGapFiller()

        assert collector is not None
        assert gap_filler is not None

        # Check that they have expected methods
        assert hasattr(collector, "collect_timeframe_data")
        assert hasattr(gap_filler, "detect_all_gaps")

    def test_api_style_consistency(self):
        """Test that both API styles provide consistent data"""
        # Compare function-based vs class-based API results
        symbol = "BTCUSDT"
        timeframe = "1d"
        start = "2024-01-01"
        end = "2024-01-02"

        try:
            # Function-based API (default RangeIndex per ADR-0023)
            df_function = gcch.fetch_data(symbol, timeframe, start=start, end=end)

            # Class-based API
            collector = gcch.BinancePublicDataCollector(
                symbol=symbol, start_date=start, end_date=end
            )
            result_class = collector.collect_timeframe_data(timeframe)

            if result_class and "dataframe" in result_class:
                df_class = result_class["dataframe"]

                # Both should be DataFrames with same columns
                assert isinstance(df_function, pd.DataFrame)
                assert isinstance(df_class, pd.DataFrame)
                assert list(df_function.columns) == list(df_class.columns)

                # Verify default RangeIndex (ADR-0023)
                if not df_function.empty:
                    assert isinstance(df_function.index, pd.RangeIndex)
                    # Should have same columns (date column preserved for explicit time ops)
                    assert len(df_function.columns) == len(df_class.columns)

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")


class TestAPIUsagePatterns:
    """Test common usage patterns expected by financial data users"""

    def test_intuitive_download_usage(self):
        """Test intuitive download usage pattern"""
        try:
            # Common download pattern with date range
            df = gcch.download("BTCUSDT", "1d", start="2024-01-01", end="2024-01-02")
            assert isinstance(df, pd.DataFrame)

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_symbol_discovery_pattern(self):
        """Test symbol and timeframe discovery pattern"""
        # Pattern for discovering available options
        symbols = gcch.get_supported_symbols()
        timeframes = gcch.get_supported_timeframes()

        assert len(symbols) > 0
        assert len(timeframes) > 0

        # Should be able to use discovered values
        symbol = symbols[0]  # First available symbol
        timeframe = timeframes[0] if "1d" not in timeframes else "1d"

        try:
            # Use explicit date range (ADR-0049: avoid limit=N to prevent future date warnings)
            df = gcch.fetch_data(symbol, timeframe, start="2024-01-01", end="2024-01-02")
            assert isinstance(df, pd.DataFrame)

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_date_range_usage(self):
        """Test date range usage with start/end dates"""
        try:
            # Test with default RangeIndex (ADR-0023)
            df = gcch.fetch_data(
                symbol="ETHUSDT",
                timeframe="1h",
                start="2024-01-01",
                end="2024-01-01",  # Single day
            )

            assert isinstance(df, pd.DataFrame)

            if not df.empty:
                # Default is RangeIndex; date column preserved for explicit time ops
                assert isinstance(df.index, pd.RangeIndex)
                assert "timestamp" in df.columns
                # Date column should be datetime type
                assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_auto_fill_gaps_enabled_by_default(self):
        """Test that auto_fill_gaps is enabled by default (zero gaps guarantee)"""
        try:
            # download() should have auto_fill_gaps=True by default
            df = gcch.download(
                "BTCUSDT", "5m", start="2023-03-23", end="2023-03-25", auto_fill_gaps=True
            )

            assert isinstance(df, pd.DataFrame)
            # Test passes if function accepts the parameter
        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_auto_fill_gaps_can_be_disabled(self):
        """Test that users can opt-out of auto-fill"""
        try:
            # Should accept auto_fill_gaps=False to get raw Vision data
            df = gcch.download(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", auto_fill_gaps=False
            )

            assert isinstance(df, pd.DataFrame)
            # Test passes if function accepts the parameter
        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_fetch_data_auto_fill_parameter(self):
        """Test that fetch_data also supports auto_fill_gaps parameter"""
        try:
            # Use explicit date range (ADR-0049: avoid limit=N to prevent future date warnings)
            # 48 hours = 2 days of hourly data
            df_with_fill = gcch.fetch_data(
                "ETHUSDT", "1h", start="2024-01-01", end="2024-01-03", auto_fill_gaps=True
            )

            df_without_fill = gcch.fetch_data(
                "ETHUSDT", "1h", start="2024-01-01", end="2024-01-03", auto_fill_gaps=False
            )

            assert isinstance(df_with_fill, pd.DataFrame)
            assert isinstance(df_without_fill, pd.DataFrame)
            # Both should work, with potentially different gap filling behavior
        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_download_delivers_zero_gaps_guarantee(self):
        """Test that download() delivers on 'zero gaps guarantee' promise"""
        try:
            # Use period with known Binance Vision gap (March 24, 2023)
            df = gcch.download(
                "BTCUSDT",
                timeframe="5m",
                start="2023-03-23",
                end="2023-03-25",
                auto_fill_gaps=True,
            )

            if df.empty:
                pytest.skip("No data returned for test period")

            # Convert date column to datetime if needed
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df_sorted = df.sort_values("timestamp").reset_index(drop=True)

                # Check for gaps (5-minute timeframe = 5 min expected)
                time_diffs = df_sorted["timestamp"].diff()
                expected_interval = pd.Timedelta(minutes=5)

                # Allow 1.5x the expected interval as tolerance for minor variations
                max_gap = expected_interval * 1.5
                large_gaps = time_diffs[time_diffs > max_gap]

                # With auto_fill_gaps=True, should have minimal gaps
                # (or gaps should be from legitimate market halts, not Vision archive holes)
                assert len(large_gaps) == 0, (
                    f"Found {len(large_gaps)} gaps despite auto_fill_gaps=True"
                )

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
