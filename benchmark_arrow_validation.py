#!/usr/bin/env python3
"""
Arrow Performance Validation Benchmark for v6.0.0 (ADR-0023)

Validates performance claims:
- Target: ≥2x speedup (goal: 3x, 82,000 rows/s)
- Target: ≥50% memory reduction (goal: 75%)

Baseline (v5.0.0 with clickhouse-driver):
- Query speed: 27,432 rows/sec (0.03s for 721 rows)
- Memory: Unknown (not measured)

Compares:
1. Arrow-optimized queries (query_df_arrow)
2. Standard queries (query_df)
3. Multi-query performance
4. Memory profiling
"""

import gc
import time
import traceback
import tracemalloc
from datetime import datetime
from typing import Any, Dict


def measure_memory_mb() -> float:
    """Get current memory usage in MB."""
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def benchmark_arrow_query() -> Dict[str, Any]:
    """Benchmark Arrow-optimized query."""
    print("\n" + "=" * 70)
    print("BENCHMARK 1: Arrow-Optimized Query (query_df_arrow)")
    print("=" * 70)

    try:
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

        gc.collect()
        tracemalloc.start()
        mem_before = measure_memory_mb()

        with ClickHouseConnection() as conn:
            start = time.time()

            # Query with Arrow optimization
            df = conn.query_dataframe(
                """
                SELECT * FROM ohlcv FINAL
                WHERE symbol = 'BTCUSDT'
                  AND timeframe = '1h'
                  AND instrument_type = 'spot'
                  AND timestamp >= '2024-01-01'
                  AND timestamp <= '2024-01-31'
                ORDER BY timestamp
                """
            )

            duration = time.time() - start

        mem_after = measure_memory_mb()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rows = len(df)
        speed = rows / duration if duration > 0 else 0
        mem_used_mb = mem_after - mem_before
        mem_traced_mb = peak / 1024 / 1024

        print("✅ Arrow-optimized query completed")
        print(f"   Rows: {rows:,}")
        print(f"   Duration: {duration:.4f}s")
        print(f"   Speed: {speed:,.0f} rows/sec")
        print(f"   Memory (RSS): {mem_used_mb:.2f} MB")
        print(f"   Memory (traced peak): {mem_traced_mb:.2f} MB")
        print(f"   DataFrame type: {type(df).__module__}.{type(df).__name__}")

        return {
            "method": "Arrow-optimized (query_df_arrow)",
            "rows": rows,
            "duration_s": duration,
            "speed_rows_per_sec": speed,
            "memory_rss_mb": mem_used_mb,
            "memory_traced_mb": mem_traced_mb,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return None


def benchmark_standard_query() -> Dict[str, Any]:
    """Benchmark standard query without explicit Arrow."""
    print("\n" + "=" * 70)
    print("BENCHMARK 2: Standard Query (for comparison)")
    print("=" * 70)

    try:
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

        gc.collect()
        tracemalloc.start()
        mem_before = measure_memory_mb()

        with ClickHouseConnection() as conn:
            start = time.time()

            # Use client.query_df without Arrow (standard pandas conversion)
            df = conn.client.query_df(
                """
                SELECT * FROM ohlcv FINAL
                WHERE symbol = 'BTCUSDT'
                  AND timeframe = '1h'
                  AND instrument_type = 'spot'
                  AND timestamp >= '2024-01-01'
                  AND timestamp <= '2024-01-31'
                ORDER BY timestamp
                """
            )

            duration = time.time() - start

        mem_after = measure_memory_mb()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rows = len(df)
        speed = rows / duration if duration > 0 else 0
        mem_used_mb = mem_after - mem_before
        mem_traced_mb = peak / 1024 / 1024

        print("✅ Standard query completed")
        print(f"   Rows: {rows:,}")
        print(f"   Duration: {duration:.4f}s")
        print(f"   Speed: {speed:,.0f} rows/sec")
        print(f"   Memory (RSS): {mem_used_mb:.2f} MB")
        print(f"   Memory (traced peak): {mem_traced_mb:.2f} MB")

        return {
            "method": "Standard (query_df)",
            "rows": rows,
            "duration_s": duration,
            "speed_rows_per_sec": speed,
            "memory_rss_mb": mem_used_mb,
            "memory_traced_mb": mem_traced_mb,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return None


def benchmark_large_query() -> Dict[str, Any]:
    """Benchmark large query (full year)."""
    print("\n" + "=" * 70)
    print("BENCHMARK 3: Large Query (1 year, Arrow-optimized)")
    print("=" * 70)

    try:
        from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

        gc.collect()
        tracemalloc.start()
        mem_before = measure_memory_mb()

        with ClickHouseConnection() as conn:
            start = time.time()

            df = conn.query_dataframe(
                """
                SELECT * FROM ohlcv FINAL
                WHERE symbol = 'BTCUSDT'
                  AND timeframe = '1h'
                  AND instrument_type = 'spot'
                  AND timestamp >= '2024-01-01'
                  AND timestamp <= '2024-12-31'
                ORDER BY timestamp
                """
            )

            duration = time.time() - start

        mem_after = measure_memory_mb()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rows = len(df)
        speed = rows / duration if duration > 0 else 0
        mem_used_mb = mem_after - mem_before
        mem_traced_mb = peak / 1024 / 1024

        print("✅ Large query completed")
        print(f"   Rows: {rows:,}")
        print(f"   Duration: {duration:.4f}s")
        print(f"   Speed: {speed:,.0f} rows/sec")
        print(f"   Memory (RSS): {mem_used_mb:.2f} MB")
        print(f"   Memory (traced peak): {mem_traced_mb:.2f} MB")

        return {
            "method": "Large query (1 year, Arrow)",
            "rows": rows,
            "duration_s": duration,
            "speed_rows_per_sec": speed,
            "memory_rss_mb": mem_used_mb,
            "memory_traced_mb": mem_traced_mb,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return None


def benchmark_query_ohlcv() -> Dict[str, Any]:
    """Benchmark query_ohlcv() API."""
    print("\n" + "=" * 70)
    print("BENCHMARK 4: query_ohlcv() API (cached)")
    print("=" * 70)

    try:
        from gapless_crypto_clickhouse import query_ohlcv

        gc.collect()
        tracemalloc.start()
        mem_before = measure_memory_mb()

        start = time.time()

        df = query_ohlcv(
            "BTCUSDT",
            "1h",
            "2024-01-01",
            "2024-01-31",
            auto_ingest=False,
            fill_gaps=False,
        )

        duration = time.time() - start

        mem_after = measure_memory_mb()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rows = len(df)
        speed = rows / duration if duration > 0 else 0
        mem_used_mb = mem_after - mem_before
        mem_traced_mb = peak / 1024 / 1024

        print("✅ query_ohlcv() completed")
        print(f"   Rows: {rows:,}")
        print(f"   Duration: {duration:.4f}s")
        print(f"   Speed: {speed:,.0f} rows/sec")
        print(f"   Memory (RSS): {mem_used_mb:.2f} MB")
        print(f"   Memory (traced peak): {mem_traced_mb:.2f} MB")

        return {
            "method": "query_ohlcv() API",
            "rows": rows,
            "duration_s": duration,
            "speed_rows_per_sec": speed,
            "memory_rss_mb": mem_used_mb,
            "memory_traced_mb": mem_traced_mb,
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return None


def print_summary(results, baseline_speed=27432):
    """Print summary and validation."""
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)

    results = [r for r in results if r is not None]

    if not results:
        print("⚠️  No results to display")
        return

    # Header
    print(f"\n{'Method':<40} {'Rows':>10} {'Time (s)':>10} {'Rows/s':>12} {'Mem (MB)':>10}")
    print("-" * 90)

    # Results
    for r in results:
        print(
            f"{r['method']:<40} {r['rows']:>10,} {r['duration_s']:>10.4f} "
            f"{r['speed_rows_per_sec']:>12,.0f} {r['memory_traced_mb']:>10.2f}"
        )

    # Validation against baseline
    print("\n" + "=" * 70)
    print("VALIDATION AGAINST BASELINE")
    print("=" * 70)
    print(f"Baseline (v5.0.0 clickhouse-driver): {baseline_speed:,} rows/sec")

    arrow_result = next((r for r in results if "Arrow-optimized" in r["method"]), None)
    if arrow_result:
        speedup = arrow_result["speed_rows_per_sec"] / baseline_speed
        print(f"\nArrow-optimized (v6.0.0): {arrow_result['speed_rows_per_sec']:,.0f} rows/sec")
        print(f"Speedup: {speedup:.2f}x")

        if speedup >= 3.0:
            print("✅ EXCELLENT: Achieved 3x speedup goal!")
        elif speedup >= 2.0:
            print("✅ PASS: Achieved 2x speedup target")
        else:
            print(f"⚠️  WARNING: Speedup {speedup:.2f}x < 2x target")

    # Memory comparison
    standard_result = next((r for r in results if "Standard" in r["method"]), None)
    if arrow_result and standard_result:
        mem_reduction = (
            (standard_result["memory_traced_mb"] - arrow_result["memory_traced_mb"])
            / standard_result["memory_traced_mb"]
            * 100
        )
        print("\nMemory Comparison:")
        print(f"  Standard: {standard_result['memory_traced_mb']:.2f} MB")
        print(f"  Arrow: {arrow_result['memory_traced_mb']:.2f} MB")
        print(f"  Reduction: {mem_reduction:.1f}%")

        if mem_reduction >= 75:
            print("✅ EXCELLENT: Achieved 75% memory reduction goal!")
        elif mem_reduction >= 50:
            print("✅ PASS: Achieved 50% memory reduction target")
        else:
            print(f"⚠️  INFO: Memory reduction {mem_reduction:.1f}% (may vary by dataset size)")


def main():
    """Run all benchmarks."""
    print("=" * 70)
    print("Arrow Performance Validation - ADR-0023")
    print(f"Started: {datetime.now()}")
    print("=" * 70)

    results = []

    # Run benchmarks
    results.append(benchmark_arrow_query())
    results.append(benchmark_standard_query())
    results.append(benchmark_large_query())
    results.append(benchmark_query_ohlcv())

    # Summary and validation
    print_summary(results)

    print(f"\n✅ Benchmarks completed at {datetime.now()}")
    print("\nResults saved to: logs/0023-arrow-migration-*.log")


if __name__ == "__main__":
    main()
