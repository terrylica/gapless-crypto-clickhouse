# Parameter Aliases for Date Range Parameters

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Terry Li
**Related ADRs**: None
**Related Plans**: [0017-parameter-aliases](../../development/plan/0017-parameter-aliases/plan.md)

## Context and Problem Statement

Current API uses `start` and `end` parameters for date ranges, but parameter names lack semantic clarity.

**Alpha Forge Feedback**: "Parameter names like `start`/`end` are ambiguous - add `start_date`/`end_date` aliases"

**Current API**:

````python
df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")
collector = BinancePublicDataCollector(start_date="2024-01-01", end_date="2024-06-30")
```bash

**Inconsistency**: Function-based API uses `start`/`end`, class-based API uses `start_date`/`end_date`

**Question**: Should we add parameter aliases to support both naming conventions?

## Decision Drivers

- **API Clarity**: Explicit parameter names reduce ambiguity
- **Consistency**: Function-based and class-based APIs should align
- **Backward Compatibility**: Existing code using `start`/`end` must continue working
- **Alpha Forge Integration**: Clearer API improves adoption
- **Python Conventions**: Most datetime libraries use `*_date` suffixes

## Considered Options

1. **Add parameter aliases** (support both `start`/`end` AND `start_date`/`end_date`)
2. **Deprecate and rename** (`start`/`end` → `start_date`/`end_date` with deprecation warnings)
3. **Keep current naming** (no changes, reject feedback)
4. **Force consistency** (rename all to `start_date`/`end_date`, breaking change)

## Decision Outcome

**Chosen option**: Add parameter aliases (support both forms)

**Rationale**:

### Why Parameter Aliases

**Backward Compatibility**:

- Existing code using `start`/`end` continues working without changes
- No deprecation warnings needed (both forms are first-class)
- Zero migration burden for current users

**API Clarity**:

- `start_date="2024-01-01"` is more explicit than `start="2024-01-01"`
- Aligns with class-based API naming (`BinancePublicDataCollector(start_date=...)`)
- Reduces cognitive load for new users

**Implementation Simplicity**:

- No breaking changes required
- Simple parameter normalization in function bodies
- No deprecation timeline management

### Implementation Strategy

**Function Signatures**:

```python
def download(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # NEW alias
    end_date: Optional[str] = None,    # NEW alias
    limit: Optional[int] = None,
    **kwargs
) -> pd.DataFrame:
    # Normalize: prefer explicit _date parameters
    if start_date is not None and start is not None:
        raise ValueError("Cannot specify both 'start' and 'start_date'")
    if end_date is not None and end is not None:
        raise ValueError("Cannot specify both 'end' and 'end_date'")

    # Use whichever was provided
    actual_start = start_date if start_date is not None else start
    actual_end = end_date if end_date is not None else end
```bash

**Class-based API**:

- Already uses `start_date`/`end_date` (no changes needed)
- Maintains consistency

**Type Hints**:

- All parameters remain `Optional[str]`
- No breaking changes to type signatures

## Consequences

### Positive

- ✅ **Zero Breaking Changes**: Existing code continues working without modification
- ✅ **Improved Clarity**: New users prefer explicit `start_date`/`end_date` naming
- ✅ **API Consistency**: Function-based and class-based APIs now aligned
- ✅ **Alpha Forge Feedback**: Addresses feedback without breaking changes
- ✅ **Future-Proof**: No deprecation timeline to manage

### Negative

- ⚠️ **Parameter Validation Overhead**: Must validate that both forms aren't specified simultaneously
- ⚠️ **Documentation Burden**: Must document both parameter forms
- ⚠️ **Cognitive Overhead**: Users must choose between two equivalent forms

### Neutral

- Multiple valid parameter names (standard Python practice, e.g., `file` vs `filename`)
- Slightly longer function signatures (acceptable trade-off)

## Implementation Plan

### Phase 1: Update Function Signatures

**Files to modify**:

1. `src/gapless_crypto_clickhouse/api.py` - Add aliases to `download()`, `fetch_data()`
2. `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py` - Already uses `start_date`/`end_date`

**Change Pattern**:

```python
# Before
def download(symbol: str, timeframe: str, start: Optional[str] = None, end: Optional[str] = None, ...)

# After
def download(
    symbol: str,
    timeframe: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    start_date: Optional[str] = None,  # Alias for start
    end_date: Optional[str] = None,    # Alias for end
    ...
)
```text

### Phase 2: Add Parameter Normalization

**Validation Logic**:

```python
# Conflict detection
if start is not None and start_date is not None:
    raise ValueError(
        "Cannot specify both 'start' and 'start_date'. "
        "Use either 'start' OR 'start_date', not both."
    )

# Normalization
actual_start = start_date if start_date is not None else start
actual_end = end_date if end_date is not None else end
```text

**Error Handling**:

- Raise `ValueError` if both forms specified simultaneously
- Clear error message explains conflict
- No silent fallbacks or defaults

### Phase 3: Update Documentation

**Files to update**:

1. `README.md` - Show both parameter forms in examples
2. `docs/guides/python-api.md` - Document parameter aliases
3. Function docstrings - Explain alias behavior
4. `llms.txt` - Update AI agent documentation

**Documentation Pattern**:

```python
def download(...):
    """
    Download historical cryptocurrency data.

    Parameters:
        start (str, optional): Start date (YYYY-MM-DD). Alias: start_date
        end (str, optional): End date (YYYY-MM-DD). Alias: end_date
        start_date (str, optional): Alias for start (recommended)
        end_date (str, optional): Alias for end (recommended)

    Examples:
        # Both forms are equivalent:
        df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-06-30")
        df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-06-30")
    """
```text

### Phase 4: Test Coverage

**Test Cases**:

```python
def test_start_end_legacy_parameters():
    """Legacy start/end parameters still work."""
    df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0

def test_start_date_end_date_aliases():
    """New start_date/end_date aliases work."""
    df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0

def test_mixed_parameters_raise_error():
    """Cannot use both start and start_date simultaneously."""
    with pytest.raises(ValueError, match="Cannot specify both"):
        gcch.download("BTCUSDT", "1h", start="2024-01-01", start_date="2024-01-02")
````

## Validation Criteria

### Acceptance Criteria

- [ ] All function-based APIs support both `start`/`end` AND `start_date`/`end_date`
- [ ] Validation raises `ValueError` when both forms specified simultaneously
- [ ] Documentation updated to show both parameter forms
- [ ] Test coverage for legacy parameters, new aliases, and conflict detection
- [ ] No breaking changes to existing code
- [ ] Type hints remain unchanged

### SLO Impact

- **Correctness**: Improved (explicit parameter names reduce user errors)
- **Observability**: Improved (better error messages for parameter conflicts)
- **Maintainability**: Slight increase (must maintain both parameter forms)
- **Availability**: No change (backward compatible)

## Migration Path

**For existing users**:

- No migration required (backward compatible)
- Can continue using `start`/`end` indefinitely
- Can adopt `start_date`/`end_date` gradually

**For new users**:

- Documentation recommends `start_date`/`end_date` (clearer intent)
- Both forms documented as first-class (no deprecation warnings)

**For Alpha Forge integration**:

- Can use preferred `start_date`/`end_date` naming immediately
- No breaking changes to worry about

## References

- Alpha Forge Feedback: `/tmp/RESPONSE_TO_ALPHA_FORGE_FEEDBACK.md` (Issue #3)
- Python Convention: `pandas.DataFrame.loc[start_date:end_date]`
- Existing Class API: `BinancePublicDataCollector(start_date=..., end_date=...)`

## Compliance

- **OSS Libraries**: No custom code needed (parameter normalization is trivial)
- **Error Handling**: Raise `ValueError` for conflicts (raise+propagate pattern)
- **Backward Compatibility**: Full backward compatibility (additive change only)
- **Auto-Validation**: Test coverage validates both parameter forms work correctly

## Future Work

- **Timeframe Aliases**: Consider adding `interval` as alias for `timeframe` (CCXT compatibility)
- **Parameter Consolidation**: Monitor which parameter names users prefer over time
- **API Style Guide**: Document preferred parameter naming conventions

---

**ADR-0017** | Parameter Aliases | Accepted | 2025-11-19
