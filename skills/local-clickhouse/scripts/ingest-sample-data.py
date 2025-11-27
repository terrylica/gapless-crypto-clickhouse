#!/usr/bin/env python3
"""ADR-0045: Ingest sample Binance data to local ClickHouse.

Uses query_ohlcv() API with auto_ingest=True for real data ingestion.
No synthetic data - uses real Binance CDN data per ADR-0038.

Usage:
    python ingest-sample-data.py
    # or via uv:
    uv run python skills/local-clickhouse/scripts/ingest-sample-data.py

Exit codes:
    0: Success
    1: ClickHouse not available
    2: Ingestion failed
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

# Semantic constants (ADR-0045)
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_TIMEFRAME = "1h"
DEFAULT_START_DATE = "2024-01-01"
DEFAULT_END_DATE = "2024-01-07"  # 7 days = 168 rows (reasonable sample)
PORT_LOCAL_HTTP = 8123


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
    """Ingest sample data to local ClickHouse."""
    # Set local mode
    os.environ["GCCH_MODE"] = "local"
    os.environ["CLICKHOUSE_HOST"] = "localhost"
    os.environ["CLICKHOUSE_HTTP_PORT"] = str(PORT_LOCAL_HTTP)

    # Check ClickHouse availability
    if not check_clickhouse_available():
        print(f"ERROR: ClickHouse not running on localhost:{PORT_LOCAL_HTTP}", file=sys.stderr)
        print("Run: skills/local-clickhouse/scripts/start-clickhouse.sh", file=sys.stderr)
        return 1

    try:
        # Import after setting environment
        from gapless_crypto_clickhouse import query_ohlcv

        print(f"Ingesting {DEFAULT_SYMBOL} {DEFAULT_TIMEFRAME} data...")
        print(f"Date range: {DEFAULT_START_DATE} to {DEFAULT_END_DATE}")

        # Query with auto_ingest=True (downloads and ingests real data)
        df = query_ohlcv(
            symbol=DEFAULT_SYMBOL,
            timeframe=DEFAULT_TIMEFRAME,
            start=DEFAULT_START_DATE,
            end=DEFAULT_END_DATE,
            auto_ingest=True,
        )

        # Report results
        result = {
            "timestamp": datetime.now().isoformat(),
            "symbol": DEFAULT_SYMBOL,
            "timeframe": DEFAULT_TIMEFRAME,
            "start_date": DEFAULT_START_DATE,
            "end_date": DEFAULT_END_DATE,
            "rows_ingested": len(df),
            "columns": list(df.columns),
            "date_range_actual": {
                "min": str(df["timestamp"].min()) if "timestamp" in df.columns else str(df.index.min()),
                "max": str(df["timestamp"].max()) if "timestamp" in df.columns else str(df.index.max()),
            },
        }

        print(f"\nIngestion complete: {len(df)} rows")
        print(json.dumps(result, indent=2))
        return 0

    except Exception as e:
        print(f"ERROR: Ingestion failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
