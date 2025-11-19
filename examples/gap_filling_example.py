#!/usr/bin/env python3
"""
Gap Filling Example

This example demonstrates how to detect and fill gaps in cryptocurrency data
using the UniversalGapFiller with authentic Binance API data sources.
"""

from pathlib import Path

import pandas as pd

from gapless_crypto_clickhouse import UniversalGapFiller


def create_sample_data_with_gaps():
    """Create sample CSV data with intentional gaps for demonstration"""
    print("Creating sample data with gaps for demonstration...")

    # Create hourly data with gaps
    dates = pd.date_range("2024-01-01", periods=48, freq="1h")
    data = pd.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i for i in range(48)],
            "high": [105.0 + i for i in range(48)],
            "low": [95.0 + i for i in range(48)],
            "close": [102.0 + i for i in range(48)],
            "volume": [1000.0] * 48,
        }
    )

    # Remove some rows to create gaps
    data_with_gaps = data.drop([10, 11, 12, 25, 26, 27, 40])

    # Save to CSV
    sample_file = Path("sample_btc_1h_with_gaps.csv")
    data_with_gaps.to_csv(sample_file, index=False)

    print(f"✅ Created sample file: {sample_file}")
    print(f"   Original data points: {len(data)}")
    print(f"   Data with gaps: {len(data_with_gaps)}")
    print(f"   Missing points: {len(data) - len(data_with_gaps)}")
    print()

    return sample_file


def main():
    """Demonstrate gap detection and filling"""
    print("🔧 Gapless Crypto Data - Gap Filling Example")
    print("=" * 60)

    # Create sample data
    sample_file = create_sample_data_with_gaps()

    # Initialize gap filler
    gap_filler = UniversalGapFiller()

    # Detect gaps
    print("Detecting gaps...")
    gaps = gap_filler.detect_all_gaps(sample_file, "1h")

    print("✅ Gap detection completed")
    print(f"   Found {len(gaps)} gaps")
    print()

    if gaps:
        print("Gap details:")
        for i, gap in enumerate(gaps):
            print(f"  Gap {i + 1}: {gap}")
        print()

        # Fill the first gap as demonstration
        print("Filling gaps...")
        filled_count = 0

        for gap in gaps:
            try:
                success = gap_filler.fill_gap(gap, sample_file, "1h")
                if success:
                    filled_count += 1
                    print(f"  ✅ Filled gap: {gap}")
                else:
                    print(f"  ❌ Failed to fill gap: {gap}")
            except Exception as e:
                print(f"  ❌ Error filling gap {gap}: {e}")

        print()
        print(f"Successfully filled {filled_count} out of {len(gaps)} gaps")

        # Verify the results
        print("Verifying results...")
        final_data = pd.read_csv(sample_file)
        print(f"  Final data points: {len(final_data)}")

        # Check for remaining gaps
        remaining_gaps = gap_filler.detect_all_gaps(sample_file, "1h")
        print(f"  Remaining gaps: {len(remaining_gaps)}")

    else:
        print("No gaps found in the data")

    # Cleanup
    if sample_file.exists():
        sample_file.unlink()
        print(f"\n🧹 Cleaned up sample file: {sample_file}")


if __name__ == "__main__":
    main()
