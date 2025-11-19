#!/usr/bin/env python3
"""
Advanced API Examples for gapless-crypto-data

Demonstrates the class-based API for complex workflows and power users.
Shows how to use the full capabilities of the library.
"""

from pathlib import Path

from gapless_crypto_clickhouse import (
    AtomicCSVOperations,
    BinancePublicDataCollector,
    UniversalGapFiller,
)


def example_ultra_high_frequency_collection():
    """Demonstrate ultra-high frequency and extended timeframes"""
    print("⚡ Ultra-High Frequency & Extended Timeframes Example")
    print("=" * 50)

    # Ultra-high frequency collection (1s data)
    print("Collecting 1-second ultra-high frequency data (small date range)...")
    uhf_collector = BinancePublicDataCollector(
        symbol="BTCUSDT",
        start_date="2024-01-01",
        end_date="2024-01-01",  # Single day for 1s data
        output_dir="./uhf_data",
    )

    try:
        uhf_result = uhf_collector.collect_timeframe_data("1s")
        if uhf_result and "dataframe" in uhf_result:
            df = uhf_result["dataframe"]
            print(f"✅ 1s data: {len(df)} bars (ultra-high frequency)")
            print(f"   File size: {uhf_result['filepath'].stat().st_size / (1024 * 1024):.1f} MB")
        else:
            print("⚠️  1s data not available for this date range")
    except Exception as e:
        print(f"⚠️  1s collection: {e}")

    # Extended timeframes collection
    print("\nCollecting extended timeframes (6h, 8h, 12h, 1d)...")
    extended_collector = BinancePublicDataCollector(
        symbol="ETHUSDT",
        start_date="2024-01-01",
        end_date="2024-02-01",
        output_dir="./extended_data",
    )

    extended_timeframes = ["6h", "8h", "12h", "1d"]
    try:
        extended_results = extended_collector.collect_multiple_timeframes(extended_timeframes)
        if extended_results:
            print(f"✅ Extended timeframes: {len(extended_results)} collected")
            for tf, filepath in extended_results.items():
                file_size = filepath.stat().st_size / (1024 * 1024)
                print(f"   {tf}: {filepath.name} ({file_size:.1f} MB)")
        else:
            print("❌ Extended timeframes collection failed")
    except Exception as e:
        print(f"❌ Extended collection error: {e}")

    print("\n💡 Note: All 13 timeframes supported with intelligent fallback system")
    print("   • Ultra-high frequency: 1s (use short date ranges)")
    print("   • Standard: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h")
    print("   • Extended: 6h, 8h, 12h, 1d (automatic monthly-to-daily fallback)")
    print()


def example_advanced_collection():
    """Advanced data collection with custom configuration"""
    print("🎯 Advanced Collection Example")
    print("=" * 50)

    # Initialize collector with custom parameters
    collector = BinancePublicDataCollector(
        symbol="BTCUSDT", start_date="2024-01-01", end_date="2024-01-31", output_dir="./custom_data"
    )

    print("Collector configured:")
    print(f"  Symbol: {collector.symbol}")
    print(
        f"  Date range: {collector.start_date.strftime('%Y-%m-%d')} to {collector.end_date.strftime('%Y-%m-%d')}"
    )
    print(f"  Output directory: {collector.output_dir}")
    print()

    # Collect specific timeframes
    timeframes = ["1h", "4h", "1d"]
    print(f"Collecting timeframes: {timeframes}")

    try:
        results = collector.collect_multiple_timeframes(timeframes)

        if results:
            print(f"✅ Collection successful! Generated {len(results)} files:")
            for timeframe, filepath in results.items():
                file_size = filepath.stat().st_size / (1024 * 1024)
                print(f"  {timeframe}: {filepath.name} ({file_size:.1f} MB)")
        else:
            print("❌ Collection failed")

    except Exception as e:
        print(f"❌ Collection error: {e}")
    print()


def example_single_timeframe_collection():
    """Detailed single timeframe collection with metadata"""
    print("📊 Single Timeframe Collection with Metadata")
    print("=" * 50)

    collector = BinancePublicDataCollector(
        symbol="ETHUSDT", start_date="2024-06-01", end_date="2024-06-30"
    )

    print("Collecting ETHUSDT 1-hour data for June 2024...")

    try:
        result = collector.collect_timeframe_data("1h")

        if result and "dataframe" in result:
            df = result["dataframe"]
            filepath = result["filepath"]
            stats = result["stats"]

            print("✅ Collection successful!")
            print(f"  DataFrame shape: {df.shape}")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  File saved: {filepath}")
            print(f"  Collection stats: {stats}")

            # Analyze the data
            print("\n📈 Data Analysis:")
            print(f"  Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  Total volume: {df['volume'].sum():,.0f}")
            print(f"  Total trades: {df['number_of_trades'].sum():,}")
            print(
                f"  Average taker buy ratio: {(df['taker_buy_base_asset_volume'].sum() / df['volume'].sum()):.1%}"
            )

        else:
            print("❌ Collection failed")

    except Exception as e:
        print(f"❌ Collection error: {e}")
    print()


def example_gap_detection_and_filling():
    """Advanced gap detection and filling"""
    print("🔧 Advanced Gap Detection and Filling")
    print("=" * 50)

    # Initialize gap filler
    gap_filler = UniversalGapFiller()

    # Example with sample data files
    sample_data_dir = Path("./src/gapless_crypto_data/sample_data")

    if sample_data_dir.exists():
        csv_files = list(sample_data_dir.glob("*.csv"))
        print(f"Found {len(csv_files)} CSV files to analyze")

        for csv_file in csv_files[:2]:  # Process first 2 files
            print(f"\nAnalyzing: {csv_file.name}")

            # Extract timeframe from filename
            timeframe = "1h"  # Default
            for tf in [
                "1s",
                "1m",
                "3m",
                "5m",
                "15m",
                "30m",
                "1h",
                "2h",
                "4h",
                "6h",
                "8h",
                "12h",
                "1d",
            ]:
                if f"-{tf}_" in csv_file.name:
                    timeframe = tf
                    break

            print(f"  Detected timeframe: {timeframe}")

            try:
                # Detect gaps
                gaps = gap_filler.detect_all_gaps(csv_file, timeframe)
                print(f"  Gaps detected: {len(gaps)}")

                if gaps:
                    print("  Gap details:")
                    for i, gap in enumerate(gaps[:3]):  # Show first 3 gaps
                        duration = gap["duration"].total_seconds() / 3600  # Hours
                        print(
                            f"    {i + 1}. {gap['start_time']} → {gap['end_time']} ({duration:.1f}h)"
                        )

                    # Fill gaps
                    result = gap_filler.process_file(csv_file, timeframe)
                    print(
                        f"  Fill result: {result['gaps_filled']}/{result['gaps_detected']} gaps filled ({result['success_rate']:.1f}%)"
                    )
                else:
                    print("  ✅ No gaps found - data is complete!")

            except Exception as e:
                print(f"  ❌ Gap analysis error: {e}")

    else:
        print(f"📁 Sample data directory not found: {sample_data_dir}")
        print("💡 Run basic collection first to generate sample data")
    print()


def example_atomic_operations():
    """Demonstrate atomic file operations"""
    print("🛡️ Atomic File Operations Example")
    print("=" * 50)

    # Create test data
    test_data = [
        ["2024-01-01 00:00:00", 42000.0, 42100.0, 41900.0, 42050.0, 100.5],
        ["2024-01-01 01:00:00", 42050.0, 42200.0, 42000.0, 42150.0, 150.3],
        ["2024-01-01 02:00:00", 42150.0, 42300.0, 42100.0, 42250.0, 200.1],
    ]

    test_file = Path("./test_atomic.csv")

    print("Testing atomic CSV operations...")

    try:
        # Initialize atomic operations
        atomic_ops = AtomicCSVOperations()

        # Write test data atomically
        headers = ["date", "open", "high", "low", "close", "volume"]
        atomic_ops.write_csv_atomic(test_file, test_data, headers)
        print(f"✅ Atomic write successful: {test_file}")

        # Read and verify
        if test_file.exists():
            with open(test_file, "r") as f:
                content = f.read()
            print(f"✅ File verification: {len(content)} characters written")

            # Clean up
            test_file.unlink()
            print("✅ Test file cleaned up")
        else:
            print("❌ File was not created")

    except Exception as e:
        print(f"❌ Atomic operations error: {e}")
        # Clean up on error
        if test_file.exists():
            test_file.unlink()
    print()


def example_validation_and_quality_checks():
    """Data validation and quality analysis"""
    print("✅ Data Validation Example")
    print("=" * 50)

    # This example shows how to use the collector's validation features
    collector = BinancePublicDataCollector(symbol="SOLUSDT")

    # Find sample files to validate
    sample_data_dir = Path("./src/gapless_crypto_data/sample_data")

    if sample_data_dir.exists():
        csv_files = list(sample_data_dir.glob("*SOLUSDT*.csv"))

        if csv_files:
            csv_file = csv_files[0]
            print(f"Validating: {csv_file.name}")

            try:
                # Extract timeframe for validation
                timeframe = None
                for tf in [
                    "1s",
                    "1m",
                    "3m",
                    "5m",
                    "15m",
                    "30m",
                    "1h",
                    "2h",
                    "4h",
                    "6h",
                    "8h",
                    "12h",
                    "1d",
                ]:
                    if f"-{tf}_" in csv_file.name:
                        timeframe = tf
                        break

                # Validate the CSV file
                validation_result = collector.validate_csv_file(csv_file, timeframe)

                print("✅ Validation completed:")
                print(f"  Status: {validation_result['validation_summary']}")
                print(f"  Errors: {validation_result['total_errors']}")
                print(f"  Warnings: {validation_result['total_warnings']}")
                print(f"  File size: {validation_result['file_size_mb']:.1f} MB")

                if "structure_validation" in validation_result:
                    structure = validation_result["structure_validation"]
                    print(f"  Format: {structure['format_type']}")

            except Exception as e:
                print(f"❌ Validation error: {e}")
        else:
            print("📁 No SOLUSDT sample files found")
    else:
        print("📁 Sample data directory not found")
    print()


if __name__ == "__main__":
    print("🏆 Gapless Crypto Data - Advanced API Examples")
    print("=" * 60)
    print()

    try:
        example_ultra_high_frequency_collection()
        example_advanced_collection()
        example_single_timeframe_collection()
        example_gap_detection_and_filling()
        example_atomic_operations()
        example_validation_and_quality_checks()

        print("✅ All advanced examples completed!")
        print()
        print("💡 Advanced usage tips:")
        print("   1. Use class-based API for complex workflows")
        print("   2. Leverage validation features for production data")
        print("   3. Implement atomic operations for safe file handling")
        print("   4. Monitor gap filling for data quality assurance")

    except Exception as e:
        print(f"❌ Error running advanced examples: {e}")
        print("💡 Ensure you have proper permissions and network access")
