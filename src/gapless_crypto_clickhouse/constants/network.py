"""Network configuration constants for HTTP clients and connections (ADR-0046).

Single source of truth for timeouts, concurrency settings, HTTP status codes,
and retry configurations used by REST clients and HTTP downloaders.

Usage:
    from gapless_crypto_clickhouse.constants.network import (
        TIMEOUT_API,
        HTTP_OK,
        HTTP_RATE_LIMITED,
        RETRY_MAX_ATTEMPTS,
    )
"""

from typing import Final, Tuple

# =============================================================================
# TIMEOUTS (seconds)
# =============================================================================

TIMEOUT_CONNECT: Final[float] = 10.0
"""TCP connection establishment timeout."""

TIMEOUT_READ: Final[float] = 60.0
"""Default read timeout for HTTP responses."""

TIMEOUT_WRITE: Final[float] = 10.0
"""Write timeout for request body."""

TIMEOUT_POOL: Final[float] = 5.0
"""Timeout waiting for connection from pool."""

TIMEOUT_API: Final[float] = 30.0
"""Default timeout for REST API requests."""

TIMEOUT_CDN: Final[float] = 60.0
"""Default timeout for CDN downloads."""

# =============================================================================
# CONNECTION POOL
# =============================================================================

MAX_CONCURRENT_DOWNLOADS: Final[int] = 13
"""Maximum concurrent download workers (CDN has no rate limiting)."""

CONNECTION_POOL_SIZE: Final[int] = 20
"""HTTP connection pool size."""

CONNECTION_POOL_HEADROOM: Final[int] = 10
"""Additional connections beyond pool size for max_connections."""

KEEPALIVE_EXPIRY: Final[float] = 30.0
"""HTTP keepalive connection expiry time in seconds."""

# =============================================================================
# HTTP STATUS CODES
# =============================================================================

HTTP_OK: Final[int] = 200
"""Successful HTTP response."""

HTTP_NOT_MODIFIED: Final[int] = 304
"""Resource not modified (for ETag caching)."""

HTTP_IP_BANNED: Final[int] = 418
"""Binance IP ban status code (I'm a teapot)."""

HTTP_RATE_LIMITED: Final[int] = 429
"""Too many requests - rate limited."""

HTTP_RATE_LIMIT_CODES: Final[Tuple[int, ...]] = (HTTP_IP_BANNED, HTTP_RATE_LIMITED)
"""HTTP status codes indicating rate limiting."""

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

RETRY_MAX_ATTEMPTS: Final[int] = 3
"""Maximum number of retry attempts for transient failures."""

RETRY_BASE_DELAY: Final[float] = 1.0
"""Base delay between retries in seconds."""

RETRY_MULTIPLIER: Final[float] = 2.0
"""Multiplier for exponential backoff."""

RETRY_MAX_DELAY: Final[int] = 3
"""Maximum delay between retries in seconds."""

DEFAULT_RETRY_AFTER: Final[int] = 60
"""Default retry-after for rate limits when not specified."""

# =============================================================================
# SELF-VALIDATING ASSERTIONS
# =============================================================================

# Verify timeout values are positive
assert TIMEOUT_CONNECT > 0, f"TIMEOUT_CONNECT must be positive: {TIMEOUT_CONNECT}"
assert TIMEOUT_READ > 0, f"TIMEOUT_READ must be positive: {TIMEOUT_READ}"
assert TIMEOUT_API > 0, f"TIMEOUT_API must be positive: {TIMEOUT_API}"

# Verify HTTP status codes are valid (100-599)
assert 100 <= HTTP_OK <= 599, f"HTTP_OK must be valid status: {HTTP_OK}"
assert 100 <= HTTP_NOT_MODIFIED <= 599, f"HTTP_NOT_MODIFIED must be valid: {HTTP_NOT_MODIFIED}"
assert all(100 <= code <= 599 for code in HTTP_RATE_LIMIT_CODES), "Rate limit codes must be valid"

# Verify retry configuration is sane
assert RETRY_MAX_ATTEMPTS >= 1, f"RETRY_MAX_ATTEMPTS must be >= 1: {RETRY_MAX_ATTEMPTS}"
assert RETRY_BASE_DELAY >= 0, f"RETRY_BASE_DELAY must be >= 0: {RETRY_BASE_DELAY}"

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Timeouts
    "TIMEOUT_CONNECT",
    "TIMEOUT_READ",
    "TIMEOUT_WRITE",
    "TIMEOUT_POOL",
    "TIMEOUT_API",
    "TIMEOUT_CDN",
    # Connection pool
    "MAX_CONCURRENT_DOWNLOADS",
    "CONNECTION_POOL_SIZE",
    "CONNECTION_POOL_HEADROOM",
    "KEEPALIVE_EXPIRY",
    # HTTP status codes
    "HTTP_OK",
    "HTTP_NOT_MODIFIED",
    "HTTP_IP_BANNED",
    "HTTP_RATE_LIMITED",
    "HTTP_RATE_LIMIT_CODES",
    # Retry configuration
    "RETRY_MAX_ATTEMPTS",
    "RETRY_BASE_DELAY",
    "RETRY_MULTIPLIER",
    "RETRY_MAX_DELAY",
    "DEFAULT_RETRY_AFTER",
]
