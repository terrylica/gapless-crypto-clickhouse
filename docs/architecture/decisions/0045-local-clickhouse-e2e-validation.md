# ADR-0045: Local ClickHouse E2E Validation Workflow

## Status

Accepted

## Date

2025-11-26

## Context

ADR-0044 introduced local ClickHouse as an alternative deployment mode. During implementation, a "show and tell" workflow emerged:

1. Start local ClickHouse (mise-installed)
2. Deploy production schema
3. Ingest real Binance data via `query_ohlcv()` API
4. Visualize in Play UI via Playwright
5. Capture evidence (screenshots, JSON, query results)

This workflow needs formalization into:

- Reusable skill scripts
- Automated pytest E2E tests
- Evidence capture for validation

### Constraints

| Constraint         | Rationale                                       |
| ------------------ | ----------------------------------------------- |
| Local-only (no CI) | mise ClickHouse not available in GitHub Actions |
| Fail hard          | Developers must have mise ClickHouse installed  |
| No Docker          | Uses native mise installation                   |
| subprocess.run()   | Clean separation between skill and tests        |

## Decision

Formalize the local ClickHouse E2E workflow as:

### Skill Architecture

Consolidate `clickhouse-local-setup` into `local-clickhouse` skill with scripts:

```
skills/local-clickhouse/
├── SKILL.md              # Installation + E2E workflow
└── scripts/
    ├── start-clickhouse.sh      # Start mise ClickHouse
    ├── deploy-schema.sh         # Deploy schema (calls existing)
    ├── ingest-sample-data.py    # Ingest via query_ohlcv()
    ├── take-screenshot.py       # Playwright Play UI capture
    └── validate-data.py         # Query validation + JSON output
```

### pytest E2E Architecture

Update `tests/test_local_clickhouse_e2e.py`:

- Remove `pytest.skipif` → fail hard with `pytest.fail()`
- Add Playwright screenshot tests
- Add JSON evidence capture
- Invoke skill scripts via `subprocess.run()`

### Evidence Storage

```
tests/screenshots/           # gitignored
├── play-ui-{timestamp}.png  # Playwright captures
└── validation-{timestamp}.json  # Structured results
```

## Consequences

### Positive

- Reproducible local validation workflow
- Evidence capture for debugging
- Skill scripts usable standalone or via pytest
- Full circle: skill → pytest → skill

### Negative

- No CI validation (local-only)
- Requires mise ClickHouse installation

### Amends

- **ADR-0044**: Adds E2E validation layer to local ClickHouse support

## References

- ADR-0044: Local ClickHouse Option
- ADR-0038: Real Binance Data Validation (methodology)
