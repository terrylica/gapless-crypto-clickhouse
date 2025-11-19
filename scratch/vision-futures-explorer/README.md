# Vision Futures Explorer

**Branch**: `vision-futures-explorer`
**Created**: 2025-11-12
**Purpose**: Explore discovery of all actively traded USDT perpetual futures instruments historically via Binance Vision

## Objectives

1. **Symbol Discovery**: Enumerate all USDT perpetual futures symbols from Binance Vision S3 bucket
2. **Historical Availability**: Determine which symbols existed/traded on any given historical date
3. **Integration Pattern**: Demonstrate how futures discovery integrates with gapless-crypto-data architecture
4. **Separation Decision**: Document whether futures should be separate package or integrated

## Research Findings

### Binance Vision Futures Structure

**Base URL**: `https://data.binance.vision/data/futures/um/`

- `um` = USD-M (USDT-Margined) futures
- `daily/` = Daily aggregated data files
- `monthly/` = Monthly aggregated data files
- `klines/` = OHLCV candlestick data

**Contract Types**:

- **Perpetual**: No expiration (e.g., BTCUSDT) - ~400+ symbols
- **Delivery**: Quarterly expiration (e.g., BTCUSDT_231229) - excluded from this exploration

### S3 Discovery Method

**Endpoint**: `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision`

**Parameters**:

- `prefix=data/futures/um/daily/klines/`
- `delimiter=/`
- `marker={continuation_token}` (for pagination)

**Returns**: XML with `<CommonPrefixes>` listing all symbol directories

### Key Differences: Futures vs Spot

| Aspect              | Spot          | Futures (UM)              |
| ------------------- | ------------- | ------------------------- |
| Base URL            | `/data/spot/` | `/data/futures/um/`       |
| 1-second data       | ✅ Supported  | ❌ Not supported          |
| Perpetual contracts | N/A           | ✅ Primary focus          |
| Delivery contracts  | N/A           | ✅ Quarterly/bi-quarterly |
| Data format         | 11-column CSV | 11-column CSV (same)      |

## Modules

### 1. `futures_discovery.py`

S3-based enumeration of all USDT perpetual futures symbols.

**Key Functions**:

- `discover_all_perpetual_symbols()`: Query S3, parse XML, return symbol list
- `classify_symbol(symbol)`: Distinguish perpetual vs delivery contracts
- `paginate_s3_listing()`: Handle 1000-result pagination

### 2. `historical_probe.py`

Determine symbol availability for specific historical dates.

**Key Functions**:

- `check_symbol_availability(symbol, date)`: Probe for data file existence
- `get_available_symbols_for_date(date)`: Return all symbols active on given date
- `generate_historical_snapshot(start, end)`: Create date-to-symbols mapping

### 3. `vision_futures_collector.py`

Integration bridge demonstrating futures collection with gapless-crypto-data patterns.

**Key Features**:

- Extends `BinancePublicDataCollector` pattern
- Maintains CSV validation compatibility
- Documents architectural differences
- Proposes separation strategy

## Usage Examples

### Discover All Perpetual Symbols

```python
from futures_discovery import discover_all_perpetual_symbols

symbols = discover_all_perpetual_symbols()
print(f"Found {len(symbols)} USDT perpetual futures")
# Output: Found 421 USDT perpetual futures
```

### Check Historical Availability

```python
from historical_probe import check_symbol_availability
from datetime import date

result = check_symbol_availability("BTCUSDT", date(2024, 1, 15))
print(f"BTCUSDT on 2024-01-15: {result['available']}")
# Output: BTCUSDT on 2024-01-15: True
```

### Collect Futures Data

```python
from vision_futures_collector import BinanceFuturesCollector

collector = BinanceFuturesCollector(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
df = collector.collect_timeframe_data("1h")
print(df.shape)
# Output: (744, 11)
```

## Testing Strategy

1. **Symbol Discovery**: Verify against known contracts (BTCUSDT, ETHUSDT, SOLUSDT)
2. **Historical Probe**: Test dates: 2023-06-15, 2024-01-15, 2025-01-15
3. **Integration**: Compare futures vs spot collection workflows
4. **Validation**: Ensure CSV format matches spot 11-column structure

## Next Steps

1. Run empirical tests to validate discovery mechanism
2. Compare S3 discovery vs API `exchangeInfo` completeness
3. Document whether perpetual futures can share validation pipeline with spot
4. Identify architectural constraints requiring separation

## References

- Binance Vision: https://data.binance.vision/
- S3 API: https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html
- Binance Futures API: https://binance-docs.github.io/apidocs/futures/en/
- GitHub: https://github.com/binance/binance-public-data
