#!/usr/bin/env python3
"""Production Health Validation - ADR-0037

Validates production environment (ClickHouse Cloud) health.
Runs simplified connectivity and query tests.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import clickhouse_connect


def validate_production_health(release_version: str) -> dict:
    """Validate production ClickHouse Cloud environment health.

    Returns structured validation result for ClickHouse storage.
    """
    result = {
        "validation_type": "production_health",
        "release_version": release_version,
        "status": "failed",
        "error_message": "",
        "duration_ms": 0,
        "validation_context": {},
    }

    start_time = datetime.now(timezone.utc)

    # Get connection parameters from environment
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        result["error_message"] = "Missing CLICKHOUSE_HOST or CLICKHOUSE_PASSWORD environment variables"
        return result

    try:
        # Connect to ClickHouse Cloud
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
        )

        # Test 1: Basic connectivity
        ping_result = client.command("SELECT 1")
        if ping_result != 1:
            result["error_message"] = f"Unexpected ping result: {ping_result}"
            return result

        # Test 2: Check ohlcv table exists
        tables = client.command("SHOW TABLES")
        if "ohlcv" not in tables:
            result["error_message"] = "ohlcv table not found"
            return result

        # Test 3: Simple count query
        count_result = client.query("SELECT COUNT(*) FROM ohlcv LIMIT 1")
        row_count = count_result.result_rows[0][0] if count_result.result_rows else 0

        # Success
        result["status"] = "passed"
        result["validation_context"] = {
            "host": host,
            "tables_found": tables,
            "ohlcv_row_count": str(row_count),
            "connectivity": "ok",
        }

    except Exception as e:
        result["error_message"] = f"Production health check failed: {str(e)}"
        result["validation_context"] = {
            "host": host,
            "error_type": type(e).__name__,
        }

    end_time = datetime.now(timezone.utc)
    result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate Production Environment Health")
    parser.add_argument("--release-version", required=True, help="Release version (e.g., v9.0.0)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    print(f"[Production Health Validation] Checking ClickHouse Cloud for release {args.release_version}...")

    result = validate_production_health(args.release_version)

    # Write JSON result
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    # Print status
    if result["status"] == "passed":
        print(f"✅ Production health validation passed ({result['duration_ms']}ms)")
        return 0
    else:
        print(f"❌ Production health validation failed: {result['error_message']}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
