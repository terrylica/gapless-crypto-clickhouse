"""CSV validation module for data integrity and quality assurance.

This module provides comprehensive validation for cryptocurrency market data CSVs,
including structure validation, datetime sequence checking, OHLCV quality analysis,
coverage validation, and statistical anomaly detection.

Classes:
    CSVValidator: Main validator class for CSV file validation
    ValidationReport: Pydantic model for type-safe validation reports
    ValidationStorage: DuckDB-based persistent storage for validation reports

Functions:
    get_validation_db_path: Get XDG-compliant path to validation database
    extract_symbol_timeframe_from_path: Extract trading pair symbol and timeframe from CSV file paths

SLO Targets:
    Correctness: 100% - all validation rules enforce data integrity
    Observability: Complete reporting of all errors, warnings, and metrics
    Maintainability: Single source of truth for validation logic
"""

from gapless_crypto_clickhouse.validation.csv_validator import CSVValidator
from gapless_crypto_clickhouse.validation.models import ValidationReport
from gapless_crypto_clickhouse.validation.storage import (
    ValidationStorage,
    extract_symbol_timeframe_from_path,
    get_validation_db_path,
)

__all__ = [
    "CSVValidator",
    "ValidationReport",
    "ValidationStorage",
    "get_validation_db_path",
    "extract_symbol_timeframe_from_path",
]
