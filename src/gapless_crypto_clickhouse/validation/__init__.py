"""Validation module for data integrity and quality assurance.

This module provides comprehensive validation for cryptocurrency market data,
including CSV validation, E2E testing primitives, and production monitoring.

CSV Validation:
    CSVValidator: Main validator class for CSV file validation
    ValidationReport: Pydantic model for type-safe validation reports
    ValidationStorage: DuckDB-based persistent storage for validation reports

E2E Testing Primitives:
    create_clickhouse_client: Create ClickHouse client with standard configuration
    validate_table_exists: Verify table exists in ClickHouse
    insert_test_data: Insert test data with error handling
    query_with_final: Query data with FINAL deduplication
    cleanup_test_data: Remove test data from table
    log_with_timestamp: Log messages with UTC timestamp

SLO Targets:
    Correctness: 100% - all validation rules enforce data integrity
    Observability: Complete reporting of all errors, warnings, and metrics
    Maintainability: Single source of truth for validation logic
"""

from gapless_crypto_clickhouse.validation.csv_validator import CSVValidator
from gapless_crypto_clickhouse.validation.e2e_core import (
    cleanup_test_data,
    create_clickhouse_client,
    insert_test_data,
    log_with_timestamp,
    query_with_final,
    validate_table_exists,
)
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
    # E2E Testing Primitives
    "create_clickhouse_client",
    "validate_table_exists",
    "insert_test_data",
    "query_with_final",
    "cleanup_test_data",
    "log_with_timestamp",
]
