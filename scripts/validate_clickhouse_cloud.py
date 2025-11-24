#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "clickhouse-connect>=0.8.11",
#     "pandas>=2.2.0",
#     "pyarrow>=18.1.0",
# ]
# ///
"""
ClickHouse Cloud Production Validation Script

ADR-0035: CI/CD Production Validation Policy

Validates ClickHouse Cloud AWS production environment:
1. Schema validation (dry-run mode)
2. ORDER BY verification (symbol-first from ADR-0034)
3. Write/read round-trip (deduplication correctness)
4. Cleanup test data

Environment Variables (via Doppler):
- CLICKHOUSE_HOST
- CLICKHOUSE_PORT (default: 8443)
- CLICKHOUSE_USER (default: default)
- CLICKHOUSE_PASSWORD

Exit Codes:
- 0: All validations passed
- 1: Validation failed
"""

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import clickhouse_connect
import pandas as pd


def log(message: str) -> None:
    """Print timestamped log message."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def create_log_directory() -> Path:
    """Create logs directory if it doesn't exist."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    return log_dir


def validate_schema(client: clickhouse_connect.driver.client.Client) -> bool:
    """Validate ClickHouse Cloud schema matches expected configuration."""
    log("=" * 80)
    log("STEP 1: Schema Validation")
    log("=" * 80)

    # Check table exists
    tables = client.command("SHOW TABLES")
    if "ohlcv" not in tables:
        log("❌ FAILED: ohlcv table not found")
        return False
    log("✅ Table 'ohlcv' exists")

    # Get CREATE TABLE statement
    create_table_sql = client.command("SHOW CREATE TABLE ohlcv")

    # Verify ORDER BY (ADR-0034: symbol-first)
    expected_order_by = "(symbol, timeframe, toStartOfHour(timestamp), timestamp)"
    if expected_order_by in create_table_sql:
        log(f"✅ ORDER BY verified: {expected_order_by}")
    else:
        log(f"❌ FAILED: ORDER BY mismatch")
        log(f"   Expected: {expected_order_by}")
        log(f"   Actual: {create_table_sql}")
        return False

    # Verify table engine (ReplacingMergeTree or SharedReplacingMergeTree for Cloud)
    if "ReplacingMergeTree(_version)" in create_table_sql:
        log("✅ Table engine verified: ReplacingMergeTree(_version)")
    elif "SharedReplacingMergeTree(_version)" in create_table_sql:
        log("✅ Table engine verified: SharedReplacingMergeTree(_version) [ClickHouse Cloud]")
    else:
        log("❌ FAILED: Table engine mismatch")
        log(f"   Expected: ReplacingMergeTree(_version) or SharedReplacingMergeTree(_version)")
        log(f"   Actual: {create_table_sql}")
        return False

    # Verify partition key
    if "PARTITION BY toYYYYMMDD(timestamp)" in create_table_sql:
        log("✅ Partition key verified: toYYYYMMDD(timestamp)")
    else:
        log("❌ FAILED: Partition key mismatch")
        return False

    log("✅ Schema validation passed")
    return True


def calculate_version_hash(row: pd.Series) -> int:
    """Calculate deterministic version hash for deduplication."""
    content = (
        f"{row['timestamp']}|{row['symbol']}|{row['timeframe']}|"
        f"{row['instrument_type']}|{row['open']}|{row['high']}|{row['low']}|"
        f"{row['close']}|{row['volume']}|{row['close_time']}|"
        f"{row['quote_asset_volume']}|{row['number_of_trades']}|"
        f"{row['taker_buy_base_asset_volume']}|{row['taker_buy_quote_asset_volume']}|"
        f"{row['funding_rate']}|{row['data_source']}"
    )
    hash_bytes = hashlib.sha256(content.encode("utf-8")).digest()
    return int.from_bytes(hash_bytes[:8], byteorder="big")


def validate_write_read_roundtrip(
    client: clickhouse_connect.driver.client.Client,
) -> bool:
    """Validate write/read round-trip with deduplication."""
    log("")
    log("=" * 80)
    log("STEP 2: Write/Read Round-Trip Validation")
    log("=" * 80)

    # Generate test data (100 BTCUSDT 1h bars)
    test_symbol = "VALIDATION_TEST_BTCUSDT"
    test_timeframe = "1h"
    num_rows = 100

    log(f"Generating {num_rows} test rows ({test_symbol} {test_timeframe})...")

    base_timestamp = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    timestamps = [base_timestamp.replace(hour=i % 24) for i in range(num_rows)]

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": [test_symbol] * num_rows,
            "timeframe": [test_timeframe] * num_rows,
            "instrument_type": ["futures-um"] * num_rows,
            "open": [50000.0 + i for i in range(num_rows)],
            "high": [50001.0 + i for i in range(num_rows)],
            "low": [49999.0 + i for i in range(num_rows)],
            "close": [50000.5 + i for i in range(num_rows)],
            "volume": [100.0 + i for i in range(num_rows)],
            "close_time": [ts.replace(minute=59, second=59) for ts in timestamps],
            "quote_asset_volume": [5000000.0 + i * 1000 for i in range(num_rows)],
            "number_of_trades": [1000 + i for i in range(num_rows)],
            "taker_buy_base_asset_volume": [50.0 + i * 0.5 for i in range(num_rows)],
            "taker_buy_quote_asset_volume": [
                2500000.0 + i * 500 for i in range(num_rows)
            ],
            "funding_rate": [0.0001] * num_rows,
            "data_source": ["validation_test"] * num_rows,
        }
    )

    # Calculate deterministic version hashes
    df["_version"] = df.apply(calculate_version_hash, axis=1)
    df["_sign"] = 1

    log(f"✅ Generated {len(df)} test rows")
    log(f"   Timestamp range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    log(f"   Version hashes: {df['_version'].nunique()} unique")

    # Write test data
    log("Writing test data to ClickHouse Cloud...")
    try:
        client.insert("ohlcv", df.to_dict("list"))
        log(f"✅ Inserted {len(df)} rows")
    except Exception as e:
        log(f"❌ FAILED: Insert failed: {e}")
        return False

    # Read test data WITHOUT FINAL (may include duplicates)
    log("Reading test data WITHOUT FINAL...")
    try:
        result_no_final = client.query(
            f"SELECT COUNT(*) as count FROM ohlcv WHERE symbol = '{test_symbol}'"
        )
        count_no_final = result_no_final.result_rows[0][0]
        log(f"✅ Row count WITHOUT FINAL: {count_no_final}")
    except Exception as e:
        log(f"❌ FAILED: Query without FINAL failed: {e}")
        return False

    # Read test data WITH FINAL (deduplicated)
    log("Reading test data WITH FINAL (deduplicated)...")
    try:
        result_with_final = client.query(
            f"SELECT COUNT(*) as count FROM ohlcv FINAL WHERE symbol = '{test_symbol}'"
        )
        count_with_final = result_with_final.result_rows[0][0]
        log(f"✅ Row count WITH FINAL: {count_with_final}")
    except Exception as e:
        log(f"❌ FAILED: Query with FINAL failed: {e}")
        return False

    # Verify deduplication correctness
    if count_with_final == num_rows:
        log(
            f"✅ Deduplication verified: {count_with_final} rows (expected {num_rows})"
        )
    else:
        log(f"❌ FAILED: Deduplication mismatch")
        log(f"   Expected: {num_rows} rows")
        log(f"   Actual: {count_with_final} rows")
        return False

    # Insert duplicates to test deduplication
    log("Inserting duplicate rows to test deduplication...")
    try:
        client.insert("ohlcv", df.to_dict("list"))
        log(f"✅ Inserted {len(df)} duplicate rows")
    except Exception as e:
        log(f"❌ FAILED: Duplicate insert failed: {e}")
        return False

    # Read again with FINAL (should still be 100 rows after merge)
    log("Verifying deduplication after duplicate insert...")
    try:
        result_after_dup = client.query(
            f"SELECT COUNT(*) as count FROM ohlcv FINAL WHERE symbol = '{test_symbol}'"
        )
        count_after_dup = result_after_dup.result_rows[0][0]
        log(f"✅ Row count after duplicate insert (WITH FINAL): {count_after_dup}")
    except Exception as e:
        log(f"❌ FAILED: Query after duplicate insert failed: {e}")
        return False

    if count_after_dup == num_rows:
        log(
            f"✅ Deduplication after re-insert verified: {count_after_dup} rows (expected {num_rows})"
        )
    else:
        log(f"❌ FAILED: Deduplication after re-insert mismatch")
        log(f"   Expected: {num_rows} rows")
        log(f"   Actual: {count_after_dup} rows")
        return False

    log("✅ Write/read round-trip validation passed")
    return True


def cleanup_test_data(client: clickhouse_connect.driver.client.Client) -> bool:
    """Cleanup test data from validation."""
    log("")
    log("=" * 80)
    log("STEP 3: Cleanup Test Data")
    log("=" * 80)

    test_symbol = "VALIDATION_TEST_BTCUSDT"

    log(f"Deleting test data (symbol: {test_symbol})...")
    try:
        client.command(f"DELETE FROM ohlcv WHERE symbol = '{test_symbol}'")
        log("✅ Test data deleted")
    except Exception as e:
        log(f"⚠️  WARNING: Cleanup failed (non-fatal): {e}")
        return True  # Non-fatal error

    # Verify cleanup
    try:
        result = client.query(
            f"SELECT COUNT(*) as count FROM ohlcv FINAL WHERE symbol = '{test_symbol}'"
        )
        remaining_rows = result.result_rows[0][0]
        if remaining_rows == 0:
            log("✅ Cleanup verified: 0 rows remaining")
        else:
            log(
                f"⚠️  WARNING: {remaining_rows} rows still present (may require OPTIMIZE TABLE)"
            )
    except Exception as e:
        log(f"⚠️  WARNING: Cleanup verification failed: {e}")

    log("✅ Cleanup completed")
    return True


def main() -> int:
    """Main validation function."""
    log("")
    log("=" * 80)
    log("ClickHouse Cloud Production Validation")
    log("ADR-0035: CI/CD Production Validation Policy")
    log("=" * 80)
    log("")

    # Create logs directory
    create_log_directory()

    # Get ClickHouse Cloud connection parameters from environment
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        log("❌ FAILED: Missing required environment variables")
        log("   Required: CLICKHOUSE_HOST, CLICKHOUSE_PASSWORD")
        log("   Optional: CLICKHOUSE_PORT (default: 8443), CLICKHOUSE_USER (default: default)")
        return 1

    log(f"Connecting to ClickHouse Cloud...")
    log(f"  Host: {host}")
    log(f"  Port: {port}")
    log(f"  User: {username}")

    # Connect to ClickHouse Cloud
    try:
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
            settings={"do_not_merge_across_partitions_select_final": 1},
        )
        log("✅ Connected to ClickHouse Cloud")
    except Exception as e:
        log(f"❌ FAILED: Connection failed: {e}")
        return 1

    # Get ClickHouse version
    try:
        version = client.command("SELECT version()")
        log(f"  Version: {version}")
        log("")
    except Exception as e:
        log(f"⚠️  WARNING: Could not retrieve version: {e}")

    # Run validations
    validation_results = []

    # 1. Schema validation
    schema_valid = validate_schema(client)
    validation_results.append(("Schema Validation", schema_valid))

    # 2. Write/read round-trip validation
    if schema_valid:
        roundtrip_valid = validate_write_read_roundtrip(client)
        validation_results.append(("Write/Read Round-Trip", roundtrip_valid))
    else:
        log("⚠️  SKIPPING: Write/read round-trip (schema validation failed)")
        validation_results.append(("Write/Read Round-Trip", False))
        roundtrip_valid = False

    # 3. Cleanup test data
    if roundtrip_valid:
        cleanup_success = cleanup_test_data(client)
        validation_results.append(("Cleanup", cleanup_success))
    else:
        log("⚠️  SKIPPING: Cleanup (write/read validation failed)")

    # Summary
    log("")
    log("=" * 80)
    log("VALIDATION SUMMARY")
    log("=" * 80)

    all_passed = all(result for _, result in validation_results)

    for validation_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        log(f"{status}: {validation_name}")

    log("")
    if all_passed:
        log("=" * 80)
        log("✅ ALL VALIDATIONS PASSED")
        log("=" * 80)
        return 0
    else:
        log("=" * 80)
        log("❌ VALIDATION FAILED")
        log("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
