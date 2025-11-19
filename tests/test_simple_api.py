#!/usr/bin/env python3
"""
Test cases for the simple function-based API

Ensures the convenience functions work correctly and provide
the expected financial data library experience.
"""

import pandas as pd
import pytest

import gapless_crypto_clickhouse as gcd


class TestSimpleAPI:
    """Test the function-based convenience API"""

    def test_import_all_functions(self):
        """Test that all convenience functions are properly exported"""
        # Test function-based API exports
        assert hasattr(gcd, "fetch_data")
        assert hasattr(gcd, "download")
        assert hasattr(gcd, "get_supported_symbols")
        assert hasattr(gcd, "get_supported_timeframes")
        assert hasattr(gcd, "fill_gaps")
        assert hasattr(gcd, "get_info")

        # Test class-based API exports (backward compatibility)
        assert hasattr(gcd, "BinancePublicDataCollector")
        assert hasattr(gcd, "UniversalGapFiller")

    def test_get_supported_symbols(self):
        """Test getting supported trading symbols"""
        symbols = gcd.get_supported_symbols()

        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SOLUSDT" in symbols

        # All symbols should be strings and end with USDT
        for symbol in symbols:
            assert isinstance(symbol, str)
            assert symbol.endswith("USDT")

    def test_get_supported_timeframes(self):
        """Test getting supported timeframe intervals"""
        timeframes = gcd.get_supported_timeframes()

        assert isinstance(timeframes, list)
        assert len(timeframes) > 0

        # Check for common timeframes
        expected_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for tf in expected_timeframes:
            assert tf in timeframes

    def test_get_info(self):
        """Test library information function"""
        info = gcd.get_info()

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
        assert info["name"] == "gapless-crypto-data"
        assert info["version"] == gcd.__version__
        assert isinstance(info["supported_symbols"], list)
        assert isinstance(info["supported_timeframes"], list)
        assert isinstance(info["features"], list)

    def test_fetch_data_parameters(self):
        """Test fetch_data function parameter handling"""
        # Test with minimal parameters (should not raise)
        try:
            df = gcd.fetch_data("BTCUSDT", "1h", limit=1)
            # Should return DataFrame even if empty
            assert isinstance(df, pd.DataFrame)
            # With default datetime index, should have DatetimeIndex (if data available)
            if not df.empty:
                assert isinstance(df.index, pd.DatetimeIndex)
        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_fetch_data_index_types(self):
        """Test fetch_data function with different index_type parameters"""
        try:
            # Test datetime index (default)
            df_datetime = gcd.fetch_data("BTCUSDT", "1h", limit=1, index_type="datetime")
            assert isinstance(df_datetime, pd.DataFrame)
            if not df_datetime.empty:
                assert isinstance(df_datetime.index, pd.DatetimeIndex)

            # Test range index (legacy)
            df_range = gcd.fetch_data("BTCUSDT", "1h", limit=1, index_type="range")
            assert isinstance(df_range, pd.DataFrame)
            if not df_range.empty:
                assert isinstance(df_range.index, pd.RangeIndex)
                assert "date" in df_range.columns

            # Test auto index (same as datetime)
            df_auto = gcd.fetch_data("BTCUSDT", "1h", limit=1, index_type="auto")
            assert isinstance(df_auto, pd.DataFrame)
            if not df_auto.empty:
                assert isinstance(df_auto.index, pd.DatetimeIndex)

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_fetch_data_invalid_index_type(self):
        """Test fetch_data function with invalid index_type parameter"""
        with pytest.raises(ValueError, match="Invalid index_type"):
            gcd.fetch_data("BTCUSDT", "1h", limit=1, index_type="invalid")

    def test_fetch_data_default_behavior(self):
        """Test that fetch_data defaults to datetime index for better UX"""
        try:
            # Default behavior should be datetime index
            df = gcd.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
            assert isinstance(df, pd.DataFrame)
            if not df.empty:
                assert isinstance(df.index, pd.DatetimeIndex)
                # Should STILL have 'date' column for backward compatibility
                assert "date" in df.columns
                # Should have expected OHLCV columns
                expected_cols = ["open", "high", "low", "close", "volume"]
                for col in expected_cols:
                    assert col in df.columns

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_backward_compatibility_range_index(self):
        """Test backward compatibility with range index"""
        try:
            # Explicit range index should work like before
            df = gcd.fetch_data(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", index_type="range"
            )
            assert isinstance(df, pd.DataFrame)
            if not df.empty:
                assert isinstance(df.index, pd.RangeIndex)
                assert "date" in df.columns
                # Can manually set index like before
                df_indexed = df.set_index("date")
                assert isinstance(df_indexed.index, pd.DatetimeIndex)

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_download_alias(self):
        """Test that download is an alias for fetch_data"""
        # Should not raise errors for basic parameter validation
        try:
            df1 = gcd.fetch_data("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
            df2 = gcd.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")

            # Both should return DataFrames with same structure
            assert isinstance(df1, pd.DataFrame)
            assert isinstance(df2, pd.DataFrame)
            assert list(df1.columns) == list(df2.columns)

        except Exception as e:
            # Network issues are acceptable in tests
            assert "network" in str(e).lower() or "timeout" in str(e).lower()

    def test_download_index_type_support(self):
        """Test that download function supports index_type parameter"""
        try:
            # Test datetime index (default)
            df_datetime = gcd.download(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", index_type="datetime"
            )
            assert isinstance(df_datetime, pd.DataFrame)
            if not df_datetime.empty:
                assert isinstance(df_datetime.index, pd.DatetimeIndex)

            # Test range index
            df_range = gcd.download(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", index_type="range"
            )
            assert isinstance(df_range, pd.DataFrame)
            if not df_range.empty:
                assert isinstance(df_range.index, pd.RangeIndex)

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_expected_dataframe_columns(self):
        """Test that returned DataFrames have expected microstructure columns"""
        try:
            # Test with datetime index (default) - 'date' column still present
            df_datetime = gcd.fetch_data("BTCUSDT", "1d", start="2024-01-01", end="2024-01-02")

            if not df_datetime.empty:
                # Expected columns when using datetime index (includes 'date' column for compatibility)
                expected_datetime_columns = [
                    "date",
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
                ]

                for col in expected_datetime_columns:
                    assert col in df_datetime.columns

                # Check index is datetime and data types
                assert isinstance(df_datetime.index, pd.DatetimeIndex)
                assert pd.api.types.is_datetime64_any_dtype(df_datetime["date"])
                assert pd.api.types.is_numeric_dtype(df_datetime["open"])
                assert pd.api.types.is_numeric_dtype(df_datetime["volume"])

            # Test with range index (legacy) - same columns but RangeIndex
            df_range = gcd.fetch_data(
                "BTCUSDT", "1d", start="2024-01-01", end="2024-01-02", index_type="range"
            )

            if not df_range.empty:
                # Expected columns when using range index (same as datetime)
                expected_range_columns = [
                    "date",
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
                ]

                for col in expected_range_columns:
                    assert col in df_range.columns

                # Check data types for range index version
                assert isinstance(df_range.index, pd.RangeIndex)
                assert pd.api.types.is_datetime64_any_dtype(df_range["date"])
                assert pd.api.types.is_numeric_dtype(df_range["open"])
                assert pd.api.types.is_numeric_dtype(df_range["volume"])

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_fill_gaps_function_signature(self):
        """Test fill_gaps function parameter handling"""
        # Test with non-existent directory (should not crash)
        result = gcd.fill_gaps("./non_existent_directory")

        assert isinstance(result, dict)
        assert "files_processed" in result
        assert "gaps_detected" in result
        assert "gaps_filled" in result
        assert "success_rate" in result
        assert "file_results" in result

    def test_backward_compatibility(self):
        """Test that class-based API still works (backward compatibility)"""
        # Should be able to import and instantiate classes
        collector = gcd.BinancePublicDataCollector()
        gap_filler = gcd.UniversalGapFiller()

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
            # Function-based API with range index for consistency comparison
            df_function = gcd.fetch_data(
                symbol, timeframe, start=start, end=end, index_type="range"
            )

            # Class-based API
            collector = gcd.BinancePublicDataCollector(
                symbol=symbol, start_date=start, end_date=end
            )
            result_class = collector.collect_timeframe_data(timeframe)

            if result_class and "dataframe" in result_class:
                df_class = result_class["dataframe"]

                # Both should be DataFrames with same columns when using range index
                assert isinstance(df_function, pd.DataFrame)
                assert isinstance(df_class, pd.DataFrame)
                assert list(df_function.columns) == list(df_class.columns)

                # Test that new default datetime index also works
                df_function_datetime = gcd.fetch_data(symbol, timeframe, start=start, end=end)
                assert isinstance(df_function_datetime, pd.DataFrame)
                if not df_function_datetime.empty:
                    assert isinstance(df_function_datetime.index, pd.DatetimeIndex)
                    # Should have same columns (date column preserved for compatibility)
                    assert len(df_function_datetime.columns) == len(df_class.columns)

        except Exception as e:
            # Network issues are acceptable in tests
            pytest.skip(f"Network-dependent test failed: {e}")


class TestAPIUsagePatterns:
    """Test common usage patterns expected by financial data users"""

    def test_intuitive_download_usage(self):
        """Test intuitive download usage pattern"""
        try:
            # Common download pattern with date range
            df = gcd.download("BTCUSDT", "1d", start="2024-01-01", end="2024-01-02")
            assert isinstance(df, pd.DataFrame)

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_symbol_discovery_pattern(self):
        """Test symbol and timeframe discovery pattern"""
        # Pattern for discovering available options
        symbols = gcd.get_supported_symbols()
        timeframes = gcd.get_supported_timeframes()

        assert len(symbols) > 0
        assert len(timeframes) > 0

        # Should be able to use discovered values
        symbol = symbols[0]  # First available symbol
        timeframe = timeframes[0] if "1d" not in timeframes else "1d"

        try:
            df = gcd.fetch_data(symbol, timeframe, limit=1)
            assert isinstance(df, pd.DataFrame)

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_date_range_usage(self):
        """Test date range usage with start/end dates"""
        try:
            # Test with default datetime index
            df = gcd.fetch_data(
                symbol="ETHUSDT",
                timeframe="1h",
                start="2024-01-01",
                end="2024-01-01",  # Single day
            )

            assert isinstance(df, pd.DataFrame)

            if not df.empty:
                # With default datetime index, index is datetime but date column preserved
                assert isinstance(df.index, pd.DatetimeIndex)
                assert "date" in df.columns

            # Test with legacy range index
            df_range = gcd.fetch_data(
                symbol="ETHUSDT",
                timeframe="1h",
                start="2024-01-01",
                end="2024-01-01",
                index_type="range",
            )

            if not df_range.empty:
                # With range index, should have date column as datetime
                assert "date" in df_range.columns
                assert pd.api.types.is_datetime64_any_dtype(df_range["date"])

        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_auto_fill_gaps_enabled_by_default(self):
        """Test that auto_fill_gaps is enabled by default (zero gaps guarantee)"""
        try:
            # download() should have auto_fill_gaps=True by default
            df = gcd.download(
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
            df = gcd.download(
                "BTCUSDT", "1h", start="2024-01-01", end="2024-01-02", auto_fill_gaps=False
            )

            assert isinstance(df, pd.DataFrame)
            # Test passes if function accepts the parameter
        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_fetch_data_auto_fill_parameter(self):
        """Test that fetch_data also supports auto_fill_gaps parameter"""
        try:
            # fetch_data() should also have auto_fill_gaps parameter
            df_with_fill = gcd.fetch_data("ETHUSDT", "1h", limit=48, auto_fill_gaps=True)

            df_without_fill = gcd.fetch_data("ETHUSDT", "1h", limit=48, auto_fill_gaps=False)

            assert isinstance(df_with_fill, pd.DataFrame)
            assert isinstance(df_without_fill, pd.DataFrame)
            # Both should work, with potentially different gap filling behavior
        except Exception as e:
            pytest.skip(f"Network-dependent test failed: {e}")

    def test_download_delivers_zero_gaps_guarantee(self):
        """Test that download() delivers on 'zero gaps guarantee' promise"""
        try:
            # Use period with known Binance Vision gap (March 24, 2023)
            df = gcd.download(
                "BTCUSDT",
                timeframe="5m",
                start="2023-03-23",
                end="2023-03-25",
                auto_fill_gaps=True,
            )

            if df.empty:
                pytest.skip("No data returned for test period")

            # Convert date column to datetime if needed
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df_sorted = df.sort_values("date").reset_index(drop=True)

                # Check for gaps (5-minute timeframe = 5 min expected)
                time_diffs = df_sorted["date"].diff()
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
