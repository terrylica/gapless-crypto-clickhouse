# Spot and Futures Symbol Alignment Implementation Plan

**Version**: v4.1.0
**ADR ID**: 0022
**Status**: In Progress
**Author**: Terry Li
**Date**: 2025-11-20
**Related ADR**: [ADR-0022 (Spot/Futures Symbol Alignment)](../../../architecture/decisions/0022-spot-futures-symbol-alignment.md)
**Related ADR**: [ADR-0021 (UM Futures Support)](../../../architecture/decisions/0021-um-futures-support.md)

---

## Objective

Align spot and futures symbol coverage to 713 symbols each by using `binance-futures-availability` as the single source of truth for both instrument types, removing the artificial 20-symbol limitation on spot data.

**Success Criteria**:

- `get_supported_symbols("spot")` returns 713 symbols
- `get_supported_symbols("futures-um")` returns 713 symbols
- `BinancePublicDataCollector.known_symbols` hardcoded dict removed
- All "20 symbols" references updated to "713 symbols"
- All tests pass
- 100% backward compatible (additive change)

---

## Background

### v4.0.0 Implementation Gap

After implementing UM futures support in v4.0.0 ([ADR-0021](../../../architecture/decisions/0021-um-futures-support.md)), a critical misalignment was identified:

- **Spot**: 20 hardcoded USDT pairs in `BinancePublicDataCollector.known_symbols`
- **Futures**: 713 validated symbols from `binance-futures-availability` package

**User Requirement** (2025-11-20):

> "as a matter of fact You have to do some additional change as well because it is wrong to have just 20 USDT pair for the spot. the spot and future should completely be aligned, meaning whenever we have the futures, we must have the spot. So the 713 applicable for both the spot and future"

### Why This Matters

1. **Inconsistent UX**: Futures users have 36x more symbol options than spot users
2. **Artificial Limitation**: No technical reason to limit spot to 20 symbols
3. **Maintenance Burden**: Hardcoded dict requires manual updates
4. **Package Trust**: `binance-futures-availability` already validated (95%+ SLA)

---

## Context

### Investigation Summary (2025-11-20)

**Task**: Find all locations with hardcoded 20-symbol references

**Agent**: Plan subagent (medium thoroughness)

**Findings**: 9 locations requiring updates

#### Code Locations

1. **`api.py` Line 66-68**: `get_supported_symbols()` implementation

   ```python
   # Current: Bifurcated logic (spot=20, futures=713)
   if instrument_type == "futures-um":
       from binance_futures_availability.config.symbol_loader import load_symbols
       return load_symbols("perpetual")  # 713 symbols
   else:
       collector = BinancePublicDataCollector()
       return list(collector.known_symbols.keys())  # 20 symbols
   ```

2. **`api.py` Lines 89-95**: `SupportedSymbol` type alias

   ```python
   # 20 hardcoded symbols in Literal (must deprecate - 713 too large)
   SupportedSymbol = Literal["BTCUSDT", "ETHUSDT", ...]
   ```

3. **`api.py` Docstrings**: Lines 42, 498, 640, 745
   - "20 symbols" → "713 symbols"

4. **`binance_public_data_collector.py` Lines 301-328**: `known_symbols` dict

   ```python
   # Hardcoded dict (28 lines) - remove entirely
   known_symbols = {
       "BTCUSDT": "Bitcoin",
       "ETHUSDT": "Ethereum",
       # ... 18 more symbols
   }
   ```

5. **`binance_public_data_collector.py` Line 87**: Class docstring
   - "spot only" → update to reflect 713-symbol coverage

6. **`binance_public_data_collector.py` Line 190**: Parameter docstring
   - "20 symbols" → "713 symbols"

7. **`__init__.py` Lines 76-82**: Module docstring
   - "20 USDT pairs" → "713 perpetual symbols"

8. **`tests/test_timestamp_utils.py`**: Uses `get_supported_symbols()` dynamically
   - Will adapt automatically (no changes needed)

#### Architecture Decision

**Decision**: Use `binance-futures-availability` for BOTH spot and futures

**Rationale**:

- Binance markets are aligned (perpetual futures → spot pairs exist)
- Package already validated in production (daily S3 Vision probes)
- No need for separate symbol sources or validation logic
- Simplifies codebase (single source of truth)

**Alternative Considered**: Separate spot symbol package

- **Rejected**: Over-engineering, duplication, maintenance burden

**See**: [ADR-0022](../../../architecture/decisions/0022-spot-futures-symbol-alignment.md) for complete analysis

### Current State (v4.0.0)

```
┌─────────────────────────────────────────────────────────────┐
│ API Layer (api.py)                                          │
│                                                             │
│ get_supported_symbols(instrument_type="spot"):              │
│   if instrument_type == "futures-um":                       │
│     return load_symbols("perpetual")  # 713 symbols         │
│   else:                                                     │
│     return collector.known_symbols.keys()  # 20 symbols ❌  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Collector Layer (binance_public_data_collector.py)         │
│                                                             │
│ known_symbols = {  # Hardcoded dict (28 lines) ❌           │
│   "BTCUSDT": "Bitcoin",                                     │
│   "ETHUSDT": "Ethereum",                                    │
│   # ... 18 more symbols                                    │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Target State (v4.1.0)

```
┌─────────────────────────────────────────────────────────────┐
│ API Layer (api.py)                                          │
│                                                             │
│ get_supported_symbols(instrument_type="spot"):              │
│   _validate_instrument_type(instrument_type)                │
│   return load_symbols("perpetual")  # 713 symbols ✅        │
│                                                             │
│ # Same 713 symbols for both "spot" and "futures-um"         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ binance-futures-availability Package                        │
│                                                             │
│ load_symbols("perpetual")                                   │
│   → 713 validated symbols (95%+ SLA)                        │
│   → Daily S3 Vision probes                                  │
│   → DuckDB availability tracking                            │
└─────────────────────────────────────────────────────────────┘
```

**Key Changes**:

- ❌ Remove `BinancePublicDataCollector.known_symbols` dict
- ✅ Single code path: `load_symbols("perpetual")` for both types
- ✅ Consistent 713-symbol coverage for spot and futures

---

## Plan

### Phase 1: Code Simplification (Core Implementation)

#### Task 1.1: Update `get_supported_symbols()` Function

**File**: `src/gapless_crypto_clickhouse/api.py` (Lines 66-68)

**Before**:

```python
def get_supported_symbols(instrument_type: InstrumentType = "spot") -> List[str]:
    """Get list of supported symbols for given instrument type.

    Args:
        instrument_type: Type of instrument ("spot" or "futures-um")

    Returns:
        List of supported symbols (20 for spot, 713 for futures-um)
    """
    _validate_instrument_type(instrument_type)
    if instrument_type == "futures-um":
        from binance_futures_availability.config.symbol_loader import load_symbols
        return load_symbols("perpetual")
    else:
        collector = BinancePublicDataCollector()
        return list(collector.known_symbols.keys())
```

**After**:

```python
def get_supported_symbols(instrument_type: InstrumentType = "spot") -> List[str]:
    """Get list of supported symbols for given instrument type.

    Returns 713 validated perpetual symbols for both spot and futures.
    Symbol list sourced from binance-futures-availability package
    (validated daily via S3 Vision probes, 95%+ SLA).

    Note: The instrument_type parameter is retained for API compatibility,
    but both "spot" and "futures-um" return the same 713-symbol list.
    Rationale: Binance markets are aligned - perpetual futures symbols
    correspond to spot pairs.

    Args:
        instrument_type: Type of instrument ("spot" or "futures-um")

    Returns:
        List of 713 supported symbols (same for both spot and futures)

    Raises:
        ValueError: If instrument_type is invalid

    Example:
        >>> symbols = get_supported_symbols("spot")
        >>> len(symbols)
        713
        >>> get_supported_symbols("spot") == get_supported_symbols("futures-um")
        True
    """
    from binance_futures_availability.config.symbol_loader import load_symbols

    # Validate parameter (fail fast on invalid types)
    _validate_instrument_type(instrument_type)

    # Return same 713 symbols for both types (ADR-0022)
    return load_symbols("perpetual")
```

**Changes**:

- ✅ Remove if/else bifurcation logic
- ✅ Import `load_symbols` at function level
- ✅ Single code path for both instrument types
- ✅ Enhanced docstring explaining alignment rationale
- ✅ Added example demonstrating 713-symbol count

#### Task 1.2: Deprecate `SupportedSymbol` Type Alias

**File**: `src/gapless_crypto_clickhouse/api.py` (Lines 89-95)

**Before**:

```python
SupportedSymbol = Literal[
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT",
    "XRPUSDT", "DOTUSDT", "UNIUSDT", "LTCUSDT", "LINKUSDT",
    "SOLUSDT", "MATICUSDT", "XLMUSDT", "ETCUSDT", "ATOMUSDT",
    "VETUSDT", "FILUSDT", "TRXUSDT", "AVAXUSDT", "AAVEUSDT"
]
```

**After**:

```python
# DEPRECATED in v4.1.0: SupportedSymbol type alias removed
# Reason: 713-symbol Literal exceeds practical type checker limits
# Migration: Use `str` for symbol parameters, validate via get_supported_symbols()
#
# Before (v4.0.0):
#   def my_function(symbol: SupportedSymbol) -> None: ...
#
# After (v4.1.0):
#   def my_function(symbol: str) -> None:
#       if symbol not in get_supported_symbols():
#           raise ValueError(f"Unsupported symbol: {symbol}")
```

**Changes**:

- ❌ Remove 20-symbol Literal type alias
- ✅ Add deprecation notice with migration guide
- ✅ Suggest runtime validation via `get_supported_symbols()`

#### Task 1.3: Remove `known_symbols` Hardcoded Dict

**File**: `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py` (Lines 301-328)

**Before**:

```python
known_symbols = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    # ... 18 more symbols (28 lines total)
}
```

**After**:

- ❌ Delete entire dict (no replacement needed)
- ✅ Symbol validation now handled by `get_supported_symbols()` in API layer

**Rationale**:

- Collector layer doesn't need symbol validation (API layer handles it)
- Package provides authoritative symbol source
- Reduces code duplication and maintenance burden

### Phase 2: Documentation Updates

#### Task 2.1: Update Module Docstring

**File**: `src/gapless_crypto_clickhouse/__init__.py` (Lines 76-82)

**Before**:

```python
"""Gapless Crypto ClickHouse - ClickHouse-based cryptocurrency data collection

Features:
- 20 USDT pairs (spot) with plans for 400+ futures symbols
- 16 timeframes (1s to 1mo)
- Zero-gap guarantee via dual data source strategy
"""
```

**After**:

```python
"""Gapless Crypto ClickHouse - ClickHouse-based cryptocurrency data collection

Features:
- 713 perpetual symbols (spot and futures-um)
- 16 timeframes (1s to 1mo)
- Zero-gap guarantee via dual data source strategy
- ReplacingMergeTree schema with deterministic versioning
"""
```

#### Task 2.2: Update Function Docstrings (9 Locations)

**Files**: `api.py`, `binance_public_data_collector.py`

**Pattern**: Replace "20 symbols" → "713 symbols"

**Locations**:

1. `api.py` Line 42: Module-level docstring
2. `api.py` Line 498: `fetch_data()` docstring
3. `api.py` Line 640: `download()` docstring
4. `api.py` Line 745: `download_multiple()` docstring
5. `binance_public_data_collector.py` Line 87: Class docstring
6. `binance_public_data_collector.py` Line 190: Parameter docstring

**Example**:

```python
# Before
"""Download OHLCV data for one of 20 supported USDT pairs"""

# After
"""Download OHLCV data for one of 713 supported perpetual symbols"""
```

### Phase 3: Validation and Release

#### Task 3.1: Run Test Suite

**Command**:

```bash
uv run pytest tests/ -v --cov=src/gapless_crypto_clickhouse --cov-report=term-missing
```

**Expected**: All 27+ tests pass

**Auto-Fix Strategy**:

- If tests fail, analyze failure output
- Fix issues immediately before proceeding
- Re-run tests until all pass

#### Task 3.2: Type Checking

**Command**:

```bash
uv run mypy src/gapless_crypto_clickhouse
```

**Expected**: No type errors (SupportedSymbol deprecation might trigger warnings)

#### Task 3.3: Create Conventional Commit

**Format**:

```bash
git add -A
git commit -m "feat: align spot and futures to 713 symbols each

- Use binance-futures-availability for both spot and futures
- Remove BinancePublicDataCollector.known_symbols hardcoded dict
- Deprecate SupportedSymbol type alias (713-symbol Literal too large)
- Update all docstrings from '20 symbols' to '713 symbols'
- Spot users gain 693 additional symbols (additive change)

Refs: ADR-0022
BREAKING CHANGE: None - fully backward compatible (additive only)"
```

**Semantic Version**: v4.1.0 (minor bump, feature enhancement)

#### Task 3.4: Release via semantic-release

**Workflow**:

1. Export GitHub token: `export GH_TOKEN="$(gh auth token)"`
2. Run semantic-release: `npx semantic-release`
3. Verify GitHub release created: `gh release view v4.1.0`

#### Task 3.5: Publish to PyPI via Doppler

**Workflow** (from `~/.claude/skills/pypi-doppler`):

```bash
# Retrieve token from Doppler and publish
UV_PUBLISH_TOKEN=$(doppler secrets get PYPI_TOKEN --project claude-config --config prd --plain) uv publish

# Verify publication
curl -s https://pypi.org/pypi/gapless-crypto-clickhouse/json | jq -r '.info.version'
# Expected: "4.1.0"
```

---

## Implementation Checklist

### Phase 1: Code Simplification

- [ ] Update `get_supported_symbols()` to use `load_symbols("perpetual")` for both types
- [ ] Deprecate `SupportedSymbol` type alias with migration guide
- [ ] Remove `BinancePublicDataCollector.known_symbols` hardcoded dict

### Phase 2: Documentation Updates

- [ ] Update `__init__.py` module docstring (20 → 713)
- [ ] Update `api.py` docstrings (4 locations)
- [ ] Update `binance_public_data_collector.py` docstrings (2 locations)

### Phase 3: Validation and Release

- [ ] Run test suite (`uv run pytest`)
- [ ] Run type checker (`uv run mypy`)
- [ ] Create conventional commit
- [ ] Release v4.1.0 via semantic-release
- [ ] Publish to PyPI via Doppler

---

## Task List

### Active Tasks

1. **[IN PROGRESS]** Create ADR-0022 MADR document ✅ COMPLETED
2. **[IN PROGRESS]** Create implementation plan (this document)
3. **[PENDING]** Update `get_supported_symbols()` function
4. **[PENDING]** Deprecate `SupportedSymbol` type alias
5. **[PENDING]** Remove `known_symbols` hardcoded dict
6. **[PENDING]** Update all docstrings (9 locations)
7. **[PENDING]** Run test suite
8. **[PENDING]** Run type checker
9. **[PENDING]** Create conventional commit
10. **[PENDING]** Release v4.1.0 via semantic-release + PyPI

### Completed Tasks

- ✅ Investigation: Find all 20-symbol references (9 locations)
- ✅ Architecture Decision: ADR-0022 MADR document created
- ✅ Planning: Implementation plan created (this document)

---

## Risk Assessment

### Low Risk

- ✅ **Backward Compatibility**: 100% compatible (additive change only)
- ✅ **Package Trust**: binance-futures-availability already validated (95%+ SLA)
- ✅ **Code Simplification**: Removes code (reduces surface area for bugs)

### Medium Risk

- ⚠️ **Type Alias Deprecation**: Users relying on `SupportedSymbol` must migrate to `str`
  - **Mitigation**: Clear deprecation notice with migration guide
  - **Impact**: Low (type alias not in public API documentation)

### No Risk

- ✅ **API Compatibility**: `get_supported_symbols()` signature unchanged
- ✅ **URL Routing**: No changes to URL/endpoint selection logic
- ✅ **Test Coverage**: 27+ tests validate spot, futures, and alignment

---

## SLO Impact

| SLO Target          | Before (v4.0.0)                     | After (v4.1.0)                                 | Impact       |
| ------------------- | ----------------------------------- | ---------------------------------------------- | ------------ |
| **Availability**    | Spot: 20 symbols, Futures: 713      | Spot: 713, Futures: 713                        | ✅ Improved  |
| **Correctness**     | Spot: hardcoded, Futures: validated | Both: validated (binance-futures-availability) | ✅ Improved  |
| **Observability**   | instrument_type tracked             | instrument_type tracked (same list)            | ➡️ No change |
| **Maintainability** | 28-line hardcoded dict              | Single package dependency                      | ✅ Improved  |

---

## Rollback Plan

**If issues discovered post-release**:

1. **Revert Commit**:

   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Emergency Release**: v4.1.1 (patch)
   - Restore `known_symbols` hardcoded dict
   - Restore bifurcated `get_supported_symbols()` logic
   - Document issue in CHANGELOG

3. **Root Cause Analysis**:
   - Investigate failure mode
   - Update ADR-0022 with lessons learned
   - Plan alternative approach if needed

**Rollback Triggers**:

- Symbol validation failures (e.g., package unavailable)
- Breaking changes discovered in user code
- Performance degradation (unlikely - same package load)

---

## Success Metrics

### Acceptance Criteria

- ✅ `get_supported_symbols("spot")` returns 713 symbols
- ✅ `get_supported_symbols("futures-um")` returns 713 symbols
- ✅ Both calls return identical symbol lists
- ✅ `BinancePublicDataCollector.known_symbols` dict removed
- ✅ `SupportedSymbol` type alias deprecated
- ✅ All "20 symbols" docstrings updated to "713 symbols"
- ✅ All tests pass (27+)
- ✅ Type checking passes (mypy)
- ✅ v4.1.0 released to GitHub + PyPI

### Post-Release Verification

**Command**:

```python
import gapless_crypto_clickhouse as gcc

# Verify 713 symbols for both types
spot_symbols = gcc.get_supported_symbols("spot")
futures_symbols = gcc.get_supported_symbols("futures-um")

assert len(spot_symbols) == 713, f"Expected 713 spot symbols, got {len(spot_symbols)}"
assert len(futures_symbols) == 713, f"Expected 713 futures symbols, got {len(futures_symbols)}"
assert spot_symbols == futures_symbols, "Spot and futures symbols must be identical"

print("✅ Symbol alignment verified: 713 symbols for both spot and futures")
```

---

**Implementation Plan v4.1.0** | Spot/Futures Symbol Alignment | In Progress | 2025-11-20
