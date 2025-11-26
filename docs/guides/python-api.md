---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Python API Reference

## Purpose

Comprehensive guide to programmatic usage of gapless-crypto-data via Python API for data collection, gap filling, and validation workflows.

## API Layers

**Two Usage Patterns**:

1. **Function-Based API**: Simple, intuitive functions for common tasks (`gcch.fetch_data()`, `gcch.download()`, `gcch.fill_gaps()`)
2. **Class-Based API**: Advanced workflows with fine-grained control (`BinancePublicDataCollector`, `UniversalGapFiller`, `CSVValidator`)

**Examples**: Complete working examples in `examples/`

## Function-Based API (Simple)

### Library Information

````python
import gapless_crypto_clickhouse as gcch

# Get library info
info = gcch.get_info()
print(f"{info['name']} v{info['version']}")

# Available symbols and timeframes
symbols = gcch.get_supported_symbols()      # ['BTCUSDT', 'ETHUSDT', ...]
timeframes = gcch.get_supported_timeframes() # ['1s', '1m', '3m', '5m', ...]
```text

### Fetch Recent Data

```python
# Fetch recent bars with limit
df = gcch.fetch_data("BTCUSDT", "1h", limit=100)

print(f"Fetched {len(df)} bars")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")
print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
```text

### Download Date Range

```python
# Download specific date range
df = gcch.download(
    "ETHUSDT",
    "4h",
    start="2024-01-01",
    end="2024-02-01"
)

print(f"Downloaded {len(df)} bars")

# Microstructure analysis
buy_ratio = df["taker_buy_base_asset_volume"].sum() / df["volume"].sum()
print(f"Taker buy ratio: {buy_ratio:.1%}")
```text

### Gap Filling

```python
# Fill gaps in directory
results = gcch.fill_gaps("./data")

print(f"Files processed: {results['files_processed']}")
print(f"Gaps detected: {results['gaps_detected']}")
print(f"Gaps filled: {results['gaps_filled']}")
print(f"Success rate: {results['success_rate']:.1f}%")
```text

## Class-Based API (Advanced)

### Basic Collection

```python
from gapless_crypto_clickhouse import BinancePublicDataCollector

collector = BinancePublicDataCollector()
collector.collect_data(
    symbol="BTCUSDT",
    timeframes=["1h", "4h"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```text

### Custom Configuration

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-01-31",
    output_dir="./custom_data"
)

# Collect multiple timeframes
timeframes = ["1h", "4h", "1d"]
results = collector.collect_multiple_timeframes(timeframes)

for timeframe, filepath in results.items():
    file_size = filepath.stat().st_size / (1024 * 1024)
    print(f"{timeframe}: {filepath.name} ({file_size:.1f} MB)")
```text

### Single Timeframe Collection

```python
collector = BinancePublicDataCollector(
    symbol="ETHUSDT",
    start_date="2024-06-01",
    end_date="2024-06-30"
)

result = collector.collect_timeframe_data("1h")

if result and "dataframe" in result:
    df = result["dataframe"]
    filepath = result["filepath"]
    stats = result["stats"]

    print(f"DataFrame shape: {df.shape}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"File saved: {filepath}")
    print(f"Collection stats: {stats}")
```bash

### Ultra-High Frequency Collection

```python
# 1-second data (use short date ranges)
uhf_collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    start_date="2024-01-01",
    end_date="2024-01-01",  # Single day for 1s data
    output_dir="./uhf_data"
)

uhf_result = uhf_collector.collect_timeframe_data("1s")

if uhf_result and "dataframe" in uhf_result:
    df = uhf_result["dataframe"]
    print(f"1s data: {len(df)} bars (ultra-high frequency)")
```bash

**Note**: All 16 timeframes supported with intelligent fallback:

- Ultra-high frequency: **1s** (short date ranges)
- Standard: **1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h**
- Extended: **6h, 8h, 12h, 1d** (automatic monthly-to-daily fallback)
- Exotic: **3d, 1w, 1mo**

### Multi-Symbol Collection

> **Note**: This package provides a Python API only (no CLI interface). For CLI-based workflows, use the parent package [gapless-crypto-data](https://github.com/terrylica/gapless-crypto-data).

Loop for per-symbol collection:

```python
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
for symbol in symbols:
    collector = BinancePublicDataCollector(symbol=symbol)
    collector.collect_multiple_timeframes(["1h", "4h"])
```text

## Gap Filling API

### Basic Gap Filling

```python
from gapless_crypto_clickhouse import UniversalGapFiller

gap_filler = UniversalGapFiller()
gap_filler.fill_gaps(directory="./data")
```text

### Gap Detection and Analysis

```python
from pathlib import Path

gap_filler = UniversalGapFiller()

csv_file = Path("data/BTCUSDT-1h.csv")
timeframe = "1h"

# Detect all gaps
gaps = gap_filler.detect_all_gaps(csv_file, timeframe)
print(f"Gaps detected: {len(gaps)}")

if gaps:
    print("Gap details:")
    for i, gap in enumerate(gaps[:3]):  # Show first 3 gaps
        duration = gap["duration"].total_seconds() / 3600  # Hours
        print(f"  {i + 1}. {gap['start_time']} → {gap['end_time']} ({duration:.1f}h)")

    # Fill gaps
    result = gap_filler.process_file(csv_file, timeframe)
    print(f"Fill result: {result['gaps_filled']}/{result['gaps_detected']} gaps filled")
    print(f"Success rate: {result['success_rate']:.1f}%")
```text

## Validation API

### CSV Validation (5-Layer)

```python
from gapless_crypto_clickhouse.validation import CSVValidator

validator = CSVValidator()
report = validator.validate_csv_file(
    "data/BTCUSDT-1h.csv",
    expected_timeframe="1h",
    store_report=False  # Optional: persist to DuckDB
)

print(f"Status: {report['validation_summary']}")
print(f"Errors: {report['total_errors']}")
print(f"Warnings: {report['total_warnings']}")
print(f"File size: {report['file_size_mb']:.1f} MB")
```text

### Validation with DuckDB Persistence

```python
from gapless_crypto_clickhouse.validation import CSVValidator, ValidationStorage

# Validate and store report
validator = CSVValidator()
report = validator.validate_csv_file(
    "data/BTCUSDT-1h.csv",
    expected_timeframe="1h",
    store_report=True  # Persist to DuckDB
)

# Query validation history
storage = ValidationStorage()
recent = storage.query_recent(limit=10, symbol="BTCUSDT")
failed = storage.query_by_status("FAILED")
stats = storage.get_summary_stats()

# Export to pandas for analysis
df = storage.export_to_dataframe()
```text

**Storage Location**: `~/.cache/gapless-crypto-data/validation.duckdb`

See [Validation Query Patterns](docs/validation/QUERY_PATTERNS.md) for complete query examples.

## Atomic File Operations

### Corruption-Proof Writes

```python
from pathlib import Path
from gapless_crypto_clickhouse import AtomicCSVOperations

atomic_ops = AtomicCSVOperations()

# Write data atomically (no partial writes)
test_data = [
    ["2024-01-01 00:00:00", 42000.0, 42100.0, 41900.0, 42050.0, 100.5],
    ["2024-01-01 01:00:00", 42050.0, 42200.0, 42000.0, 42150.0, 150.3],
]

headers = ["date", "open", "high", "low", "close", "volume"]
atomic_ops.write_csv_atomic(Path("data.csv"), test_data, headers)
```text

**Guarantee**: Either complete file write or no file (no corruption on failure)

## Output Formats

### CSV (Default)

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    output_format="csv"  # Default
)
```text

### Parquet (5-10x Compression)

```python
collector = BinancePublicDataCollector(
    symbol="BTCUSDT",
    output_format="parquet"  # 5-10x compression
)
collector.collect_timeframe_data("1h")
```text

**Advantages**: Faster loading, type preservation, columnar storage

**Trade-offs**: Requires PyArrow dependency, less human-readable

See [Data Format Specification](docs/architecture/DATA_FORMAT.md) for details.

## Data Analysis Patterns

### Price Action Analysis

```python
# Fetch data
df = gcch.fetch_data("BTCUSDT", "1h", limit=100)

# Price statistics
print(f"Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
print(f"Open: ${df['open'].iloc[0]:.2f}")
print(f"Close: ${df['close'].iloc[-1]:.2f}")

# Price change percentage
price_change = ((df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]) * 100
print(f"Price change: {price_change:+.1f}%")
```text

### Microstructure Analysis

```python
# Order flow metrics
buy_ratio = df["taker_buy_base_asset_volume"].sum() / df["volume"].sum()
print(f"Taker buy ratio: {buy_ratio:.1%}")

# Trade frequency
avg_trades_per_bar = df["number_of_trades"].mean()
print(f"Average trades per bar: {avg_trades_per_bar:.0f}")

# Volume analysis
print(f"Total volume: {df['volume'].sum():,.0f}")
print(f"Average volume: {df['volume'].mean():.2f}")
```text

### Coverage Validation

```python
# Check data completeness
print(f"Total bars: {len(df)}")
print(f"Date range: {df['date'].min()} to {df['date'].max()}")

# Detect gaps
gaps = gap_filler.detect_all_gaps(csv_file, timeframe)
print(f"Gaps found: {len(gaps)}")
```text

## Batch Processing Workflow

### Batch Validation

```python
from pathlib import Path
from gapless_crypto_clickhouse.validation import CSVValidator, ValidationStorage

validator = CSVValidator()
storage = ValidationStorage()

# Batch validate all CSV files
for csv_file in Path("data/").glob("*.csv"):
    report = validator.validate_csv_file(str(csv_file), store_report=True)
    print(f"Validated {csv_file.name}: {report['validation_summary']}")

# Analyze batch results
stats = storage.get_summary_stats()
print(f"\nBatch results:")
print(f"  Total: {stats['total_validations']}")
print(f"  Avg errors: {stats['avg_errors']:.2f}")

# Find failures
failed = storage.query_by_status("FAILED")
if failed:
    print(f"\nFailed validations: {len(failed)}")
    for f in failed:
        print(f"  {f['file_path']}")
```python

## SLOs (Service Level Objectives)

### Correctness

- **Zero-gap guarantee**: All timestamps present within collection range
- **Authentic data only**: Direct from Binance (no synthetic values)
- **Type safety**: Pydantic validation for all API responses

### Observability

- **Progress reporting**: Real-time collection status
- **Validation reports**: Complete error and warning capture
- **Persistent history**: DuckDB storage for AI agent queries

### Maintainability

- **Backward compatibility**: Function-based API never breaks
- **Optional features**: `store_report=False` default for new features
- **Clear documentation**: Examples for all usage patterns

## Complete Examples

**Location**: `examples/`

### Simple API Examples

`simple_api_examples.py` - Function-based patterns for common tasks

### Advanced API Examples

`advanced_api_examples.py` - Class-based patterns for complex workflows

### Quick Start Examples

- `basic_data_collection.py` - Basic collection workflow
- `complete_workflow.py` - End-to-end workflow
- `gap_filling_example.py` - Gap detection and filling
- `safe_data_collection.py` - Atomic operations

**Run examples**:

```bash
uv run python examples/simple_api_examples.py
uv run python examples/advanced_api_examples.py
````

## Related Documentation

- **Data Collection Guide**: [DATA_COLLECTION.md](docs/guides/DATA_COLLECTION.md)
- **Validation Overview**: [docs/validation/OVERVIEW.md](docs/validation/OVERVIEW.md)
- **Query Patterns**: [docs/validation/QUERY_PATTERNS.md](docs/validation/QUERY_PATTERNS.md)
- **Data Format**: [docs/architecture/DATA_FORMAT.md](docs/architecture/DATA_FORMAT.md)
