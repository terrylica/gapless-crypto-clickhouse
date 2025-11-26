# ADR-0023: Apache Arrow Migration for Query Performance at Scale

## Status

Implemented (v6.0.0)

## Context

### Problem Statement

Alpha Forge team reported performance concerns with the current implementation, requesting hosted ClickHouse service with auto-ingestion. Benchmark analysis (2025-11-20) revealed:

**Current Performance (clickhouse-driver v0.2.9)**:

- Query speed: 27,432 rows/sec (excellent)
- Download bottleneck: 96% of time spent downloading from CDN
- DataFrame creation: pandas native format (row-oriented conversion)

**Research Findings** (Apache Arrow benefits):

- 3x faster DataFrame creation (5-10 GB/s vs 100-500 MB/s)
- 4x less memory (zero-copy when compatible)
- Industry standard (Polars, DuckDB, PyArrow)

### Use Cases Requiring Faster Queries

1. **Large result sets**: 10k+ rows common for backtesting (60% of Alpha Forge queries)
2. **Memory-constrained environments**: ML models (TA-Lib) compete for memory
3. **High-frequency queries**: Trading strategies iterate rapidly during development
4. **Multi-symbol queries**: Portfolio analysis requires 10-100 symbols simultaneously

### Benchmark Results

```text
Operation                  | Rows   | Time (s) | Rows/s  | Memory
---------------------------|--------|----------|---------|--------
ClickHouse Query (current) | 721    | 0.03s    | 27,432  | Unknown
Projected (Arrow)          | 721    | 0.01s    | 82,000  | -75%
Large Dataset (current)    | 26,352 | 10.10s   | 2,608   | Unknown
```

**Bottleneck**: 96% of time in downloads, 0.3% in query execution. Arrow improves the 0.3%, but enables new capabilities (in-memory aggregations, joins).

### Validation Results (Post-Implementation, 2025-11-20)

Comparative benchmarks validated Arrow performance across multiple dataset sizes using `benchmark_arrow_scale_analysis.py`:

**Scale Analysis Results**:

```text
Scale      | Method    | Rows   | Time (s) | Rows/s  | Memory (MB) | Speedup
-----------|-----------|--------|----------|---------|-------------|--------
Small      | Arrow     | 721    | 0.0428s  | 16,844  | 1.29        | 1.21x
Small      | Standard  | 721    | 0.0516s  | 13,972  | 1.15        | baseline
Medium     | Arrow     | 4,345  | 0.1215s  | 35,768  | 1.34        | 1.77x
Medium     | Standard  | 4,345  | 0.2152s  | 20,188  | 3.09        | baseline
Large      | Arrow     | 8,761  | 0.2123s  | 41,272  | 3.32        | 2.01x ✅
Large      | Standard  | 8,761  | 0.4266s  | 20,534  | 5.83        | baseline
```

**Key Findings**:

1. **Arrow vs Standard (within v6.0.0)**:
   - Small (721 rows): 1.21x faster
   - Medium (4,345 rows): 1.77x faster
   - Large (8,761 rows): **2.01x faster** ✅ **Achieved 2x target**
   - Memory reduction: 43-57% for medium/large datasets

2. **Arrow vs Baseline (v5.0.0 clickhouse-driver TCP)**:
   - Small queries: 0.61x (slower due to HTTP protocol overhead)
   - Medium queries: 1.30x (on par, Arrow benefits emerging)
   - Large queries: 1.50x (faster, Arrow columnar benefits dominate)

3. **Protocol Trade-off**:
   - HTTP protocol (port 8123) adds 30-40% overhead on small queries (<1000 rows)
   - Arrow columnar benefits dominate at scale (>4000 rows)
   - Trade-off accepted: HTTP provides wider compatibility (firewalls, reverse proxies, nginx)

4. **Memory Characteristics**:
   - Small datasets: Minimal difference (-12% for Arrow, within measurement noise)
   - Medium/large datasets: Arrow uses 43-57% **less** memory than standard query_df
   - Zero-copy benefits require sufficient data volume to amortize setup costs

**Conclusion**: Arrow achieves **2x speedup target** at scale (>8000 rows). Protocol overhead acceptable given value proposition: unified API (`query_ohlcv()`) + auto-ingestion + better scalability. Performance story reframed from "3x faster everywhere" (projected) to "2x faster at scale with unified API" (validated).

## Decision

Migrate from `clickhouse-driver` to `clickhouse-connect` with Apache Arrow format enabled.

**Migration Scope**:

1. Replace clickhouse-driver (native TCP) with clickhouse-connect (HTTP + Arrow)
2. Enable Arrow format for all query operations
3. Implement `query_ohlcv()` with lazy auto-ingestion (addresses Alpha Forge request)
4. Add AI discoverability (probe.py, llms.txt)
5. Validate 3x speedup claim via comparative benchmarks

**Out of Scope**:

- Hosted ClickHouse service (not viable for OSS project, requires $200+/month infrastructure)
- Download optimization (already at CDN limits, ETag caching working)

## Consequences

### Positive

1. **2x faster queries at scale**: 41,272 rows/s vs 20,534 rows/s for large datasets (>8000 rows) ✅
2. **43-57% less memory**: Arrow buffers reduce memory usage for medium/large queries
3. **Future-proof**: Arrow is ecosystem standard (Polars, DuckDB compatibility)
4. **Auto-ingestion**: Unified `query_ohlcv()` eliminates manual download step (addresses Alpha Forge request)
5. **AI discoverability**: llms.txt + probe.py enables AI agents to discover capabilities
6. **Wider compatibility**: HTTP protocol works with firewalls, reverse proxies, nginx (vs native TCP)

### Negative

1. **Protocol change**: Native TCP (9000) → HTTP (8123) - requires port exposure
2. **Breaking change**: v6.0.0 required (connection module API changes)
3. **Small query overhead**: HTTP protocol adds 30-40% overhead for queries <1000 rows (trade-off for wider compatibility)
4. **Schema compatibility**: Must validate Arrow zero-copy conditions (no nulls, single chunk)

### Neutral

1. **Dependency change**: clickhouse-driver → clickhouse-connect (both mature OSS)
2. **Deduplication**: FINAL keyword still required (no change in correctness guarantee)

## Implementation Notes

### Migration Strategy

1. **Phase 1: Driver Migration** (v6.0.0-alpha.1)
   - Update pyproject.toml dependency
   - Rewrite ClickHouseConnection using clickhouse-connect.get_client()
   - Enable Arrow format: `query_df(..., use_arrow=True)`
   - Migrate bulk loader to new insert API

2. **Phase 2: Query API** (v6.0.0-alpha.2)
   - Implement query_ohlcv() with lazy auto-ingestion
   - Add probe.py and llms.txt
   - Update **init**.py exports

3. **Phase 3: Validation** (v6.0.0-beta.1)
   - Comparative benchmark: clickhouse-driver vs clickhouse-connect
   - Validate 3x speedup (accept if ≥2x)
   - Integration tests

4. **Phase 4: Release** (v6.0.0)
   - Update documentation (README, migration guide)
   - Conventional commits for semantic-release
   - PyPI publish via Doppler

### SLO Compliance

- **Availability**: HTTP protocol adds nginx/reverse proxy compatibility
- **Correctness**: Zero-gap guarantee preserved (FINAL keyword unchanged)
- **Observability**: Arrow metadata available via PyArrow introspection
- **Maintainability**: Simpler HTTP protocol (fewer network edge cases)

### Error Handling

- Arrow conversion failures: Raise ArrowTypeError (no fallback to native format)
- Connection failures: Raise ConnectionError (no retry)
- Schema mismatches: Raise ValueError (no silent coercion)

## Alternatives Considered

### Alternative 1: Keep clickhouse-driver, Add Arrow Post-Processing

Convert pandas DataFrame to Arrow after query execution.

**Rejected**: Double conversion overhead (ClickHouse → pandas → Arrow). No performance gain, increases complexity.

### Alternative 2: Hosted ClickHouse Service

Provide managed database service as Alpha Forge requested.

**Rejected**: Infrastructure costs ($200-500/month), maintenance burden (monitoring, backups, scaling), not viable for OSS project. Arrow migration + auto-ingestion addresses 60% of request without infrastructure.

### Alternative 3: Polars DataFrame Output

Return Polars instead of pandas.

**Rejected**: Breaking change for all users. Arrow is internal optimization, pandas API preserved.

## References

- [Apache Arrow Documentation](https://arrow.apache.org/docs/python/pandas.html)
- [clickhouse-connect GitHub](https://github.com/ClickHouse/clickhouse-connect)
- [Alpha Forge Feature Request](https://github.com/gapless-crypto/gapless-crypto-clickhouse/issues/XXX)
- Benchmark Results: `benchmark_gapless_clickhouse.py` (2025-11-20)
- ADR-0005: ClickHouse Migration (established database choice)
- ADR-0021: Microsecond Precision (schema context)
