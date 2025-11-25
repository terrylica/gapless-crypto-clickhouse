#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "clickhouse-connect>=0.7.0",
#     "pandas>=2.2.0",
#     "requests>=2.28.0",
# ]
# ///
"""
Real Binance Data Validation Script

ADR-0038: Real Binance Data Validation

Validates the complete Binance Vision → ClickHouse pipeline using real data:
- Downloads real BTCUSDT klines from Binance CDN (2024-01-01)
- Tests both futures (12-column header) and spot (11-column no header) formats
- Validates schema compliance, deduplication, and data integrity

9-Stage Pipeline:
1. CDN Download - HTTP 200, ZIP > 0 bytes
2. ZIP Extract - Single CSV per archive
3. CSV Parse - Format detection (futures vs spot)
4. DataFrame Validation - OHLC and volume constraints
5. _version Hash - Deterministic SHA256 computation
6. ClickHouse Insert - 24 rows per format
7. Query FINAL - Verify row counts
8. Deduplication Test - Re-insert doesn't double count
9. Schema Compliance - 18 columns, symbol-first ORDER BY

Exit Codes:
- 0: All validations passed
- 1: Validation failed (raises exception)

Environment Variables (via Doppler):
- CLICKHOUSE_HOST
- CLICKHOUSE_PORT (default: 8443)
- CLICKHOUSE_USER (default: default)
- CLICKHOUSE_PASSWORD
"""

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import clickhouse_connect
import pandas as pd
import requests

# Constants
TEST_SYMBOL = "BTCUSDT"
TEST_TIMEFRAME = "1h"
EXPECTED_ROWS = 24  # 24 hourly bars per day

# Use different test dates for futures vs spot to avoid ORDER BY key collision
# ORDER BY is (symbol, timeframe, toStartOfHour(timestamp), timestamp) - instrument_type is NOT included
# If both formats use same date, ReplacingMergeTree treats them as duplicates (keeps highest _version)
TEST_DATES = {
    "futures": "2024-01-01",
    "spot": "2024-01-02",
}

CDN_URLS = {
    "futures": f"https://data.binance.vision/data/futures/um/daily/klines/{TEST_SYMBOL}/{TEST_TIMEFRAME}/{TEST_SYMBOL}-{TEST_TIMEFRAME}-{TEST_DATES['futures']}.zip",
    "spot": f"https://data.binance.vision/data/spot/daily/klines/{TEST_SYMBOL}/{TEST_TIMEFRAME}/{TEST_SYMBOL}-{TEST_TIMEFRAME}-{TEST_DATES['spot']}.zip",
}

INSTRUMENT_TYPES = {
    "futures": "futures-um",
    "spot": "spot",
}

# Column definitions (both spot and futures have 12 columns)
SPOT_COLUMNS = [
    "open_time",
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
    "ignore",
]


def log_with_timestamp(message: str) -> None:
    """Print timestamped log message with UTC timezone."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def calculate_version_hash(row: pd.Series) -> int:
    """Calculate deterministic version hash for deduplication.

    Matches the pattern in clickhouse_bulk_loader.py.
    """
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


class BinanceRealDataValidator:
    """9-stage validation pipeline for real Binance data."""

    def __init__(
        self,
        release_version: str = "",
        git_commit: str = "",
    ):
        self.release_version = release_version
        self.git_commit = git_commit
        self.results: dict = {
            "validation_type": "binance_real_data",
            "release_version": release_version,
            "git_commit": git_commit,
            "status": "pending",
            "stages": {},
            "error_message": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.client: clickhouse_connect.driver.client.Client | None = None

    def run(self) -> dict:
        """Execute 9-stage validation pipeline."""
        log_with_timestamp("=" * 80)
        log_with_timestamp("Real Binance Data Validation (ADR-0038)")
        log_with_timestamp("=" * 80)

        start_time = datetime.now(timezone.utc)

        # Connect to ClickHouse
        self._connect_clickhouse()

        # Process both formats
        for format_name in ["futures", "spot"]:
            log_with_timestamp("")
            log_with_timestamp(f"{'=' * 40}")
            log_with_timestamp(f"Processing {format_name.upper()} format")
            log_with_timestamp(f"{'=' * 40}")

            # Stage 1-3: Download, extract, parse
            df = self._stage_1_3_download_and_parse(format_name)

            # Stage 4: DataFrame validation
            self._stage_4_validate_dataframe(df, format_name)

            # Stage 5: Compute version hashes
            df = self._stage_5_compute_hashes(df, format_name)

            # Stage 6: Insert to ClickHouse
            self._stage_6_insert(df, format_name)

            # Stage 7: Query FINAL
            self._stage_7_query_final(format_name)

            # Stage 8: Deduplication test
            self._stage_8_dedup_test(df, format_name)

        # Stage 9: Schema compliance (once for both)
        self._stage_9_schema_compliance()

        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        self.results["status"] = "passed"
        self.results["duration_ms"] = duration_ms

        log_with_timestamp("")
        log_with_timestamp("=" * 80)
        log_with_timestamp(f"✅ ALL STAGES PASSED ({duration_ms}ms)")
        log_with_timestamp("=" * 80)

        return self.results

    def _connect_clickhouse(self) -> None:
        """Connect to ClickHouse Cloud."""
        host = os.environ.get("CLICKHOUSE_HOST")
        port = int(os.environ.get("CLICKHOUSE_PORT", "8443"))
        username = os.environ.get("CLICKHOUSE_USER", "default")
        password = os.environ.get("CLICKHOUSE_PASSWORD")

        if not host or not password:
            raise ValueError(
                "Missing required environment variables: CLICKHOUSE_HOST, CLICKHOUSE_PASSWORD"
            )

        log_with_timestamp(f"Connecting to ClickHouse Cloud ({host}:{port})...")

        self.client = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            secure=True,
            settings={
                "do_not_merge_across_partitions_select_final": 1,
                "async_insert": 0,  # Immediate visibility for validation
            },
        )

        version = self.client.command("SELECT version()")
        log_with_timestamp(f"✅ Connected to ClickHouse {version}")

    def _stage_1_3_download_and_parse(self, format_name: str) -> pd.DataFrame:
        """Stages 1-3: Download ZIP, extract CSV, parse DataFrame."""
        url = CDN_URLS[format_name]
        instrument_type = INSTRUMENT_TYPES[format_name]

        # Stage 1: CDN Download
        log_with_timestamp(f"Stage 1: Downloading {format_name} data from CDN...")
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            raise RuntimeError(
                f"CDN download failed: HTTP {response.status_code} for {url}"
            )
        if len(response.content) == 0:
            raise RuntimeError(f"CDN returned empty ZIP for {url}")

        log_with_timestamp(
            f"✅ Stage 1: Downloaded {len(response.content)} bytes (HTTP 200)"
        )
        self.results["stages"][f"{format_name}_download"] = {
            "status": "passed",
            "bytes": len(response.content),
        }

        # Stage 2: ZIP Extract
        log_with_timestamp(f"Stage 2: Extracting ZIP archive...")
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            file_list = zf.namelist()
            if len(file_list) != 1:
                raise RuntimeError(
                    f"Expected 1 CSV in ZIP, found {len(file_list)}: {file_list}"
                )
            csv_filename = file_list[0]
            csv_content = zf.read(csv_filename)

        log_with_timestamp(f"✅ Stage 2: Extracted {csv_filename}")
        self.results["stages"][f"{format_name}_extract"] = {
            "status": "passed",
            "filename": csv_filename,
        }

        # Stage 3: CSV Parse + Format Detection
        log_with_timestamp(f"Stage 3: Parsing CSV and detecting format...")

        # Detect format by checking first line
        first_line = csv_content.decode("utf-8").split("\n")[0]
        has_header = first_line.startswith("open_time")

        if has_header:
            # Futures format: 12 columns with header
            df = pd.read_csv(io.BytesIO(csv_content), header=0)
            if "ignore" in df.columns:
                df = df.drop(columns=["ignore"])
            # Rename columns to match spot format
            df = df.rename(
                columns={
                    "count": "number_of_trades",
                    "quote_volume": "quote_asset_volume",
                    "taker_buy_volume": "taker_buy_base_asset_volume",
                    "taker_buy_quote_volume": "taker_buy_quote_asset_volume",
                }
            )
            detected_format = "futures"
        else:
            # Spot format: 12 columns without header (includes 'ignore' column)
            df = pd.read_csv(io.BytesIO(csv_content), header=None, names=SPOT_COLUMNS)
            if "ignore" in df.columns:
                df = df.drop(columns=["ignore"])
            detected_format = "spot"

        # Verify row count
        if len(df) != EXPECTED_ROWS:
            raise RuntimeError(
                f"Expected {EXPECTED_ROWS} rows, got {len(df)} for {format_name}"
            )

        # Convert timestamps
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
        df = df.drop(columns=["open_time"])

        # Add metadata columns
        df["symbol"] = TEST_SYMBOL
        df["timeframe"] = TEST_TIMEFRAME
        df["instrument_type"] = instrument_type
        df["data_source"] = "binance_cdn_validation"
        df["funding_rate"] = None  # NULL for both

        log_with_timestamp(
            f"✅ Stage 3: Parsed {len(df)} rows, detected format: {detected_format}"
        )
        self.results["stages"][f"{format_name}_parse"] = {
            "status": "passed",
            "rows": len(df),
            "detected_format": detected_format,
            "has_header": has_header,
        }

        return df

    def _stage_4_validate_dataframe(self, df: pd.DataFrame, format_name: str) -> None:
        """Stage 4: Validate OHLC and volume constraints."""
        log_with_timestamp(f"Stage 4: Validating DataFrame constraints...")

        errors = []

        # OHLC constraints
        if not (df["high"] >= df["low"]).all():
            errors.append("high < low violation")
        if not (df["high"] >= df["open"]).all():
            errors.append("high < open violation")
        if not (df["high"] >= df["close"]).all():
            errors.append("high < close violation")
        if not (df["low"] <= df["open"]).all():
            errors.append("low > open violation")
        if not (df["low"] <= df["close"]).all():
            errors.append("low > close violation")

        # Volume constraints
        if not (df["volume"] >= 0).all():
            errors.append("negative volume")
        if not (df["taker_buy_base_asset_volume"] <= df["volume"]).all():
            errors.append("taker_buy_base > volume violation")
        if not (
            df["taker_buy_quote_asset_volume"] <= df["quote_asset_volume"]
        ).all():
            errors.append("taker_buy_quote > quote_asset violation")

        # Timestamp constraints
        timestamps = df["timestamp"].sort_values()
        if not timestamps.equals(df["timestamp"]):
            errors.append("timestamps not chronological")

        if errors:
            raise RuntimeError(f"DataFrame validation failed: {errors}")

        log_with_timestamp(f"✅ Stage 4: All constraints passed")
        self.results["stages"][f"{format_name}_validate"] = {
            "status": "passed",
            "ohlc_valid": True,
            "volume_valid": True,
            "timestamps_chronological": True,
        }

    def _stage_5_compute_hashes(
        self, df: pd.DataFrame, format_name: str
    ) -> pd.DataFrame:
        """Stage 5: Compute deterministic version hashes."""
        log_with_timestamp(f"Stage 5: Computing _version hashes...")

        df["_version"] = df.apply(calculate_version_hash, axis=1)
        df["_sign"] = 1

        unique_hashes = df["_version"].nunique()
        if unique_hashes != EXPECTED_ROWS:
            raise RuntimeError(
                f"Expected {EXPECTED_ROWS} unique hashes, got {unique_hashes}"
            )

        log_with_timestamp(f"✅ Stage 5: {unique_hashes} unique hashes computed")
        self.results["stages"][f"{format_name}_hash"] = {
            "status": "passed",
            "unique_hashes": unique_hashes,
        }

        return df

    def _stage_6_insert(self, df: pd.DataFrame, format_name: str) -> None:
        """Stage 6: Insert data to ClickHouse."""
        log_with_timestamp(f"Stage 6: Inserting {len(df)} rows to ClickHouse...")

        # Reorder columns to match schema
        column_order = [
            "timestamp",
            "symbol",
            "timeframe",
            "instrument_type",
            "data_source",
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
            "_version",
            "_sign",
        ]
        df = df[column_order]

        self.client.insert_df("ohlcv", df)

        log_with_timestamp(f"✅ Stage 6: Inserted {len(df)} rows")
        self.results["stages"][f"{format_name}_insert"] = {
            "status": "passed",
            "rows_inserted": len(df),
        }

    def _stage_7_query_final(self, format_name: str) -> None:
        """Stage 7: Query with FINAL to verify row count."""
        instrument_type = INSTRUMENT_TYPES[format_name]
        test_date = TEST_DATES[format_name]
        log_with_timestamp(f"Stage 7: Querying with FINAL (instrument_type={instrument_type}, date={test_date})...")

        query = f"""
            SELECT COUNT(*) as count
            FROM ohlcv FINAL
            WHERE symbol = '{TEST_SYMBOL}'
              AND timeframe = '{TEST_TIMEFRAME}'
              AND instrument_type = '{instrument_type}'
              AND toDate(timestamp) = '{test_date}'
        """
        result = self.client.query(query)
        row_count = result.result_rows[0][0]

        if row_count != EXPECTED_ROWS:
            raise RuntimeError(
                f"Expected {EXPECTED_ROWS} rows for {format_name}, got {row_count}"
            )

        log_with_timestamp(f"✅ Stage 7: Query returned {row_count} rows (FINAL)")
        self.results["stages"][f"{format_name}_query"] = {
            "status": "passed",
            "row_count": row_count,
        }

    def _stage_8_dedup_test(self, df: pd.DataFrame, format_name: str) -> None:
        """Stage 8: Re-insert and verify deduplication."""
        instrument_type = INSTRUMENT_TYPES[format_name]
        test_date = TEST_DATES[format_name]
        log_with_timestamp(f"Stage 8: Re-inserting to test deduplication...")

        # Re-insert the same data
        column_order = [
            "timestamp",
            "symbol",
            "timeframe",
            "instrument_type",
            "data_source",
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
            "_version",
            "_sign",
        ]
        df_reinsert = df[column_order]
        self.client.insert_df("ohlcv", df_reinsert)

        # Query with FINAL - should still be EXPECTED_ROWS, not double
        query = f"""
            SELECT COUNT(*) as count
            FROM ohlcv FINAL
            WHERE symbol = '{TEST_SYMBOL}'
              AND timeframe = '{TEST_TIMEFRAME}'
              AND instrument_type = '{instrument_type}'
              AND toDate(timestamp) = '{test_date}'
        """
        result = self.client.query(query)
        row_count = result.result_rows[0][0]

        if row_count != EXPECTED_ROWS:
            raise RuntimeError(
                f"Deduplication failed: expected {EXPECTED_ROWS}, got {row_count} after re-insert"
            )

        log_with_timestamp(
            f"✅ Stage 8: Deduplication verified ({row_count} rows after re-insert)"
        )
        self.results["stages"][f"{format_name}_dedup"] = {
            "status": "passed",
            "row_count_after_reinsert": row_count,
        }

    def _stage_9_schema_compliance(self) -> None:
        """Stage 9: Verify schema compliance."""
        log_with_timestamp("")
        log_with_timestamp(f"Stage 9: Verifying schema compliance...")

        # Get CREATE TABLE statement
        create_table = self.client.command("SHOW CREATE TABLE ohlcv")

        # Verify ORDER BY (ADR-0034: symbol-first)
        expected_order_by = "(symbol, timeframe, toStartOfHour(timestamp), timestamp)"
        if expected_order_by not in create_table:
            raise RuntimeError(
                f"ORDER BY mismatch: expected {expected_order_by}"
            )
        log_with_timestamp(f"✅ ORDER BY verified: {expected_order_by}")

        # Verify engine
        if "ReplacingMergeTree" not in create_table and "SharedReplacingMergeTree" not in create_table:
            raise RuntimeError("Expected ReplacingMergeTree or SharedReplacingMergeTree engine")
        log_with_timestamp(f"✅ Engine verified: ReplacingMergeTree")

        # Verify column count
        columns = self.client.query(
            "SELECT name FROM system.columns WHERE table = 'ohlcv'"
        )
        column_count = len(columns.result_rows)
        if column_count != 18:
            raise RuntimeError(f"Expected 18 columns, got {column_count}")
        log_with_timestamp(f"✅ Column count verified: {column_count}")

        self.results["stages"]["schema_compliance"] = {
            "status": "passed",
            "order_by": expected_order_by,
            "engine": "ReplacingMergeTree",
            "column_count": column_count,
        }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate real Binance data pipeline (ADR-0038)"
    )
    parser.add_argument(
        "--release-version",
        default="",
        help="Release version being validated",
    )
    parser.add_argument(
        "--git-commit",
        default="",
        help="Git commit SHA",
    )
    parser.add_argument(
        "--output",
        default="binance-validation-result.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    validator = BinanceRealDataValidator(
        release_version=args.release_version,
        git_commit=args.git_commit,
    )

    try:
        results = validator.run()
        results["status"] = "passed"
    except Exception as e:
        log_with_timestamp(f"❌ VALIDATION FAILED: {e}")
        results = validator.results
        results["status"] = "failed"
        results["error_message"] = str(e)
        raise  # Re-raise to get non-zero exit code

    # Write results to JSON
    output_path = Path(args.output)
    output_path.write_text(json.dumps(results, indent=2, default=str))
    log_with_timestamp(f"Results written to {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
