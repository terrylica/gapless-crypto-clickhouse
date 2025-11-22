"""
ClickHouse connection and schema management for gapless-crypto-clickhouse.

Provides ClickHouseConnection class for database operations using clickhouse-driver.
Replaces QuestDB implementation (ADR-0003) for future-proofing and ecosystem maturity.

Usage:
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

    with ClickHouseConnection() as conn:
        conn.execute("SELECT 1")
"""

from .config import ClickHouseConfig
from .connection import ClickHouseConnection

__all__ = ["ClickHouseConnection", "ClickHouseConfig"]
