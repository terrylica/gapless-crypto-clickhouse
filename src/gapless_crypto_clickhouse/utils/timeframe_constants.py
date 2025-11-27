"""DEPRECATED: Timeframe constants have moved to gapless_crypto_clickhouse.constants.

This module is retained for backwards compatibility. All imports now forward
to the new location: gapless_crypto_clickhouse.constants.timeframes

Migration (ADR-0048):
    # Before
    from gapless_crypto_clickhouse.utils.timeframe_constants import TIMEFRAME_TO_MINUTES

    # After
    from gapless_crypto_clickhouse.constants import TIMEFRAME_TO_MINUTES
"""

import warnings

# Re-export all symbols from new location for backwards compatibility
from ..constants.timeframes import (
    EXOTIC_TIMEFRAMES,
    STANDARD_TIMEFRAMES,
    TIMEFRAME_TO_BINANCE_INTERVAL,
    TIMEFRAME_TO_MILLISECONDS,
    TIMEFRAME_TO_MINUTES,
    TIMEFRAME_TO_PYTHON_TIMEDELTA,
    TIMEFRAME_TO_SECONDS,
    TIMEFRAME_TO_TIMEDELTA,
    VALID_TIMEFRAMES,
    Timeframe,
)

# Emit deprecation warning on import
warnings.warn(
    "gapless_crypto_clickhouse.utils.timeframe_constants is deprecated. "
    "Use gapless_crypto_clickhouse.constants instead (ADR-0048).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "Timeframe",
    "TIMEFRAME_TO_MINUTES",
    "TIMEFRAME_TO_BINANCE_INTERVAL",
    "TIMEFRAME_TO_MILLISECONDS",
    "TIMEFRAME_TO_SECONDS",
    "TIMEFRAME_TO_TIMEDELTA",
    "TIMEFRAME_TO_PYTHON_TIMEDELTA",
    "VALID_TIMEFRAMES",
    "STANDARD_TIMEFRAMES",
    "EXOTIC_TIMEFRAMES",
]
