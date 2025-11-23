# Cross-Reference Consistency Audit (Clean Slate)

## Reference Statistics

- Total markdown link references: 279
- Valid references: 276
- Broken references: 3
- Potential issues found: 244
- Success rate: 98.9%

## Broken References

1. **File**: `docs/README.md` (line 20)
   - **References**: `PYPI_PUBLISHING_CONFIGURATION.yaml`
   - **Resolved to**: `/Users/terryli/eon/gapless-crypto-clickhouse/docs/PYPI_PUBLISHING_CONFIGURATION.yaml`
   - **Status**: Missing/Wrong Path

2. **File**: `docs/diagrams/README.md` (line 116)
   - **References**: `./docs/diagrams/01-collection-pipeline.mmd`
   - **Resolved to**: `/Users/terryli/eon/gapless-crypto-clickhouse/docs/diagrams/docs/diagrams/01-collection-pipeline.mmd`
   - **Status**: Missing/Wrong Path

3. **File**: `docs/diagrams/README.md` (line 146)
   - **References**: `./assets/collection-pipeline.png`
   - **Resolved to**: `/Users/terryli/eon/gapless-crypto-clickhouse/docs/diagrams/assets/collection-pipeline.png`
   - **Status**: Missing/Wrong Path

## Potential Issues

### Backtick Reference (232)

- `AGENTS.md` (line 5) → `api.py`
- `README.md` (line 1132) → `.metadata.json`
- `REFERENCE_VALIDATION_REPORT.md` (line 15) → `PYPI_PUBLISHING_CONFIGURATION.yaml`
- `REFERENCE_VALIDATION_REPORT.md` (line 16) → `/Users/terryli/eon/gapless-crypto-clickhouse/docs/PYPI_PUBLISHING_CONFIGURATION.yaml`
- `REFERENCE_VALIDATION_REPORT.md` (line 22) → `/Users/terryli/eon/gapless-crypto-clickhouse/docs/diagrams/docs/diagrams/01-collection-pipeline.mmd`
- `docs/CLICKHOUSE_MIGRATION.md` (line 316) → `tmp/clickhouse_quick_validation.py`
- `docs/CLICKHOUSE_MIGRATION.md` (line 317) → `tmp/clickhouse_futures_validation.py`
- `docs/MIGRATION_v3_to_v4.md` (line 318) → `tests/test_cli.py`
- `docs/MIGRATION_v3_to_v4.md` (line 319) → `tests/test_cli_integration.py`
- `docs/README.md` (line 20) → `PYPI_PUBLISHING_CONFIGURATION.yaml`

### Python Import (12)

- `README.md` (line 1168) → `gapless_crypto_clickhouse.streaming`
- `docs/CLICKHOUSE_MIGRATION.md` (line 118) → `gapless_crypto_clickhouse.questdb`
- `docs/CLICKHOUSE_MIGRATION.md` (line 145) → `gapless_crypto_clickhouse.collectors.questdb_bulk_loader`
- `docs/CLICKHOUSE_MIGRATION.md` (line 169) → `gapless_crypto_clickhouse.query`
- `docs/MIGRATION_v3_to_v4.md` (line 48) → `gapless_crypto_clickhouse.questdb`
- `docs/MIGRATION_v3_to_v4.md` (line 49) → `gapless_crypto_clickhouse.collectors.questdb_bulk_loader`
- `docs/MIGRATION_v3_to_v4.md` (line 236) → `gapless_crypto_clickhouse.questdb`
- `docs/MIGRATION_v3_to_v4.md` (line 237) → `gapless_crypto_clickhouse.query`
- `docs/development/CLI_MIGRATION_GUIDE.md` (line 78) → `gapless_crypto_data`
- `docs/development/CLI_MIGRATION_GUIDE.md` (line 79) → `gapless_crypto_data`

## Consistency Issues

- Absolute paths: 134
- Relative paths (./ or ../): 80
- Repository-relative paths: 62

⚠️ **Inconsistency detected**: Mix of absolute and repo-relative paths

## Score: 1/10

**Rationale**: Deductions for: 3 broken markdown links, 244 potential issues, inconsistent path formats
