# ADR-0050: Instrument Type Constants Refactoring

**ADR**: [docs/architecture/decisions/0050-instrument-type-constants-refactoring.md](/docs/architecture/decisions/0050-instrument-type-constants-refactoring.md)

## Context

### Problem Statement

Instrument type handling is fragmented across 8+ files with:

- Inconsistent validation sets (`{"spot", "futures-um"}` vs `{"spot", "futures", "futures-um"}`)
- Hidden normalization (`futures-um` → `futures`) in query/loader layers
- Schema comment mismatch (says `futures-um`, stores `futures`)
- Test confusion (accepting multiple values)

### Decision

Store literal API values (`spot`, `futures-um`) without normalization. Centralize constants following ADR-0048 pattern.

### SLO Focus

- **Correctness**: Consistent values across layers
- **Maintainability**: Single source of truth for instrument types

## Task List

- [x] Create ADR-0050 and plan structure
- [x] Extend constants/binance.py with VALID_INSTRUMENT_TYPES
- [x] Update constants/**init**.py exports
- [x] Remove normalization in clickhouse_query.py (4 locations)
- [x] Remove normalization in clickhouse_bulk_loader.py
- [x] Update api.py to use centralized validation
- [x] Update binance_public_data_collector.py validation
- [x] Update universal_gap_filler.py validation
- [x] Fix test_futures_um.py assertions (strict futures-um)
- [x] Fix test_multi_symbol_isolation.py assertions
- [x] Fix test_clickhouse_query.py assertions
- [x] Update schema.sql comment
- [x] Run test suite validation (444 passed)

## Plan

## Overview

Centralize instrument type constants (`spot`, `futures-um`, `futures-cm`) following the ADR-0048 timeframe constants pattern. Remove normalization logic to store exact API values in ClickHouse, preparing for futures-cm support.

**Key Decisions**:

- Store `'futures-um'` literally in ClickHouse (not normalized to `'futures'`)
- Test assertions check DB value strictly (no lenient `{"futures", "futures-um"}` sets)
- Prepare for `'futures-cm'` without implementing pipeline yet

## Phase 1: Extend Constants Module

### File: `src/gapless_crypto_clickhouse/constants/binance.py`

Add after existing `InstrumentType` definition (line ~25):

```python
# =============================================================================
# INSTRUMENT TYPE CONSTANTS (ADR-0050)
# =============================================================================

# Individual constants for programmatic use
INSTRUMENT_SPOT: Final[str] = "spot"
INSTRUMENT_FUTURES_UM: Final[str] = "futures-um"
INSTRUMENT_FUTURES_CM: Final[str] = "futures-cm"  # Future support

# Validation sets
VALID_INSTRUMENT_TYPES: Final[FrozenSet[str]] = frozenset({
    INSTRUMENT_SPOT,
    INSTRUMENT_FUTURES_UM,
})
"""Valid instrument types for public API (O(1) membership testing)."""

IMPLEMENTED_INSTRUMENT_TYPES: Final[FrozenSet[str]] = frozenset({
    INSTRUMENT_SPOT,
    INSTRUMENT_FUTURES_UM,
})
"""Currently implemented instrument types (have working pipelines)."""

# Future: Add futures-cm to VALID but not IMPLEMENTED until pipeline ready
# VALID_INSTRUMENT_TYPES = frozenset({INSTRUMENT_SPOT, INSTRUMENT_FUTURES_UM, INSTRUMENT_FUTURES_CM})
```

Update existing `InstrumentType` Literal:

```python
InstrumentType = Literal["spot", "futures-um"]  # Keep as-is for now
# Future: InstrumentType = Literal["spot", "futures-um", "futures-cm"]
```

### File: `src/gapless_crypto_clickhouse/constants/__init__.py`

Add to exports:

```python
from .binance import (
    # ... existing exports ...
    INSTRUMENT_SPOT,
    INSTRUMENT_FUTURES_UM,
    INSTRUMENT_FUTURES_CM,
    VALID_INSTRUMENT_TYPES,
    IMPLEMENTED_INSTRUMENT_TYPES,
)
```

## Phase 2: Remove Normalization Logic

### File: `src/gapless_crypto_clickhouse/clickhouse_query.py`

**4 locations to fix** (lines 168-173, 280-285, 411-416, 570-575):

Before (repeated 4 times):

```python
# ADR-0021: Accept 'futures-um' and normalize to 'futures'
valid_types = {"spot", "futures", "futures-um"}
if instrument_type not in valid_types:
    raise ValueError(...)
instrument_type = "futures" if instrument_type == "futures-um" else instrument_type
```

After:

```python
from .constants import VALID_INSTRUMENT_TYPES

if instrument_type not in VALID_INSTRUMENT_TYPES:
    raise ValueError(
        f"Invalid instrument_type: '{instrument_type}'. "
        f"Must be one of: {sorted(VALID_INSTRUMENT_TYPES)}"
    )
# NO normalization - store exact API value
```

### File: `src/gapless_crypto_clickhouse/collectors/clickhouse_bulk_loader.py`

**Lines 129-138**:

Before:

```python
valid_types = {"spot", "futures", "futures-um"}
if instrument_type not in valid_types:
    raise ValueError(...)
self.instrument_type = "futures" if instrument_type == "futures-um" else instrument_type
```

After:

```python
from ..constants import VALID_INSTRUMENT_TYPES

if instrument_type not in VALID_INSTRUMENT_TYPES:
    raise ValueError(
        f"Invalid instrument_type: '{instrument_type}'. "
        f"Must be one of: {sorted(VALID_INSTRUMENT_TYPES)}"
    )
self.instrument_type = instrument_type  # NO normalization
```

### File: `src/gapless_crypto_clickhouse/api.py`

**Line 35**: Remove duplicate `InstrumentType` definition, import from constants
**Lines 140-147**: Use centralized `VALID_INSTRUMENT_TYPES`

### File: `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py`

**Lines 251-255**: Replace inline tuple with `VALID_INSTRUMENT_TYPES`

### File: `src/gapless_crypto_clickhouse/gap_filling/universal_gap_filler.py`

**Lines 123-127**: Replace inline tuple with `VALID_INSTRUMENT_TYPES`

## Phase 3: Fix Test Assertions (Strict DB Value)

### File: `tests/test_futures_um.py`

| Line    | Current                                      | Change To                                                         |
| ------- | -------------------------------------------- | ----------------------------------------------------------------- |
| 158-162 | `valid_values = {"futures-um", "um"}`        | `assert (df["instrument_type"] == "futures-um").all()`            |
| 239-243 | `valid_futures_types = {"futures-um", "um"}` | `assert (df["instrument_type"] == "futures-um").all()`            |
| 284-286 | `valid_futures_types = {"futures-um", "um"}` | `assert df_futures["instrument_type"].isin(["futures-um"]).all()` |
| 304     | `isin(["futures-um", "um"])`                 | `isin(["futures-um"])`                                            |

### File: `tests/test_multi_symbol_isolation.py`

**Line 103**: Keep `instrument_type="futures-um"` (already correct for API)
**Line 113**: Change `== "futures"` to `== "futures-um"` (strict DB value)

### File: `tests/test_clickhouse_query.py`

**Lines 74-77, 129-134**: Update tests to reject `"futures"` as invalid (only accept `"futures-um"`)

## Phase 4: Update Schema Comment

### File: `src/gapless_crypto_clickhouse/clickhouse/schema.sql`

**Line 22** - Already correct, but add clarifying comment:

```sql
instrument_type LowCardinality(String) CODEC(ZSTD(3)), -- 'spot', 'futures-um', or 'futures-cm' (ADR-0050)
```

## Phase 5: Validate Changes

Run test suite:

```bash
uv run pytest tests/test_futures_um.py tests/test_multi_symbol_isolation.py tests/test_clickhouse_query.py -v
```

## Critical Files Summary

| File                                   | Changes                                          |
| -------------------------------------- | ------------------------------------------------ |
| `constants/binance.py`                 | Add VALID_INSTRUMENT_TYPES, individual constants |
| `constants/__init__.py`                | Re-export new constants                          |
| `clickhouse_query.py`                  | Remove normalization (4 locations)               |
| `clickhouse_bulk_loader.py`            | Remove normalization (1 location)                |
| `api.py`                               | Use centralized validation                       |
| `binance_public_data_collector.py`     | Use centralized validation                       |
| `universal_gap_filler.py`              | Use centralized validation                       |
| `tests/test_futures_um.py`             | Strict assertions for 'futures-um'               |
| `tests/test_multi_symbol_isolation.py` | Expect 'futures-um' from DB                      |
| `tests/test_clickhouse_query.py`       | Reject 'futures' as invalid                      |
| `schema.sql`                           | Update comment                                   |

## Rollback Strategy

If tests fail after changes:

1. Check if existing ClickHouse data has `'futures'` stored (unlikely if DB fresh)
2. If data exists with `'futures'`, run migration: `UPDATE ohlcv SET instrument_type = 'futures-um' WHERE instrument_type = 'futures'`
3. Ultimate fallback: Re-add normalization temporarily

## Future: Adding futures-cm

When implementing futures-cm pipeline:

1. Add `INSTRUMENT_FUTURES_CM` to `VALID_INSTRUMENT_TYPES` (already defined)
2. Add to `IMPLEMENTED_INSTRUMENT_TYPES`
3. Add CDN/API URLs to `CDN_URL_BY_INSTRUMENT`, `API_URL_BY_INSTRUMENT`
4. Update `InstrumentType` Literal to include `"futures-cm"`
5. Create test suite `tests/test_futures_cm.py`

No other changes needed - centralized constants handle validation automatically.
