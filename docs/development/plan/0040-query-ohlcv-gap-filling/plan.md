# Plan 0040: query_ohlcv() Gap Filling Implementation

**ADR**: [ADR-0040](../../../architecture/decisions/0040-query-ohlcv-gap-filling.md)

**Status**: Complete

**Author**: Claude Code

**Last Updated**: 2025-11-25

---

## Overview

Implement gap filling in `query_ohlcv()` function using Binance REST API with tenacity retry logic.

### Goals

1. Fix TODO at query_api.py:210-215 (gap filling stub)
2. Create robust REST client with retry logic
3. Support chunking for large gaps (>1000 bars)
4. Maintain ReplacingMergeTree deduplication

### Non-Goals

- Phase 2 "ensure_fresh" parameter (deferred)
- Scheduled background ingestion (deferred)
- Rate limit optimization (acceptable 1s delay)

---

## Context

### Problem

Investigation revealed split implementation:

```text
query_ohlcv() workflow:
  1. Check ClickHouse   ✅
  2. Auto-ingest        ✅
  3. Query with FINAL   ✅
  4. Detect gaps        ✅
  5. Fill gaps          ❌ TODO (lines 210-215)
```

The TODO block currently logs a warning but doesn't fill gaps:

```python
if len(gaps) > 0:
    logger.info(f"{sym}: Detected {len(gaps)} gaps, filling via REST API")
    # TODO: Implement gap filling via REST API
    logger.warning(f"{sym}: Gap filling not yet implemented in v6.0.0")
```sql

### User Decisions

- **Scope**: Phase 1 only (fix query_ohlcv gap filling)
- **Retry**: Add tenacity (port patterns from data-source-manager)
- **Fresh default**: False (conservative, backward compatible)

### Reference Implementation

Battle-tested patterns from `../data-source-manager/utils/for_core/rest_client_utils.py`:

- tenacity: 3 attempts with 1s/2s/3s backoff
- HTTP 418/429: Rate limit detection with retry-after header
- Chunking: `calculate_chunks()` for >1000 bar ranges

---

## Task List

| #   | Task                                | Status | Notes                             |
| --- | ----------------------------------- | ------ | --------------------------------- |
| 1   | Create ADR-0040 and plan            | Done   | This document                     |
| 2   | Create rest_client.py with tenacity | Done   | Port from data-source-manager     |
| 3   | Wire gap filling into query_ohlcv() | Done   | Replace TODO stub                 |
| 4   | Add tenacity dependency             | Done   | pyproject.toml                    |
| 5   | Run build and validate              | Done   | Auto-fix errors (e2e_core import) |
| 6   | Update ADR status                   | Done   | Mark complete                     |

---

## Implementation Details

### Step 1: Create rest_client.py

**File**: `src/gapless_crypto_clickhouse/gap_filling/rest_client.py`

Components:

- `REST_CHUNK_SIZE = 1000` - Binance API limit
- `API_MAX_RETRIES = 3` - tenacity attempts
- `API_TIMEOUT = 30.0` - httpx timeout
- `RateLimitError` - Custom exception for 418/429
- `fetch_klines_with_retry()` - Decorated fetch function
- `calculate_chunks()` - Time range splitting

### Step 2: Wire into query_ohlcv()

**File**: `src/gapless_crypto_clickhouse/query_api.py`

Add helper function `_fill_gaps_from_api()`:

1. Create UniversalGapFiller instance
2. For each gap: fetch via REST API
3. Convert to DataFrame with \_version hash
4. Insert to ClickHouse
5. Re-query to include filled data

### Step 3: Add tenacity dependency

**File**: `pyproject.toml`

```toml
dependencies = [
    ...
    "tenacity>=8.0.0",  # Retry logic for REST API gap filling
]
```

---

## Risk Assessment

| Risk             | Likelihood | Impact | Mitigation                             |
| ---------------- | ---------- | ------ | -------------------------------------- |
| Rate limiting    | Medium     | Low    | Built-in 1s delay, few gaps typically  |
| Schema mismatch  | Low        | High   | Use same \_version hash as bulk loader |
| Network failures | Medium     | Low    | tenacity retry handles transient       |
| Duplicate rows   | Low        | Low    | ReplacingMergeTree deduplication       |

---

## Success Criteria

- [x] `query_ohlcv(fill_gaps=True)` actually fills gaps
- [x] tenacity retry handles HTTP 429, timeouts
- [x] Chunking works for gaps >1000 bars
- [ ] ReplacingMergeTree deduplication (no duplicates) - requires production test
- [x] No regression in `download()` and `fill_gaps()` (imports verified)

---

## Testing Plan

1. **Unit test**: rest_client.py retry logic with mocked responses
2. **Integration test**: Fill known gap via query_ohlcv()
3. **Dedup test**: Re-insert same data, verify row count unchanged
4. **Rate limit test**: Trigger HTTP 429, verify retry with backoff

---

## Future Enhancements (Deferred)

- **Phase 2**: Fresh Data Bridge (`ensure_fresh` parameter)
- **Scheduled ingestion**: Background job for proactive fresh data
