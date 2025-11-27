# ADR-0046: Semantic Constants Abstraction

## Status

Accepted

## Date

2025-11-26

## Context

The codebase has accumulated ~25 semantic constants across 7 files with ~40% duplication rate. Key issues:

1. **Critical Duplication**: `config.py` and `probe.py` define identical constants (MODE_LOCAL, MODE_CLOUD, ENV_GCCH_MODE, etc.)
2. **Magic Numbers**: ~40 hardcoded values scattered across collectors, validators, and REST clients
3. **Type Safety Gap**: No `Final[]` annotations, no `Literal` type constraints
4. **Inconsistent Imports**: Some files import from config.py, others define locally

The existing `timeframe_constants.py` demonstrates the gold standard pattern: single source of truth with derived mappings and self-validating assertions.

## Decision

Implement domain-specific constants modules following the `timeframe_constants.py` pattern:

```
src/gapless_crypto_clickhouse/
├── constants/
│   ├── __init__.py           # Re-exports all constants
│   ├── deployment.py         # Modes, env vars, hosts, ports (ADR-0044)
│   ├── network.py            # Timeouts, concurrency, HTTP status codes
│   └── binance.py            # API URLs, chunk sizes, rate limits
├── validation/
│   └── constants.py          # Statistical thresholds, coverage limits
```

Design principles:

- **Single Source of Truth**: Each constant defined exactly once
- **Full Type Safety**: `Final[]` annotations + `Literal` type aliases
- **Self-Validating**: Module-level assertions catch misconfigurations at import time
- **Domain Separation**: Network, deployment, API constants in separate modules
- **Public API Export**: Key constants exported from top-level `__init__.py`

## Consequences

### Positive

- Zero constant duplication in core package
- Type checker catches mode/port misuse at development time
- Self-validating assertions prevent configuration drift
- Clearer import semantics for SDK users

### Negative

- Additional modules to maintain
- Circular import risk (mitigated by clean dependency hierarchy)

### Neutral

- Skill scripts keep local constants (intentional isolation)
- Migration requires updating ~10 consumer files

## References

- ADR-0044: Local ClickHouse Option (deployment modes)
- ADR-0045: Local ClickHouse E2E Validation (skill script constants)
- `timeframe_constants.py`: Gold standard pattern
