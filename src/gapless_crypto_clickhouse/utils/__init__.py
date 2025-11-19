"""Utility modules for gapless-crypto-data."""

from .error_handling import (
    DataCollectionError,
    FileOperationError,
    GapFillingError,
    GaplessCryptoError,
    ValidationError,
    format_user_error,
    format_user_warning,
    get_standard_logger,
    handle_operation_error,
    safe_operation,
    validate_file_path,
)

__all__ = [
    "GaplessCryptoError",
    "DataCollectionError",
    "GapFillingError",
    "FileOperationError",
    "ValidationError",
    "get_standard_logger",
    "handle_operation_error",
    "safe_operation",
    "validate_file_path",
    "format_user_error",
    "format_user_warning",
]
