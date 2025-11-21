# ADR-0024: Comprehensive Validation System Canonicity for v6.0.0

## Status

✅ **Implemented** (2025-11-21)

- Accepted: 2025-11-20
- Implemented: 2025-11-20 (commit fece5db)
- CI Validated: 2025-11-21 (commit 1d1b818)
- Version: 6.0.5

## Implementation

See [COMPLETION_REPORT.md](../../development/plan/0024-comprehensive-validation-canonicity/COMPLETION_REPORT.md) for full CI validation results and deliverables.

## Context

### Problem Statement

Post-v6.0.0 Arrow migration (ADR-0023), multi-agent investigation revealed validation system has critical gaps:

**Documentation Drift**:

- E2E docs claim "Version: 1.0.0" (actual: v6.0.0, 5-version drift)
- 6 files claim DateTime64(3) millisecond precision (actual: DateTime64(6) microsecond, per ADR-0021)
- No documentation explaining relationship between CSV validation (DuckDB), ClickHouse validation (E2E), and performance validation (benchmarks)

**Missing Runtime Validation**:

- **Schema validation gap**: No runtime check verifies ClickHouse schema matches expected schema.sql
- Risk: DateTime64(3) vs DateTime64(6) mismatch could occur silently, causing 1000x data loss
- Risk: Wrong engine (MergeTree vs ReplacingMergeTree) breaks zero-gap guarantee

**Untested v6.0.0 Features**:

- **Arrow query equivalence**: Performance benchmarks exist, but NO test proves Arrow queries return identical results to standard queries
- **query_ohlcv() API**: Core v6.0.0 feature (unified API with auto-ingestion) has zero dedicated tests
- **Protocol change**: v6.0.0 uses HTTP (port 8123), not native TCP (port 9000), no explicit validation
- **Data integrity**: No tests prove multi-symbol isolation (BTCUSDT query doesn't leak ETHUSDT data) or FINAL keyword deduplication

**E2E Test Gaps**:

- Screenshot baselines never generated (tests/e2e/screenshots/ directory doesn't exist)
- Screenshot comparison is manual (no automated pixel-diff validation)
- CH-UI tests skipped in CI (requires interactive configuration)

### Success Criteria (v6.0.0 Canonical State)

Validation system is canonical when:

1. **Documentation accurate**: All version numbers, timestamp precision, references match v6.0.0 reality
2. **Schema validation exists**: Runtime validator detects schema drift, raises exceptions (no silent failures)
3. **Query correctness proven**: Arrow queries return identical results to standard queries
4. **API coverage complete**: query_ohlcv() tested for auto-ingestion, idempotency, multi-symbol, error handling
5. **Data integrity validated**: Multi-symbol isolation and deduplication proven with tests
6. **E2E functional**: Screenshot baselines exist, automated comparison working
7. **Trustworthiness high**: Validation system score ≥95/100 (currently 85/100)

### Multi-Agent Investigation Summary

Six parallel agents investigated validation state:

**Agent 1 (E2E State)**: Found complete E2E framework (12 tests, ADR-0013) but frozen at v1.0.0, never executed
**Agent 2 (Schema)**: Found schema.sql correct (DateTime64(6)) but 6 docs claim DateTime64(3), zero runtime validation
**Agent 3 (Data Integrity)**: Found deduplication logic exists but no test validates FINAL keyword, no multi-symbol isolation test
**Agent 4 (Meta-Validation)**: Found ValidationStorage well-tested (12 tests) but screenshot comparison manual, no baseline automation
**Agent 5 (Documentation)**: Found docs 100% aligned with code BUT missing v6.0.0 context, three validation layers not explained
**Agent 6 (v6.0.0 Gaps)**: Found Arrow performance validated but correctness NOT proven, query_ohlcv() untested, protocol change unvalidated

## Decision

Implement comprehensive validation update to achieve v6.0.0 canonical state across 4 dimensions:

### 1. Documentation Canonicity

**Update all docs to v6.0.0 reality**:

- Version headers: 1.0.0 → 6.0.0 (E2E_TESTING_GUIDE.md, SCREENSHOT_BASELINE.md, CURRENT_ARCHITECTURE_STATUS.yaml)
- Timestamp precision: DateTime64(3) → DateTime64(6) in 6 files
- Create ARCHITECTURE.md explaining three validation layers (CSV/DuckDB, ClickHouse/E2E, Performance/Benchmarks)

### 2. Schema Runtime Validation

**Implement SchemaValidator module**:

- Validate schema at connection time via system.columns, system.tables queries
- Detect: column types (DateTime64(6) vs (3)), engine config (ReplacingMergeTree), partition/sorting keys, compression codecs
- **Behavior**: STRICT - Raise SchemaValidationError on any mismatch (no fallback, no retry)
- **Integration**: ClickHouseConnection.**enter**() calls validator after health_check()

### 3. Query Correctness Validation

**Prove Arrow query equivalence** (8 tests):

- Verify Arrow-optimized queries return identical results to standard queries
- Validate: data equivalence, column order, data types (DateTime64(6)), NULL handling, edge cases

**Comprehensive query_ohlcv() testing** (15 tests):

- Auto-ingestion: downloads missing data, idempotent on subsequent calls
- Multi-symbol: list of symbols returns combined DataFrame, isolation verified
- Instrument type: spot vs futures-um separation validated
- Error handling: invalid symbol/timeframe/date format raises exceptions

### 4. Data Integrity Validation

**Multi-symbol isolation tests** (5 tests):

- Prove BTCUSDT query doesn't return ETHUSDT data (no cross-contamination)
- Verify spot vs futures isolation via instrument_type filter
- Validate timeframe isolation (1h data doesn't appear in 4h query)

**Deduplication proof tests** (6 tests):

- Prove FINAL keyword deduplicates (compare with/without FINAL)
- Verify version hash determinism (identical inputs → identical hashes)
- Validate re-ingestion idempotency (row count unchanged)

**Protocol validation tests** (4 tests):

- Verify v6.0.0 uses HTTP protocol (port 8123)
- Validate HTTP health check and query execution
- Verify HTTP error propagation (400, 500 → exceptions)

### 5. E2E Enhancements

**Automated screenshot comparison**:

- Implement Playwright's `expect(page).to_have_screenshot()` with pixel-diff thresholds
- Configure: max_diff_pixels=100, threshold=0.2 (20% per-pixel tolerance)
- Generate and commit 12 screenshot baselines

**CI integration**:

- Add benchmark job (informational, non-blocking) to track performance trends
- Run all 12 E2E tests in CI with automated screenshot comparison

## Consequences

### Positive

1. **Documentation canonical**: All docs match v6.0.0 reality, no misleading timestamp precision claims
2. **Schema drift detection**: Runtime validator prevents silent schema mismatches (1000x data loss risk eliminated)
3. **Query correctness guaranteed**: Arrow equivalence tests prove v6.0.0 optimization didn't break correctness
4. **API coverage complete**: query_ohlcv() fully tested, auto-ingestion behavior validated
5. **Data integrity proven**: Multi-symbol isolation and deduplication validated with automated tests
6. **E2E functional**: Screenshot baselines exist, visual regression detection automated
7. **Trustworthiness increased**: 85/100 → 98/100 (46 new tests added, 100+ total tests)
8. **CI enforcement**: Benchmarks run automatically, performance trends tracked

### Negative

1. **Implementation effort**: 44-60 hours (8-12 days) for comprehensive update
2. **CI duration increase**: Benchmark job adds ~5 minutes to pipeline (mitigated: separate job, doesn't block fast tests)
3. **Screenshot maintenance**: 12 baselines to update when UI changes (mitigated: automated comparison catches regressions early)
4. **Schema validator overhead**: Adds ~50-100ms to connection time (mitigated: caching possible, acceptable for correctness guarantee)

### Neutral

1. **Breaking change potential**: Schema validator may discover existing schema drift in user environments (intentional, forces fix)
2. **Test count increase**: 46 new tests added, increases maintenance burden (acceptable, critical coverage gaps)

## Implementation Plan

See: `/docs/development/plan/0024-comprehensive-validation-canonicity/plan.md`

**Phases**:

1. Documentation updates (Day 1, 4-6h)
2. Schema runtime validation (Day 2, 6-8h)
3. Arrow query equivalence (Day 3, 4-6h)
4. query_ohlcv() test suite (Day 4-5, 8-10h)
5. Data integrity tests (Day 6, 6-8h)
6. E2E enhancements (Day 7, 6-8h)
7. CI/CD integration (Day 8, 4-6h)
8. Validation & documentation (Day 9-10, 6-8h)

**Estimated Total**: 44-60 hours (8-12 days)

## SLO Impact

**Availability**: ✅ Improved - Schema validator prevents connections to misconfigured databases
**Correctness**: ✅ Improved - Arrow equivalence, multi-symbol isolation, deduplication proven
**Observability**: ✅ Improved - Schema validation errors explicit, benchmark trends tracked in CI
**Maintainability**: ✅ Improved - Documentation canonical, validation architecture documented

## Validation Strategy

After each phase:

1. Run affected tests: `uv run pytest <test_file> -v`
2. Run full validation: `uv run scripts/run_validation.py`
3. Verify zero errors before proceeding to next phase

Final validation:

- All tests pass (100+ tests)
- Schema validator integrated and tested
- Screenshot baselines generated and committed
- CI pipeline green with benchmark job

## References

- ADR-0021: UM Futures Support (DateTime64(6) upgrade)
- ADR-0023: Arrow Migration (v6.0.0 performance optimization)
- ADR-0013: Autonomous Validation Framework (E2E Playwright tests)
- Multi-agent investigation reports (6 parallel agents, 2025-11-20)

## Acceptance Criteria

✅ All documentation version numbers match v6.0.0
✅ All DateTime64 references correct (microsecond precision)
✅ SchemaValidator module implemented and integrated
✅ Arrow query equivalence tests pass (8 tests)
✅ query_ohlcv() comprehensive tests pass (15 tests)
✅ Data integrity tests pass (15 tests: multi-symbol + deduplication + protocol)
✅ E2E screenshot baselines generated and committed (12 baselines)
✅ Automated screenshot comparison working
✅ Benchmark CI job running (informational, non-blocking)
✅ Validation system trustworthiness score ≥95/100
✅ Zero validation errors in full test suite
