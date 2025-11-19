# ADR-0001: QuestDB as Single Source of Truth

## Status

**Superseded by [ADR-0005: ClickHouse Migration](0005-clickhouse-migration.md)** (2025-11-17)

Originally: Accepted

## Context

gapless-crypto-data v3.x uses file-based storage (CSV/Parquet) for OHLCV cryptocurrency market data. This architecture has limitations:

- **No concurrent writes**: File-based storage doesn't support multiple data sources writing simultaneously
- **Gap detection complexity**: Requires scanning multiple files to detect timestamp gaps
- **Query performance**: Loading and filtering large CSV/Parquet files is slower than database queries
- **No real-time capability**: Cannot ingest WebSocket streams efficiently alongside bulk historical data
- **Storage fragmentation**: 5,200+ files (400 symbols × 13 timeframes) complicate management

**User Requirements** (2025-11-15):
- Machine interface only (Python API, no CLI)
- macOS development with Colima (not Docker Desktop)
- Linux production with native QuestDB (no Docker overhead)
- Single source of truth storage (no persistent intermediate files)
- Support for concurrent data sources (CloudFront bulk + WebSocket real-time + REST API gap-fill)

**Constraints**:
- Must preserve CloudFront CDN 22x speedup advantage for bulk historical data
- Must support 400+ Binance symbols with 13 timeframes (1s to 1d)
- Must maintain 11-column microstructure format (OHLCV + order flow metrics)
- Must provide zero-gap guarantee through authentic data sources

## Decision

Replace file-based storage with **QuestDB time-series database** as the single source of truth for all OHLCV data.

### Architecture

**Single unified table** (not 5,200 separate tables):
```sql
CREATE TABLE ohlcv (
    timestamp TIMESTAMP,
    symbol SYMBOL capacity 512,
    timeframe SYMBOL capacity 16,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    close_time TIMESTAMP,
    quote_asset_volume DOUBLE,
    number_of_trades LONG,
    taker_buy_base_asset_volume DOUBLE,
    taker_buy_quote_asset_volume DOUBLE,
    data_source SYMBOL capacity 8
) timestamp(timestamp) PARTITION BY DAY WAL;
```

**Deployment Options**:

1. **macOS Development**: Colima + QuestDB container
   - QuestDB in Docker (questdb/questdb:9.2.0)
   - Python code native (uv-managed, no container)
   - Named volumes for 3.5x faster I/O vs bind mounts

2. **Linux Production (Recommended)**: Native QuestDB + Native Python
   - QuestDB binary as systemd service
   - Python code as systemd service (uv-managed)
   - 2-5% faster than Docker, zero container overhead

3. **Linux Production (Alternative)**: Docker QuestDB + Native Python
   - QuestDB in Docker (easier deployment)
   - Python code native (uv-managed)
   - ~10% disk I/O overhead vs native

**Data Flow**:
```
CloudFront ZIPs → Extract → Pandas → ILP → QuestDB (preserve 22x speedup)
Binance WebSocket → Parse → ILP → QuestDB (new capability)
Binance REST API → Parse → ILP → QuestDB (gap filling)
```

## Consequences

### Positive

- **Concurrent writes**: WAL mode supports CloudFront bulk + WebSocket real-time + REST API gap-fill simultaneously
- **Faster queries**: SQL queries with designated timestamp indexing (sub-second for typical OHLCV ranges)
- **Real-time capability**: WebSocket streaming ingestion via ILP protocol
- **Unified gap detection**: SQL-based timestamp sequence analysis across all data sources
- **Data lineage**: `data_source` column tracks provenance (cloudfront/api/websocket)
- **Production-proven**: QuestDB used by Tier 1/2 investment banks and crypto exchanges

### Negative

- **Breaking change**: v4.0.0 major version bump, file-based APIs removed
- **Infrastructure dependency**: Requires QuestDB deployment (container or native)
- **Migration complexity**: Users must migrate existing CSV/Parquet files to QuestDB
- **Learning curve**: Users must learn QuestDB deployment and SQL queries

### Neutral

- **CLI removal**: Already deprecated in v3.3.0, now fully removed
- **Python containerization**: Explicitly not using Docker for Python (uv/uvx manages dependencies)
- **Storage format**: QuestDB columnar storage replaces Parquet (similar compression)

## Compliance

### SLOs

**Availability**:
- QuestDB uptime: 99.9% (CloudFront SLA) for data source
- Deployment health checks: systemd/Docker health monitoring
- Data source failover: CloudFront → REST API fallback

**Correctness**:
- Zero-gap guarantee: Maintained through concurrent CloudFront + REST API ingestion
- Authentic data only: No synthetic values, direct from Binance sources
- Deduplication: UPSERT semantics prevent duplicate timestamps

**Observability**:
- Prometheus metrics: QuestDB /metrics endpoint (port 9003)
- systemd journal logging: All services log to journalctl
- Data lineage tracking: `data_source` column in ohlcv table

**Maintainability**:
- Single table schema: Simpler than 5,200 files
- Standard SQL queries: Familiar interface for data retrieval
- Documented deployment: 3 options (Colima, native, Docker) with guides

### Error Handling

- **No fallbacks**: Raise exceptions on ingestion failures
- **No retries**: Upstream responsibility (CloudFront has built-in reliability)
- **Propagate errors**: Let callers handle connection failures, data validation errors
- **Auto-validation**: QuestDB TIMESTAMP constraints enforce chronological ordering

### OSS Libraries

- **QuestDB**: Apache 2.0 licensed, production-ready time-series database
- **questdb Python client**: Official Python SDK for ILP ingestion
- **psycopg3**: PostgreSQL wire protocol client (BSD-3-Clause)
- **uv**: Rust-based Python package manager (MIT/Apache 2.0)

## Alternatives Considered

### Option 1: DuckDB (Rejected)

**Pros**: Already used for ValidationStorage, familiar
**Cons**:
- Single-process write lock (cannot handle concurrent CloudFront + WebSocket + API)
- Not a time-series database (no designated timestamp, partitioning)
- Empirical testing showed 7,500x slower single-threaded writes vs Parquet

**Verdict**: Keep for ValidationStorage analytics, not suitable for primary OHLCV storage

### Option 2: ClickHouse (Rejected)

**Pros**: Production-proven in crypto (Coinhall, Longbridge), excellent analytics
**Cons**:
- Requires batch ingestion (1-second batches, not tick-by-tick)
- 22x slower OHLCV queries than QuestDB (547ms vs 25ms)
- Higher operational complexity (MergeTree engines, partition tuning)

**Verdict**: Better for multi-year data warehouse, overkill for this use case

### Option 3: Redis TimeSeries + Parquet Hybrid (Rejected)

**Pros**: Sub-ms real-time queries, low cost ($55/mo)
**Cons**:
- Dual storage complexity (hot/cold split)
- Redis memory limits (400 symbols × 13 timeframes = high memory usage)
- Query federation layer required

**Verdict**: Good for cost-sensitive deployments, but added complexity

### Option 4: Continue File-Based (Rejected)

**Pros**: No migration, zero deployment complexity
**Cons**:
- Cannot add real-time WebSocket capability
- Cannot support concurrent writes
- Fragmented storage (5,200+ files)

**Verdict**: Does not meet new concurrent write and real-time requirements

## Implementation Plan

See `docs/plan/0001-questdb-refactor/plan.yaml` for detailed implementation timeline.

**Phases**:
1. Infrastructure & Documentation (Week 1-2)
2. Python API Refactoring (Week 3-5)
3. uv Dependency Management (Week 6)
4. Migration Tooling (Week 7)
5. Testing & Validation (Week 8-9)
6. Documentation (Week 10-11)

**Release**: v4.0.0 (11 weeks)

## References

- [QuestDB Performance Benchmarks](../research/questdb-docker-image-analysis.md)
- [Colima vs Docker Desktop](https://github.com/abiosoft/colima)
- [QuestDB Official Documentation](https://questdb.com/docs/)
- [uv Python Package Manager](https://github.com/astral-sh/uv)

## Metadata

- **ADR ID**: 0001
- **Date**: 2025-11-15
- **Authors**: gapless-crypto-data team
- **Status**: Accepted
- **Related Plans**: docs/plan/0001-questdb-refactor/plan.yaml
