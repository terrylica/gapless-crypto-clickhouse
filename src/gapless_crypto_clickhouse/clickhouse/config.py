"""
ClickHouse configuration for gapless-crypto-data v4.0.0.

Environment variable support for connection parameters.
Follows same pattern as QuestDBConfig (ADR-0003).

Error Handling: Raise and propagate (no fallback, no defaults for required params)
"""

import os
from dataclasses import dataclass


@dataclass
class ClickHouseConfig:
    """
    ClickHouse connection configuration.

    Attributes:
        host: ClickHouse server hostname (default: localhost)
        port: Native protocol port (default: 9000)
        http_port: HTTP interface port (default: 8123)
        database: Database name (default: default)
        user: Username (default: default)
        password: Password (default: empty)

    Environment Variables:
        CLICKHOUSE_HOST: Override host
        CLICKHOUSE_PORT: Override native protocol port
        CLICKHOUSE_HTTP_PORT: Override HTTP port
        CLICKHOUSE_DATABASE: Override database name
        CLICKHOUSE_USER: Override username
        CLICKHOUSE_PASSWORD: Override password

    Example:
        # Default configuration (localhost)
        config = ClickHouseConfig.from_env()

        # Custom configuration
        config = ClickHouseConfig(host="clickhouse.example.com", port=9000)
    """

    host: str = "localhost"
    port: int = 9000
    http_port: int = 8123
    database: str = "default"
    user: str = "default"
    password: str = ""

    @classmethod
    def from_env(cls) -> "ClickHouseConfig":
        """
        Create configuration from environment variables.

        Returns:
            ClickHouseConfig with values from environment or defaults

        Raises:
            ValueError: If CLICKHOUSE_PORT is not a valid integer

        Example:
            export CLICKHOUSE_HOST=clickhouse.example.com
            export CLICKHOUSE_PORT=9000
            config = ClickHouseConfig.from_env()
        """
        try:
            port = int(os.getenv("CLICKHOUSE_PORT", "9000"))
            http_port = int(os.getenv("CLICKHOUSE_HTTP_PORT", "8123"))
        except ValueError as e:
            raise ValueError(
                f"Invalid CLICKHOUSE_PORT or CLICKHOUSE_HTTP_PORT (must be integer): {e}"
            ) from e

        return cls(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=port,
            http_port=http_port,
            database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            user=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
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
            f"user='{self.user}', password='***')"
        )
