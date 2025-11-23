# ADR-0032: Binance Dual Notation Handling for Monthly Timeframe

**Status**: Accepted

**Date**: 2025-01-22

**Deciders**: Development Team

**Context**: Follow-up to ADR-0031 (comprehensive validation)

## Context and Problem Statement

During comprehensive validation (ADR-0031), we discovered that Binance uses different notation for the monthly timeframe across its two data systems:

- **Public Data Repository** (data.binance.vision): Uses `"1mo"` for monthly data files
- **REST API** (api.binance.com/api/v3/klines): Uses `"1M"` for monthly interval parameter

This dual notation is intentional and system-specific. Our implementation correctly handles this via `TIMEFRAME_TO_BINANCE_INTERVAL` mapping, but tests incorrectly expected identity mapping for all timeframes.

## Decision Drivers

- **Correctness**: Implementation must work with both Binance systems
- **Simplicity**: Avoid over-engineering for a single special case
- **Maintainability**: Clear documentation prevents future confusion
- **Test Coverage**: Tests must validate dual notation, not assume identity mapping

## Considered Options

1. **Status Quo (Dictionary-based mapping)** - Keep simple `TIMEFRAME_TO_BINANCE_INTERVAL` dictionary
2. **Explicit Configuration Objects** - Use dataclasses to represent dual notation
3. **Pydantic Enum with Field Validator** - Type-safe models with validation
4. **Runtime Validator** - Add validation logic to detect mismatches
5. **Helper Functions** - Add `to_api_interval()` and `to_public_data_path()` utilities

## Decision Outcome

Chosen option: **Status Quo with enhanced documentation and test fixes**

**Rationale**:

- Current implementation already works correctly
- Only 1 out of 16 timeframes has dual notation (`1mo` → `1M`)
- Other exotic timeframes (3d, 1w) use identity mapping
- Dictionary lookups are O(1) and simple
- Pydantic would over-engineer for marginal benefit
- No API surface changes needed

**Changes Required**:

1. **Fix test bug**: `test_binance_interval_mapping_completeness()` incorrectly expects identity mapping for all timeframes
2. **Add dual notation test**: Explicitly validate `1mo` → `1M` mapping with empirical evidence
3. **Update documentation**: Add module docstring explaining dual notation architecture
4. **Update timeframe counts**: Tests reference "13 timeframes" but implementation now has 16

### Positive Consequences

- **Zero API changes**: Backward compatible, no breaking changes
- **Empirically validated**: Tests verify against live Binance endpoints
- **Clear documentation**: Future developers understand dual notation is intentional
- **Simple maintenance**: Dictionary-based approach easy to understand and modify

### Negative Consequences

- **Special case handling**: `1mo` requires exception in test logic
- **Documentation burden**: Must maintain comments explaining dual notation

## Empirical Validation

### Public Data Repository (data.binance.vision)

```bash
# ✅ Accepts "1mo"
curl -I "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1mo/..."
HTTP/1.1 200 OK

# ❌ Rejects "1M"
curl -I "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1M/..."
HTTP/1.1 404 Not Found
```

### REST API (api.binance.com)

```bash
# ✅ Accepts "1M"
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1M&limit=1"
[1735689600000,"96666.00000000","96827.30000000",...]

# ❌ Rejects "1mo"
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1mo&limit=1"
{"code":-1120,"msg":"Invalid interval."}
```

### Other Exotic Timeframes (Identity Mapping)

```bash
# 3d - Both systems accept "3d"
curl -I "https://data.binance.vision/.../3d/..." → HTTP 200 ✅
curl "https://api.binance.com/api/v3/klines?interval=3d" → HTTP 200 + Data ✅

# 1w - Both systems accept "1w"
curl -I "https://data.binance.vision/.../1w/..." → HTTP 200 ✅
curl "https://api.binance.com/api/v3/klines?interval=1w" → HTTP 200 + Data ✅
```

**Conclusion**: Only `1mo` has dual notation. All other exotic timeframes use consistent notation.

## Implementation

### Current Implementation (Correct)

```python
# src/gapless_crypto_clickhouse/utils/timeframe_constants.py
TIMEFRAME_TO_BINANCE_INTERVAL: Dict[str, str] = {
    # ... standard timeframes (identity mapping) ...
    "3d": "3d",   # Identity mapping
    "1w": "1w",   # Identity mapping
    "1mo": "1M",  # Dual notation for REST API compatibility
}
```

### Test Fixes Required

```python
# tests/test_timeframe_constants.py (lines 110-115)
# BEFORE (WRONG - assumes all mappings are identity)
for timeframe in TIMEFRAME_TO_MINUTES.keys():
    assert TIMEFRAME_TO_BINANCE_INTERVAL[timeframe] == timeframe

# AFTER (CORRECT - handles 1mo exception)
for timeframe in TIMEFRAME_TO_MINUTES.keys():
    expected = "1M" if timeframe == "1mo" else timeframe
    assert TIMEFRAME_TO_BINANCE_INTERVAL[timeframe] == expected
```

### New Test (Dual Notation Validation)

```python
def test_binance_monthly_dual_notation(self):
    """Verify 1mo→1M mapping for REST API compatibility.

    Binance uses different notation for monthly timeframe:
    - Public Data: "1mo" (data.binance.vision)
    - REST API: "1M" (api.binance.com/api/v3/klines)

    This is intentional and empirically validated against live endpoints.
    """
    assert TIMEFRAME_TO_BINANCE_INTERVAL["1mo"] == "1M"
```

## Links

- Related: ADR-0031 (comprehensive validation - identified this issue)
- Implementation Plan: `docs/development/plan/0032-binance-dual-notation/plan.md`
- Test File: `tests/test_timeframe_constants.py`
- Constants Module: `src/gapless_crypto_clickhouse/utils/timeframe_constants.py`
