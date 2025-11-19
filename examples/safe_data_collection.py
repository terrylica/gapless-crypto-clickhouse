#!/usr/bin/env python3
"""
Safe Data Collection Example with Error Handling

This example demonstrates proper error handling and safe date range usage
to avoid common pitfalls when collecting cryptocurrency data.

Key Principles:
1. Use historical dates only (not future dates)
2. Respect symbol listing dates
3. Handle errors gracefully
4. Provide informative error messages
"""

import warnings
from datetime import datetime, timedelta

from gapless_crypto_clickhouse import BinancePublicDataCollector


def safe_data_collection_example():
    """Example with proper error handling and safe date ranges"""
    print("🛡️  Safe Data Collection Example")
    print("=" * 50)

    # Known symbols with their listing dates (for reference)
    # BTCUSDT: 2017-08-17, ETHUSDT: 2017-08-17
    # SOLUSDT: 2020-08-11, ADAUSDT: 2018-04-17

    # Calculate safe date range (1 week of recent historical data)
    today = datetime.now().date()
    end_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")  # One week ago
    start_date = (today - timedelta(days=14)).strftime("%Y-%m-%d")  # Two weeks ago

    print(f"📅 Safe date range: {start_date} to {end_date}")
    print("   (Avoids future dates and uses recently confirmed data)")
    print()

    for symbol in ["BTCUSDT", "ETHUSDT"]:
        print(f"🚀 Collecting {symbol} data...")

        try:
            # Catch warnings about date issues
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                collector = BinancePublicDataCollector(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )

                # Display any warnings
                if w:
                    for warning in w:
                        print(f"⚠️  Warning: {warning.message}")

            # Collect data
            timeframes = ["1h", "4h"]
            results = collector.collect_multiple_timeframes(timeframes)

            if results:
                print(f"✅ {symbol} collection successful!")
                for tf, filepath in results.items():
                    size_mb = filepath.stat().st_size / (1024 * 1024)
                    print(f"   {tf}: {filepath.name} ({size_mb:.1f} MB)")
            else:
                print(f"❌ {symbol} collection failed")

        except Exception as e:
            print(f"❌ Error collecting {symbol}: {e}")
            print("   This might be due to:")
            print("   - Network connectivity issues")
            print("   - Binance server temporarily unavailable")
            print("   - Data not yet available for requested dates")

        print()


def demonstrate_date_validation():
    """Demonstrate what happens with problematic date ranges"""
    print("🔍 Date Validation Examples")
    print("=" * 40)

    # Example 1: Future date (will trigger warning)
    print("Example 1: Future date (should trigger warning)")
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            BinancePublicDataCollector(
                symbol="BTCUSDT",
                start_date="2030-01-01",  # Future date - demonstrates warning
                end_date="2030-01-31",
            )

            if w:
                for warning in w:
                    print(f"⚠️  Expected warning: {warning.message}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()

    # Example 2: Date before symbol listing (will trigger warning)
    print("Example 2: Date before SOLUSDT listing (should trigger warning)")
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            BinancePublicDataCollector(
                symbol="SOLUSDT",  # Listed 2020-08-11 - demonstrates validation
                start_date="2019-01-01",  # Before listing
                end_date="2019-01-31",
            )

            if w:
                for warning in w:
                    print(f"⚠️  Expected warning: {warning.message}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print()


def main():
    """Run all examples"""
    print("🚀 Gapless Crypto Data - Safe Collection Examples")
    print("=" * 60)
    print()

    # Run safe collection example
    safe_data_collection_example()

    # Demonstrate validation
    demonstrate_date_validation()

    print("💡 Key Takeaways:")
    print("   1. Always use historical dates (not future)")
    print("   2. Check symbol listing dates before requesting early data")
    print("   3. Use recent historical data (1-2 weeks old) for reliability")
    print("   4. Handle warnings and exceptions gracefully")
    print("   5. Test with small date ranges first")


if __name__ == "__main__":
    main()
