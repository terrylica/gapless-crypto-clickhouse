"""Centralized timeframe constants for data collection and gap detection.

This module provides single source of truth for timeframe-to-interval mappings
used across collectors and gap fillers, eliminating code duplication and
preventing calculation bugs.

SLO Targets:
    Maintainability: Single source of truth eliminates 3+ code duplications
    Correctness: All 13 timeframes map to accurate minute values
    Availability: Supports full spectrum from 1s to 1d timeframes
"""

from datetime import timedelta
from typing import Dict

import pandas as pd

# Timeframe to minutes mapping (single source of truth)
TIMEFRAME_TO_MINUTES: Dict[str, float] = {
    "1s": 1 / 60,  # 1 second = 1/60 minute
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "6h": 360,
    "8h": 480,
    "12h": 720,
    "1d": 1440,  # 24 hours = 1440 minutes
}

# Pandas Timedelta mapping (derived from minutes)
TIMEFRAME_TO_TIMEDELTA: Dict[str, pd.Timedelta] = {
    timeframe: pd.Timedelta(minutes=minutes) for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}

# Python timedelta mapping (for non-pandas contexts)
TIMEFRAME_TO_PYTHON_TIMEDELTA: Dict[str, timedelta] = {
    timeframe: timedelta(minutes=minutes) for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}

# Binance API interval mapping (for API parameter compatibility)
TIMEFRAME_TO_BINANCE_INTERVAL: Dict[str, str] = {
    "1s": "1s",
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
}

# Validation: All timeframes must be present in all mappings
_EXPECTED_TIMEFRAMES = {
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

assert set(TIMEFRAME_TO_MINUTES.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_MINUTES missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_MINUTES.keys())}"
)
assert set(TIMEFRAME_TO_TIMEDELTA.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_TIMEDELTA missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_TIMEDELTA.keys())}"
)
assert set(TIMEFRAME_TO_BINANCE_INTERVAL.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_BINANCE_INTERVAL missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_BINANCE_INTERVAL.keys())}"
)
