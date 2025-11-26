# ADR-0041: Gap Filling Validation

**Status**: Accepted

**Date**: 2025-11-25

**Context**: [Plan 0041](../../development/plan/0041-gap-filling-validation/plan.md)

## Context and Problem Statement

ADR-0040 implemented gap filling via REST API in `query_ohlcv()`. The implementation is complete but lacks comprehensive validation for the "fresh data bridge" scenario where Vision CDN lags 1-7 days behind real-time data.

| Component                          | Implementation | Validation       | Status |
| ---------------------------------- | -------------- | ---------------- | ------ |
| `fetch_gap_data()`                 | ADR-0040       | None             | Gap    |
| `_convert_api_data_to_dataframe()` | ADR-0040       | None             | Gap    |
| `_compute_version_hash()`          | ADR-0040       | None             | Gap    |
| Deduplication via FINAL            | ADR-0040       | ADR-0038 partial | Gap    |
| `data_source="rest_api"` tagging   | ADR-0040       | None             | Gap    |

## Decision Drivers

- **Correctness**: Gap-filled data must integrate seamlessly with CDN-sourced data
- **Observability**: Track gap filling operations via structured JSON artifacts
- **Maintainability**: Follow ADR-0038 pipeline pattern for consistency
- **Availability**: Non-blocking CI/CD (validation failures don't block releases)

## Considered Options

1. **Unit tests only** - Fast but doesn't validate production integration
2. **Integration tests only** - Real validation but slow
3. **Production pipeline only** - CI/CD focused but missing edge cases
4. **All three layers (selected)** - Comprehensive coverage with appropriate tradeoffs

## Decision Outcome

**Chosen option**: All three validation layers

**Rationale**:

- Unit tests (Layer 1): Fast feedback (<5s), isolated edge case coverage
- Integration tests (Layer 2): Real API + ClickHouse validation (~90s)
- Production pipeline (Layer 3): ADR-0038 style CI/CD observability

### Validation Architecture

```
Layer 1: Unit Tests
├── test_gap_filling_unit.py (query_api.py functions)
└── test_rest_client_unit.py (rest_client.py functions)

Layer 2: Integration Tests
└── test_gap_filling_integration.py (real API + ClickHouse)

Layer 3: Production Pipeline
├── scripts/validate_gap_filling.py (7-stage pipeline)
├── Earthfile +gap-filling-validation target
└── .github/workflows/production-validation.yml job
```

### Test Data Strategy

| Layer       | Date Strategy                    | Rationale                  |
| ----------- | -------------------------------- | -------------------------- |
| Unit        | Fixed (2024-11-01 to 2024-11-07) | Reproducibility, mocked    |
| Integration | Fixed (2024-11-01 to 2024-11-07) | Reproducibility            |
| Production  | Yesterday (dynamic)              | Fresh data bridge scenario |

### Data Cleanup Policy

Leave data permanently (ADR-0038 pattern). Benefits:

- Validates idempotency via deduplication tests
- Avoids cleanup race conditions
- Production data tagged with `data_source="rest_api"` or `data_source="gap_filling_validation"`

### Consequences

**Good**:

- Comprehensive gap filling validation across all scenarios
- Non-blocking CI/CD with structured JSON artifacts
- Consistent observability with ADR-0038

**Bad**:

- Additional test files to maintain
- Integration tests require network access

## Validation

- [x] Unit tests pass in <5s with 90%+ coverage (44 tests in 0.29s)
- [x] Integration tests pass with real API/ClickHouse (9 tests in 3.49s)
- [x] Production pipeline validates fresh data bridge scenario (7-stage pipeline)
- [x] Deduplication confirmed: re-insert produces same row count (test coverage)
- [x] `data_source="rest_api"` correctly tags gap-filled data (test coverage)
- [x] JSON artifacts exported and uploaded to GitHub Actions (workflow configured)
- [x] No regression in existing validations (ADR-0038) (403 unrelated tests pass)

## Links

- [Plan 0041](../../development/plan/0041-gap-filling-validation/plan.md)
- [ADR-0038](0038-real-binance-data-validation.md) - Real Binance data validation pattern
- [ADR-0040](0040-query-ohlcv-gap-filling.md) - Gap filling implementation
