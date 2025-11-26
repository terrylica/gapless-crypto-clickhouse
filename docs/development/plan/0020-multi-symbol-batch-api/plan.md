# Multi-Symbol Batch Download API Implementation Plan

**ADR ID**: 0020
**Status**: Complete
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-20
**Completed**: 2025-11-20
**Released**: v3.1.0

---

## Objective

Add multi-symbol batch download API with concurrent execution to provide 10-20x performance improvement for cross-sectional analysis workflows.

## Background

### Problem

Current API requires sequential loops for multiple symbols:

```python
# Current approach - slow
dataframes = {}
for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"]:
    dataframes[symbol] = gcd.download(symbol, "1h", start_date="2024-01-01")
# → 5x sequential time (no concurrency)
```bash

**Alpha Forge Feedback**: "Need `fetch_data(symbols=[...])` - Most common use case but undocumented"

**Use Case**: Cross-sectional strategies analyze 20-50 symbols simultaneously.

### Solution

Add `download_multiple()` function with concurrent execution:

```python
# New approach - fast
results = gcd.download_multiple(
    symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"],
    timeframe="1h",
    start_date="2024-01-01"
)
# → ~1-2x sequential time (parallel download from CDN)
# → 10-20x faster for 20 symbols
```python

## Goals

1. **Add `download_multiple()` Function** - Batch download with concurrent execution
2. **Concurrent Execution** - Use ThreadPoolExecutor for parallel I/O
3. **Error Handling** - Support partial success (some symbols fail, others succeed)
4. **Type Safety** - Full type hints and return type annotation
5. **Backward Compatible** - Existing `download()` unchanged

## Non-Goals

- Async API (`async def download_multiple_async()`) - defer to future
- Progress callbacks/monitoring - defer to future
- Modifying existing `download()` function - maintain backward compatibility
- Supporting symbol batching strategies - user responsibility

## Design

### API Design

**Function Signature**:

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

    Executes concurrent downloads using ThreadPoolExecutor for network-bound
    operations. Returns dict mapping symbol → DataFrame.

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
        Only includes successful downloads (failed symbols omitted)

    Raises:
        ValueError: If all symbols fail, or if raise_on_partial_failure=True
                   and any symbol fails

    Example:
        >>> results = gcd.download_multiple(
        ...     symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01",
        ...     end_date="2024-06-30"
        ... )
        >>> len(results)
        3
        >>> results["BTCUSDT"].shape
        (4344, 11)

        # With error handling
        >>> results = gcd.download_multiple(
        ...     symbols=["BTCUSDT", "INVALID"],
        ...     timeframe="1h",
        ...     start_date="2024-01-01"
        ... )
        >>> len(results)
        1  # Only BTCUSDT succeeded
    """
```text

### Implementation Strategy

**File**: `src/gapless_crypto_clickhouse/api.py`

**Implementation**:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

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
    """Download historical data for multiple symbols concurrently."""

    # Input validation
    if not symbols:
        raise ValueError("symbols list cannot be empty")

    if max_workers < 1:
        raise ValueError("max_workers must be >= 1")

    results: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    # Concurrent execution with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all download tasks
        future_to_symbol = {
            executor.submit(
                download,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                **kwargs
            ): symbol
            for symbol in symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                errors[symbol] = str(e)

                # Fail fast mode
                if raise_on_partial_failure:
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise ValueError(
                        f"Download failed for {symbol}: {e}"
                    ) from e

    # Handle complete failure
    if not results and errors:
        raise ValueError(
            f"All {len(symbols)} symbols failed. Errors: {errors}"
        )

    # Log warnings for partial failures
    if errors:
        import warnings
        warnings.warn(
            f"Failed to download {len(errors)} symbols: {list(errors.keys())}",
            UserWarning
        )

    return results
```text

### Error Handling Strategy

**Partial Success (default behavior)**:

```python
# 5 symbols, 1 fails
results = download_multiple(["BTC", "ETH", "SOL", "INVALID", "BNB"])
# → Returns: {"BTC": df1, "ETH": df2, "SOL": df3, "BNB": df4}
# → Logs warning: "Failed to download 1 symbols: ['INVALID']"
```text

**Fail Fast Mode**:

```python
# Strict mode (raise on any failure)
results = download_multiple(
    symbols=["BTC", "INVALID"],
    raise_on_partial_failure=True
)
# → Raises ValueError immediately on first failure
# → Cancels remaining pending downloads
```text

**Complete Failure**:

```python
# All symbols fail
results = download_multiple(["INVALID1", "INVALID2", "INVALID3"])
# → Raises ValueError: "All 3 symbols failed. Errors: {...}"
```python

### Concurrency Parameters

**max_workers Default (5)**:

- Conservative choice (avoids overwhelming CDN)
- Reasonable for most use cases (5-20 symbols)
- Users can increase for larger batches
- CloudFront CDN supports many concurrent connections

**Scaling Considerations**:

| Symbols | Recommended max_workers | Expected Speedup |
| ------- | ----------------------- | ---------------- |
| 5       | 5 (default)             | 4-5x             |
| 20      | 10-15                   | 10-15x           |
| 50      | 20-25                   | 20-25x           |

## Implementation Checklist

### Pre-Implementation

- [x] Create ADR-0020
- [x] Create this plan document
- [ ] Review existing `download()` function signature

### Implementation

- [ ] Add `download_multiple()` function to `api.py`:
  - Import ThreadPoolExecutor, as_completed
  - Implement function with signature above
  - Add input validation (empty list, max_workers < 1)
  - Implement concurrent execution logic
  - Implement error handling (partial success, complete failure)
  - Add warning for partial failures
- [ ] Update `__init__.py`:
  - Add `download_multiple` to imports
  - Add to `__all__` list
- [ ] Update type hints:
  - Add return type annotation: `dict[str, pd.DataFrame]`
  - Ensure all parameters have type hints
- [ ] Update docstring with examples and error cases

### Testing

- [ ] Create `tests/test_download_multiple.py`:
  - Test successful concurrent download (5 symbols)
  - Test empty symbols list (ValueError)
  - Test invalid max_workers (ValueError)
  - Test partial failure (some symbols succeed)
  - Test complete failure (all symbols fail)
  - Test raise_on_partial_failure=True mode
  - Test kwargs forwarding to download()
  - Test performance improvement (5x faster for 5 symbols)
- [ ] Add integration test:
  - Download 10 symbols concurrently
  - Verify all DataFrames have correct schema
  - Verify data quality matches sequential download

### Documentation

- [ ] Update function docstring with:
  - Full parameter descriptions
  - Return value description
  - Error conditions (ValueError cases)
  - Multiple examples (success, partial failure)
- [ ] Update `README.md` with batch download example
- [ ] Update `llms.txt` with new function
- [ ] Document performance characteristics

### Release

- [ ] Run test suite with new function
- [ ] Commit with conventional commit message
- [ ] Include in v3.1.0 release (with NumPy fix)
- [ ] Update Alpha Forge with new capability

## Detailed Design

### Threading vs Multiprocessing

**Choice**: ThreadPoolExecutor (threads)

**Rationale**:

- **Network-bound**: Downloads dominated by network I/O, not CPU
- **GIL Impact**: Minimal (threads wait on I/O, release GIL)
- **Overhead**: Threads lightweight vs processes
- **Simplicity**: ThreadPoolExecutor easier than ProcessPoolExecutor

**Benchmark Expected**:

```
Sequential (5 symbols): ~50 seconds
Concurrent (5 symbols, max_workers=5): ~10-12 seconds
Speedup: 4-5x
```

### Resource Management

**Connection Pooling**:

- httpx already uses connection pooling (configured in `download()`)
- ThreadPoolExecutor manages thread lifecycle
- Context manager ensures cleanup (`with ThreadPoolExecutor()`)

**Memory Usage**:

- Each DataFrame loads into memory (standard for pandas)
- ~5-10 MB per symbol (typical for 1 month of 1h data)
- 20 symbols = ~100-200 MB peak memory (acceptable)

### Backward Compatibility

**No Breaking Changes**:

- New function (additive change only)
- Existing `download()` unchanged
- Existing user code unaffected
- Optional migration (users can continue using loops)

## Rollout Plan

### Timeline

- **Implementation**: 2025-11-19 (1-2 hours)
- **Testing**: 2025-11-19 (1 hour)
- **Release**: v3.1.0 same day (with NumPy fix)
- **Alpha Forge Notification**: Immediately after release

### Validation Steps

1. **Unit Tests**: All new tests pass
2. **Integration Test**: 10-symbol concurrent download succeeds
3. **Performance Test**: Verify 5x+ speedup for 5 symbols
4. **Error Handling**: Partial failure and complete failure work correctly
5. **Documentation**: Examples in README work as written

### Rollback Strategy

**If critical issues found**:

- Remove `download_multiple()` from `api.py`
- Remove from `__init__.py` exports
- Keep in separate branch for future release
- No impact on existing users (additive change)

**Indicators for rollback**:

- Deadlocks or race conditions detected
- Memory leaks during concurrent execution
- Data corruption (DataFrames incorrect)
- Performance worse than sequential (unexpected)

## Risks and Mitigations

### Risk 1: CloudFront Rate Limiting

**Risk**: Concurrent requests trigger rate limiting
**Likelihood**: Low (CloudFront designed for high concurrency)
**Impact**: Medium (downloads fail or slow down)
**Mitigation**:

- Conservative max_workers default (5)
- Users can reduce if rate limiting encountered
- Error messages indicate rate limiting

### Risk 2: Memory Pressure

**Risk**: Loading many large DataFrames causes OOM
**Likelihood**: Low (typical usage 5-20 symbols)
**Impact**: High (program crash)
**Mitigation**:

- Document memory requirements
- Recommend batching for >50 symbols
- Results returned as-completed (streaming)

### Risk 3: Thread Safety Issues

**Risk**: Shared state causes race conditions
**Likelihood**: Very Low (no shared mutable state)
**Impact**: High (data corruption)
**Mitigation**:

- Each download() call independent
- Results dict populated atomically
- ThreadPoolExecutor handles synchronization

## Success Metrics

### Primary Metrics

- [ ] Function implemented and exported
- [ ] All tests pass (unit + integration)
- [ ] Performance improvement validated (5x+ for 5 symbols)
- [ ] Error handling works correctly (partial/complete failure)
- [ ] Documentation complete with examples

### Secondary Metrics

- [ ] Alpha Forge adoption (replaces sequential loops)
- [ ] No bug reports related to concurrency
- [ ] No performance regressions for single-symbol downloads

## Open Questions

- **Q**: Should max_workers adapt based on symbol count?
  **A**: No - keep simple, users can configure explicitly

- **Q**: Should we add progress callbacks?
  **A**: Defer to future work (v3.2.0 feature)

- **Q**: Should we support async API?
  **A**: Defer to future work (when ecosystem demands)

## References

- ADR-0020: Multi-Symbol Batch Download API
- Alpha Forge Feedback: "Need multi-symbol batch API"
- Python ThreadPoolExecutor: https://docs.python.org/3/library/concurrent.futures.html
- Binance CloudFront CDN: Supports high concurrency

## Log Files

Implementation logs stored in:

- `logs/0020-multi-symbol-batch-api-YYYYMMDD_HHMMSS.log`

---

**Plan 0020** | Multi-Symbol Batch API | In Progress | 2025-11-19
