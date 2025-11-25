# Plan 0038: Real Binance Data Validation

**ADR**: [ADR-0038](../../../architecture/decisions/0038-real-binance-data-validation.md)

**Status**: Complete

**Author**: Claude Code

**Last Updated**: 2025-11-25

---

## Overview

Replace synthetic data validation with real Binance Vision data validation. Consolidate two legacy scripts into a single 9-stage validation pipeline integrated with Earthly.

### Goals

1. Eliminate synthetic data (`VALIDATION_TEST_BTCUSDT`, `E2E_TEST`)
2. Validate real Binance CDN → ClickHouse pipeline end-to-end
3. Test both futures (12-column with header) and spot (12-column no header) formats
4. Integrate validation into Earthly for CI/CD reproducibility

### Non-Goals

- Performance optimization (SLO: correctness over speed)
- Backward compatibility with legacy scripts
- Data cleanup (real data stays permanently)

---

## Context

### Current State

| Script | Data Type | Symbol | Issues |
|--------|-----------|--------|--------|
| `validate_clickhouse_cloud.py` | Synthetic | `VALIDATION_TEST_BTCUSDT` | Fake OHLCV, fake hashes |
| `validate_e2e_simple.py` | Synthetic | `E2E_TEST` | 1 fake row, no format validation |

### Problem

Synthetic validation cannot detect:
- CDN format changes (header presence, column count)
- Transformation bugs (CSV → DataFrame → ClickHouse)
- Real-world deduplication edge cases

### Solution

Download real Binance Vision data (BTCUSDT) and validate the complete pipeline.

**Important**: Futures and spot use different test dates to avoid ORDER BY key collision. The schema ORDER BY is `(symbol, timeframe, toStartOfHour(timestamp), timestamp)` - `instrument_type` is NOT included. Using the same timestamp for both would cause ReplacingMergeTree to treat them as duplicates.

---

## Design

### Test Data Sources

| Format | Date | URL | Expected |
|--------|------|-----|----------|
| Futures | 2024-01-01 | `https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-01.zip` | 24 rows, 12 cols, header |
| Spot | 2024-01-02 | `https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-02.zip` | 24 rows, 12 cols, no header |

### 9-Stage Validation Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: CDN Download                                       │
│ ├── Futures: HTTP 200, ZIP > 0 bytes                       │
│ └── Spot: HTTP 200, ZIP > 0 bytes                          │
├─────────────────────────────────────────────────────────────┤
│ Stage 2: ZIP Extract                                        │
│ ├── Futures: Single CSV with header                        │
│ └── Spot: Single CSV without header                        │
├─────────────────────────────────────────────────────────────┤
│ Stage 3: CSV Parse + Format Detection                       │
│ ├── Futures: 24 rows × 12 columns (drop 'ignore')          │
│ └── Spot: 24 rows × 12 columns (drop 'ignore', add names)  │
├─────────────────────────────────────────────────────────────┤
│ Stage 4: DataFrame Validation                               │
│ ├── OHLC: high >= low, high >= open/close                  │
│ ├── Volume: taker_buy <= total, all >= 0                   │
│ └── Timestamp: chronological, 1h intervals                 │
├─────────────────────────────────────────────────────────────┤
│ Stage 5: _version Hash Computation                          │
│ ├── SHA256(timestamp|OHLCV|symbol|timeframe|instrument_type)│
│ └── Verify 24 unique deterministic hashes per format       │
├─────────────────────────────────────────────────────────────┤
│ Stage 6: ClickHouse Insert                                  │
│ ├── Futures: 24 rows (instrument_type='futures-um')        │
│ └── Spot: 24 rows (instrument_type='spot')                 │
├─────────────────────────────────────────────────────────────┤
│ Stage 7: Query FINAL                                        │
│ ├── COUNT(*) WHERE instrument_type='futures-um' → 24       │
│ └── COUNT(*) WHERE instrument_type='spot' → 24             │
├─────────────────────────────────────────────────────────────┤
│ Stage 8: Deduplication Test                                 │
│ ├── Re-insert same data                                    │
│ └── COUNT(*) still = 24 (not 48) per instrument_type       │
├─────────────────────────────────────────────────────────────┤
│ Stage 9: Schema Compliance                                  │
│ ├── 18 columns present                                     │
│ ├── DateTime64(6) precision                                │
│ └── ORDER BY (symbol, timeframe, toStartOfHour, timestamp) │
└─────────────────────────────────────────────────────────────┘
```

### Earthly Target

```earthly
binance-real-data-check:
    FROM +validation-base
    ARG RELEASE_VERSION
    ARG GIT_COMMIT=""

    COPY scripts/validate_binance_real_data.py .

    RUN --secret CLICKHOUSE_HOST \
        --secret CLICKHOUSE_PORT \
        --secret CLICKHOUSE_USER \
        --secret CLICKHOUSE_PASSWORD \
        python validate_binance_real_data.py \
            --release-version "$RELEASE_VERSION" \
            --git-commit "$GIT_COMMIT" \
            --output binance-validation-result.json

    SAVE ARTIFACT binance-validation-result.json AS LOCAL ./artifacts/
```

---

## Task List

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1 | Create ADR-0038 and plan structure | ✅ Done | |
| 2 | Create `validate_binance_real_data.py` | ✅ Done | 9-stage pipeline |
| 3 | Delete legacy scripts | ✅ Done | `validate_clickhouse_cloud.py`, `validate_e2e_simple.py` |
| 4 | Add Earthly target | ✅ Done | `+binance-real-data-check` |
| 5 | Update `production-validation.yml` | ✅ Done | Replace synthetic jobs |
| 6 | Update `release-validation.yml` | ✅ Done | Add binance validation |
| 7 | Run local validation | ✅ Done | All 9 stages passed (1404ms) |
| 8 | Commit and push | ⏳ Pending | `feat(validation):` |
| 9 | Semantic release | ⏳ Pending | Creates v12.1.0 |
| 10 | PyPI publish | ⏳ Pending | `pypi-doppler` skill |

---

## Files Changed

### Create
- `scripts/validate_binance_real_data.py`

### Modify
- `Earthfile` - Add `+binance-real-data-check`, update `validation-base`
- `.github/workflows/production-validation.yml` - Replace synthetic jobs
- `.github/workflows/release-validation.yml` - Add binance validation

### Delete
- `scripts/validate_clickhouse_cloud.py`
- `scripts/validate_e2e_simple.py`

---

## Success Criteria

| Criterion | Metric | Actual |
|-----------|--------|--------|
| CDN Download | HTTP 200 for both futures and spot | ✅ Passed |
| Format Detection | Futures: 12 cols, Spot: 12 cols | ✅ Passed |
| OHLC Validation | All constraints pass | ✅ Passed |
| Insert Success | 48 rows total (24 + 24) | ✅ Passed |
| Query FINAL | 24 rows per date (different dates) | ✅ Passed |
| Deduplication | Re-insert doesn't double count | ✅ Passed |
| Schema Match | 18 columns, symbol-first ORDER BY | ✅ Passed |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| CDN unavailable | Non-blocking (exit 0), Pushover alert |
| Data already exists | Idempotent via ReplacingMergeTree |
| Schema drift | Stage 9 validates ORDER BY |

---

## Timeline

| Phase | Estimate |
|-------|----------|
| Script creation | 15 min |
| Legacy deletion | 1 min |
| Earthly integration | 5 min |
| Workflow updates | 5 min |
| Testing + commit | 5 min |
| Release + publish | 5 min |
| **Total** | **~35 min** |
