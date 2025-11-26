# Upfront Input Validation Implementation Plan

**ADR ID**: 0018
**Status**: In Progress
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-19
**Target Release**: v2.6.0

---

## Objective

Add upfront input validation with actionable error messages to catch invalid inputs before expensive network/database operations, improving user experience and fast failure.

## Background

### Problem

Current API performs minimal validation before executing operations:

````python
# Invalid symbol - fails during data collection (5+ seconds delay)
df = gcc.download("BTCUSD", "1h")  # Network request → 404 → "No data found"

# Invalid timeframe - fails during collection
df = gcc.download("BTCUSDT", "3h")  # Network request → empty data

# Invalid date format - fails during parsing
df = gcc.download("BTCUSDT", "1h", start="2024-13-01")  # datetime error
```text

**Issues**:

- Slow feedback (errors after network operations)
- Unclear error messages
- No suggestions for correction

### Solution

Add upfront validation with helpful error messages:

```python
# After implementation
df = gcc.download("BTCUSD", "1h")
# → ValueError: Invalid symbol 'BTCUSD'. Did you mean 'BTCUSDT'?
#    Supported symbols: BTCUSDT, ETHUSDT, BNBUSDT, ... (see get_supported_symbols())
```text

## Goals

1. **Symbol Validation** - Validate against `known_symbols` before network requests
2. **Timeframe Validation** - Validate against `available_timeframes` immediately
3. **Date Format Validation** - Validate YYYY-MM-DD format upfront
4. **Actionable Errors** - Error messages guide users to correct usage
5. **Fast Failure** - Catch errors in < 1ms vs 5s network delay

## Non-Goals

- Fuzzy matching with Levenshtein distance (defer to future work)
- Date range vs symbol listing date validation (defer to future work)
- Network connectivity validation (out of scope)
- Data availability pre-checks (expensive, defeats purpose)

## Design

### Validation Strategy

**Principle**: Fail fast with actionable feedback

**Validation Order**:

1. Symbol validation (check against known_symbols)
2. Timeframe validation (check against available_timeframes)
3. Date format validation (YYYY-MM-DD regex + parsing)

**Error Message Pattern**:

````

ValueError: Invalid <parameter> '<value>'. <Suggestion>
Supported <parameters>: <list> (see <function>())

````text

### Implementation Details

#### 1. Symbol Validation Function

**Location**: `src/gapless_crypto_clickhouse/api.py`

**Function**:

```python
def _validate_symbol(symbol: str) -> None:
    """Validate symbol against known supported symbols.

    Args:
        symbol: Trading pair symbol to validate

    Raises:
        ValueError: If symbol is not supported, with suggestions
    """
    from gapless_crypto_clickhouse import get_supported_symbols

    supported = get_supported_symbols()

    if symbol not in supported:
        # Find close matches (simple prefix matching)
        close_matches = [s for s in supported if s.startswith(symbol[:3].upper())]

        if close_matches:
            raise ValueError(
                f"Invalid symbol '{symbol}'. Did you mean '{close_matches[0]}'? "
                f"Supported symbols: {', '.join(supported[:5])}, ... "
                f"(see get_supported_symbols() for full list)"
            )
        else:
            raise ValueError(
                f"Invalid symbol '{symbol}'. "
                f"Supported symbols: {', '.join(supported[:10])}, ... "
                f"(see get_supported_symbols() for full list of {len(supported)} symbols)"
            )
```bash

**Why This Design**:

- Simple prefix matching (fast, no external dependencies)
- Shows first 5 symbols for brevity
- Directs users to `get_supported_symbols()` for complete list
- Provides "Did you mean?" suggestion when possible

#### 2. Timeframe Validation Function

**Location**: `src/gapless_crypto_clickhouse/api.py`

**Function**:

```python
def _validate_timeframe_value(timeframe: str) -> None:
    """Validate timeframe against supported timeframes.

    Args:
        timeframe: Timeframe interval to validate

    Raises:
        ValueError: If timeframe is not supported
    """
    from gapless_crypto_clickhouse import get_supported_timeframes

    supported = get_supported_timeframes()

    if timeframe not in supported:
        raise ValueError(
            f"Invalid timeframe '{timeframe}'. "
            f"Supported timeframes: {', '.join(supported)} "
            f"(see get_supported_timeframes() for details)"
        )
```text

**Why This Design**:

- Shows all supported timeframes (only 13, fits in error message)
- No fuzzy matching needed (timeframes are short, typos less likely)
- Clear enumeration guides users

#### 3. Date Format Validation Function

**Location**: `src/gapless_crypto_clickhouse/api.py`

**Function**:

```python
def _validate_date_format(date_str: Optional[str], param_name: str) -> None:
    """Validate date string format (YYYY-MM-DD).

    Args:
        date_str: Date string to validate
        param_name: Parameter name for error context

    Raises:
        ValueError: If date format is invalid
    """
    if date_str is None:
        return

    import re
    from datetime import datetime

    # Check YYYY-MM-DD format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(
            f"Invalid {param_name} format '{date_str}'. "
            f"Expected format: YYYY-MM-DD (e.g., '2024-01-01')"
        )

    # Validate date is parseable
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(
            f"Invalid {param_name} date '{date_str}': {str(e)}"
        ) from e
```text

**Why This Design**:

- Two-stage validation: format regex then parsing
- Shows example format for clarity
- Preserves datetime error message for invalid dates (e.g., "2024-13-01")

#### 4. Integration into API Functions

**Update `fetch_data()` function**:

```python
def fetch_data(...):
    """..."""
    # Validate and resolve timeframe parameters
    period = _validate_timeframe_parameters(timeframe, interval)

    # Validate deprecated index_type parameter
    _validate_index_type_parameter(index_type)

    # NEW: Upfront input validation
    _validate_symbol(symbol)
    _validate_timeframe_value(period)
    _validate_date_format(start, "start")
    _validate_date_format(end, "end")

    # Validate and normalize date range parameters
    if start is not None and start_date is not None:
        ...

    # Continue with existing logic
    ...
```text

**Update `download()` function**:

```python
def download(...):
    """..."""
    # Apply default if neither parameter specified
    if timeframe is None and interval is None:
        timeframe = "1h"

    # Validate and normalize date range parameters
    if start is not None and start_date is not None:
        ...

    # Normalize: prefer explicit _date parameters
    start = start_date if start_date is not None else start
    end = end_date if end_date is not None else end

    # NEW: Delegate to fetch_data (which now has validation)
    return fetch_data(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        ...
    )
```bash

**Note**: Since `download()` calls `fetch_data()`, validation in `fetch_data()` covers both entry points.

### Test Strategy

**File**: `tests/test_input_validation.py` (new)

**Test Cases**:

```python
import pytest
import gapless_crypto_clickhouse as gcc


class TestSymbolValidation:
    """Test symbol validation with helpful error messages."""

    def test_invalid_symbol_raises_error(self):
        """Invalid symbol raises ValueError."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            gcc.download("INVALIDPAIR", "1h")

    def test_invalid_symbol_suggests_correction(self):
        """Invalid symbol with close match suggests correction."""
        with pytest.raises(ValueError, match="Did you mean 'BTCUSDT'"):
            gcc.download("BTCUSD", "1h")

    def test_invalid_symbol_shows_supported_list(self):
        """Invalid symbol shows list of supported symbols."""
        with pytest.raises(ValueError, match="Supported symbols.*get_supported_symbols"):
            gcc.download("XYZ", "1h")

    def test_valid_symbol_passes(self):
        """Valid symbol passes validation (may fail later for other reasons)."""
        # Should not raise ValueError for symbol validation
        try:
            gcc.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
        except ValueError as e:
            if "Invalid symbol" in str(e):
                pytest.fail("Valid symbol should not raise symbol validation error")


class TestTimeframeValidation:
    """Test timeframe validation with helpful error messages."""

    def test_invalid_timeframe_raises_error(self):
        """Invalid timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            gcc.download("BTCUSDT", "3h")  # 3h not supported

    def test_invalid_timeframe_shows_supported_list(self):
        """Invalid timeframe shows all supported timeframes."""
        with pytest.raises(ValueError, match="Supported timeframes:.*1s.*1m.*1d"):
            gcc.download("BTCUSDT", "7d")

    def test_valid_timeframe_passes(self):
        """Valid timeframe passes validation."""
        try:
            gcc.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
        except ValueError as e:
            if "Invalid timeframe" in str(e):
                pytest.fail("Valid timeframe should not raise timeframe validation error")


class TestDateFormatValidation:
    """Test date format validation with helpful error messages."""

    def test_invalid_date_format_raises_error(self):
        """Invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start format"):
            gcc.download("BTCUSDT", "1h", start="2024/01/01")

    def test_invalid_date_format_shows_example(self):
        """Invalid date format shows expected format."""
        with pytest.raises(ValueError, match="Expected format: YYYY-MM-DD"):
            gcc.download("BTCUSDT", "1h", start="01-01-2024")

    def test_invalid_date_value_raises_error(self):
        """Invalid date value raises ValueError."""
        with pytest.raises(ValueError, match="Invalid start date"):
            gcc.download("BTCUSDT", "1h", start="2024-13-01")  # Month 13

    def test_valid_date_format_passes(self):
        """Valid date format passes validation."""
        try:
            gcc.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
        except ValueError as e:
            if "Invalid start format" in str(e) or "Invalid end format" in str(e):
                pytest.fail("Valid date format should not raise date validation error")


class TestFetchDataValidation:
    """Test validation also applies to fetch_data()."""

    def test_fetch_data_validates_symbol(self):
        """fetch_data() validates symbol."""
        with pytest.raises(ValueError, match="Invalid symbol"):
            gcc.fetch_data("INVALID", "1h")

    def test_fetch_data_validates_timeframe(self):
        """fetch_data() validates timeframe."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            gcc.fetch_data("BTCUSDT", "3h")

    def test_fetch_data_validates_dates(self):
        """fetch_data() validates date formats."""
        with pytest.raises(ValueError, match="Invalid start format"):
            gcc.fetch_data("BTCUSDT", "1h", start="2024/01/01")
````

## Implementation Checklist

### Pre-Implementation

- [x] Create ADR-0018
- [x] Create this plan document
- [ ] Review existing validation patterns in codebase

### Implementation

- [ ] Create `_validate_symbol()` function in api.py
- [ ] Create `_validate_timeframe_value()` function in api.py
- [ ] Create `_validate_date_format()` function in api.py
- [ ] Integrate validation calls into `fetch_data()`
- [ ] Verify `download()` inherits validation via `fetch_data()`

### Testing

- [ ] Create tests/test_input_validation.py
- [ ] Test invalid symbol errors
- [ ] Test invalid timeframe errors
- [ ] Test invalid date format errors
- [ ] Test valid inputs pass through
- [ ] Run full test suite (ensure no regressions)

### Documentation

- [ ] Update function docstrings with validation behavior
- [ ] Update error handling documentation

### Release

- [ ] Commit with conventional commit message
- [ ] semantic-release creates v2.6.0
- [ ] Verify GitHub release notes
- [ ] Update Alpha Forge status document

## Rollout Plan

### Timeline

- **Implementation**: 2025-11-19 (same day as v2.4.0, v2.5.0)
- **Release**: v2.6.0 immediately after implementation
- **Alpha Forge Notification**: Batch update with all three releases

### Validation Steps

1. **Unit Tests**: All validation tests pass
2. **Integration Tests**: Existing tests pass with no regressions
3. **Manual Verification**: Error messages are helpful and actionable

### Rollback Strategy

**If critical issues found**:

- Remove validation calls from `fetch_data()`
- Keep validation functions for future use
- No breaking changes (validation is additive)

**Mitigation**: Comprehensive test coverage reduces rollback risk

## Risks and Mitigations

### Risk 1: False Positives

**Risk**: Validation rejects valid symbols/timeframes
**Likelihood**: Very Low (validation against known lists)
**Impact**: High (blocks valid operations)
**Mitigation**: Validation uses same source as actual operations (`get_supported_symbols()`, `get_supported_timeframes()`)

### Risk 2: Performance Overhead

**Risk**: Validation adds latency to API calls
**Likelihood**: Low (simple list lookups)
**Impact**: Very Low (~1ms vs 5s network operations)
**Mitigation**: Validation is O(n) list lookup, negligible vs network I/O

### Risk 3: Suggestion Accuracy

**Risk**: "Did you mean?" suggestions are incorrect
**Likelihood**: Medium (simple prefix matching)
**Impact**: Low (users can still see full list)
**Mitigation**: Prefix matching is conservative, shows alternatives

## Success Metrics

### Primary Metrics

- [ ] Invalid symbols caught before network requests
- [ ] Invalid timeframes caught immediately
- [ ] Invalid date formats caught upfront
- [ ] Error messages include actionable guidance
- [ ] Zero false positives in validation

### Secondary Metrics

- [ ] Error feedback < 1ms (vs 5s network delay)
- [ ] Test coverage for all validation paths
- [ ] User reports of improved error clarity

## Open Questions

- **Q**: Should we validate date ranges against symbol listing dates?
  **A**: Defer to future work (requires per-symbol metadata lookup)

- **Q**: Should we add fuzzy matching for symbol suggestions?
  **A**: Defer to future work (requires additional dependencies)

- **Q**: Should validation be optional via parameter?
  **A**: No - validation improves correctness SLO, always enabled

## References

- ADR-0018: Upfront Input Validation
- Alpha Forge Feedback: `/tmp/RESPONSE_TO_ALPHA_FORGE_FEEDBACK.md` (Issue #4)
- Existing Validation: `_validate_timeframe_parameters()` in api.py
- Python Best Practices: `argparse` error message patterns

## Log Files

Implementation logs stored in:

- `logs/0018-upfront-input-validation-YYYYMMDD_HHMMSS.log`

---

**Plan 0018** | Upfront Input Validation | In Progress | 2025-11-19
