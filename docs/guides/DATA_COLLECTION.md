---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Data Collection Guide

## Purpose

Guide to collecting complete historical cryptocurrency market data from Binance with zero-gap guarantee.

## Default Collection Configuration

**Symbol**: SOLUSDT (default)

**Timeframes**: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h (8 timeframes)

**Date Range**: 2020-08-15 to 2025-03-20 (4.1-year historical range, configurable)

**Output Location**: `src/gapless_crypto_data/sample_data/` (default)

## Dual Data Source Strategy

### Primary: Binance Public Data Repository

- **Method**: Monthly ZIP file downloads via CloudFront CDN
- **Performance**: 22x faster than direct API calls
- **Data**: Complete historical OHLCV with order flow metrics
- **Format**: 11-column microstructure CSV
- **Availability**: Monthly archives from 2017 to present

### Secondary: Binance API

- **Purpose**: Gap filling for missing data
- **Method**: REST API calls to Binance public endpoints
- **Data**: Authentic real-time and historical data
- **Usage**: Automatic when gaps detected in primary data
- **Guarantee**: Only authentic data (never synthetic)

## Output Directory Structure

```
output_dir/
├── {SYMBOL}_{TIMEFRAME}_{START_DATE}_to_{END_DATE}.csv
├── {SYMBOL}_{TIMEFRAME}_{START_DATE}_to_{END_DATE}.csv.metadata.json
└── ...
```

**File Naming**:

- Pattern: `binance_spot_{SYMBOL}-{TIMEFRAME}_{START}-{END}_v{VERSION}.csv`
- Example: `binance_spot_BTCUSDT-1h_20240101-20240131_v2.10.0.csv`

**Metadata Sidecar**:

- JSON file with collection statistics
- Generation timestamp
- Data source information
- Version tracking

## CLI Usage

### Standard Collection

Default collection (SOLUSDT, all timeframes):

```bash
uv run gapless-crypto-data
```

Custom symbol and timeframes:

```bash
uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h,4h
```

Multiple symbols (native multi-symbol support):

```bash
uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT,SOLUSDT --timeframes 1h,4h
```

Custom date range:

```bash
uv run gapless-crypto-data --start 2023-01-01 --end 2023-12-31
```

Custom output directory:

```bash
uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h,4h --output-dir ./crypto_data
```

### Gap Filling Operations

Manual gap filling for existing datasets:

```bash
uv run gapless-crypto-data --fill-gaps --directory ./data
```

Gap filling with specific filters:

```bash
uv run gapless-crypto-data --fill-gaps --directory ./data --symbol BTCUSDT --timeframe 1h
```

## Python API Usage

### Basic Collection

```python
from gapless_crypto_data import BinancePublicDataCollector

collector = BinancePublicDataCollector()
collector.collect_data(
    symbol="BTCUSDT",
    timeframes=["1h", "4h"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

### Multi-Symbol Collection

For multiple symbols, use CLI multi-symbol support (recommended):

```bash
uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT --timeframes 1h,4h
```

Or loop for complex per-symbol logic:

```python
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
for symbol in symbols:
    collector = BinancePublicDataCollector(symbol=symbol)
    collector.collect_multiple_timeframes(["1h", "4h"])
```

### Custom Output Directory

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    output_dir="/path/to/output"
)
collector.collect_timeframe_data("1h")
```

### Parquet Output Format

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    output_format="parquet"  # 5-10x compression
)
collector.collect_timeframe_data("1h")
```

## Supported Symbols

Get list of supported symbols:

```python
import gapless_crypto_data as gcd

symbols = gcd.get_supported_symbols()
print(symbols)
```

**Common Symbols**:

- BTCUSDT (Bitcoin)
- ETHUSDT (Ethereum)
- SOLUSDT (Solana)
- BNBUSDT (Binance Coin)

## Supported Timeframes

Get list of supported timeframes:

```python
timeframes = gcd.get_supported_timeframes()
print(timeframes)
```

**Available Timeframes**:

- Ultra-high frequency: 1s
- Minutes: 1m, 3m, 5m, 15m, 30m
- Hours: 1h, 2h, 4h, 6h, 8h, 12h
- Daily: 1d

**Total**: 13 timeframes

## Collection Workflow

### Step 1: Initialize Collector

```python
from gapless_crypto_data import BinancePublicDataCollector

collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-01-31",
    output_dir="./data"
)
```

### Step 2: Collect Timeframe Data

Single timeframe:

```python
result = collector.collect_timeframe_data("1h")
print(f"Collected {result['dataframe'].shape[0]} bars")
```

Multiple timeframes:

```python
timeframes = ["1h", "4h", "1d"]
results = collector.collect_multiple_timeframes(timeframes)
```

### Step 3: Verify Output Files

```python
from pathlib import Path

output_files = list(Path("./data").glob("*.csv"))
print(f"Generated {len(output_files)} CSV files")

for file in output_files:
    print(f"  {file.name}")
```

## Data Integrity

### Automatic Gap Detection

Gap detection runs automatically during collection:

- Analyzes timestamp sequences
- Identifies missing periods
- Reports gaps in output

### Automatic Gap Filling

Enable automatic gap filling:

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    auto_fill_gaps=True  # Default: False
)
```

### Manual Validation

Validate collected data:

```python
from gapless_crypto_data.validation import CSVValidator

validator = CSVValidator()
report = validator.validate_csv_file("data/BTCUSDT-1h.csv", expected_timeframe="1h")

print(f"Validation: {report['validation_summary']}")
print(f"Errors: {report['total_errors']}")
print(f"Gaps: {report['datetime_validation']['gaps_found']}")
```

## Performance Characteristics

**Collection Speed**: 22x faster than API-only approaches

- Monthly ZIP downloads: ~2-5 seconds per file
- CloudFront CDN: Global edge network
- ETag caching: Bandwidth optimization for repeat downloads

**Memory Usage**: ~100MB peak for full year collection

- Streaming ZIP extraction
- In-memory CSV processing
- Efficient DataFrame operations

## SLOs (Service Level Objectives)

### Availability

- **Data Source**: Binance public repository (99.99% SLA via CloudFront)
- **Dependencies**: Network connectivity, disk space

### Correctness

- **Zero-gap guarantee**: All timestamps present within collection range
- **Authentic data**: Direct from Binance (no synthetic values)
- **Format validation**: 11-column microstructure format verified

### Observability

- **Progress reporting**: Real-time collection status
- **File generation**: Output files created with metadata
- **Error logging**: Complete exception trace with context

### Maintainability

- **Configuration**: Flexible via constructor parameters
- **Output formats**: CSV (default), Parquet (optional)
- **Test coverage**: Collection tests in `/Users/terryli/eon/gapless-crypto-data/tests/test_binance_collector.py`

## Troubleshooting

### Missing Data Periods

If gaps detected:

1. Check Binance public repository availability
2. Use gap filling: `--fill-gaps --directory ./data`
3. Verify date range is within Binance data availability

### Download Failures

If downloads fail:

1. Check network connectivity
2. Verify symbol exists on Binance
3. Check CloudFront CDN status

### Output Directory Errors

If file write errors:

1. Verify output directory exists and is writable
2. Check disk space availability
3. Ensure no file permission issues

## Related Documentation

- **Architecture Overview**: [docs/architecture/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/architecture/OVERVIEW.md)
- **Data Format**: [docs/architecture/DATA_FORMAT.md](/Users/terryli/eon/gapless-crypto-data/docs/architecture/DATA_FORMAT.md)
- **Python API Reference**: [python-api.md](/Users/terryli/eon/gapless-crypto-data/docs/guides/python-api.md)
- **Gap Filling**: [GAP_FILLING.md](/Users/terryli/eon/gapless-crypto-data/docs/guides/GAP_FILLING.md) (planned)
- **Validation**: [docs/validation/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/OVERVIEW.md)
