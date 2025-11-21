# Comprehensive Validation System Canonicity for v6.0.0

**ADR ID**: 0024
**Status**: In Progress
**Owner**: Eon Labs Engineering
**Created**: 2025-11-20
**Last Updated**: 2025-11-20

---

## (a) Plan

### Objective

Update validation system to canonical v6.0.0 state: fix documentation drift, implement runtime schema validation, prove query correctness, validate data integrity, automate screenshot comparison, integrate benchmarks into CI.

### Scope

**In Scope**:

- Documentation: Update 15 files (version headers, DateTime64 precision, validation architecture)
- Schema Validation: New SchemaValidator module with strict validation (raise on mismatch)
- Query Correctness: 8 Arrow equivalence tests, 15 query_ohlcv() tests
- Data Integrity: 15 tests (multi-symbol isolation, deduplication proof, protocol validation)
- E2E: Automated screenshot comparison, generate 12 baselines
- CI/CD: Benchmark job (informational), all E2E tests with comparison

**Out of Scope**:

- Backward compatibility tests for v5.0.0 → v6.0.0 migration (migration guide sufficient)
- Performance optimization (already validated in ADR-0023)
- Security hardening (not SLO focus)
- UI/UX improvements to web interfaces

### Success Metrics

- **Documentation**: 100% canonical (all version numbers, timestamps match v6.0.0)
- **Schema Validation**: 100% coverage (column types, engine, partitioning, sorting, compression)
- **Query Correctness**: 100% Arrow equivalence proven (8/8 tests pass)
- **API Coverage**: 100% query_ohlcv() tested (15/15 tests pass)
- **Data Integrity**: 100% isolation/deduplication proven (15/15 tests pass)
- **E2E**: 100% baselines generated (12/12 screenshots), automated comparison working
- **Trustworthiness**: ≥95/100 (target: 98/100, up from 85/100)
- **Test Count**: 100+ total tests (46 new tests added)

### Non-Goals

- Implementing hosted ClickHouse service (out of scope for OSS project)
- Optimizing existing validation performance (already fast enough)
- Adding new validation layers beyond CSV/ClickHouse/Performance
- Refactoring existing validation code (focus on gaps, not improvements)

---

## (b) Context

### Background

**v6.0.0 Release (2025-11-20)**: Arrow migration (ADR-0023) achieved 2x speedup at scale, but post-release multi-agent investigation revealed validation system not canonical:

1. **Documentation Drift**: E2E docs claim v1.0.0 (5-version lag), 6 files claim DateTime64(3) (actual: DateTime64(6))
2. **Missing Runtime Validation**: No code validates ClickHouse schema matches schema.sql expectations
3. **Untested v6.0.0 Features**: Arrow correctness not proven, query_ohlcv() untested, protocol change unvalidated
4. **E2E Gaps**: Screenshot baselines never generated, comparison manual, CH-UI tests skipped in CI

### Problem Statement

**Data Loss Risk**: If ClickHouse schema drifts to DateTime64(3), microsecond data truncated to milliseconds → 1000x data loss, NO detection mechanism

**Correctness Risk**: Arrow optimization (v6.0.0) tested for performance, NOT correctness → no proof queries return identical results

**API Coverage Gap**: query_ohlcv() is core v6.0.0 feature (unified API, auto-ingestion), zero dedicated tests

**Integrity Risk**: No tests prove multi-symbol isolation (BTCUSDT vs ETHUSDT), FINAL keyword deduplication, protocol change (HTTP vs TCP)

### Constraints

- **No Breaking Changes**: Schema validator must not break existing valid schemas
- **No Performance Regression**: Validation overhead <100ms per connection
- **No CI Slowdown**: Benchmark job must not block fast tests (separate job, informational)
- **No Backward Compatibility**: v6.0.0 is breaking change (documented), focus on canonical state
- **SLO Focus**: availability/correctness/observability/maintainability (NOT speed/perf/security)
- **Error Handling**: raise+propagate (no fallback, no retry, no silent failures)

### Assumptions

- ClickHouse 24.11+ available (Docker Compose provided)
- schema.sql is correct (DateTime64(6), ReplacingMergeTree, 17 columns)
- E2E tests can run locally (Playwright 1.56+ installed via uv)
- CI has GitHub Actions access for benchmark artifacts
- Users follow migration guide for v5.0.0 → v6.0.0 (no automated migration tests needed)

### Dependencies

**Internal**:

- schema.sql (canonical schema definition)
- ClickHouseConnection (connection management)
- ADR-0023 (Arrow migration baseline)
- ADR-0021 (DateTime64(6) upgrade rationale)
- ADR-0013 (E2E framework architecture)

**External**:

- clickhouse-connect ≥0.7.0 (HTTP client)
- pyarrow ≥14.0.0 (Arrow format support)
- playwright ≥1.56.0 (E2E browser automation)
- pytest-asyncio ≥0.26.0 (async test support)
- DuckDB (ValidationStorage persistence)

### Risks & Mitigation

| Risk                                            | Impact | Probability | Mitigation                                                |
| ----------------------------------------------- | ------ | ----------- | --------------------------------------------------------- |
| Schema validator breaks existing valid schemas  | High   | Low         | Test with schema.sql first, comprehensive test coverage   |
| Screenshot comparison flaky (timing, rendering) | Medium | Medium      | Generous thresholds (max_diff_pixels=100), retry logic    |
| Benchmark CI adds significant pipeline time     | Low    | High        | Separate job (doesn't block tests), cache ClickHouse data |
| New tests discover bugs in v6.0.0               | High   | Medium      | Expected! Fix bugs, document in ADR if breaking           |
| Documentation update overwhelming               | Low    | Low         | Automated find-replace for version numbers, DateTime64    |

---

## (c) Task List

### Phase 1: Documentation Updates (Day 1, 4-6h)

- [ ] **Task 1.1**: Update version headers (3 files)
  - E2E_TESTING_GUIDE.md line 7: "Version: 1.0.0" → "Version: 6.0.0"
  - SCREENSHOT_BASELINE.md line 7: "Version: 1.0.0" → "Version: 6.0.0"
  - CURRENT_ARCHITECTURE_STATUS.yaml: "v1.0.0" → "v6.0.0"

- [ ] **Task 1.2**: Fix DateTime64(3) → DateTime64(6) (6 files)
  - DATA_FORMAT.md: Update timestamp/close_time precision
  - OVERVIEW.md: Update timestamp precision
  - CLICKHOUSE_MIGRATION.md: Update schema examples
  - ADR-0005: Add "Superseded by ADR-0021" note
  - ADR-0012: Update timestamp precision
  - plan/0012-\*/plan.md: Update timestamp precision

- [ ] **Task 1.3**: Create validation architecture document
  - New file: docs/validation/ARCHITECTURE.md
  - Document three validation layers: CSV/DuckDB, ClickHouse/E2E, Performance/Benchmarks
  - Explain when to use each layer

- [ ] **Task 1.4**: Add v6.0.0 compatibility clarifications
  - OVERVIEW.md: Add section explaining v6.0.0 compatibility
  - Reference ADR-0023 for query performance validation

- [ ] **Task 1.5**: Update CLAUDE.md and README.md
  - Add ARCHITECTURE.md reference
  - Update validation section with new coverage

**Validation**: Run `grep -r "DateTime64(3)" docs/` → expect 0 results, `grep -r "Version: 1.0.0" docs/validation/` → expect 0 results

---

### Phase 2: Schema Runtime Validation (Day 2, 6-8h)

- [ ] **Task 2.1**: Implement SchemaValidator module
  - New file: src/gapless_crypto_clickhouse/clickhouse/schema_validator.py
  - ExpectedSchema dataclass (17 columns, engine config, codecs)
  - SchemaValidator class with validation methods
  - SchemaValidationError exception class

- [ ] **Task 2.2**: Integrate into ClickHouseConnection
  - Modify src/gapless_crypto_clickhouse/clickhouse/connection.py
  - Add SchemaValidator call in **enter**() after health_check()
  - Log validation success/failure

- [ ] **Task 2.3**: Add schema validation tests
  - New file: tests/test_schema_validation.py
  - 8 tests: happy path, missing column, wrong type, wrong engine, missing version, wrong partition, wrong sorting, exception propagation

- [ ] **Task 2.4**: Validate schema validator
  - Run: `uv run pytest tests/test_schema_validation.py -v`
  - Verify all 8 tests pass

**Validation**: Run `uv run pytest tests/test_schema_validation.py -v` → expect 8/8 pass

---

### Phase 3: Arrow Query Equivalence (Day 3, 4-6h)

- [ ] **Task 3.1**: Create Arrow equivalence test suite
  - New file: tests/test_arrow_equivalence.py
  - 8 tests: simple query, large dataset, column order, data types, NULL handling, empty result, single row, special characters

- [ ] **Task 3.2**: Validate Arrow equivalence
  - Run: `uv run pytest tests/test_arrow_equivalence.py -v`
  - Verify all 8 tests pass
  - Confirm Arrow returns identical results to standard queries

**Validation**: Run `uv run pytest tests/test_arrow_equivalence.py -v` → expect 8/8 pass

---

### Phase 4: query_ohlcv() Test Suite (Day 4-5, 8-10h)

- [ ] **Task 4.1**: Create query_ohlcv test suite
  - New file: tests/test_query_ohlcv_api.py
  - 15 tests: auto-ingestion (4), multi-symbol (3), instrument type (3), error handling (3), edge cases (2)

- [ ] **Task 4.2**: Validate query_ohlcv API
  - Run: `uv run pytest tests/test_query_ohlcv_api.py -v`
  - Verify all 15 tests pass
  - Confirm auto-ingestion, idempotency, multi-symbol, error handling work

**Validation**: Run `uv run pytest tests/test_query_ohlcv_api.py -v` → expect 15/15 pass

---

### Phase 5: Data Integrity Tests (Day 6, 6-8h)

- [ ] **Task 5.1**: Multi-symbol isolation tests
  - New file: tests/test_multi_symbol_isolation.py
  - 5 tests: BTCUSDT/ETHUSDT isolation, ingestion isolation, spot/futures isolation, instrument_type filter, timeframe isolation

- [ ] **Task 5.2**: Deduplication proof tests
  - New file: tests/test_deduplication_final.py
  - 6 tests: FINAL deduplicates, without FINAL returns duplicates, version hash determinism, collision resistance, re-ingestion idempotency, latest version wins

- [ ] **Task 5.3**: Protocol validation tests
  - New file: tests/test_protocol_http.py
  - 4 tests: HTTP port 8123, health check via HTTP, query via HTTP, HTTP error propagation

- [ ] **Task 5.4**: Validate data integrity
  - Run: `uv run pytest tests/test_multi_symbol_isolation.py tests/test_deduplication_final.py tests/test_protocol_http.py -v`
  - Verify all 15 tests pass (5+6+4)

**Validation**: Run data integrity tests → expect 15/15 pass

---

### Phase 6: E2E Enhancements (Day 7, 6-8h)

- [ ] **Task 6.1**: Implement automated screenshot comparison
  - Modify: tests/e2e/test_ch_ui_dashboard.py (add expect(page).to_have_screenshot())
  - Modify: tests/e2e/test_clickhouse_play.py (add expect(page).to_have_screenshot())
  - Configure thresholds: max_diff_pixels=100, threshold=0.2

- [ ] **Task 6.2**: Generate screenshot baselines
  - Start services: `docker-compose up -d`
  - Run E2E tests: `uv run scripts/run_validation.py --e2e-only`
  - Review generated screenshots in tests/e2e/screenshots/
  - Commit 12 baselines to git

- [ ] **Task 6.3**: Validate E2E enhancements
  - Re-run: `uv run scripts/run_validation.py --e2e-only`
  - Verify screenshot comparison detects no differences (baselines match)

**Validation**: Run E2E tests twice → first generates baselines, second compares successfully

---

### Phase 7: CI/CD Integration (Day 8, 4-6h)

- [ ] **Task 7.1**: Add benchmark CI job
  - Modify: .github/workflows/ci.yml
  - Add new job: benchmark (informational, non-blocking)
  - Configure: run benchmark_arrow_scale_analysis.py, upload results as artifacts

- [ ] **Task 7.2**: Update E2E CI job
  - Modify: .github/workflows/ci.yml
  - Update E2E job to run all 12 tests (CH-UI + ClickHouse Play)
  - Add screenshot comparison validation
  - Upload screenshot diffs on failure

- [ ] **Task 7.3**: Validate CI integration
  - Push to feature branch
  - Verify CI runs successfully (all jobs green)
  - Check benchmark artifacts uploaded

**Validation**: Push feature branch, check CI status → all jobs pass

---

### Phase 8: Validation & Documentation (Day 9-10, 6-8h)

- [ ] **Task 8.1**: Run complete validation suite
  - Start ClickHouse: `docker-compose up -d`
  - Run full validation: `uv run scripts/run_validation.py`
  - Verify all phases pass (static, unit, integration, E2E)

- [ ] **Task 8.2**: Create validation coverage report
  - New file: docs/validation/COVERAGE_REPORT.md
  - Document test counts, coverage metrics, trustworthiness score

- [ ] **Task 8.3**: Update documentation index
  - Update docs/validation/OVERVIEW.md with new test references
  - Update CLAUDE.md with ARCHITECTURE.md link
  - Update README.md E2E validation section

- [ ] **Task 8.4**: Final validation check
  - Run: `uv run pytest -v`
  - Confirm: 100+ tests pass
  - Verify: Zero validation errors

**Validation**: Full test suite passes, coverage report shows 98/100 trustworthiness

---

### Phase 9: Release & Merge (Day 11, 2-4h)

- [ ] **Task 9.1**: Create conventional commit
  - Message: "feat(validation)!: comprehensive v6.0.0 canonicity update with schema validation, Arrow equivalence, query_ohlcv tests"
  - Body: Reference ADR-0024, list breaking changes (schema validator strict mode)

- [ ] **Task 9.2**: Run semantic-release (if applicable)
  - Version bump: Patch/minor depending on breaking changes
  - Generate CHANGELOG.md entry
  - Create GitHub release

- [ ] **Task 9.3**: Create pull request
  - Title: "feat(validation)!: Comprehensive E2E validation canonicity for v6.0.0 (ADR-0024)"
  - Description: Link to ADR-0024, summarize changes, note breaking changes

- [ ] **Task 9.4**: Merge after approval
  - Request review
  - Address feedback
  - Merge to main

**Validation**: PR approved, merged, CI passes on main

---

## Progress Tracking

**Overall Progress**: 22% (8/36 tasks complete)

**Phase Status**:

- Phase 1 (Documentation): ✅ Complete (5/5 tasks)
- Phase 2 (Schema Validation): ✅ Complete (4/4 tasks, tests pending ClickHouse)
- Phase 3 (Arrow Equivalence): 🔴 Not Started
- Phase 4 (query_ohlcv Tests): 🔴 Not Started
- Phase 5 (Data Integrity): 🔴 Not Started
- Phase 6 (E2E Enhancements): 🔴 Not Started
- Phase 7 (CI Integration): 🔴 Not Started
- Phase 8 (Validation & Docs): 🔴 Not Started
- Phase 9 (Release): 🔴 Not Started

**Last Updated**: 2025-11-20 (Phases 1-2 completed)

---

## Notes

- Auto-validate after each task completion
- Update this plan if scope/context changes
- Keep ADR-0024 in sync with plan status
- Log nohup runs to logs/0024-comprehensive-validation-canonicity-YYYYMMDD_HHMMSS.log
