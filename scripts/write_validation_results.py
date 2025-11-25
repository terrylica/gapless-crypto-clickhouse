#!/usr/bin/env python3
"""Write Validation Results to ClickHouse - ADR-0037

Reads validation JSON files and inserts them into monitoring.validation_results table.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import clickhouse_connect

# Valid status values for monitoring.validation_results schema (Enum8)
VALID_STATUSES = {"passed", "failed", "warning"}


def write_validation_results(results_dir: str) -> dict:
    """Write validation results to ClickHouse monitoring.validation_results table.

    Returns summary of write operations.
    """
    summary = {
        "total_files": 0,
        "successful_inserts": 0,
        "failed_inserts": 0,
        "errors": [],
    }

    # Get connection parameters from environment
    host = os.getenv("CLICKHOUSE_HOST")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    username = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD")

    if not host or not password:
        summary["errors"].append("Missing CLICKHOUSE_HOST or CLICKHOUSE_PASSWORD")
        return summary

    try:
        # Connect to ClickHouse Cloud
        client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
        )

        # Find all JSON result files
        results_path = Path(results_dir)
        json_files = list(results_path.glob("*-result.json"))

        summary["total_files"] = len(json_files)

        if len(json_files) == 0:
            summary["errors"].append(f"No validation result files found in {results_dir}")
            return summary

        # Column names for explicit insert (excluding auto-generated validation_id)
        column_names = [
            "event_time",
            "event_date",
            "validation_type",
            "release_version",
            "git_commit",
            "symbol",
            "timeframe",
            "status",
            "error_message",
            "duration_ms",
            "validation_context",
            "environment",
        ]

        # Insert each validation result
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    data = json.load(f)

                # Validate status enum
                status = data.get("status", "failed")
                if status not in VALID_STATUSES:
                    raise ValueError(
                        f"Invalid status '{status}' in {json_file.name}. "
                        f"Must be one of {VALID_STATUSES}"
                    )

                # Prepare row for insertion (list format, matching column_names order)
                event_time = datetime.now(timezone.utc)
                row = [
                    event_time,  # event_time
                    event_time.date(),  # event_date
                    data.get("validation_type", "unknown"),  # validation_type
                    data.get("release_version", ""),  # release_version
                    data.get("git_commit", ""),  # git_commit
                    "",  # symbol (empty for release validations)
                    "",  # timeframe (empty for release validations)
                    status,  # status
                    data.get("error_message", ""),  # error_message
                    data.get("duration_ms", 0),  # duration_ms
                    data.get("validation_context", {}),  # validation_context
                    "production",  # environment
                ]

                # Insert row with explicit column names
                client.insert("monitoring.validation_results", [row], column_names=column_names)
                summary["successful_inserts"] += 1

            except Exception as e:
                summary["failed_inserts"] += 1
                summary["errors"].append(f"Failed to insert {json_file.name}: {str(e)}")

    except Exception as e:
        summary["errors"].append(f"ClickHouse connection failed: {str(e)}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Write Validation Results to ClickHouse")
    parser.add_argument("--results-dir", required=True, help="Directory containing validation JSON files")
    args = parser.parse_args()

    print(f"[ClickHouse Write] Processing validation results from {args.results_dir}...")

    summary = write_validation_results(args.results_dir)

    # Print summary
    print(f"Total files: {summary['total_files']}")
    print(f"Successful inserts: {summary['successful_inserts']}")
    print(f"Failed inserts: {summary['failed_inserts']}")

    if summary["errors"]:
        print("Errors:")
        for error in summary["errors"]:
            print(f"  - {error}")

    # Return non-zero exit code if any errors
    if summary["failed_inserts"] > 0 or summary["errors"]:
        return 1

    print("✅ All validation results written to ClickHouse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
