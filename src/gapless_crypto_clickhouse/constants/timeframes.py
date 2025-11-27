"""Centralized timeframe constants (ADR-0046, ADR-0048).

Single source of truth for timeframe-to-interval mappings used across
collectors, gap fillers, validators, and query builders.

Binance Dual Notation Architecture:
    - Monthly timeframe uses DIFFERENT notation across Binance systems:
      * Public Data Repository (data.binance.vision): "1mo" in file paths
      * REST API (api.binance.com/api/v3/klines): "1M" as interval parameter
    - Other exotic timeframes (3d, 1w): Identity mapping (same notation everywhere)
    - TIMEFRAME_TO_BINANCE_INTERVAL handles this mapping automatically

Derived Maps (ADR-0048):
    - TIMEFRAME_TO_MILLISECONDS: For REST API interval calculations
    - TIMEFRAME_TO_SECONDS: For ClickHouse gap detection queries
    - VALID_TIMEFRAMES: Frozenset for O(1) validation

Usage:
    from gapless_crypto_clickhouse.constants import (
        Timeframe,
        TIMEFRAME_TO_MINUTES,
        TIMEFRAME_TO_MILLISECONDS,
        VALID_TIMEFRAMES,
    )
"""

from datetime import timedelta
from typing import Dict, Final, FrozenSet, Literal

import pandas as pd

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

Timeframe = Literal[
    "1s", "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1mo"
]
"""Type alias for valid timeframes (16 total: 13 standard + 3 exotic)."""

# =============================================================================
# PRIMARY MAPPINGS
# =============================================================================

TIMEFRAME_TO_MINUTES: Final[Dict[str, float]] = {
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
    "1d": 1440,   # 24 hours = 1440 minutes
    "3d": 4320,   # 3 days = 72 hours = 4320 minutes
    "1w": 10080,  # 7 days = 168 hours = 10080 minutes
    "1mo": 43200, # 30 days = 720 hours = 43200 minutes (approximate)
}
"""Timeframe to minutes mapping (single source of truth)."""

TIMEFRAME_TO_BINANCE_INTERVAL: Final[Dict[str, str]] = {
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
"""Binance API interval mapping (handles 1mo → 1M conversion)."""

# =============================================================================
# DERIVED MAPPINGS (computed from TIMEFRAME_TO_MINUTES)
# =============================================================================

TIMEFRAME_TO_MILLISECONDS: Final[Dict[str, int]] = {
    timeframe: int(minutes * 60 * 1000)
    for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}
"""Timeframe to milliseconds for REST API calculations."""

TIMEFRAME_TO_SECONDS: Final[Dict[str, int]] = {
    timeframe: int(minutes * 60)
    for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}
"""Timeframe to seconds for ClickHouse gap detection queries."""

TIMEFRAME_TO_TIMEDELTA: Final[Dict[str, pd.Timedelta]] = {
    timeframe: pd.Timedelta(minutes=minutes)
    for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}
"""Pandas Timedelta mapping for DataFrame operations."""

TIMEFRAME_TO_PYTHON_TIMEDELTA: Final[Dict[str, timedelta]] = {
    timeframe: timedelta(minutes=minutes)
    for timeframe, minutes in TIMEFRAME_TO_MINUTES.items()
}
"""Python timedelta mapping for non-pandas contexts."""

# =============================================================================
# VALIDATION SETS
# =============================================================================

VALID_TIMEFRAMES: Final[FrozenSet[str]] = frozenset(TIMEFRAME_TO_MINUTES.keys())
"""Frozenset of valid timeframes for O(1) membership testing."""

STANDARD_TIMEFRAMES: Final[FrozenSet[str]] = frozenset({
    "1s", "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h", "1d"
})
"""Standard timeframes (1s through 1d) - available for all symbols."""

EXOTIC_TIMEFRAMES: Final[FrozenSet[str]] = frozenset({"3d", "1w", "1mo"})
"""Exotic timeframes (3d, 1w, 1mo) - may have limited symbol availability."""

# =============================================================================
# SELF-VALIDATING ASSERTIONS
# =============================================================================

_EXPECTED_TIMEFRAMES = {
    "1s", "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1mo",
}

# Verify all mappings cover all timeframes
assert set(TIMEFRAME_TO_MINUTES.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_MINUTES missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_MINUTES.keys())}"
)
assert set(TIMEFRAME_TO_BINANCE_INTERVAL.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_BINANCE_INTERVAL missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_BINANCE_INTERVAL.keys())}"
)
assert set(TIMEFRAME_TO_MILLISECONDS.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_MILLISECONDS missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_MILLISECONDS.keys())}"
)
assert set(TIMEFRAME_TO_SECONDS.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_SECONDS missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_SECONDS.keys())}"
)
assert set(TIMEFRAME_TO_TIMEDELTA.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_TIMEDELTA missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_TIMEDELTA.keys())}"
)
assert set(TIMEFRAME_TO_PYTHON_TIMEDELTA.keys()) == _EXPECTED_TIMEFRAMES, (
    f"TIMEFRAME_TO_PYTHON_TIMEDELTA missing timeframes: "
    f"{_EXPECTED_TIMEFRAMES - set(TIMEFRAME_TO_PYTHON_TIMEDELTA.keys())}"
)

# Verify set relationships
assert STANDARD_TIMEFRAMES | EXOTIC_TIMEFRAMES == VALID_TIMEFRAMES, (
    "STANDARD_TIMEFRAMES + EXOTIC_TIMEFRAMES must equal VALID_TIMEFRAMES"
)
assert STANDARD_TIMEFRAMES & EXOTIC_TIMEFRAMES == set(), (
    "STANDARD_TIMEFRAMES and EXOTIC_TIMEFRAMES must be disjoint"
)

# Verify derived map values are correct
assert TIMEFRAME_TO_MILLISECONDS["1m"] == 60000, "1m should be 60000ms"
assert TIMEFRAME_TO_MILLISECONDS["1h"] == 3600000, "1h should be 3600000ms"
assert TIMEFRAME_TO_SECONDS["1m"] == 60, "1m should be 60s"
assert TIMEFRAME_TO_SECONDS["1d"] == 86400, "1d should be 86400s"

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Type definitions
    "Timeframe",
    # Primary mappings
    "TIMEFRAME_TO_MINUTES",
    "TIMEFRAME_TO_BINANCE_INTERVAL",
    # Derived mappings
    "TIMEFRAME_TO_MILLISECONDS",
    "TIMEFRAME_TO_SECONDS",
    "TIMEFRAME_TO_TIMEDELTA",
    "TIMEFRAME_TO_PYTHON_TIMEDELTA",
    # Validation sets
    "VALID_TIMEFRAMES",
    "STANDARD_TIMEFRAMES",
    "EXOTIC_TIMEFRAMES",
]
