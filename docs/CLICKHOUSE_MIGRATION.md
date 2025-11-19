# ClickHouse Migration Guide

QuestDB → ClickHouse migration guide for gapless-crypto-data v4.0.0+.

**Status**: ClickHouse implementation complete (ADR-0005). QuestDB deprecated as of v4.0.0, will be removed in v5.0.0.

**Related Documents**:
- [ADR-0005: ClickHouse Migration](decisions/0005-clickhouse-migration.md) - Decision rationale
- [Plan: ClickHouse Migration](plan/0005-clickhouse-migration/plan.yaml) - Implementation plan

## Migration Rationale

**Decision**: Migrate from QuestDB to ClickHouse for future-proofing and ecosystem maturity.

**Key Drivers**:
1. **Ecosystem Maturity**: ClickHouse has larger ecosystem, more integrations, enterprise support
2. **Scalability Ceiling**: ClickHouse supports distributed deployments (ClickHouse Cloud, Kubernetes)
3. **Query Capabilities**: Advanced analytics, window functions, materialized views
4. **Future-Proofing**: Reduce risk of dependency on niche time-series database

**Trade-offs Accepted**:
- Eventual consistency via ReplacingMergeTree (vs immediate DEDUP in QuestDB)
- FINAL keyword overhead (10-30%) for queries requiring deduplication
- Slightly more complex setup (Docker Compose vs single binary)

## Architecture Changes

### Database Engine

**Before (QuestDB)**:
```
Engine: QuestDB with DEDUP ENABLE UPSERT KEYS
Protocol: PostgreSQL wire (queries) + ILP (ingestion)
Deduplication: Immediate, at write time
Performance: 92K-208K rows/sec (ILP), <1s queries
```

**After (ClickHouse)**:
```
Engine: ClickHouse with ReplacingMergeTree
Protocol: Native protocol (port 9000) for all operations
Deduplication: Eventual, via deterministic _version hash
Performance: 1,180 rows/sec (bulk insert), FINAL query overhead 10-30%
```

### Schema Mapping

| QuestDB Column | ClickHouse Column | Type Mapping |
|----------------|-------------------|--------------|
| `symbol` (SYMBOL) | `symbol` (LowCardinality(String)) | Space-efficient string |
| `timeframe` (SYMBOL) | `timeframe` (LowCardinality(String)) | Space-efficient string |
| `instrument_type` (SYMBOL) | `instrument_type` (LowCardinality(String)) | ADR-0004 futures support |
| `timestamp` (TIMESTAMP) | `timestamp` (DateTime64(3)) | Millisecond precision |
| `open`, `high`, `low`, `close`, `volume` (DOUBLE) | Float64 | Same precision |
| `number_of_trades` (LONG) | Int64 | Same precision |
| N/A | `_version` (UInt64) | Deterministic hash for deduplication |
| N/A | `_sign` (Int8) | ReplacingMergeTree merge strategy |

**Compression**:
- Timestamps: DoubleDelta codec (time-series optimization)
- OHLCV floats: Gorilla codec (financial data optimization)
- Strings: ZSTD(3) codec (general compression)

**Partitioning**: By `toYYYYMMDD(timestamp)` for efficient time-range queries

### Deduplication Strategy

**QuestDB Approach** (Immediate):
```sql
CREATE TABLE ohlcv (
    ...
) TIMESTAMP(timestamp) PARTITION BY MONTH
DEDUP ENABLE UPSERT KEYS(timestamp, symbol, timeframe, instrument_type);
```
- Duplicates rejected at write time
- No query-time overhead

**ClickHouse Approach** (Eventual):
```sql
CREATE TABLE ohlcv (
    ...
    _version UInt64,  -- Deterministic hash of row content
    _sign Int8 DEFAULT 1
) ENGINE = ReplacingMergeTree(_version)
ORDER BY (timestamp, symbol, timeframe, instrument_type)
```
- Duplicates written, merged asynchronously
- Query with `FINAL` keyword to force deduplication
- Deterministic `_version` ensures identical data → identical hash → consistent merge outcome

**Zero-Gap Guarantee Preserved**:
```python
# Application-level deterministic versioning
def _compute_version_hash(row):
    version_input = f"{row['timestamp']}{row['open']}{row['high']}{row['low']}{row['close']}{row['volume']}{row['symbol']}{row['timeframe']}{row['instrument_type']}"
    hash_bytes = hashlib.sha256(version_input.encode("utf-8")).digest()
    return int.from_bytes(hash_bytes[:8], byteorder="big", signed=False)
```

## Code Migration

### Connection

**Before (QuestDB)**:
```python
from gapless_crypto_data.questdb import QuestDBConnection

with QuestDBConnection() as conn:
    # PostgreSQL queries
    result = conn.execute_query("SELECT * FROM ohlcv LIMIT 10")
```

**After (ClickHouse)**:
```python
from gapless_crypto_data.clickhouse import ClickHouseConnection

with ClickHouseConnection() as conn:
    # Native protocol queries
    result = conn.execute("SELECT * FROM ohlcv LIMIT 10")
```

**Environment Variables**:
- QuestDB: `QUESTDB_HOST`, `QUESTDB_HTTP_PORT`, `QUESTDB_PG_PORT`
- ClickHouse: `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, `CLICKHOUSE_HTTP_PORT`

### Bulk Ingestion

**Before (QuestDB)**:
```python
from gapless_crypto_data.collectors.questdb_bulk_loader import QuestDBBulkLoader

with QuestDBConnection() as conn:
    loader = QuestDBBulkLoader(conn, instrument_type="spot")
    rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
```

**After (ClickHouse)**:
```python
from gapless_crypto_data.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

with ClickHouseConnection() as conn:
    loader = ClickHouseBulkLoader(conn, instrument_type="spot")
    rows = loader.ingest_month("BTCUSDT", "1h", 2024, 1)
```

**API Compatibility**: Method signatures unchanged, drop-in replacement.

### Query API

**Before (QuestDB)**:
```python
from gapless_crypto_data.query import OHLCVQuery

with QuestDBConnection() as conn:
    query = OHLCVQuery(conn)
    df = query.get_range("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
```

**After (ClickHouse)**:
```python
from gapless_crypto_data.clickhouse_query import OHLCVQuery

with ClickHouseConnection() as conn:
    query = OHLCVQuery(conn)
    df = query.get_range("BTCUSDT", "1h", "2024-01-01", "2024-01-31")
```

**API Compatibility**: Method signatures unchanged, drop-in replacement.

**FINAL Keyword**: Automatically added to all queries for deduplication.

## Deployment

### Local Development

**Docker Compose**:
```yaml
# docker-compose.yml
services:
  clickhouse:
    image: clickhouse/clickhouse-server:24.1-alpine
    ports:
      - "9000:9000"   # Native protocol
      - "8123:8123"   # HTTP interface
    volumes:
      - clickhouse-data:/var/lib/clickhouse
      - ./src/gapless_crypto_data/clickhouse/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro
    environment:
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ""
      CLICKHOUSE_DB: default
```

**Start**:
```bash
docker-compose up -d
docker-compose logs -f  # View logs
```

**Schema Initialization**:
```bash
# Automatic via initdb.d
# Or manual:
docker exec -i gapless-clickhouse clickhouse-client < src/gapless_crypto_data/clickhouse/schema.sql
```

### Production

**ClickHouse Cloud** (recommended):
1. Create cluster at https://clickhouse.cloud
2. Copy connection details to environment variables
3. Run schema.sql via `clickhouse-client`

**Self-Hosted**:
- Kubernetes: Use ClickHouse operator
- Docker Swarm: Use Docker Compose with volumes
- Bare metal: Follow ClickHouse docs for your OS

**Security**:
- Set `CLICKHOUSE_PASSWORD` (empty password for localhost dev only)
- Enable TLS for production
- Configure access control lists (ACLs)

## Performance Characteristics

### Ingestion

| Metric | QuestDB (ILP) | ClickHouse (Bulk) |
|--------|---------------|-------------------|
| Single month (744 rows) | 0.3-0.5s | 0.6-0.8s |
| Throughput | 92K-208K rows/sec | 1,180 rows/sec |
| Network protocol | ILP (custom) | Native (columnar) |

**Note**: ClickHouse throughput is lower for small batches, but scales better for large batches due to columnar format.

### Query

| Query Type | QuestDB | ClickHouse (FINAL) |
|------------|---------|---------------------|
| `get_latest(limit=10)` | <100ms | <150ms (+50% overhead) |
| `get_range(1 month)` | <500ms | <650ms (+30% overhead) |
| `get_multi_symbol(3 symbols)` | <1s | <1.3s (+30% overhead) |

**FINAL Overhead**: 10-30% query time increase due to on-demand deduplication merge.

**Optimization**: For read-heavy workloads, run `OPTIMIZE TABLE ohlcv FINAL` periodically to force merges and reduce FINAL overhead.

## Data Migration

### Export from QuestDB

```bash
# Export to CSV
docker exec questdb clickhouse-client --query "SELECT * FROM ohlcv FORMAT CSV" > ohlcv_export.csv
```

### Import to ClickHouse

```python
import pandas as pd
from gapless_crypto_data.clickhouse import ClickHouseConnection

# Read CSV
df = pd.read_csv("ohlcv_export.csv")

# Add ClickHouse-specific columns
df["_version"] = df.apply(compute_version_hash, axis=1)  # See clickhouse_bulk_loader.py
df["_sign"] = 1

# Import
with ClickHouseConnection() as conn:
    conn.insert_dataframe(df, "ohlcv")
```

**Note**: For large datasets (>10M rows), use `clickhouse-client` batch import or `clickhouse-local` for faster ingestion.

## Validation

### Verification Checklist

- [ ] ClickHouse container running (`docker ps`)
- [ ] Schema created (`SHOW TABLES`, `DESCRIBE TABLE ohlcv`)
- [ ] Test ingestion (spot + futures)
- [ ] Test queries (`get_latest`, `get_range`, `get_multi_symbol`)
- [ ] Verify zero-gap guarantee (duplicate ingestion test)
- [ ] Check spot/futures isolation (no cross-contamination)

### Validation Scripts

Located in `tmp/`:
- `tmp/clickhouse_quick_validation.py` - Basic functionality (5 tests)
- `tmp/clickhouse_futures_validation.py` - ADR-0004 futures support (5 tests)

```bash
# Run validation
uv run --active python tmp/clickhouse_quick_validation.py
uv run --active python tmp/clickhouse_futures_validation.py
```

## Deprecation Timeline

### v4.0.0 (Current)

- ✅ ClickHouse implementation complete
- ⚠️ QuestDB deprecated but still functional
- Dependencies: Both `questdb` and `clickhouse-driver` installed
- Documentation: Migration guide published

### v4.x.x (Transition Period)

- QuestDB code remains but marked `@deprecated`
- Tests run against both QuestDB and ClickHouse
- Users encouraged to migrate

### v5.0.0 (Future Breaking Change)

- ❌ QuestDB code removed entirely
- Dependencies: `questdb` and `psycopg` removed from `pyproject.toml`
- Breaking change: QuestDB imports raise `ImportError`

**Migration Window**: v4.0.0 → v5.0.0 (estimated 6-12 months)

## Troubleshooting

### "Connection refused" on port 9000

**Cause**: ClickHouse not running or port conflict (e.g., QuestDB also uses 9000)

**Solution**:
```bash
# Check if ClickHouse running
docker ps | grep clickhouse

# Start ClickHouse
docker-compose up -d

# Use alternative port
CLICKHOUSE_PORT=9001 docker-compose up -d
```

### "Table ohlcv doesn't exist"

**Cause**: Schema not initialized

**Solution**:
```bash
docker exec -i gapless-clickhouse clickhouse-client < src/gapless_crypto_data/clickhouse/schema.sql
```

### Slow queries with FINAL

**Cause**: ReplacingMergeTree has many unmerged parts

**Solution**:
```sql
-- Force merge to reduce FINAL overhead
OPTIMIZE TABLE ohlcv FINAL;

-- Check merge status
SELECT table, sum(rows) as rows, count() as parts
FROM system.parts
WHERE table = 'ohlcv' AND active
GROUP BY table;
```

### Duplicates still visible after ingestion

**Cause**: ReplacingMergeTree uses eventual consistency

**Solution**:
```sql
-- Query with FINAL to force deduplication
SELECT * FROM ohlcv FINAL WHERE ...;

-- Or force merge (async)
OPTIMIZE TABLE ohlcv FINAL;
```

## References

- [ClickHouse Documentation](https://clickhouse.com/docs/en/)
- [ReplacingMergeTree Engine](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replacingmergetree)
- [ADR-0003: QuestDB Schema Robustness Validation](decisions/0003-questdb-schema-robustness-validation.md) - Original QuestDB implementation
- [ADR-0004: Futures Support Implementation](decisions/0004-futures-support-implementation.md) - Dual instrument type support
- [ADR-0005: ClickHouse Migration](decisions/0005-clickhouse-migration.md) - This migration decision
