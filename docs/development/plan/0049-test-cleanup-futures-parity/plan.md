# Plan: Test Suite Cleanup and UM Futures Parity

**ADR**: [ADR-0049](/docs/architecture/decisions/0049-test-cleanup-futures-parity.md)
**Status**: In Progress
**Created**: 2024-11-26

---

## Context

### Problem Statement

The test suite (529 passed, 3 skipped, 21 warnings) contains:

- Redundant tests providing zero unique coverage
- Deprecated parameter tests for `index_type` (removed in v3.0.0)
- Incomplete futures test coverage despite production support for 715 UM futures symbols

### Requirements

- Remove all redundant tests (priority per user directive)
- Ensure COMPLETE compatibility between spot and UM-margined perpetual futures
- Eliminate deprecated test warnings
- Fix remaining technical warnings (NA/nan, dates, imports)

### Constraints

- SLO: Correctness over speed
- No backward compatibility required
- Auto-validate after each change

---

## Plan

### Phase 1: Deletions (Zero Risk)

| File                                               | Lines            | Reason                           |
| -------------------------------------------------- | ---------------- | -------------------------------- |
| `tests/test_binance_collector.py`                  | 71-109           | 100% covered by integration test |
| `tests/test_simple_api.py`                         | 213-276          | Stale DatetimeIndex assertion    |
| `tests/test_simple_api.py`                         | 105-166, 190-208 | Deprecated index_type tests      |
| `tests/test_api_edge_cases.py`                     | 56-68            | Deprecated index_type tests      |
| `tests/test_gapless_validation_1d_2018_present.py` | 94               | Remove accidental return         |

### Phase 2: Updates (Low Risk)

| File                                | Change                                                    |
| ----------------------------------- | --------------------------------------------------------- |
| `tests/test_timeframe_constants.py` | Import from `.constants` not `.utils.timeframe_constants` |
| `tests/test_arrow_equivalence.py`   | Add `.convert_dtypes()` for NA/nan compatibility          |
| `tests/test_simple_api.py`          | Replace `limit=N` with explicit date ranges               |

### Phase 3: Create Futures Test Suite

Create `tests/test_futures_um.py` with comprehensive coverage:

```
TestFuturesUMDataCollection
├── test_collect_futures_data_from_cdn
├── test_futures_csv_format_has_header
└── test_futures_12_column_format

TestFuturesUMQueryAPI
├── test_query_ohlcv_futures_instrument_type
├── test_ohlcv_query_get_range_futures
├── test_ohlcv_query_get_latest_futures
└── test_ohlcv_query_get_multi_symbol_futures

TestFuturesUMSpecificFeatures
├── test_funding_rate_column_present
├── test_funding_rate_values_not_null
└── test_instrument_type_is_futures_um

TestFuturesSpotIsolation
├── test_spot_futures_data_isolation
└── test_query_does_not_cross_contaminate

TestFuturesUMGapFilling
├── test_gap_detection_futures
└── test_gap_filling_futures_rest_api
```

### Phase 4: Documentation

- Add ADR-0049 comments to modified files
- Update test file headers with deprecation notes

---

## Task List

- [ ] Create ADR-0049
- [ ] Create plan document
- [ ] Phase 1: Delete redundant tests
- [ ] Phase 2: Update imports and fix warnings
- [ ] Phase 3: Create test_futures_um.py
- [ ] Phase 4: Add ADR comments
- [ ] Run full test suite and validate

---

## Expected Outcome

| Metric           | Before  | After    |
| ---------------- | ------- | -------- |
| Passed           | 529     | 540+     |
| Skipped          | 3       | 1        |
| Warnings         | 21      | ~3       |
| Futures Coverage | Partial | Complete |

---

## Files Modified

| File                                               | Action          |
| -------------------------------------------------- | --------------- |
| `tests/test_binance_collector.py`                  | DELETE test     |
| `tests/test_simple_api.py`                         | DELETE + UPDATE |
| `tests/test_api_edge_cases.py`                     | DELETE tests    |
| `tests/test_gapless_validation_1d_2018_present.py` | FIX             |
| `tests/test_timeframe_constants.py`                | UPDATE import   |
| `tests/test_arrow_equivalence.py`                  | FIX NA/nan      |
| `tests/test_futures_um.py`                         | **CREATE**      |
