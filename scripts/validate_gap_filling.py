#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "clickhouse-connect>=0.7.0",
#     "httpx>=0.25.0",
#     "pandas>=2.2.0",
#     "tenacity>=8.0.0",
# ]
# ///
"""
Gap Filling Validation Script

ADR-0041: Gap Filling Validation

Validates the REST API gap filling pipeline using yesterday's data:
- Tests fresh data bridge scenario (Vision API lag)
- Validates DataFrame conversion and schema compliance
- Verifies ReplacingMergeTree deduplication

7-Stage Pipeline:
1. REST API Connectivity - HTTP HEAD to spot + futures endpoints
2. Fresh Data Fetch - GET yesterday's BTCUSDT 1h (24 rows x 2 formats)
3. Response Validation - 12-element arrays, OHLCV constraints
4. DataFrame Conversion - 18-column schema, data_source="rest_api"
5. Version Hash Compute - SHA256 deterministic, 24 unique hashes
6. ClickHouse Insert - 48 rows total (24 spot + 24 futures)
7. Deduplication Test - Re-insert -> still 48 rows with FINAL

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
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import clickhouse_connect
import httpx
import pandas as pd

# Constants
TEST_SYMBOL = "BTCUSDT"
TEST_TIMEFRAME = "1h"
EXPECTED_ROWS_PER_FORMAT = 24  # 24 hourly bars per day

# API endpoints
SPOT_API_URL = "https://api.binance.com/api/v3/klines"
FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"

INSTRUMENT_TYPES = {
    "spot": "spot",
    "futures": "futures-um",
}


def log_with_timestamp(message: str) -> None:
    """Print timestamped log message with UTC timezone."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{timestamp}] {message}")


def calculate_version_hash(row: pd.Series) -> int:
    """Calculate deterministic version hash for deduplication."""
    version_input = (
        f"{row['timestamp']}"
        f"{row['open']}{row['high']}{row['low']}{row['close']}{row['volume']}"
        f"{row['symbol']}{row['timeframe']}{row['instrument_type']}"
    )
    hash_bytes = hashlib.sha256(version_input.encode("utf-8")).digest()
    return int.from_bytes(hash_bytes[:8], byteorder="big", signed=False)


class GapFillingValidator:
    """7-stage validation pipeline for gap filling."""

    def __init__(self, release_version: str = "", git_commit: str = ""):
        self.release_version = release_version
        self.git_commit = git_commit
        self.results: dict = {
            "validation_type": "gap_filling",
            "release_version": release_version,
            "git_commit": git_commit,
            "status": "pending",
            "stages": {},
            "error_message": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.client: clickhouse_connect.driver.client.Client | None = None
        self.test_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )

    def run(self) -> dict:
        """Execute 7-stage validation pipeline."""
        log_with_timestamp("=" * 80)
        log_with_timestamp("Gap Filling Validation (ADR-0041)")
        log_with_timestamp(f"Test Date: {self.test_date} (yesterday)")
        log_with_timestamp("=" * 80)

        start_time = datetime.now(timezone.utc)

        # Stage 1: REST API Connectivity
        self._stage_1_connectivity()

        # Connect to ClickHouse
        self._connect_clickhouse()

        # Process both formats
        all_dataframes = []
        for format_name in ["spot", "futures"]:
            log_with_timestamp("")
            log_with_timestamp(f"{'=' * 40}")
            log_with_timestamp(f"Processing {format_name.upper()} format")
            log_with_timestamp(f"{'=' * 40}")

            # Stage 2: Fresh data fetch
            raw_klines = self._stage_2_fetch_data(format_name)

            # Stage 3: Response validation
            self._stage_3_validate_response(raw_klines, format_name)

            # Stage 4: DataFrame conversion
            df = self._stage_4_convert_dataframe(raw_klines, format_name)

            # Stage 5: Version hash compute
            df = self._stage_5_compute_hashes(df, format_name)

            all_dataframes.append(df)

        # Stage 6: ClickHouse insert (both formats)
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        self._stage_6_insert(combined_df)

        # Stage 7: Deduplication test
        self._stage_7_dedup_test(combined_df)

        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        self.results["status"] = "passed"
        self.results["duration_ms"] = duration_ms

        log_with_timestamp("")
        log_with_timestamp("=" * 80)
        log_with_timestamp(f"ALL STAGES PASSED ({duration_ms}ms)")
        log_with_timestamp("=" * 80)

        return self.results

    def _stage_1_connectivity(self) -> None:
        """Stage 1: Verify REST API connectivity."""
        log_with_timestamp("Stage 1: Checking REST API connectivity...")

        spot_ok = False
        futures_ok = False

        try:
            response = httpx.head(SPOT_API_URL, timeout=10)
            spot_ok = response.status_code in (200, 400)  # 400 = missing params (ok)
        except Exception as e:
            log_with_timestamp(f"Spot API check failed: {e}")

        try:
            response = httpx.head(FUTURES_API_URL, timeout=10)
            futures_ok = response.status_code in (200, 400)
        except Exception as e:
            log_with_timestamp(f"Futures API check failed: {e}")

        if not spot_ok or not futures_ok:
            raise RuntimeError(
                f"REST API connectivity failed: spot={spot_ok}, futures={futures_ok}"
            )

        log_with_timestamp(f"Stage 1: API connectivity OK (spot={spot_ok}, futures={futures_ok})")
        self.results["stages"]["rest_api_connectivity"] = {
            "status": "passed",
            "spot_ok": spot_ok,
            "futures_ok": futures_ok,
        }

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
                "async_insert": 0,
            },
        )

        version = self.client.command("SELECT version()")
        log_with_timestamp(f"Connected to ClickHouse {version}")

    def _stage_2_fetch_data(self, format_name: str) -> list:
        """Stage 2: Fetch fresh data from REST API."""
        log_with_timestamp(f"Stage 2: Fetching {format_name} data for {self.test_date}...")

        base_url = SPOT_API_URL if format_name == "spot" else FUTURES_API_URL

        # Calculate timestamps for yesterday
        test_date_dt = datetime.strptime(self.test_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        start_ms = int(test_date_dt.timestamp() * 1000)
        end_ms = int((test_date_dt + timedelta(days=1)).timestamp() * 1000)

        params = {
            "symbol": TEST_SYMBOL,
            "interval": TEST_TIMEFRAME,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1000,
        }

        response = httpx.get(base_url, params=params, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(
                f"API request failed: HTTP {response.status_code} - {response.text}"
            )

        raw_klines = response.json()

        if isinstance(raw_klines, dict) and "code" in raw_klines:
            raise RuntimeError(f"API error: {raw_klines}")

        log_with_timestamp(f"Stage 2: Fetched {len(raw_klines)} klines")
        self.results["stages"][f"{format_name}_fetch"] = {
            "status": "passed",
            "date": self.test_date,
            "rows": len(raw_klines),
        }

        return raw_klines

    def _stage_3_validate_response(self, raw_klines: list, format_name: str) -> None:
        """Stage 3: Validate API response structure."""
        log_with_timestamp(f"Stage 3: Validating {format_name} response...")

        if len(raw_klines) != EXPECTED_ROWS_PER_FORMAT:
            raise RuntimeError(
                f"Expected {EXPECTED_ROWS_PER_FORMAT} klines, got {len(raw_klines)}"
            )

        for i, kline in enumerate(raw_klines):
            if len(kline) < 12:
                raise RuntimeError(
                    f"Kline {i} has {len(kline)} elements, expected 12"
                )

            # OHLCV validation
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])

            if high_price < low_price:
                raise RuntimeError(f"Kline {i}: high < low")
            if high_price < open_price or high_price < close_price:
                raise RuntimeError(f"Kline {i}: high < open or close")
            if low_price > open_price or low_price > close_price:
                raise RuntimeError(f"Kline {i}: low > open or close")
            if volume < 0:
                raise RuntimeError(f"Kline {i}: negative volume")

        log_with_timestamp(f"Stage 3: Response validation passed")
        self.results["stages"][f"{format_name}_validate"] = {
            "status": "passed",
            "klines_validated": len(raw_klines),
        }

    def _stage_4_convert_dataframe(self, raw_klines: list, format_name: str) -> pd.DataFrame:
        """Stage 4: Convert to ClickHouse-ready DataFrame."""
        log_with_timestamp(f"Stage 4: Converting {format_name} to DataFrame...")

        instrument_type = INSTRUMENT_TYPES[format_name]

        rows = []
        for kline in raw_klines:
            rows.append(
                {
                    "timestamp": datetime.fromtimestamp(
                        int(kline[0]) / 1000, tz=timezone.utc
                    ),
                    "symbol": TEST_SYMBOL,
                    "timeframe": TEST_TIMEFRAME,
                    "instrument_type": instrument_type,
                    "data_source": "gap_filling_validation",
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": datetime.fromtimestamp(
                        int(kline[6]) / 1000, tz=timezone.utc
                    ),
                    "quote_asset_volume": float(kline[7]),
                    "number_of_trades": int(kline[8]),
                    "taker_buy_base_asset_volume": float(kline[9]),
                    "taker_buy_quote_asset_volume": float(kline[10]),
                    "funding_rate": None,
                }
            )

        df = pd.DataFrame(rows)

        # Verify column count
        if len(df.columns) != 16:  # Before adding _version and _sign
            raise RuntimeError(f"Expected 16 columns, got {len(df.columns)}")

        log_with_timestamp(f"Stage 4: Created DataFrame with {len(df.columns)} columns")
        self.results["stages"][f"{format_name}_convert"] = {
            "status": "passed",
            "columns": len(df.columns) + 2,  # Will add _version and _sign
        }

        return df

    def _stage_5_compute_hashes(self, df: pd.DataFrame, format_name: str) -> pd.DataFrame:
        """Stage 5: Compute deterministic version hashes."""
        log_with_timestamp(f"Stage 5: Computing {format_name} version hashes...")

        df["_version"] = df.apply(calculate_version_hash, axis=1)
        df["_sign"] = 1

        unique_hashes = df["_version"].nunique()
        if unique_hashes != EXPECTED_ROWS_PER_FORMAT:
            raise RuntimeError(
                f"Expected {EXPECTED_ROWS_PER_FORMAT} unique hashes, got {unique_hashes}"
            )

        log_with_timestamp(f"Stage 5: {unique_hashes} unique hashes computed")
        self.results["stages"][f"{format_name}_hash"] = {
            "status": "passed",
            "unique_hashes": unique_hashes,
        }

        return df

    def _stage_6_insert(self, df: pd.DataFrame) -> None:
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

        log_with_timestamp(f"Stage 6: Inserted {len(df)} rows")
        self.results["stages"]["clickhouse_insert"] = {
            "status": "passed",
            "rows_inserted": len(df),
        }

    def _stage_7_dedup_test(self, df: pd.DataFrame) -> None:
        """Stage 7: Verify deduplication by re-inserting."""
        log_with_timestamp("Stage 7: Testing deduplication...")

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

        # Query with FINAL - should still be 48 rows
        expected_total = EXPECTED_ROWS_PER_FORMAT * 2  # spot + futures
        query = f"""
            SELECT COUNT(*) as count
            FROM ohlcv FINAL
            WHERE symbol = '{TEST_SYMBOL}'
              AND timeframe = '{TEST_TIMEFRAME}'
              AND data_source = 'gap_filling_validation'
              AND toDate(timestamp) = '{self.test_date}'
        """
        result = self.client.query(query)
        row_count = result.result_rows[0][0]

        if row_count != expected_total:
            raise RuntimeError(
                f"Deduplication failed: expected {expected_total}, got {row_count}"
            )

        log_with_timestamp(f"Stage 7: Deduplication verified ({row_count} rows)")
        self.results["stages"]["deduplication_test"] = {
            "status": "passed",
            "rows_after_reinsert": row_count,
        }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate gap filling pipeline (ADR-0041)"
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
        default="gap-filling-result.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    validator = GapFillingValidator(
        release_version=args.release_version,
        git_commit=args.git_commit,
    )

    try:
        results = validator.run()
        results["status"] = "passed"
    except Exception as e:
        log_with_timestamp(f"VALIDATION FAILED: {e}")
        results = validator.results
        results["status"] = "failed"
        results["error_message"] = str(e)
        raise  # Re-raise to get non-zero exit code

    # Write results to JSON
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)
    log_with_timestamp(f"Results written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
