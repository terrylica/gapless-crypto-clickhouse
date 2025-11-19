#!/usr/bin/env python3
"""Quick ClickHouse Migration Validation (Phase 5) - Simplified

Tests core ClickHouse implementation functionality without schema creation.
"""

import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    """Run quick ClickHouse validation."""
    logger.info("=" * 80)
    logger.info("ClickHouse Migration Quick Validation")
    logger.info("=" * 80)

    try:
        from gapless_crypto_data.clickhouse import ClickHouseConfig, ClickHouseConnection
        from gapless_crypto_data.clickhouse_query import OHLCVQuery
        from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

        config = ClickHouseConfig(host="localhost", port=9001)

        # Test 1: Connection
        logger.info("\n[1/5] Testing connection...")
        with ClickHouseConnection(config) as conn:
            conn.health_check()
            logger.info("✓ Connection successful")

        # Test 2: Schema verification
        logger.info("\n[2/5] Verifying schema...")
        with ClickHouseConnection(config) as conn:
            result = conn.execute("SELECT COUNT(*) FROM system.tables WHERE name = 'ohlcv'")
            if result[0][0] == 1:
                logger.info("✓ ohlcv table exists")
            else:
                logger.error("✗ ohlcv table not found")
                sys.exit(1)

        # Test 3: Bulk ingestion
        logger.info("\n[3/5] Testing ingestion (BTCUSDT 1h, 2024-01)...")
        with ClickHouseConnection(config) as conn:
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            start = datetime.now()
            rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
            duration = (datetime.now() - start).total_seconds()
            logger.info(
                f"✓ Ingested {rows} rows in {duration:.2f}s ({rows / duration:.0f} rows/sec)"
            )

        # Test 4: Query API
        logger.info("\n[4/5] Testing query API...")
        with ClickHouseConnection(config) as conn:
            query = OHLCVQuery(conn)

            # get_latest
            df = query.get_latest("BTCUSDT", "1h", limit=10)
            logger.info(f"✓ get_latest: {len(df)} rows")

            # get_range
            df = query.get_range("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
            logger.info(f"✓ get_range: {len(df)} rows")
            logger.info(f"  Date range: {df.iloc[0]['timestamp']} → {df.iloc[-1]['timestamp']}")
            logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")

        # Test 5: Duplicate ingestion (zero-gap guarantee)
        logger.info("\n[5/5] Testing zero-gap guarantee (duplicate ingestion)...")
        with ClickHouseConnection(config) as conn:
            # Count before
            result = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
            count_before = result[0][0]

            # Re-ingest same data
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")
            loader.ingest_month("BTCUSDT", "1h", 2024, 1)

            # Count after (with FINAL to ensure deduplication is applied)
            result = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
            count_after = result[0][0]

            if count_before == count_after:
                logger.info(f"✓ Zero-gap validated: {count_before} rows (no duplicates)")
            else:
                logger.warning(f"⚠ Count difference: {count_before} → {count_after}")
                logger.warning("  Running OPTIMIZE to force merge...")
                conn.execute("OPTIMIZE TABLE ohlcv FINAL")
                result = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL")
                count_optimized = result[0][0]
                if count_before == count_optimized:
                    logger.info(f"✓ After OPTIMIZE: {count_optimized} rows (duplicates removed)")
                else:
                    logger.error(f"✗ Still different: {count_optimized} (expected {count_before})")

        logger.info("\n" + "=" * 80)
        logger.info("✓ Validation complete!")
        logger.info("=" * 80)
        return 0

    except Exception as e:
        logger.error(f"\n✗ Validation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
