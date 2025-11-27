# ADR-0044: Local ClickHouse as Alternative Deployment Mode

## Status

Accepted

## Date

2025-11-26

## Context

ADR-0043 mandated ClickHouse Cloud as the single source of truth. However, users need deployment flexibility for specific use cases:

| Persona               | Need                                                      |
| --------------------- | --------------------------------------------------------- |
| No Cloud credentials  | Try package immediately without signup                    |
| Developer backtesting | Fast local queries (50-100x faster than Cloud round-trip) |
| Offline development   | Air-gapped environments, no network dependency            |
| Cost-conscious        | Avoid Cloud costs during experimentation                  |

### Investigation Summary (13 Agents)

Comprehensive evaluation of local database options:

| Database             | Multi-Process | Query Speed  | SQL/Indicators | PyPI Bundleable |
| -------------------- | ------------- | ------------ | -------------- | --------------- |
| Redis                | Yes           | 5-10s (OLTP) | None           | Yes             |
| DuckDB               | Single-writer | 250ms        | Full           | Yes             |
| chDB                 | Single-writer | 400ms        | Full           | 100MB limit     |
| QuestDB              | Yes           | 25ms         | Limited        | No              |
| **ClickHouse LOCAL** | **Yes**       | **50ms**     | **Full**       | **No**          |

**Key Finding**: ClickHouse LOCAL provides identical SQL dialect to Cloud, enabling zero-migration between environments.

## Decision

Support TWO deployment modes, selectable via `GCCH_MODE` environment variable:

- **Cloud mode** (default when `CLICKHOUSE_HOST` is remote): ClickHouse Cloud (production, multi-user)
- **Local mode** (when `GCCH_MODE=local` or `CLICKHOUSE_HOST=localhost`): Local ClickHouse installation

### Configuration

```bash
# Explicit local mode
export GCCH_MODE=local

# Auto-detection (localhost triggers local mode)
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_HTTP_PORT=8123
```

### Mode Detection Logic

```
GCCH_MODE=local → Local mode (explicit)
GCCH_MODE=cloud → Cloud mode (requires CLICKHOUSE_HOST)
GCCH_MODE=auto (default) →
  - CLICKHOUSE_HOST in (localhost, 127.0.0.1, "") → Local mode
  - CLICKHOUSE_HOST is remote hostname → Cloud mode
```

### AI Discoverability

Enable AI coding agents to discover deployment options:

- `llms.txt`: Document both modes with installation instructions
- `probe.py`: Expose `get_deployment_modes()`, `check_local_clickhouse()`

## Consequences

### Positive

- Users can start immediately without Cloud signup
- Same SQL, same schema, same API in both modes
- 50-100x faster queries for backtesting workloads
- Offline development enabled

### Negative

- Binary not bundleable in PyPI wheel (467MB)
- Requires server process management locally
- 2-4GB RAM minimum for local ClickHouse

### Amends

- **ADR-0043**: Relaxed from Cloud-only to Cloud-preferred with local option

## Implementation

### Files Modified

| File                                                 | Change                        |
| ---------------------------------------------------- | ----------------------------- |
| `src/gapless_crypto_clickhouse/llms.txt`             | Add Deployment Modes section  |
| `src/gapless_crypto_clickhouse/probe.py`             | Add introspection functions   |
| `src/gapless_crypto_clickhouse/clickhouse/config.py` | Support GCCH_MODE             |
| `skills/clickhouse-local-setup/SKILL.md`             | Claude Code skill (NEW)       |
| `tests/test_local_clickhouse_e2e.py`                 | Real Binance data tests (NEW) |

## References

- ADR-0043: ClickHouse Cloud-Only Policy (amended by this ADR)
- ADR-0038: Real Binance Data Validation (test methodology)
- ADR-0034: Schema Optimization for Prop Trading
