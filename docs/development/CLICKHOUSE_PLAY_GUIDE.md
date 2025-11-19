# ClickHouse Play Usage Guide

## Overview

ClickHouse Play is a built-in web interface that ships with ClickHouse 20.11+ for quick ad-hoc queries. It requires zero installation and provides instant access via the HTTP interface.

## Access

**URL**: http://localhost:8123/play

**Availability**: Already running with your Docker ClickHouse container

## Features

### Supported
- ✅ Query execution with results display
- ✅ Query history via URL base64 encoding
- ✅ Simple tabular results display
- ✅ Shareable query URLs (history encoded in URL)

### Limitations
- ❌ Results limited to **10,000 rows**
- ❌ Results limited to **1MB** total size
- ❌ No progress indicator
- ❌ No default database selection (must use fully qualified names)
- ❌ No charting/visualization capabilities
- ❌ No schema management features
- ❌ Basic interface (no IntelliSense, syntax highlighting)

## Quick Start

### 1. Open Play UI
```bash
open http://localhost:8123/play
```

### 2. Run Your First Query
```sql
SELECT 1
```

### 3. Query the Database
```sql
-- Must use fully qualified table names (database.table)
SELECT count() FROM default.ohlcv

-- Show all tables
SHOW TABLES FROM default

-- Explore schema
DESCRIBE TABLE default.ohlcv
```

## Example Queries

### Basic Data Exploration
```sql
-- Count total bars by symbol
SELECT
    symbol,
    count() as bar_count
FROM default.ohlcv FINAL
GROUP BY symbol
ORDER BY bar_count DESC

-- Latest data for BTCUSDT 1h
SELECT
    timestamp,
    open,
    high,
    low,
    close,
    volume
FROM default.ohlcv FINAL
WHERE symbol = 'BTCUSDT'
  AND timeframe = '1h'
ORDER BY timestamp DESC
LIMIT 100

-- Date range summary
SELECT
    symbol,
    timeframe,
    min(timestamp) as first_bar,
    max(timestamp) as last_bar,
    count() as total_bars
FROM default.ohlcv FINAL
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe
```

### Gap Detection
```sql
-- Find gaps in data (missing hours)
WITH lagged AS (
    SELECT
        symbol,
        timeframe,
        timestamp,
        lagInFrame(timestamp) OVER (
            PARTITION BY symbol, timeframe
            ORDER BY timestamp
        ) as prev_timestamp
    FROM default.ohlcv FINAL
    WHERE symbol = 'BTCUSDT'
      AND timeframe = '1h'
)
SELECT
    prev_timestamp,
    timestamp,
    dateDiff('hour', prev_timestamp, timestamp) as hours_gap
FROM lagged
WHERE prev_timestamp != toDateTime(0)
  AND dateDiff('hour', prev_timestamp, timestamp) > 1
ORDER BY timestamp
```

## Best Practices

### When to Use Play UI
- ✅ Quick sanity checks (row counts, schema validation)
- ✅ Testing query syntax before using in code
- ✅ Sharing query results via URL
- ✅ One-off administrative queries

### When NOT to Use Play UI
- ❌ Exploring large datasets (>10K rows) → Use CH-UI instead
- ❌ Complex multi-query workflows → Use clickhouse-client instead
- ❌ Schema modifications (DDL) → Use clickhouse-client or CH-UI
- ❌ Performance analysis → Use chdig instead
- ❌ Data visualization (charts) → Use CH-UI or Python tools

## Query URL Sharing

Play UI encodes queries in the URL for easy sharing:

```
http://localhost:8123/play#<base64-encoded-query>
```

**Example**:
1. Run query: `SELECT count() FROM default.ohlcv`
2. Copy URL from browser (includes base64-encoded query)
3. Share URL with team (query auto-populates when opened)

## Troubleshooting

### "Connection refused"
**Cause**: ClickHouse HTTP interface not running

**Solution**:
```bash
# Check ClickHouse container status
docker ps | grep clickhouse

# If not running, start it
docker-compose up -d clickhouse

# Test HTTP interface
curl http://localhost:8123/ping
```

### "Database default doesn't exist"
**Cause**: Schema not initialized

**Solution**:
```bash
# Check if tables exist
docker exec gapless-clickhouse clickhouse-client --query "SHOW TABLES FROM default"

# If empty, schema may not have loaded
docker-compose down && docker-compose up -d
```

### "Results too large"
**Cause**: Query returns >10K rows or >1MB data

**Solution**: Use CH-UI or clickhouse-client instead
```bash
# CH-UI (no limits)
open http://localhost:5521

# OR clickhouse-client
docker exec -it gapless-clickhouse clickhouse-client
```

## Comparison with Other Tools

| Feature | Play UI | CH-UI | clickhouse-client |
|---------|---------|-------|-------------------|
| Installation | ✅ Built-in | Docker | Built-in |
| Result Limit | 10K rows | Unlimited | Unlimited |
| Charts | ❌ No | ✅ Yes | ❌ No |
| Syntax Highlighting | ❌ No | ✅ Yes | ✅ Yes |
| Schema Browser | ❌ No | ✅ Yes | ⚠️ CLI |
| Multi-query | ❌ No | ✅ Yes | ✅ Yes |
| Best For | Quick checks | Exploration | Automation |

## Next Steps

- **For richer exploration**: Use [CH-UI](../CHUI_GUIDE.md) (http://localhost:5521)
- **For automation**: Use [clickhouse-client](./CLICKHOUSE_CLIENT_GUIDE.md)
- **For monitoring**: Use [chdig](./CHDIG_GUIDE.md)

## References

- Official docs: https://clickhouse.com/docs/en/interfaces/http
- ClickHouse Play: Included with ClickHouse 20.11+
- ADR-0008: ClickHouse Local Visualization Toolchain
