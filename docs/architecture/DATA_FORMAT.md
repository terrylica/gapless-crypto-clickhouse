---
version: "1.0.1"
last_updated: "2025-10-28"
canonical_source: true
supersedes: ["1.0.0"]
---

# Data Format Specification

## 11-Column Microstructure Format

Gapless Crypto Data produces CSV files in 11-column microstructure format, providing complete market data beyond basic OHLCV.

### Column Definitions

| Column                         | Type      | Description              | Range/Constraints           |
| ------------------------------ | --------- | ------------------------ | --------------------------- |
| `date`                         | TIMESTAMP | Open time in UTC         | ISO 8601 format             |
| `open`                         | DOUBLE    | Opening price for period | > 0                         |
| `high`                         | DOUBLE    | Highest price in period  | >= open, low, close         |
| `low`                          | DOUBLE    | Lowest price in period   | <= open, high, close; > 0   |
| `close`                        | DOUBLE    | Closing price for period | > 0                         |
| `volume`                       | DOUBLE    | Base asset volume        | >= 0                        |
| `close_time`                   | TIMESTAMP | Close time in UTC        | ISO 8601 format             |
| `quote_asset_volume`           | DOUBLE    | Quote asset volume       | >= 0                        |
| `number_of_trades`             | INTEGER   | Trade count in period    | >= 0                        |
| `taker_buy_base_asset_volume`  | DOUBLE    | Taker buy base volume    | >= 0, <= volume             |
| `taker_buy_quote_asset_volume` | DOUBLE    | Taker buy quote volume   | >= 0, <= quote_asset_volume |

### Data Categories

**Standard OHLCV Columns** (5 columns):

- `open`, `high`, `low`, `close`: Price action
- `volume`: Base asset trading volume

**Order Flow Metrics** (4 columns):

- `quote_asset_volume`: Total quote asset traded
- `number_of_trades`: Trade frequency
- `taker_buy_base_asset_volume`: Aggressor buy volume (base)
- `taker_buy_quote_asset_volume`: Aggressor buy volume (quote)

**Timestamps** (2 columns):

- `date`: Period start time (open time)
- `close_time`: Period end time

### Use Cases

**Price Action Analysis**:

- OHLC data for candlestick charting
- High-low range for volatility analysis
- Open-close relationship for momentum

**Volume Profiling**:

- Base/quote volume for liquidity analysis
- Volume-weighted price calculations
- Trading activity intensity

**Order Flow Analysis**:

- Taker buy ratio: Market buying pressure
- Aggressive vs passive order flow
- Microstructure imbalance detection

**Trade Frequency**:

- Number of trades per period
- Activity clustering analysis
- Liquidity proxy metrics

### Example CSV

```csv
date,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume
2024-01-01T00:00:00,42150.50,42200.00,42100.00,42175.25,125.50,2024-01-01T00:59:59,5295312.50,1250,62.75,2647656.25
2024-01-01T01:00:00,42175.25,42250.00,42150.00,42220.00,138.25,2024-01-01T01:59:59,5835412.50,1320,70.50,2975706.25
```

### Data Integrity Constraints

**OHLC Relationships**:

- `high >= open`
- `high >= close`
- `high >= low`
- `low <= open`
- `low <= close`
- All OHLC values > 0

**Volume Constraints**:

- All volume values >= 0
- `taker_buy_base_asset_volume <= volume`
- `taker_buy_quote_asset_volume <= quote_asset_volume`

**Trade Count**:

- `number_of_trades >= 0`
- `number_of_trades` is integer

**Timestamp Constraints**:

- `close_time > date`
- Timestamps in chronological order
- No gaps in sequence (for gapless datasets)

### Format Transitions

**v2.x → v3.x**:

- Added DuckDB validation persistence
- No changes to 11-column format
- Backward compatible

**Historical Context**:

- 11-column format introduced in v2.0.0
- Based on Binance public data repository schema
- Unchanged since initial release (stable format)

### Validation

All CSV files should be validated using CSVValidator:

```python
from gapless_crypto_data.validation import CSVValidator

validator = CSVValidator()
report = validator.validate_csv_file("data.csv", expected_timeframe="1h")

if report["total_errors"] > 0:
    print(f"Validation failed: {report['validation_summary']}")
else:
    print("Format validation passed")
```

See [Validation Overview](/Users/terryli/eon/gapless-crypto-data/docs/validation/OVERVIEW.md) for complete validation specifications.

### File Naming Convention

Standard format: `binance_spot_{SYMBOL}-{TIMEFRAME}_{START_DATE}-{END_DATE}_v{VERSION}.csv`

Examples:

- `binance_spot_BTCUSDT-1h_20240101-20240131_v2.10.0.csv`
- `binance_spot_ETHUSDT-5m_20240201-20240228_v3.0.0.csv`

### Metadata Headers

CSV files include metadata headers (comment lines starting with `#`):

```
# Binance Spot Market Data v2.10.0
# Symbol: BTCUSDT
# Timeframe: 1h
# Start: 2024-01-01
# End: 2024-01-31
# Generated: 2024-02-01T12:00:00Z
#
```

These headers are ignored during CSV parsing (via `comment="#"` parameter).

## Alternative Formats

### Parquet Support

Parquet format supported via `output_format="parquet"`:

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    output_format="parquet"
)
```

**Advantages**:

- 5-10x compression vs CSV
- Faster loading with columnar storage
- Type preservation (no string parsing)

**Trade-offs**:

- Requires PyArrow dependency
- Less human-readable than CSV
- Metadata stored separately

See [Parquet Implementation Specification](/Users/terryli/eon/gapless-crypto-data/docs/api/pruning-parquet-implementation.yaml) for details.

## SLOs (Service Level Objectives)

### Correctness

**Format Stability**: 11-column format unchanged since v2.0.0 release (immutable schema)

**Data Integrity**: All files must pass CSVValidator integrity checks (OHLC relationships, volume constraints, timestamp ordering)

**Constraint Enforcement**: Validation pipeline enforces all documented constraints (zero tolerance for violations)

### Observability

**Format Detection**: Automatic detection of 11-column vs legacy 6-column format

**Validation Reporting**: Complete validation reports with per-constraint error details via ValidationStorage

**Metadata Transparency**: CSV metadata headers document symbol, timeframe, date range, version

### Maintainability

**Backward Compatibility**: Format additions follow strict backward compatibility rules (no breaking changes)

**Documentation Sync**: Format specification kept in sync with CSVValidator implementation

**Type Consistency**: Data types documented with explicit range/constraint specifications

## Related Documentation

- **Architecture Overview**: [OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/architecture/OVERVIEW.md)
- **Data Collection**: [docs/guides/DATA_COLLECTION.md](/Users/terryli/eon/gapless-crypto-data/docs/guides/DATA_COLLECTION.md)
- **Validation**: [docs/validation/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/OVERVIEW.md)
