"""
ClickHouse Cloud connection and schema management for gapless-crypto-clickhouse.

**ClickHouse Cloud** is the single source of truth (ADR-0043: Cloud-only policy).
CLICKHOUSE_HOST environment variable is REQUIRED - no localhost fallback.

Usage:
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    # Via Doppler (recommended)
    # doppler run --project aws-credentials --config prd -- python script.py
    with ClickHouseConnection() as conn:
        conn.execute("SELECT 1")
"""

from .config import ClickHouseCloudRequiredError, ClickHouseConfig
from .connection import ClickHouseConnection

__all__ = ["ClickHouseConnection", "ClickHouseConfig", "ClickHouseCloudRequiredError"]
