"""Validation threshold constants for data quality checks (ADR-0046).

Single source of truth for statistical thresholds, coverage limits,
and anomaly detection parameters used by CSV validators.

Usage:
    from gapless_crypto_clickhouse.validation.constants import (
        IQR_MULTIPLIER,
        COVERAGE_LOW_THRESHOLD,
        MAX_GAPS_BEFORE_ERROR,
    )
"""

from typing import Final

# =============================================================================
# COVERAGE THRESHOLDS
# =============================================================================

COVERAGE_LOW_THRESHOLD: Final[float] = 95.0
"""Warn if data coverage is below 95% (missing data suspected)."""

COVERAGE_HIGH_THRESHOLD: Final[float] = 105.0
"""Warn if data coverage exceeds 105% (duplicate data suspected)."""

# =============================================================================
# GAP DETECTION
# =============================================================================

MAX_GAPS_BEFORE_ERROR: Final[int] = 10
"""Maximum acceptable gaps before validation reports an error."""

# =============================================================================
# IQR OUTLIER DETECTION
# =============================================================================

IQR_LOWER_QUANTILE: Final[float] = 0.25
"""Lower quantile (Q1) for IQR calculation."""

IQR_UPPER_QUANTILE: Final[float] = 0.75
"""Upper quantile (Q3) for IQR calculation."""

IQR_MULTIPLIER: Final[float] = 1.5
"""IQR multiplier for outlier bounds (Q1 - 1.5*IQR, Q3 + 1.5*IQR)."""

# =============================================================================
# ANOMALY THRESHOLDS
# =============================================================================

REPEATED_VALUE_THRESHOLD: Final[float] = 0.10
"""Maximum acceptable repeated value rate (10% of rows)."""

PRICE_OUTLIER_THRESHOLD: Final[float] = 0.05
"""Maximum acceptable price outlier rate (5% of rows)."""

VOLUME_OUTLIER_THRESHOLD: Final[float] = 0.02
"""Maximum acceptable volume outlier rate (2% of rows)."""

# =============================================================================
# SELF-VALIDATING ASSERTIONS
# =============================================================================

# Verify coverage thresholds make sense
assert 0 < COVERAGE_LOW_THRESHOLD < 100, f"COVERAGE_LOW_THRESHOLD invalid: {COVERAGE_LOW_THRESHOLD}"
assert COVERAGE_HIGH_THRESHOLD > 100, f"COVERAGE_HIGH_THRESHOLD must be > 100: {COVERAGE_HIGH_THRESHOLD}"
assert COVERAGE_LOW_THRESHOLD < COVERAGE_HIGH_THRESHOLD, "Low threshold must be < high threshold"

# Verify gap threshold is positive
assert MAX_GAPS_BEFORE_ERROR > 0, f"MAX_GAPS_BEFORE_ERROR must be positive: {MAX_GAPS_BEFORE_ERROR}"

# Verify IQR parameters
assert 0 < IQR_LOWER_QUANTILE < 1, f"IQR_LOWER_QUANTILE must be in (0, 1): {IQR_LOWER_QUANTILE}"
assert 0 < IQR_UPPER_QUANTILE < 1, f"IQR_UPPER_QUANTILE must be in (0, 1): {IQR_UPPER_QUANTILE}"
assert IQR_LOWER_QUANTILE < IQR_UPPER_QUANTILE, "Lower quantile must be < upper quantile"
assert IQR_MULTIPLIER > 0, f"IQR_MULTIPLIER must be positive: {IQR_MULTIPLIER}"

# Verify anomaly thresholds are valid percentages
assert 0 < REPEATED_VALUE_THRESHOLD <= 1, f"REPEATED_VALUE_THRESHOLD invalid: {REPEATED_VALUE_THRESHOLD}"
assert 0 < PRICE_OUTLIER_THRESHOLD <= 1, f"PRICE_OUTLIER_THRESHOLD invalid: {PRICE_OUTLIER_THRESHOLD}"
assert 0 < VOLUME_OUTLIER_THRESHOLD <= 1, f"VOLUME_OUTLIER_THRESHOLD invalid: {VOLUME_OUTLIER_THRESHOLD}"

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Coverage thresholds
    "COVERAGE_LOW_THRESHOLD",
    "COVERAGE_HIGH_THRESHOLD",
    # Gap detection
    "MAX_GAPS_BEFORE_ERROR",
    # IQR outlier detection
    "IQR_LOWER_QUANTILE",
    "IQR_UPPER_QUANTILE",
    "IQR_MULTIPLIER",
    # Anomaly thresholds
    "REPEATED_VALUE_THRESHOLD",
    "PRICE_OUTLIER_THRESHOLD",
    "VOLUME_OUTLIER_THRESHOLD",
]
