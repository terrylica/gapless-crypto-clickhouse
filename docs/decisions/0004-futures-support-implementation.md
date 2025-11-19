# ADR-0004: Futures Support Implementation via instrument_type Schema Extension

## Status

**Superseded by [ADR-0005: ClickHouse Migration](0005-clickhouse-migration.md)** (2025-11-17)

Originally: Proposed (futures support with `instrument_type` column ported to ClickHouse)

## Context

### Problem Statement

ADR-0003 validated the QuestDB schema's production-readiness at 53.7M row scale (5 spot symbols × 16 timeframes × 122 days) with **99% capacity headroom** (507/512 unused symbol slots). Users require collecting both spot and USDT-margined perpetual futures data using the same unified database.

**User requirement**: "Extend gapless-crypto-data to support Binance USDT-margined (UM) perpetual futures with same zero-gap guarantee and 22x CloudFront CDN speedup."

**Validated findings from ADR-0003**:
- ✅ Schema PRODUCTION-READY at 53.7M row scale
- ✅ Zero DEDUP collisions, optimal partition strategy
- ✅ All 16 timeframes validated (including "1mo")
- ✅ 99% symbol capacity headroom (507 unused slots)
- ✅ Single-table approach empirically justified

### Current State

**Spot-only support** (v2.x):
- Data source: `https://data.binance.vision/data/spot/monthly/klines/`
- CSV format: 11 columns, no header
- Timeframes: 16 (1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo)
- Schema: `ohlcv` table without `instrument_type` column
- DEDUP key: `(timestamp, symbol, timeframe)`

**Futures support gap**:
- ❌ Futures data source not accessible (URL hardcoded to `/data/spot/`)
- ❌ Futures CSV format incompatible (12 columns with header vs 11 columns no header)
- ❌ Cannot distinguish spot vs futures rows (no `instrument_type` column)
- ❌ DEDUP key collision risk if spot and futures share same symbol/timeframe

### Constraints

1. **Backwards compatibility**: Existing spot data must remain accessible without migration
2. **Zero-gap guarantee**: Must preserve for both spot and futures
3. **Performance SLOs**: Must maintain 100K+ rows/sec ILP ingestion rate
4. **Schema versioning**: Breaking changes require major version bump (v2.x → v3.0.0)
5. **No separate package**: Single unified `gapless-crypto-data` package (avoid code duplication)

## Decision

**Adopt single-table schema extension approach** (recommended by ADR-0003 Phase 1.4):

### Schema Extension

Add `instrument_type` SYMBOL column to existing `ohlcv` table:

```sql
-- Migration: docs/migrations/0004-add-instrument-type-column.sql
ALTER TABLE ohlcv ADD COLUMN instrument_type SYMBOL CAPACITY 2 CACHE;

-- Backfill existing spot data
UPDATE ohlcv SET instrument_type = 'spot';

-- Update DEDUP key to prevent spot/futures collisions
ALTER TABLE ohlcv DEDUP ENABLE UPSERT KEYS(timestamp, symbol, timeframe, instrument_type);
```

**Rationale**:
- **Capacity**: Only 2 values needed ('spot', 'futures') - minimal memory overhead
- **CACHE enabled**: Most queries filter by instrument_type (frequent access)
- **DEDUP safety**: Prevents collisions between spot and futures with same symbol/timeframe/timestamp
- **Query benefit**: `WHERE instrument_type = 'spot'` reduces scan size by ~50% after futures ingestion

### Code Changes

**1. URL Parameterization** (`src/gapless_crypto_data/collectors/questdb_bulk_loader.py`):
```python
class QuestDBBulkLoader:
    SPOT_BASE_URL = "https://data.binance.vision/data/spot"
    FUTURES_BASE_URL = "https://data.binance.vision/data/futures/um"  # USDT-margined

    def __init__(self, connection: QuestDBConnection, instrument_type: str = "spot"):
        self.instrument_type = instrument_type
        self.base_url = (
            self.SPOT_BASE_URL if instrument_type == "spot"
            else self.FUTURES_BASE_URL
        )
```

**2. CSV Parser Extension** (`src/gapless_crypto_data/collectors/questdb_bulk_loader.py:_parse_csv()`):
```python
def _parse_csv(self, csv_path: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    # Detect header presence (futures has header, spot doesn't)
    with open(csv_path) as f:
        first_line = f.readline()
        has_header = first_line.startswith("open_time")  # Futures CSV header

    # Conditional parsing
    if self.instrument_type == "futures":
        df = pd.read_csv(csv_path, header=0)  # 12 columns with header
        # Futures has additional 'ignore' column (always empty)
    else:
        df = pd.read_csv(csv_path, header=None, names=[...])  # 11 columns

    df["instrument_type"] = self.instrument_type
    return df
```

**3. ILP Ingestion Update** (`src/gapless_crypto_data/collectors/questdb_bulk_loader.py:_ingest_dataframe()`):
```python
sender.dataframe(
    df_ingest,
    table_name="ohlcv",
    symbols=["symbol", "timeframe", "data_source", "instrument_type"],  # Added instrument_type
    at="timestamp",
)
```

**4. Query API Extension** (`src/gapless_crypto_data/query.py`):
```python
def get_ohlcv(
    self,
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    instrument_type: str = "spot",  # New parameter, defaults to spot for backwards compat
) -> pd.DataFrame:
    sql = """
        SELECT * FROM ohlcv
        WHERE symbol = ? AND timeframe = ? AND instrument_type = ?
        AND timestamp >= ? AND timestamp <= ?
    """
    params = (symbol, timeframe, instrument_type, start_ts, end_ts)
```

**5. CLI Flag Addition** (`src/gapless_crypto_data/cli.py`):
```python
@click.option(
    "--instrument-type",
    type=click.Choice(["spot", "futures"]),
    default="spot",
    help="Instrument type: spot or USDT-margined perpetual futures"
)
def main(symbol, timeframe, start_date, end_date, instrument_type):
    loader = QuestDBBulkLoader(conn, instrument_type=instrument_type)
```

### Migration Strategy

**Breaking change**: Requires v3.0.0 major version bump

**Migration steps** (in-place, no data loss):
1. **Backup**: `SELECT * FROM ohlcv INTO BACKUP 'ohlcv_pre_v3_migration'`
2. **Schema migration**: Run `docs/migrations/0004-add-instrument-type-column.sql`
3. **Verification**: Check `SELECT COUNT(*) FROM ohlcv` unchanged, `instrument_type` column present
4. **Code deployment**: Update to v3.0.0 with `--instrument-type` flag

**Backwards compatibility**:
- ✅ Existing queries work unchanged (no `instrument_type` filter defaults to all data)
- ✅ CLI defaults to `--instrument-type spot` (existing commands work)
- ❌ New writes require `instrument_type` parameter (raises error if missing)

## Consequences

### Positive

- **Unified data model**: Single query API for spot and futures (filter by `instrument_type`)
- **99% capacity headroom**: Schema supports both spot and futures without running out of slots
- **Query performance benefit**: `WHERE instrument_type = 'spot'` cuts scan size in half
- **Cross-instrument queries enabled**: Easy to compare spot vs futures pricing
- **Minimal code changes**: ~70 lines across 5 files, low regression risk
- **Empirically validated**: Schema robustness proven at 53.7M row scale

### Negative

- **Breaking schema change**: Requires major version bump v2.x → v3.0.0
- **Migration required**: Existing users must run migration script (one-time, low risk)
- **Table size doubles**: ~108M rows after futures ingestion (still within QuestDB capacity)
- **12-column futures format**: Requires conditional CSV parsing logic

### Neutral

- **Implementation effort**: 15 hours (2 working days) estimated
- **Testing effort**: Re-run ADR-0003 validation suite with futures data (~4 hours)

## Alternatives Considered

### Alternative 1: Separate `gapless-futures-data` Package

**Pros**:
- No breaking changes to existing package
- Architectural isolation

**Cons**:
- 80% code duplication (collectors, query API, CLI)
- Maintenance burden (bug fixes ported to both packages)
- Fragmented ecosystem (users install 2 packages)
- Wasted capacity (spot uses 1%, futures uses another 1%)
- Cross-instrument queries impossible

**Verdict**: Rejected due to maintenance burden and wasted capacity

### Alternative 2: Multi-table Approach (separate `ohlcv_spot`, `ohlcv_futures`)

**Pros**:
- Table isolation
- No DEDUP key modification needed

**Cons**:
- Query API complexity (which table to query?)
- Cross-instrument queries require UNION
- Doubles partition management overhead
- Violates single-table design validated in ADR-0003

**Verdict**: Rejected due to query complexity and partition overhead

## Implementation Plan

See `docs/plan/0004-futures-support/plan.yaml` for detailed implementation timeline.

**Phases**:
1. **Phase 1**: Schema migration script (1 hour)
2. **Phase 2**: CSV parser extension (2 hours)
3. **Phase 3**: URL parameterization (1 hour)
4. **Phase 4**: ILP ingestion update (1 hour)
5. **Phase 5**: CLI flag addition (0.5 hours)
6. **Phase 6**: Query API update (1 hour)
7. **Phase 7**: Unit tests (2 hours)
8. **Phase 8**: Integration tests (2 hours)
9. **Phase 9**: Documentation (1 hour)
10. **Phase 10**: Futures data validation (re-run ADR-0003 agents) (4 hours)

**Total**: 15.5 hours (2 working days)

## References

- **ADR-0003**: QuestDB Schema Robustness Validation (53.7M row validation)
- **FUTURES_ROADMAP.md**: `tmp/schema-robustness/futures-design/FUTURES_ROADMAP.md`
- **Binance Futures Data**: `https://data.binance.vision/?prefix=data/futures/um/monthly/klines/`
- **QuestDB SYMBOL Column Docs**: https://questdb.io/docs/reference/sql/create-table/#symbol

## Decision Makers

- [Your name/role]
- [Approval date]

## Compliance

- **Error handling**: raise-and-propagate (no fallback, no retry, no silent failures)
- **SLOs**: availability (CloudFront 99.99%), correctness (zero-gap), observability (instrument_type tracking), maintainability (single codebase)
- **OSS preference**: Reuse psycopg, pandas, questdb SDK (no custom CSV parser beyond conditional logic)
- **Auto-validation**: Re-run ADR-0003 6-agent validation suite with futures data
- **Semantic release**: Conventional commits → v3.0.0 tag → GitHub release → changelog
