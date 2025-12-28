# ADR-0051: mise Toolchain Implementation

## Status

Accepted

## Date

2025-12-10

## Context

The project currently lacks unified development tooling configuration. Developers must:

1. Manually install ClickHouse (Homebrew, source, or binary download)
2. Configure environment variables individually
3. Run validation workflows through separate scripts
4. Maintain Python virtual environments manually

### Investigation Summary (3 Agents)

| Component         | Current State                 | Gap Identified                  |
| ----------------- | ----------------------------- | ------------------------------- |
| mise config       | **No `.mise.toml` exists**    | Critical - no toolchain SSoT    |
| Local ClickHouse  | E2E scripts exist (ADR-0044)  | No lifecycle task orchestration |
| Connection config | ADR-0034 FINAL opt documented | **Not implemented in code**     |

### Exemplar Pattern: gapless-deribit-clickhouse

The sibling project `~/eon/gapless-deribit-clickhouse` demonstrates full mise integration:

- 50+ orchestrated tasks
- mise-managed ClickHouse (`clickhouse = "latest"`)
- `[env]` SSoT with `_.python.venv`, `_.file`
- Task dependency chains (`depends`, `depends_post`)
- Credential handling via Doppler wrapper tasks

## Decision

Implement full mise toolchain following `gapless-deribit-clickhouse` exemplar pattern:

### 1. Tool Management via mise

```toml
[tools]
python = "3"
uv = "latest"
clickhouse = "latest"  # mise-managed (replaces Homebrew)
node = "latest"        # for semantic-release
```

### 2. Environment Configuration SSoT

```toml
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
```

### 3. Task Orchestration Categories

| Category       | Tasks                                                         |
| -------------- | ------------------------------------------------------------- |
| Core           | install, test, lint, format                                   |
| ClickHouse     | ch-start, ch-stop, ch-status, ch-logs, ch-client              |
| Schema         | db-init, local-init, local-validate, cloud-validate           |
| Seeding        | seed-local, seed-cloud                                        |
| Validation     | validate-local, validate-cloud, validate-full                 |
| Production     | validate-production (Doppler wrapper)                         |
| Hidden Helpers | \_check-credentials,\_check-local-server, \_check-binance-cdn |

### 4. FINAL Optimization (ADR-0034 Implementation)

Add to `connection.py`:

```python
settings={
    "max_block_size": 100000,
    # ADR-0034: Partition-aware FINAL optimization
    # Reduces overhead from 10-30% to 2-5%
    "do_not_merge_across_partitions_select_final": 1,
}
```

### 5. GitHub Actions Strategy

| Workflow                  | Action | Rationale                        |
| ------------------------- | ------ | -------------------------------- |
| release.yml               | KEEP   | Semantic versioning automation   |
| production-validation.yml | KEEP   | Scheduled 6-hour cron monitoring |
| release-validation.yml    | KEEP   | Post-release observability       |

GitHub Actions retained for scheduled cron monitoring. Local mise tasks handle development workflows.

## Consequences

### Positive

- Single `mise install` command sets up complete development environment
- mise-managed ClickHouse ensures version consistency across developers
- Task orchestration provides discoverable, repeatable workflows
- `_.file = '.env'` enables flexible credential handling
- FINAL optimization reduces query overhead by 5-25%

### Negative

- Requires mise installation (minor friction for new developers)
- ~250 lines of `.mise.toml` configuration to maintain
- Two systems for CI (mise tasks local, GitHub Actions scheduled)

### Implements

- **ADR-0034**: FINAL optimization setting (previously documented, now implemented)
- **ADR-0044**: Local ClickHouse lifecycle via mise tasks
- **ADR-0045**: E2E validation integration with mise orchestration

## Implementation

### Files Modified

| File                                                     | Change                             |
| -------------------------------------------------------- | ---------------------------------- |
| `.mise.toml`                                             | Full toolchain configuration (NEW) |
| `src/gapless_crypto_clickhouse/clickhouse/connection.py` | Add FINAL optimization setting     |
| `CLAUDE.md`                                              | Document mise workflow             |

## References

- ADR-0034: Schema Optimization for Prop Trading (FINAL setting source)
- ADR-0044: Local ClickHouse as Alternative Deployment Mode
- ADR-0045: Local ClickHouse E2E Validation
- mise Configuration Skill: `Skill(itp:mise-configuration)`
- mise Tasks Skill: `Skill(itp:mise-tasks)`
