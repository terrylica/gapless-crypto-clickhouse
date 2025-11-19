#!/usr/bin/env python3
"""
Simple API Examples for gapless-crypto-data

Demonstrates the function-based API for common use cases.
Familiar patterns for intuitive cryptocurrency data collection.
"""

import gapless_crypto_clickhouse as gcd


def example_basic_usage():
    """Basic data fetching examples"""
    print("🚀 Basic Usage Examples")
    print("=" * 50)

    # Get library information
    info = gcd.get_info()
    print(f"Library: {info['name']} v{info['version']}")
    print(f"Description: {info['description']}")
    print()

    # Get available symbols and timeframes
    symbols = gcd.get_supported_symbols()
    timeframes = gcd.get_supported_timeframes()

    print(f"Supported symbols ({len(symbols)}): {symbols}")
    print(f"Available timeframes ({len(timeframes)}): {timeframes}")
    print()


def example_fetch_recent_data():
    """Fetch recent data with limit"""
    print("📊 Fetching Recent Data")
    print("=" * 50)

    # Fetch recent 100 hourly bars for Bitcoin
    print("Fetching recent 100 hourly BTCUSDT bars...")
    df = gcd.fetch_data("BTCUSDT", "1h", limit=100)

    if not df.empty:
        print(f"✅ Fetched {len(df)} bars")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
        print(f"Average volume: {df['volume'].mean():.2f}")
        print(f"Total trades: {df['number_of_trades'].sum():,}")
    else:
        print("❌ No data fetched")
    print()


def example_download_date_range():
    """Download data for specific date range"""
    print("📅 Download with Date Range")
    print("=" * 50)

    # Download ETHUSDT 4-hour data for specific period
    print("Downloading ETHUSDT 4h data (2024-01-01 to 2024-02-01)...")
    df = gcd.download("ETHUSDT", "4h", start="2024-01-01", end="2024-02-01")

    if not df.empty:
        print(f"✅ Downloaded {len(df)} bars")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print("Price statistics:")
        print(f"  Open: ${df['open'].iloc[0]:.2f}")
        print(f"  Close: ${df['close'].iloc[-1]:.2f}")
        print(f"  High: ${df['high'].max():.2f}")
        print(f"  Low: ${df['low'].min():.2f}")

        # Microstructure analysis
        buy_ratio = df["taker_buy_base_asset_volume"].sum() / df["volume"].sum()
        print(f"  Taker buy ratio: {buy_ratio:.1%}")
    else:
        print("❌ No data downloaded")
    print()


def example_multiple_symbols():
    """Work with multiple symbols"""
    print("🔄 Multiple Symbols Example")
    print("=" * 50)

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in symbols:
        print(f"Fetching {symbol} daily data...")
        df = gcd.fetch_data(symbol, "1d", limit=30)  # Last 30 days

        if not df.empty:
            price_change = (
                (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]
            ) * 100
            print(f"  ✅ {symbol}: {len(df)} days, price change: {price_change:+.1f}%")
        else:
            print(f"  ❌ {symbol}: No data")
    print()


def example_gap_filling():
    """Demonstrate gap filling functionality"""
    print("🔧 Gap Filling Example")
    print("=" * 50)

    # Note: This example assumes you have CSV files to process
    # In practice, you would first collect data, then fill gaps

    import os

    data_dir = "./sample_data"

    if os.path.exists(data_dir):
        print(f"Checking for gaps in {data_dir}...")
        results = gcd.fill_gaps(data_dir)

        print("Gap filling results:")
        print(f"  Files processed: {results['files_processed']}")
        print(f"  Gaps detected: {results['gaps_detected']}")
        print(f"  Gaps filled: {results['gaps_filled']}")
        print(f"  Success rate: {results['success_rate']:.1f}%")

        if results["file_results"]:
            print("  Per-file results:")
            for filename, file_result in results["file_results"].items():
                print(
                    f"    {filename}: {file_result['gaps_filled']}/{file_result['gaps_detected']} gaps filled"
                )
    else:
        print(f"📁 Data directory {data_dir} not found")
        print("💡 First collect some data, then run gap filling")
    print()


if __name__ == "__main__":
    print("🎯 Gapless Crypto Data - Simple API Examples")
    print("=" * 60)
    print()

    try:
        example_basic_usage()
        example_fetch_recent_data()
        example_download_date_range()
        example_multiple_symbols()
        example_gap_filling()

        print("✅ All examples completed successfully!")
        print()
        print("💡 Next steps:")
        print("   1. Try modifying the symbols and timeframes")
        print("   2. Experiment with different date ranges")
        print("   3. Use the data for your analysis or backtesting")
        print("   4. Check out advanced_api_examples.py for class-based usage")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        print("💡 Make sure you have internet connectivity for data fetching")
