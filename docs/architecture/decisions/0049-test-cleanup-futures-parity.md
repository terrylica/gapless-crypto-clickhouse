# ADR-0049: Test Suite Cleanup and UM Futures Parity

## Status

Accepted

## Context

After completing ADR-0048 (Hardcode Audit), the test suite showed:

- **529 passed, 3 skipped, 21 warnings**

Investigation by 9 sub-agents revealed:

- 2 of 3 skipped tests are 100% redundant (covered by integration tests)
- 1 skipped test (futures) has unique coverage but was hardcoded to skip
- 67% of warnings come from deprecated `index_type` parameter tests
- No comprehensive test suite for UM-margined perpetual futures exists

**Business Requirement**: Complete compatibility between spot and UM-margined perpetual futures is critical for production trading systems.

## Decision

### Remove Redundancy

Delete tests that provide zero unique coverage:

- `test_binance_collector.py:71-109` - 100% covered by `test_integration.py`
- `test_simple_api.py:213-276` - stale DatetimeIndex assertion
- All `index_type` parameter tests - deprecated per ADR-0023, removed in v3.0.0

### Create Comprehensive Futures Test Suite

Create `tests/test_futures_um.py` mirroring all spot test coverage:

- Data collection from Binance futures CDN
- Query API with `instrument_type="futures-um"`
- Gap detection and filling for futures
- Spot/futures data isolation validation
- `funding_rate` column validation (futures-specific)

### Fix Remaining Warnings

- Update timeframe constants import path (ADR-0048 migration)
- Fix Arrow NA/nan comparison (pandas 3.x compatibility)
- Replace dynamic dates with explicit ranges
- Remove accidental `return` statement in validation test

## Consequences

### Positive

- **Futures parity**: Complete test coverage for UM-margined futures
- **Warning reduction**: 21 → ~3 warnings (85% reduction)
- **Test clarity**: Remove 200+ lines of redundant/deprecated tests
- **Maintainability**: Cleaner test suite with clear boundaries

### Negative

- **Initial effort**: Creating comprehensive futures test suite (~200-300 lines)
- **CI time**: Additional futures tests increase CI duration

## Implementation

**Plan Document**: [docs/development/plan/0049-test-cleanup-futures-parity/plan.md](/docs/development/plan/0049-test-cleanup-futures-parity/plan.md)

**Global Plan**: [docs/development/plan/0049-test-cleanup-futures-parity/global-plan.md](/docs/development/plan/0049-test-cleanup-futures-parity/global-plan.md)

## References

- ADR-0023: Apache Arrow Migration (RangeIndex default)
- ADR-0048: Hardcode Audit and Refactoring
- CLAUDE.md: 715 validated USDT-margined futures symbols
