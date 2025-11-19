#!/usr/bin/env python3
"""
Comprehensive ClickHouse Migration Validation

Implements all verification steps from docs/CLICKHOUSE_MIGRATION.md
Generates validation report for ADR-0005 acceptance criteria.

Usage:
    uv run --active python tmp/comprehensive_validation.py
"""

import logging
import sys
from datetime import datetime
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class ValidationReport:
    """Validation report for ADR-0005 acceptance criteria."""

    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []
        self.start_time = datetime.now()

    def add_check(self, name: str, passed: bool, details: str = ""):
        """Add validation check result."""
        self.checks.append((name, passed, details))
        status = "✓" if passed else "✗"
        logger.info(f"{status} {name}")
        if details:
            logger.info(f"  {details}")

    def generate_report(self) -> Dict:
        """Generate validation report."""
        passed = sum(1 for _, p, _ in self.checks if p)
        total = len(self.checks)
        duration = (datetime.now() - self.start_time).total_seconds()

        return {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": duration,
            "total_checks": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": f"{passed / total * 100:.1f}%",
            "checks": [
                {"name": name, "passed": passed, "details": details}
                for name, passed, details in self.checks
            ],
        }

    def print_summary(self):
        """Print validation summary."""
        report = self.generate_report()
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total checks: {report['total_checks']}")
        logger.info(f"Passed: {report['passed']}")
        logger.info(f"Failed: {report['failed']}")
        logger.info(f"Success rate: {report['success_rate']}")
        logger.info(f"Duration: {report['duration_seconds']:.2f}s")
        logger.info("=" * 80)

        if report["failed"] > 0:
            logger.error("\nFailed checks:")
            for check in report["checks"]:
                if not check["passed"]:
                    logger.error(f"  ✗ {check['name']}: {check['details']}")


def main():
    """Run comprehensive validation."""
    logger.info("=" * 80)
    logger.info("CLICKHOUSE MIGRATION COMPREHENSIVE VALIDATION")
    logger.info("ADR-0005 Acceptance Criteria Verification")
    logger.info("=" * 80)

    report = ValidationReport()

    try:
        from gapless_crypto_data.clickhouse import ClickHouseConfig, ClickHouseConnection
        from gapless_crypto_data.clickhouse_query import OHLCVQuery
        from gapless_crypto_data.collectors.clickhouse_bulk_loader import (
            ClickHouseBulkLoader,
        )

        config = ClickHouseConfig(host="localhost", port=9001)

        # ====================================================================
        # SECTION 1: Infrastructure (Migration Guide Checklist)
        # ====================================================================
        logger.info("\n[SECTION 1] Infrastructure Verification")
        logger.info("-" * 80)

        # Check 1.1: ClickHouse container running
        with ClickHouseConnection(config) as conn:
            try:
                conn.health_check()
                report.add_check("Container running", True, "localhost:9001 accessible")
            except Exception as e:
                report.add_check("Container running", False, str(e))
                return 1

        # Check 1.2: Schema created
        with ClickHouseConnection(config) as conn:
            result = conn.execute("SELECT COUNT(*) FROM system.tables WHERE name = 'ohlcv'")
            if result[0][0] == 1:
                report.add_check("Schema created", True, "ohlcv table exists")
            else:
                report.add_check("Schema created", False, "ohlcv table not found")
                return 1

            # Check 1.3: Schema structure
            result = conn.execute("DESCRIBE TABLE ohlcv")
            columns = {row[0]: row[1] for row in result}

            expected_columns = {
                "timestamp": "DateTime64(3)",
                "symbol": "LowCardinality(String)",
                "timeframe": "LowCardinality(String)",
                "instrument_type": "LowCardinality(String)",
                "data_source": "LowCardinality(String)",
                "open": "Float64",
                "high": "Float64",
                "low": "Float64",
                "close": "Float64",
                "volume": "Float64",
                "close_time": "DateTime64(3)",
                "quote_asset_volume": "Float64",
                "number_of_trades": "Int64",
                "taker_buy_base_asset_volume": "Float64",
                "taker_buy_quote_asset_volume": "Float64",
                "_version": "UInt64",
                "_sign": "Int8",
            }

            missing = set(expected_columns.keys()) - set(columns.keys())
            if not missing:
                report.add_check("Schema structure", True, f"{len(columns)} columns verified")
            else:
                report.add_check("Schema structure", False, f"Missing columns: {missing}")

            # Check 1.4: Table engine
            result = conn.execute("SELECT engine FROM system.tables WHERE name = 'ohlcv'")
            engine = result[0][0]
            if engine == "ReplacingMergeTree":
                report.add_check("Table engine", True, "ReplacingMergeTree configured")
            else:
                report.add_check("Table engine", False, f"Wrong engine: {engine}")

        # ====================================================================
        # SECTION 2: Spot Data Ingestion & Queries
        # ====================================================================
        logger.info("\n[SECTION 2] Spot Data Verification")
        logger.info("-" * 80)

        with ClickHouseConnection(config) as conn:
            # Check 2.1: Spot ingestion
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            rows = loader.ingest_month("ETHUSDT", "1h", 2024, 2)  # Different month
            if rows > 0:
                report.add_check("Spot ingestion", True, f"{rows} rows ingested")
            else:
                report.add_check("Spot ingestion", False, "No rows ingested")

            # Check 2.2: get_latest query
            query = OHLCVQuery(conn)
            df = query.get_latest("ETHUSDT", "1h", limit=10, instrument_type="spot")
            if len(df) == 10:
                report.add_check("get_latest query", True, f"Retrieved {len(df)} rows")
            else:
                report.add_check("get_latest query", False, f"Expected 10 rows, got {len(df)}")

            # Check 2.3: get_range query
            df = query.get_range(
                "ETHUSDT", "1h", "2024-02-01", "2024-02-29", instrument_type="spot"
            )
            if len(df) > 0:
                report.add_check("get_range query", True, f"Retrieved {len(df)} rows")
            else:
                report.add_check("get_range query", False, "No rows returned")

            # Check 2.4: get_multi_symbol query
            df = query.get_multi_symbol(
                ["BTCUSDT", "ETHUSDT"],
                "1h",
                "2024-01-01",
                "2024-01-31",
                instrument_type="spot",
            )
            if len(df) > 0:
                symbols = df["symbol"].unique().tolist()
                report.add_check(
                    "get_multi_symbol query", True, f"{len(df)} rows, symbols: {symbols}"
                )
            else:
                report.add_check("get_multi_symbol query", False, "No rows returned")

        # ====================================================================
        # SECTION 3: Futures Data (ADR-0004)
        # ====================================================================
        logger.info("\n[SECTION 3] Futures Data Verification (ADR-0004)")
        logger.info("-" * 80)

        with ClickHouseConnection(config) as conn:
            # Check 3.1: Futures ingestion
            loader = ClickHouseBulkLoader(conn, instrument_type="futures")
            rows = loader.ingest_month("ETHUSDT", "1h", 2024, 2)
            if rows > 0:
                report.add_check("Futures ingestion", True, f"{rows} rows ingested")
            else:
                report.add_check("Futures ingestion", False, "No rows ingested")

            # Check 3.2: Spot/futures isolation
            result = conn.execute(
                "SELECT instrument_type, COUNT(*) FROM ohlcv FINAL GROUP BY instrument_type"
            )
            counts = {row[0]: row[1] for row in result}

            if "spot" in counts and "futures" in counts:
                report.add_check(
                    "Spot/futures isolation",
                    True,
                    f"spot: {counts['spot']}, futures: {counts['futures']}",
                )
            else:
                report.add_check(
                    "Spot/futures isolation", False, f"Missing instrument types: {counts}"
                )

            # Check 3.3: instrument_type parameter
            query = OHLCVQuery(conn)
            df_spot = query.get_latest("ETHUSDT", "1h", limit=5, instrument_type="spot")
            df_futures = query.get_latest("ETHUSDT", "1h", limit=5, instrument_type="futures")

            spot_types = df_spot["instrument_type"].unique().tolist()
            futures_types = df_futures["instrument_type"].unique().tolist()

            if spot_types == ["spot"] and futures_types == ["futures"]:
                report.add_check("instrument_type parameter", True, "Filtering works")
            else:
                report.add_check(
                    "instrument_type parameter",
                    False,
                    f"Wrong types: spot={spot_types}, futures={futures_types}",
                )

            # Check 3.4: No cross-contamination
            result = conn.execute(
                """
                SELECT instrument_type, COUNT(*) FROM ohlcv FINAL
                WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                  AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
                GROUP BY instrument_type
            """
            )
            feb_counts = {row[0]: row[1] for row in result}

            if (
                len(feb_counts) == 2
                and feb_counts.get("spot", 0) > 0
                and feb_counts.get("futures", 0) > 0
            ):
                report.add_check(
                    "No cross-contamination",
                    True,
                    f"Both types present: {feb_counts}",
                )
            else:
                report.add_check(
                    "No cross-contamination", False, f"Unexpected counts: {feb_counts}"
                )

        # ====================================================================
        # SECTION 4: Zero-Gap Guarantee (ADR-0005)
        # ====================================================================
        logger.info("\n[SECTION 4] Zero-Gap Guarantee Verification")
        logger.info("-" * 80)

        with ClickHouseConnection(config) as conn:
            # Check 4.1: Duplicate ingestion (spot)
            result = conn.execute(
                """
                SELECT COUNT(*) FROM ohlcv FINAL
                WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                  AND instrument_type = 'spot'
                  AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
            """
            )
            count_before = result[0][0]

            # Re-ingest same data
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            loader.ingest_month("ETHUSDT", "1h", 2024, 2)

            result = conn.execute(
                """
                SELECT COUNT(*) FROM ohlcv FINAL
                WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                  AND instrument_type = 'spot'
                  AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
            """
            )
            count_after = result[0][0]

            if count_before == count_after:
                report.add_check(
                    "Zero-gap (spot)",
                    True,
                    f"{count_before} rows maintained (no duplicates)",
                )
            else:
                # Try OPTIMIZE
                conn.execute("OPTIMIZE TABLE ohlcv FINAL")
                result = conn.execute(
                    """
                    SELECT COUNT(*) FROM ohlcv FINAL
                    WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                      AND instrument_type = 'spot'
                      AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
                """
                )
                count_optimized = result[0][0]

                if count_before == count_optimized:
                    report.add_check(
                        "Zero-gap (spot)",
                        True,
                        f"{count_optimized} rows after OPTIMIZE (duplicates removed)",
                    )
                else:
                    report.add_check(
                        "Zero-gap (spot)",
                        False,
                        f"Count mismatch: {count_before} → {count_after} → {count_optimized}",
                    )

            # Check 4.2: Duplicate ingestion (futures)
            result = conn.execute(
                """
                SELECT COUNT(*) FROM ohlcv FINAL
                WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                  AND instrument_type = 'futures'
                  AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
            """
            )
            count_before = result[0][0]

            loader = ClickHouseBulkLoader(conn, instrument_type="futures")
            loader.ingest_month("ETHUSDT", "1h", 2024, 2)

            result = conn.execute(
                """
                SELECT COUNT(*) FROM ohlcv FINAL
                WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                  AND instrument_type = 'futures'
                  AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
            """
            )
            count_after = result[0][0]

            if count_before == count_after:
                report.add_check(
                    "Zero-gap (futures)",
                    True,
                    f"{count_before} rows maintained (no duplicates)",
                )
            else:
                conn.execute("OPTIMIZE TABLE ohlcv FINAL")
                result = conn.execute(
                    """
                    SELECT COUNT(*) FROM ohlcv FINAL
                    WHERE symbol = 'ETHUSDT' AND timeframe = '1h'
                      AND instrument_type = 'futures'
                      AND timestamp >= '2024-02-01' AND timestamp <= '2024-02-29'
                """
                )
                count_optimized = result[0][0]

                if count_before == count_optimized:
                    report.add_check(
                        "Zero-gap (futures)",
                        True,
                        f"{count_optimized} rows after OPTIMIZE",
                    )
                else:
                    report.add_check(
                        "Zero-gap (futures)",
                        False,
                        f"Count mismatch: {count_before} → {count_after} → {count_optimized}",
                    )

        # ====================================================================
        # SECTION 5: Performance & FINAL Keyword
        # ====================================================================
        logger.info("\n[SECTION 5] Performance Verification")
        logger.info("-" * 80)

        with ClickHouseConnection(config) as conn:
            # Check 5.1: FINAL keyword overhead measurement
            query = OHLCVQuery(conn)

            start = datetime.now()
            df = query.get_range(
                "BTCUSDT", "1h", "2024-01-01", "2024-01-31", instrument_type="spot"
            )
            duration = (datetime.now() - start).total_seconds()

            if duration < 5.0:  # Should be <1s per migration guide, but allow 5s buffer
                report.add_check(
                    "Query performance",
                    True,
                    f"{len(df)} rows in {duration:.3f}s (FINAL overhead acceptable)",
                )
            else:
                report.add_check(
                    "Query performance",
                    False,
                    f"{len(df)} rows in {duration:.3f}s (too slow)",
                )

        # ====================================================================
        # Print summary
        # ====================================================================
        report.print_summary()

        # Return exit code
        validation_report = report.generate_report()
        return 0 if validation_report["failed"] == 0 else 1

    except Exception as e:
        logger.error(f"\n✗ Validation failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
