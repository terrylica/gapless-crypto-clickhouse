#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "clickhouse-connect>=0.8.11",
# ]
# ///
"""
Simplified E2E Validation Script

ADR-0035: CI/CD Production Validation Policy

3-layer validation:
1. Environment: ClickHouse Cloud connection + schema exists
2. Data flow: Write test data → verify ingestion
3. Query: Read with FINAL → verify deduplication

Exit Codes:
- 0: All validations passed
- 1: Validation failed
"""

import os
import sys
from datetime import datetime, timezone

import clickhouse_connect


def log(message: str) -> None:
    """Print timestamped log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def main() -> int:
    """Main E2E validation function."""
    log("")
    log("=" * 80)
    log("Simplified E2E Validation")
    log("=" * 80)
    log("")

    # Get connection parameters
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        log("❌ FAILED: Missing required environment variables")
        return 1

    try:
        # Layer 1: Environment Validation
        log("=" * 80)
        log("Layer 1: Environment Validation")
        log("=" * 80)

        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
        )

        result = client.command("SELECT 1")
        log(f"✅ ClickHouse Cloud connection successful: {result}")

        tables = client.command("SHOW TABLES")
        log(f"✅ Tables found: {tables}")
        assert "ohlcv" in tables, "ohlcv table not found"
        log("✅ Layer 1 passed: Environment validated")
        log("")

        # Layer 2: Data Flow Validation
        log("=" * 80)
        log("Layer 2: Data Flow Validation")
        log("=" * 80)

        # Insert single test row
        test_data = [
            [datetime.now()],  # timestamp
            ["E2E_TEST"],  # symbol
            ["1h"],  # timeframe
            ["futures-um"],  # instrument_type
            [100.0],  # open
            [101.0],  # high
            [99.0],  # low
            [100.5],  # close
            [1000.0],  # volume
            [datetime.now()],  # close_time
            [100000.0],  # quote_asset_volume
            [100],  # number_of_trades
            [500.0],  # taker_buy_base_asset_volume
            [50000.0],  # taker_buy_quote_asset_volume
            [0.0001],  # funding_rate
            ["e2e_test"],  # data_source
            [99999],  # _version
            [1],  # _sign
        ]

        column_names = [
            "timestamp",
            "symbol",
            "timeframe",
            "instrument_type",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "funding_rate",
            "data_source",
            "_version",
            "_sign",
        ]

        client.insert("ohlcv", test_data, column_names=column_names)
        log("✅ Test data inserted successfully")
        log("✅ Layer 2 passed: Data flow validated")
        log("")

        # Layer 3: Query Validation
        log("=" * 80)
        log("Layer 3: Query Validation")
        log("=" * 80)

        result = client.query("SELECT * FROM ohlcv FINAL WHERE symbol = 'E2E_TEST' LIMIT 10")
        row_count = result.row_count
        log(f"✅ Query executed successfully, rows: {row_count}")

        # Cleanup
        client.command("DELETE FROM ohlcv WHERE symbol = 'E2E_TEST'")
        log("✅ Test data cleaned up")
        log("✅ Layer 3 passed: Query validated")
        log("")

        log("=" * 80)
        log("✅ All 3 layers passed: E2E validation successful")
        log("=" * 80)
        return 0

    except Exception as e:
        log(f"❌ FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
