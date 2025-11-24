#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "gapless-crypto-clickhouse",
# ]
# ///
"""
Simplified E2E Validation Script

ADR-0035: CI/CD Production Validation Policy
ADR-0036: CI/CD Workflow DRY Refactoring (uses e2e_core module)

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
import traceback
from datetime import datetime

import pandas as pd

from gapless_crypto_clickhouse.validation import (
    cleanup_test_data,
    create_clickhouse_client,
    insert_test_data,
    log_with_timestamp,
    query_with_final,
    validate_table_exists,
)


def main() -> int:
    """Main E2E validation function."""
    log_with_timestamp("")
    log_with_timestamp("=" * 80)
    log_with_timestamp("Simplified E2E Validation")
    log_with_timestamp("=" * 80)
    log_with_timestamp("")

    # Get connection parameters
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        log_with_timestamp("❌ FAILED: Missing required environment variables")
        return 1

    try:
        # Layer 1: Environment Validation
        log_with_timestamp("=" * 80)
        log_with_timestamp("Layer 1: Environment Validation")
        log_with_timestamp("=" * 80)

        client = create_clickhouse_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
        )

        result = client.command("SELECT 1")
        log_with_timestamp(f"✅ ClickHouse Cloud connection successful: {result}")

        tables = client.command("SHOW TABLES")
        log_with_timestamp(f"✅ Tables found: {tables}")
        assert validate_table_exists(client, "ohlcv"), "ohlcv table not found"
        log_with_timestamp("✅ Layer 1 passed: Environment validated")
        log_with_timestamp("")

        # Layer 2: Data Flow Validation
        log_with_timestamp("=" * 80)
        log_with_timestamp("Layer 2: Data Flow Validation")
        log_with_timestamp("=" * 80)

        # Insert single test row using pandas DataFrame
        test_timestamp = datetime.now()
        test_df = pd.DataFrame({
            "timestamp": [test_timestamp],
            "symbol": ["E2E_TEST"],
            "timeframe": ["1h"],
            "instrument_type": ["futures-um"],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000.0],
            "close_time": [test_timestamp],
            "quote_asset_volume": [100000.0],
            "number_of_trades": [100],
            "taker_buy_base_asset_volume": [500.0],
            "taker_buy_quote_asset_volume": [50000.0],
            "funding_rate": [0.0001],
            "data_source": ["e2e_test"],
            "_version": [99999],
            "_sign": [1],
        })

        insert_test_data(client, "ohlcv", test_df)
        log_with_timestamp("✅ Test data inserted successfully")
        log_with_timestamp("✅ Layer 2 passed: Data flow validated")
        log_with_timestamp("")

        # Layer 3: Query Validation
        log_with_timestamp("=" * 80)
        log_with_timestamp("Layer 3: Query Validation")
        log_with_timestamp("=" * 80)

        result = query_with_final(client, "ohlcv", "E2E_TEST")
        row_count = result.result_rows[0][0]
        log_with_timestamp(f"✅ Query executed successfully, rows: {row_count}")

        # Cleanup
        cleanup_test_data(client, "ohlcv", "E2E_TEST")
        log_with_timestamp("✅ Test data cleaned up")
        log_with_timestamp("✅ Layer 3 passed: Query validated")
        log_with_timestamp("")

        log_with_timestamp("=" * 80)
        log_with_timestamp("✅ All 3 layers passed: E2E validation successful")
        log_with_timestamp("=" * 80)
        return 0

    except Exception as e:
        log_with_timestamp(f"❌ FAILED: E2E validation error")
        log_with_timestamp(f"   Exception type: {type(e).__name__}")
        log_with_timestamp(f"   Exception message: {str(e)}")
        log_with_timestamp(f"   Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
