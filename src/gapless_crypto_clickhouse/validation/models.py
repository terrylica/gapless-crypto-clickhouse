"""Pydantic models for validation report persistence.

This module provides type-safe data models for validation reports with
OpenAPI 3.1.1 compatibility for AI coding agent consumption.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ValidationReport(BaseModel):
    """Structured validation report with full observability.

    This model provides type-safe representation of CSV validation results
    with automatic schema generation for OpenAPI/JSON Schema compliance.

    Examples:
        >>> from datetime import datetime, timezone
        >>> report = ValidationReport(
        ...     validation_timestamp=datetime.now(timezone.utc),
        ...     file_path="/path/to/BTCUSDT-1h.csv",
        ...     file_size_mb=15.3,
        ...     total_bars=8760,
        ...     total_errors=0,
        ...     total_warnings=2,
        ...     validation_summary="GOOD - 2 warnings",
        ...     validation_duration_ms=123.45,
        ...     structure_validation={},
        ...     datetime_validation={},
        ...     ohlcv_validation={},
        ...     coverage_validation={},
        ...     anomaly_validation={}
        ... )
        >>> report.model_dump_json()
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "validation_timestamp": "2025-10-18T12:00:00Z",
                "file_path": "/data/BTCUSDT-1h.csv",
                "validator_version": "3.3.0",
                "total_errors": 0,
                "total_warnings": 2,
                "validation_summary": "GOOD - 2 warnings",
            }
        }
    )

    # Metadata
    validation_timestamp: datetime = Field(
        description="ISO 8601 validation timestamp with timezone"
    )
    file_path: str = Field(description="Absolute path to validated CSV file")
    file_size_mb: float = Field(description="File size in megabytes", ge=0)
    validator_version: str = Field(default="3.3.0", description="Validator version (SemVer)")

    # Extracted context from file path
    symbol: Optional[str] = Field(
        default=None,
        description="Trading pair symbol extracted from filename (e.g., BTCUSDT)",
    )
    timeframe: Optional[str] = Field(
        default=None, description="Timeframe extracted from filename (e.g., 1h)"
    )

    # Core Results
    total_bars: int = Field(description="Total number of data bars validated", ge=0)
    total_errors: int = Field(description="Total validation errors detected", ge=0)
    total_warnings: int = Field(description="Total validation warnings detected", ge=0)
    validation_summary: str = Field(description="Summary status: PERFECT | GOOD | FAILED")

    # Performance Metrics
    validation_duration_ms: float = Field(description="Validation duration in milliseconds", ge=0)

    # Layer Results (detailed validation results as JSON)
    structure_validation: Dict[str, Any] = Field(
        description="Layer 1: Structure validation results"
    )
    datetime_validation: Dict[str, Any] = Field(description="Layer 2: DateTime validation results")
    ohlcv_validation: Dict[str, Any] = Field(
        description="Layer 3: OHLCV quality validation results"
    )
    coverage_validation: Dict[str, Any] = Field(description="Layer 4: Coverage validation results")
    anomaly_validation: Dict[str, Any] = Field(description="Layer 5: Anomaly detection results")

    # Flattened metrics for efficient querying (extracted from layer results)
    date_range_start: Optional[datetime] = Field(
        default=None, description="Start of data date range"
    )
    date_range_end: Optional[datetime] = Field(default=None, description="End of data date range")
    duration_days: Optional[float] = Field(default=None, description="Duration of data in days")
    gaps_found: Optional[int] = Field(default=None, description="Number of timestamp gaps detected")
    chronological_order: Optional[bool] = Field(
        default=None, description="Whether timestamps are chronologically ordered"
    )

    price_min: Optional[float] = Field(default=None, description="Minimum price value")
    price_max: Optional[float] = Field(default=None, description="Maximum price value")
    volume_min: Optional[float] = Field(default=None, description="Minimum volume")
    volume_max: Optional[float] = Field(default=None, description="Maximum volume")
    volume_mean: Optional[float] = Field(default=None, description="Mean volume")
    ohlc_errors: Optional[int] = Field(default=None, description="Number of OHLC logic errors")
    negative_zero_values: Optional[int] = Field(
        default=None, description="Count of negative or zero price values"
    )

    expected_bars: Optional[int] = Field(default=None, description="Expected number of bars")
    actual_bars: Optional[int] = Field(default=None, description="Actual number of bars")
    coverage_percentage: Optional[float] = Field(
        default=None, description="Coverage percentage (actual/expected * 100)"
    )

    price_outliers: Optional[int] = Field(
        default=None, description="Number of price outliers detected"
    )
    volume_outliers: Optional[int] = Field(
        default=None, description="Number of volume outliers detected"
    )
    suspicious_patterns: Optional[int] = Field(
        default=None, description="Number of suspicious patterns detected"
    )

    @classmethod
    def from_legacy_dict(
        cls,
        legacy: Dict[str, Any],
        duration_ms: float = 0,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> "ValidationReport":
        """Convert legacy dict-based validation results to typed report.

        Args:
            legacy: Legacy validation results dictionary from CSVValidator
            duration_ms: Validation duration in milliseconds
            symbol: Optional trading pair symbol (extracted from filename)
            timeframe: Optional timeframe (extracted from filename)

        Returns:
            Typed ValidationReport instance

        Examples:
            >>> legacy_results = {
            ...     "validation_timestamp": "2025-10-18T12:00:00Z",
            ...     "file_path": "/data/BTCUSDT-1h.csv",
            ...     "total_errors": 0,
            ...     "total_warnings": 2,
            ...     # ... more fields
            ... }
            >>> report = ValidationReport.from_legacy_dict(
            ...     legacy_results,
            ...     duration_ms=123.45,
            ...     symbol="BTCUSDT",
            ...     timeframe="1h"
            ... )
        """
        # Parse datetime if string
        validation_ts = legacy["validation_timestamp"]
        if isinstance(validation_ts, str):
            validation_ts = datetime.fromisoformat(validation_ts.rstrip("Z"))

        # Extract flattened metrics from layer results
        datetime_val = legacy.get("datetime_validation", {})
        ohlcv_val = legacy.get("ohlcv_validation", {})
        coverage_val = legacy.get("coverage_validation", {})
        anomaly_val = legacy.get("anomaly_validation", {})

        # Parse date range timestamps
        date_range = datetime_val.get("date_range", {})
        date_range_start = None
        date_range_end = None
        if date_range:
            if "start" in date_range:
                date_range_start = datetime.fromisoformat(date_range["start"].rstrip("Z"))
            if "end" in date_range:
                date_range_end = datetime.fromisoformat(date_range["end"].rstrip("Z"))

        # Extract price range
        price_range = ohlcv_val.get("price_range", {})
        volume_stats = ohlcv_val.get("volume_stats", {})

        return cls(
            validation_timestamp=validation_ts,
            file_path=legacy["file_path"],
            file_size_mb=legacy.get("file_size_mb", 0.0),
            symbol=symbol,
            timeframe=timeframe,
            total_bars=legacy.get("total_bars", 0),
            total_errors=legacy["total_errors"],
            total_warnings=legacy["total_warnings"],
            validation_summary=legacy["validation_summary"],
            validation_duration_ms=duration_ms,
            structure_validation=legacy.get("structure_validation", {}),
            datetime_validation=datetime_val,
            ohlcv_validation=ohlcv_val,
            coverage_validation=coverage_val,
            anomaly_validation=anomaly_val,
            # Flattened metrics for SQL queries
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            duration_days=datetime_val.get("duration_days"),
            gaps_found=datetime_val.get("gaps_found"),
            chronological_order=datetime_val.get("chronological_order"),
            price_min=price_range.get("min"),
            price_max=price_range.get("max"),
            volume_min=volume_stats.get("min"),
            volume_max=volume_stats.get("max"),
            volume_mean=volume_stats.get("mean"),
            ohlc_errors=ohlcv_val.get("ohlc_errors"),
            negative_zero_values=ohlcv_val.get("negative_zero_values"),
            expected_bars=coverage_val.get("expected_bars"),
            actual_bars=coverage_val.get("actual_bars"),
            coverage_percentage=coverage_val.get("coverage_percentage"),
            price_outliers=anomaly_val.get("price_outliers"),
            volume_outliers=anomaly_val.get("volume_outliers"),
            suspicious_patterns=anomaly_val.get("suspicious_patterns"),
        )
