# Multi-Symbol Batch Download API

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Terry Li
**Related ADRs**: None
**Related Plans**: [0020-multi-symbol-batch-api](../../development/plan/0020-multi-symbol-batch-api/plan.md)

## Context and Problem Statement

Alpha Forge AI agents identified a HIGH PRIORITY improvement: Multi-symbol batch API.

**Current State**: Users must loop over symbols sequentially

````python
# Current approach - slow for multiple symbols
dataframes = {}
for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
    dataframes[symbol] = gcc.download(symbol, "1h", start_date="2024-01-01")
# → Sequential execution, no concurrency
```python

**Alpha Forge Feedback**: "Need `fetch_data(symbols=[...])` for 10-20x faster fetching"

**Use Case**: Cross-sectional analysis strategies require downloading 20-50 symbols simultaneously.

**Question**: Should we add a multi-symbol batch download API with concurrent execution?

## Decision Drivers

- **Performance**: Sequential loops are slow for multiple symbols
- **User Experience**: Batch API simplifies common use case
- **Alpha Forge Integration**: High-value improvement (Grade: A)
- **Implementation Effort**: Low (50 lines with `concurrent.futures`)
- **SLO Focus**: Availability (faster operations), Maintainability (cleaner user code)

## Considered Options

1. **Add `download_multiple()` function** with concurrent execution
2. **Add `symbols` parameter to existing `download()`** (breaking change)
3. **Keep current API** (users handle concurrency)
4. **Add async API** (`async def download_async()`)

## Decision Outcome

**Chosen option**: Add `download_multiple()` function with concurrent execution

**Rationale**:

### Why Separate Function

**API Design**:

- **Backward Compatibility**: Existing `download()` unchanged
- **Type Safety**: Different return type (`dict[str, DataFrame]` vs `DataFrame`)
- **Clear Intent**: Function name signals batch operation
- **Optional**: Users can continue using `download()` if preferred

**Return Type**:

```python
def download_multiple(
    symbols: list[str],
    timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_workers: int = 5,
    **kwargs
) -> dict[str, pd.DataFrame]:
    """Download historical data for multiple symbols concurrently.

    Returns:
        dict mapping symbol → DataFrame
        Example: {"BTCUSDT": df1, "ETHUSDT": df2, ...}
    """
```python

### Why Concurrent Execution

**Performance Benefit**:

- **Network-bound**: Data fetching dominated by network I/O (not CPU)
- **ThreadPoolExecutor**: Python threads ideal for I/O-bound operations
- **Expected Speedup**: 10-20x for 20 symbols (parallel download from CDN)
- **Resource Usage**: Reasonable (max 5 concurrent by default)

**Implementation Strategy**:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_multiple(symbols, timeframe, max_workers=5, **kwargs):
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_symbol = {
            executor.submit(download, symbol, timeframe, **kwargs): symbol
            for symbol in symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                errors[symbol] = str(e)

    # Raise if all failed, otherwise return partial results
    if not results and errors:
        raise ValueError(f"All {len(symbols)} symbols failed: {errors}")

    return results
```python

**Error Handling Strategy**:

- **Partial Success**: Return successful downloads, log failures
- **Complete Failure**: Raise ValueError with all error details
- **Individual Errors**: Include in returned dict as `{symbol: error_msg}`

### Why Not Other Options

**Option 2: Add `symbols` parameter to `download()`**:

- ❌ Breaking change (different return type based on parameter)
- ❌ Type safety issues (Union[DataFrame, dict[str, DataFrame]])
- ❌ Confusing API (one function, two behaviors)

**Option 3: Keep current API**:

- ❌ Users reinvent concurrency (error-prone)
- ❌ Misses high-value improvement opportunity
- ❌ Alpha Forge explicitly requested this feature

**Option 4: Add async API**:

- ❌ Overkill (threading sufficient for I/O-bound)
- ❌ Requires async ecosystem adoption
- ❌ More complex for users (async/await syntax)

## Consequences

### Positive

- ✅ **10-20x Performance**: Parallel downloads from CDN
- ✅ **Simplified User Code**: No manual concurrency management
- ✅ **Backward Compatible**: Existing code unchanged
- ✅ **Type Safe**: Clear return type annotation
- ✅ **Error Handling**: Partial success supported

### Negative

- ⚠️ **API Surface Growth**: One more function to document/maintain
- ⚠️ **Resource Usage**: max_workers concurrent connections (configurable)
- ⚠️ **Complexity**: Threading adds some implementation complexity

### Neutral

- ThreadPoolExecutor is standard library (no new dependencies)
- max_workers default (5) chosen conservatively
- Users can still use sequential `download()` if preferred

## Implementation Plan

### Function Signature

```python
def download_multiple(
    symbols: list[str],
    timeframe: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    max_workers: int = 5,
    raise_on_partial_failure: bool = False,
    **kwargs
) -> dict[str, pd.DataFrame]:
    """Download historical data for multiple symbols concurrently.

    Args:
        symbols: List of trading pair symbols (e.g., ["BTCUSDT", "ETHUSDT"])
        timeframe: Candle interval (e.g., "1h", "4h", "1d")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Maximum bars per symbol
        max_workers: Maximum concurrent downloads (default: 5)
        raise_on_partial_failure: Raise error if any symbol fails (default: False)
        **kwargs: Additional parameters passed to download()

    Returns:
        dict[str, pd.DataFrame]: Mapping of symbol → DataFrame

    Raises:
        ValueError: If all symbols fail, or if raise_on_partial_failure=True and any fail

    Example:
        >>> results = gcc.download_multiple(
        ...     symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01",
        ...     end_date="2024-06-30"
        ... )
        >>> len(results)
        3
        >>> results["BTCUSDT"].shape
        (4344, 11)
    """
```text

### Error Handling

**Partial Success Strategy**:

```python
# Example: 3 symbols, 1 fails
results = download_multiple(["BTCUSDT", "ETHUSDT", "INVALID"])
# → Returns: {"BTCUSDT": df1, "ETHUSDT": df2}
# → Logs warning: "Failed to download INVALID: Invalid symbol..."

# Strict mode (fail fast)
results = download_multiple(
    ["BTCUSDT", "INVALID"],
    raise_on_partial_failure=True
)
# → Raises ValueError immediately
```text

### Integration

**File**: `src/gapless_crypto_clickhouse/api.py`

**Location**: After existing `download()` function

**Export**: Add to `__init__.py`:

```python
from gapless_crypto_clickhouse.api import download_multiple
__all__ = [..., "download_multiple"]
```bash

## Validation Criteria

### Acceptance Criteria

- [ ] `download_multiple()` function implemented in `api.py`
- [ ] Concurrent execution with ThreadPoolExecutor
- [ ] Partial success error handling
- [ ] Type hints and docstring complete
- [ ] Exported in `__init__.py`
- [ ] Test suite covers:
  - Successful concurrent download (5 symbols)
  - Partial failure handling (some symbols fail)
  - Complete failure handling (all symbols fail)
  - max_workers parameter validation
  - raise_on_partial_failure parameter
- [ ] Performance test validates speedup (5-10x for 5 symbols)

### SLO Impact

- **Availability**: Improved (faster multi-symbol operations)
- **Correctness**: No change (uses existing `download()` internally)
- **Observability**: Improved (batch operation visibility)
- **Maintainability**: Slight increase (one more function to maintain)

## Migration Path

**For existing users**:

- No migration required (new function is additive)
- Can adopt incrementally (replace loops with `download_multiple()`)
- Backward compatible (existing `download()` unchanged)

**For Alpha Forge integration**:

```python
# Before (sequential)
results = {}
for symbol in symbols:
    results[symbol] = gcc.download(symbol, "1h", start_date="2024-01-01")
# → Slow (20 symbols = 20x sequential time)

# After (concurrent)
results = gcc.download_multiple(
    symbols=symbols,
    timeframe="1h",
    start_date="2024-01-01"
)
# → Fast (20 symbols ≈ 1-2x sequential time with concurrency)
````

## References

- Alpha Forge Feedback: "Need multi-symbol batch API for 10-20x speedup"
- Python ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html
- Binance Public Data CloudFront CDN: Supports concurrent connections

## Compliance

- **OSS Libraries**: Uses standard library `concurrent.futures` (no new deps)
- **Error Handling**: Raise+propagate pattern (ValueError for failures)
- **Backward Compatibility**: Full backward compatibility (additive change)
- **Auto-Validation**: Test suite validates concurrent execution

## Future Work

- **Progress Callbacks**: Add callback parameter for download progress
- **Async API**: Consider `async def download_multiple_async()` for async workflows
- **Batch Optimizations**: Optimize ClickHouse bulk inserts for multi-symbol

---

**ADR-0020** | Multi-Symbol Batch API | Accepted | 2025-11-19
