"""Unit tests for ClickHouse configuration (ADR-0044: Dual-Mode Support).

Tests ClickHouseConfig dataclass with Cloud and Local modes.
All tests are unit tests - no network or Cloud/Local connection required.

Mode Selection:
- GCCH_MODE=local → Local mode (localhost:8123)
- GCCH_MODE=cloud → Cloud mode (requires CLICKHOUSE_HOST)
- GCCH_MODE=auto (default) → Auto-detect based on CLICKHOUSE_HOST
"""

import os
from unittest.mock import patch

import pytest

from gapless_crypto_clickhouse.clickhouse.config import (
    ClickHouseCloudRequiredError,
    ClickHouseConfig,
    ENV_GCCH_MODE,
    ENV_CLICKHOUSE_HOST,
    MODE_LOCAL,
    MODE_CLOUD,
    MODE_AUTO,
    LOCAL_HOSTS,
    PORT_LOCAL_HTTP,
    PORT_LOCAL_NATIVE,
    PORT_CLOUD_HTTP,
    PORT_CLOUD_NATIVE,
)


class TestClickHouseConfig:
    """Test ClickHouseConfig dataclass."""

    def test_default_values(self):
        """Test default values are for local mode (ADR-0044)."""
        config = ClickHouseConfig()
        assert config.host == "localhost"  # Local default
        assert config.port == PORT_LOCAL_NATIVE  # Local native port (9000)
        assert config.http_port == PORT_LOCAL_HTTP  # Local HTTP port (8123)
        assert config.database == "default"
        assert config.user == "default"
        assert config.secure is False  # Local mode default

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
    """Test ClickHouseConfig.from_env() with dual-mode support (ADR-0044)."""

    def test_from_env_explicit_local_mode(self):
        """GCCH_MODE=local creates local config without CLICKHOUSE_HOST."""
        env_vars = {ENV_GCCH_MODE: MODE_LOCAL}
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "localhost"
            assert config.http_port == PORT_LOCAL_HTTP
            assert config.port == PORT_LOCAL_NATIVE
            assert config.secure is False

    def test_from_env_explicit_cloud_mode_requires_host(self):
        """GCCH_MODE=cloud without CLICKHOUSE_HOST raises error."""
        env_vars = {ENV_GCCH_MODE: MODE_CLOUD}
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ClickHouseCloudRequiredError) as exc_info:
                ClickHouseConfig.from_env()
            assert "CLICKHOUSE_HOST" in str(exc_info.value)
            assert "REQUIRED" in str(exc_info.value)

    def test_from_env_explicit_cloud_mode_with_host(self):
        """GCCH_MODE=cloud with CLICKHOUSE_HOST creates cloud config."""
        env_vars = {
            ENV_GCCH_MODE: MODE_CLOUD,
            ENV_CLICKHOUSE_HOST: "myinstance.clickhouse.cloud",
            "CLICKHOUSE_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "myinstance.clickhouse.cloud"
            assert config.http_port == PORT_CLOUD_HTTP
            assert config.port == PORT_CLOUD_NATIVE
            assert config.secure is True

    def test_from_env_auto_detect_empty_host_is_local(self):
        """Auto mode with empty CLICKHOUSE_HOST uses local mode."""
        env_vars = {ENV_CLICKHOUSE_HOST: ""}
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "localhost"
            assert config.http_port == PORT_LOCAL_HTTP
            assert config.secure is False

    def test_from_env_auto_detect_localhost_is_local(self):
        """Auto mode with localhost uses local mode."""
        env_vars = {ENV_CLICKHOUSE_HOST: "localhost"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "localhost"
            assert config.http_port == PORT_LOCAL_HTTP
            assert config.secure is False

    def test_from_env_auto_detect_127_is_local(self):
        """Auto mode with 127.0.0.1 uses local mode."""
        env_vars = {ENV_CLICKHOUSE_HOST: "127.0.0.1"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "127.0.0.1"
            assert config.http_port == PORT_LOCAL_HTTP
            assert config.secure is False

    def test_from_env_auto_detect_remote_host_is_cloud(self):
        """Auto mode with remote hostname uses cloud mode."""
        env_vars = {ENV_CLICKHOUSE_HOST: "myinstance.clickhouse.cloud"}
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "myinstance.clickhouse.cloud"
            assert config.http_port == PORT_CLOUD_HTTP
            assert config.secure is True

    def test_from_env_with_all_vars_cloud(self):
        """Test from_env with all environment variables set (cloud mode)."""
        env_vars = {
            ENV_GCCH_MODE: MODE_CLOUD,
            ENV_CLICKHOUSE_HOST: "myinstance.clickhouse.cloud",
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

    def test_from_env_with_all_vars_local(self):
        """Test from_env with all environment variables set (local mode)."""
        env_vars = {
            ENV_GCCH_MODE: MODE_LOCAL,
            ENV_CLICKHOUSE_HOST: "localhost",
            "CLICKHOUSE_PORT": "9000",
            "CLICKHOUSE_HTTP_PORT": "8123",
            "CLICKHOUSE_DATABASE": "mydb",
            "CLICKHOUSE_USER": "myuser",
            "CLICKHOUSE_PASSWORD": "",
            "CLICKHOUSE_SECURE": "false",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = ClickHouseConfig.from_env()
            assert config.host == "localhost"
            assert config.port == 9000
            assert config.http_port == 8123
            assert config.database == "mydb"
            assert config.user == "myuser"
            assert config.password == ""
            assert config.secure is False

    def test_from_env_secure_variations_cloud(self):
        """Test from_env parses CLICKHOUSE_SECURE correctly in cloud mode."""
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
                ENV_GCCH_MODE: MODE_CLOUD,
                ENV_CLICKHOUSE_HOST: "test.cloud",
                "CLICKHOUSE_SECURE": secure_value,
            }
            with patch.dict(os.environ, env_vars, clear=True):
                config = ClickHouseConfig.from_env()
                assert config.secure is expected, f"Failed for {secure_value}"

    def test_from_env_invalid_port_raises_error_local(self):
        """Invalid CLICKHOUSE_PORT raises ValueError in local mode."""
        env_vars = {
            ENV_GCCH_MODE: MODE_LOCAL,
            "CLICKHOUSE_PORT": "not_a_number",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                ClickHouseConfig.from_env()
            assert "CLICKHOUSE_PORT" in str(exc_info.value)

    def test_from_env_invalid_port_raises_error_cloud(self):
        """Invalid CLICKHOUSE_PORT raises ValueError in cloud mode."""
        env_vars = {
            ENV_GCCH_MODE: MODE_CLOUD,
            ENV_CLICKHOUSE_HOST: "test.cloud",
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
