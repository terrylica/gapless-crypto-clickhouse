"""Unit tests for ClickHouse configuration (ADR-0043: Cloud-Only Policy).

Tests ClickHouseConfig dataclass and ClickHouseCloudRequiredError exception.
All tests are unit tests - no network or Cloud connection required.
"""

import os
from unittest.mock import patch

import pytest

from gapless_crypto_clickhouse.clickhouse.config import (
    ClickHouseCloudRequiredError,
    ClickHouseConfig,
)


class TestClickHouseConfig:
    """Test ClickHouseConfig dataclass."""

    def test_default_values(self):
        """Test default values for Cloud configuration."""
        config = ClickHouseConfig(host="test.clickhouse.cloud", password="secret")
        assert config.port == 9440  # Cloud native secure port
        assert config.http_port == 8443  # Cloud HTTPS port
        assert config.database == "default"
        assert config.user == "default"
        assert config.secure is True  # Cloud requires TLS

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ClickHouseConfig(
            host="custom.clickhouse.cloud",
            port=9000,
            http_port=8123,
            database="mydb",
            user="myuser",
            password="mypass",
            secure=False,
        )
        assert config.host == "custom.clickhouse.cloud"
        assert config.port == 9000
        assert config.http_port == 8123
        assert config.database == "mydb"
        assert config.user == "myuser"
        assert config.password == "mypass"
        assert config.secure is False

    def test_repr_hides_password(self):
        """Test __repr__ hides password for security."""
        config = ClickHouseConfig(host="test.cloud", password="supersecret")
        repr_str = repr(config)
        assert "supersecret" not in repr_str
        assert "***" in repr_str
        assert "test.cloud" in repr_str


class TestClickHouseConfigFromEnv:
    """Test ClickHouseConfig.from_env() method."""

    def test_from_env_missing_host_raises_error(self):
        """Missing CLICKHOUSE_HOST raises ClickHouseCloudRequiredError."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove CLICKHOUSE_HOST if it exists
            env = {k: v for k, v in os.environ.items() if k != "CLICKHOUSE_HOST"}
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ClickHouseCloudRequiredError) as exc_info:
                    ClickHouseConfig.from_env()
                assert "CLICKHOUSE_HOST" in str(exc_info.value)
                assert "REQUIRED" in str(exc_info.value)

    def test_from_env_with_all_vars(self):
        """Test from_env with all environment variables set."""
        env_vars = {
            "CLICKHOUSE_HOST": "myinstance.clickhouse.cloud",
            "CLICKHOUSE_PORT": "9440",
            "CLICKHOUSE_HTTP_PORT": "8443",
            "CLICKHOUSE_DATABASE": "production",
            "CLICKHOUSE_USER": "admin",
            "CLICKHOUSE_PASSWORD": "secret123",
            "CLICKHOUSE_SECURE": "true",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "myinstance.clickhouse.cloud"
            assert config.port == 9440
            assert config.http_port == 8443
            assert config.database == "production"
            assert config.user == "admin"
            assert config.password == "secret123"
            assert config.secure is True

    def test_from_env_defaults(self):
        """Test from_env uses Cloud defaults when optional vars not set."""
        env_vars = {
            "CLICKHOUSE_HOST": "test.clickhouse.cloud",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "test.clickhouse.cloud"
            assert config.port == 9440  # Cloud default
            assert config.http_port == 8443  # Cloud default
            assert config.database == "default"
            assert config.user == "default"
            assert config.password == ""
            assert config.secure is True  # Cloud default

    def test_from_env_secure_variations(self):
        """Test from_env parses CLICKHOUSE_SECURE correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
        ]
        for secure_value, expected in test_cases:
            env_vars = {
                "CLICKHOUSE_HOST": "test.cloud",
                "CLICKHOUSE_SECURE": secure_value,
            }
            with patch.dict(os.environ, env_vars, clear=True):
                config = ClickHouseConfig.from_env()
                assert config.secure is expected, f"Failed for {secure_value}"

    def test_from_env_invalid_port_raises_error(self):
        """Invalid CLICKHOUSE_PORT raises ValueError."""
        env_vars = {
            "CLICKHOUSE_HOST": "test.cloud",
            "CLICKHOUSE_PORT": "not_a_number",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ClickHouseConfig.from_env()
            assert "CLICKHOUSE_PORT" in str(exc_info.value)


class TestClickHouseConfigValidate:
    """Test ClickHouseConfig.validate() method."""

    def test_validate_empty_host(self):
        """Empty host raises ValueError."""
        config = ClickHouseConfig(host="", password="test")
        with pytest.raises(ValueError, match="host cannot be empty"):
            config.validate()

    def test_validate_invalid_port_zero(self):
        """Port 0 raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", port=0)
        with pytest.raises(ValueError, match="port must be between"):
            config.validate()

    def test_validate_invalid_port_negative(self):
        """Negative port raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", port=-1)
        with pytest.raises(ValueError, match="port must be between"):
            config.validate()

    def test_validate_invalid_port_too_high(self):
        """Port > 65535 raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", port=70000)
        with pytest.raises(ValueError, match="port must be between"):
            config.validate()

    def test_validate_invalid_http_port(self):
        """Invalid http_port raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", http_port=0)
        with pytest.raises(ValueError, match="http_port must be between"):
            config.validate()

    def test_validate_empty_database(self):
        """Empty database raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", database="")
        with pytest.raises(ValueError, match="database cannot be empty"):
            config.validate()

    def test_validate_empty_user(self):
        """Empty user raises ValueError."""
        config = ClickHouseConfig(host="test.cloud", user="")
        with pytest.raises(ValueError, match="user cannot be empty"):
            config.validate()

    def test_validate_success(self):
        """Valid config passes validation."""
        config = ClickHouseConfig(
            host="test.clickhouse.cloud",
            port=8443,
            http_port=8443,
            database="default",
            user="default",
            password="secret",
        )
        # Should not raise
        config.validate()


class TestClickHouseCloudRequiredError:
    """Test ClickHouseCloudRequiredError exception."""

    def test_error_is_value_error(self):
        """ClickHouseCloudRequiredError is a ValueError subclass."""
        error = ClickHouseCloudRequiredError("test message")
        assert isinstance(error, ValueError)
        assert isinstance(error, ClickHouseCloudRequiredError)

    def test_error_message(self):
        """Error message is preserved."""
        message = "CLICKHOUSE_HOST not set"
        error = ClickHouseCloudRequiredError(message)
        assert str(error) == message

    def test_error_can_be_caught_as_value_error(self):
        """Error can be caught as ValueError."""
        try:
            raise ClickHouseCloudRequiredError("test")
        except ValueError as e:
            assert "test" in str(e)
