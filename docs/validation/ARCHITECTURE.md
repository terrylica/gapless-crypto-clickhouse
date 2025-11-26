# Validation System Architecture

**Version**: 6.0.0
**Last Updated**: 2025-11-20
**ADR**: [ADR-0024](../architecture/decisions/0024-comprehensive-validation-canonicity.md)

---

## Overview

The validation system consists of **three independent layers**, each serving distinct purposes in the data quality pipeline:

1. **CSV Data Validation** (CSVValidator + DuckDB) - Raw data quality assurance
2. **ClickHouse Query Validation** (E2E Tests + Playwright) - Query interface correctness
3. **Query Performance Validation** (Arrow Benchmarks) - Performance regression detection

This architecture ensures comprehensive validation across the data lifecycle: ingestion → storage → retrieval → performance.

---

## Layer 1: CSV Data Validation

**Purpose**: Validate raw CSV files from CDN/API before ClickHouse ingestion

**Technology Stack**:

- **CSVValidator** (`src/gapless_crypto_clickhouse/validation/csv_validator.py`) - 5-layer validation pipeline
- **ValidationStorage** (`src/gapless_crypto_clickhouse/validation/storage.py`) - DuckDB persistence
- **pandas** - DataFrame manipulation and statistical analysis

**Validation Layers** (5 total):

1. **Structure**: Column presence, format detection (enhanced vs legacy)
2. **DateTime**: Chronological order, gap detection per timeframe
3. **OHLCV Quality**: Logic checks (High ≥ Low, Open/Close within range), negative/zero detection
4. **Coverage**: Expected vs actual bar counts (95-105% thresholds)
5. **Anomaly Detection**: IQR-based outliers, suspicious patterns (>10% repeated values)

**When to Use**:

- Before ingesting new data to ClickHouse
- After gap filling operations
- When investigating data quality issues from upstream sources (Binance CDN/API)

**Unchanged in v6.0.0**: This layer is independent of ClickHouse query optimization (ADR-0023 Arrow migration). CSV validation continues to use DuckDB persistence with identical API.

**Documentation**:

- [Validation Overview](OVERVIEW.md) - 5-layer pipeline details
- [ValidationStorage Specification](STORAGE.md) - DuckDB schema and API
- [Query Patterns](QUERY_PATTERNS.md) - Common validation queries

---

## Layer 2: ClickHouse Query Validation

**Purpose**: Validate query correctness and UI rendering after data ingestion

**Technology Stack**:

- **Playwright 1.56+** - Browser automation for E2E testing
- **pytest-asyncio** - Async test execution
- **Screenshot comparison** - Visual regression detection (automated pixel-diff)

**Test Coverage** (12 E2E tests):

- **CH-UI Dashboard** (localhost:5521): 6 tests (landing page, query execution, error handling, large datasets, edge cases)
- **ClickHouse Play** (localhost:8123/play): 6 tests (same scenarios as CH-UI)

**Validation Scope**:

- Query interface correctness (HTTP protocol, port 8123)
- SQL query execution (FINAL keyword, deduplication)
- UI rendering (result tables, error messages, empty states)
- Visual regression (automated screenshot comparison with baselines)

**When to Use**:

- After schema changes (ALTER TABLE)
- After ClickHouse version upgrades
- After UI changes to CH-UI or ClickHouse Play
- Before releasing new versions

**Added in v6.0.0**: E2E validation framework introduced in ADR-0013 (2025-11-19) to validate Arrow migration correctness.

**Documentation**:

- [E2E Testing Guide](E2E_TESTING_GUIDE.md) - Test writing, execution, debugging
- [Screenshot Baseline Management](SCREENSHOT_BASELINE.md) - Visual regression workflow

---

## Layer 3: Query Performance Validation

**Purpose**: Validate performance claims and detect regressions

**Technology Stack**:

- **tracemalloc** - Memory profiling
- **psutil** - System resource monitoring
- **Comparative benchmarks** - Arrow vs standard query comparison

**Benchmarks** (2 scripts):

1. **benchmark_arrow_scale_analysis.py** - Validates ADR-0023 performance claims across dataset sizes
2. **benchmark_arrow_validation.py** - Compares Arrow vs standard query performance

**Validated Claims** (v6.0.0):

- 2.01x speedup at scale (>8000 rows) ✅
- 43-57% memory reduction for medium/large datasets ✅
- HTTP protocol overhead ~30-40% on small queries (<1000 rows) ✅

**When to Use**:

- After query optimization changes (e.g., Arrow migration)
- When investigating performance regressions
- Before releasing performance-sensitive features
- For validating performance claims in ADRs

**Added in v6.0.0**: Benchmarks created to validate Arrow migration (ADR-0023) performance claims.

**Documentation**:

- ADR-0023: Arrow Migration (performance validation methodology)
- Benchmark scripts (self-documenting with inline comments)

---

## Validation Flow Diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│                     Data Collection Phase                        │
├─────────────────────────────────────────────────────────────────┤
│  Binance CDN/API  →  CSV Files  →  Layer 1: CSV Validation     │
│                                     (CSVValidator + DuckDB)      │
│                                                                   │
│                      ✅ Pass  │  ❌ Fail (log + raise)          │
│                         ↓                                         │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Ingestion Phase                             │
├─────────────────────────────────────────────────────────────────┤
│  Valid CSV  →  ClickHouse Ingestion  →  Layer 2: Schema Check  │
│                (ClickHouseBulkLoader)    (SchemaValidator)       │
│                                                                   │
│                      ✅ Pass  │  ❌ Fail (raise exception)      │
│                         ↓                                         │
└─────────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Query Phase                                │
├─────────────────────────────────────────────────────────────────┤
│  ClickHouse DB  →  Query API  →  Layer 2: E2E Validation       │
│                   (query_ohlcv)   (Playwright tests)             │
│                                                                   │
│                                   Layer 3: Performance Benchmark │
│                                   (Arrow vs standard comparison) │
│                                                                   │
│                      ✅ Pass  │  ❌ Fail (CI alert)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Independence

**Key Principle**: Each validation layer operates independently and can detect distinct failure modes.

**Layer 1 (CSV)**: Detects upstream data quality issues (Binance CDN corrupted files, API rate limits, gap injection attacks)

**Layer 2 (ClickHouse)**: Detects schema drift, query correctness issues, deduplication failures, UI rendering bugs

**Layer 3 (Performance)**: Detects performance regressions, memory leaks, query optimization failures

**No Overlap**: A file can pass Layer 1 (valid CSV structure) but fail Layer 2 (schema mismatch in ClickHouse). A query can pass Layer 2 (correct results) but fail Layer 3 (unacceptable performance regression).

---

## SLO Alignment

All validation layers align with project SLOs:

- **Availability**: Schema validator prevents connections to misconfigured databases (Layer 2)
- **Correctness**: CSV validation + E2E tests + Arrow equivalence guarantee data integrity (Layers 1+2)
- **Observability**: ValidationStorage + CI benchmark artifacts provide queryable validation history (Layers 1+3)
- **Maintainability**: Clear separation of concerns, each layer testable in isolation

---

## When to Use Each Layer

| Scenario                           | Layer 1 (CSV) | Layer 2 (E2E)  | Layer 3 (Perf) |
| ---------------------------------- | ------------- | -------------- | -------------- |
| Investigating data gaps            | ✅ Primary    | -              | -              |
| Validating new ClickHouse version  | -             | ✅ Primary     | ✅ Secondary   |
| After schema changes (ALTER TABLE) | -             | ✅ Primary     | -              |
| Before releasing v6.x.y            | ✅            | ✅             | ✅             |
| Debugging query performance        | -             | -              | ✅ Primary     |
| Validating gap filling             | ✅ Primary    | -              | -              |
| Testing UI changes (CH-UI)         | -             | ✅ Primary     | -              |
| After query optimization (Arrow)   | -             | ✅ Correctness | ✅ Performance |

---

## Version History

- **v3.3.0** (2025-10-27): Layer 1 added (CSVValidator + DuckDB persistence)
- **v6.0.0** (2025-11-19): Layer 2 added (E2E Playwright tests, ADR-0013)
- **v6.0.0** (2025-11-20): Layer 3 added (Arrow benchmarks, ADR-0023)
- **v6.0.0** (2025-11-20): Schema validator added to Layer 2 (ADR-0024)

---

## References

- [ADR-0013: Autonomous Validation Framework](../architecture/decisions/0013-autonomous-validation-framework.md) - E2E test design
- [ADR-0023: Arrow Migration](../architecture/decisions/0023-arrow-migration.md) - Performance validation
- [ADR-0024: Comprehensive Validation Canonicity](../architecture/decisions/0024-comprehensive-validation-canonicity.md) - This architecture
- [Validation Overview](OVERVIEW.md) - Layer 1 details
- [E2E Testing Guide](E2E_TESTING_GUIDE.md) - Layer 2 details
