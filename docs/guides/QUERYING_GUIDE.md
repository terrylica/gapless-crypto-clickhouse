# Querying Cached Data

This guide explains how to query existing data from ClickHouse using gapless-crypto-clickhouse.

## Quick Start

```python
import gapless_crypto_clickhouse as gcch

# Query existing cached data (fast: 0.1-2s)
df = gcch.query_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30",
    auto_ingest=False  # Skip auto-download, query cache only
)

# Check if data exists first
status = gcch.check_setup()
if status["ready"]:
    print(f"ClickHouse has {status['data_count']:,} rows")
```

## Primary Query Function: `query_ohlcv()`

The main entry point for querying data is `query_ohlcv()`. It supports two modes:

### Mode 1: Auto-Ingestion (Default)

Downloads missing data automatically from Binance CDN, then queries.

```python
# First query: 30-60s (downloads + ingests)
# Subsequent queries: 0.1-2s (cache hit)
df = gcch.query_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30"
)
```

### Mode 2: Cache-Only (Fast)

Query only cached data. Raises error if data missing.

```python
df = gcch.query_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30",
    auto_ingest=False  # No download, cache only
)
```

### Multi-Symbol Queries

```python
df = gcch.query_ohlcv(
    symbol=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30"
)
```

### Futures Data

```python
df = gcch.query_ohlcv(
    symbol="BTCUSDT",
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30",
    instrument_type="futures-um"
)
```

## Column Names

This package uses `timestamp` instead of Binance's native `open_time`:

| Package Column | Binance Native | Description |
|---------------|----------------|-------------|
| `timestamp` | `open_time` | Candle open time |
| `close_time` | `close_time` | Candle close time |

### Converting to Binance Column Names

```python
# Get data with package naming
df = gcch.query_ohlcv(symbol="BTCUSDT", timeframe="1h", ...)

# Convert to Binance naming if needed
df_binance = gcch.to_binance_columns(df)
print(df_binance.columns[0])  # 'open_time' instead of 'timestamp'

# Convert back
df_package = gcch.to_package_columns(df_binance)
```

## All Returned Columns

```python
df = gcch.query_ohlcv(...)
print(df.columns.tolist())
# ['timestamp', 'open', 'high', 'low', 'close', 'volume',
#  'close_time', 'quote_asset_volume', 'number_of_trades',
#  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
```

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime64[ns] | Candle open time (UTC) |
| `open` | float64 | Open price |
| `high` | float64 | High price |
| `low` | float64 | Low price |
| `close` | float64 | Close price |
| `volume` | float64 | Base asset volume |
| `close_time` | datetime64[ns] | Candle close time (UTC) |
| `quote_asset_volume` | float64 | Quote asset volume |
| `number_of_trades` | int64 | Trade count |
| `taker_buy_base_asset_volume` | float64 | Taker buy base volume |
| `taker_buy_quote_asset_volume` | float64 | Taker buy quote volume |

## Alternative APIs

### `fetch_data()` - File-Based Collection

Collects data from Binance CDN without ClickHouse:

```python
# Download and return as DataFrame (no ClickHouse required)
df = gcch.fetch_data(
    symbol="BTCUSDT",
    timeframe="1h",
    start_date="2024-01-01",
    end_date="2024-06-30"
)
```

### `download()` - Alias for `fetch_data()`

```python
df = gcch.download(
    symbol="ETHUSDT",
    timeframe="4h",
    start="2024-01-01",
    end="2024-06-30"
)
```

## Discovery APIs

```python
# Check what's available
symbols = gcch.get_supported_symbols()      # 715 symbols
timeframes = gcch.get_supported_timeframes() # 16 timeframes

# Check system status
status = gcch.check_setup()
print(f"Mode: {status['mode']}")  # 'local' or 'cloud'
print(f"Ready: {status['ready']}")
print(f"Data rows: {status['data_count']}")
```

## Performance Characteristics

| Scenario | Latency |
|----------|---------|
| First query (with auto-ingest) | 30-60s |
| Cached query | 0.1-2s |
| Multi-symbol query (3 symbols) | 0.3-5s |
| Large date range (1 year, 1h) | 1-3s |

## Error Handling

```python
from gapless_crypto_clickhouse import (
    GaplessCryptoDataError,
    DataCollectionError,
    NetworkError,
    ValidationError
)

try:
    df = gcch.query_ohlcv(
        symbol="BTCUSDT",
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2024-06-30",
        auto_ingest=False
    )
except ValidationError as e:
    print(f"Data validation failed: {e}")
except NetworkError as e:
    print(f"Network error: {e}")
except DataCollectionError as e:
    print(f"Collection error: {e}")
```

## Related Documentation

- [Python API Reference](/docs/guides/python-api.md) - Complete API reference
- [Data Collection Guide](/docs/guides/DATA_COLLECTION.md) - CLI and collection workflows
- [Architecture Overview](/docs/architecture/OVERVIEW.md) - System design
