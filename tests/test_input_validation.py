"""Test upfront input validation with helpful error messages.

This module tests the validation functions added in v2.6.0:
- Symbol validation against known_symbols
- Timeframe validation against available_timeframes
- Date format validation (YYYY-MM-DD)
"""

import pytest

import gapless_crypto_clickhouse as gcc


class TestSymbolValidation:
    """Test symbol validation with helpful error messages."""

    def test_invalid_symbol_raises_error(self):
        """Invalid symbol raises ValueError."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            gcc.download("INVALIDPAIR", "1h")

    def test_invalid_symbol_suggests_correction(self):
        """Invalid symbol with close match suggests correction."""
        with pytest.raises(ValueError, match="Did you mean"):
            gcc.download("BTCUSD", "1h")

    def test_invalid_symbol_shows_supported_list(self):
        """Invalid symbol shows list of supported symbols."""
        with pytest.raises(ValueError, match="Supported .* symbols.*get_supported_symbols"):
            gcc.download("XYZ", "1h")

    def test_valid_symbol_passes(self):
        """Valid symbol passes validation (may fail later for other reasons)."""
        # Should not raise ValueError for symbol validation
        try:
            gcc.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
        except ValueError as e:
            if "Invalid symbol" in str(e):
                pytest.fail("Valid symbol should not raise symbol validation error")


class TestTimeframeValidation:
    """Test timeframe validation with helpful error messages."""

    def test_invalid_timeframe_raises_error(self):
        """Invalid timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            gcc.download("BTCUSDT", "3h")  # 3h not supported

    def test_invalid_timeframe_shows_supported_list(self):
        """Invalid timeframe shows all supported timeframes."""
        with pytest.raises(ValueError, match="Supported timeframes:.*1s.*1m.*1d"):
            gcc.download("BTCUSDT", "7d")

    def test_valid_timeframe_passes(self):
        """Valid timeframe passes validation."""
        try:
            gcc.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
        except ValueError as e:
            if "Invalid timeframe" in str(e):
                pytest.fail("Valid timeframe should not raise timeframe validation error")


class TestDateFormatValidation:
    """Test date format validation with helpful error messages."""

    def test_invalid_date_format_raises_error(self):
        """Invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start/start_date format"):
            gcc.download("BTCUSDT", "1h", start="2024/01/01")

    def test_invalid_date_format_shows_example(self):
        """Invalid date format shows expected format."""
        with pytest.raises(ValueError, match="Expected format: YYYY-MM-DD"):
            gcc.download("BTCUSDT", "1h", start="01-01-2024")

    def test_invalid_date_value_raises_error(self):
        """Invalid date value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start/start_date date"):
            gcc.download("BTCUSDT", "1h", start="2024-13-01")  # Month 13

    def test_valid_date_format_passes(self):
        """Valid date format passes validation."""
        try:
            gcc.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
        except ValueError as e:
            if "Invalid start" in str(e) or "Invalid end" in str(e):
                pytest.fail("Valid date format should not raise date validation error")


class TestFetchDataValidation:
    """Test validation also applies to fetch_data()."""

    def test_fetch_data_validates_symbol(self):
        """fetch_data() validates symbol."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            gcc.fetch_data("INVALID", "1h")

    def test_fetch_data_validates_timeframe(self):
        """fetch_data() validates timeframe."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            gcc.fetch_data("BTCUSDT", "3h")

    def test_fetch_data_validates_dates(self):
        """fetch_data() validates date formats."""
        with pytest.raises(ValueError, match="Invalid start/start_date format"):
            gcc.fetch_data("BTCUSDT", "1h", start="2024/01/01")


class TestValidationWithParameterAliases:
    """Test validation works correctly with parameter aliases (v2.5.0 + v2.6.0)."""

    def test_start_date_alias_validation(self):
        """Validation works with start_date alias."""
        with pytest.raises(ValueError, match="Invalid start/start_date format"):
            gcc.download("BTCUSDT", "1h", start_date="2024/01/01")

    def test_end_date_alias_validation(self):
        """Validation works with end_date alias."""
        with pytest.raises(ValueError, match="Invalid end/end_date format"):
            gcc.download("BTCUSDT", "1h", end_date="2024/01/01")
