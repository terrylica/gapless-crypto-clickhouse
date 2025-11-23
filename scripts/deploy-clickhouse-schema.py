#!/usr/bin/env python3
"""Deploy ClickHouse schema to ClickHouse Cloud.

This script:
1. Connects to ClickHouse Cloud using Doppler credentials
2. Deploys the schema from src/gapless_crypto_clickhouse/clickhouse/schema.sql
3. Validates the deployment
4. Provides detailed error reporting

Usage:
    # Deploy to ClickHouse Cloud (requires Doppler credentials)
    doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py

    # Dry-run mode (print SQL without executing)
    doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py --dry-run

Requirements:
    - Doppler credentials configured (aws-credentials/prd)
    - clickhouse-connect installed (uv sync)
    - Schema file exists at src/gapless_crypto_clickhouse/clickhouse/schema.sql

Exit codes:
    0 = Success (schema deployed and validated)
    1 = Error (connection failure, deployment failure, or validation failure)
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import clickhouse_connect
except ImportError:
    print("ERROR: clickhouse-connect not installed")
    print("Run: uv sync")
    sys.exit(1)


def get_credentials():
    """Get ClickHouse Cloud credentials from environment (Doppler)."""
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not all([host, password]):
        print("ERROR: Missing ClickHouse credentials in environment")
        print(f"  CLICKHOUSE_HOST: {'✅' if host else '❌ MISSING'}")
        print(f"  CLICKHOUSE_PORT: {port}")
        print(f"  CLICKHOUSE_USER: {user}")
        print(f"  CLICKHOUSE_PASSWORD: {'✅' if password else '❌ MISSING'}")
        print()
        print("Run with Doppler:")
        print("  doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py")
        sys.exit(1)

    return {
        "host": host,
        "port": port,
        "username": user,
        "password": password,
    }


def load_schema(schema_path: Path) -> str:
    """Load schema SQL from file."""
    if not schema_path.exists():
        print(f"ERROR: Schema file not found: {schema_path}")
        sys.exit(1)

    with open(schema_path) as f:
        return f.read()


def deploy_schema(client, schema_sql: str, dry_run: bool = False):
    """Deploy schema to ClickHouse Cloud.

    Args:
        client: ClickHouse client instance
        schema_sql: SQL schema to deploy
        dry_run: If True, print SQL without executing
    """
    if dry_run:
        print("=" * 80)
        print("DRY RUN MODE - SQL to be executed:")
        print("=" * 80)
        print(schema_sql)
        print("=" * 80)
        return

    print("Deploying schema to ClickHouse Cloud...")
    try:
        client.command(schema_sql)
        print("✅ Schema deployed successfully!")
    except Exception as e:
        print(f"❌ ERROR deploying schema: {type(e).__name__}: {e}")
        sys.exit(1)


def validate_deployment(client):
    """Validate schema deployment."""
    print()
    print("Validating deployment...")

    # Check if ohlcv table exists
    try:
        result = client.query("EXISTS TABLE ohlcv")
        table_exists = result.result_rows[0][0] == 1

        if not table_exists:
            print("❌ ERROR: ohlcv table does not exist after deployment")
            sys.exit(1)

        print("✅ ohlcv table exists")
    except Exception as e:
        print(f"❌ ERROR checking table existence: {e}")
        sys.exit(1)

    # Get table schema
    try:
        result = client.query("DESCRIBE TABLE ohlcv")
        print()
        print("Table schema:")
        print(f"{'Column':<30} {'Type':<30} {'Default':<15}")
        print("-" * 80)
        for row in result.result_rows:
            column_name = row[0]
            column_type = row[1]
            default_value = row[2] if len(row) > 2 else ""
            print(f"{column_name:<30} {column_type:<30} {default_value:<15}")
    except Exception as e:
        print(f"❌ ERROR getting table schema: {e}")
        sys.exit(1)

    # Verify critical columns
    try:
        result = client.query("DESCRIBE TABLE ohlcv")
        columns = {row[0]: row[1] for row in result.result_rows}

        critical_columns = {
            "timestamp": "DateTime64(6)",
            "symbol": "LowCardinality(String)",
            "timeframe": "LowCardinality(String)",
            "instrument_type": "LowCardinality(String)",
            "data_source": "LowCardinality(String)",
            "open": "Float64",
            "high": "Float64",
            "low": "Float64",
            "close": "Float64",
            "volume": "Float64",
            "close_time": "DateTime64(6)",
            "quote_asset_volume": "Float64",
            "number_of_trades": "Int64",
            "taker_buy_base_asset_volume": "Float64",
            "taker_buy_quote_asset_volume": "Float64",
            "funding_rate": "Nullable(Float64)",
            "_version": "UInt64",
            "_sign": "Int8",
        }

        print()
        print("Validating critical columns:")
        all_valid = True
        for column, expected_type in critical_columns.items():
            actual_type = columns.get(column)
            if actual_type == expected_type:
                print(f"  ✅ {column}: {actual_type}")
            else:
                print(f"  ❌ {column}: expected {expected_type}, got {actual_type}")
                all_valid = False

        if not all_valid:
            print()
            print("❌ ERROR: Schema validation failed (column type mismatch)")
            sys.exit(1)

        print()
        print("✅ All critical columns validated successfully!")

    except Exception as e:
        print(f"❌ ERROR validating columns: {e}")
        sys.exit(1)

    # Get table engine
    try:
        result = client.query("SHOW CREATE TABLE ohlcv")
        create_table_sql = result.result_rows[0][0]

        # Check for ReplacingMergeTree
        if "ReplacingMergeTree" not in create_table_sql:
            print("❌ ERROR: Table does not use ReplacingMergeTree engine")
            sys.exit(1)

        print("✅ Table engine: ReplacingMergeTree")

        # Check for _version parameter
        if "ReplacingMergeTree(_version)" not in create_table_sql:
            print("⚠️  WARNING: ReplacingMergeTree may not be using _version parameter")
        else:
            print("✅ ReplacingMergeTree uses _version for deduplication")

    except Exception as e:
        print(f"❌ ERROR validating table engine: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy ClickHouse schema to ClickHouse Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL without executing (for testing)",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=Path("src/gapless_crypto_clickhouse/clickhouse/schema.sql"),
        help="Path to schema.sql file (default: src/gapless_crypto_clickhouse/clickhouse/schema.sql)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ClickHouse Cloud Schema Deployment")
    print("=" * 80)
    print()

    # Get credentials
    creds = get_credentials()
    print(f"Host: {creds['host']}")
    print(f"Port: {creds['port']}")
    print(f"User: {creds['username']}")
    print()

    # Load schema
    schema_sql = load_schema(args.schema_path)
    print(f"Schema loaded from: {args.schema_path}")
    print(f"Schema size: {len(schema_sql)} bytes")
    print()

    # Connect to ClickHouse Cloud
    try:
        client = clickhouse_connect.get_client(
            host=creds["host"],
            port=creds["port"],
            username=creds["username"],
            password=creds["password"],
            secure=True,  # ClickHouse Cloud requires SSL
        )
        print("✅ Connected to ClickHouse Cloud")

        # Get ClickHouse version
        result = client.query("SELECT version()")
        version = result.result_rows[0][0]
        print(f"ClickHouse version: {version}")
        print()

    except Exception as e:
        print(f"❌ ERROR connecting to ClickHouse Cloud: {type(e).__name__}: {e}")
        sys.exit(1)

    # Deploy schema
    deploy_schema(client, schema_sql, dry_run=args.dry_run)

    if args.dry_run:
        print()
        print("DRY RUN COMPLETE - No changes made")
        sys.exit(0)

    # Validate deployment
    validate_deployment(client)

    print()
    print("=" * 80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Test data ingestion: python scripts/test-data-ingestion.py")
    print("  2. Verify queries: python scripts/test-clickhouse-queries.py")
    print("  3. Run integration tests: uv run pytest -m integration")


if __name__ == "__main__":
    main()
