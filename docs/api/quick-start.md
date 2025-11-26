# Quick Start Guide - gapless-crypto-data

Cryptocurrency data collection with gap detection and filling capabilities. Provides 11-column microstructure format.

## Installation

````bash
pip install gapless-crypto-data
# or with uv
uv add gapless-crypto-data
```text

## Simple API (Recommended)

### Basic Usage

```python
import gapless_crypto_clickhouse as gcc

# Fetch recent data with date range
df = gcc.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# Or with limit
df = gcc.fetch_data("ETHUSDT", "4h", limit=1000)

# Get available symbols and timeframes
symbols = gcc.get_supported_symbols()
timeframes = gcc.get_supported_timeframes()

# Library information
info = gcc.get_info()
print(f"Version: {info['version']}")
```text

### Data Structure

All functions return pandas DataFrames with complete microstructure data:

```python
df.columns
# ['date', 'open', 'high', 'low', 'close', 'volume',
#  'close_time', 'quote_asset_volume', 'number_of_trades',
#  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']

# Professional analysis
buy_pressure = df['taker_buy_base_asset_volume'].sum() / df['volume'].sum()
avg_trade_size = df['volume'].sum() / df['number_of_trades'].sum()
```text

### Gap Filling

```python
# Fill gaps in existing CSV files
results = gcc.fill_gaps("./data")
print(f"Filled {results['gaps_filled']}/{results['gaps_detected']} gaps")
```text

## Advanced API (Power Users)

```python
from gapless_crypto_clickhouse import BinancePublicDataCollector, UniversalGapFiller

# Custom collection with full control
collector = BinancePublicDataCollector(
    symbol="SOLUSDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    output_dir="./crypto_data"
)

result = collector.collect_timeframe_data("1h")
df = result["dataframe"]
filepath = result["filepath"]
```text

## CLI Usage

```bash
# Default: SOLUSDT, comprehensive timeframes, 4+ years
uv run gapless-crypto-data

# Custom symbols and timeframes
uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT --timeframes 1h,4h

# Fill gaps in existing data
uv run gapless-crypto-data --fill-gaps --directory ./data
````

## Key Features

- **22x faster** than API-only approaches via Binance public data repository
- **Zero gaps guarantee** through authentic API-first validation
- **Full microstructure format** with order flow and liquidity metrics
- **Production-grade** data quality for quantitative trading
- **Both APIs** - simple functions for quick use, classes for complex workflows

## Supported Assets

**20 USDT pairs** (spot + futures dual coverage):

Top symbols by market cap: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, DOTUSDT, LINKUSDT, MATICUSDT, LTCUSDT, UNIUSDT, ATOMUSDT, FTMUSDT, NEARUSDT, ALGOUSDT, SANDUSDT, MANAUSDT, APEUSDT

All symbols validated for both Binance Spot and UM-margined perpetual futures markets.

## Performance

- Collection: 1 year of hourly data in ~30 seconds
- Gap filling: Automatic detection and authentic data filling
- Memory efficient: Streaming support for unlimited dataset sizes

## Next Steps

- Check `examples/simple_api_examples.py` for more usage patterns
- See `examples/advanced_api_examples.py` for complex workflows
- Use with your backtesting framework for authentic historical data
