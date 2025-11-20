# v6.0.0: Apache Arrow Migration + Auto-Ingestion

**Author**: Claude Code
**Created**: 2025-11-20
**ADR**: [0023-arrow-migration](../../../architecture/decisions/0023-arrow-migration.md)
**Status**: In Progress

---

## Objective

Migrate from clickhouse-driver to clickhouse-connect with Apache Arrow support to achieve 3x faster query performance and implement lazy auto-ingestion addressing Alpha Forge's feature request.

**Success Metrics**:

- Query speed: ≥2x faster (target: 3x, 82,000 rows/s)
- Memory usage: ≥50% reduction (target: 75%)
- Benchmark validation: All tests pass with Arrow enabled
- Zero-gap guarantee: Preserved (FINAL keyword still works)

---

## Context

### Background

**Alpha Forge Feature Request** (2025-11-19):

- Requested hosted ClickHouse service with auto-ingestion
- Complained about slow CSV downloads (10-30 seconds)
- Wanted unified query API: `query_ohlcv()`

**Benchmark Analysis** (2025-11-20):

```
Current Performance (clickhouse-driver):
- Query speed: 27,432 rows/sec (0.03s for 721 rows)
- Download bottleneck: 96% of time downloading from CDN
- Large dataset: 10.10s total (9.7s download, 0.3s query)

Alpha Forge Misunderstanding:
- They think package is CSV-only
- Reality: ClickHouse integration exists since v1.0.0
- Missing: Auto-ingestion, unified query API
```

**Decision** (ADR-0023):

- Arrow migration addresses 60% of request (3x speed, 4x less memory)
- Auto-ingestion addresses 40% (lazy on-demand download)
- Hosted service rejected (infrastructure costs, not viable for OSS)

### Current State (v5.0.0)

**Dependencies**:

```toml
clickhouse-driver = ">=0.2.9"
pandas = ">=2.0.0,<2.2.0"
numpy = ">=1.23.2,<2.0.0"
```

**Architecture**:

- Connection: clickhouse-driver.Client (native TCP, port 9000)
- Query: OHLCVQuery returns pandas DataFrame
- Bulk loader: ClickHouseBulkLoader.ingest_from_dataframe()
- Exports: fetch_data(), download(), download_multiple()

**Missing**:

- ❌ query_ohlcv() with auto-ingestion
- ❌ AI discoverability (probe.py, llms.txt)
- ❌ Arrow optimization
- ❌ Unified database query API

### Target State (v6.0.0)

**Dependencies**:

```toml
clickhouse-connect = ">=0.7.0"  # Replaces clickhouse-driver
pandas = ">=2.0.0,<2.2.0"
numpy = ">=1.23.2,<2.0.0"
pyarrow = ">=14.0.0"  # Arrow support
```

**Architecture**:

- Connection: clickhouse_connect.get_client() (HTTP, port 8123)
- Query: All queries use Arrow format (`use_arrow=True`)
- Auto-ingestion: query_ohlcv() checks database → download if missing → ingest → query
- Exports: fetch_data(), download(), query_ohlcv() (NEW)

**New Capabilities**:

- ✅ 3x faster queries via Arrow zero-copy
- ✅ 75% less memory via Arrow buffers
- ✅ Lazy auto-ingestion (download on first query miss)
- ✅ AI discoverability (probe.py, llms.txt)

---

## Plan

### Phase 1: Driver Migration (v6.0.0-alpha.1)

**Goal**: Replace clickhouse-driver with clickhouse-connect, validate basic functionality.

**Tasks**:

1. Update pyproject.toml dependencies
   - Remove: clickhouse-driver
   - Add: clickhouse-connect>=0.7.0, pyarrow>=14.0.0

2. Rewrite src/gapless_crypto_clickhouse/clickhouse/connection.py
   - Replace Client with clickhouse_connect.get_client()
   - Enable Arrow: `query_df(..., use_arrow=True)`
   - Preserve API: execute(), query_dataframe(), insert_dataframe()
   - Update health_check() to return bool (fix benchmark bug)

3. Update src/gapless_crypto_clickhouse/collectors/clickhouse_bulk_loader.py
   - Use new connection.insert_dataframe() API
   - Validate funding_rate column handling (bug fix from benchmark)

4. Update src/gapless_crypto_clickhouse/clickhouse_query.py
   - Use Arrow-optimized query_dataframe()
   - Validate FINAL keyword still works

**Validation**:

```bash
# Install dependencies
uv sync

# Run unit tests
uv run pytest tests/unit/test_clickhouse_connection.py -v

# Manual connection test
.venv/bin/python -c "
from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
with ClickHouseConnection() as conn:
    df = conn.query_dataframe('SELECT 1 as test')
    print(f'Success: {df}')
    print(f'Arrow format: {type(df).__module__}')
"
```

**Acceptance Criteria**:

- All unit tests pass
- Manual connection test works
- DataFrame is pandas (not Arrow, just internal optimization)
- FINAL keyword queries return correct results

### Phase 2: Query API (v6.0.0-alpha.2)

**Goal**: Implement query_ohlcv() with lazy auto-ingestion.

**Tasks**:

1. Create src/gapless_crypto_clickhouse/query_api.py

   ```python
   def query_ohlcv(
       symbol: Union[str, List[str]],
       timeframe: str,
       start_date: str,
       end_date: str,
       instrument_type: InstrumentType = "spot",
       auto_ingest: bool = True,
       fill_gaps: bool = True,
       clickhouse_config: Optional[ClickHouseConfig] = None,
   ) -> pd.DataFrame:
       """
       Query OHLCV with lazy auto-ingestion.

       Workflow:
       1. Check if data exists (COUNT query)
       2. If missing and auto_ingest: download and ingest
       3. Query ClickHouse with FINAL
       4. If fill_gaps: detect and fill gaps via REST API
       5. Return DataFrame (Arrow-optimized internally)
       """
   ```

2. Create src/gapless_crypto_clickhouse/probe.py
   - Implement capability discovery for AI agents
   - List available symbols, timeframes, date ranges
   - Expose query_ohlcv() parameters and defaults

3. Create src/gapless_crypto_clickhouse/llms.txt
   - Machine-readable API documentation
   - Usage examples for query_ohlcv()
   - Configuration options

4. Update src/gapless_crypto_clickhouse/**init**.py
   - Add export: query_ohlcv()
   - Add export: probe module

**Validation**:

```bash
# Test auto-ingestion workflow
.venv/bin/python -c "
from gapless_crypto_clickhouse import query_ohlcv
import os
os.environ['CLICKHOUSE_HOST'] = 'localhost'

# First call: should download + ingest
df = query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
print(f'First query: {len(df)} rows')

# Second call: should query only (cached)
df = query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
print(f'Second query: {len(df)} rows')
"

# Test probe
.venv/bin/python -c "
from gapless_crypto_clickhouse import probe
print(probe.get_capabilities())
"
```

**Acceptance Criteria**:

- query_ohlcv() downloads missing data automatically
- Cached queries skip download (idempotent)
- probe.get_capabilities() returns valid JSON
- llms.txt validates against schema

### Phase 3: Benchmarking (v6.0.0-beta.1)

**Goal**: Validate 3x speedup claim via comparative benchmarks.

**Tasks**:

1. Create benchmark_arrow_comparison.py
   - Test 1: Small query (721 rows) - clickhouse-driver vs clickhouse-connect+Arrow
   - Test 2: Medium query (8,784 rows) - same comparison
   - Test 3: Large query (100k+ rows) - stress test
   - Test 4: Memory profiling - measure RSS before/after

2. Run benchmarks and collect data

   ```bash
   .venv/bin/python benchmark_arrow_comparison.py > logs/0023-arrow-migration-$(date +%Y%m%d_%H%M%S).log 2>&1
   ```

3. Analyze results
   - Accept if: ≥2x speedup (target: 3x)
   - Accept if: ≥50% memory reduction (target: 75%)
   - Document actual vs projected in ADR

**Validation**:

```bash
# Expected output format:
# Driver: clickhouse-driver | Rows: 721 | Time: 0.03s | Speed: 27,432 rows/s | Memory: 5.2 MB
# Driver: clickhouse-connect+Arrow | Rows: 721 | Time: 0.01s | Speed: 82,000 rows/s | Memory: 1.3 MB
# Speedup: 2.99x | Memory reduction: 75%
```

**Acceptance Criteria**:

- Speedup ≥2x (pass), ≥3x (excellent)
- Memory reduction ≥50% (pass), ≥75% (excellent)
- All integration tests pass
- No regression in correctness (zero-gap guarantee preserved)

### Phase 4: Documentation & Release (v6.0.0)

**Goal**: Document migration, publish to PyPI.

**Tasks**:

1. Update README.md
   - Add query_ohlcv() usage example
   - Document Arrow benefits (3x speed, 4x memory)
   - Update quick start guide

2. Create docs/guides/MIGRATION_v5_to_v6.md
   - Breaking changes: Connection API changes
   - Migration steps: Update imports, change connection usage
   - Before/after examples

3. Update CHANGELOG.md via semantic-release
   - feat: Add query_ohlcv() with lazy auto-ingestion
   - feat: Migrate to clickhouse-connect with Apache Arrow
   - fix: Add funding_rate column to bulk loader schema
   - fix: Fix health_check() return type bug

4. Publish to PyPI
   - Use semantic-release skill with GH token
   - Conventional commits → tag → GH release → publish
   - Doppler for PyPI token

**Validation**:

```bash
# Test fresh install
pip install gapless-crypto-clickhouse==6.0.0

# Test quick start example
python -c "
from gapless_crypto_clickhouse import query_ohlcv
df = query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-31')
print(f'Success: {len(df)} rows')
"
```

**Acceptance Criteria**:

- PyPI publish succeeds
- Fresh install works
- Documentation renders correctly
- CHANGELOG.md generated automatically

---

## Task List

### Phase 1: Driver Migration ✅ = Done, 🔄 = In Progress, ⏳ = Pending

- ✅ 1.1: Update pyproject.toml dependencies (remove clickhouse-driver, add clickhouse-connect + pyarrow)
- ✅ 1.2: Rewrite ClickHouseConnection for clickhouse-connect
- ✅ 1.3: Update ClickHouseBulkLoader for new connection API
- ✅ 1.4: Update OHLCVQuery for Arrow-optimized queries
- ✅ 1.5: Run unit tests and validate basic functionality

### Phase 2: Query API

- ✅ 2.1: Implement query_ohlcv() in query_api.py
- ✅ 2.2: Create probe.py for AI discoverability
- ✅ 2.3: Create llms.txt for machine-readable docs
- ✅ 2.4: Update **init**.py exports
- ✅ 2.5: Test auto-ingestion workflow

### Phase 3: Benchmarking

- ⏳ 3.1: Create benchmark_arrow_comparison.py
- ⏳ 3.2: Run comparative benchmarks
- ⏳ 3.3: Analyze results and validate speedup claims
- ⏳ 3.4: Update ADR with actual performance data

### Phase 4: Documentation & Release

- ⏳ 4.1: Update README.md with query_ohlcv() examples
- ⏳ 4.2: Create MIGRATION_v5_to_v6.md guide
- ⏳ 4.3: Generate CHANGELOG.md via semantic-release
- ⏳ 4.4: Publish v6.0.0 to PyPI

---

## Risks & Mitigations

### Risk 1: Arrow Speedup Less Than 3x

**Impact**: Marketing claim invalidated, user disappointment.

**Mitigation**:

- Accept ≥2x as success (still significant improvement)
- Document actual speedup in CHANGELOG
- Explain when Arrow helps (large datasets) vs doesn't (small queries)

### Risk 2: Breaking Changes Affect Users

**Impact**: Upgrade friction, support burden.

**Mitigation**:

- Major version bump (v6.0.0) signals breaking change
- Provide migration guide with before/after examples
- Keep v5.0.x branch maintained for 3 months

### Risk 3: Arrow Zero-Copy Conditions Not Met

**Impact**: Fallback to row-oriented conversion, no speedup.

**Mitigation**:

- Validate schema compatibility (no nulls in numeric columns except funding_rate)
- Use single-chunk Arrow tables
- Document when zero-copy fails (observability)

---

## Open Questions

1. **Q**: Should we support both clickhouse-driver and clickhouse-connect?
   **A**: No. Major version bump allows clean break. v5.0.x maintained for 3 months.

2. **Q**: What if Arrow is not available (missing pyarrow)?
   **A**: Make pyarrow required dependency. Arrow is standard, worth the extra 10 MB.

3. **Q**: How to handle mixed instrument types in query_ohlcv()?
   **A**: Require explicit instrument_type parameter. No auto-detection (prevents silent errors).

---

## Success Criteria (Overall)

- ✅ All unit tests pass
- ✅ Benchmark shows ≥2x speedup
- ✅ Benchmark shows ≥50% memory reduction
- ✅ Auto-ingestion works (download on first miss)
- ✅ Documentation updated (README, migration guide)
- ✅ v6.0.0 published to PyPI
- ✅ Zero-gap guarantee preserved (FINAL keyword still works)

---

## Timeline

- **Phase 1**: 2 hours (driver migration)
- **Phase 2**: 3 hours (query API + probe + llms.txt)
- **Phase 3**: 1 hour (benchmarking)
- **Phase 4**: 1 hour (docs + release)
- **Total**: 7 hours

**Note**: No calendar deadlines. Complete when validation passes.
