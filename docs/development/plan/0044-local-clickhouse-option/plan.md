# Plan 0044: Local ClickHouse Deployment Option

**ADR**: [ADR-0044](../../../architecture/decisions/0044-local-clickhouse-option.md)

**Status**: Done (pending commit)

**Author**: Claude Code

**Last Updated**: 2025-11-26

---

## Overview

Enable local ClickHouse as an alternative deployment mode for development, backtesting, and offline scenarios while maintaining ClickHouse Cloud as the production recommendation.

### Goals

1. Support dual deployment modes (Cloud and Local)
2. Enable AI coding agents to discover local option via probe.py/llms.txt
3. Validate with real Binance data (Spot + Futures UM)
4. Zero SQL migration between modes (identical dialect)

### Non-Goals

- Bundle ClickHouse binary in PyPI wheel (467MB exceeds 100MB limit)
- Replace ClickHouse Cloud as production recommendation
- Support QuestDB/DuckDB as alternatives (research complete, ClickHouse LOCAL selected)

---

## Context

### Problem

ADR-0043's Cloud-only policy blocks users who:

- Lack Cloud credentials
- Need offline development
- Want faster backtesting (50-100x vs Cloud round-trip)
- Want to evaluate package before Cloud commitment

### Research Summary (13 Agents)

| Criterion        | ClickHouse LOCAL | QuestDB | DuckDB | Redis |
| ---------------- | ---------------- | ------- | ------ | ----- |
| Multi-process    | Yes              | Yes     | No     | Yes   |
| SQL completeness | Full             | Limited | Full   | None  |
| Query latency    | 50ms             | 25ms    | 250ms  | 5-10s |
| Window functions | Yes              | No      | Yes    | No    |
| ClickHouse SQL   | Native           | No      | No     | No    |

**Decision**: ClickHouse LOCAL - identical SQL to Cloud, full feature parity.

### Semantic Constants

```python
# Environment Variables
ENV_GCCH_MODE = "GCCH_MODE"
ENV_CLICKHOUSE_HOST = "CLICKHOUSE_HOST"
ENV_CLICKHOUSE_HTTP_PORT = "CLICKHOUSE_HTTP_PORT"

# Mode Values
MODE_LOCAL = "local"
MODE_CLOUD = "cloud"
MODE_AUTO = "auto"

# Default Ports
PORT_LOCAL_HTTP = 8123
PORT_CLOUD_HTTP = 8443

# Local Host Indicators
LOCAL_HOSTS = ("localhost", "127.0.0.1", "")
```

---

## Task List

| #   | Task                  | Status  | Notes                                                                                                         |
| --- | --------------------- | ------- | ------------------------------------------------------------------------------------------------------------- |
| 1   | Create ADR-0044       | Done    | MADR format                                                                                                   |
| 2   | Create plan directory | Done    | Google Design Doc format                                                                                      |
| 3   | Update llms.txt       | Done    | Deployment Modes section added                                                                                |
| 4   | Update probe.py       | Done    | 4 new functions: get_deployment_modes, get_current_mode, get_local_installation_guide, check_local_clickhouse |
| 5   | Update config.py      | Done    | Dual-mode support with GCCH_MODE env var                                                                      |
| 6   | Create skill          | Done    | skills/clickhouse-local-setup/SKILL.md                                                                        |
| 7   | Create E2E tests      | Done    | tests/test_local_clickhouse_e2e.py with real Binance data                                                     |
| 8   | Run validation        | Done    | 60 tests pass (26 config + 34 probe)                                                                          |
| 9   | Commit and release    | Pending | Semantic versioning                                                                                           |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ADR-0044 Local ClickHouse Option                       │
│                         Dual Deployment Mode                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐    ┌─────────────────────────────────┐
│         Cloud Mode (Default)         │    │         Local Mode              │
├─────────────────────────────────────┤    ├─────────────────────────────────┤
│ GCCH_MODE=cloud OR auto-detected    │    │ GCCH_MODE=local                 │
│ CLICKHOUSE_HOST=*.clickhouse.cloud  │    │ CLICKHOUSE_HOST=localhost       │
│ Port: 8443 (HTTPS)                  │    │ Port: 8123 (HTTP)               │
│ Secure: True (TLS)                  │    │ Secure: False                   │
│ Credentials: Doppler/env            │    │ Credentials: Optional           │
└─────────────────────────────────────┘    └─────────────────────────────────┘
                │                                        │
                ▼                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         query_ohlcv() API                                   │
│                    (Identical interface both modes)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  from gapless_crypto_clickhouse import query_ohlcv                          │
│  df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-06-30")             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      AI Agent Discovery Layer                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  llms.txt              │  probe.py                                          │
│  ├── Deployment Modes  │  ├── get_deployment_modes()                        │
│  ├── Cloud Mode        │  ├── get_current_mode()                            │
│  ├── Local Mode        │  ├── get_local_installation_guide()                │
│  └── Installation      │  └── check_local_clickhouse()                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### config.py Mode Detection

```python
@classmethod
def from_env(cls) -> "ClickHouseConfig":
    mode = os.environ.get("GCCH_MODE", "auto").lower()

    if mode == "local":
        return cls._from_env_local()
    elif mode == "cloud":
        return cls._from_env_cloud()
    else:  # auto
        host = os.environ.get("CLICKHOUSE_HOST", "")
        if host in LOCAL_HOSTS:
            return cls._from_env_local()
        return cls._from_env_cloud()
```

### probe.py Functions

| Function                         | Purpose                                |
| -------------------------------- | -------------------------------------- |
| `get_deployment_modes()`         | List available modes with descriptions |
| `get_current_mode()`             | Detect active mode from environment    |
| `get_local_installation_guide()` | Platform-specific install steps        |
| `check_local_clickhouse()`       | Detect if local ClickHouse is running  |

### E2E Test Data Sources

| Market     | URL Pattern                                                              |
| ---------- | ------------------------------------------------------------------------ |
| Spot       | `https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/`       |
| Futures UM | `https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/` |

---

## Validation Strategy

### Layer 1: Unit Tests (probe.py)

- Mode detection logic
- Installation guide generation
- No network required

### Layer 2: Integration Tests (real data)

- Download real BTCUSDT spot data from Binance CDN
- Download real BTCUSDT futures UM data from Binance CDN
- Ingest to local ClickHouse
- Query with FINAL (deduplication)
- Verify OHLC constraints

### Run Commands

```bash
# Run local ClickHouse E2E tests
GCCH_MODE=local uv run pytest tests/test_local_clickhouse_e2e.py -v

# Skip automatically if ClickHouse not installed
uv run pytest tests/test_local_clickhouse_e2e.py -v
```

---

## SLOs

| Metric          | Target                                            |
| --------------- | ------------------------------------------------- |
| Availability    | Tests skip gracefully if ClickHouse not installed |
| Correctness     | Real Binance data validates OHLC constraints      |
| Observability   | pytest logs mode detection and connection status  |
| Maintainability | Single config.py change point for mode logic      |

---

## Risk Assessment

| Risk                           | Likelihood | Impact | Mitigation                       |
| ------------------------------ | ---------- | ------ | -------------------------------- |
| Local ClickHouse not installed | High       | Low    | pytest.skip() with clear message |
| Port conflict on 8123          | Medium     | Low    | Clear error message              |
| Schema mismatch                | Low        | High   | Use identical schema in tests    |

---

## Success Criteria

- [x] llms.txt documents both deployment modes
- [x] probe.py exposes 4 new functions
- [x] config.py supports GCCH_MODE=local|cloud|auto
- [x] E2E tests pass with real Binance spot + futures data
- [x] Tests skip gracefully when ClickHouse not installed
- [x] No regression in existing Cloud-mode tests (60 tests pass)
