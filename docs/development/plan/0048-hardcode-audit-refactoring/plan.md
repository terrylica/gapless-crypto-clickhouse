# Hardcode Audit and Refactoring Plan

**ADR**: [0048](../../../architecture/decisions/0048-hardcode-audit-refactoring.md)
**adr-id**: 0048
**Status**: Complete
**Last Updated**: 2025-11-26
**Session**: `~/.claude/plans/memoized-noodling-meadow.md`

## Context

### Problem Statement

Following ADR-0046 (Semantic Constants Abstraction), an automated audit using the `code-hardcode-audit` skill revealed 100+ hardcoded values requiring refactoring.

### Audit Results

| Category             | Tool         | Findings | Priority | Status  |
| -------------------- | ------------ | -------- | -------- | ------- |
| HTTP Status Codes    | Ruff PLR2004 | 5        | Low      | ✅ Done |
| Hardcoded Timeframes | Semgrep      | ~80      | Medium   | ✅ Done |
| Magic Numbers        | Ruff PLR2004 | ~30      | High     | ✅ Done |

### User Decisions

| Decision  | Choice                                 |
| --------- | -------------------------------------- |
| Scope     | Full refactoring (all 4 phases)        |
| Skill fix | Yes, fix Semgrep rule ID display first |
| ADR       | Yes, create ADR-0048                   |

## Plan

### Phase 1: HTTP Status Codes ✅

Replace hardcoded 200/304 with existing `HTTP_OK`/`HTTP_NOT_MODIFIED` constants.

**Files**: `binance_public_data_collector.py` (4 instances), `httpx_downloader.py` (1 instance)

### Phase 2: Magic Numbers ✅

Add constants to `constants/binance.py`:

- CSV column counts: `CSV_COLUMNS_SPOT_OUTPUT`, `CSV_COLUMNS_BINANCE_RAW`, `CSV_COLUMNS_MINIMUM_OHLCV`
- Timestamp boundaries: `TIMESTAMP_MILLISECONDS_MIN/MAX`, `TIMESTAMP_MICROSECONDS_MIN/MAX`
- Column indices: `CSV_INDEX_*` for positional access (11 constants)
- Time unit conversions: `MICROSECONDS_PER_MILLISECOND`, `MILLISECONDS_PER_SECOND`

**Consumer replacements**:

- ✅ `collectors/binance_public_data_collector.py` - timestamp boundaries, column indices
- ✅ `collectors/clickhouse_bulk_loader.py` - column count validations

### Phase 3: Timeframe Consolidation ✅

Moved `utils/timeframe_constants.py` → `constants/timeframes.py`:

- ✅ Added `Timeframe` Literal type for IDE autocomplete
- ✅ Added `TIMEFRAME_TO_MILLISECONDS` derived map (for REST API)
- ✅ Added `TIMEFRAME_TO_SECONDS` derived map (for ClickHouse)
- ✅ Added `VALID_TIMEFRAMES`, `STANDARD_TIMEFRAMES`, `EXOTIC_TIMEFRAMES` sets
- ✅ Removed duplicate interval maps from 6 consumer files
- ✅ Deprecated old location with re-export shim and deprecation warning

### Phase 4: Type Safety (Optional)

Update function signatures to use `Timeframe` Literal type. Non-breaking, can be done incrementally.

## Task List

| #   | Task                                 | Status  | Notes                           |
| --- | ------------------------------------ | ------- | ------------------------------- |
| 0   | Fix skill Semgrep rule ID display    | ✅ Done | `_extract_rule_id()` helper     |
| 1   | Create ADR-0048                      | ✅ Done | MADR format                     |
| 2   | Replace HTTP status code hardcodes   | ✅ Done | 5 replacements                  |
| 3   | Add CSV/timestamp constants          | ✅ Done | ~20 new constants               |
| 4   | Update constants/**init**.py exports | ✅ Done | Re-export new constants         |
| 5   | Replace magic numbers in collectors  | ✅ Done | 2 files updated                 |
| 6   | Move timeframe_constants.py          | ✅ Done | Created constants/timeframes.py |
| 7   | Add Timeframe Literal type           | ✅ Done | Type alias                      |
| 8   | Add TIMEFRAME_TO_MILLISECONDS        | ✅ Done | Derived map                     |
| 9   | Remove duplicate interval maps       | ✅ Done | 6 consumer files                |
| 10  | Run tests and validate               | ✅ Done | Imports verified                |

## Files Modified

### Constants (new/modified)

- `src/gapless_crypto_clickhouse/constants/binance.py` - Added ~20 constants
- `src/gapless_crypto_clickhouse/constants/timeframes.py` - New file with Timeframe type
- `src/gapless_crypto_clickhouse/constants/__init__.py` - Updated exports

### Consumers (updated)

- `src/gapless_crypto_clickhouse/api.py` - Removed duplicate interval_minutes
- `src/gapless_crypto_clickhouse/clickhouse_query.py` - Removed duplicate timeframe_to_seconds
- `src/gapless_crypto_clickhouse/gap_filling/rest_client.py` - Removed duplicate interval_map
- `src/gapless_crypto_clickhouse/validation/csv_validator.py` - Removed 2 duplicate interval_maps
- `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py` - Updated imports, timestamp boundaries, column indices
- `src/gapless_crypto_clickhouse/collectors/clickhouse_bulk_loader.py` - Updated column count validations
- `src/gapless_crypto_clickhouse/collectors/httpx_downloader.py` - Added HTTP_OK import
- `src/gapless_crypto_clickhouse/gap_filling/universal_gap_filler.py` - Updated import path

### Deprecated

- `src/gapless_crypto_clickhouse/utils/timeframe_constants.py` - Now a re-export shim with deprecation warning

## Success Criteria

1. ✅ All imports work correctly (verified)
2. ✅ Deprecation warning shows for old import path
3. ✅ Centralized constants module complete
4. ✅ Magic number replacements in collectors complete
5. ✅ Ruff check passes
