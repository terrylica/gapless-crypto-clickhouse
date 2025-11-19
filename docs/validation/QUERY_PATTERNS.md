---
version: "1.0.1"
last_updated: "2025-10-28"
canonical_source: true
supersedes: ["1.0.0"]
---

# Validation Query Patterns for AI Agents

## Purpose

Common query patterns for AI coding agents to analyze validation history and diagnose data quality issues.

All examples use `ValidationStorage` from `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/validation/storage.py`

## Basic Query Patterns

### Recent Validations

Query most recent validation reports:

```python
from gapless_crypto_data.validation import ValidationStorage

storage = ValidationStorage()
recent = storage.query_recent(limit=10)

for report in recent:
    print(f"{report['validation_timestamp']}: {report['file_path']}")
    print(f"  Status: {report['validation_summary']}")
    print(f"  Errors: {report['total_errors']}, Warnings: {report['total_warnings']}")
```

### Recent Validations for Specific Symbol

```python
recent_btc = storage.query_recent(limit=10, symbol="BTCUSDT")

for report in recent_btc:
    print(f"{report['timeframe']}: {report['validation_summary']}")
```

### Recent Validations for Specific Timeframe

```python
hourly_validations = storage.query_recent(limit=10, timeframe="1h")

for report in hourly_validations:
    print(f"{report['symbol']}: {report['total_errors']} errors")
```

## Status-Based Queries

### Failed Validations

Find all failed validations:

```python
failed = storage.query_by_status("FAILED")

print(f"Found {len(failed)} failed validations")

for record in failed:
    print(f"{record['file_path']}: {record['validation_summary']}")
    print(f"  Errors: {record['total_errors']}")
    print(f"  Gaps: {record['gaps_found']}")
```

### Perfect Validations

Find validations with no errors or warnings:

```python
perfect = storage.query_by_status("PERFECT")

print(f"Found {len(perfect)} perfect validations")
```

### Validations with Warnings

```python
warnings_only = storage.query_by_status("GOOD")

for record in warnings_only:
    print(f"{record['file_path']}: {record['total_warnings']} warnings")
```

## Date Range Queries

### Validations in Last Month

```python
from datetime import datetime, timedelta

end = datetime.now()
start = end - timedelta(days=30)

last_month = storage.query_by_date_range(start, end)

print(f"Validations in last 30 days: {len(last_month)}")
```

### Specific Month Analysis

```python
from datetime import datetime

start = datetime(2025, 10, 1)
end = datetime(2025, 10, 31)

october = storage.query_by_date_range(start, end, symbol="BTCUSDT")

print(f"BTCUSDT validations in October 2025: {len(october)}")
```

### Symbol-Specific Date Range

```python
start = datetime(2025, 1, 1)
end = datetime(2025, 12, 31)

btc_2025 = storage.query_by_date_range(start, end, symbol="BTCUSDT", timeframe="1h")

errors = sum(r['total_errors'] for r in btc_2025)
print(f"Total errors in BTCUSDT-1h for 2025: {errors}")
```

## Summary Statistics

### Overall Statistics

```python
stats = storage.get_summary_stats()

print(f"Total validations: {stats['total_validations']}")
print(f"Symbols: {', '.join(stats['symbols'])}")
print(f"Timeframes: {', '.join(stats['timeframes'])}")
print(f"Average errors: {stats['avg_errors']:.2f}")
print(f"Average warnings: {stats['avg_warnings']:.2f}")
print(f"Status distribution: {stats['status_distribution']}")
```

### Status Distribution Analysis

```python
stats = storage.get_summary_stats()

for status, count in stats['status_distribution'].items():
    percentage = (count / stats['total_validations']) * 100
    print(f"{status}: {count} ({percentage:.1f}%)")
```

## DataFrame Export Patterns

### Export All Validations

```python
import pandas as pd
from gapless_crypto_data.validation import ValidationStorage

storage = ValidationStorage()
df = storage.export_to_dataframe()

print(f"Total validations: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
```

### Symbol-Specific Analysis

```python
btc_df = storage.export_to_dataframe(symbol="BTCUSDT")

# Analyze error distribution by timeframe
error_stats = btc_df.groupby("timeframe")["total_errors"].describe()
print(error_stats)
```

### Timeframe-Specific Analysis

```python
hourly_df = storage.export_to_dataframe(timeframe="1h")

# Find files with low coverage
low_coverage = hourly_df[hourly_df["coverage_percentage"] < 95.0]
print(f"Files with <95% coverage: {len(low_coverage)}")
```

### Correlation Analysis

```python
df = storage.export_to_dataframe()

# Correlation between coverage and errors
correlation = df[["coverage_percentage", "total_errors"]].corr()
print(correlation)
```

### Identify Problematic Files

```python
df = storage.export_to_dataframe()

# Files with errors
problematic = df[df["total_errors"] > 0]
print(f"Files with errors: {len(problematic)}")

# Sort by error count
worst_files = problematic.sort_values("total_errors", ascending=False).head(10)
print("\nWorst 10 files:")
for idx, row in worst_files.iterrows():
    print(f"  {row['file_path']}: {row['total_errors']} errors")
```

### Gap Analysis

```python
df = storage.export_to_dataframe()

# Files with gaps
files_with_gaps = df[df["gaps_found"] > 0]
print(f"Files with gaps: {len(files_with_gaps)}")

# Average gap count
avg_gaps = files_with_gaps["gaps_found"].mean()
print(f"Average gaps (for files with gaps): {avg_gaps:.2f}")
```

### Outlier Detection

```python
df = storage.export_to_dataframe()

# Files with price outliers
price_outliers = df[df["price_outliers"] > 0]
print(f"Files with price outliers: {len(price_outliers)}")

# Files with volume outliers
volume_outliers = df[df["volume_outliers"] > 0]
print(f"Files with volume outliers: {len(volume_outliers)}")
```

## Advanced SQL Queries

### Direct DuckDB Access

For custom queries beyond the API:

```python
import duckdb
from gapless_crypto_data.validation import get_validation_db_path

db_path = get_validation_db_path()

with duckdb.connect(str(db_path)) as conn:
    # Custom SQL query
    result = conn.execute("""
        SELECT
            symbol,
            timeframe,
            COUNT(*) as validation_count,
            AVG(total_errors) as avg_errors,
            AVG(coverage_percentage) as avg_coverage
        FROM validation_reports
        WHERE total_errors = 0
        GROUP BY symbol, timeframe
        ORDER BY validation_count DESC
    """).fetchdf()

    print(result)
```

### Time-Series Analysis

```python
with duckdb.connect(str(db_path)) as conn:
    result = conn.execute("""
        SELECT
            DATE_TRUNC('day', validation_timestamp) as day,
            COUNT(*) as validations_per_day,
            AVG(total_errors) as avg_errors_per_day
        FROM validation_reports
        GROUP BY day
        ORDER BY day DESC
        LIMIT 30
    """).fetchdf()

    print(result)
```

### Symbol Comparison

```python
with duckdb.connect(str(db_path)) as conn:
    result = conn.execute("""
        SELECT
            symbol,
            COUNT(*) as total_validations,
            SUM(CASE WHEN total_errors > 0 THEN 1 ELSE 0 END) as failed_count,
            AVG(coverage_percentage) as avg_coverage,
            AVG(gaps_found) as avg_gaps
        FROM validation_reports
        GROUP BY symbol
        ORDER BY total_validations DESC
    """).fetchdf()

    print(result)
```

## Batch Validation Workflow

### Validate Multiple Files and Analyze

```python
from pathlib import Path
from gapless_crypto_data.validation import CSVValidator, ValidationStorage

validator = CSVValidator()
storage = ValidationStorage()

# Batch validate
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
```

## Research Patterns

### Trend Detection

```python
df = storage.export_to_dataframe()

# Convert timestamp to datetime
df['validation_timestamp'] = pd.to_datetime(df['validation_timestamp'])

# Group by week and analyze trends
df['week'] = df['validation_timestamp'].dt.isocalendar().week
weekly_stats = df.groupby('week').agg({
    'total_errors': 'mean',
    'coverage_percentage': 'mean',
    'gaps_found': 'mean'
})

print("Weekly trends:")
print(weekly_stats)
```

### Quality Regression Detection

```python
# Compare recent validations to historical baseline
recent_df = storage.export_to_dataframe()
recent_df['validation_timestamp'] = pd.to_datetime(recent_df['validation_timestamp'])

# Last 7 days vs previous 30 days
seven_days_ago = datetime.now() - timedelta(days=7)
thirty_days_ago = datetime.now() - timedelta(days=30)

recent = recent_df[recent_df['validation_timestamp'] > seven_days_ago]
baseline = recent_df[
    (recent_df['validation_timestamp'] > thirty_days_ago) &
    (recent_df['validation_timestamp'] <= seven_days_ago)
]

print(f"Recent avg errors: {recent['total_errors'].mean():.2f}")
print(f"Baseline avg errors: {baseline['total_errors'].mean():.2f}")

if recent['total_errors'].mean() > baseline['total_errors'].mean():
    print("⚠️  Quality regression detected")
```

## SLOs (Service Level Objectives)

### Correctness

**Query Accuracy**: All SQL patterns return accurate results matching DuckDB query semantics

**API Consistency**: ValidationStorage API methods produce results equivalent to direct SQL queries

**Data Integrity**: All exported DataFrames maintain referential integrity with underlying DuckDB tables

### Observability

**Query Examples**: All common query patterns documented with working code examples

**API Discovery**: All ValidationStorage query methods documented with return type specifications

**Performance Context**: Query complexity noted for large result sets (DataFrame exports, full scans)

### Maintainability

**Pattern Library**: Query patterns organized by use case (common queries, batch workflows, research patterns)

**SQL Standards**: Direct SQL examples use standard DuckDB syntax (portable to other SQL databases)

**Documentation Sync**: Query patterns kept in sync with ValidationStorage API evolution

## Related Documentation

- **Validation Overview**: [OVERVIEW.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/OVERVIEW.md)
- **Storage Specification**: [STORAGE.md](/Users/terryli/eon/gapless-crypto-data/docs/validation/STORAGE.md)
- **Test Examples**: `/Users/terryli/eon/gapless-crypto-data/tests/test_validation_storage.py`
