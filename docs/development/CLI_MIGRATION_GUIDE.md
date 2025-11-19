---
version: "1.0.0"
last_updated: "2025-10-28"
canonical_source: true
supersedes: []
---

# CLI Migration Guide

⚠️ **The CLI is deprecated and will be removed in v4.0.0.**

This guide provides side-by-side examples to help you migrate from the deprecated CLI to the Python API.

## Table of Contents

- [Why Migrate?](#why-migrate)
- [Quick Migration Examples](#quick-migration-examples)
- [Common Patterns](#common-patterns)
- [Advanced Use Cases](#advanced-use-cases)
- [Benefits of Python API](#benefits-of-python-api)

---

## Why Migrate?

The Python API offers several advantages over the CLI:

1. **Better Integration**: Use data directly in your Python scripts without file I/O
2. **More Flexible**: Programmatic access to all package features
3. **Better Error Handling**: Catch and handle exceptions in your code
4. **Type Safety**: Full IDE autocomplete and type checking support
5. **Composable**: Easily combine with pandas, numpy, and other libraries

---

## Quick Migration Examples

### Basic Data Collection

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol BTCUSDT --timeframes 1h
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

# Fetch data directly as pandas DataFrame
df = gcd.fetch_data("BTCUSDT", timeframe="1h")
print(f"Collected {len(df)} bars")
```

### Multiple Timeframes

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol ETHUSDT --timeframes 1h,4h,1d
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

timeframes = ["1h", "4h", "1d"]
for tf in timeframes:
    df = gcd.fetch_data("ETHUSDT", timeframe=tf)
    print(f"{tf}: {len(df)} bars")
```

### Date Range Collection

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol BTCUSDT --timeframes 1h \
  --start 2023-01-01 --end 2023-12-31
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

df = gcd.download(
    "BTCUSDT",
    timeframe="1h",
    start="2023-01-01",
    end="2023-12-31"
)
print(f"Collected {len(df)} bars from 2023")
```

### Multiple Symbols

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1h
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
results = {}

for symbol in symbols:
    df = gcd.fetch_data(symbol, timeframe="1h")
    results[symbol] = df
    print(f"{symbol}: {len(df)} bars")
```

---

## Common Patterns

### Pattern 1: Custom Output Directory

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol BTCUSDT --timeframes 1h \
  --output-dir ./crypto_data
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd
from pathlib import Path

# Fetch data and save manually
df = gcd.fetch_data("BTCUSDT", timeframe="1h")

# Save to custom location
output_dir = Path("./crypto_data")
output_dir.mkdir(exist_ok=True)
df.to_csv(output_dir / "BTCUSDT_1h.csv", index=False)

# Or use save_parquet for better performance
gcd.save_parquet(df, output_dir / "BTCUSDT_1h.parquet")
```

### Pattern 2: Gap Filling

**CLI (Deprecated)**:

```bash
gapless-crypto-data --fill-gaps --directory ./data
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

# Fill gaps in all CSV files in directory
results = gcd.fill_gaps("./data")

print(f"Processed {results['files_processed']} files")
print(f"Filled {results['gaps_filled']}/{results['gaps_detected']} gaps")
print(f"Success rate: {results['success_rate']:.1%}")
```

### Pattern 3: Ultra-High Frequency Data

**CLI (Deprecated)**:

```bash
gapless-crypto-data --symbol BTCUSDT --timeframes 1s,1m,3m \
  --start 2024-01-01 --end 2024-01-01
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd

# Collect ultra-high frequency data for a single day
timeframes = ["1s", "1m", "3m"]
start_date = "2024-01-01"
end_date = "2024-01-01"

for tf in timeframes:
    df = gcd.download(
        "BTCUSDT",
        timeframe=tf,
        start=start_date,
        end=end_date
    )
    print(f"{tf}: {len(df):,} bars ({df.memory_usage(deep=True).sum() / 1024**2:.1f} MB)")
```

---

## Advanced Use Cases

### Batch Processing with Progress Tracking

**CLI (Deprecated)**:

```bash
# Limited progress information
gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1h,4h,1d
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd
from datetime import datetime

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
timeframes = ["1h", "4h", "1d"]

results = {}
total = len(symbols) * len(timeframes)
current = 0

for symbol in symbols:
    results[symbol] = {}
    for tf in timeframes:
        current += 1
        print(f"[{current}/{total}] Collecting {symbol} {tf}...")

        df = gcd.fetch_data(symbol, timeframe=tf, limit=1000)
        results[symbol][tf] = {
            'bars': len(df),
            'first_date': df['date'].min(),
            'last_date': df['date'].max(),
        }

        print(f"  ✅ {len(df)} bars ({df['date'].min()} to {df['date'].max()})")

print("\n📊 Collection Summary:")
for symbol, tfs in results.items():
    total_bars = sum(data['bars'] for data in tfs.values())
    print(f"{symbol}: {total_bars:,} total bars across {len(tfs)} timeframes")
```

### Data Analysis Integration

**CLI (Deprecated)**:

```bash
# CLI requires saving to file then loading in Python
gapless-crypto-data --symbol BTCUSDT --timeframes 1h --output-dir ./data
# Then in Python: df = pd.read_csv("./data/BTCUSDT_1h.csv")
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd
import pandas as pd
import numpy as np

# Fetch data directly
df = gcd.fetch_data("BTCUSDT", timeframe="1h", limit=1000)

# Immediate analysis without file I/O
df['returns'] = df['close'].pct_change()
df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
df['volatility'] = df['returns'].rolling(24).std() * np.sqrt(24)  # Daily vol

# Market microstructure analysis (11-column format)
df['taker_buy_ratio'] = df['taker_buy_base_asset_volume'] / df['volume']
df['avg_trade_size'] = df['volume'] / df['number_of_trades']

print(f"Average daily volatility: {df['volatility'].mean():.2%}")
print(f"Taker buy pressure: {df['taker_buy_ratio'].mean():.2%}")
print(f"Average trade size: {df['avg_trade_size'].mean():.4f} BTC")
```

### Error Handling and Retry Logic

**CLI (Deprecated)**:

```bash
# Limited error handling
gapless-crypto-data --symbol BTCUSDT --timeframes 1h
```

**Python API (Recommended)**:

```python
import gapless_crypto_data as gcd
from gapless_crypto_data import NetworkError, DataCollectionError
import time

def fetch_with_retry(symbol, timeframe, max_retries=3):
    """Fetch data with retry logic"""
    for attempt in range(max_retries):
        try:
            df = gcd.fetch_data(symbol, timeframe=timeframe)
            print(f"✅ Successfully fetched {symbol} {timeframe}")
            return df
        except NetworkError as e:
            print(f"⚠️  Network error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
        except DataCollectionError as e:
            print(f"❌ Data collection error: {e}")
            return None

    print(f"❌ Failed after {max_retries} attempts")
    return None

# Use the retry function
df = fetch_with_retry("BTCUSDT", "1h")
if df is not None:
    print(f"Collected {len(df)} bars")
```

---

## Benefits of Python API

### 1. Direct DataFrame Access

No need to save and load files:

```python
import gapless_crypto_data as gcd

# Immediate access to pandas DataFrame
df = gcd.fetch_data("BTCUSDT", timeframe="1h")

# Use directly with pandas operations
recent_high = df.tail(100)['high'].max()
recent_low = df.tail(100)['low'].min()
```

### 2. Integration with Data Science Stack

```python
import gapless_crypto_data as gcd
import matplotlib.pyplot as plt
import seaborn as sns

# Fetch data
df = gcd.fetch_data("BTCUSDT", timeframe="1h", limit=720)  # 30 days

# Immediate visualization
df.set_index('date')['close'].plot(figsize=(12, 6))
plt.title('BTC/USDT Price (30 days)')
plt.show()

# Statistical analysis
print(df[['open', 'high', 'low', 'close', 'volume']].describe())
```

### 3. Programmatic Control

```python
import gapless_crypto_data as gcd
from datetime import datetime, timedelta

# Dynamic date ranges
end_date = datetime.now().date()
start_date = end_date - timedelta(days=30)

df = gcd.download(
    "BTCUSDT",
    timeframe="1h",
    start=str(start_date),
    end=str(end_date)
)

# Conditional logic
if len(df) < 720:
    print(f"⚠️  Warning: Only {len(df)} bars collected (expected 720)")
```

### 4. Testing and Automation

```python
import gapless_crypto_data as gcd
import unittest

class TestDataCollection(unittest.TestCase):
    def test_btc_collection(self):
        """Test BTC data collection"""
        df = gcd.fetch_data("BTCUSDT", timeframe="1h", limit=100)

        self.assertEqual(len(df), 100)
        self.assertIn('close', df.columns)
        self.assertTrue((df['high'] >= df['low']).all())

    def test_gap_detection(self):
        """Test gap detection"""
        results = gcd.fill_gaps("./test_data")
        self.assertIn('gaps_detected', results)

if __name__ == '__main__':
    unittest.main()
```

---

## Migration Timeline

- **v3.3.0** (Current): CLI deprecated with warnings
- **v3.4.0 - v3.9.x** (2025 Q1-Q2): CLI continues to work with deprecation warnings
- **v4.0.0** (2025 Q2): CLI removed completely

We recommend migrating to the Python API as soon as possible to ensure compatibility with future releases.

---

## Need Help?

- **Documentation**: [README.md](../../README.md)
- **Examples**: [examples/](../../examples/)
- **Issues**: [GitHub Issues](https://github.com/terrylica/gapless-crypto-data/issues)

---

**Last Updated**: 2025-10-18
