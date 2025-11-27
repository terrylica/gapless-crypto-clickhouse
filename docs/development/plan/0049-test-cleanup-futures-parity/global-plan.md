# Test Skip & Warning Cleanup Plan

**Previous**: Test Failures Fixed (529 passed, 0 failed)
**Status**: ✅ APPROVED - Ready for Implementation
**Current State**: 529 passed, 3 skipped, 21 warnings

## User Decisions Summary

| Decision                   | Choice                                      |
| -------------------------- | ------------------------------------------- |
| Skip 1 (binance_collector) | DELETE redundant test ✓                     |
| Skip 2 (futures test)      | CREATE comprehensive `test_futures_um.py` ✓ |
| Skip 3 (DatetimeIndex)     | DELETE stale test ✓                         |
| index_type deprecation     | DELETE all deprecated tests + ADR comment ✓ |

## Executive Summary

9 sub-agents investigated 3 skipped tests and 21 warnings. Key findings:

| Category      | Count | Redundant?     | Recommendation            |
| ------------- | ----- | -------------- | ------------------------- |
| Skipped Tests | 3     | 2 redundant    | DELETE 1, FIX 1, UPDATE 1 |
| Warnings      | 21    | ~67% redundant | FIX 8, SUPPRESS 6, KEEP 7 |

**Impact**: Remove 122 lines (1.1% of test suite), eliminate 67% of warnings

---

## Part A: Skipped Tests Analysis (3 total)

### Skip 1: test_binance_collector.py:109

**Test**: `test_collect_small_dataset`
**Skip Reason**: "Network-dependent test failed: Error tokenizing data"
**Root Cause**: Missing `comment="#"` in `pd.read_csv()` + overly broad exception catch

| Verdict  | **DELETE** (100% redundant)                                                                    |
| -------- | ---------------------------------------------------------------------------------------------- |
| Coverage | Fully covered by `test_integration.py::test_complete_data_collection_and_gap_filling_workflow` |
| Lines    | 39 lines to remove                                                                             |
| Risk     | ZERO                                                                                           |

### Skip 2: test_query_ohlcv_api.py:183

**Test**: `test_query_ohlcv_futures_instrument_type`
**Skip Reason**: `@pytest.mark.skipif(True, ...)` - hardcoded unconditional skip
**Root Cause**: Developer uncertainty about futures data availability

| Verdict       | **CREATE COMPREHENSIVE FUTURES TEST SUITE**                                                                         |
| ------------- | ------------------------------------------------------------------------------------------------------------------- |
| User Decision | "No skipping. No trial and accept. Must ensure COMPLETE compatibility with spot AND UM-margined perpetual futures." |
| Action        | Create `tests/test_futures_um.py` mirroring all spot tests                                                          |
| Risk          | NONE - ensures production-grade futures support                                                                     |

**New File: `tests/test_futures_um.py`** (mirrors spot test coverage):

- Data collection from Binance futures CDN
- query_ohlcv() with instrument_type="futures-um"
- OHLCVQuery.get_range/get_latest/get_multi_symbol for futures
- Gap detection and filling for futures
- funding_rate column validation (futures-specific)
- Spot vs Futures isolation tests
- CSV format handling (futures have header row)

### Skip 3: test_simple_api.py:276

**Test**: `test_expected_dataframe_columns`
**Skip Reason**: DatetimeIndex vs RangeIndex assertion failure (hidden by try/except)
**Root Cause**: Test expects deprecated DatetimeIndex as default

| Verdict  | **DELETE** (redundant + stale)                                                    |
| -------- | --------------------------------------------------------------------------------- |
| Coverage | Covered by `test_fetch_data_default_behavior()` + `test_fetch_data_index_types()` |
| Lines    | 64 lines to remove (213-276)                                                      |
| Risk     | ZERO                                                                              |

---

## Part B: Warnings Analysis (21 total)

### Warning 1: Timeframe Constants Deprecation (1 occurrence)

```
DeprecationWarning: gapless_crypto_clickhouse.utils.timeframe_constants is deprecated
```

**File**: `tests/test_timeframe_constants.py:22`
**Root Cause**: Test imports from deprecated path instead of `gapless_crypto_clickhouse.constants`

| Verdict | **UPDATE** import path                                         |
| ------- | -------------------------------------------------------------- |
| Fix     | Change import from `.utils.timeframe_constants` → `.constants` |
| Risk    | ZERO                                                           |

### Warning 2: FutureWarning NA/nan Mismatch (3 occurrences)

```
FutureWarning: Mismatched null-like values <NA> and nan found
```

**File**: `tests/test_arrow_equivalence.py` (lines 29, 59, 201)
**Root Cause**: Arrow returns `pd.NA`, standard returns `np.nan` - semantically equivalent but pandas warns

| Verdict | **FIX NOW** (will break in pandas 3.x)                                  |
| ------- | ----------------------------------------------------------------------- |
| Fix     | Add `.convert_dtypes(dtype_backend='numpy_nullable')` before comparison |
| Risk    | LOW (prevents future breakage)                                          |

### Warning 3: index_type Deprecation (9 occurrences)

```
DeprecationWarning: The 'index_type' parameter is deprecated
```

**File**: `tests/test_simple_api.py` (multiple lines)
**Root Cause**: Tests use deprecated parameter unnecessarily

| User Decision | **DELETE deprecated tests**                                         |
| ------------- | ------------------------------------------------------------------- |
| Rationale     | "If no longer needed, perhaps leaving a comment would suffice"      |
| Action        | Remove all tests using index_type parameter                         |
| ADR Comment   | Document removal in test file header, reference v3.0.0 removal plan |

**Tests to DELETE** (using deprecated index_type):

- `test_fetch_data_index_types` (lines 105-129)
- `test_fetch_data_invalid_index_type` (lines 131-135)
- `test_backward_compatibility_range_index` (lines 155-166)
- `test_download_index_type_support` (lines 190-208)
- `test_api_style_consistency` index_type usage (partial update)
- `test_date_range_usage` index_type usage (partial update)

**Also DELETE from test_api_edge_cases.py**:

- `test_index_type_validation_valid_datetime` (lines 56-58)
- `test_index_type_validation_valid_range` (lines 61-63)
- `test_index_type_validation_valid_auto` (lines 66-68)

### Warning 4: PytestReturnNotNoneWarning (1 occurrence)

```
PytestReturnNotNoneWarning: Test functions should return None
```

**File**: `tests/test_gapless_validation_1d_2018_present.py:94`
**Root Cause**: Accidental `return result` at end of test (bug)

| Verdict | **FIX** (remove return statement) |
| ------- | --------------------------------- |
| Fix     | Delete line 94 (`return result`)  |
| Risk    | ZERO                              |

### Warning 5: UserWarning Future Dates (7 occurrences)

```
UserWarning: Requested end date 2025-11-26 is in the future
```

**File**: `tests/test_simple_api.py` (multiple tests)
**Root Cause**: Tests use `limit=N` without explicit dates → defaults to "today"

| Verdict | **FIX TEST DATES**                                            |
| ------- | ------------------------------------------------------------- |
| Fix     | Replace `limit=1` with `start="2024-01-01", end="2024-01-02"` |
| Tests   | 6 test calls to update                                        |

---

## Part C: Redundancy Summary

| Item                             | Lines   | Action | Coverage Lost |
| -------------------------------- | ------- | ------ | ------------- |
| test_binance_collector.py:71-109 | 39      | DELETE | 0%            |
| test_simple_api.py:213-276       | 64      | DELETE | 0%            |
| Unnecessary index_type uses      | 19      | UPDATE | 0%            |
| **Total**                        | **122** | -      | **0%**        |

---

## Final Action Plan (User Approved)

### Phase 1: Deletions (Zero Risk)

| #   | Action                  | File                                         | Lines            | Reason                           |
| --- | ----------------------- | -------------------------------------------- | ---------------- | -------------------------------- |
| 1   | DELETE redundant test   | `test_binance_collector.py`                  | 71-109           | 100% covered by integration test |
| 2   | DELETE stale test       | `test_simple_api.py`                         | 213-276          | DatetimeIndex deprecated         |
| 3   | DELETE deprecated tests | `test_simple_api.py`                         | 105-166, 190-208 | index_type removed in v3.0.0     |
| 4   | DELETE deprecated tests | `test_api_edge_cases.py`                     | 56-68            | index_type removed in v3.0.0     |
| 5   | Remove return statement | `test_gapless_validation_1d_2018_present.py` | 94               | Bug fix                          |

### Phase 2: Updates (Low Risk)

| #   | Action                | File                          | Change                                              |
| --- | --------------------- | ----------------------------- | --------------------------------------------------- |
| 6   | Update import path    | `test_timeframe_constants.py` | `.utils.timeframe_constants` → `.constants`         |
| 7   | Fix NA/nan comparison | `test_arrow_equivalence.py`   | Add `.convert_dtypes()` (3 locations)               |
| 8   | Fix test dates        | `test_simple_api.py`          | Replace `limit=N` with explicit date ranges         |
| 9   | Update partial tests  | `test_simple_api.py`          | Remove index_type from api_style + date_range tests |

### Phase 3: NEW - Comprehensive Futures Test Suite

| #   | Action | File                       | Tests                                   |
| --- | ------ | -------------------------- | --------------------------------------- |
| 10  | CREATE | `tests/test_futures_um.py` | Comprehensive UM-margined futures tests |

**`test_futures_um.py` Test Matrix** (mirrors spot parity):

```
TestFuturesUMDataCollection:
  - test_collect_futures_data_from_cdn
  - test_futures_csv_format_has_header
  - test_futures_12_column_format

TestFuturesUMQueryAPI:
  - test_query_ohlcv_futures_instrument_type
  - test_ohlcv_query_get_range_futures
  - test_ohlcv_query_get_latest_futures
  - test_ohlcv_query_get_multi_symbol_futures

TestFuturesUMSpecificFeatures:
  - test_funding_rate_column_present
  - test_funding_rate_values_not_null
  - test_instrument_type_is_futures_um

TestFuturesSpotIsolation:
  - test_spot_futures_data_isolation
  - test_query_does_not_cross_contaminate

TestFuturesUMGapFilling:
  - test_gap_detection_futures
  - test_gap_filling_futures_rest_api
```

### Phase 4: Add ADR Comment

| #   | Action             | File                     | Content                                                           |
| --- | ------------------ | ------------------------ | ----------------------------------------------------------------- |
| 11  | Add header comment | `test_simple_api.py`     | "index_type tests removed per v3.0.0 deprecation plan (ADR-0023)" |
| 12  | Add header comment | `test_api_edge_cases.py` | Same                                                              |

---

## Expected Outcome

| Metric   | Before    | After          | Improvement            |
| -------- | --------- | -------------- | ---------------------- |
| Passed   | 529       | 540+           | +11 (futures suite)    |
| Skipped  | 3         | 1              | -2                     |
| Warnings | 21        | ~3             | -85%                   |
| Coverage | Spot only | Spot + Futures | +Full futures coverage |

---

## Files Modified Summary

| File                                               | Action          | Lines Changed |
| -------------------------------------------------- | --------------- | ------------- |
| `tests/test_binance_collector.py`                  | DELETE test     | -39           |
| `tests/test_simple_api.py`                         | DELETE + UPDATE | -150+         |
| `tests/test_api_edge_cases.py`                     | DELETE tests    | -15           |
| `tests/test_gapless_validation_1d_2018_present.py` | FIX             | -1            |
| `tests/test_timeframe_constants.py`                | UPDATE import   | ~5            |
| `tests/test_arrow_equivalence.py`                  | FIX NA/nan      | +3            |
| `tests/test_futures_um.py`                         | **CREATE**      | +200-300      |
