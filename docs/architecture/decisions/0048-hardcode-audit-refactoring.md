# ADR-0048: Hardcode Audit and Refactoring

## Status

Implemented

## Context

Following ADR-0046 (Semantic Constants Abstraction) and ADR-0047 (Code Hardcode Audit Skill), an automated audit of the codebase revealed 100+ hardcoded values requiring refactoring:

| Category             | Tool         | Findings | Severity |
| -------------------- | ------------ | -------- | -------- |
| Hardcoded Timeframes | Semgrep      | ~80      | Medium   |
| Magic Numbers        | Ruff PLR2004 | ~30      | High     |
| HTTP Status Codes    | Ruff PLR2004 | 5        | Low      |

**Key issues identified**:

1. Duplicate `interval_map` definitions in 6 files
2. Hardcoded CSV column counts (11, 12, 6)
3. Timestamp boundary magic numbers (milliseconds/microseconds ranges)
4. HTTP status codes (200, 304) not using centralized constants

## Decision

Refactor all identified hardcodes following ADR-0046 patterns:

### Phase 1: HTTP Status Codes

Replace hardcoded 200/304 with existing `HTTP_OK`/`HTTP_NOT_MODIFIED` constants.

### Phase 2: Magic Numbers

Add new constants to `constants/binance.py`:

- CSV column counts: `CSV_COLUMNS_SPOT_OUTPUT`, `CSV_COLUMNS_BINANCE_RAW`
- Timestamp boundaries: `TIMESTAMP_MILLISECONDS_MIN/MAX`, `TIMESTAMP_MICROSECONDS_MIN/MAX`
- Column indices: `CSV_INDEX_*` for positional access

### Phase 3: Timeframe Consolidation

Move `utils/timeframe_constants.py` → `constants/timeframes.py`:

- Add `Timeframe` Literal type for IDE autocomplete
- Add `TIMEFRAME_TO_MILLISECONDS` derived map for REST API
- Remove duplicate `interval_map` definitions from consumer files

### Phase 4: Type Safety

Update function signatures to use `Timeframe` Literal type.

## Consequences

### Positive

- Zero hardcoded values detectable by `code-hardcode-audit` skill
- Type-safe timeframe handling with IDE autocomplete
- Single source of truth for CSV format, timestamp validation

### Negative

- Increased import statements in consumer files
- Migration effort for existing interval_map consumers

## References

- ADR-0046: Semantic Constants Abstraction
- ADR-0047: Code Hardcode Audit Skill
- Plan: `docs/development/plan/0048-hardcode-audit-refactoring/plan.md`
