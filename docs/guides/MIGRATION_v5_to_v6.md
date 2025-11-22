# Migration Guide: v5.0.0 → v6.0.0

**Release Date**: 2025-11-20
**ADR**: [0023-arrow-migration](../architecture/decisions/0023-arrow-migration.md)

---

## Summary

v6.0.0 introduces Apache Arrow optimization for 2x faster queries at scale, unified `query_ohlcv()` API with auto-ingestion, and AI discoverability features. This is a **major version** with breaking changes to the connection module.

**Key Changes**:

- ✅ **New**: `query_ohlcv()` with auto-ingestion (downloads data if missing)
- ✅ **Performance**: 2x faster queries at scale (>8000 rows) via Apache Arrow
- ✅ **Memory**: 43-57% less memory for medium/large datasets
- ✅ **AI Ready**: llms.txt + probe.py for capability discovery
- ⚠️ **Breaking**: Protocol change (Native TCP port 9000 → HTTP port 8123)
- ⚠️ **Breaking**: Driver change (clickhouse-driver → clickhouse-connect)

---

## Migration Checklist

- [ ] Update ClickHouse port configuration (9000 → 8123)
- [ ] Update exception handling (ClickHouseError → Exception)
- [ ] Update connection instantiation (if using custom config)
- [ ] Test existing queries (FINAL keyword still works)
- [ ] Optional: Migrate to `query_ohlcv()` for auto-ingestion
- [ ] Optional: Use probe module if building AI agents

---

## Breaking Changes

### 1. Protocol Change: TCP → HTTP

**Before (v5.0.0)**:

```python
# Native TCP protocol (port 9000)
CLICKHOUSE_PORT=9000  # Default
```

**After (v6.0.0)**:

```python
# HTTP protocol (port 8123)
CLICKHOUSE_HTTP_PORT=8123  # Default
```

**Migration**:

```bash
# Update .env file
# OLD: CLICKHOUSE_PORT=9000
# NEW: CLICKHOUSE_HTTP_PORT=8123

# Or use environment variable
export CLICKHOUSE_HTTP_PORT=8123
```

**If using Docker Compose**, update port mapping:

```yaml
# docker-compose.yml
services:
  clickhouse:
    ports:
      - "8123:8123" # HTTP port (NEW)
      # - "9000:9000"  # Native TCP (OLD, remove if not needed)
```

### 2. Driver Change: clickhouse-driver → clickhouse-connect

**Before (v5.0.0)**:

```python
from clickhouse_driver.errors import Error as ClickHouseError

try:
    # ... query code
except ClickHouseError as e:
    print(f"ClickHouse error: {e}")
```

**After (v6.0.0)**:

```python
# clickhouse-connect uses standard exceptions
try:
    # ... query code
except Exception as e:
    print(f"ClickHouse error: {e}")
```

**Migration**:

1. Remove `from clickhouse_driver.errors import Error as ClickHouseError`
2. Replace `ClickHouseError` with `Exception` in error handling
3. No functional change - error handling behavior unchanged

### 3. Connection API (Advanced Users Only)

If you're using the low-level `ClickHouseConnection` class directly:

**Before (v5.0.0)**:

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

with ClickHouseConnection() as conn:
    # health_check() returned None on success
    conn.health_check()  # Raised exception on failure

    # Client access
    result = conn.client.execute("SELECT 1")
```

**After (v6.0.0)**:

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

with ClickHouseConnection() as conn:
    # health_check() now returns bool
    if not conn.health_check():
        raise Exception("Health check failed")

    # Client access unchanged (abstracted)
    result = conn.execute("SELECT 1")  # Use wrapper method
```

**Migration**:

- Update health check to use boolean return value
- Prefer wrapper methods (`conn.execute()`, `conn.query_dataframe()`) over direct client access

---

## New Features

### 1. Unified Query API: `query_ohlcv()`

The **recommended way** to query data in v6.0.0+ is using the new unified API:

**New in v6.0.0**:

```python
from gapless_crypto_clickhouse import query_ohlcv

# Query with auto-ingestion (downloads data if missing)
df = query_ohlcv(
    "BTCUSDT",
    "1h",
    "2024-01-01",
    "2024-01-31"
)
# First call: Downloads + ingests + queries (30-60s)
# Subsequent calls: Queries only (0.1-2s, cached in ClickHouse)

# Multi-symbol query
df = query_ohlcv(
    ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "1h",
    "2024-01-01",
    "2024-01-31"
)

# Futures data
df = query_ohlcv(
    "BTCUSDT",
    "1h",
    "2024-01-01",
    "2024-01-31",
    instrument_type="futures-um"
)
```

**Benefits**:

- **Auto-ingestion**: No manual download step required
- **Idempotent**: Safe to call repeatedly, downloads only if data missing
- **Arrow-optimized**: 2x faster at scale, 43-57% less memory
- **Simple**: Single function for most use cases

**Migration from v5.0.0**:

```python
# OLD (v5.0.0): Manual workflow
from gapless_crypto_clickhouse import download
from gapless_crypto_clickhouse.clickhouse_query import OHLCVQuery
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

# Step 1: Download data
df_download = download("BTCUSDT", "1h", "2024-01-01", "2024-01-31")

# Step 2: Ingest to ClickHouse (manual bulk loader setup)
# ... (complex ingestion code)

# Step 3: Query from ClickHouse
with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)
    df = query.get_range("BTCUSDT", "1h", "2024-01-01", "2024-01-31")

# NEW (v6.0.0): Unified API
from gapless_crypto_clickhouse import query_ohlcv

# All steps in one call
df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
```

### 2. Apache Arrow Optimization

All queries use Apache Arrow internally for 2x speedup at scale:

**Performance Characteristics**:

- **Small queries** (<1000 rows): HTTP protocol overhead ~30-40%
- **Medium queries** (1000-5000 rows): 1.5-1.8x faster
- **Large queries** (>8000 rows): 2x faster ✅
- **Memory**: 43-57% reduction for medium/large datasets

**No code changes required** - Arrow optimization is automatic when using `query_dataframe()` or `query_ohlcv()`.

### 3. AI Agent Discoverability

New introspection capabilities for AI coding agents:

```python
from gapless_crypto_clickhouse import probe

# Get all capabilities
caps = probe.get_capabilities()
print(caps["query_methods"]["query_ohlcv"])

# Get supported symbols
symbols = probe.get_supported_symbols()  # 713 symbols

# Get supported timeframes
timeframes = probe.get_supported_timeframes()  # 16 timeframes

# Get performance info
perf = probe.get_performance_info()
print(f"Query speedup: {perf['arrow']['query_speedup']}")  # "2x faster"
```

**Machine-readable documentation**:

```python
# Read llms.txt for AI agents
import requests
response = requests.get("https://raw.githubusercontent.com/terrylica/gapless-crypto-clickhouse/main/src/gapless_crypto_clickhouse/llms.txt")
print(response.text)
```

---

## Performance Comparison

### Validated Benchmarks (2025-11-20)

**Arrow vs Standard (within v6.0.0)**:

| Dataset Size   | Arrow Rows/s | Standard Rows/s | Speedup      | Memory Reduction |
| -------------- | ------------ | --------------- | ------------ | ---------------- |
| Small (721)    | 16,844       | 13,972          | 1.21x        | -12% (noise)     |
| Medium (4,345) | 35,768       | 20,188          | 1.77x        | +57%             |
| Large (8,761)  | 41,272       | 20,534          | **2.01x** ✅ | +43%             |

**Arrow vs Baseline (v5.0.0 clickhouse-driver)**:

| Dataset Size   | v6.0.0 Arrow | v5.0.0 TCP | Speedup               |
| -------------- | ------------ | ---------- | --------------------- |
| Small (721)    | 16,844       | 27,432     | 0.61x (HTTP overhead) |
| Medium (4,345) | 35,768       | ~27,432    | 1.30x                 |
| Large (8,761)  | 41,272       | ~27,432    | 1.50x                 |

**Key Insights**:

1. Arrow achieves **2x speedup target** at scale (>8000 rows)
2. HTTP protocol adds overhead on small queries (trade-off for wider compatibility)
3. Use case: Most analytical queries are medium/large datasets where Arrow excels

---

## Compatibility Notes

### What's Unchanged

✅ **Zero-gap guarantee**: FINAL keyword still works, deduplication unchanged
✅ **Schema**: Same 11-column (spot) / 12-column (futures) format
✅ **File-based API**: `download()`, `fetch_data()` still available
✅ **Bulk loader**: `ClickHouseBulkLoader` API unchanged
✅ **Query API**: `OHLCVQuery` class still available (not deprecated)

### What Changed

⚠️ **Port**: 9000 → 8123 (environment variable update required)
⚠️ **Exceptions**: `ClickHouseError` → `Exception`
⚠️ **Health check**: Returns `bool` instead of `None`

---

## Testing Your Migration

### 1. Basic Connection Test

```python
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection

# Test HTTP connection
with ClickHouseConnection() as conn:
    if not conn.health_check():
        raise Exception("Connection failed - check port 8123")

    result = conn.execute("SELECT 1 as test")
    print(f"✅ Connection working: {result[0][0] == 1}")
```

### 2. Query Test

```python
from gapless_crypto_clickhouse import query_ohlcv

# Test auto-ingestion workflow
df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
print(f"✅ Query working: {len(df)} rows retrieved")
```

### 3. Performance Test

```python
import time
from gapless_crypto_clickhouse import query_ohlcv

# Warm-up query
df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-12-31", auto_ingest=False)

# Benchmark
start = time.time()
df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-12-31", auto_ingest=False)
duration = time.time() - start
speed = len(df) / duration

print(f"✅ Performance: {speed:,.0f} rows/s (expect >35K for ~8700 rows)")
```

---

## Troubleshooting

### Issue: Connection Refused (Port 9000)

**Symptom**: `Connection refused` error when connecting to ClickHouse

**Cause**: v6.0.0 uses HTTP (port 8123), not native TCP (port 9000)

**Solution**:

```bash
# Check ClickHouse is listening on port 8123
docker-compose ps
netstat -an | grep 8123

# Update environment variable
export CLICKHOUSE_HTTP_PORT=8123
```

### Issue: ImportError for ClickHouseError

**Symptom**: `ImportError: cannot import name 'Error' from 'clickhouse_driver.errors'`

**Cause**: clickhouse-driver removed, replaced with clickhouse-connect

**Solution**: Replace `ClickHouseError` with `Exception` in error handling

### Issue: Slow Queries (<10K rows/s)

**Symptom**: Queries slower than v5.0.0 baseline

**Cause**: HTTP protocol overhead on small queries

**Solution**: This is expected for small queries (<1000 rows). Arrow benefits appear at scale:

- Small queries: ~16K rows/s (HTTP overhead)
- Medium queries: ~35K rows/s (Arrow benefits emerging)
- Large queries: ~41K rows/s (Arrow benefits dominate)

If you need maximum performance for small queries, consider batching multiple small queries into larger result sets.

---

## Rollback Plan

If you need to rollback to v5.0.0:

```bash
# Uninstall v6.0.0
pip uninstall gapless-crypto-clickhouse

# Install v5.0.0
pip install gapless-crypto-clickhouse==5.0.0

# Revert port configuration
export CLICKHOUSE_PORT=9000  # Native TCP

# Restart ClickHouse if needed
docker-compose restart clickhouse
```

**Note**: v5.0.0 will be maintained for **3 months** (until 2025-02-20) for critical bug fixes only.

---

## Getting Help

- **Documentation**: [README.md](../../README.md)
- **Architecture**: [ADR-0023](../architecture/decisions/0023-arrow-migration.md)
- **Performance**: See `benchmark_arrow_scale_analysis.py` in repository root
- **Issues**: [GitHub Issues](https://github.com/terrylica/gapless-crypto-clickhouse/issues)

---

## Recommended Migration Path

1. **Week 1**: Test v6.0.0 in development environment
   - Update port configuration
   - Run existing queries
   - Validate performance

2. **Week 2**: Migrate to `query_ohlcv()` API
   - Replace manual download + ingest + query workflows
   - Leverage auto-ingestion for simplified code

3. **Week 3**: Deploy to production
   - Update port mappings in docker-compose.yml
   - Monitor performance metrics
   - Validate zero-gap guarantee preserved

**Estimated effort**: 2-4 hours for typical integration
