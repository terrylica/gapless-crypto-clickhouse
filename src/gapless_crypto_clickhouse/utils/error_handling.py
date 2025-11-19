"""
Standardized error handling framework for gapless-crypto-data.

Provides consistent exception handling, logging, and error reporting across all modules.
Eliminates duplicate error handling patterns and ensures consistent debugging experience.
"""

import logging
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union


class GaplessCryptoError(Exception):
    """Base exception for all gapless-crypto-data errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class DataCollectionError(GaplessCryptoError):
    """Errors during data collection from Binance."""

    pass


class GapFillingError(GaplessCryptoError):
    """Errors during gap detection or filling operations."""

    pass


class FileOperationError(GaplessCryptoError):
    """Errors during file I/O operations."""

    pass


class ValidationError(GaplessCryptoError):
    """Errors during data validation."""

    pass


def get_standard_logger(module_name: str) -> logging.Logger:
    """Get standardized logger for consistent formatting across modules."""
    logger = logging.getLogger(f"gapless_crypto_clickhouse.{module_name}")

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


def handle_operation_error(
    operation_name: str,
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
    reraise: bool = False,
    default_return: Any = None,
) -> Any:
    """
    Standardized error handling for operations.

    Args:
        operation_name: Human-readable operation description
        exception: The caught exception
        context: Additional context for debugging
        logger: Logger instance (uses default if None)
        reraise: Whether to re-raise the exception after logging
        default_return: Value to return if not re-raising

    Returns:
        default_return value, or re-raises if reraise=True
    """
    if logger is None:
        logger = get_standard_logger("error_handler")

    # Format context information
    context_str = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_str = f" (Context: {', '.join(context_items)})"

    # Log the error with standard format
    error_msg = f"❌ {operation_name} failed: {str(exception)}{context_str}"
    logger.error(error_msg)

    # Optionally log full traceback for debugging
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Full traceback: {traceback.format_exc()}")

    if reraise:
        raise

    return default_return


def safe_operation(
    operation_name: str,
    func: Callable,
    context: Optional[Dict[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
    exception_types: tuple = (Exception,),
    default_return: Any = None,
    reraise: bool = False,
) -> Any:
    """
    Execute operation with standardized error handling.

    Args:
        operation_name: Human-readable operation description
        func: Function to execute
        context: Additional context for debugging
        logger: Logger instance (uses default if None)
        exception_types: Tuple of exception types to catch
        default_return: Value to return on error
        reraise: Whether to re-raise caught exceptions

    Returns:
        Function result or default_return on error
    """
    try:
        return func()
    except exception_types as e:
        return handle_operation_error(
            operation_name=operation_name,
            exception=e,
            context=context,
            logger=logger,
            reraise=reraise,
            default_return=default_return,
        )


def validate_file_path(file_path: Union[str, Path], operation: str = "file operation") -> Path:
    """
    Validate file path with standardized error handling.

    Args:
        file_path: Path to validate
        operation: Operation description for error messages

    Returns:
        Validated Path object

    Raises:
        FileOperationError: If path is invalid
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileOperationError(
                f"File not found: {path}", context={"operation": operation, "path": str(path)}
            )
        return path
    except Exception as e:
        if isinstance(e, FileOperationError):
            raise
        raise FileOperationError(
            f"Invalid file path: {file_path}", context={"operation": operation, "error": str(e)}
        )


def format_user_error(message: str, suggestion: Optional[str] = None) -> str:
    """
    Format user-facing error message with consistent styling.

    Args:
        message: Error message
        suggestion: Optional suggestion for resolution

    Returns:
        Formatted error message
    """
    formatted = f"❌ ERROR: {message}"
    if suggestion:
        formatted += f"\n💡 SUGGESTION: {suggestion}"
    return formatted


def format_user_warning(message: str, suggestion: Optional[str] = None) -> str:
    """
    Format user-facing warning message with consistent styling.

    Args:
        message: Warning message
        suggestion: Optional suggestion for resolution

    Returns:
        Formatted warning message
    """
    formatted = f"⚠️  WARNING: {message}"
    if suggestion:
        formatted += f"\n💡 SUGGESTION: {suggestion}"
    return formatted
