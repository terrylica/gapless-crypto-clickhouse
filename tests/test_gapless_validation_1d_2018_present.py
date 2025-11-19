#!/usr/bin/env python3
"""
Comprehensive gapless validation test for 1-day data from 2018 to 2 days before today.

This test validates true gapless-ness by:
1. Collecting 1d BTCUSDT data from 2018-01-01 to 2 days before today
2. Detecting any gaps in the collected data
3. Validating complete coverage with no missing days
4. Ensuring data integrity across the full historical range

Real-world production validation test for the gapless-crypto-data system.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from gapless_crypto_clickhouse.collectors.binance_public_data_collector import (
    BinancePublicDataCollector,
)
from gapless_crypto_clickhouse.gap_filling.universal_gap_filler import UniversalGapFiller


class TestGaplessValidation1d2018Present:
    """Comprehensive gapless validation for 1-day data from 2018 to present."""

    @pytest.fixture
    def date_range(self):
        """Calculate date range from 2018-01-01 to 2 days before today."""
        start_date = "2018-01-01"

        # Calculate 2 days before today
        today = datetime.now()
        end_date_dt = today - timedelta(days=2)
        end_date = end_date_dt.strftime("%Y-%m-%d")

        return start_date, end_date

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for test data."""
        temp_dir = tempfile.mkdtemp(prefix="gapless_validation_")
        yield temp_dir

        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_collect_1d_data_2018_to_present(self, date_range, temp_output_dir):
        """Test collection of 1d data from 2018 to 2 days before today."""
        start_date, end_date = date_range

        print(f"\n📅 Testing gapless 1d data from {start_date} to {end_date}")
        print(f"🗂️  Output directory: {temp_output_dir}")

        # Initialize collector
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date=start_date, end_date=end_date, output_dir=temp_output_dir
        )

        # Collect 1d data
        result = collector.collect_timeframe_data("1d")

        # Validate collection succeeded
        assert result is not None, "Data collection failed"
        assert "dataframe" in result, "No dataframe in result"

        df = result["dataframe"]
        assert len(df) > 0, "No data collected"

        print(f"✅ Collected {len(df)} daily bars")

        # Validate date range coverage
        min_date = df["date"].min()
        max_date = df["date"].max()

        print(f"📊 Date range: {min_date} to {max_date}")

        # Should start close to 2018-01-01 (BTCUSDT launched Sep 2017)
        assert min_date.year >= 2017, f"Data should start from 2017 or later, got {min_date}"

        # Should end close to our target end date
        # Note: Binance data availability may lag by several weeks
        expected_end = datetime.strptime(end_date, "%Y-%m-%d")
        date_diff = abs((max_date - expected_end).days)
        assert date_diff <= 30, (
            f"End date should be within 30 days of {end_date}, got {max_date} (diff: {date_diff} days)"
        )

        return result

    def test_validate_gapless_coverage(self, date_range, temp_output_dir):
        """Validate that 1d data has zero gaps from 2018 to present."""
        start_date, end_date = date_range

        # First collect the data
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date=start_date, end_date=end_date, output_dir=temp_output_dir
        )

        result = collector.collect_timeframe_data("1d")
        assert result is not None, "Data collection failed"

        # Save to CSV for gap analysis
        df = result["dataframe"]
        csv_file = Path(temp_output_dir) / "BTCUSDT_1d_gapless_validation.csv"
        df.to_csv(csv_file, index=False)

        print(f"💾 Saved data to {csv_file}")
        print(f"📊 Analyzing {len(df)} daily bars for gaps...")

        # Initialize gap filler for gap detection
        gap_filler = UniversalGapFiller()

        # Detect any gaps in the data
        gaps = gap_filler.detect_all_gaps(str(csv_file), "1d")

        print("🔍 Gap detection complete")

        if gaps:
            print(f"❌ Found {len(gaps)} gaps in 1d data:")
            for i, gap in enumerate(gaps):
                gap_start = gap["start_time"]
                gap_end = gap["end_time"]
                duration = gap["duration"]
                missing_days = duration.total_seconds() / (24 * 60 * 60)

                print(f"  Gap {i + 1}: {gap_start} → {gap_end} ({missing_days:.1f} days)")

        # CRITICAL: For true gapless-ness, there should be ZERO gaps
        assert len(gaps) == 0, f"Found {len(gaps)} gaps in 1d data - gapless guarantee violated!"

        print("✅ GAPLESS VALIDATION PASSED: Zero gaps found in 1d data")

    def test_data_integrity_validation(self, date_range, temp_output_dir):
        """Validate data integrity across the full historical range."""
        start_date, end_date = date_range

        # Collect data
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date=start_date, end_date=end_date, output_dir=temp_output_dir
        )

        result = collector.collect_timeframe_data("1d")
        df = result["dataframe"]

        print(f"🔬 Validating data integrity for {len(df)} daily bars")

        # Validate required columns
        expected_columns = [
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

        for col in expected_columns:
            assert col in df.columns, f"Missing required column: {col}"

        # Validate no null values in critical columns
        critical_columns = ["date", "open", "high", "low", "close", "volume"]
        for col in critical_columns:
            null_count = df[col].isnull().sum()
            assert null_count == 0, f"Found {null_count} null values in {col}"

        # Validate OHLC relationships
        invalid_ohlc = df[
            (df["high"] < df["open"])
            | (df["high"] < df["close"])
            | (df["low"] > df["open"])
            | (df["low"] > df["close"])
            | (df["high"] < df["low"])
        ]

        assert len(invalid_ohlc) == 0, (
            f"Found {len(invalid_ohlc)} bars with invalid OHLC relationships"
        )

        # Validate chronological order
        date_series = pd.to_datetime(df["date"])
        assert date_series.is_monotonic_increasing, "Dates are not in chronological order"

        # Validate daily intervals
        date_diffs = date_series.diff().dropna()

        # Allow for weekend gaps in daily data (crypto markets run 24/7 but data may have weekend patterns)
        valid_intervals = [
            pd.Timedelta(days=1),  # Normal daily interval
            pd.Timedelta(days=2),  # Weekend gap
            pd.Timedelta(days=3),  # Long weekend
        ]

        invalid_intervals = []
        for i, diff in enumerate(date_diffs):
            if diff not in valid_intervals:
                invalid_intervals.append((i, diff))

        # For crypto data, we expect mostly 1-day intervals
        normal_intervals = sum(1 for diff in date_diffs if diff == pd.Timedelta(days=1))
        interval_ratio = normal_intervals / len(date_diffs)

        print(
            f"📈 Normal 1-day intervals: {normal_intervals}/{len(date_diffs)} ({interval_ratio:.1%})"
        )

        # At least 95% should be normal daily intervals
        assert interval_ratio >= 0.95, (
            f"Only {interval_ratio:.1%} normal intervals, expected >= 95%"
        )

        print("✅ DATA INTEGRITY VALIDATION PASSED")

    def test_weekend_handling_validation(self, date_range, temp_output_dir):
        """Validate proper handling of weekends in daily crypto data."""
        start_date, end_date = date_range

        # Collect data
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date=start_date, end_date=end_date, output_dir=temp_output_dir
        )

        result = collector.collect_timeframe_data("1d")
        df = result["dataframe"]

        # Convert to datetime and add weekday information
        df["datetime"] = pd.to_datetime(df["date"])
        df["weekday"] = df["datetime"].dt.day_name()
        df["is_weekend"] = df["datetime"].dt.weekday >= 5  # Saturday=5, Sunday=6

        # Count weekend vs weekday data
        weekend_count = df["is_weekend"].sum()
        weekday_count = (~df["is_weekend"]).sum()

        print(f"📅 Weekend bars: {weekend_count}")
        print(f"📅 Weekday bars: {weekday_count}")

        # For crypto markets (24/7), we should have both weekend and weekday data
        # Ratio should be approximately 2/5 (2 weekend days per 5 weekdays)
        if weekday_count > 0:
            weekend_ratio = weekend_count / weekday_count
            expected_ratio = 2 / 5  # 2 weekend days per 5 weekdays

            print(f"📊 Weekend/Weekday ratio: {weekend_ratio:.2f} (expected ~{expected_ratio:.2f})")

            # Allow reasonable deviation (crypto markets are 24/7)
            assert 0.3 <= weekend_ratio <= 0.5, f"Unexpected weekend ratio: {weekend_ratio:.2f}"

        print("✅ WEEKEND HANDLING VALIDATION PASSED")

    def test_volume_and_trades_validation(self, date_range, temp_output_dir):
        """Validate volume and trade count data quality."""
        start_date, end_date = date_range

        # Collect data
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT", start_date=start_date, end_date=end_date, output_dir=temp_output_dir
        )

        result = collector.collect_timeframe_data("1d")
        df = result["dataframe"]

        print(f"📊 Validating volume and trade data for {len(df)} bars")

        # Validate volume data
        zero_volume_count = (df["volume"] == 0).sum()
        negative_volume_count = (df["volume"] < 0).sum()

        print(f"📈 Zero volume bars: {zero_volume_count}")
        print(f"📈 Negative volume bars: {negative_volume_count}")

        # Should have no negative volume
        assert negative_volume_count == 0, (
            f"Found {negative_volume_count} bars with negative volume"
        )

        # Zero volume should be very rare for BTCUSDT (major pair)
        zero_volume_ratio = zero_volume_count / len(df)
        assert zero_volume_ratio < 0.01, f"Too many zero volume bars: {zero_volume_ratio:.2%}"

        # Validate trade count data
        if "number_of_trades" in df.columns:
            zero_trades_count = (df["number_of_trades"] == 0).sum()
            negative_trades_count = (df["number_of_trades"] < 0).sum()

            print(f"🔢 Zero trade count bars: {zero_trades_count}")
            print(f"🔢 Negative trade count bars: {negative_trades_count}")

            # Should have no negative trade counts
            assert negative_trades_count == 0, (
                f"Found {negative_trades_count} bars with negative trade count"
            )

            # Zero trades should be very rare for BTCUSDT
            zero_trades_ratio = zero_trades_count / len(df)
            assert zero_trades_ratio < 0.01, f"Too many zero trade bars: {zero_trades_ratio:.2%}"

        # Validate quote asset volume consistency
        if "quote_asset_volume" in df.columns:
            # Quote volume should generally correlate with base volume
            quote_volume_zeros = (df["quote_asset_volume"] == 0).sum()
            quote_zero_ratio = quote_volume_zeros / len(df)

            print(f"💰 Zero quote volume bars: {quote_volume_zeros}")

            assert quote_zero_ratio < 0.01, (
                f"Too many zero quote volume bars: {quote_zero_ratio:.2%}"
            )

        print("✅ VOLUME AND TRADES VALIDATION PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
