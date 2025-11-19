# clickhouse-local File Analysis Guide

## Overview

`clickhouse-local` is an embedded ClickHouse engine that queries local and remote files using full ClickHouse SQL without requiring a running server. Perfect for file validation, format conversion, and ad-hoc analysis.

**Use Cases**:
- Pre-ingestion CSV/Parquet validation
- Format conversion (CSV ↔ JSON ↔ Parquet)
- Ad-hoc file analysis without database
- ETL preprocessing and validation

**NOT Suitable For**:
- gapless-crypto-data primary database (requires persistent ReplacingMergeTree)
- Production workloads (no persistence by default)
- Multi-user access (single-process, local-only)

## Installation

### Via Docker (Bundled)
```bash
# Already available in ClickHouse container
docker exec gapless-clickhouse clickhouse-local --version
```

### Native Binary
```bash
# Download single binary
curl https://clickhouse.com/ | sh

# Make executable
chmod +x ./clickhouse

# Run
./clickhouse local --query "SELECT 1"
```

## Quick Start

### Query Local Files
```bash
# CSV file
clickhouse-local --query "SELECT * FROM file('data.csv', CSV) LIMIT 10"

# JSON Lines
clickhouse-local --query "SELECT * FROM file('data.jsonl', JSONEachRow) LIMIT 10"

# Parquet
clickhouse-local --query "SELECT * FROM file('data.parquet', Parquet) LIMIT 10"

# Multiple files (glob pattern)
clickhouse-local --query "SELECT * FROM file('data/*.csv', CSV)"
```

### Query Remote Files
```bash
# S3 (no download required)
clickhouse-local --query "
  SELECT count()
  FROM s3('https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/*.zip')
"

# HTTP
clickhouse-local --query "
  SELECT *
  FROM url('https://example.com/data.csv', CSV)
  LIMIT 10
"
```

## Common Workflows

### Format Conversion

#### CSV to Parquet
```bash
clickhouse-local \
  --input-format CSV \
  --output-format Parquet \
  --query "SELECT * FROM table" \
  < data.csv > data.parquet
```

#### JSON to CSV
```bash
clickhouse-local \
  --input-format JSONEachRow \
  --output-format CSV \
  --query "SELECT * FROM table" \
  < data.jsonl > data.csv
```

#### Parquet to JSON
```bash
clickhouse-local --query "
  SELECT * FROM file('data.parquet', Parquet)
  FORMAT JSONEachRow
" > data.jsonl
```

### Data Validation

#### CSV Schema Inference
```bash
# Infer column types
clickhouse-local --query "
  DESCRIBE TABLE file('data.csv', CSV)
"

# Example output:
# timestamp  DateTime
# symbol     String
# close      Float64
```

#### Check for Duplicates
```bash
clickhouse-local --query "
  SELECT
    count() as total_rows,
    count(DISTINCT timestamp, symbol) as unique_rows,
    total_rows - unique_rows as duplicates
  FROM file('ohlcv.csv', CSV)
"
```

#### Find Nulls/Invalid Data
```bash
clickhouse-local --query "
  SELECT
    countIf(close IS NULL) as null_close,
    countIf(close < 0) as negative_close,
    countIf(volume < 0) as negative_volume
  FROM file('ohlcv.csv', CSV)
"
```

### Pre-Ingestion Validation

#### Validate CSV Before ClickHouse Ingestion
```bash
# 1. Check schema matches expected
clickhouse-local --query "
  SELECT
    name,
    type
  FROM (
    DESCRIBE TABLE file('incoming.csv', CSV)
  )
  ORDER BY name
"

# 2. Validate data types
clickhouse-local --query "
  SELECT
    count() as total_rows,
    min(timestamp) as earliest,
    max(timestamp) as latest,
    count(DISTINCT symbol) as symbols
  FROM file('incoming.csv', CSV)
"

# 3. Check for gaps (hourly data)
clickhouse-local --query "
  WITH lagged AS (
    SELECT
      timestamp,
      lag(timestamp) OVER (ORDER BY timestamp) as prev_ts
    FROM file('incoming.csv', CSV)
    WHERE symbol = 'BTCUSDT'
  )
  SELECT
    prev_ts,
    timestamp,
    dateDiff('hour', prev_ts, timestamp) as gap_hours
  FROM lagged
  WHERE gap_hours > 1
  ORDER BY timestamp
"
```

### Aggregation and Analysis

#### Summary Statistics
```bash
clickhouse-local --query "
  SELECT
    count() as rows,
    avg(close) as avg_price,
    stddevPop(close) as std_price,
    min(close) as min_price,
    max(close) as max_price,
    sum(volume) as total_volume
  FROM file('btcusdt.csv', CSV)
"
```

#### Time-Series Aggregation
```bash
# Daily aggregation from hourly data
clickhouse-local --query "
  SELECT
    toStartOfDay(timestamp) as date,
    argMin(close, timestamp) as open,
    max(close) as high,
    min(close) as low,
    argMax(close, timestamp) as close,
    sum(volume) as volume
  FROM file('hourly.csv', CSV)
  GROUP BY date
  ORDER BY date
" > daily.csv
```

#### Join Multiple Files
```bash
# Join price data with metadata
clickhouse-local --query "
  SELECT
    p.timestamp,
    p.symbol,
    m.name as symbol_name,
    m.category,
    p.close,
    p.volume
  FROM file('prices.csv', CSV) p
  LEFT JOIN file('metadata.csv', CSV) m
    ON p.symbol = m.symbol
  ORDER BY p.timestamp
"
```

## Advanced Features

### Create Persistent Database
```bash
# Create local database directory
mkdir -p /tmp/clickhouse_local_db

# Use persistent path
clickhouse-local --path /tmp/clickhouse_local_db --query "
  CREATE DATABASE IF NOT EXISTS mydb;

  CREATE TABLE mydb.test (
    id UInt64,
    name String
  ) ENGINE = MergeTree()
  ORDER BY id;

  INSERT INTO mydb.test VALUES (1, 'Alice'), (2, 'Bob');

  SELECT * FROM mydb.test;
"

# Data persists across invocations
clickhouse-local --path /tmp/clickhouse_local_db --query "SELECT * FROM mydb.test"
```

### Stream Processing
```bash
# Process large files without loading into memory
cat large_file.csv | clickhouse-local --input-format CSV --query "
  SELECT
    symbol,
    avg(close) as avg_close
  FROM table
  GROUP BY symbol
" --output-format PrettyCompact
```

### Complex Transformations
```bash
# Calculate returns, volatility, technical indicators
clickhouse-local --query "
  SELECT
    timestamp,
    close,
    close / lag(close) OVER (ORDER BY timestamp) - 1 as returns,
    avg(close) OVER (ORDER BY timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as sma_20,
    stddevPop(close) OVER (ORDER BY timestamp ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as volatility_20
  FROM file('btcusdt.csv', CSV)
  ORDER BY timestamp
" > btcusdt_indicators.csv
```

## File Formats

### Supported Input Formats
- CSV / TSV / CSVWithNames / TabSeparated
- JSON / JSONEachRow / JSONCompact
- Parquet / Arrow / ORC
- Native (ClickHouse binary)
- RowBinary / RowBinaryWithNamesAndTypes
- Values (INSERT format)

### Format Detection
```bash
# Automatic format detection by extension
clickhouse-local --query "SELECT * FROM file('data.csv')"  # Auto-detects CSV
clickhouse-local --query "SELECT * FROM file('data.parquet')"  # Auto-detects Parquet
clickhouse-local --query "SELECT * FROM file('data.json')"  # Auto-detects JSON

# Explicit format (recommended for clarity)
clickhouse-local --query "SELECT * FROM file('data.txt', CSV)"
```

## Comparison with clickhouse-client

| Feature | clickhouse-local | clickhouse-client |
|---------|-----------------|-------------------|
| Server Required | ❌ No | ✅ Yes |
| File Queries | ✅ Native | ⚠️ Via external tables |
| S3/HTTP Queries | ✅ Direct | ✅ Direct |
| Persistent DB | ⚠️ Optional | ✅ Always |
| Table Engines | ⚠️ Limited | ✅ All |
| ReplacingMergeTree | ❌ No | ✅ Yes |
| Deduplication | ❌ No | ✅ Yes |
| Best For | File analysis | Database queries |

## Use Cases for gapless-crypto-data

### ✅ Recommended Uses

1. **Pre-Ingestion Validation**
   ```bash
   # Validate Binance CSV before ingesting to ClickHouse
   clickhouse-local --query "
     SELECT
       count() as rows,
       count(DISTINCT symbol) as symbols,
       min(timestamp) as start,
       max(timestamp) as end
     FROM file('binance_download.csv', CSV)
   "
   ```

2. **Format Conversion**
   ```bash
   # Convert Binance data to Parquet for faster loading
   clickhouse-local --query "
     SELECT * FROM file('binance/*.csv', CSV)
   " --output-format Parquet > optimized.parquet
   ```

3. **Exploratory Analysis**
   ```bash
   # Quick stats on downloaded data
   clickhouse-local --query "
     SELECT
       symbol,
       count() as bars,
       formatReadableSize(sum(volume * close)) as notional_volume
     FROM file('*.csv', CSV)
     GROUP BY symbol
   "
   ```

### ❌ NOT Recommended

1. **Primary Database**: Use ClickHouse server instead (requires ReplacingMergeTree for deduplication)
2. **Production Pipelines**: Use ClickHouse server for reliability and persistence
3. **Multi-User Access**: clickhouse-local is single-process, local-only

## Troubleshooting

### File Not Found
```bash
# Use absolute paths
clickhouse-local --query "SELECT * FROM file('/full/path/to/data.csv', CSV)"

# Or run from file directory
cd /path/to/files
clickhouse-local --query "SELECT * FROM file('data.csv', CSV)"
```

### Schema Mismatch
```bash
# Inspect inferred schema
clickhouse-local --query "DESCRIBE TABLE file('data.csv', CSV)"

# Force schema
clickhouse-local --query "
  SELECT * FROM file('data.csv', CSV, 'timestamp DateTime, symbol String, close Float64')
"
```

### Memory Limits
```bash
# Increase memory limit
clickhouse-local --max_memory_usage 10000000000 --query "SELECT * FROM file('large.csv', CSV)"

# Use streaming (no memory limit)
cat large.csv | clickhouse-local --input-format CSV --query "SELECT count() FROM table"
```

## Next Steps

- **For persistent database**: Use [ClickHouse server](../../docker-compose.yml)
- **For automation**: Use [clickhouse-client](./CLICKHOUSE_CLIENT_GUIDE.md)
- **For exploration**: Use [CH-UI](../CHUI_GUIDE.md)

## References

- Official docs: https://clickhouse.com/docs/en/operations/utilities/clickhouse-local
- File functions: https://clickhouse.com/docs/en/sql-reference/table-functions/file
- S3 functions: https://clickhouse.com/docs/en/sql-reference/table-functions/s3
- ADR-0008: ClickHouse Local Visualization Toolchain
