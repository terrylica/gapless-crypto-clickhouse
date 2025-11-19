#!/usr/bin/env python3
"""
ClickHouse Migration Validation Script (Phase 5)

Validates the ClickHouse implementation by:
1. Testing connection and schema initialization
2. Ingesting sample data (BTCUSDT 1h, January 2024)
3. Testing query API methods
4. Validating deterministic versioning
5. Testing duplicate ingestion (zero-gap guarantee)

Usage:
    uv run --active python tmp/clickhouse_validation.py
"""

import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run ClickHouse validation tests."""
    logger.info("=" * 80)
    logger.info("ClickHouse Migration Validation (Phase 5)")
    logger.info("=" * 80)

    # Step 1: Test connection
    logger.info("\n[1/6] Testing ClickHouse connection...")
    try:
        from gapless_crypto_data.clickhouse import ClickHouseConfig, ClickHouseConnection

        # Override port to 9001 (to avoid QuestDB conflict)
        config = ClickHouseConfig(host="localhost", port=9001)

        with ClickHouseConnection(config) as conn:
            conn.health_check()
            logger.info("✓ ClickHouse connection successful")
    except Exception as e:
        logger.error(f"✗ ClickHouse connection failed: {e}")
        sys.exit(1)

    # Step 2: Verify schema exists
    logger.info("\n[2/6] Verifying ohlcv table schema...")
    try:
        with ClickHouseConnection(config) as conn:
            result = conn.execute("SHOW TABLES")
            tables = [row[0] for row in result]

            if "ohlcv" not in tables:
                logger.error("✗ ohlcv table not found. Creating schema...")
                # Read and execute schema.sql
                with open("src/gapless_crypto_data/clickhouse/schema.sql", "r") as f:
                    schema_sql = f.read()
                conn.execute(schema_sql)
                logger.info("✓ Schema created")
            else:
                logger.info("✓ ohlcv table exists")

            # Check table structure
            result = conn.execute("DESCRIBE TABLE ohlcv")
            columns = [row[0] for row in result]
            logger.info(f"  Columns: {len(columns)} ({', '.join(columns[:5])}...)")
    except Exception as e:
        logger.error(f"✗ Schema verification failed: {e}")
        sys.exit(1)

    # Step 3: Test bulk ingestion
    logger.info("\n[3/6] Testing bulk ingestion (BTCUSDT 1h, 2024-01)...")
    try:
        from gapless_crypto_data.collectors.clickhouse_bulk_loader import (
            ClickHouseBulkLoader,
        )

        with ClickHouseConnection(config) as conn:
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")

            start_time = datetime.now()
            rows = loader.ingest_month(symbol="BTCUSDT", timeframe="1h", year=2024, month=1)
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"✓ Ingested {rows} rows in {duration:.2f}s ({rows / duration:.0f} rows/sec)"
            )
    except Exception as e:
        logger.error(f"✗ Bulk ingestion failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Step 4: Test query API
    logger.info("\n[4/6] Testing query API methods...")
    try:
        from gapless_crypto_data.clickhouse_query import OHLCVQuery

        with ClickHouseConnection(config) as conn:
            query = OHLCVQuery(conn)

            # Test get_latest
            df_latest = query.get_latest("BTCUSDT", "1h", limit=10)
            logger.info(f"✓ get_latest: {len(df_latest)} rows")

            # Test get_range
            df_range = query.get_range("BTCUSDT", "1h", start="2024-01-01", end="2024-01-31")
            logger.info(f"✓ get_range: {len(df_range)} rows")

            # Validate data integrity
            if len(df_range) > 0:
                logger.info(f"  First timestamp: {df_range.iloc[0]['timestamp']}")
                logger.info(f"  Last timestamp: {df_range.iloc[-1]['timestamp']}")
                logger.info(
                    f"  Close range: {df_range['close'].min():.2f} - {df_range['close'].max():.2f}"
                )
    except Exception as e:
        logger.error(f"✗ Query API failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Step 5: Test duplicate ingestion (zero-gap guarantee)
    logger.info("\n[5/6] Testing duplicate ingestion (zero-gap guarantee)...")
    try:
        with ClickHouseConnection(config) as conn:
            # Get row count before duplicate ingestion
            result_before = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
            count_before = result_before[0][0]

            # Re-ingest the same month
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            rows = loader.ingest_month(symbol="BTCUSDT", timeframe="1h", year=2024, month=1)
            logger.info(f"  Re-ingested {rows} rows (duplicate)")

            # Get row count after duplicate ingestion
            result_after = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
            count_after = result_after[0][0]

            if count_before == count_after:
                logger.info(f"✓ Zero-gap guarantee validated: {count_before} rows (no duplicates)")
            else:
                logger.warning(
                    f"⚠ Row count changed: {count_before} → {count_after} (expected no change)"
                )
                logger.warning("  This may be due to ReplacingMergeTree eventual consistency")
                logger.warning("  Wait for merge to complete and re-check with OPTIMIZE TABLE")

                # Force merge
                conn.execute("OPTIMIZE TABLE ohlcv FINAL")
                result_optimized = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
                count_optimized = result_optimized[0][0]

                if count_before == count_optimized:
                    logger.info(f"✓ After OPTIMIZE: {count_optimized} rows (duplicates removed)")
                else:
                    logger.error(
                        f"✗ After OPTIMIZE: {count_optimized} rows (still different from {count_before})"
                    )
    except Exception as e:
        logger.error(f"✗ Duplicate ingestion test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Step 6: Benchmark query performance with FINAL keyword
    logger.info("\n[6/6] Benchmarking query performance (FINAL keyword overhead)...")
    try:
        with ClickHouseConnection(config) as conn:
            query = OHLCVQuery(conn)

            # Benchmark get_range with FINAL
            start_time = datetime.now()
            df = query.get_range("BTCUSDT", "1h", start="2024-01-01", end="2024-01-31")
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"✓ Query with FINAL: {len(df)} rows in {duration:.3f}s ({len(df) / duration:.0f} rows/sec)"
            )
    except Exception as e:
        logger.error(f"✗ Performance benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    logger.info("\n" + "=" * 80)
    logger.info("✓ ClickHouse validation complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
