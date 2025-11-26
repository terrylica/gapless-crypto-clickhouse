# Upfront Input Validation with Better Error Messages

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Terry Li
**Related ADRs**: None
**Related Plans**: [0018-upfront-input-validation](../../development/plan/0018-upfront-input-validation/plan.md)

## Context and Problem Statement

Current API performs minimal input validation before making expensive network/database operations.

**Alpha Forge Feedback**: "Error messages are unclear - validate inputs upfront with actionable feedback"

**Current Behavior**:

````python
# Invalid symbol - fails during data collection
df = gcc.download("INVALIDPAIR", "1h")  # Network request → 404 → unclear error

# Invalid timeframe - fails during collection
df = gcc.download("BTCUSDT", "3h")  # Network request → empty data → confusing

# Invalid date format - fails during collection
df = gcc.download("BTCUSDT", "1h", start="2024-13-01")  # Proceeds → fails later
```bash

**Issues**:

- Errors occur during network operations (slow feedback)
- Error messages don't guide users to correct usage
- No validation of known-good symbols and timeframes

**Question**: Should we add upfront input validation with better error messages?

## Decision Drivers

- **Fast Feedback**: Catch errors before expensive operations
- **Actionable Errors**: Error messages should guide users to correct usage
- **Alpha Forge Integration**: Clearer errors improve developer experience
- **Correctness SLO**: Early validation prevents invalid states

## Considered Options

1. **Add upfront validation** with symbol/timeframe checks
2. **Keep current behavior** (validate during collection)
3. **Add validation + suggestions** (recommend correct symbols/timeframes)
4. **Strict mode only** (optional validation for power users)

## Decision Outcome

**Chosen option**: Add upfront validation with actionable error messages

**Rationale**:

### Why Upfront Validation

**Fast Failure**:

- Validate symbols against `known_symbols` before network requests
- Validate timeframes against `available_timeframes` immediately
- Validate date formats before collection starts
- Reduces wasted time on invalid operations

**Better Error Messages**:

```python
# Before (unclear error after network delay)
df = gcc.download("BTCUSD", "1h")  # → "No data found" (after 5s network delay)

# After (immediate validation with actionable feedback)
df = gcc.download("BTCUSD", "1h")
# → ValueError: Invalid symbol 'BTCUSD'. Did you mean 'BTCUSDT'?
#    Supported symbols: BTCUSDT, ETHUSDT, BNBUSDT, ... (see get_supported_symbols())
```text

**Implementation Strategy**:

```python
def download(...):
    # Upfront validation
    _validate_symbol(symbol)  # Check against known_symbols
    _validate_timeframe(period)  # Check against available_timeframes
    _validate_date_format(start, end)  # YYYY-MM-DD format check

    # Continue with existing logic
    ...
```text

### Validation Functions

**Symbol Validation**:

```python
def _validate_symbol(symbol: str) -> None:
    """Validate symbol against known symbols.

    Raises:
        ValueError: If symbol is invalid with suggestions
    """
    from gapless_crypto_clickhouse import get_supported_symbols

    supported = get_supported_symbols()

    if symbol not in supported:
        # Find close matches (fuzzy matching)
        close_matches = [s for s in supported if s.startswith(symbol[:3])]

        if close_matches:
            raise ValueError(
                f"Invalid symbol '{symbol}'. Did you mean {close_matches[0]}? "
                f"Supported symbols: {', '.join(supported[:5])}, ... "
                f"(see get_supported_symbols() for full list)"
            )
        else:
            raise ValueError(
                f"Invalid symbol '{symbol}'. "
                f"Supported symbols: {', '.join(supported[:10])}, ... "
                f"(see get_supported_symbols() for full list)"
            )
```text

**Timeframe Validation**:

```python
def _validate_timeframe_value(timeframe: str) -> None:
    """Validate timeframe against available timeframes.

    Raises:
        ValueError: If timeframe is invalid with suggestions
    """
    from gapless_crypto_clickhouse import get_supported_timeframes

    supported = get_supported_timeframes()

    if timeframe not in supported:
        raise ValueError(
            f"Invalid timeframe '{timeframe}'. "
            f"Supported timeframes: {', '.join(supported)} "
            f"(see get_supported_timeframes())"
        )
```text

**Date Format Validation**:

```python
def _validate_date_format(date_str: Optional[str], param_name: str) -> None:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate
        param_name: Parameter name for error message

    Raises:
        ValueError: If date format is invalid
    """
    if date_str is None:
        return

    import re
    from datetime import datetime

    # Check format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(
            f"Invalid {param_name} format '{date_str}'. "
            f"Expected format: YYYY-MM-DD (e.g., '2024-01-01')"
        )

    # Check valid date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid {param_name} date '{date_str}': {str(e)}"
        )
```bash

## Consequences

### Positive

- ✅ **Fast Feedback**: Errors caught immediately (< 1ms vs 5s network delay)
- ✅ **Actionable Errors**: Error messages guide users to correct usage
- ✅ **Better UX**: Alpha Forge developers get clear, helpful error messages
- ✅ **Correctness**: Invalid inputs rejected before expensive operations
- ✅ **Type Safety**: Runtime validation complements static type hints

### Negative

- ⚠️ **Additional Validation Overhead**: ~1ms per API call (negligible vs 5s network)
- ⚠️ **Maintenance Burden**: Validation logic must stay in sync with supported symbols/timeframes

### Neutral

- Validation happens before network operations (design trade-off accepted)
- Error messages are verbose (improves UX, acceptable cost)

## Implementation Plan

### Phase 1: Create Validation Functions

**File**: `src/gapless_crypto_clickhouse/api.py`

**New Functions**:

1. `_validate_symbol()` - Symbol validation with suggestions
2. `_validate_timeframe_value()` - Timeframe validation
3. `_validate_date_format()` - Date format validation

### Phase 2: Integrate Validation

**Functions to update**:

1. `fetch_data()` - Add validation calls before collection
2. `download()` - Add validation calls before fetching

**Integration Pattern**:

```python
def download(...):
    # Existing: Timeframe normalization
    period = _validate_timeframe_parameters(timeframe, interval)

    # NEW: Upfront validation
    _validate_symbol(symbol)
    _validate_timeframe_value(period)
    _validate_date_format(start, "start")
    _validate_date_format(end, "end")

    # Continue with existing logic
    ...
```text

### Phase 3: Test Coverage

**Test Cases**:

```python
def test_invalid_symbol_raises_helpful_error():
    """Invalid symbol raises ValueError with suggestions."""
    with pytest.raises(ValueError, match="Did you mean 'BTCUSDT'"):
        gcc.download("BTCUSD", "1h")

def test_invalid_timeframe_raises_helpful_error():
    """Invalid timeframe raises ValueError with supported list."""
    with pytest.raises(ValueError, match="Supported timeframes"):
        gcc.download("BTCUSDT", "3h")  # 3h not supported

def test_invalid_date_format_raises_helpful_error():
    """Invalid date format raises ValueError with example."""
    with pytest.raises(ValueError, match="Expected format: YYYY-MM-DD"):
        gcc.download("BTCUSDT", "1h", start="2024/01/01")
````

## Validation Criteria

### Acceptance Criteria

- [ ] Symbol validation catches invalid symbols before network requests
- [ ] Timeframe validation catches invalid timeframes immediately
- [ ] Date format validation catches malformed dates upfront
- [ ] Error messages include actionable guidance (suggestions, examples)
- [ ] Test coverage for all validation paths
- [ ] No breaking changes to existing valid API calls

### SLO Impact

- **Correctness**: Improved (invalid inputs rejected immediately)
- **Observability**: Improved (clearer error messages)
- **Availability**: Improved (fast failure vs slow network timeout)
- **Maintainability**: Slight increase (validation logic maintenance)

## Migration Path

**For existing users**:

- No migration required (backward compatible)
- Valid API calls continue working unchanged
- Invalid calls now fail faster with better error messages

**For Alpha Forge integration**:

- Clearer error messages improve debugging experience
- Fast feedback reduces development iteration time
- No breaking changes to worry about

## References

- Alpha Forge Feedback: `/tmp/RESPONSE_TO_ALPHA_FORGE_FEEDBACK.md` (Issue #4)
- Existing Validation: `_validate_timeframe_parameters()` (lines 82-112)
- Python Validation Patterns: `argparse`, `pydantic` for structured validation

## Compliance

- **OSS Libraries**: Use standard library `re` and `datetime` for validation
- **Error Handling**: Raise `ValueError` for invalid inputs (raise+propagate pattern)
- **Backward Compatibility**: Full backward compatibility (valid calls unchanged)
- **Auto-Validation**: Test coverage validates error messages are helpful

## Future Work

- **Fuzzy Matching**: Implement Levenshtein distance for symbol suggestions
- **Date Range Validation**: Warn if date range predates symbol listing
- **Symbol Auto-Complete**: IDE integration for symbol suggestions

---

**ADR-0018** | Upfront Input Validation | Accepted | 2025-11-19
