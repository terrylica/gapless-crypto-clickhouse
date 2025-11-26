# Parameter Aliases Implementation Plan

**ADR ID**: 0017
**Status**: In Progress
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-19
**Target Release**: v2.5.0

---

## Objective

Add parameter aliases to support both `start`/`end` AND `start_date`/`end_date` for date range parameters in function-based APIs, improving API clarity while maintaining full backward compatibility.

## Background

### Problem

Current function-based API uses ambiguous parameter names:

`````python
df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")
```text

**Issues**:

- `start` and `end` lack semantic clarity (start of what? end of what?)
- Inconsistent with class-based API which uses `start_date`/`end_date`
- Alpha Forge feedback requests more explicit parameter names

### Solution

Add parameter aliases so both forms work:

```python
# Legacy form (still works)
df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

# New explicit form (recommended)
df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")
```text

## Goals

1. **Add Parameter Aliases** - Support both `start`/`end` and `start_date`/`end_date`
2. **Maintain Backward Compatibility** - Existing code continues working without changes
3. **Add Conflict Detection** - Raise error if both forms specified simultaneously
4. **Update Documentation** - Document both parameter forms clearly
5. **Test Coverage** - Validate legacy, new, and conflict scenarios

## Non-Goals

- Deprecating `start`/`end` parameters (both forms are first-class)
- Changing class-based API (already uses `start_date`/`end_date`)
- Adding aliases for other parameters (scope limited to date ranges)
- Type signature changes (all parameters remain `Optional[str]`)

## Design

### Parameter Normalization Strategy

**Principle**: Accept both forms, normalize internally, validate conflicts

**Implementation Pattern**:

```python
def download(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # Alias for start
    end_date: Optional[str] = None,    # Alias for end
    limit: Optional[int] = None,
    **kwargs
) -> pd.DataFrame:
    """Download historical data with flexible date parameter names."""

    # Conflict detection (raise+propagate pattern)
    if start is not None and start_date is not None:
        raise ValueError(
            "Cannot specify both 'start' and 'start_date'. "
            "Use either 'start' OR 'start_date', not both."
        )
    if end is not None and end_date is not None:
        raise ValueError(
            "Cannot specify both 'end' and 'end_date'. "
            "Use either 'end' OR 'end_date', not both."
        )

    # Normalize: prefer explicit _date parameters
    actual_start = start_date if start_date is not None else start
    actual_end = end_date if end_date is not None else end

    # Continue with existing logic using actual_start and actual_end
    ...
```text

### Files to Modify

#### 1. Update Function Signatures (`api.py`)

**File**: `src/gapless_crypto_clickhouse/api.py`

**Functions to update**:

- `download()` - Primary data download function
- `fetch_data()` - Recent data fetching function

**Current Signatures** (lines ~100-130):

```python
def download(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs
) -> pd.DataFrame:
    ...

def fetch_data(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs
) -> pd.DataFrame:
    ...
```text

**Updated Signatures**:

```python
def download(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # Alias for start
    end_date: Optional[str] = None,    # Alias for end
    limit: Optional[int] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Download historical cryptocurrency data.

    Parameters:
        symbol: Trading pair (e.g., "BTCUSDT")
        timeframe: Candle interval (e.g., "1h", "4h", "1d")
        start: Start date (YYYY-MM-DD). Alias: start_date
        end: End date (YYYY-MM-DD). Alias: end_date
        start_date: Alias for start (recommended for clarity)
        end_date: Alias for end (recommended for clarity)
        limit: Maximum number of bars to fetch
        **kwargs: Additional parameters

    Returns:
        DataFrame with 11-column microstructure format

    Raises:
        ValueError: If both start and start_date specified simultaneously

    Examples:
        # Legacy form (still supported)
        df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")

        # Explicit form (recommended)
        df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")
    """
    # Parameter normalization
    if start is not None and start_date is not None:
        raise ValueError("Cannot specify both 'start' and 'start_date'")
    if end is not None and end_date is not None:
        raise ValueError("Cannot specify both 'end' and 'end_date'")

    actual_start = start_date if start_date is not None else start
    actual_end = end_date if end_date is not None else end

    # Continue with existing logic
    ...
```text

#### 2. Update Documentation

**Files to update**:

1. `README.md` - Show both parameter forms in Quick Start
2. `docs/guides/python-api.md` - Document parameter aliases
3. `docs/api/quick-start.md` - Update examples
4. `llms.txt` - Update AI agent documentation

**README.md Changes**:

````markdown
# Quick Start

## Function-based API

```python
import gapless_crypto_clickhouse as gcch

# Explicit parameter names (recommended)
df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")

# Legacy form (still supported)
df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")
```text
`````

````

#### 3. Test Coverage

**File**: `tests/test_parameter_aliases.py` (new file)

**Test Cases**:
```python
import pytest
import gapless_crypto_clickhouse as gcch


def test_legacy_start_end_parameters():
    """Legacy start/end parameters continue working."""
    df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0
    assert "date" in df.columns


def test_new_start_date_end_date_aliases():
    """New start_date/end_date aliases work correctly."""
    df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0
    assert "date" in df.columns


def test_both_forms_produce_same_results():
    """Legacy and new forms produce identical results."""
    df1 = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
    df2 = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")

    assert len(df1) == len(df2)
    assert df1.equals(df2)


def test_conflict_start_and_start_date_raises_error():
    """Specifying both start and start_date raises ValueError."""
    with pytest.raises(ValueError, match="Cannot specify both 'start' and 'start_date'"):
        gcch.download("BTCUSDT", "1h", start="2024-01-01", start_date="2024-01-02")


def test_conflict_end_and_end_date_raises_error():
    """Specifying both end and end_date raises ValueError."""
    with pytest.raises(ValueError, match="Cannot specify both 'end' and 'end_date'"):
        gcch.download("BTCUSDT", "1h", end="2024-06-30", end_date="2024-07-01")


def test_fetch_data_legacy_parameters():
    """fetch_data() also supports legacy parameters."""
    df = gcch.fetch_data("ETHUSDT", "4h", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0


def test_fetch_data_new_aliases():
    """fetch_data() supports new parameter aliases."""
    df = gcch.fetch_data("ETHUSDT", "4h", start_date="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0
````

## Detailed Design

### Error Handling Strategy

**Principle**: Raise explicit errors for misuse, no silent fallbacks

**Conflict Detection**:

````python
if start is not None and start_date is not None:
    raise ValueError(
        "Cannot specify both 'start' and 'start_date'. "
        "Use either 'start' OR 'start_date', not both."
    )
```bash

**Why ValueError**:

- Standard Python exception for invalid parameter combinations
- Caught by testing frameworks for validation
- Clear error message guides users to correct usage

**No Silent Defaults**:

- Do NOT silently prefer one parameter over the other
- Do NOT issue warnings and continue (raise+propagate pattern)
- Users must fix their code if both specified

### Type Hint Compatibility

**No Breaking Changes**:

```python
# Before and after - identical type hints
start: Optional[str] = None
end: Optional[str] = None
start_date: Optional[str] = None
end_date: Optional[str] = None
```text

**Type Checkers**:

- `mypy` validation passes (all optional strings)
- IDE autocomplete shows all parameter forms
- No deprecation warnings (both forms first-class)

### Documentation Standards

**Docstring Format**:

```python
Parameters:
    start (str, optional): Start date (YYYY-MM-DD). Alias: start_date
    end (str, optional): End date (YYYY-MM-DD). Alias: end_date
    start_date (str, optional): Alias for start (recommended)
    end_date (str, optional): Alias for end (recommended)

Examples:
    # Both forms are equivalent and fully supported:
    df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")
    df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")

Raises:
    ValueError: If both 'start' and 'start_date' specified simultaneously
````

## Implementation Checklist

### Pre-Implementation

- [x] Create ADR-0017
- [x] Create this plan document
- [ ] Identify all functions requiring parameter aliases

### Implementation

- [ ] Update `download()` function in api.py
- [ ] Update `fetch_data()` function in api.py
- [ ] Add parameter normalization logic
- [ ] Add conflict detection with ValueError
- [ ] Update function docstrings

### Documentation

- [ ] Update README.md with both parameter forms
- [ ] Update docs/guides/python-api.md
- [ ] Update docs/api/quick-start.md
- [ ] Update llms.txt for AI agents

### Testing

- [ ] Create tests/test_parameter_aliases.py
- [ ] Test legacy parameters (start/end)
- [ ] Test new aliases (start_date/end_date)
- [ ] Test conflict detection (both specified)
- [ ] Test equivalence (both forms produce same results)
- [ ] Run full test suite (ensure no regressions)

### Release

- [ ] Commit with conventional commit message
- [ ] semantic-release creates v2.5.0
- [ ] Verify GitHub release notes
- [ ] Update Alpha Forge status document

## Rollout Plan

### Timeline

- **Implementation**: 2025-11-19 (same day as v2.4.0)
- **Release**: v2.5.0 immediately after implementation
- **Alpha Forge Notification**: After v2.6.0 (batch update)

### Validation Steps

1. **Unit Tests**: All parameter alias tests pass
2. **Integration Tests**: Existing tests pass with no regressions
3. **Manual Verification**: Both parameter forms work in real usage

### Rollback Strategy

**If critical issues found**:

- Rollback is simple (remove new parameters, keep legacy)
- No breaking changes introduced (backward compatible)
- Users unaffected (legacy parameters unchanged)

**Mitigation**: Comprehensive test coverage reduces rollback risk

## Risks and Mitigations

### Risk 1: Parameter Name Conflicts

**Risk**: Users accidentally specify both `start` and `start_date`
**Likelihood**: Medium (copy-paste errors, refactoring mistakes)
**Impact**: Low (clear error message, easy to fix)
**Mitigation**: Explicit ValueError with clear remediation guidance

### Risk 2: Documentation Confusion

**Risk**: Users unsure which parameter form to use
**Likelihood**: Medium (multiple valid forms)
**Impact**: Low (both work correctly)
**Mitigation**: Documentation recommends `start_date`/`end_date` as preferred

### Risk 3: Type Checker Warnings

**Risk**: Static type checkers flag duplicate parameters
**Likelihood**: Very Low (all parameters optional, same type)
**Impact**: Very Low (no actual issue)
**Mitigation**: Both parameters have identical type hints

## Success Metrics

### Primary Metrics

- [ ] All tests pass (legacy, new aliases, conflicts)
- [ ] Zero breaking changes (existing code unaffected)
- [ ] Documentation clearly explains both forms
- [ ] Alpha Forge can use `start_date`/`end_date` immediately

### Secondary Metrics

- [ ] Type checkers pass (mypy clean)
- [ ] IDE autocomplete shows all parameter forms
- [ ] Error messages guide users to correct usage

## Open Questions

- **Q**: Should we recommend one form over the other?
  **A**: Yes - documentation recommends `start_date`/`end_date` for clarity, but both first-class

- **Q**: Should we add similar aliases for other parameters (e.g., `interval` → `timeframe`)?
  **A**: Defer to future work based on user feedback

- **Q**: How to handle parameter aliases in kwargs-based forwarding?
  **A**: Normalize before passing to underlying classes

## References

- ADR-0017: Parameter Aliases
- Alpha Forge Feedback: `/tmp/RESPONSE_TO_ALPHA_FORGE_FEEDBACK.md` (Issue #3)
- Python Parameter Alias Patterns: `pandas.DataFrame.to_csv(path_or_buf=...)` supports both positional and keyword

## Log Files

Implementation logs stored in:

- `logs/0017-parameter-aliases-YYYYMMDD_HHMMSS.log`

---

**Plan 0017** | Parameter Aliases | In Progress | 2025-11-19
