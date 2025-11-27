"""Deployment mode constants for ClickHouse configuration (ADR-0044, ADR-0046).

Single source of truth for deployment modes, environment variables,
and port configurations. Follows timeframe_constants.py pattern.

Design Principles:
    - Final[] annotations prevent accidental reassignment
    - Literal types enable type-safe mode selection
    - Self-validating assertions catch misconfigurations at import time

Environment Variable Usage:
    GCCH_MODE: Deployment mode selection ("local", "cloud", "auto")
    CLICKHOUSE_HOST: ClickHouse server hostname
    CLICKHOUSE_PORT: Native protocol port
    CLICKHOUSE_HTTP_PORT: HTTP(S) interface port
    CLICKHOUSE_DATABASE: Database name
    CLICKHOUSE_USER: Username
    CLICKHOUSE_PASSWORD: Password
    CLICKHOUSE_SECURE: Enable TLS ("true"/"false")
"""

from typing import Final, Literal, Tuple

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

DeploymentMode = Literal["local", "cloud", "auto"]
"""Type alias for valid deployment modes."""

# =============================================================================
# DEPLOYMENT MODES (ADR-0044)
# =============================================================================

MODE_LOCAL: Final[str] = "local"
"""Local ClickHouse installation (development, backtesting)."""

MODE_CLOUD: Final[str] = "cloud"
"""ClickHouse Cloud on AWS (production, multi-user)."""

MODE_AUTO: Final[str] = "auto"
"""Auto-detect mode based on CLICKHOUSE_HOST value."""

VALID_MODES: Final[Tuple[str, ...]] = (MODE_LOCAL, MODE_CLOUD, MODE_AUTO)
"""All valid deployment mode values for validation."""

# =============================================================================
# LOCAL HOST DETECTION
# =============================================================================

LOCAL_HOSTS: Final[Tuple[str, ...]] = ("localhost", "127.0.0.1", "")
"""Hostnames that indicate local mode in auto-detection."""

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

ENV_GCCH_MODE: Final[str] = "GCCH_MODE"
"""Environment variable for deployment mode selection."""

ENV_CLICKHOUSE_HOST: Final[str] = "CLICKHOUSE_HOST"
"""Environment variable for ClickHouse hostname."""

ENV_CLICKHOUSE_PORT: Final[str] = "CLICKHOUSE_PORT"
"""Environment variable for native protocol port."""

ENV_CLICKHOUSE_HTTP_PORT: Final[str] = "CLICKHOUSE_HTTP_PORT"
"""Environment variable for HTTP(S) interface port."""

ENV_CLICKHOUSE_DATABASE: Final[str] = "CLICKHOUSE_DATABASE"
"""Environment variable for database name."""

ENV_CLICKHOUSE_USER: Final[str] = "CLICKHOUSE_USER"
"""Environment variable for username."""

ENV_CLICKHOUSE_PASSWORD: Final[str] = "CLICKHOUSE_PASSWORD"
"""Environment variable for password."""

ENV_CLICKHOUSE_SECURE: Final[str] = "CLICKHOUSE_SECURE"
"""Environment variable for TLS/SSL enable flag."""

CLICKHOUSE_ENV_VARS: Final[Tuple[str, ...]] = (
    ENV_GCCH_MODE,
    ENV_CLICKHOUSE_HOST,
    ENV_CLICKHOUSE_PORT,
    ENV_CLICKHOUSE_HTTP_PORT,
    ENV_CLICKHOUSE_DATABASE,
    ENV_CLICKHOUSE_USER,
    ENV_CLICKHOUSE_PASSWORD,
    ENV_CLICKHOUSE_SECURE,
)
"""All ClickHouse-related environment variable names."""

# =============================================================================
# NETWORK PORTS
# =============================================================================

PORT_LOCAL_HTTP: Final[int] = 8123
"""Local ClickHouse HTTP interface port."""

PORT_LOCAL_NATIVE: Final[int] = 9000
"""Local ClickHouse native protocol port."""

PORT_CLOUD_HTTP: Final[int] = 8443
"""ClickHouse Cloud HTTPS interface port."""

PORT_CLOUD_NATIVE: Final[int] = 9440
"""ClickHouse Cloud native secure port."""

PORT_MIN: Final[int] = 1
"""Minimum valid port number."""

PORT_MAX: Final[int] = 65535
"""Maximum valid port number."""

# =============================================================================
# DEFAULTS
# =============================================================================

DEFAULT_HOST: Final[str] = "localhost"
"""Default hostname for local mode."""

DEFAULT_DATABASE: Final[str] = "default"
"""Default database name."""

DEFAULT_USER: Final[str] = "default"
"""Default username."""

# =============================================================================
# SELF-VALIDATING ASSERTIONS
# =============================================================================

# Verify deployment modes are complete
assert MODE_LOCAL in VALID_MODES, "MODE_LOCAL must be in VALID_MODES"
assert MODE_CLOUD in VALID_MODES, "MODE_CLOUD must be in VALID_MODES"
assert MODE_AUTO in VALID_MODES, "MODE_AUTO must be in VALID_MODES"

# Verify port ranges
assert PORT_MIN <= PORT_LOCAL_HTTP <= PORT_MAX, f"PORT_LOCAL_HTTP out of range: {PORT_LOCAL_HTTP}"
assert PORT_MIN <= PORT_LOCAL_NATIVE <= PORT_MAX, f"PORT_LOCAL_NATIVE out of range: {PORT_LOCAL_NATIVE}"
assert PORT_MIN <= PORT_CLOUD_HTTP <= PORT_MAX, f"PORT_CLOUD_HTTP out of range: {PORT_CLOUD_HTTP}"
assert PORT_MIN <= PORT_CLOUD_NATIVE <= PORT_MAX, f"PORT_CLOUD_NATIVE out of range: {PORT_CLOUD_NATIVE}"

# Verify environment variable names are non-empty
assert all(env for env in CLICKHOUSE_ENV_VARS), "All environment variable names must be non-empty"

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Type definitions
    "DeploymentMode",
    # Deployment modes
    "MODE_LOCAL",
    "MODE_CLOUD",
    "MODE_AUTO",
    "VALID_MODES",
    # Local host detection
    "LOCAL_HOSTS",
    # Environment variables
    "ENV_GCCH_MODE",
    "ENV_CLICKHOUSE_HOST",
    "ENV_CLICKHOUSE_PORT",
    "ENV_CLICKHOUSE_HTTP_PORT",
    "ENV_CLICKHOUSE_DATABASE",
    "ENV_CLICKHOUSE_USER",
    "ENV_CLICKHOUSE_PASSWORD",
    "ENV_CLICKHOUSE_SECURE",
    "CLICKHOUSE_ENV_VARS",
    # Ports
    "PORT_LOCAL_HTTP",
    "PORT_LOCAL_NATIVE",
    "PORT_CLOUD_HTTP",
    "PORT_CLOUD_NATIVE",
    "PORT_MIN",
    "PORT_MAX",
    # Defaults
    "DEFAULT_HOST",
    "DEFAULT_DATABASE",
    "DEFAULT_USER",
]
