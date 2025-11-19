---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Validation Architecture

## Purpose

5-layer validation engine with DuckDB-based persistence for CSV data quality assurance, optimized for AI coding agent queries and research workflows.

**Version**: v3.3.0+ (DuckDB persistence added)

## Architecture Components

### CSVValidator

**Location**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/csv_validator.py`

**Purpose**: Multi-layer validation of OHLCV CSV files

**5-Layer Validation Pipeline**:

1. **Structure Validation**
   - Column names present
   - Data types correct
   - Required fields populated

2. **DateTime Validation**
   - Timestamp ordering (chronological)
   - Gap detection (timeframe-aware)
   - Date range analysis

3. **OHLCV Validation**
   - Price logic (H≥L, O/C within H-L)
   - Negative/zero detection
   - Volume statistics

4. **Coverage Validation**
   - Expected vs actual bar counts
   - Missing data percentage
   - Date range completeness

5. **Anomaly Detection**
   - Statistical outliers (IQR method)
   - Price outliers
   - Volume outliers
   - Suspicious patterns

### ValidationReport (Pydantic Model)

**Location**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/models.py`

**Purpose**: Type-safe validation report with OpenAPI 3.1.1 schema

**Fields**: 34 typed fields

- Metadata (timestamp, file path, size, version)
- Core results (total bars, errors, warnings, summary, duration)
- Layer results (JSON columns for nested data)
- Flattened metrics (extracted for SQL efficiency)

**Type Safety**: Pydantic 2.0+ with automatic validation

**Serialization**: JSON with automatic numpy/pandas type conversion

### ValidationStorage

**Location**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/storage.py`

**Purpose**: DuckDB persistent storage for validation reports

**Storage**: `~/.cache/gapless-crypto-data/validation.duckdb` (XDG-compliant)

**Interface**: SQL query interface for flexible data exploration

See [Storage Specification](/Users/terryli/eon/gapless-crypto-data/docs/validation/STORAGE.md) for complete schema details.

## Storage Backend

**Technology**: DuckDB 1.1.0+ (single-file OLAP database)

**Advantages**:

- Zero infrastructure (no server, no setup)
- Columnar storage for analytical queries
- SQL interface for AI agents
- Single-file portability

**Location**: XDG cache directory (`~/.cache/gapless-crypto-data/`)

**Performance**: Indexed queries for fast lookups (symbol+timeframe, timestamp)

## Data Flow

```
CSV File
   ↓
CSVValidator.validate_csv_file()
   ↓
5-Layer Validation Pipeline
   ↓
ValidationReport (Pydantic)
   ↓
store_report=True (optional)
   ↓
ValidationStorage.insert_report()
   ↓
DuckDB (validation.duckdb)
   ↓
Query Interface (SQL/pandas)
```

## Usage Patterns

### Basic Validation (No Persistence)

```python
from gapless_crypto_data.validation import CSVValidator

validator = CSVValidator()
report = validator.validate_csv_file("data/BTCUSDT-1h.csv", expected_timeframe="1h")

if report["total_errors"] == 0:
    print("Validation passed")
else:
    print(f"Errors: {report['total_errors']}")
    print(f"Summary: {report['validation_summary']}")
```

### Validation with Persistence

```python
from gapless_crypto_data.validation import CSVValidator

validator = CSVValidator()
report = validator.validate_csv_file(
    "data/BTCUSDT-1h.csv",
    expected_timeframe="1h",
    store_report=True  # Persist to DuckDB
)
```

### Query Validation History

```python
from gapless_crypto_data.validation import ValidationStorage

storage = ValidationStorage()

# Recent validations
recent = storage.query_recent(limit=10, symbol="BTCUSDT")

# Failed validations
failed = storage.query_by_status("FAILED")

# Summary statistics
stats = storage.get_summary_stats()
print(f"Total: {stats['total_validations']}")
print(f"Avg errors: {stats['avg_errors']}")
```

See [Query Patterns Guide](/Users/terryli/eon/gapless-crypto-data/docs/validation/QUERY_PATTERNS.md) for complete examples.

## Design Principles

### AI-First Design

- SQL query interface for flexible exploration
- Structured JSON schema for machine parsing
- Summary statistics API for trend analysis
- Pandas export for ML/analysis workflows

### Zero-Overhead Persistence

- Optional `store_report=False` (default) for backward compatibility
- No performance impact when disabled
- Automatic database creation on first use
- XDG cache directory compliance

### High-Volume Support

- Efficient columnar storage (1000+ validations/week)
- Microsecond-precision timing (`time.perf_counter()`)
- Automatic numpy/pandas type conversion
- Indexed queries for fast lookups

## Backward Compatibility

All existing code works without modification:

```python
# Existing code (no changes needed)
validator = CSVValidator()
report = validator.validate_csv_file("data.csv")  # Returns dict, no DB storage

# New feature (opt-in)
report = validator.validate_csv_file("data.csv", store_report=True)  # Persists to DuckDB
```

**Default**: `store_report=False` (no persistence)

**Migration**: Add `store_report=True` when persistence desired

## SLOs (Service Level Objectives)

### Correctness

- **100% rule accuracy**: All validation rules must be correct
- **No false positives**: Valid data never flagged as errors
- **No false negatives**: Invalid data always detected

### Observability

- **Complete reporting**: All errors and warnings captured
- **Persistent history**: Validation reports stored indefinitely
- **Query interface**: SQL access for analysis

### Maintainability

- **Single source of truth**: CSVValidator is canonical validator
- **Type safety**: Pydantic models prevent data corruption
- **Test coverage**: Validation tests in `/Users/terryli/eon/gapless-crypto-data/tests/test_validation_storage.py`

## Helper Functions

### Extract Symbol/Timeframe from Path

```python
from gapless_crypto_data.validation import extract_symbol_timeframe_from_path

symbol, timeframe = extract_symbol_timeframe_from_path(
    "binance_spot_BTCUSDT-1h_20240101-20240102_v2.10.0.csv"
)
# Returns: ('BTCUSDT', '1h')
```

**Supported Patterns**:

- `binance_spot_{SYMBOL}-{TIMEFRAME}_{START}-{END}_v{VERSION}.csv`
- `{SYMBOL}-{TIMEFRAME}.csv`
- Various other formats

### Get Database Path

```python
from gapless_crypto_data.validation import get_validation_db_path

db_path = get_validation_db_path()
# Returns: Path('~/.cache/gapless-crypto-data/validation.duckdb')
```

**XDG-Compliant**: Uses `$HOME/.cache/` directory

## Research Workflow Integration

Validation storage designed for high-volume research:

1. **Batch Validation**: Validate 100+ CSV files, store all reports
2. **Trend Analysis**: Query validation history for quality patterns
3. **Regression Detection**: Compare metrics across time periods
4. **AI-Assisted Debugging**: AI agents query database to diagnose issues

**Example Workflow**:

```python
from pathlib import Path
from gapless_crypto_data.validation import CSVValidator, ValidationStorage

validator = CSVValidator()
storage = ValidationStorage()

# Batch validate all CSV files
for csv_file in Path("data/").glob("*.csv"):
    report = validator.validate_csv_file(str(csv_file), store_report=True)
    print(f"Validated {csv_file.name}: {report['validation_summary']}")

# Analyze validation history
stats = storage.get_summary_stats()
print(f"Total validations: {stats['total_validations']}")
print(f"Status distribution: {stats['status_distribution']}")

# Export for analysis
df = storage.export_to_dataframe()
correlation = df[["coverage_percentage", "total_errors"]].corr()
```

## Related Documentation

- **Storage Specification**: [STORAGE.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/STORAGE.md)
- **Query Patterns**: [QUERY_PATTERNS.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/QUERY_PATTERNS.md)
- **Architecture Overview**: [docs/architecture/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/architecture/OVERVIEW.md)
- **Test Suite**: [tests/test_validation_storage.py](/Users/terryli/eon/gapless-crypto-data/tests/test_validation_storage.py)
