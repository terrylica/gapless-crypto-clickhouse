"""
ClickHouse configuration for gapless-crypto-clickhouse.

Supports TWO deployment modes (ADR-0044, amends ADR-0043):

**Cloud Mode** (production, multi-user):
- Connect to ClickHouse Cloud on AWS
- CLICKHOUSE_HOST environment variable is REQUIRED
- Default port: 8443 (HTTPS), secure: True

**Local Mode** (development, backtesting):
- Connect to local ClickHouse installation
- No credentials required
- Default port: 8123 (HTTP), secure: False

Mode Selection (GCCH_MODE environment variable):
- "local": Force local mode
- "cloud": Force cloud mode (requires CLICKHOUSE_HOST)
- "auto" (default): Auto-detect based on CLICKHOUSE_HOST
  - localhost/127.0.0.1/"" → local mode
  - Remote hostname → cloud mode

Error Handling: Raise and propagate (no fallback for cloud mode required params)
"""

import os
from dataclasses import dataclass

# Import semantic constants from centralized module (ADR-0046)
from ..constants import (
    ENV_CLICKHOUSE_HOST,
    ENV_GCCH_MODE,
    LOCAL_HOSTS,
    MODE_AUTO,
    MODE_CLOUD,
    MODE_LOCAL,
    PORT_CLOUD_HTTP,
    PORT_CLOUD_NATIVE,
    PORT_LOCAL_HTTP,
    PORT_LOCAL_NATIVE,
)

# Re-export for backward compatibility
__all__ = [
    "ClickHouseCloudRequiredError",
    "ClickHouseConfig",
    "ENV_GCCH_MODE",
    "ENV_CLICKHOUSE_HOST",
    "MODE_LOCAL",
    "MODE_CLOUD",
    "MODE_AUTO",
    "LOCAL_HOSTS",
    "PORT_LOCAL_HTTP",
    "PORT_LOCAL_NATIVE",
    "PORT_CLOUD_HTTP",
    "PORT_CLOUD_NATIVE",
]


class ClickHouseCloudRequiredError(ValueError):
    """Raised when ClickHouse Cloud credentials are not configured in cloud mode."""

    pass


@dataclass
class ClickHouseConfig:
    """
    ClickHouse connection configuration supporting Cloud and Local modes (ADR-0044).

    Supports TWO deployment modes:
    - **Cloud Mode**: ClickHouse Cloud on AWS (production, requires credentials)
    - **Local Mode**: Local ClickHouse installation (development, no credentials)

    Attributes:
        host: ClickHouse hostname (Cloud or localhost)
        port: Native protocol port (9440 Cloud / 9000 Local)
        http_port: HTTP(S) interface port (8443 Cloud / 8123 Local)
        database: Database name (default: default)
        user: Username (default: default)
        password: Password (required for Cloud, optional for Local)
        secure: Enable TLS/SSL (True for Cloud, False for Local)

    Environment Variables:
        GCCH_MODE: Deployment mode ("local", "cloud", "auto")
        CLICKHOUSE_HOST: Hostname (required for cloud mode)
        CLICKHOUSE_PORT: Native port
        CLICKHOUSE_HTTP_PORT: HTTP(S) port
        CLICKHOUSE_DATABASE: Database name
        CLICKHOUSE_USER: Username
        CLICKHOUSE_PASSWORD: Password
        CLICKHOUSE_SECURE: Enable TLS ("true"/"false")

    Example:
        # Auto-detect mode (Cloud if CLICKHOUSE_HOST is remote)
        config = ClickHouseConfig.from_env()

        # Explicit local mode
        # export GCCH_MODE=local
        config = ClickHouseConfig.from_env()

        # Cloud via Doppler (recommended)
        # doppler run --project aws-credentials --config prd -- python script.py
        config = ClickHouseConfig.from_env()

    Raises:
        ClickHouseCloudRequiredError: If cloud mode but CLICKHOUSE_HOST not set
    """

    host: str = "localhost"  # Default to localhost for local mode
    port: int = PORT_LOCAL_NATIVE  # Local native port
    http_port: int = PORT_LOCAL_HTTP  # Local HTTP port
    database: str = "default"
    user: str = "default"
    password: str = ""
    secure: bool = False  # Local mode default

    @classmethod
    def from_env(cls) -> "ClickHouseConfig":
        """
        Create configuration from environment variables with mode detection.

        Mode Selection (ADR-0044):
        - GCCH_MODE=local → Local mode (localhost:8123)
        - GCCH_MODE=cloud → Cloud mode (requires CLICKHOUSE_HOST)
        - GCCH_MODE=auto (default) → Auto-detect based on CLICKHOUSE_HOST

        Returns:
            ClickHouseConfig with values from environment

        Raises:
            ClickHouseCloudRequiredError: If cloud mode but CLICKHOUSE_HOST not set
            ValueError: If CLICKHOUSE_PORT is not a valid integer

        Example:
            # Local mode (explicit)
            # export GCCH_MODE=local
            config = ClickHouseConfig.from_env()

            # Cloud mode via Doppler (recommended)
            # doppler run --project aws-credentials --config prd -- python script.py
            config = ClickHouseConfig.from_env()

            # Auto-detect (localhost → local, remote → cloud)
            config = ClickHouseConfig.from_env()
        """
        mode = os.getenv(ENV_GCCH_MODE, MODE_AUTO).lower()

        if mode == MODE_LOCAL:
            return cls._from_env_local()
        elif mode == MODE_CLOUD:
            return cls._from_env_cloud()
        else:  # auto
            host = os.getenv(ENV_CLICKHOUSE_HOST, "")
            if host in LOCAL_HOSTS:
                return cls._from_env_local()
            return cls._from_env_cloud()

    @classmethod
    def _from_env_local(cls) -> "ClickHouseConfig":
        """
        Create local mode configuration.

        Local defaults:
        - host: localhost
        - port: 9000 (native)
        - http_port: 8123 (HTTP)
        - secure: False
        - password: optional
        """
        try:
            port = int(os.getenv("CLICKHOUSE_PORT", str(PORT_LOCAL_NATIVE)))
            http_port = int(os.getenv("CLICKHOUSE_HTTP_PORT", str(PORT_LOCAL_HTTP)))
        except ValueError as e:
            raise ValueError(
                f"Invalid CLICKHOUSE_PORT or CLICKHOUSE_HTTP_PORT (must be integer): {e}"
            ) from e

        # Default to localhost if CLICKHOUSE_HOST is empty or not set
        host = os.getenv(ENV_CLICKHOUSE_HOST, "localhost")
        if not host:  # Handle empty string case
            host = "localhost"

        return cls(
            host=host,
            port=port,
            http_port=http_port,
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            secure=os.getenv("CLICKHOUSE_SECURE", "false").lower() in ("true", "1", "yes"),
        )

    @classmethod
    def _from_env_cloud(cls) -> "ClickHouseConfig":
        """
        Create cloud mode configuration.

        Cloud defaults:
        - host: REQUIRED (no fallback)
        - port: 9440 (native secure)
        - http_port: 8443 (HTTPS)
        - secure: True
        - password: required for production

        Raises:
            ClickHouseCloudRequiredError: If CLICKHOUSE_HOST is not set
        """
        host = os.getenv(ENV_CLICKHOUSE_HOST)
        if not host:
            raise ClickHouseCloudRequiredError(
                "CLICKHOUSE_HOST environment variable is REQUIRED in cloud mode.\n"
                "ClickHouse Cloud is the production recommendation (ADR-0044).\n"
                "\n"
                "Configure via Doppler (recommended):\n"
                "  doppler run --project aws-credentials --config prd -- python script.py\n"
                "\n"
                "Or via environment variables:\n"
                "  export CLICKHOUSE_HOST=your-instance.clickhouse.cloud\n"
                "  export CLICKHOUSE_PASSWORD=your-password\n"
                "\n"
                "For local development, use:\n"
                "  export GCCH_MODE=local"
            )

        try:
            port = int(os.getenv("CLICKHOUSE_PORT", str(PORT_CLOUD_NATIVE)))
            http_port = int(os.getenv("CLICKHOUSE_HTTP_PORT", str(PORT_CLOUD_HTTP)))
        except ValueError as e:
            raise ValueError(
                f"Invalid CLICKHOUSE_PORT or CLICKHOUSE_HTTP_PORT (must be integer): {e}"
            ) from e

        return cls(
            host=host,
            port=port,
            http_port=http_port,
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            secure=os.getenv("CLICKHOUSE_SECURE", "true").lower() in ("true", "1", "yes"),
        )

    def validate(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If any parameter is invalid

        Example:
            config = ClickHouseConfig(port=-1)
            config.validate()  # Raises ValueError
        """
        if not self.host:
            raise ValueError("host cannot be empty")

        if not (1 <= self.port <= 65535):
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")

        if not (1 <= self.http_port <= 65535):
            raise ValueError(f"http_port must be between 1 and 65535, got {self.http_port}")

        if not self.database:
            raise ValueError("database cannot be empty")

        if not self.user:
            raise ValueError("user cannot be empty")

    def __repr__(self) -> str:
        """String representation (hide password)."""
        return (
            f"ClickHouseConfig(host='{self.host}', port={self.port}, "
            f"http_port={self.http_port}, database='{self.database}', "
            f"user='{self.user}', password='***', secure={self.secure})"
        )
