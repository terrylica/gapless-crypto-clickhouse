"""Regression tests for timeframe interval calculation bug.

These tests prevent regression of the critical bug where hour-based timeframes
(2h, 4h, 6h, 8h, 12h) were incorrectly parsed as minute intervals.

Bug Example (PRE-FIX):
    "2h"[:-1] = "2" → int("2") = 2 → 2 minutes (WRONG!)

Expected (POST-FIX):
    TIMEFRAME_TO_MINUTES["2h"] = 120 minutes (CORRECT!)

SLO Targets:
    Correctness: 100% accurate interval mappings for all 13 timeframes
    Maintainability: Centralized constants prevent future parsing bugs
"""

from datetime import timedelta

import pandas as pd
import pytest

from gapless_crypto_clickhouse.utils.timeframe_constants import (
    TIMEFRAME_TO_BINANCE_INTERVAL,
    TIMEFRAME_TO_MINUTES,
    TIMEFRAME_TO_PYTHON_TIMEDELTA,
    TIMEFRAME_TO_TIMEDELTA,
)


class TestTimeframeConstants:
    """Test centralized timeframe constant mappings."""

    def test_timeframe_to_minutes_all_13_timeframes(self):
        """Verify all 13 supported timeframes have correct minute mappings."""
        expected_mappings = {
            "1s": 1 / 60,  # 1 second
            "1m": 1,
            "3m": 3,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "2h": 120,  # Critical: Must be 120, not 2
            "4h": 240,  # Critical: Must be 240, not 4
            "6h": 360,  # Critical: Must be 360, not 6
            "8h": 480,  # Critical: Must be 480, not 8
            "12h": 720,  # Critical: Must be 720, not 12
            "1d": 1440,
        }

        assert TIMEFRAME_TO_MINUTES == expected_mappings, (
            f"Timeframe minute mappings incorrect. "
            f"Difference: {set(TIMEFRAME_TO_MINUTES.items()) ^ set(expected_mappings.items())}"
        )

    @pytest.mark.parametrize(
        "timeframe,expected_minutes",
        [
            ("2h", 120),
            ("4h", 240),
            ("6h", 360),
            ("8h", 480),
            ("12h", 720),
        ],
    )
    def test_hour_based_timeframes_critical_bug_regression(self, timeframe, expected_minutes):
        """Regression test for hour-based timeframe parsing bug.

        This test specifically guards against the bug where:
            int("2h"[:-1]) = 2 minutes (WRONG)
        Instead of:
            TIMEFRAME_TO_MINUTES["2h"] = 120 minutes (CORRECT)
        """
        actual_minutes = TIMEFRAME_TO_MINUTES[timeframe]

        assert actual_minutes == expected_minutes, (
            f"CRITICAL BUG REGRESSION: {timeframe} maps to {actual_minutes} minutes, "
            f"expected {expected_minutes} minutes. "
            f"Hour-based timeframes must NOT be parsed as '{timeframe[:-1]}' minutes!"
        )

    def test_timedelta_mappings_consistency(self):
        """Verify pandas Timedelta mappings match minute values."""
        for timeframe, minutes in TIMEFRAME_TO_MINUTES.items():
            expected_timedelta = pd.Timedelta(minutes=minutes)
            actual_timedelta = TIMEFRAME_TO_TIMEDELTA[timeframe]

            assert actual_timedelta == expected_timedelta, (
                f"Timedelta mapping inconsistent for {timeframe}: "
                f"expected {expected_timedelta}, got {actual_timedelta}"
            )

    def test_python_timedelta_mappings_consistency(self):
        """Verify Python timedelta mappings match minute values."""
        for timeframe, minutes in TIMEFRAME_TO_MINUTES.items():
            expected_timedelta = timedelta(minutes=minutes)
            actual_timedelta = TIMEFRAME_TO_PYTHON_TIMEDELTA[timeframe]

            assert actual_timedelta == expected_timedelta, (
                f"Python timedelta mapping inconsistent for {timeframe}: "
                f"expected {expected_timedelta}, got {actual_timedelta}"
            )

    def test_binance_interval_mapping_completeness(self):
        """Verify all timeframes have Binance API interval mappings."""
        assert set(TIMEFRAME_TO_BINANCE_INTERVAL.keys()) == set(TIMEFRAME_TO_MINUTES.keys()), (
            "Binance interval mapping missing timeframes"
        )

        # All mappings should be identity (timeframe string = Binance interval)
        for timeframe in TIMEFRAME_TO_MINUTES.keys():
            assert TIMEFRAME_TO_BINANCE_INTERVAL[timeframe] == timeframe, (
                f"Binance interval for {timeframe} should be '{timeframe}', "
                f"got '{TIMEFRAME_TO_BINANCE_INTERVAL[timeframe]}'"
            )

    def test_gap_detection_scenario_2h_timeframe(self):
        """Simulate gap detection with 2h timeframe to verify correct interval."""
        timeframe = "2h"
        expected_interval_minutes = 120

        # Simulate timestamps with a 4-hour gap (should detect 2 missing candles)
        timestamps = pd.to_datetime(
            ["2024-01-01 00:00:00", "2024-01-01 02:00:00", "2024-01-01 06:00:00"]
        )

        expected_gap_duration = timedelta(hours=4)
        actual_gap = timestamps[2] - timestamps[1]

        assert actual_gap == expected_gap_duration
        assert actual_gap > TIMEFRAME_TO_PYTHON_TIMEDELTA[timeframe], (
            f"4-hour gap should be detected as missing candles for {timeframe} timeframe"
        )

        # Verify gap is exactly 2 missing candles
        missing_candles = actual_gap.total_seconds() / 60 / expected_interval_minutes
        assert missing_candles == 2, (
            f"4-hour gap in {timeframe} data should represent 2 missing candles, "
            f"got {missing_candles}"
        )

    def test_all_mappings_have_same_timeframes(self):
        """Ensure all mapping dictionaries cover the same 13 timeframes."""
        expected_timeframes = {
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
        }

        assert set(TIMEFRAME_TO_MINUTES.keys()) == expected_timeframes
        assert set(TIMEFRAME_TO_TIMEDELTA.keys()) == expected_timeframes
        assert set(TIMEFRAME_TO_PYTHON_TIMEDELTA.keys()) == expected_timeframes
        assert set(TIMEFRAME_TO_BINANCE_INTERVAL.keys()) == expected_timeframes


class TestGapFillerUsesConstants:
    """Verify UniversalGapFiller uses centralized constants (not duplicated code)."""

    def test_gap_filler_imports_timeframe_constants(self):
        """Verify gap filler imports centralized timeframe constants."""
        # Verify the module imports the constants
        import gapless_crypto_clickhouse.gap_filling.universal_gap_filler as gap_filler_module

        assert hasattr(gap_filler_module, "TIMEFRAME_TO_TIMEDELTA"), (
            "UniversalGapFiller must import TIMEFRAME_TO_TIMEDELTA"
        )
        assert hasattr(gap_filler_module, "TIMEFRAME_TO_PYTHON_TIMEDELTA"), (
            "UniversalGapFiller must import TIMEFRAME_TO_PYTHON_TIMEDELTA"
        )
        assert hasattr(gap_filler_module, "TIMEFRAME_TO_BINANCE_INTERVAL"), (
            "UniversalGapFiller must import TIMEFRAME_TO_BINANCE_INTERVAL"
        )

    def test_binance_collector_imports_timeframe_constants(self):
        """Verify BinancePublicDataCollector uses centralized constants."""
        import gapless_crypto_clickhouse.collectors.binance_public_data_collector as collector_module

        assert hasattr(collector_module, "TIMEFRAME_TO_MINUTES"), (
            "BinancePublicDataCollector must import TIMEFRAME_TO_MINUTES"
        )
