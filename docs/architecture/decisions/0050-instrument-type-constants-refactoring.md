# ADR-0050: Instrument Type Constants Refactoring

## Status

Accepted

## Context

The codebase has inconsistent handling of `instrument_type` values across layers:

- **API layer** accepts: `"spot"`, `"futures-um"`
- **Internal layers** normalize `"futures-um"` to `"futures"` before DB storage
- **Schema comment** claims `"futures-um"` but code stores `"futures"`
- **Tests** are confused, accepting both values inconsistently

This prevents clean addition of `"futures-cm"` (COIN-margined futures) support.

### SLO Focus

- **Correctness**: Consistent instrument_type values across all layers
- **Maintainability**: Centralized constants following ADR-0048 pattern
- **Observability**: Clear distinction between API-facing and stored values

## Decision

1. **Store literal API values**: Remove normalization, store `"futures-um"` exactly as received
2. **Centralize constants**: Add `VALID_INSTRUMENT_TYPES` to `constants/binance.py`
3. **Strict test assertions**: Tests assert exact DB value, no lenient sets
4. **Prepare for futures-cm**: Define constant but don't implement pipeline

## Consequences

### Positive

- Clean futures-cm addition (just add to constants)
- Single source of truth for instrument types
- Tests catch normalization bugs
- Schema comment matches stored values

### Negative

- Existing data with `"futures"` requires migration (if any exists)
- Breaking change for code expecting `"futures"` in DB

## Implementation Plan

See: [docs/development/plan/0050-instrument-type-constants-refactoring/plan.md](/docs/development/plan/0050-instrument-type-constants-refactoring/plan.md)

## References

- ADR-0021: UM Futures Support (introduced `futures-um`)
- ADR-0046: Semantic Constants Abstraction
- ADR-0048: Hardcode Audit Refactoring (timeframe constants pattern)
