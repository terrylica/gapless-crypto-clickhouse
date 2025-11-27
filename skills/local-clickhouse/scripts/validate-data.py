#!/usr/bin/env python3
"""ADR-0045: Validate local ClickHouse data and output JSON evidence.

Queries local ClickHouse for data integrity validation:
- Row counts by symbol/timeframe
- OHLC constraint validation
- Schema compliance

Usage:
    python validate-data.py [output_dir]
    # Default output: tests/screenshots/validation-{timestamp}.json

Exit codes:
    0: All validations passed
    1: ClickHouse not available
    2: Validation failed
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Semantic constants (ADR-0045)
PORT_LOCAL_HTTP = 8123
DEFAULT_SCREENSHOTS_DIR = "tests/screenshots"
VALIDATION_JSON_PATTERN = "validation-{timestamp}.json"


def check_clickhouse_available() -> bool:
    """Check if local ClickHouse is running."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", PORT_LOCAL_HTTP))
        sock.close()
        return result == 0
    except Exception:
        return False


def main() -> int:
    """Run validation and output JSON evidence."""
    # Set local mode
    os.environ["GCCH_MODE"] = "local"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["CLICKHOUSE_HTTP_PORT"] = str(PORT_LOCAL_HTTP)

    # Determine output directory
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_SCREENSHOTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check ClickHouse availability
    if not check_clickhouse_available():
        print(f"ERROR: ClickHouse not running on localhost:{PORT_LOCAL_HTTP}", file=sys.stderr)
        return 1

    try:
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "clickhouse_version": None,
            "database_check": None,
            "table_check": None,
            "row_counts": [],
            "ohlc_validation": None,
            "schema_validation": None,
            "overall_status": "pending",
            "errors": [],
        }

        # 1. Version check
        try:
            result = client.query("SELECT version()")
            validation_results["clickhouse_version"] = result.result_rows[0][0]
            print(f"ClickHouse version: {validation_results['clickhouse_version']}")
        except Exception as e:
            validation_results["errors"].append(f"Version check failed: {e}")

        # 2. Database check
        try:
            result = client.query("SELECT name FROM system.databases WHERE name = 'default'")
            validation_results["database_check"] = len(result.result_rows) > 0
            print(f"Database 'default' exists: {validation_results['database_check']}")
        except Exception as e:
            validation_results["errors"].append(f"Database check failed: {e}")

        # 3. Table check
        try:
            result = client.query("SELECT name FROM system.tables WHERE database = 'default' AND name = 'ohlcv'")
            validation_results["table_check"] = len(result.result_rows) > 0
            print(f"Table 'ohlcv' exists: {validation_results['table_check']}")
        except Exception as e:
            validation_results["errors"].append(f"Table check failed: {e}")

        # 4. Row counts by symbol/timeframe
        if validation_results["table_check"]:
            try:
                result = client.query("""
                    SELECT symbol, timeframe, count() as rows
                    FROM ohlcv FINAL
                    GROUP BY symbol, timeframe
                    ORDER BY rows DESC
                    LIMIT 20
                """)
                validation_results["row_counts"] = [
                    {"symbol": row[0], "timeframe": row[1], "rows": row[2]}
                    for row in result.result_rows
                ]
                total_rows = sum(r["rows"] for r in validation_results["row_counts"])
                print(f"Total rows: {total_rows} across {len(validation_results['row_counts'])} symbol/timeframe combinations")
            except Exception as e:
                validation_results["errors"].append(f"Row count failed: {e}")

            # 5. OHLC constraint validation
            try:
                result = client.query("""
                    SELECT
                        countIf(high < open OR high < close OR high < low) as high_violations,
                        countIf(low > open OR low > close OR low > high) as low_violations,
                        countIf(volume < 0) as volume_violations,
                        count() as total_rows
                    FROM ohlcv FINAL
                """)
                row = result.result_rows[0]
                validation_results["ohlc_validation"] = {
                    "high_violations": row[0],
                    "low_violations": row[1],
                    "volume_violations": row[2],
                    "total_rows": row[3],
                    "valid": row[0] == 0 and row[1] == 0 and row[2] == 0,
                }
                print(f"OHLC validation: {'PASSED' if validation_results['ohlc_validation']['valid'] else 'FAILED'}")
            except Exception as e:
                validation_results["errors"].append(f"OHLC validation failed: {e}")

            # 6. Schema validation (check expected columns exist)
            try:
                result = client.query("""
                    SELECT name, type FROM system.columns
                    WHERE database = 'default' AND table = 'ohlcv'
                    ORDER BY position
                """)
                columns = {row[0]: row[1] for row in result.result_rows}
                expected_columns = ["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]
                missing = [col for col in expected_columns if col not in columns]
                validation_results["schema_validation"] = {
                    "columns_found": list(columns.keys()),
                    "expected_columns": expected_columns,
                    "missing_columns": missing,
                    "valid": len(missing) == 0,
                }
                print(f"Schema validation: {'PASSED' if validation_results['schema_validation']['valid'] else 'FAILED'}")
            except Exception as e:
                validation_results["errors"].append(f"Schema validation failed: {e}")

        # Determine overall status
        if validation_results["errors"]:
            validation_results["overall_status"] = "failed"
        elif (
            validation_results["table_check"]
            and validation_results.get("ohlc_validation", {}).get("valid", False)
            and validation_results.get("schema_validation", {}).get("valid", False)
        ):
            validation_results["overall_status"] = "passed"
        else:
            validation_results["overall_status"] = "incomplete"

        # Write JSON output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / VALIDATION_JSON_PATTERN.format(timestamp=timestamp)
        output_path.write_text(json.dumps(validation_results, indent=2, default=str))

        print(f"\nValidation results saved: {output_path}")
        print(f"Overall status: {validation_results['overall_status'].upper()}")

        return 0 if validation_results["overall_status"] == "passed" else 2

    except ImportError as e:
        print(f"ERROR: Required package not installed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: Validation failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
