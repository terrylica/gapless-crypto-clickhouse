# mise Toolchain Implementation - Design Specification

**ADR**: [0051-mise-toolchain-implementation](/docs/architecture/decisions/0051-mise-toolchain-implementation.md)

**Date**: 2025-12-10

## Overview

Implement full mise toolchain for gapless-crypto-clickhouse following the `gapless-deribit-clickhouse` exemplar pattern. This provides unified tool management, environment configuration, and task orchestration.

## Architecture

```
mise Toolchain Architecture

                                      ┌−−−−−−−−−−−−−−−−−−−−−−−−−−−┐
                                      ╎                           ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │       .env file       │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎                           ╎
                                      └−−−−−−−−−−−−−−−−−−−−−−−−−−−┘
                                          │
                                          │ GCCH_MODE
                                          ∨
                                      ┌−−−−−−−−−−−−−−−−−−−−−−−−−−−┐
                                      ╎ mise tasks:               ╎
                                      ╎                           ╎
                                      ╎ ╭───────────────────────╮ ╎
                                      ╎ │       ch-start        │ ╎
                                      ╎ ╰───────────────────────╯ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │      local-init       │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │    validate-local     │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
┌−−−−−−−−−−−−−−−−−−−−−┐               ╎   │                       ╎
╎ Credentials:        ╎               ╎   │                       ╎
╎                     ╎               ╎   ∨                       ╎
╎ ┌─────────────────┐ ╎  production   ╎ ┌───────────────────────┐ ╎
╎ │ Doppler wrapper │ ╎ ────────────> ╎ │    validate-cloud     │ ╎
╎ └─────────────────┘ ╎               ╎ └───────────────────────┘ ╎
╎                     ╎               ╎   │                       ╎
└−−−−−−−−−−−−−−−−−−−−−┘               ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ╭───────────────────────╮ ╎
                                      ╎ │        ch-stop        │ ╎
                                      ╎ ╰───────────────────────╯ ╎
                                      ╎                           ╎
                                      └−−−−−−−−−−−−−−−−−−−−−−−−−−−┘
                                      ┌−−−−−−−−−−−−−−−−−−−−−−−−−−−┐
                                      ╎ mise install:             ╎
                                      ╎                           ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │     python = "3"      │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │     uv = "latest"     │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │ clickhouse = "latest" │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎   │                       ╎
                                      ╎   │                       ╎
                                      ╎   ∨                       ╎
                                      ╎ ┌───────────────────────┐ ╎
                                      ╎ │    node = "latest"    │ ╎
                                      ╎ └───────────────────────┘ ╎
                                      ╎                           ╎
                                      └−−−−−−−−−−−−−−−−−−−−−−−−−−−┘
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "mise Toolchain Architecture"; flow: south; }

( mise install:
  [python = "3"]
  [uv = "latest"]
  [clickhouse = "latest"]
  [node = "latest"]
)

( mise tasks:
  [ch-start] { shape: rounded; }
  [local-init]
  [validate-local]
  [validate-cloud]
  [ch-stop] { shape: rounded; }
)

( Credentials:
  [.env file]
  [Doppler wrapper]
)

[python = "3"] -> [uv = "latest"]
[uv = "latest"] -> [clickhouse = "latest"]
[clickhouse = "latest"] -> [node = "latest"]

[ch-start] -> [local-init]
[local-init] -> [validate-local]
[validate-local] -> [validate-cloud]
[validate-cloud] -> [ch-stop]

[.env file] -- GCCH_MODE --> [ch-start]
[Doppler wrapper] -- production --> [validate-cloud]
```

</details>

## Implementation Details

### 1. `.mise.toml` Structure

```toml
# ADR-0051: mise toolchain implementation
min_version = "2024.9.5"

[env]
_.python.venv = { path = ".venv", create = true }
_.file = '.env'
GCCH_MODE = "auto"
CLICKHOUSE_DATABASE = "default"
CLICKHOUSE_LOCAL_HOST = "localhost"
CLICKHOUSE_LOCAL_PORT = "8123"
CLICKHOUSE_DATA_DIR = "{{config_root}}/tmp/clickhouse/data"
CLICKHOUSE_LOG_DIR = "{{config_root}}/tmp/clickhouse/logs"
CLICKHOUSE_PID_FILE = "{{config_root}}/tmp/clickhouse/clickhouse.pid"

[tools]
python = "3"
uv = "latest"
clickhouse = "latest"
node = "latest"

[tasks]
# ~40 tasks organized by category
```

### 2. Task Categories

| Category   | Tasks                                            | Purpose                      |
| ---------- | ------------------------------------------------ | ---------------------------- |
| Core       | install, test, lint, format                      | Development workflow         |
| ClickHouse | ch-start, ch-stop, ch-status, ch-logs, ch-client | Server lifecycle             |
| Schema     | db-init, local-init, local-validate              | Database setup               |
| Validation | validate-local, validate-cloud, validate-full    | E2E validation               |
| Production | validate-production                              | Doppler-wrapped cloud access |

### 3. Task Dependency Chains

**Development Setup:**

```
dev → ch-start → _ch-dirs
    → local-init → _check-local-server
                 → [depends_post] local-validate
```

**Full Validation:**

```
validate-full
├── _check-binance-cdn
├── _check-binance-api
├── validate-local (full local chain)
├── validate-cloud (full cloud chain)
└── validate-gap-filling (ADR-0041)
```

### 4. FINAL Optimization (connection.py)

**Location**: `src/gapless_crypto_clickhouse/clickhouse/connection.py`

**Change**:

```python
# Before
settings={
    "max_block_size": 100000,
}

# After
settings={
    "max_block_size": 100000,
    # ADR-0034: Partition-aware FINAL optimization
    # Reduces overhead from 10-30% to 2-5%
    "do_not_merge_across_partitions_select_final": 1,
}
```

### 5. Credential Strategy

| Context    | Method                                           |
| ---------- | ------------------------------------------------ |
| Local dev  | `_.file = '.env'` auto-loads credentials         |
| Cloud      | `GCCH_MODE=cloud` + environment variables        |
| Production | `mise run validate-production` (Doppler wrapper) |

## Files to Modify

| File                                                     | Action | Purpose                      |
| -------------------------------------------------------- | ------ | ---------------------------- |
| `.mise.toml`                                             | CREATE | Full toolchain configuration |
| `src/gapless_crypto_clickhouse/clickhouse/connection.py` | MODIFY | Add FINAL optimization       |
| `CLAUDE.md`                                              | UPDATE | Document mise workflow       |
| `.github/workflows/production-validation.yml`            | KEEP   | Retain for scheduled cron    |

## Verification Steps

1. `mise install` - Installs all tools including ClickHouse
2. `mise run ch-start` - Starts local ClickHouse server
3. `mise run local-init` - Initializes database schema
4. `mise run validate-local` - Runs local E2E validation
5. `mise run ch-stop` - Stops ClickHouse server

## Success Criteria

- [ ] `mise install` completes without errors
- [ ] `mise run ch-start` starts ClickHouse on localhost:8123
- [ ] `mise run validate-local` passes all tests
- [ ] FINAL optimization reduces query overhead (measurable via EXPLAIN)
- [ ] GitHub Actions cron continues to work (production-validation.yml)
