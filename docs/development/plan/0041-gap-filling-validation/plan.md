# Plan 0041: Gap Filling Validation Design

**ADR**: [ADR-0041](../../../architecture/decisions/0041-gap-filling-validation.md)

**Status**: Complete

**Author**: Claude Code

**Last Updated**: 2025-11-25

---

## Overview

Implement comprehensive validations for the gap filling feature (ADR-0040) ensuring REST API correctly fills gaps where Vision CDN lags 1-7 days.

### Goals

1. Unit tests for isolated function validation (<5s execution)
2. Integration tests for real API + ClickHouse validation (~90s)
3. Production pipeline (ADR-0038 pattern) for CI/CD observability

### Non-Goals

- tenacity retry logic testing (covered in ADR-0040)
- Performance benchmarking
- Rate limit stress testing

---

## Context

### Problem

ADR-0040 implemented gap filling but lacks validation for critical scenarios:

| Scenario               | Description                                | Risk   |
| ---------------------- | ------------------------------------------ | ------ |
| Fresh data bridge      | Vision API lags 1-7 days behind real-time  | High   |
| Large gap chunking     | Gaps >1000 bars require multiple API calls | Medium |
| Version hash collision | Different data producing same hash         | Low    |
| Deduplication failure  | Re-insert doubles row count                | High   |
| Data source tagging    | `rest_api` vs `cloudfront` provenance      | Medium |

### User Decisions

- **Scope**: All three layers (Unit + Integration + Production pipeline)
- **Test Data**: Both strategies (yesterday for production, fixed dates for unit/integration)
- **CI/CD**: production-validation.yml only (scheduled every 6 hours)
- **Data Cleanup**: Leave permanently (ADR-0038 pattern, validates idempotency)

### Reference Implementation

ADR-0038 `scripts/validate_binance_real_data.py`:

- 9-stage pipeline pattern
- JSON artifact schema
- Non-blocking Earthly targets
- Pushover notification integration

---

## Task List

| #   | Task                                       | Status | Notes                                                                    |
| --- | ------------------------------------------ | ------ | ------------------------------------------------------------------------ |
| 1   | Create ADR-0041 and plan                   | Done   | This document                                                            |
| 2   | Add fixtures to conftest.py                | Done   | sample_gap_dataframe, sample_api_kline_response, sample_api_candle_dicts |
| 3   | Implement test_gap_filling_unit.py         | Done   | Unit tests for query_api.py functions                                    |
| 4   | Implement test_rest_client_unit.py         | Done   | Unit tests for rest_client.py functions                                  |
| 5   | Implement test_gap_filling_integration.py  | Done   | Integration tests with real API/ClickHouse                               |
| 6   | Implement scripts/validate_gap_filling.py  | Done   | 7-stage production pipeline                                              |
| 7   | Add Earthly target +gap-filling-validation | Done   | Added to Earthfile                                                       |
| 8   | Update production-validation.yml           | Done   | Add gap-filling-validation job                                           |
| 9   | Run validations, verify all pass           | Done   | 53 tests pass (21 unit, 23 rest_client, 9 integration)                   |

---

## Architecture Diagram

```sql
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADR-0041 Gap Filling Validation                          │
│                      Three-Layer Validation Model                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Layer 1       │    │   Layer 2       │    │   Layer 3       │
│   Unit Tests    │    │ Integration     │    │  Production     │
│                 │    │    Tests        │    │   Pipeline      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Mocked httpx  │    │ • Real Binance  │    │ • 7-Stage       │
│ • Isolated      │    │   REST API      │    │   Pipeline      │
│ • <5s runtime   │    │ • Real ClickHse │    │ • JSON Artifact │
│ • Fixed dates   │    │ • ~90s runtime  │    │ • Every 6 hours │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Test Execution Targets                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  pytest tests/          │  pytest -m integration   │  earthly +gap-filling- │
│  test_gap_filling_      │  tests/test_gap_filling  │  validation            │
│  unit.py                │  _integration.py         │                        │
│  test_rest_client_      │                          │  production-validation │
│  unit.py                │                          │  .yml (scheduled)      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Data Flow Topology                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │ Binance REST │     │  fetch_gap   │     │  DataFrame   │               │
│   │ API (Spot/   │────▶│  _data()     │────▶│  Conversion  │               │
│   │ Futures)     │     │              │     │  (18 cols)   │               │
│   └──────────────┘     └──────────────┘     └──────┬───────┘               │
│                                                    │                        │
│                                                    ▼                        │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐               │
│   │ ClickHouse   │◀────│ Version Hash │◀────│ data_source= │               │
│   │ Insert       │     │ (_version)   │     │ "rest_api"   │               │
│   │ (FINAL dedup)│     │ SHA256       │     │              │               │
│   └──────────────┘     └──────────────┘     └──────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    7-Stage Production Pipeline                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐   ┌───┐                     │
│  │ 1 │──▶│ 2 │──▶│ 3 │──▶│ 4 │──▶│ 5 │──▶│ 6 │──▶│ 7 │                     │
│  └───┘   └───┘   └───┘   └───┘   └───┘   └───┘   └───┘                     │
│   API    Fresh   Resp.   DF      Hash   Click-  Dedup                      │
│   Conn.  Data    Valid.  Conv.   Comp.  House   Test                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Layer 1: Unit Tests

**File**: `tests/test_gap_filling_unit.py`

| Class                         | Functions Tested                   | Key Assertions                                       |
| ----------------------------- | ---------------------------------- | ---------------------------------------------------- |
| TestComputeVersionHash        | `_compute_version_hash()`          | Determinism, uniqueness, UInt64 range                |
| TestConvertApiDataToDataframe | `_convert_api_data_to_dataframe()` | Column order, data_source="rest_api", UTC timestamps |
| TestFillGapsFromApi           | `_fill_gaps_from_api()`            | Empty gaps skip API, multiple gaps accumulate rows   |

**File**: `tests/test_rest_client_unit.py`

| Class                    | Functions Tested            | Key Assertions                           |
| ------------------------ | --------------------------- | ---------------------------------------- |
| TestGetIntervalMs        | `get_interval_ms()`         | 16 timeframes, ValueError for invalid    |
| TestCalculateChunks      | `calculate_chunks()`        | Single chunk, multiple chunks, max limit |
| TestFetchKlinesWithRetry | `fetch_klines_with_retry()` | Success, rate limit, API error           |
| TestFetchGapData         | `fetch_gap_data()`          | Endpoint selection, boundary filtering   |

### Layer 2: Integration Tests

**File**: `tests/test_gap_filling_integration.py`

**Test Data**: Fixed date range 2024-11-01 to 2024-11-07

| Test                                         | Purpose                                   | Expected Duration |
| -------------------------------------------- | ----------------------------------------- | ----------------- |
| test_gap_filling_recent_days_uses_rest_api   | Verify REST API fills Vision lag gaps     | 10-30s            |
| test_rest_api_data_matches_clickhouse_schema | Validate 18-column schema compliance      | 5-10s             |
| test_deduplication_same_gap_data_twice       | Insert twice -> same row count with FINAL | 15-30s            |
| test_data_source_column_distinguishes        | `rest_api` vs `cloudfront` provenance     | 2-5s              |

### Layer 3: Production Pipeline

**File**: `scripts/validate_gap_filling.py`

7-Stage Pipeline:

| Stage | Name                  | Description                                      |
| ----- | --------------------- | ------------------------------------------------ |
| 1     | REST API Connectivity | HTTP HEAD to spot + futures endpoints            |
| 2     | Fresh Data Fetch      | GET yesterday's BTCUSDT 1h (24 rows x 2 formats) |
| 3     | Response Validation   | 12-element arrays, OHLCV constraints             |
| 4     | DataFrame Conversion  | 18-column schema, data_source="rest_api"         |
| 5     | Version Hash Compute  | SHA256 deterministic, 24 unique hashes           |
| 6     | ClickHouse Insert     | 48 rows total (24 spot + 24 futures)             |
| 7     | Deduplication Test    | Re-insert -> still 48 rows with FINAL            |

### JSON Artifact Schema

```json
{
  "validation_type": "gap_filling",
  "release_version": "v13.0.1",
  "status": "passed",
  "timestamp": "2025-11-25T14:30:00Z",
  "duration_ms": 5432,
  "stages": {
    "rest_api_connectivity": {
      "status": "passed",
      "spot_ok": true,
      "futures_ok": true
    },
    "fresh_data_fetch": {
      "status": "passed",
      "date": "2025-11-24",
      "spot_rows": 24,
      "futures_rows": 24
    },
    "response_validation": { "status": "passed" },
    "dataframe_conversion": { "status": "passed", "columns": 18 },
    "version_hash_compute": { "status": "passed", "unique_hashes": 48 },
    "clickhouse_insert": { "status": "passed", "rows_inserted": 48 },
    "deduplication_test": { "status": "passed", "rows_after_reinsert": 48 }
  }
}
```

---

## Risk Assessment

| Risk                  | Likelihood | Impact | Mitigation                       |
| --------------------- | ---------- | ------ | -------------------------------- |
| Network failure in CI | Medium     | Low    | Non-blocking + pytest.skip()     |
| API rate limiting     | Low        | Low    | Single request per test day      |
| Test data collision   | Low        | Low    | Different dates for spot/futures |

---

## Success Criteria

- [x] Unit tests pass in <5s with 90%+ coverage (44 tests in 0.29s)
- [x] Integration tests pass with real API/ClickHouse (9 tests in 3.49s)
- [x] Production pipeline validates fresh data bridge scenario (7-stage pipeline implemented)
- [x] Deduplication confirmed: re-insert produces same row count (test coverage)
- [x] `data_source="rest_api"` correctly tags gap-filled data (test coverage)
- [x] JSON artifacts exported and uploaded to GitHub Actions (workflow configured)
- [x] No regression in existing validations (ADR-0038) (403 unrelated tests pass)
