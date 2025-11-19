#!/usr/bin/env python3
"""
Complete Workflow Example

This example demonstrates the complete workflow of the gapless-crypto-data package:
1. Ultra-fast data collection from Binance public repository with 11-column microstructure format
2. Gap detection and analysis
3. Gap filling with authentic API-first validation
4. Data validation and quality checks for all 11 columns
"""

import pandas as pd

from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller


def collect_data_sample():
    """Collect a small sample of data for demonstration"""
    print("📊 Step 1: Data Collection")
    print("-" * 40)

    # Initialize collector with a small date range for demo
    collector = BinancePublicDataCollector(
        symbol="ETHUSDT",
        start_date="2024-01-01",
        end_date="2024-01-03",  # Small range for quick demo
    )

    print(f"Collecting {collector.symbol} data...")
    print(
        f"Date range: {collector.start_date.strftime('%Y-%m-%d')} to {collector.end_date.strftime('%Y-%m-%d')}"
    )

    # Collect 1-hour data
    results = collector.collect_multiple_timeframes(["1h"])

    if results:
        csv_file = list(results.values())[0]
        file_size_mb = csv_file.stat().st_size / (1024 * 1024)

        # Load and analyze the data
        df = pd.read_csv(csv_file)

        print("✅ Collection successful!")
        print(f"   File: {csv_file.name} ({file_size_mb:.2f} MB)")
        print(f"   Data points: {len(df)}")
        print(f"   Columns: {len(df.columns)} (Full 11-column microstructure format)")
        print(f"   Date range: {df.iloc[0]['date']} to {df.iloc[-1]['date']}")
        print()

        return csv_file
    else:
        print("❌ Collection failed")
        return None


def analyze_data_quality(csv_file):
    """Analyze data quality and detect gaps"""
    print("🔍 Step 2: Data Quality Analysis")
    print("-" * 40)

    # Initialize gap filler
    gap_filler = UniversalGapFiller()

    # Load data for analysis
    df = pd.read_csv(csv_file)
    print(f"Analyzing {csv_file.name}...")
    print(f"Total records: {len(df)}")

    # Convert dates and analyze time series
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Check for basic data quality issues
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Time span: {df['date'].max() - df['date'].min()}")

    # Expected vs actual data points (assuming 1-hour intervals)
    expected_hours = int((df["date"].max() - df["date"].min()).total_seconds() / 3600) + 1
    actual_points = len(df)

    print(f"Expected data points (1h intervals): {expected_hours}")
    print(f"Actual data points: {actual_points}")

    if actual_points < expected_hours:
        print(f"⚠️  Missing {expected_hours - actual_points} data points")
    else:
        print("✅ No missing data points detected")

    # Detect gaps using the gap filler
    print("\nDetecting gaps with UniversalGapFiller...")
    gaps = gap_filler.detect_all_gaps(csv_file, "1h")

    print(f"Gaps detected: {len(gaps)}")
    if gaps:
        print("Gap details:")
        for i, gap in enumerate(gaps[:3]):  # Show first 3 gaps
            print(f"  Gap {i + 1}: {gap}")
        if len(gaps) > 3:
            print(f"  ... and {len(gaps) - 3} more gaps")
    print()

    return gaps


def fill_gaps_if_needed(csv_file, gaps):
    """Fill gaps if any are detected"""
    if not gaps:
        print("🎉 Step 3: No Gap Filling Needed")
        print("-" * 40)
        print("No gaps detected - data is already complete!")
        print()
        return True

    print("🔧 Step 3: Gap Filling")
    print("-" * 40)

    gap_filler = UniversalGapFiller()

    print(f"Filling {len(gaps)} gaps...")
    filled_count = 0

    for i, gap in enumerate(gaps):
        try:
            print(f"  Filling gap {i + 1}/{len(gaps)}...")
            success = gap_filler.fill_gap(gap, csv_file, "1h")
            if success:
                filled_count += 1
                print("    ✅ Success")
            else:
                print("    ❌ Failed")
        except Exception as e:
            print(f"    ❌ Error: {e}")

    print(f"\nGap filling completed: {filled_count}/{len(gaps)} successful")
    print()

    return filled_count == len(gaps)


def validate_final_data(csv_file):
    """Validate the final dataset"""
    print("✅ Step 4: Final Validation")
    print("-" * 40)

    # Load final data
    df = pd.read_csv(csv_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    print(f"Final dataset: {csv_file.name}")
    print(f"Total records: {len(df)}")
    print(f"Columns: {len(df.columns)} (Full 11-column microstructure format)")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Check data completeness
    expected_hours = int((df["date"].max() - df["date"].min()).total_seconds() / 3600) + 1
    completeness = len(df) / expected_hours * 100

    print(f"Data completeness: {completeness:.1f}%")

    # Check for missing values
    missing_data = df.isnull().sum()
    print("Missing values by column:")
    for col in df.columns:
        if missing_data[col] > 0:
            print(f"  {col}: {missing_data[col]}")
        else:
            print(f"  {col}: 0 (✅)")

    # Basic price data validation
    if all(col in df.columns for col in ["open", "high", "low", "close"]):
        # Check OHLC relationships
        valid_ohlc = (
            (df["high"] >= df["open"])
            & (df["high"] >= df["close"])
            & (df["low"] <= df["open"])
            & (df["low"] <= df["close"])
        ).all()

        print(f"OHLC data validity: {'✅ Valid' if valid_ohlc else '❌ Invalid'}")

    print("\nSample data (first 3 rows):")
    print(df.head(3).to_string(index=False))
    print()


def main():
    """Execute the complete workflow"""
    print("🚀 Gapless Crypto Data - Complete Workflow Demo")
    print("=" * 60)
    print("This demo shows the complete data collection and validation workflow")
    print()

    try:
        # Step 1: Collect data
        csv_file = collect_data_sample()
        if not csv_file:
            print("Demo failed at data collection step")
            return

        # Step 2: Analyze quality
        gaps = analyze_data_quality(csv_file)

        # Step 3: Fill gaps
        success = fill_gaps_if_needed(csv_file, gaps)

        # Step 4: Validate
        validate_final_data(csv_file)

        # Summary
        print("🎯 Workflow Summary")
        print("-" * 40)
        print("✅ Data collection: Success")
        print("✅ Quality analysis: Complete")
        print(f"✅ Gap filling: {'Success' if success else 'Partial'}")
        print("✅ Final validation: Complete")
        print()
        print("🎉 Demo completed successfully!")
        print(f"📁 Final dataset available at: {csv_file}")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
