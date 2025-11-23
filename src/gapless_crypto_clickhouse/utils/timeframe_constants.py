"""Centralized timeframe constants for data collection and gap detection.

This module provides single source of truth for timeframe-to-interval mappings
used across collectors and gap fillers, eliminating code duplication and
preventing calculation bugs.

Binance Dual Notation Architecture:
    - Monthly timeframe uses DIFFERENT notation across Binance systems:
      * Public Data Repository (data.binance.vision): "1mo" in file paths
      * REST API (api.binance.com/api/v3/klines): "1M" as interval parameter
    - Other exotic timeframes (3d, 1w): Identity mapping (same notation everywhere)
    - TIMEFRAME_TO_BINANCE_INTERVAL handles this mapping automatically

SLO Targets:
    Maintainability: Single source of truth eliminates 3+ code duplications
    Correctness: All 16 timeframes map to accurate minute values
    Availability: Supports full spectrum from 1s to 1mo (13 standard + 3 exotic)
    Compatibility: Dual notation support for Public Data + REST API workflows
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
    "3d": 4320,  # 3 days = 72 hours = 4320 minutes
    "1w": 10080,  # 7 days = 168 hours = 10080 minutes
    "1mo": 43200,  # 30 days = 720 hours = 43200 minutes (approximate)
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
# NOTE: Monthly timeframe has dual notation:
#   - "1mo" for Public Data Repository paths (data.binance.vision)
#   - "1M" for REST API interval parameter (api.binance.com/api/v3/klines)
# All other timeframes use identity mapping (e.g., "3d" → "3d", "1w" → "1w")
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
    "3d": "3d",
    "1w": "1w",
    "1mo": "1M",  # Binance API uses "1M" for monthly interval
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
    "3d",
    "1w",
    "1mo",
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
