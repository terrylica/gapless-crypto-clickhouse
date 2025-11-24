#!/usr/bin/env python3
"""
ClickHouse Monitoring Schema Deployment

ADR-0037: Release Validation Observability Flow

Deploys monitoring database and validation_results table for release validation metrics.

Requirements:
- gapless-crypto-clickhouse package must be installed (uv pip install --system -e .)
- ClickHouse Cloud credentials in environment (via Doppler or env vars)

Exit Codes:
- 0: Schema deployed successfully
- 1: Deployment failed
"""

import os
import sys
from datetime import datetime, timezone

import clickhouse_connect


def log_with_timestamp(message: str) -> None:
    """Print timestamped log message with UTC timezone."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def main() -> int:
    """Deploy ClickHouse monitoring schema."""
    log_with_timestamp("")
    log_with_timestamp("=" * 80)
    log_with_timestamp("ClickHouse Monitoring Schema Deployment")
    log_with_timestamp("ADR-0037: Release Validation Observability Flow")
    log_with_timestamp("=" * 80)
    log_with_timestamp("")

    # Get ClickHouse Cloud connection parameters from environment
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        log_with_timestamp("❌ FAILED: Missing required environment variables")
        log_with_timestamp("   Required: CLICKHOUSE_HOST, CLICKHOUSE_PASSWORD")
        log_with_timestamp("   Optional: CLICKHOUSE_PORT (default: 8443), CLICKHOUSE_USER (default: default)")
        return 1

    log_with_timestamp(f"Connecting to ClickHouse Cloud...")
    log_with_timestamp(f"  Host: {host}")
    log_with_timestamp(f"  Port: {port}")
    log_with_timestamp(f"  User: {username}")

    # Connect to ClickHouse Cloud
    try:
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
        )
        log_with_timestamp("✅ Connected to ClickHouse Cloud")
    except Exception as e:
        log_with_timestamp(f"❌ FAILED: Connection failed: {e}")
        return 1

    # Get ClickHouse version
    try:
        version = client.command("SELECT version()")
        log_with_timestamp(f"  Version: {version}")
        log_with_timestamp("")
    except Exception as e:
        log_with_timestamp(f"⚠️  WARNING: Could not retrieve version: {e}")

    # Create monitoring database
    log_with_timestamp("=" * 80)
    log_with_timestamp("Creating monitoring database...")
    log_with_timestamp("=" * 80)

    try:
        client.command("CREATE DATABASE IF NOT EXISTS monitoring")
        log_with_timestamp("✅ Database 'monitoring' created (or already exists)")
    except Exception as e:
        log_with_timestamp(f"❌ FAILED: Database creation failed: {e}")
        return 1

    # Create validation_results table
    log_with_timestamp("")
    log_with_timestamp("=" * 80)
    log_with_timestamp("Creating validation_results table...")
    log_with_timestamp("=" * 80)

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS monitoring.validation_results (
        event_time DateTime DEFAULT now(),
        event_date Date DEFAULT toDate(now()),

        validation_id UUID DEFAULT generateUUIDv4(),
        validation_type LowCardinality(String),
        release_version String,
        git_commit String,

        symbol String DEFAULT '',
        timeframe String DEFAULT '',
        status Enum8('passed' = 1, 'failed' = 2, 'warning' = 3),

        error_message String DEFAULT '',
        duration_ms UInt32 DEFAULT 0,
        validation_context Map(String, String),

        environment LowCardinality(String) DEFAULT 'production'
    )
    ENGINE = MergeTree()
    ORDER BY (release_version, validation_type, event_time)
    PARTITION BY toStartOfDay(event_date)
    """

    try:
        client.command(create_table_sql)
        log_with_timestamp("✅ Table 'validation_results' created (or already exists)")
    except Exception as e:
        log_with_timestamp(f"❌ FAILED: Table creation failed: {e}")
        return 1

    # Verify schema
    log_with_timestamp("")
    log_with_timestamp("=" * 80)
    log_with_timestamp("Verifying schema...")
    log_with_timestamp("=" * 80)

    try:
        create_table_verify = client.command("SHOW CREATE TABLE monitoring.validation_results")
        log_with_timestamp("✅ Schema verification successful")
        log_with_timestamp("")
        log_with_timestamp("CREATE TABLE statement:")
        log_with_timestamp(create_table_verify)
    except Exception as e:
        log_with_timestamp(f"❌ FAILED: Schema verification failed: {e}")
        return 1

    # Summary
    log_with_timestamp("")
    log_with_timestamp("=" * 80)
    log_with_timestamp("✅ DEPLOYMENT SUCCESSFUL")
    log_with_timestamp("=" * 80)
    log_with_timestamp("")
    log_with_timestamp("Database: monitoring")
    log_with_timestamp("Table: validation_results")
    log_with_timestamp("Engine: MergeTree")
    log_with_timestamp("ORDER BY: (release_version, validation_type, event_time)")
    log_with_timestamp("PARTITION BY: toStartOfDay(event_date)")
    log_with_timestamp("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
