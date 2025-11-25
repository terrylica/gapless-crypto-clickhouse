"""Validation module for data integrity and quality assurance.

This module provides comprehensive validation for cryptocurrency market data,
including CSV validation and production monitoring.

CSV Validation:
    CSVValidator: Main validator class for CSV file validation
    ValidationReport: Pydantic model for type-safe validation reports
    ValidationStorage: DuckDB-based persistent storage for validation reports

SLO Targets:
    Correctness: 100% - all validation rules enforce data integrity
    Observability: Complete reporting of all errors, warnings, and metrics
    Maintainability: Single source of truth for validation logic

Note:
    E2E testing primitives (e2e_core.py) removed in ADR-0039.
    Production validation now uses scripts/validate_binance_real_data.py.
"""

from gapless_crypto_clickhouse.validation.csv_validator import CSVValidator
from gapless_crypto_clickhouse.validation.models import ValidationReport
from gapless_crypto_clickhouse.validation.storage import (
    ValidationStorage,
    extract_symbol_timeframe_from_path,
    get_validation_db_path,
)

__all__ = [
    # CSV Validation
    "CSVValidator",
    "ValidationReport",
    "ValidationStorage",
    "get_validation_db_path",
    "extract_symbol_timeframe_from_path",
]
