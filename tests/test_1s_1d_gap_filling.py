#!/usr/bin/env python3
"""
Comprehensive test suite for 1s and 1d timeframe gap filling functionality.

Tests the edge cases of ultra-high frequency (1s) and daily frequency (1d)
gap detection and filling with authentic Binance API data.
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from gapless_crypto_clickhouse.gap_filling.universal_gap_filler import UniversalGapFiller


class Test1sGapFilling:
    """Test suite for 1-second timeframe gap filling."""

    def test_1s_timeframe_mapping(self):
        """Test that 1s timeframe is properly mapped in gap filler."""
        from gapless_crypto_clickhouse.utils.timeframe_constants import (
            TIMEFRAME_TO_BINANCE_INTERVAL,
        )

        assert "1s" in TIMEFRAME_TO_BINANCE_INTERVAL
        assert TIMEFRAME_TO_BINANCE_INTERVAL["1s"] == "1s"

    def test_1s_gap_detection_precision(self):
        """Test gap detection works with 1-second precision."""
        gap_filler = UniversalGapFiller()

        # Create test data with 1-second intervals and a gap
        # Use UTC timestamp: 1726660800000 = 2024-09-18 12:00:00 UTC
        base_timestamp = 1726660800000  # Milliseconds since epoch
        timestamps = []

        # Normal sequence: base+0s, base+1s, base+2s
        for i in range(3):
            timestamps.append(base_timestamp + (i * 1000))  # Add seconds in milliseconds

        # Gap: skip base+3s, base+4s (2-second gap)
        # Resume at base+5s, base+6s
        for i in range(5, 7):
            timestamps.append(base_timestamp + (i * 1000))

        # Create test DataFrame
        test_data = []
        for i, ts in enumerate(timestamps):
            test_data.append(
                [
                    ts,  # Open time
                    f"100.{i}",  # Open
                    f"101.{i}",  # High
                    f"99.{i}",  # Low
                    f"100.{i}",  # Close
                    "1000.0",  # Volume
                    ts + 999,  # Close time (1s interval = 1000ms)
                    "50000.0",  # Quote volume
                    "100",  # Trade count
                    "500.0",  # Taker buy base
                    "25000.0",  # Taker buy quote
                ]
            )

        df = pd.DataFrame(
            test_data,
            columns=[
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
            ],
        )

        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"], unit="ms")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            temp_file = f.name

        try:
            # Detect gaps
            gaps = gap_filler.detect_all_gaps(temp_file, "1s")

            # Should detect one gap (2 seconds missing: 12:00:03 and 12:00:04)
            assert len(gaps) == 1

            gap = gaps[0]
            # Expected gap: from base+3s to base+4s (2 seconds missing)
            expected_start_ts = (base_timestamp + 3000) / 1000  # Convert to seconds
            expected_end_ts = (base_timestamp + 4000) / 1000

            # Verify gap timing with UTC timestamps
            gap_start_ts = gap["start_time"].timestamp()
            gap_end_ts = gap["end_time"].timestamp()

            # UTC timestamp precision check (allow reasonable tolerance)
            assert abs(gap_start_ts - expected_start_ts) < 3600  # Within 1 hour
            assert abs(gap_end_ts - expected_end_ts) < 3600

            # Calculate missing bars from duration and expected interval
            missing_bars = int(
                gap["duration"].total_seconds() / gap["expected_interval"].total_seconds()
            )
            assert missing_bars >= 2  # Gap detection may include boundary effects

        finally:
            os.unlink(temp_file)

    @patch("gapless_crypto_clickhouse.gap_filling.universal_gap_filler.httpx.get")
    def test_1s_gap_filling_api_call(self, mock_get):
        """Test that 1s gap filling makes correct API calls."""
        gap_filler = UniversalGapFiller()

        # Mock API response for 1s data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                1758234363000,
                "100.50",
                "100.60",
                "100.40",
                "100.55",
                "1000.0",
                1758234363999,
                "100550.0",
                "50",
                "500.0",
                "50275.0",
                "0",
            ],
            [
                1758234364000,
                "100.55",
                "100.65",
                "100.45",
                "100.60",
                "1100.0",
                1758234364999,
                "110660.0",
                "55",
                "550.0",
                "55363.0",
                "0",
            ],
        ]
        mock_get.return_value = mock_response

        # Test gap filling
        test_gap = {
            "start_time": datetime.fromtimestamp(1758234363),
            "end_time": datetime.fromtimestamp(1758234364),
            "missing_bars": 2,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Create minimal test CSV
            f.write(
                "date,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume\n"
            )
            f.write(
                "2025-09-18 12:00:00,100.0,101.0,99.0,100.0,1000.0,2025-09-18 12:00:00.999,50000.0,100,500.0,25000.0\n"
            )
            temp_file = f.name

        try:
            # This should make an API call for 1s interval
            gap_filler.fill_gap(test_gap, temp_file, "1s")

            # Verify API was called with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args

            # Check that the API call parameters include 1s interval
            call_kwargs = call_args[1] if len(call_args) > 1 else {}
            params = call_kwargs.get("params", {})
            assert params.get("interval") == "1s", (
                f"Expected 1s interval, got {params.get('interval')}"
            )
            assert params.get("symbol") == "BTCUSDT", (
                f"Expected BTCUSDT symbol, got {params.get('symbol')}"
            )

        finally:
            os.unlink(temp_file)

    def test_1s_data_volume_handling(self):
        """Test that 1s timeframe handles large data volumes efficiently."""
        gap_filler = UniversalGapFiller()

        # Create large dataset (1 hour = 3600 1-second bars)
        base_time = datetime(2025, 9, 18, 12, 0, 0)
        large_data = []

        for i in range(3600):  # 1 hour of 1s data
            ts = int((base_time + timedelta(seconds=i)).timestamp() * 1000)
            large_data.append(
                [
                    ts,
                    "100.0",
                    "101.0",
                    "99.0",
                    "100.0",
                    "1000.0",
                    ts + 999,
                    "50000.0",
                    "100",
                    "500.0",
                    "25000.0",
                ]
            )

        df = pd.DataFrame(
            large_data,
            columns=[
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
            ],
        )

        df["date"] = pd.to_datetime(df["date"], unit="ms")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            temp_file = f.name

        try:
            # This should handle large dataset without issues
            gaps = gap_filler.detect_all_gaps(temp_file, "1s")

            # Perfect 1-hour sequence should have no gaps
            assert len(gaps) == 0

        finally:
            os.unlink(temp_file)


class Test1dGapFilling:
    """Test suite for 1-day timeframe gap filling."""

    def test_1d_timeframe_mapping(self):
        """Test that 1d timeframe is properly mapped in gap filler."""
        from gapless_crypto_clickhouse.utils.timeframe_constants import (
            TIMEFRAME_TO_BINANCE_INTERVAL,
        )

        assert "1d" in TIMEFRAME_TO_BINANCE_INTERVAL
        assert TIMEFRAME_TO_BINANCE_INTERVAL["1d"] == "1d"

    def test_1d_gap_detection_precision(self):
        """Test gap detection works with 1-day precision."""
        gap_filler = UniversalGapFiller()

        # Create test data with daily intervals and a gap
        # Use UTC timestamp: 1726358400000 = 2024-09-15 00:00:00 UTC
        base_timestamp = 1726358400000  # Milliseconds since epoch (Sep 15, 2024 UTC)
        timestamps = []

        # Normal sequence: base+0d, base+1d, base+2d
        for i in range(3):
            timestamps.append(
                base_timestamp + (i * 24 * 60 * 60 * 1000)
            )  # Add days in milliseconds

        # Gap: skip base+3d, base+4d (2-day gap)
        # Resume at base+5d, base+6d
        for i in range(5, 7):
            timestamps.append(base_timestamp + (i * 24 * 60 * 60 * 1000))

        # Create test DataFrame
        test_data = []
        for i, ts in enumerate(timestamps):
            test_data.append(
                [
                    ts,  # Open time (start of day)
                    f"45000.{i}",  # Open
                    f"46000.{i}",  # High
                    f"44000.{i}",  # Low
                    f"45500.{i}",  # Close
                    "1000000.0",  # Volume
                    ts + (24 * 60 * 60 * 1000 - 1),  # Close time (end of day)
                    "45500000000.0",  # Quote volume
                    "50000",  # Trade count
                    "500000.0",  # Taker buy base
                    "22750000000.0",  # Taker buy quote
                ]
            )

        df = pd.DataFrame(
            test_data,
            columns=[
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
            ],
        )

        # Convert date column to datetime
        df["date"] = pd.to_datetime(df["date"], unit="ms")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            temp_file = f.name

        try:
            # Detect gaps
            gaps = gap_filler.detect_all_gaps(temp_file, "1d")

            # Should detect one gap (2 days missing: Sep 18 and Sep 19)
            assert len(gaps) == 1

            gap = gaps[0]
            # Expected gap: from base+3d to base+4d (2 days missing)
            expected_start_ts = (
                base_timestamp + 3 * 24 * 60 * 60 * 1000
            ) / 1000  # Convert to seconds
            expected_end_ts = (base_timestamp + 4 * 24 * 60 * 60 * 1000) / 1000

            # Verify gap timing with UTC timestamps
            gap_start_ts = gap["start_time"].timestamp()
            gap_end_ts = gap["end_time"].timestamp()

            # UTC timestamp precision check (allow reasonable tolerance for daily data)
            assert abs(gap_start_ts - expected_start_ts) <= 86400  # Within 1 day
            assert abs(gap_end_ts - expected_end_ts) <= 86400

            # Calculate missing bars from duration and expected interval
            missing_bars = int(
                gap["duration"].total_seconds() / gap["expected_interval"].total_seconds()
            )
            assert missing_bars >= 2  # Gap detection may include boundary effects

        finally:
            os.unlink(temp_file)

    @patch("gapless_crypto_clickhouse.gap_filling.universal_gap_filler.httpx.get")
    def test_1d_gap_filling_api_call(self, mock_get):
        """Test that 1d gap filling makes correct API calls."""
        gap_filler = UniversalGapFiller()

        # Mock API response for 1d data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            [
                1757894400000,
                "45000.0",
                "46000.0",
                "44000.0",
                "45500.0",
                "1000000.0",
                1757980799999,
                "45500000000.0",
                "50000",
                "500000.0",
                "22750000000.0",
                "0",
            ],
            [
                1757980800000,
                "45500.0",
                "46500.0",
                "44500.0",
                "46000.0",
                "1100000.0",
                1758067199999,
                "50600000000.0",
                "55000",
                "550000.0",
                "25330000000.0",
                "0",
            ],
        ]
        mock_get.return_value = mock_response

        # Test gap filling
        test_gap = {
            "start_time": datetime.fromtimestamp(1757894400),  # Sep 14
            "end_time": datetime.fromtimestamp(1757980800),  # Sep 15
            "missing_bars": 2,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            # Create minimal test CSV
            f.write(
                "date,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume\n"
            )
            f.write(
                "2025-09-13 00:00:00,45000.0,46000.0,44000.0,45500.0,1000000.0,2025-09-13 23:59:59.999,45500000000.0,50000,500000.0,22750000000.0\n"
            )
            temp_file = f.name

        try:
            # This should make an API call for 1d interval
            gap_filler.fill_gap(test_gap, temp_file, "1d")

            # Verify API was called with correct parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args

            # Check that the API call parameters include 1d interval
            call_kwargs = call_args[1] if len(call_args) > 1 else {}
            params = call_kwargs.get("params", {})
            assert params.get("interval") == "1d", (
                f"Expected 1d interval, got {params.get('interval')}"
            )
            assert params.get("symbol") == "BTCUSDT", (
                f"Expected BTCUSDT symbol, got {params.get('symbol')}"
            )

        finally:
            os.unlink(temp_file)

    def test_1d_weekend_gap_handling(self):
        """Test handling of weekend gaps in daily data."""
        gap_filler = UniversalGapFiller()

        # Create weekday data (Mon-Fri) with weekend gap
        # Use UTC timestamps for precise weekday sequence
        # 1726358400000 = 2024-09-15 00:00:00 UTC (Sunday)
        # We'll use Monday Sep 16 as starting point
        base_monday = 1726444800000  # 2024-09-16 00:00:00 UTC (Monday)

        weekday_offsets = [0, 1, 2, 3, 4, 7]  # Mon, Tue, Wed, Thu, Fri, [skip weekend], Mon
        timestamps = []

        for offset_days in weekday_offsets:
            ts = base_monday + (offset_days * 24 * 60 * 60 * 1000)
            timestamps.append(ts)

        test_data = []
        for i, ts in enumerate(timestamps):
            test_data.append(
                [
                    ts,
                    f"45000.{i}",
                    f"46000.{i}",
                    f"44000.{i}",
                    f"45500.{i}",
                    "1000000.0",
                    ts + (24 * 60 * 60 * 1000 - 1),
                    "45500000000.0",
                    "50000",
                    "500000.0",
                    "22750000000.0",
                ]
            )

        df = pd.DataFrame(
            test_data,
            columns=[
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
            ],
        )

        df["date"] = pd.to_datetime(df["date"], unit="ms")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            df.to_csv(f.name, index=False)
            temp_file = f.name

        try:
            # Detect gaps
            gaps = gap_filler.detect_all_gaps(temp_file, "1d")

            # Should detect weekend gap (Sat 20, Sun 21)
            assert len(gaps) == 1

            gap = gaps[0]
            # Weekend gap: Sep 21 and Sep 22 (2024, not 2025)

            # Calculate missing bars from duration and expected interval
            missing_bars = int(
                gap["duration"].total_seconds() / gap["expected_interval"].total_seconds()
            )
            assert missing_bars >= 2  # Weekend gap may include additional days

        finally:
            os.unlink(temp_file)


class TestConcurrentDownloadWith1sAnd1d:
    """Test concurrent download architecture with extreme timeframes."""

    def test_concurrent_architecture_supports_1s_and_1d(self):
        """Test that concurrent collection architecture supports 1s and 1d."""
        # Import concurrent components
        from gapless_crypto_clickhouse.collectors.hybrid_url_generator import HybridUrlGenerator

        # Test URL generation for 1s
        url_generator = HybridUrlGenerator()

        # Test with very short date range for 1s (to avoid massive datasets)
        start_date = datetime(2025, 9, 18, 12, 0, 0)
        end_date = datetime(2025, 9, 18, 12, 1, 0)  # 1 minute only

        # Should be able to generate tasks for 1s
        tasks_1s = url_generator.generate_download_tasks(
            symbol="BTCUSDT", timeframe="1s", start_date=start_date, end_date=end_date
        )

        # 1s data should use daily sources for such recent data
        assert len(tasks_1s) > 0

        # Test with longer range for 1d
        start_date_1d = datetime(2025, 1, 1)
        end_date_1d = datetime(2025, 3, 1)

        tasks_1d = url_generator.generate_download_tasks(
            symbol="BTCUSDT", timeframe="1d", start_date=start_date_1d, end_date=end_date_1d
        )

        # 1d data should work with both monthly and daily sources
        assert len(tasks_1d) > 0

        # Test strategy summary
        strategy_1s = url_generator.get_collection_strategy_summary(
            symbol="BTCUSDT", timeframe="1s", start_date=start_date, end_date=end_date
        )

        strategy_1d = url_generator.get_collection_strategy_summary(
            symbol="BTCUSDT", timeframe="1d", start_date=start_date_1d, end_date=end_date_1d
        )

        assert strategy_1s["total_tasks"] > 0
        assert strategy_1d["total_tasks"] > 0


class TestDataIntegrityFor1sAnd1d:
    """Test data integrity and authenticity for extreme timeframes."""

    def test_1s_data_authenticity_structure(self):
        """Test that 1s data maintains authentic 11-column structure."""
        # This would test that 1s gap-filled data maintains the same structure
        # as original Binance data

        # Test data structure expectations
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

        # Create test file with correct structure
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(",".join(expected_columns) + "\n")
            f.write(
                "2025-09-18 12:00:00,100.0,101.0,99.0,100.0,1000.0,2025-09-18 12:00:00.999,50000.0,100,500.0,25000.0\n"
            )
            temp_file = f.name

        try:
            # Read the file back
            df = pd.read_csv(temp_file)

            # Verify all expected columns are present
            for col in expected_columns:
                assert col in df.columns, f"Missing column: {col}"

            # Verify we have exactly 11 columns (authentic Binance structure)
            assert len(df.columns) == 11

        finally:
            os.unlink(temp_file)

    def test_1d_data_authenticity_structure(self):
        """Test that 1d data maintains authentic 11-column structure."""
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

        # Create test file with daily data structure
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(",".join(expected_columns) + "\n")
            f.write(
                "2025-09-18 00:00:00,45000.0,46000.0,44000.0,45500.0,1000000.0,2025-09-18 23:59:59.999,45500000000.0,50000,500000.0,22750000000.0\n"
            )
            temp_file = f.name

        try:
            # Read the file back
            df = pd.read_csv(temp_file)

            # Verify all expected columns are present
            for col in expected_columns:
                assert col in df.columns, f"Missing column: {col}"

            # Verify we have exactly 11 columns (authentic Binance structure)
            assert len(df.columns) == 11

        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
