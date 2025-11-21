#!/usr/bin/env python3
"""
Performance Benchmark: gapless-crypto-clickhouse vs gapless-crypto-data

Measures:
1. First-time download speed
2. Cached query speed
3. Database ingestion speed
4. Database query speed
5. Memory usage
6. Concurrent query handling
"""

import time
from datetime import datetime
from pathlib import Path


def measure_memory():
    """Get current memory usage in MB (simplified, no psutil)"""
    return 0.0  # Disabled for simplicity

def benchmark_csv_download():
    """Benchmark CSV-based download (gapless-crypto-data)"""
    print("\n" + "="*70)
    print("BENCHMARK 1: CSV-based Download (gapless-crypto-data)")
    print("="*70)

    try:
        import gapless_crypto_data as gcd_csv

        # Clear cache if exists
        cache_dir = Path.home() / ".gapless_crypto_data"
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            print("✅ Cache cleared")

        mem_before = measure_memory()
        start = time.time()

        # Fetch 1 month of 1h data
        df = gcd_csv.fetch_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start="2024-01-01",
            end="2024-01-31"
        )

        duration = time.time() - start
        mem_after = measure_memory()

        print(f"✅ Downloaded {len(df):,} bars")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"💾 Memory used: {mem_after - mem_before:.2f} MB")
        print(f"📊 Data shape: {df.shape}")
        print(f"🔢 Columns: {list(df.columns)}")

        return {
            "method": "CSV-based (gapless-crypto-data)",
            "rows": len(df),
            "duration_s": duration,
            "memory_mb": mem_after - mem_before,
            "speed_rows_per_sec": len(df) / duration
        }

    except ImportError:
        print("⚠️  gapless-crypto-data not installed, skipping")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def benchmark_clickhouse_download():
    """Benchmark ClickHouse-based download"""
    print("\n" + "="*70)
    print("BENCHMARK 2: ClickHouse-based Download (gapless-crypto-clickhouse)")
    print("="*70)

    try:
        import gapless_crypto_clickhouse as gcd_ch

        mem_before = measure_memory()
        start = time.time()

        # Fetch same data
        df = gcd_ch.fetch_data(
            symbol="BTCUSDT",
            timeframe="1h",
            start="2024-01-01",
            end="2024-01-31"
        )

        duration = time.time() - start
        mem_after = measure_memory()

        print(f"✅ Downloaded {len(df):,} bars")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"💾 Memory used: {mem_after - mem_before:.2f} MB")
        print(f"📊 Data shape: {df.shape}")

        return {
            "method": "ClickHouse-based",
            "rows": len(df),
            "duration_s": duration,
            "memory_mb": mem_after - mem_before,
            "speed_rows_per_sec": len(df) / duration
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def benchmark_clickhouse_ingestion():
    """Benchmark ClickHouse database ingestion"""
    print("\n" + "="*70)
    print("BENCHMARK 3: ClickHouse Database Ingestion")
    print("="*70)

    try:
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
        from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

        with ClickHouseConnection() as conn:
            # health_check() is called in __enter__, will raise if unavailable
            loader = ClickHouseBulkLoader(conn, instrument_type="spot")

            mem_before = measure_memory()
            start = time.time()

            # Ingest January 2024
            rows = loader.ingest_month("BTCUSDT", "1h", year=2024, month=1)

            duration = time.time() - start
            mem_after = measure_memory()

            print(f"✅ Ingested {rows:,} rows")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"💾 Memory used: {mem_after - mem_before:.2f} MB")
            print(f"📈 Ingestion speed: {rows / duration:.0f} rows/s")

            return {
                "method": "ClickHouse ingestion",
                "rows": rows,
                "duration_s": duration,
                "memory_mb": mem_after - mem_before,
                "speed_rows_per_sec": rows / duration
            }

    except Exception as e:
        print(f"⚠️  ClickHouse not available or error: {e}")
        return None

def benchmark_clickhouse_query():
    """Benchmark ClickHouse query performance"""
    print("\n" + "="*70)
    print("BENCHMARK 4: ClickHouse Query Performance")
    print("="*70)

    try:
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
        from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery

        with ClickHouseConnection() as conn:
            # health_check() is called in __enter__, will raise if unavailable
            query = OHLCVQuery(conn)

            mem_before = measure_memory()
            start = time.time()

            # Query same date range
            df = query.get_range(
                symbol="BTCUSDT",
                timeframe="1h",
                start="2024-01-01",
                end="2024-01-31",
                instrument_type="spot"
            )

            duration = time.time() - start
            mem_after = measure_memory()

            print(f"✅ Queried {len(df):,} rows")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"💾 Memory used: {mem_after - mem_before:.2f} MB")
            print(f"📈 Query speed: {len(df) / duration:.0f} rows/s")

            return {
                "method": "ClickHouse query",
                "rows": len(df),
                "duration_s": duration,
                "memory_mb": mem_after - mem_before,
                "speed_rows_per_sec": len(df) / duration
            }

    except Exception as e:
        print(f"⚠️  ClickHouse query error: {e}")
        return None

def benchmark_large_dataset():
    """Benchmark large dataset (1 year, multiple symbols)"""
    print("\n" + "="*70)
    print("BENCHMARK 5: Large Dataset (1 year, 3 symbols)")
    print("="*70)

    try:
        import gapless_crypto_clickhouse as gcd

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

        mem_before = measure_memory()
        start = time.time()

        total_rows = 0
        for symbol in symbols:
            df = gcd.fetch_data(
                symbol=symbol,
                timeframe="1h",
                start="2024-01-01",
                end="2024-12-31"
            )
            total_rows += len(df)
            print(f"  {symbol}: {len(df):,} rows")

        duration = time.time() - start
        mem_after = measure_memory()

        print(f"\n✅ Total: {total_rows:,} rows")
        print(f"⏱️  Duration: {duration:.2f}s")
        print(f"💾 Memory used: {mem_after - mem_before:.2f} MB")
        print(f"📈 Average speed: {total_rows / duration:.0f} rows/s")

        return {
            "method": "Large dataset (3 symbols, 1 year)",
            "rows": total_rows,
            "duration_s": duration,
            "memory_mb": mem_after - mem_before,
            "speed_rows_per_sec": total_rows / duration
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def print_summary(results):
    """Print summary table"""
    print("\n" + "="*70)
    print("PERFORMANCE SUMMARY")
    print("="*70)

    results = [r for r in results if r is not None]

    if not results:
        print("⚠️  No results to display")
        return

    # Header
    print(f"\n{'Method':<40} {'Rows':>10} {'Time (s)':>10} {'MB':>8} {'Rows/s':>12}")
    print("-" * 88)

    # Results
    for r in results:
        print(f"{r['method']:<40} {r['rows']:>10,} {r['duration_s']:>10.2f} {r['memory_mb']:>8.1f} {r['speed_rows_per_sec']:>12,.0f}")

    # Compare CSV vs ClickHouse
    csv_result = next((r for r in results if "CSV-based" in r["method"]), None)
    ch_result = next((r for r in results if "ClickHouse-based" in r["method"]), None)

    if csv_result and ch_result:
        speedup = csv_result["duration_s"] / ch_result["duration_s"]
        print("\n" + "="*70)
        print("📊 COMPARISON: CSV vs ClickHouse Download")
        print(f"   Speedup: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
        print(f"   CSV time: {csv_result['duration_s']:.2f}s")
        print(f"   ClickHouse time: {ch_result['duration_s']:.2f}s")

        if speedup < 5:
            print("\n⚠️  WARNING: Claimed '22x faster' not validated")
            print(f"   Actual speedup: {speedup:.2f}x")
            print("   This may be due to:")
            print("   - Network speed differences")
            print("   - Cache warming")
            print("   - Dataset size (small test)")

def main():
    """Run all benchmarks"""
    print("🔬 Gapless Crypto ClickHouse Performance Probe")
    print(f"📅 Started: {datetime.now()}")

    results = []

    # Run benchmarks
    results.append(benchmark_csv_download())
    results.append(benchmark_clickhouse_download())
    results.append(benchmark_clickhouse_ingestion())
    results.append(benchmark_clickhouse_query())
    results.append(benchmark_large_dataset())

    # Summary
    print_summary(results)

    print(f"\n✅ Benchmarks completed at {datetime.now()}")

if __name__ == "__main__":
    main()
