# Semantic Constants Abstraction

**ADR**: [0046](../../architecture/decisions/0046-semantic-constants-abstraction.md)
**Status**: Completed
**Last Updated**: 2025-11-26

## Context

### Problem Statement

The gapless-crypto-clickhouse codebase has ~25 semantic constants with ~40% duplication:

| Category         | Duplicated Constants               | Files                                         |
| ---------------- | ---------------------------------- | --------------------------------------------- |
| Deployment Modes | MODE_LOCAL, MODE_CLOUD, MODE_AUTO  | config.py, probe.py                           |
| Environment Vars | ENV_GCCH_MODE, ENV_CLICKHOUSE_HOST | config.py, probe.py                           |
| Ports            | PORT_LOCAL_HTTP (8123)             | config.py, probe.py, skill scripts, E2E tests |
| API URLs         | SPOT_API_URL, FUTURES_API_URL      | rest_client.py, validate_gap_filling.py       |

### Investigation Summary (9 Sub-Agents)

| Batch | Agent               | Finding                                                    |
| ----- | ------------------- | ---------------------------------------------------------- |
| 1     | Constants Inventory | 25 constants, 40% duplicated across 7 files                |
| 1     | ADR-0045 Compliance | 85% compliant, needs centralization                        |
| 1     | Config Module       | config.py appropriate as central location                  |
| 2     | Type Safety         | Literal/Enum patterns exist; deployment modes lack Final[] |
| 2     | Best Practices      | timeframe_constants.py is gold standard                    |
| 2     | Magic Numbers       | ~40 magic numbers identified                               |
| 3     | Minimal Change      | 1 file change possible (probe.py only)                     |
| 3     | Clean Architecture  | Full constants.py module design                            |
| 3     | Gradual Migration   | 5-phase PR strategy                                        |

### User Decisions

| Decision      | Choice                                                    |
| ------------- | --------------------------------------------------------- |
| Scope         | Full Codebase                                             |
| Architecture  | Domain Modules (deployment, network, binance, validation) |
| Type Safety   | Full (Final[] + Literal + TypeAlias + assertions)         |
| Skill Scripts | Keep Local (intentional isolation)                        |
| PR Strategy   | Single atomic PR                                          |
| Public API    | Export from top-level **init**.py                         |

## Plan

### Architecture

```
src/gapless_crypto_clickhouse/
├── constants/
│   ├── __init__.py           # Re-exports all constants
│   ├── deployment.py         # Modes, env vars, hosts, ports
│   ├── network.py            # Timeouts, concurrency, HTTP codes
│   └── binance.py            # API URLs, chunk sizes
├── validation/
│   └── constants.py          # Statistical thresholds
```

### Module Specifications

#### constants/deployment.py

- DeploymentMode = Literal["local", "cloud", "auto"]
- MODE_LOCAL, MODE_CLOUD, MODE_AUTO with Final[str]
- ENV_GCCH_MODE, ENV_CLICKHOUSE_HOST, etc.
- PORT_LOCAL_HTTP, PORT_LOCAL_NATIVE, PORT_CLOUD_HTTP, PORT_CLOUD_NATIVE
- Self-validating assertions

#### constants/network.py

- TIMEOUT_CONNECT, TIMEOUT_READ, TIMEOUT_WRITE, TIMEOUT_API
- MAX_CONCURRENT_DOWNLOADS, CONNECTION_POOL_SIZE
- HTTP_OK, HTTP_RATE_LIMITED, HTTP_IP_BANNED
- RETRY_MAX_ATTEMPTS, RETRY_BASE_DELAY

#### constants/binance.py

- InstrumentType = Literal["spot", "futures-um"]
- BINANCE_CDN_SPOT, BINANCE_CDN_FUTURES_UM
- BINANCE_API_SPOT, BINANCE_API_FUTURES
- API_CHUNK_SIZE, API_MAX_CHUNKS
- CDN_URL_BY_INSTRUMENT, API_URL_BY_INSTRUMENT mappings

#### validation/constants.py

- IQR_MULTIPLIER, IQR_LOWER_QUANTILE, IQR_UPPER_QUANTILE
- COVERAGE_LOW_THRESHOLD, COVERAGE_HIGH_THRESHOLD
- MAX_GAPS_BEFORE_ERROR

## Task List

| #   | Task                           | Status  | Notes                                         |
| --- | ------------------------------ | ------- | --------------------------------------------- |
| 1   | Create ADR-0046                | Done    | MADR format                                   |
| 2   | Create plan document           | Done    | Google Design Doc format                      |
| 3   | Create constants/deployment.py | Done    | Ports, modes, env vars, Final[]               |
| 4   | Create constants/network.py    | Done    | Timeouts, HTTP codes, retry config            |
| 5   | Create constants/binance.py    | Done    | API URLs, limits, InstrumentType              |
| 6   | Create constants/**init**.py   | Done    | Re-exports 67 constants                       |
| 7   | Create validation/constants.py | Done    | IQR, coverage thresholds                      |
| 8   | Update config.py               | Done    | Import from constants, backward compat        |
| 9   | Update probe.py                | Done    | Import from constants, remove duplicates      |
| 10  | Update rest_client.py          | Done    | Network + Binance imports                     |
| 11  | Update httpx_downloader.py     | Skipped | Not needed - uses constants via other modules |
| 12  | Update collectors              | Skipped | Not needed - uses constants via other modules |
| 13  | Update csv_validator.py        | Skipped | Not needed - uses constants via other modules |
| 14  | Update **init**.py             | Done    | Public API exports (6 deployment constants)   |
| 15  | Run validation suite           | Done    | 43 tests pass, ruff clean                     |

## Success Criteria

1. Zero constant duplication in config.py, probe.py
2. All constants have Final[] type annotations
3. DeploymentMode and InstrumentType Literal types available
4. Self-validating assertions run on module import
5. All existing tests pass
6. Top-level imports work: `from gapless_crypto_clickhouse import MODE_LOCAL`

## SLO Alignment

| SLO             | How Addressed                                         |
| --------------- | ----------------------------------------------------- |
| Availability    | Self-validating assertions catch misconfig at startup |
| Correctness     | Type safety prevents mode/port misuse                 |
| Observability   | Clear constant naming improves debugging              |
| Maintainability | Single source of truth eliminates sync bugs           |
