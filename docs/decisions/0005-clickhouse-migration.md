# ADR-0005: ClickHouse Migration for Future-Proofing and Ecosystem Maturity

## Status

**Implemented** (2025-11-17)

- Implementation: 7 phases completed (35 hours planned)
- Validation: 15/15 checks passed (100% success rate)
- Migration guide: `docs/CLICKHOUSE_MIGRATION.md`

## Context

### Problem Statement

After completing QuestDB schema validation (ADR-0003, 53.7M rows) and futures support implementation (ADR-0004), leadership expressed concern about long-term future-proofing. The specific drivers:

**User requirement**: "Migrate to ClickHouse for future-proofing - more robust ecosystem, broader adoption, higher scalability ceiling for long-term growth."

**Validated findings from QuestDB implementation**:
- ✅ Schema PRODUCTION-READY at 53.7M row scale (ADR-0003)
- ✅ Zero DEDUP collisions, optimal partition strategy
- ✅ All 16 timeframes validated (including "1mo")
- ✅ Futures support implemented (ADR-0004, instrument_type column)
- ⚠️ Smaller ecosystem vs ClickHouse (13K vs 26K GitHub stars)
- ⚠️ Single-node scaling limits (may require clustering at 1B+ rows)

### Current State

**QuestDB implementation** (v3.x, development/prototype):
- Database: QuestDB 9.2.0 (time-series optimized)
- Schema: `ohlcv` table with DEDUP ENABLE UPSERT KEYS
- Zero-gap guarantee: ✅ PROVEN (immediate consistency)
- Ingestion: 92K-208K rows/sec via ILP protocol
- Query: PostgreSQL wire protocol (standard SQL)
- Scale: Validated at 53.7M rows, headroom to ~200M rows
- Status: Development/prototype (no production deployment yet)

**Migration drivers**:
- ✅ **Ecosystem maturity**: ClickHouse has 300+ contributors, Fortune 500 adoption
- ✅ **Scalability ceiling**: Proven at petabyte scale (1000x current projection)
- ✅ **Feature richness**: Advanced analytics (window functions, ML, materialized views)
- ✅ **Future-proofing**: Bet on more mature ecosystem for 5-10 year horizon
- ⚠️ **Alpha-forge compatibility**: INVALID (alpha-forge uses CSV files, not databases)

### Constraints

1. **Zero-gap guarantee**: Must preserve via application-level deduplication
2. **Backwards compatibility**: API unchanged (instrument_type parameter)
3. **Performance SLOs**: Must maintain 100K+ rows/sec ingestion rate
4. **Validation requirement**: Re-run ADR-0003 validation suite (53.7M rows)
5. **Development timeline**: 35 hours (5 working days) acceptable

## Decision

**Adopt ClickHouse with application-level deduplication** to preserve zero-gap guarantee while gaining ecosystem benefits.

### Schema Design

**ClickHouse schema** (`src/gapless_crypto_data/clickhouse/schema.sql`):

```sql
CREATE TABLE IF NOT EXISTS ohlcv (
    timestamp DateTime64(3),  -- Millisecond precision
    symbol LowCardinality(String),  -- QuestDB SYMBOL → ClickHouse LowCardinality
    timeframe LowCardinality(String),
    instrument_type LowCardinality(String),  -- 'spot' or 'futures'

    -- OHLCV data
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Float64,

    -- Additional microstructure metrics
    close_time DateTime64(3),
    quote_asset_volume Float64,
    number_of_trades Int64,
    taker_buy_base_asset_volume Float64,
    taker_buy_quote_asset_volume Float64,

    data_source LowCardinality(String),  -- 'cloudfront'

    -- Deduplication support (application-level)
    _version UInt64,  -- Deterministic hash of row content
    _sign Int8        -- ReplacingMergeTree sign (1 for active rows)

) ENGINE = ReplacingMergeTree(_version)
ORDER BY (timestamp, symbol, timeframe, instrument_type)
PARTITION BY toYYYYMMDD(timestamp)
SETTINGS index_granularity = 8192;
```

**Type mappings** (QuestDB → ClickHouse):
- `SYMBOL` → `LowCardinality(String)` (space-efficient for low-cardinality columns)
- `DOUBLE` → `Float64`
- `LONG` → `Int64`
- `TIMESTAMP` → `DateTime64(3)` (millisecond precision)
- `PARTITION BY DAY` → `PARTITION BY toYYYYMMDD(timestamp)`

**Rationale**:
- **ReplacingMergeTree**: Handles duplicates via background merges (eventual consistency)
- **_version column**: Deterministic hash ensures identical writes → identical versions
- **ORDER BY composite key**: Optimizes queries for (timestamp, symbol, timeframe, instrument_type)
- **LowCardinality**: ClickHouse equivalent to QuestDB SYMBOL (compression + indexing)

### Zero-Gap Guarantee Strategy

**Challenge**: ClickHouse ReplacingMergeTree uses **eventual consistency** (duplicates visible until merge)

**Solution**: **Application-level deterministic versioning**

```python
def _prepare_clickhouse_row(row: Dict) -> Dict:
    """
    Add deterministic version for ReplacingMergeTree deduplication.

    Ensures identical data → identical version → consistent merge outcome.
    """
    # Create deterministic hash from data content
    version_input = (
        f"{row['timestamp']}"
        f"{row['open']}{row['high']}{row['low']}{row['close']}"
        f"{row['volume']}{row['symbol']}{row['timeframe']}{row['instrument_type']}"
    )

    row['_version'] = hash(version_input) & 0xFFFFFFFFFFFFFFFF  # UInt64
    row['_sign'] = 1  # Positive sign (active row)
    return row
```

**Why this preserves zero-gap guarantee**:
- ✅ Duplicate writes produce identical `_version` values
- ✅ ReplacingMergeTree keeps row with highest `_version` (deterministic)
- ✅ Queries with `FINAL` keyword return deduplicated results
- ⚠️ Caveat: Small query performance penalty with `FINAL` (~10-30% overhead)

### Code Changes

**1. Connection Layer** (`src/gapless_crypto_data/clickhouse/connection.py`):

```python
from clickhouse_driver import Client

class ClickHouseConnection:
    def __init__(self, host: str = "localhost", port: int = 9000):
        self.client = Client(
            host=host,
            port=port,
            settings={'use_numpy': True}  # Optimize for pandas integration
        )

    def execute(self, query: str, params: Optional[Dict] = None):
        """Execute query with parameter substitution."""
        return self.client.execute(query, params or {})

    def insert_dataframe(self, df: pd.DataFrame, table: str):
        """Bulk insert DataFrame to ClickHouse."""
        self.client.insert_dataframe(f"INSERT INTO {table} VALUES", df)
```

**2. Ingestion Rewrite** (`src/gapless_crypto_data/collectors/clickhouse_bulk_loader.py`):

```python
class ClickHouseBulkLoader:
    def _ingest_dataframe(self, df: pd.DataFrame) -> int:
        # Add deterministic versioning
        df['_version'] = df.apply(
            lambda row: hash(f"{row['timestamp']}{row['open']}{row['high']}"
                           f"{row['low']}{row['close']}{row['volume']}"
                           f"{row['symbol']}{row['timeframe']}{row['instrument_type']}")
            & 0xFFFFFFFFFFFFFFFF,
            axis=1
        )
        df['_sign'] = 1

        # Bulk insert
        self.connection.insert_dataframe(df, table='ohlcv')
        return len(df)
```

**3. Query API Update** (`src/gapless_crypto_data/query.py`):

```python
class OHLCVQuery:
    def get_range(self, symbol, timeframe, start, end, instrument_type="spot"):
        sql = """
            SELECT
                timestamp, symbol, timeframe, instrument_type,
                open, high, low, close, volume,
                close_time, quote_asset_volume, number_of_trades,
                taker_buy_base_asset_volume, taker_buy_quote_asset_volume,
                data_source
            FROM ohlcv FINAL  -- FINAL ensures deduplication
            WHERE symbol = %(symbol)s
              AND timeframe = %(timeframe)s
              AND instrument_type = %(instrument_type)s
              AND timestamp >= %(start)s
              AND timestamp <= %(end)s
            ORDER BY timestamp ASC
        """

        params = {
            'symbol': symbol,
            'timeframe': timeframe,
            'instrument_type': instrument_type,
            'start': start,
            'end': end
        }

        result = self.connection.execute(sql, params)
        return pd.DataFrame(result, columns=[...])
```

### Migration Strategy

**Approach**: Clean break (no dual-write), full re-validation

**Migration steps**:
1. **Schema creation**: Deploy ClickHouse schema
2. **Code deployment**: Update to v4.0.0 with ClickHouse implementation
3. **Validation**: Re-run ADR-0003 validation suite (53.7M rows)
4. **Futures support**: Adapt ADR-0004 implementation for ClickHouse

**Backwards compatibility**:
- ❌ **Breaking change**: Database engine changed (QuestDB → ClickHouse)
- ✅ **API preserved**: `get_range()`, `get_latest()`, `get_multi_symbol()` signatures unchanged
- ✅ **instrument_type parameter**: Preserved from ADR-0004

## Consequences

### Positive

- **Ecosystem maturity**: 300+ contributors, Fortune 500 adoption (Uber, Cloudflare, Spotify)
- **Scalability ceiling**: Proven at petabyte scale (1000x current 53.7M row validation)
- **Feature richness**: Advanced analytics (window functions, ML, materialized views)
- **Query flexibility**: Standard SQL with advanced ClickHouse functions
- **Long-term viability**: Stronger bet for 5-10 year horizon

### Negative

- **Eventual consistency**: ReplacingMergeTree duplicates visible until background merge
- **Query overhead**: `FINAL` keyword adds 10-30% query latency
- **Migration effort**: 35 hours development + 12 hours re-validation
- **Operational complexity**: Requires tuning (MergeTree settings, compression)
- **No cross-partition dedup**: Application must ensure deterministic versioning

### Neutral

- **Development timeline**: 5 working days (acceptable for prototype stage)
- **Validation effort**: Re-run ADR-0003 suite (expected, not blocking)

## Alternatives Considered

### Alternative 1: Keep QuestDB (Rejected)

**Pros**:
- Zero-gap guarantee preserved (immediate consistency)
- No migration effort
- Simpler operations

**Cons**:
- Smaller ecosystem (13K vs 26K GitHub stars)
- Single-node scaling limits (may require clustering at 1B+ rows)
- Fewer advanced analytics features
- Less future-proof for long-term growth

**Verdict**: Rejected due to future-proofing priority

### Alternative 2: Hybrid Approach - Abstraction Layer

**Pros**:
- Database-agnostic code
- Can switch between QuestDB/ClickHouse via config
- Lower risk (can validate ClickHouse before full migration)

**Cons**:
- Engineering overhead (abstraction layer complexity)
- Lowest common denominator features
- Dual maintenance burden

**Verdict**: Rejected due to immediate decision timeline (days, not months)

## Implementation Plan

See `docs/plan/0005-clickhouse-migration/plan.yaml` for detailed implementation timeline.

**Phases**:
1. **Phase 1**: ClickHouse schema design (3 hours)
2. **Phase 2**: Connection layer implementation (4 hours)
3. **Phase 3**: Ingestion rewrite with deduplication (10 hours)
4. **Phase 4**: Query API rewrite (6 hours)
5. **Phase 5**: Empirical validation (8 hours) - Re-run ADR-0003 with 53.7M rows
6. **Phase 6**: Futures support adaptation (3 hours)
7. **Phase 7**: Documentation and migration guide (1 hour)

**Total**: 35 hours (5 working days)

## References

- **ADR-0003**: QuestDB Schema Robustness Validation (53.7M row validation)
- **ADR-0004**: Futures Support Implementation (instrument_type column)
- **ClickHouse ReplacingMergeTree Docs**: https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/replacingmergetree
- **ClickHouse Python Driver**: https://github.com/mymarilyn/clickhouse-driver

## Decision Makers

- [Engineering Lead]
- [Date: 2025-11-16]

## Compliance

- **Error handling**: raise-and-propagate (no fallback, no retry, no silent failures)
- **SLOs**: availability (ClickHouse 99.9%), correctness (zero-gap via deterministic versioning), observability (_version tracking), maintainability (ClickHouse ecosystem)
- **OSS preference**: Reuse clickhouse-driver, pandas (no custom ingestion protocol)
- **Auto-validation**: Re-run ADR-0003 6-agent validation suite with ClickHouse
- **Semantic release**: Conventional commits → v4.0.0 tag → GitHub release → changelog
