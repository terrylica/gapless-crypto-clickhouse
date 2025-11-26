"""
ClickHouse configuration for gapless-crypto-clickhouse.

**ClickHouse Cloud** is the single source of truth for this package (ADR-0043).
Configure credentials via Doppler (aws-credentials/prd) or environment variables.

STRICT CLOUD-ONLY POLICY:
- CLICKHOUSE_HOST environment variable is REQUIRED (no localhost fallback)
- Default port is 8443 (ClickHouse Cloud HTTPS)
- Default secure is True (TLS/SSL enabled)

Error Handling: Raise and propagate (no fallback, no defaults for required params)
"""

import os
from dataclasses import dataclass


class ClickHouseCloudRequiredError(ValueError):
    """Raised when ClickHouse Cloud credentials are not configured."""

    pass


@dataclass
class ClickHouseConfig:
    """
    ClickHouse Cloud connection configuration.

    **ClickHouse Cloud** is the single source of truth (ADR-0043).
    CLICKHOUSE_HOST environment variable is REQUIRED - no localhost fallback.

    Attributes:
        host: ClickHouse Cloud hostname (REQUIRED, e.g., your-instance.clickhouse.cloud)
        port: Native protocol port (default: 9440 for Cloud secure)
        http_port: HTTPS interface port (default: 8443 for Cloud)
        database: Database name (default: default)
        user: Username (default: default)
        password: Password (required for Cloud)
        secure: Enable TLS/SSL (default: True for Cloud)

    Environment Variables:
        CLICKHOUSE_HOST: ClickHouse Cloud hostname (REQUIRED)
        CLICKHOUSE_PORT: Native port (9440 for Cloud secure)
        CLICKHOUSE_HTTP_PORT: HTTPS port (8443 for Cloud)
        CLICKHOUSE_DATABASE: Database name
        CLICKHOUSE_USER: Username
        CLICKHOUSE_PASSWORD: Password (required for Cloud)
        CLICKHOUSE_SECURE: Set to 'true' for ClickHouse Cloud (default: true)

    Example:
        # ClickHouse Cloud via Doppler (recommended)
        # doppler run --project aws-credentials --config prd -- python script.py
        config = ClickHouseConfig.from_env()

        # ClickHouse Cloud via environment
        # export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
        # export CLICKHOUSE_PASSWORD=your-password
        config = ClickHouseConfig.from_env()

    Raises:
        ClickHouseCloudRequiredError: If CLICKHOUSE_HOST is not set
    """

    host: str = ""  # REQUIRED - no default (Cloud-only policy)
    port: int = 9440  # Cloud secure native port
    http_port: int = 8443  # Cloud HTTPS port
    database: str = "default"
    user: str = "default"
    password: str = ""
    secure: bool = True  # Cloud requires TLS/SSL

    @classmethod
    def from_env(cls) -> "ClickHouseConfig":
        """
        Create configuration from environment variables.

        **STRICT CLOUD-ONLY POLICY**: CLICKHOUSE_HOST is REQUIRED.
        No localhost fallback - ClickHouse Cloud is the single source of truth.

        Returns:
            ClickHouseConfig with values from environment

        Raises:
            ClickHouseCloudRequiredError: If CLICKHOUSE_HOST is not set
            ValueError: If CLICKHOUSE_PORT is not a valid integer

        Example:
            # Via Doppler (recommended)
            # doppler run --project aws-credentials --config prd -- python script.py
            config = ClickHouseConfig.from_env()

            # Via environment variables
            # export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
            # export CLICKHOUSE_PASSWORD=your-password
            config = ClickHouseConfig.from_env()
        """
        # STRICT CLOUD-ONLY: Require CLICKHOUSE_HOST (ADR-0043)
        host = os.getenv("CLICKHOUSE_HOST")
        if not host:
            raise ClickHouseCloudRequiredError(
                "CLICKHOUSE_HOST environment variable is REQUIRED.\n"
                "ClickHouse Cloud is the single source of truth (ADR-0043).\n"
                "\n"
                "Configure via Doppler (recommended):\n"
                "  doppler run --project aws-credentials --config prd -- python script.py\n"
                "\n"
                "Or via environment variables:\n"
                "  export CLICKHOUSE_HOST=your-instance.clickhouse.cloud\n"
                "  export CLICKHOUSE_PASSWORD=your-password"
            )

        try:
            # Cloud defaults: 9440 (native secure), 8443 (HTTPS)
            port = int(os.getenv("CLICKHOUSE_PORT", "9440"))
            http_port = int(os.getenv("CLICKHOUSE_HTTP_PORT", "8443"))
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
            # Cloud-only default: secure=True
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
