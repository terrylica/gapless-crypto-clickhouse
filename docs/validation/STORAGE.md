---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# ValidationStorage Specification

## Purpose

DuckDB-based persistent storage for CSV validation reports with SQL query interface for AI coding agents.

**Location**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/storage.py`

## Database Schema

### Table: `validation_reports`

**30+ columns** with flattened metrics for efficient SQL queries

#### Metadata Columns

| Column                 | Type      | Description                              |
| ---------------------- | --------- | ---------------------------------------- |
| `validation_timestamp` | TIMESTAMP | When validation executed (UTC)           |
| `file_path`            | VARCHAR   | Absolute path to validated CSV file      |
| `file_size_mb`         | DOUBLE    | File size in megabytes                   |
| `validator_version`    | VARCHAR   | CSVValidator version (default: '3.3.0')  |
| `symbol`               | VARCHAR   | Trading symbol (extracted from filename) |
| `timeframe`            | VARCHAR   | Timeframe (e.g., '1h', '5m')             |

#### Core Results Columns

| Column                   | Type    | Description                                           |
| ------------------------ | ------- | ----------------------------------------------------- |
| `total_bars`             | INTEGER | Total rows in CSV file                                |
| `total_errors`           | INTEGER | Count of validation errors                            |
| `total_warnings`         | INTEGER | Count of validation warnings                          |
| `validation_summary`     | VARCHAR | Summary status (e.g., "PERFECT", "GOOD - 2 warnings") |
| `validation_duration_ms` | DOUBLE  | Execution time in milliseconds                        |

#### Layer Results (JSON Columns)

Nested data for detailed layer results:

| Column                 | Type | Description                  |
| ---------------------- | ---- | ---------------------------- |
| `structure_validation` | JSON | Structure validation results |
| `datetime_validation`  | JSON | DateTime validation results  |
| `ohlcv_validation`     | JSON | OHLCV validation results     |
| `coverage_validation`  | JSON | Coverage validation results  |
| `anomaly_validation`   | JSON | Anomaly detection results    |

#### Flattened Metrics (for SQL Queries)

**DateTime Metrics**:

- `date_range_start` (TIMESTAMP) - First timestamp in data
- `date_range_end` (TIMESTAMP) - Last timestamp in data
- `duration_days` (DOUBLE) - Time span in days
- `gaps_found` (INTEGER) - Number of timestamp gaps
- `chronological_order` (BOOLEAN) - Timestamps in order

**Price Metrics**:

- `price_min` (DOUBLE) - Minimum price
- `price_max` (DOUBLE) - Maximum price

**Volume Metrics**:

- `volume_min` (DOUBLE) - Minimum volume
- `volume_max` (DOUBLE) - Maximum volume
- `volume_mean` (DOUBLE) - Average volume

**Quality Metrics**:

- `ohlc_errors` (INTEGER) - OHLC logic violations
- `negative_zero_values` (INTEGER) - Invalid values count

**Coverage Metrics**:

- `expected_bars` (INTEGER) - Expected bar count
- `actual_bars` (INTEGER) - Actual bar count
- `coverage_percentage` (DOUBLE) - Coverage percentage

**Anomaly Metrics**:

- `price_outliers` (INTEGER) - Price outlier count
- `volume_outliers` (INTEGER) - Volume outlier count
- `suspicious_patterns` (INTEGER) - Suspicious pattern count

### Indexes

Optimized for common query patterns:

```sql
-- Primary key
PRIMARY KEY (validation_timestamp, file_path)

-- Common filters
CREATE INDEX idx_symbol_timeframe ON validation_reports(symbol, timeframe);
CREATE INDEX idx_validation_timestamp ON validation_reports(validation_timestamp DESC);
CREATE INDEX idx_validation_summary ON validation_reports(validation_summary);
```

## Database Location

**Path**: `~/.cache/gapless-crypto-data/validation.duckdb`

**Standard**: XDG Base Directory Specification

**Platform**:

- macOS/Linux: `$HOME/.cache/gapless-crypto-data/validation.duckdb`
- Automatic directory creation if missing

## API Methods

### insert_report()

```python
storage.insert_report(report: ValidationReport) -> None
```

Insert validation report into DuckDB.

**Parameters**:

- `report`: ValidationReport (Pydantic model)

**Raises**: DuckDB exceptions on failure (no silent handling)

### query_recent()

```python
storage.query_recent(
    limit: int = 10,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
) -> List[Dict]
```

Query recent validation reports (newest first).

**Parameters**:

- `limit`: Maximum results
- `symbol`: Filter by symbol (optional)
- `timeframe`: Filter by timeframe (optional)

**Returns**: List of validation report dictionaries

### query_by_status()

```python
storage.query_by_status(status: str) -> List[Dict]
```

Query validations by status substring.

**Parameters**:

- `status`: Status string (e.g., "PERFECT", "GOOD", "FAILED")

**Returns**: List of matching validation reports

**Matching**: Case-insensitive substring match in `validation_summary`

### query_by_date_range()

```python
storage.query_by_date_range(
    start: datetime,
    end: datetime,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
) -> List[Dict]
```

Query validations within date range.

**Parameters**:

- `start`: Start datetime (inclusive)
- `end`: End datetime (inclusive)
- `symbol`: Filter by symbol (optional)
- `timeframe`: Filter by timeframe (optional)

**Returns**: List of validation reports in range

### export_to_dataframe()

```python
storage.export_to_dataframe(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
) -> pd.DataFrame
```

Export validation history to pandas DataFrame.

**Parameters**:

- `symbol`: Filter by symbol (optional)
- `timeframe`: Filter by timeframe (optional)

**Returns**: pandas DataFrame with all columns

**Use Case**: ML analysis, correlation studies, visualization

### get_summary_stats()

```python
storage.get_summary_stats() -> Dict[str, Any]
```

Get aggregate statistics across all validations.

**Returns**:

```python
{
    'total_validations': int,
    'symbols': List[str],
    'timeframes': List[str],
    'avg_errors': float,
    'avg_warnings': float,
    'status_distribution': Dict[str, int]
}
```

## Storage Characteristics

### Performance

- **Columnar storage**: Fast analytical queries
- **Indexed queries**: Sub-millisecond lookups on indexes
- **Batch inserts**: Efficient for high-volume validation

### Capacity

- **1000+ validations/week**: Efficient storage
- **Years of history**: No practical size limit
- **Single file**: Easy backup and portability

### Data Integrity

- **ACID transactions**: Guaranteed consistency
- **Type safety**: Pydantic validation before insert
- **Primary key constraint**: No duplicate validation timestamps for same file

## SLOs (Service Level Objectives)

### Correctness

- **100% data preservation**: All validation results stored accurately
- **Type safety**: Pydantic validation before persistence
- **No data loss**: ACID transactions guarantee atomicity

### Observability

- **Complete history**: All validations queryable
- **SQL interface**: Flexible ad-hoc queries
- **Export capability**: pandas DataFrame for analysis

### Maintainability

- **Single file**: Easy backup and migration
- **XDG-compliant**: Standard cache location
- **Schema versioned**: Database schema tracked in code

## Usage Examples

### Basic Insert

```python
from gapless_crypto_data.validation import ValidationStorage, ValidationReport

storage = ValidationStorage()

# Assume `report` is a ValidationReport from CSVValidator
storage.insert_report(report)
```

### Query Recent Validations

```python
storage = ValidationStorage()
recent = storage.query_recent(limit=5, symbol="BTCUSDT", timeframe="1h")

for report in recent:
    print(f"{report['validation_timestamp']}: {report['validation_summary']}")
```

### Export for Analysis

```python
import pandas as pd
from gapless_crypto_data.validation import ValidationStorage

storage = ValidationStorage()
df = storage.export_to_dataframe()

# Analyze error distribution
error_stats = df.groupby("symbol")["total_errors"].describe()
print(error_stats)

# Find problematic files
problematic = df[df["total_errors"] > 0]
print(f"Files with errors: {len(problematic)}")
```

## Direct SQL Access

Advanced users can query DuckDB directly:

```python
import duckdb
from gapless_crypto_data.validation import get_validation_db_path

db_path = get_validation_db_path()

with duckdb.connect(str(db_path)) as conn:
    # Custom SQL query
    result = conn.execute("""
        SELECT symbol, timeframe, COUNT(*) as validation_count
        FROM validation_reports
        WHERE total_errors = 0
        GROUP BY symbol, timeframe
        ORDER BY validation_count DESC
    """).fetchdf()

    print(result)
```

## Related Documentation

- **Validation Overview**: [OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/OVERVIEW.md)
- **Query Patterns**: [QUERY_PATTERNS.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/QUERY_PATTERNS.md)
- **ValidationReport Model**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/models.py`
- **Test Suite**: `/Users/terryli/eon/gapless-crypto-data/tests/test_validation_storage.py`
