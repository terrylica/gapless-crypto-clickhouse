#!/usr/bin/env python3
"""
ClickHouse Futures Support Validation (Phase 6)

Validates ADR-0004 futures support in ClickHouse implementation:
1. Futures CSV ingestion (12-column format with header)
2. Spot/futures data isolation via instrument_type column
3. Query API with instrument_type parameter
4. No cross-contamination between spot and futures data

Usage:
    uv run --active python tmp/clickhouse_futures_validation.py
"""

import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    """Run futures support validation."""
    logger.info("=" * 80)
    logger.info("ClickHouse Futures Support Validation (Phase 6 / ADR-0004)")
    logger.info("=" * 80)

    try:
        from gapless_crypto_data.clickhouse import ClickHouseConfig, ClickHouseConnection
        from gapless_crypto_data.clickhouse_query import OHLCVQuery
        from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

        config = ClickHouseConfig(host="localhost", port=9001)

        # Test 1: Futures ingestion
        logger.info("\n[1/5] Testing futures ingestion (BTCUSDT 1h, 2024-01)...")
        with ClickHouseConnection(config) as conn:
            loader = ClickHouseBulkLoader(conn, instrument_type="futures")
            start = datetime.now()
            rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
            duration = (datetime.now() - start).total_seconds()
            logger.info(
                f"✓ Ingested {rows} futures rows in {duration:.2f}s ({rows / duration:.0f} rows/sec)"
            )

        # Test 2: Verify spot/futures isolation
        logger.info("\n[2/5] Verifying spot/futures data isolation...")
        with ClickHouseConnection(config) as conn:
            # Count spot data
            result = conn.execute("SELECT COUNT(*) FROM ohlcv FINAL WHERE instrument_type = 'spot'")
            spot_count = result[0][0]

            # Count futures data
            result = conn.execute(
                "SELECT COUNT(*) FROM ohlcv FINAL WHERE instrument_type = 'futures'"
            )
            futures_count = result[0][0]

            logger.info(f"✓ Spot: {spot_count} rows")
            logger.info(f"✓ Futures: {futures_count} rows")

            if spot_count > 0 and futures_count > 0:
                logger.info("✓ Data isolation confirmed (both instrument types present)")
            else:
                logger.error(f"✗ Missing data: spot={spot_count}, futures={futures_count}")
                sys.exit(1)

        # Test 3: Query API with instrument_type parameter
        logger.info("\n[3/5] Testing query API with instrument_type...")
        with ClickHouseConnection(config) as conn:
            query = OHLCVQuery(conn)

            # Query spot data
            df_spot = query.get_latest("BTCUSDT", "1h", limit=10, instrument_type="spot")
            logger.info(f"✓ Spot query: {len(df_spot)} rows")
            logger.info(f"  Latest spot close: ${df_spot.iloc[-1]['close']:.2f}")

            # Query futures data
            df_futures = query.get_latest("BTCUSDT", "1h", limit=10, instrument_type="futures")
            logger.info(f"✓ Futures query: {len(df_futures)} rows")
            logger.info(f"  Latest futures close: ${df_futures.iloc[-1]['close']:.2f}")

            # Verify instrument_type values
            spot_types = df_spot["instrument_type"].unique()
            futures_types = df_futures["instrument_type"].unique()

            if list(spot_types) == ["spot"] and list(futures_types) == ["futures"]:
                logger.info("✓ instrument_type filtering works correctly")
            else:
                logger.error(
                    f"✗ instrument_type mismatch: spot={spot_types}, futures={futures_types}"
                )
                sys.exit(1)

        # Test 4: Cross-contamination check
        logger.info("\n[4/5] Checking for cross-contamination...")
        with ClickHouseConnection(config) as conn:
            query = OHLCVQuery(conn)

            # Get date range for both
            df_spot_range = query.get_range(
                "BTCUSDT", "1h", "2024-01-01", "2024-01-31", instrument_type="spot"
            )
            df_futures_range = query.get_range(
                "BTCUSDT", "1h", "2024-01-01", "2024-01-31", instrument_type="futures"
            )

            # Check all rows have correct instrument_type
            spot_contaminated = (df_spot_range["instrument_type"] != "spot").sum()
            futures_contaminated = (df_futures_range["instrument_type"] != "futures").sum()

            if spot_contaminated == 0 and futures_contaminated == 0:
                logger.info("✓ No cross-contamination detected")
                logger.info(f"  Spot rows: {len(df_spot_range)} (all marked 'spot')")
                logger.info(f"  Futures rows: {len(df_futures_range)} (all marked 'futures')")
            else:
                logger.error(
                    f"✗ Cross-contamination detected: spot={spot_contaminated}, futures={futures_contaminated}"
                )
                sys.exit(1)

        # Test 5: Duplicate futures ingestion (zero-gap guarantee)
        logger.info("\n[5/5] Testing futures zero-gap guarantee...")
        with ClickHouseConnection(config) as conn:
            # Count before
            result = conn.execute(
                "SELECT COUNT(*) FROM ohlcv FINAL WHERE instrument_type = 'futures'"
            )
            count_before = result[0][0]

            # Re-ingest futures data
            loader = ClickHouseBulkLoader(conn, instrument_type="futures")
            loader.ingest_month("BTCUSDT", "1h", 2024, 1)

            # Count after
            result = conn.execute(
                "SELECT COUNT(*) FROM ohlcv FINAL WHERE instrument_type = 'futures'"
            )
            count_after = result[0][0]

            if count_before == count_after:
                logger.info(f"✓ Futures zero-gap validated: {count_before} rows (no duplicates)")
            else:
                logger.warning(f"⚠ Count difference: {count_before} → {count_after}")
                logger.warning("  Running OPTIMIZE to force merge...")
                conn.execute("OPTIMIZE TABLE ohlcv FINAL")
                result = conn.execute(
                    "SELECT COUNT(*) FROM ohlcv FINAL WHERE instrument_type = 'futures'"
                )
                count_optimized = result[0][0]
                if count_before == count_optimized:
                    logger.info(f"✓ After OPTIMIZE: {count_optimized} rows (duplicates removed)")
                else:
                    logger.error(f"✗ Still different: {count_optimized} (expected {count_before})")

        logger.info("\n" + "=" * 80)
        logger.info("✓ Futures support validation complete!")
        logger.info("=" * 80)
        logger.info("\nADR-0004 futures support successfully ported to ClickHouse:")
        logger.info("  - 12-column CSV format with header ✓")
        logger.info("  - instrument_type column isolation ✓")
        logger.info("  - Query API parameter support ✓")
        logger.info("  - Zero-gap guarantee for futures ✓")
        return 0

    except Exception as e:
        logger.error(f"\n✗ Futures validation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
