# ADR-0040: query_ohlcv() Gap Filling Implementation

**Status**: Accepted

**Date**: 2025-11-25

**Context**: [Plan 0040](../../development/plan/0040-query-ohlcv-gap-filling/plan.md)

## Context and Problem Statement

The `query_ohlcv()` function in v6.0.0 has a TODO at lines 210-215 where gap detection works but gap filling is not implemented. This creates a split implementation where:

| Workflow | Detection | Filling | Status |
|----------|-----------|---------|--------|
| `download()` (CSV) | Yes | Yes | Working |
| `fill_gaps()` (batch) | Yes | Yes | Working |
| **`query_ohlcv()` (ClickHouse)** | Yes | No | **Broken** |

Users calling `query_ohlcv(fill_gaps=True)` expect gaps to be filled, but they are only detected and logged as warnings.

## Decision Drivers

- **Correctness**: `fill_gaps=True` parameter should actually fill gaps
- **Availability**: REST API provides real-time data when Vision API lags (1-7 days)
- **Maintainability**: Reuse battle-tested patterns from data-source-manager
- **Observability**: Log gap filling operations with structured context

## Considered Options

1. **Inline implementation** - Add gap filling directly in query_api.py
2. **Modular REST client (selected)** - Create dedicated rest_client.py with tenacity retry
3. **Full data-source-manager integration** - Import entire module

## Decision Outcome

**Chosen option**: Modular REST client with tenacity retry

**Rationale**:
- Separates concerns (REST client vs query logic)
- Enables reuse of retry patterns from data-source-manager
- Maintains single responsibility principle
- tenacity is battle-tested for API retry logic

### Implementation

**New Module**: `src/gapless_crypto_clickhouse/gap_filling/rest_client.py`

Key components:
- `fetch_klines_with_retry()` - tenacity-decorated HTTP fetch
- `calculate_chunks()` - Split large time ranges into API-compatible chunks
- `RateLimitError` - Custom exception for HTTP 418/429 handling

**Modified Files**:
- `src/gapless_crypto_clickhouse/query_api.py` - Wire gap filling
- `pyproject.toml` - Add tenacity>=8.0.0 dependency

### Consequences

**Good**:
- `query_ohlcv(fill_gaps=True)` actually fills gaps
- Robust retry logic handles transient failures
- Chunking supports gaps >1000 bars

**Bad**:
- Additional dependency (tenacity)
- Network calls during query (acceptable for gap filling use case)

## Validation

- [x] `query_ohlcv(fill_gaps=True)` fills detected gaps
- [x] tenacity retries on HTTP 429/timeout
- [x] Chunking works for gaps >1000 bars
- [ ] ReplacingMergeTree deduplication works (no duplicates) - requires production test
- [x] No regression in existing workflows (imports verified)

---

## Implementation Status

**Date**: 2025-11-25
**Status**: Complete

**Files Created**:
- `src/gapless_crypto_clickhouse/gap_filling/rest_client.py` - tenacity retry + chunking

**Files Modified**:
- `src/gapless_crypto_clickhouse/query_api.py` - wired gap filling
- `src/gapless_crypto_clickhouse/validation/__init__.py` - fixed e2e_core import (ADR-0039 cleanup)
- `pyproject.toml` - added tenacity>=8.0.0

**Build**: Successful (v13.0.1)

## Links

- [Plan 0040](../../development/plan/0040-query-ohlcv-gap-filling/plan.md)
- [ADR-0023](0023-arrow-migration.md) - Arrow optimization (confirmed working)
- [ADR-0039](0039-validation-redundancy-cleanup.md) - e2e_core removal
