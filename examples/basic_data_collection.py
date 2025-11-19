#!/usr/bin/env python3
"""
Basic Data Collection Example

This example demonstrates how to collect cryptocurrency data using the
BinancePublicDataCollector for ultra-fast downloads with full 11-column
microstructure format (22x faster than APIs).

IMPORTANT: This example uses safe historical date ranges that are guaranteed
to have data available. Avoid using future dates or dates before symbol listing.
"""

from datetime import datetime, timedelta

from gapless_crypto_clickhouse import BinancePublicDataCollector


def main():
    """Demonstrate basic data collection with safe date ranges"""
    print("🚀 Gapless Crypto Data - Basic Collection Example")
    print("=" * 60)

    # Use safe historical dates (avoid future dates and dates before listing)
    # BTCUSDT has been available since 2017-08-17
    end_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # One week ago
    start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")  # Two weeks ago

    print(f"📅 Using safe date range: {start_date} to {end_date}")
    print("   (This avoids 404 errors from requesting future or unavailable data)")
    print()

    # Initialize collector with safe parameters
    collector = BinancePublicDataCollector(
        symbol="BTCUSDT",  # Known to be available since 2017-08-17
        start_date=start_date,
        end_date=end_date,
    )

    # Collect data for multiple timeframes
    timeframes = ["1h", "4h"]

    print(f"Collecting {collector.symbol} data for {timeframes}")
    print(
        f"Date range: {collector.start_date.strftime('%Y-%m-%d')} to {collector.end_date.strftime('%Y-%m-%d')}"
    )
    print()

    # Collect the data
    results = collector.collect_multiple_timeframes(timeframes)

    if results:
        print("✅ Collection completed successfully!")
        print()
        print("Generated files:")
        for timeframe, filepath in results.items():
            file_size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"  {timeframe}: {filepath.name} ({file_size_mb:.1f} MB)")

            # Show first few rows
            import pandas as pd

            df = pd.read_csv(filepath)
            print(f"    Rows: {len(df)}")
            print(f"    Columns: {len(df.columns)} (Full 11-column microstructure format)")
            print(f"    Date range: {df.iloc[0]['date']} to {df.iloc[-1]['date']}")
            print()
    else:
        print("❌ Collection failed")


if __name__ == "__main__":
    main()
