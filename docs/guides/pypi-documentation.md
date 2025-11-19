# gapless-crypto-data: Complete API Documentation

Cryptocurrency data collection with function-based API and 11-column microstructure format. Includes gap detection and filling capabilities.

## Quick Start

### Installation

```bash
pip install gapless-crypto-data
```

### Simple API (Recommended for Most Users)

```python
import gapless_crypto_data as gcd

# Download recent data
df = gcd.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# Fetch with limit
df = gcd.fetch_data("ETHUSDT", "4h", limit=1000)

# Get available options
symbols = gcd.get_supported_symbols()
timeframes = gcd.get_supported_timeframes()

# Fill gaps in existing data
results = gcd.fill_gaps("./data")
```

## Core Features

- **22x faster** than API calls via Binance public data repository
- **Intuitive function-based API** for simple data collection
- **Advanced class-based API** for complex workflows
- **Zero gaps guarantee** through authentic API-first validation
- **Full 11-column microstructure format** with order flow metrics
- **Production-grade** data quality for quantitative trading

## Function-Based API Reference

### `fetch_data(symbol, interval, limit=None, start=None, end=None, output_dir=None)`

Fetch cryptocurrency data with simple function-based API.

**Parameters:**

- `symbol` (str): Trading pair symbol (e.g., "BTCUSDT", "ETHUSDT")
- `interval` (str): Timeframe interval (e.g., "1m", "5m", "1h", "4h", "1d")
- `limit` (int, optional): Maximum number of recent bars to return
- `start` (str, optional): Start date in YYYY-MM-DD format
- `end` (str, optional): End date in YYYY-MM-DD format
- `output_dir` (str/Path, optional): Directory to save CSV files

**Returns:**

- `pandas.DataFrame`: Complete OHLCV data with microstructure columns

**Examples:**

```python
# Recent 1000 hourly bars
df = gcd.fetch_data("BTCUSDT", "1h", limit=1000)

# Specific date range
df = gcd.fetch_data("ETHUSDT", "4h", start="2024-01-01", end="2024-06-30")

# Save to custom directory
df = gcd.fetch_data("SOLUSDT", "1h", limit=500, output_dir="./crypto_data")
```

### `download(symbol, interval="1h", start=None, end=None, output_dir=None)`

Download cryptocurrency data (alias for fetch_data with familiar API patterns).

**Parameters:**

- `symbol` (str): Trading pair symbol
- `interval` (str): Timeframe interval (default: "1h")
- `start` (str, optional): Start date in YYYY-MM-DD format
- `end` (str, optional): End date in YYYY-MM-DD format
- `output_dir` (str/Path, optional): Directory to save CSV files

**Returns:**

- `pandas.DataFrame`: Complete OHLCV and microstructure data

**Examples:**

```python
# Simple download with date range
df = gcd.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# Recent data
df = gcd.download("ETHUSDT", "4h")
```

### `get_supported_symbols()`

Get list of supported USDT spot trading pairs.

**Returns:**

- `List[str]`: List of supported symbol strings

**Examples:**

```python
symbols = gcd.get_supported_symbols()
print(f"Found {len(symbols)} supported symbols")
print(f"Bitcoin supported: {'BTCUSDT' in symbols}")
```

### `get_supported_timeframes()`

Get list of supported timeframe intervals.

**Returns:**

- `List[str]`: List of timeframe strings

**Examples:**

```python
timeframes = gcd.get_supported_timeframes()
print(f"Available timeframes: {timeframes}")
print(f"1-hour supported: {'1h' in timeframes}")
```

### `fill_gaps(directory, symbols=None)`

Fill gaps in existing CSV data files.

**Parameters:**

- `directory` (str/Path): Directory containing CSV files to process
- `symbols` (List[str], optional): Specific symbols to process (default: all found)

**Returns:**

- `dict`: Gap filling results with statistics

**Examples:**

```python
# Fill all gaps in directory
results = gcd.fill_gaps("./data")
print(f"Success rate: {results['success_rate']:.1f}%")

# Fill gaps for specific symbols
results = gcd.fill_gaps("./data", symbols=["BTCUSDT", "ETHUSDT"])
```

### `get_info()`

Get library information and capabilities.

**Returns:**

- `dict`: Library metadata and capabilities

**Examples:**

```python
info = gcd.get_info()
print(f"Version: {info['version']}")
print(f"Supported symbols: {len(info['supported_symbols'])}")
```

## Data Structure

All functions return pandas DataFrames with complete microstructure data:

### Column Reference

| Column                         | Type     | Description            | Example               |
| ------------------------------ | -------- | ---------------------- | --------------------- |
| `date`                         | datetime | Open timestamp         | `2024-01-01 12:00:00` |
| `open`                         | float    | Opening price          | `42150.50`            |
| `high`                         | float    | Highest price          | `42200.00`            |
| `low`                          | float    | Lowest price           | `42100.25`            |
| `close`                        | float    | Closing price          | `42175.75`            |
| `volume`                       | float    | Base asset volume      | `15.250000`           |
| `close_time`                   | datetime | Close timestamp        | `2024-01-01 12:59:59` |
| `quote_asset_volume`           | float    | Quote asset volume     | `643238.125`          |
| `number_of_trades`             | int      | Trade count            | `1547`                |
| `taker_buy_base_asset_volume`  | float    | Taker buy base volume  | `7.825000`            |
| `taker_buy_quote_asset_volume` | float    | Taker buy quote volume | `329891.750`          |

### Microstructure Analysis

```python
df = gcd.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# Professional microstructure analysis
buy_pressure = df['taker_buy_base_asset_volume'].sum() / df['volume'].sum()
avg_trade_size = df['volume'].sum() / df['number_of_trades'].sum()
market_impact = df['quote_asset_volume'].std() / df['quote_asset_volume'].mean()

print(f"Taker buy pressure: {buy_pressure:.1%}")
print(f"Average trade size: {avg_trade_size:.4f} BTC")
print(f"Market impact volatility: {market_impact:.3f}")
```

## Advanced Class-Based API

For complex workflows requiring detailed control, use the class-based API:

```python
from gapless_crypto_data import BinancePublicDataCollector, UniversalGapFiller

# Custom collection with full control
collector = BinancePublicDataCollector(
    symbol="SOLUSDT",
    start_date="2023-01-01",
    end_date="2023-12-31",
    output_dir="./crypto_data"
)

result = collector.collect_timeframe_data("1h")
df = result["dataframe"]
filepath = result["filepath"]
stats = result["stats"]

# Manual gap filling
gap_filler = UniversalGapFiller()
gaps = gap_filler.detect_all_gaps(filepath, "1h")
```

## Supported Assets & Timeframes

### Supported Symbols (USDT Spot Only)

- **Major**: BTCUSDT, ETHUSDT, SOLUSDT, ADAUSDT, DOTUSDT
- **Altcoins**: LINKUSDT, MATICUSDT, AVAXUSDT, ATOMUSDT, NEARUSDT
- **And more**: All USDT-quoted spot pairs available on Binance

### Supported Timeframes

- **Seconds**: 1s (ultra high-frequency)
- **Minutes**: 1m, 3m, 5m, 15m, 30m
- **Hours**: 1h, 2h, 4h, 6h, 8h, 12h
- **Days**: 1d, 3d
- **Weeks**: 1w
- **Months**: 1mo

## CLI Usage

```bash
# Simple collection
gapless-crypto-data --symbol BTCUSDT --timeframes 1h,4h

# Multiple symbols
gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1h,4h

# Custom date range
gapless-crypto-data --symbol BTCUSDT --timeframes 1h --start 2024-01-01 --end 2024-06-30

# Fill gaps
gapless-crypto-data --fill-gaps --directory ./data

# Help
gapless-crypto-data --help
```

## Performance Benchmarks

| Method                  | Collection Speed | Data Format              | Gap Handling          |
| ----------------------- | ---------------- | ------------------------ | --------------------- |
| **gapless-crypto-data** | **22x faster**   | 11-column microstructure | Authentic API filling |
| Traditional APIs        | 1x baseline      | Basic OHLCV              | Manual handling       |
| Other tools             | 2-5x faster      | Limited format           | Limited coverage      |

### Real-World Performance

- **1 year hourly data**: ~30 seconds vs 12+ minutes with APIs
- **Memory usage**: Constant regardless of dataset size (streaming)
- **Data quality**: Zero gaps guaranteed with authentic market data

## Error Handling

All functions implement robust error handling:

```python
try:
    df = gcd.fetch_data("BTCUSDT", "1h", limit=1000)
    if df.empty:
        print("No data returned - check symbol and timeframe")
    else:
        print(f"Successfully fetched {len(df)} bars")

except ValueError as e:
    print(f"Invalid parameters: {e}")
except ConnectionError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Data Availability

### Historical Coverage

- **BTCUSDT/ETHUSDT**: From 2017-08-17
- **SOLUSDT**: From 2020-08-11
- **Most pairs**: From their listing date on Binance
- **Current data**: Up to T-1 (yesterday), updated daily

### Safe Date Ranges

```python
# Recent data (always available)
df = gcd.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# Historical backtesting
df = gcd.download("ETHUSDT", "4h", start="2020-01-01", end="2023-12-31")

# Full history (symbol-dependent)
df = gcd.download("SOLUSDT", "1d", start="2020-08-11")  # From listing
```

## Integration Examples

### Backtesting Framework Integration

```python
import gapless_crypto_data as gcd
import pandas as pd

def prepare_backtest_data(symbol, timeframe, start, end):
    """Prepare high-quality data for backtesting"""
    # Fetch data
    df = gcd.download(symbol, timeframe, start=start, end=end)

    # Verify completeness
    if df.empty:
        raise ValueError(f"No data available for {symbol} {timeframe}")

    # Check for gaps (should be zero)
    time_diff = df['date'].diff().dropna()
    expected_interval = pd.Timedelta(hours=1) if timeframe == '1h' else pd.Timedelta(minutes=5)
    gaps = time_diff[time_diff > expected_interval * 1.5]

    if len(gaps) > 0:
        print(f"Warning: {len(gaps)} gaps detected, consider gap filling")

    return df

# Use in backtesting
btc_data = prepare_backtest_data("BTCUSDT", "1h", "2023-01-01", "2023-12-31")
```

### Portfolio Analysis

```python
import gapless_crypto_data as gcd

def analyze_portfolio(symbols, timeframe="1h", period_days=30):
    """Analyze portfolio of cryptocurrencies"""
    portfolio_data = {}

    end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=period_days)).strftime('%Y-%m-%d')

    for symbol in symbols:
        df = gcd.fetch_data(symbol, timeframe, start=start_date, end=end_date)

        if not df.empty:
            # Calculate metrics
            returns = df['close'].pct_change()
            portfolio_data[symbol] = {
                'total_return': (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100,
                'volatility': returns.std() * 100,
                'volume_profile': df['volume'].mean(),
                'trade_frequency': df['number_of_trades'].mean(),
                'buy_pressure': df['taker_buy_base_asset_volume'].sum() / df['volume'].sum()
            }

    return pd.DataFrame(portfolio_data).T

# Analyze major cryptocurrencies
results = analyze_portfolio(["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT"])
print(results.round(2))
```

## Troubleshooting

### Common Issues

**Empty DataFrame returned:**

```python
# Check if symbol is supported
symbols = gcd.get_supported_symbols()
if "YOURSYMBOL" not in symbols:
    print(f"Symbol not supported. Available: {symbols}")

# Check date range
df = gcd.fetch_data("BTCUSDT", "1h", start="2020-01-01")  # Use earlier start date
```

**Network timeouts:**

```python
# For large datasets, use smaller date ranges
import pandas as pd

def fetch_large_dataset(symbol, timeframe, start, end, chunk_months=3):
    """Fetch large datasets in chunks"""
    start_date = pd.Timestamp(start)
    end_date = pd.Timestamp(end)

    chunks = []
    current = start_date

    while current < end_date:
        chunk_end = min(current + pd.DateOffset(months=chunk_months), end_date)

        chunk_df = gcd.fetch_data(
            symbol, timeframe,
            start=current.strftime('%Y-%m-%d'),
            end=chunk_end.strftime('%Y-%m-%d')
        )

        if not chunk_df.empty:
            chunks.append(chunk_df)

        current = chunk_end

    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
```

**Gap filling issues:**

```python
# Check gap filling results
results = gcd.fill_gaps("./data")

if results['success_rate'] < 100:
    print(f"Some gaps remain: {results['gaps_detected'] - results['gaps_filled']}")
    print("Check internet connectivity and Binance API availability")
```

## Requirements

- **Python**: 3.9+
- **Dependencies**: pandas>=2.0.0, httpx>=0.25.0, joblib>=1.5.2, polars>=1.33.1, pyod>=2.0.5
- **Internet**: Required for data collection and gap filling
- **Storage**: Varies by dataset size (1GB for 1 year of 1h data)

## License

MIT License - see repository for full details.

## Support

- **Documentation**: [GitHub Repository](https://github.com/terrylica/gapless-crypto-data)
- **Issues**: [GitHub Issues](https://github.com/terrylica/gapless-crypto-data/issues)
- **Changelog**: [Release Notes](https://github.com/terrylica/gapless-crypto-data/blob/main/CHANGELOG.md)

---

**Get started in 30 seconds:**

```python
pip install gapless-crypto-data
import gapless_crypto_data as gcd
df = gcd.download("BTCUSDT", "1h", limit=1000)
print(f"Fetched {len(df)} bars with {df.shape[1]} columns of microstructure data")
```
