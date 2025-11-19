"""Comprehensive tests for error_handling module.

Tests standardized error handling framework, custom exceptions,
logging utilities, and error formatting helpers.

Target: Improve error_handling.py coverage from 31% to 70%+
"""

import logging
import tempfile
from pathlib import Path

import pytest

from gapless_crypto_clickhouse.utils.error_handling import (
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


class TestCustomExceptions:
    """Test custom exception hierarchy."""

    def test_gapless_crypto_error_basic(self):
        """Test base exception without context."""
        error = GaplessCryptoError("Test error")
        assert str(error) == "Test error"
        assert error.context == {}

    def test_gapless_crypto_error_with_context(self):
        """Test base exception with context dictionary."""
        context = {"symbol": "BTCUSDT", "timeframe": "1h"}
        error = GaplessCryptoError("Data error", context=context)
        assert str(error) == "Data error"
        assert error.context == context
        assert error.context["symbol"] == "BTCUSDT"

    def test_data_collection_error(self):
        """Test DataCollectionError inherits from base."""
        error = DataCollectionError("Collection failed", context={"url": "test.zip"})
        assert isinstance(error, GaplessCryptoError)
        assert str(error) == "Collection failed"
        assert error.context["url"] == "test.zip"

    def test_gap_filling_error(self):
        """Test GapFillingError inherits from base."""
        error = GapFillingError("Gap detection failed")
        assert isinstance(error, GaplessCryptoError)
        assert error.context == {}

    def test_file_operation_error(self):
        """Test FileOperationError inherits from base."""
        error = FileOperationError("File not found", context={"path": "/tmp/test.csv"})
        assert isinstance(error, GaplessCryptoError)
        assert error.context["path"] == "/tmp/test.csv"

    def test_validation_error(self):
        """Test ValidationError inherits from base."""
        error = ValidationError("Invalid data", context={"column": "close"})
        assert isinstance(error, GaplessCryptoError)
        assert error.context["column"] == "close"


class TestStandardLogger:
    """Test standardized logger configuration."""

    def test_get_standard_logger_basic(self):
        """Test logger creation with module name."""
        logger = get_standard_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "gapless_crypto_clickhouse.test_module"

    def test_get_standard_logger_has_handler(self):
        """Test logger has StreamHandler configured."""
        logger = get_standard_logger("test_handler")
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_get_standard_logger_has_formatter(self):
        """Test logger handler has proper formatter."""
        logger = get_standard_logger("test_formatter")
        handler = logger.handlers[0]
        assert handler.formatter is not None
        # Check format includes expected components
        format_str = handler.formatter._fmt
        assert "%(asctime)s" in format_str
        assert "%(name)s" in format_str
        assert "%(levelname)s" in format_str

    def test_get_standard_logger_level(self):
        """Test logger default level is INFO."""
        logger = get_standard_logger("test_level")
        assert logger.level == logging.INFO

    def test_get_standard_logger_reuse(self):
        """Test calling twice returns same logger without duplicate handlers."""
        logger1 = get_standard_logger("test_reuse")
        handler_count = len(logger1.handlers)
        logger2 = get_standard_logger("test_reuse")
        # Should be the same logger object
        assert logger1 is logger2
        # Should not add duplicate handlers
        assert len(logger2.handlers) == handler_count


class TestHandleOperationError:
    """Test standardized operation error handler."""

    def test_handle_operation_error_basic(self):
        """Test basic error handling without logger."""
        exception = ValueError("Test error")
        result = handle_operation_error("Test operation", exception)
        assert result is None

    def test_handle_operation_error_with_context(self):
        """Test error handling with context dictionary."""
        exception = RuntimeError("Operation failed")
        context = {"file": "test.csv", "line": 42}
        result = handle_operation_error("Read file", exception, context=context)
        assert result is None

    def test_handle_operation_error_with_logger(self, caplog):
        """Test error handling with custom logger."""
        logger = get_standard_logger("test_error_handler")
        exception = IOError("File error")
        with caplog.at_level(logging.ERROR):
            handle_operation_error("File operation", exception, logger=logger)
        assert "File operation failed" in caplog.text

    def test_handle_operation_error_reraise(self):
        """Test error handling with reraise flag (via safe_operation)."""

        # reraise only works when called from within except block
        # This is the proper usage pattern via safe_operation
        def failing_func():
            raise ValueError("Should reraise")

        with pytest.raises(ValueError, match="Should reraise"):
            safe_operation("Test operation", failing_func, reraise=True)

    def test_handle_operation_error_default_return(self):
        """Test error handling with default return value."""
        exception = KeyError("Missing key")
        result = handle_operation_error("Dict lookup", exception, default_return=42)
        assert result == 42

    def test_handle_operation_error_debug_traceback(self, caplog):
        """Test full traceback logged at DEBUG level."""
        logger = get_standard_logger("test_traceback")
        logger.setLevel(logging.DEBUG)
        exception = RuntimeError("Debug test")
        with caplog.at_level(logging.DEBUG):
            handle_operation_error("Debug operation", exception, logger=logger)
        assert "Full traceback" in caplog.text


class TestSafeOperation:
    """Test safe operation wrapper."""

    def test_safe_operation_success(self):
        """Test safe operation with successful function."""
        result = safe_operation("Test", lambda: 42)
        assert result == 42

    def test_safe_operation_exception_caught(self):
        """Test safe operation catches specified exceptions."""

        def failing_func():
            raise ValueError("Expected error")

        result = safe_operation("Test", failing_func, exception_types=(ValueError,))
        assert result is None

    def test_safe_operation_default_return_on_error(self):
        """Test safe operation returns default value on error."""

        def failing_func():
            raise RuntimeError("Error")

        result = safe_operation("Test", failing_func, default_return="fallback")
        assert result == "fallback"

    def test_safe_operation_reraise(self):
        """Test safe operation can reraise exceptions."""

        def failing_func():
            raise ValueError("Should propagate")

        with pytest.raises(ValueError, match="Should propagate"):
            safe_operation("Test", failing_func, reraise=True)

    def test_safe_operation_with_context(self, caplog):
        """Test safe operation logs context."""
        logger = get_standard_logger("test_safe_op")

        def failing_func():
            raise IOError("File error")

        with caplog.at_level(logging.ERROR):
            safe_operation(
                "File read",
                failing_func,
                context={"file": "test.csv"},
                logger=logger,
            )
        assert "file=test.csv" in caplog.text

    def test_safe_operation_specific_exception_types(self):
        """Test safe operation only catches specified exception types."""

        def failing_func():
            raise TypeError("Wrong type")

        # Should not catch TypeError when only ValueError specified
        with pytest.raises(TypeError):
            safe_operation("Test", failing_func, exception_types=(ValueError,))


class TestValidateFilePath:
    """Test file path validation."""

    def test_validate_file_path_valid(self):
        """Test validation with existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                result = validate_file_path(tmp_path)
                assert isinstance(result, Path)
                assert result == tmp_path
            finally:
                tmp_path.unlink(missing_ok=True)

    def test_validate_file_path_string_input(self):
        """Test validation accepts string path."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            try:
                result = validate_file_path(tmp_path)
                assert isinstance(result, Path)
                assert str(result) == tmp_path
            finally:
                Path(tmp_path).unlink(missing_ok=True)

    def test_validate_file_path_not_found(self):
        """Test validation raises FileOperationError for missing file."""
        with pytest.raises(FileOperationError, match="File not found"):
            validate_file_path("/nonexistent/path/file.csv")

    def test_validate_file_path_with_operation_context(self):
        """Test validation includes operation context in error."""
        with pytest.raises(FileOperationError) as exc_info:
            validate_file_path("/missing/file.csv", operation="data loading")
        assert exc_info.value.context["operation"] == "data loading"

    def test_validate_file_path_invalid_type(self):
        """Test validation handles invalid path types."""
        with pytest.raises(FileOperationError, match="Invalid file path"):
            validate_file_path(None)  # type: ignore


class TestUserMessageFormatting:
    """Test user-facing message formatting."""

    def test_format_user_error_basic(self):
        """Test error formatting without suggestion."""
        result = format_user_error("Something went wrong")
        assert "❌ ERROR: Something went wrong" in result
        assert "SUGGESTION" not in result

    def test_format_user_error_with_suggestion(self):
        """Test error formatting with suggestion."""
        result = format_user_error(
            "Invalid symbol", suggestion="Use get_supported_symbols() to see available symbols"
        )
        assert "❌ ERROR: Invalid symbol" in result
        assert "💡 SUGGESTION: Use get_supported_symbols()" in result

    def test_format_user_warning_basic(self):
        """Test warning formatting without suggestion."""
        result = format_user_warning("Data may be incomplete")
        assert "⚠️  WARNING: Data may be incomplete" in result
        assert "SUGGESTION" not in result

    def test_format_user_warning_with_suggestion(self):
        """Test warning formatting with suggestion."""
        result = format_user_warning(
            "Gap detected", suggestion="Use auto_fill_gaps=True to fill missing data"
        )
        assert "⚠️  WARNING: Gap detected" in result
        assert "💡 SUGGESTION: Use auto_fill_gaps=True" in result
