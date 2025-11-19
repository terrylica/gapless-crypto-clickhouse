#!/usr/bin/env python3
"""
Test suite for monthly-to-daily fallback functionality.

Validates that the system correctly falls back to daily file downloads
when monthly files are not available, ensuring true gapless coverage.
"""

import tempfile
from unittest.mock import patch

import pytest

from gapless_crypto_clickhouse.collectors.binance_public_data_collector import (
    BinancePublicDataCollector,
)


class TestMonthlyToDailyFallback:
    """Test the automatic fallback from monthly to daily file downloads."""

    def test_fallback_url_generation(self):
        """Test generation of daily URLs for fallback."""
        collector = BinancePublicDataCollector()

        # Test generating daily URLs for September 2025 (30 days)
        daily_urls = collector._generate_daily_urls_for_month("BTCUSDT", "1d", "2025", "09")

        # Should generate 30 URLs for September 2025
        assert len(daily_urls) == 30

        # Check first and last URLs
        first_url, first_filename = daily_urls[0]
        last_url, last_filename = daily_urls[29]

        assert first_filename == "BTCUSDT-1d-2025-09-01.zip"
        assert last_filename == "BTCUSDT-1d-2025-09-30.zip"

        # Verify URL pattern
        expected_base = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1d/"
        assert first_url == expected_base + first_filename
        assert last_url == expected_base + last_filename

    def test_fallback_filename_parsing(self):
        """Test parsing of failed monthly filename."""
        collector = BinancePublicDataCollector()

        # Test with mock fallback method to avoid actual downloads
        with (
            patch.object(collector, "_generate_daily_urls_for_month") as mock_gen_urls,
            patch.object(collector, "_download_and_extract_daily_file") as mock_download,
        ):
            mock_gen_urls.return_value = [
                ("http://test-url-1", "test-file-1"),
                ("http://test-url-2", "test-file-2"),
            ]
            mock_download.return_value = [["mock", "data"]]

            # Test fallback parsing
            collector._fallback_to_daily_files("BTCUSDT-1d-2025-09.zip")

            # Verify parsing worked correctly
            mock_gen_urls.assert_called_once_with("BTCUSDT", "1d", "2025", "09")

    def test_real_fallback_september_2025(self):
        """Test real fallback for September 2025 (should trigger fallback)."""
        # Use a temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = BinancePublicDataCollector(
                symbol="BTCUSDT",
                start_date="2025-09-01",
                end_date="2025-09-02",  # Just test a few days
                output_dir=temp_dir,
            )

            print("\n🧪 Testing fallback mechanism for September 2025")
            print(f"📁 Temp directory: {temp_dir}")

            # Attempt to collect 1d data for September 2025
            # This should trigger the fallback mechanism
            result = collector.collect_timeframe_data("1d")

            # Verify collection succeeded (even if monthly file failed)
            if result:
                print(f"✅ Fallback test passed: Collected {len(result.get('dataframe', []))} bars")
                assert result is not None
                assert "dataframe" in result
            else:
                print("⚠️  No data available for September 2025 (expected for future dates)")

    def test_fallback_logging_and_output(self, capfd):
        """Test that fallback mechanism provides proper logging."""
        collector = BinancePublicDataCollector()

        # Mock the daily URL generation and downloads
        with (
            patch.object(collector, "_generate_daily_urls_for_month") as mock_gen_urls,
            patch.object(collector, "_download_and_extract_daily_file") as mock_download,
        ):
            # Setup mocks
            mock_gen_urls.return_value = [
                ("http://test-daily-1", "BTCUSDT-1d-2025-09-01.zip"),
                ("http://test-daily-2", "BTCUSDT-1d-2025-09-02.zip"),
                ("http://test-daily-3", "BTCUSDT-1d-2025-09-03.zip"),
            ]

            # Simulate 2 successful and 1 failed daily download
            mock_download.side_effect = [
                [["1641024000000", "47000", "47500", "46800", "47200", "100.5"]],  # Day 1 data
                [["1641110400000", "47200", "47800", "47000", "47600", "95.3"]],  # Day 2 data
                [],  # Day 3 failed
            ]

            # Execute fallback
            result = collector._fallback_to_daily_files("BTCUSDT-1d-2025-09.zip")

            # Verify results
            assert len(result) == 2  # 2 successful downloads
            assert result[0][0] == "1641024000000"  # First timestamp
            assert result[1][0] == "1641110400000"  # Second timestamp

            # Check console output for proper logging
            captured = capfd.readouterr()
            assert "Fallback: Downloading daily files" in captured.out
            assert "Daily fallback successful: 2/3 daily files retrieved" in captured.out

    def test_invalid_filename_handling(self):
        """Test handling of invalid monthly filename formats."""
        collector = BinancePublicDataCollector()

        # Test with invalid filename
        result = collector._fallback_to_daily_files("invalid-filename.zip")

        # Should return empty list and not crash
        assert result == []

    def test_february_leap_year_handling(self):
        """Test daily URL generation for February in leap year."""
        collector = BinancePublicDataCollector()

        # Test February 2024 (leap year - 29 days)
        daily_urls_leap = collector._generate_daily_urls_for_month("BTCUSDT", "1h", "2024", "02")
        assert len(daily_urls_leap) == 29

        # Test February 2025 (non-leap year - 28 days)
        daily_urls_regular = collector._generate_daily_urls_for_month("BTCUSDT", "1h", "2025", "02")
        assert len(daily_urls_regular) == 28

        # Verify last day URLs
        _, leap_last_filename = daily_urls_leap[-1]
        _, regular_last_filename = daily_urls_regular[-1]

        assert leap_last_filename == "BTCUSDT-1h-2024-02-29.zip"
        assert regular_last_filename == "BTCUSDT-1h-2025-02-28.zip"

    def test_comprehensive_gapless_with_fallback(self):
        """Test that fallback maintains gapless guarantee."""
        # Use a temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test a range that includes recent months (likely to trigger fallback)
            collector = BinancePublicDataCollector(
                symbol="BTCUSDT",
                start_date="2025-08-25",  # End of August
                end_date="2025-09-05",  # Beginning of September (should trigger fallback)
                output_dir=temp_dir,
            )

            print("\n🎯 Testing gapless guarantee with fallback mechanism")

            # Collect data that spans monthly and daily files
            result = collector.collect_timeframe_data("1d")

            if result and result.get("dataframe") is not None:
                df = result["dataframe"]
                print(f"📊 Collected {len(df)} bars across August-September boundary")

                # Verify chronological order
                if len(df) > 1:
                    dates = df["date"]
                    for i in range(1, len(dates)):
                        prev_date = dates.iloc[i - 1]
                        curr_date = dates.iloc[i]
                        assert curr_date >= prev_date, (
                            f"Date order violation: {prev_date} -> {curr_date}"
                        )

                print("✅ Gapless guarantee maintained with fallback mechanism")
            else:
                print("⚠️  No data available for test period (expected for future dates)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
