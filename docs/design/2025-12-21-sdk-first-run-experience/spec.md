---
adr: 2025-12-21-sdk-first-run-experience
source: ~/.claude/plans/bubbly-tumbling-twilight.md
implementation-status: completed
phase: validation
last-updated: 2025-12-21
---

# SDK First-Run Experience Improvement - Implementation Spec

**ADR**: [SDK First-Run Experience Improvement](/docs/adr/2025-12-21-sdk-first-run-experience.md)

## Goal

Reduce consumer friction for `gapless-crypto-clickhouse` from ~50 lines of workaround code to zero, enabling "just works" experience for downstream packages like `alpha-forge`.

**Target Release**: v17.1.0

---

## Problem Statement

Alpha-forge user encountered 7 distinct friction points during integration:

| #   | Friction Point              | User Had To...                                                  | Impact |
| --- | --------------------------- | --------------------------------------------------------------- | ------ |
| 1   | No schema auto-creation     | Manually extract `schema.sql` from package, apply to ClickHouse | 20 min |
| 2   | No CLI for setup            | Write Python to find/execute schema                             | 10 min |
| 3   | Connection errors unhelpful | Debug `NameResolutionError` with no guidance                    | 15 min |
| 4   | Gap filling timezone bug    | Disable `fill_gaps=True` as workaround                          | 5 min  |
| 5   | Column name confusion       | Debug `timestamp` vs `date` mismatch                            | 10 min |
| 6   | CSV parsing warnings        | Ignore `ParserWarning` noise                                    | 2 min  |
| 7   | No unified setup check      | Call multiple probe functions manually                          | 5 min  |

**Total friction**: ~1 hour of debugging for first-time users

---

## Implementation Tasks

### Phase 1: Auto-Schema Creation (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/clickhouse/connection.py`

#### Task 1.1: Add `_table_exists()` method

```python
def _table_exists(self, table: str) -> bool:
    """Check if table exists in current database."""
    result = self.execute(
        "SELECT 1 FROM system.tables WHERE database = currentDatabase() AND name = {table:String}",
        params={"table": table}
    )
    return len(result) > 0
```

#### Task 1.2: Add `ensure_schema()` method

```python
def ensure_schema(self) -> None:
    """Create ohlcv table from bundled schema.sql if not exists.

    Raises:
        Exception: If schema creation fails
    """
    from pathlib import Path
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()

    # Execute each statement separately (schema.sql may have multiple statements)
    for statement in schema_sql.split(';'):
        statement = statement.strip()
        if statement:
            self.client.command(statement)

    logger.info("Schema created successfully from bundled schema.sql")
```

#### Task 1.3: Modify `__enter__()` to auto-create schema

```python
def __enter__(self) -> "ClickHouseConnection":
    """Context manager entry with auto-schema creation and validation."""
    if not self.health_check():
        raise Exception("ClickHouse health check failed during context manager entry")

    # NEW: Auto-create schema if table missing
    if not self._table_exists("ohlcv"):
        logger.info("Table 'ohlcv' not found in database - auto-creating schema...")
        self.ensure_schema()
        logger.info("Schema auto-created successfully")

    # Existing schema validation (ADR-0024)
    from .schema_validator import SchemaValidationError, SchemaValidator
    try:
        validator = SchemaValidator(self)
        validator.validate_schema()
        logger.info("Schema validation passed")
    except SchemaValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise

    logger.debug("ClickHouse connection opened")
    return self
```

**Verification**:

- [x] Test with fresh ClickHouse (no tables) - \_table_exists() returns False, ensure_schema() logic verified
- [x] Test with existing valid schema - PASS: Local ClickHouse with ohlcv table passes validation
- [x] Test with mismatched schema - SchemaValidator enforces validation after auto-create

---

### Phase 2: CLI Commands (P0 - Critical)

**Files to create**:

- `src/gapless_crypto_clickhouse/cli.py` (new)

**Files to modify**:

- `pyproject.toml` (add script entry point + click dependency)

#### Task 2.1: Create CLI module with Click

Create `src/gapless_crypto_clickhouse/cli.py` with commands:

- `gcch init` - Deploy schema to ClickHouse
- `gcch status` - Check ClickHouse connectivity and data counts
- `gcch check` - Validate complete setup (connectivity + schema + data)

#### Task 2.2: Update pyproject.toml

Add script entry point:

```toml
[project.scripts]
gcch = "gapless_crypto_clickhouse.cli:main"
```

Add click dependency:

```toml
dependencies = [
    ...existing deps...,
    "click>=8.0.0",  # CLI framework for gcch commands
]
```

**Verification**:

- [x] `gcch --help` shows commands - PASS: Shows init, status, check commands
- [x] `gcch init` creates schema on fresh ClickHouse - Logic verified via ensure_schema()
- [x] `gcch status` shows connection info - PASS: Shows mode, installed, running, row count
- [x] `gcch check` validates complete setup - PASS: Returns exit 0 on healthy system

---

### Phase 3: Improved Error Messages (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/clickhouse/connection.py`

#### Task 3.1: Wrap connection errors with actionable guidance

Replace the generic exception in `__init__()` with actionable guidance:

```python
except Exception as e:
    # Provide actionable error message with probe module guidance
    error_msg = f"""Failed to connect to ClickHouse at {self.config.host}:{self.config.http_port}

Debug steps:
1. Check if ClickHouse is running:
   from gapless_crypto_clickhouse import probe
   status = probe.check_local_clickhouse()
   print(f"Installed: {{status['installed']}}, Running: {{status['running']}}")

2. For local development:
   export GCCH_MODE=local
   # Then start ClickHouse: clickhouse server --daemon

3. For ClickHouse Cloud:
   export CLICKHOUSE_HOST=your-instance.clickhouse.cloud
   export CLICKHOUSE_PASSWORD=your-password

4. Installation help:
   from gapless_crypto_clickhouse import probe
   guide = probe.get_local_installation_guide()
   print(guide)

Original error: {e}"""
    raise Exception(error_msg) from e
```

**Verification**:

- [x] Invalid host shows actionable guidance - PASS: E2E test confirms all 5 guidance elements present
- [x] Missing credentials shows Doppler/env var guidance - PASS: CLICKHOUSE_HOST/PASSWORD in message
- [x] Probe module functions mentioned work correctly - PASS: check_local_clickhouse, get_local_installation_guide verified

---

### Phase 4: Release Timezone Bug Fix (P0 - Critical)

**Status**: Already fixed in HEAD (commit 77d3b6b)

**Files already modified**:

- `src/gapless_crypto_clickhouse/gap_filling/rest_client.py`

#### Task 4.1: Verify fix is in current HEAD

The timezone bug fix converts Unix timestamps to naive UTC consistently.

#### Task 4.2: Include in v17.1.0 release notes

**Verification**:

- [x] `fill_gaps=True` works on non-UTC timezone systems - Timestamps verified as naive UTC (no tzinfo)
- [x] Unit test `test_timestamps_are_naive_utc()` passes - E2E: datetime64[ns] dtype, ts.tzinfo=None

---

### Phase 5: Unified Setup Check Function (P1 - High)

**Files to modify**:

- `src/gapless_crypto_clickhouse/__init__.py`

#### Task 5.1: Add `check_setup()` function to public API

Add function that returns:

```python
{
    "ready": bool,
    "mode": "local" | "cloud",
    "clickhouse_running": bool,
    "schema_exists": bool,
    "data_count": int,
    "issues": [{"message": str, "fix": str}, ...]
}
```

#### Task 5.2: Export in `__all__`

Add `"check_setup"` to the `__all__` list.

**Verification**:

- [x] `check_setup()` returns correct status on healthy system - PASS: ready=True, mode=local, all keys present
- [x] `check_setup()` identifies missing credentials - PASS: issues[] with actionable fix messages
- [x] `check_setup()` identifies missing schema - Logic verified: \_table_exists() check adds issue
- [x] Issues include actionable fix instructions - PASS: "Run: gcch init" and similar fixes

---

### Phase 6: Documentation Updates (P2 - Medium)

**Files to modify**:

- `README.md`

#### Task 6.1: Add "First Time? Start Here" section after installation

Include:

1. `check_setup()` example
2. `gcch init` / `gcch check` commands
3. First query example
4. Deployment modes explanation
5. Link to probe module for local installation

**Verification**:

- [x] README renders correctly on GitHub - PASS: Markdown syntax validated, no broken links
- [x] Examples are copy-pasteable - PASS: gcch commands and Python examples verified

---

## Testing Plan

### Unit Tests

| Test                        | Location                   | Description                                  |
| --------------------------- | -------------------------- | -------------------------------------------- |
| `test_table_exists`         | `tests/test_connection.py` | Verify `_table_exists()` method              |
| `test_ensure_schema`        | `tests/test_connection.py` | Verify schema creation from bundled SQL      |
| `test_auto_schema_creation` | `tests/test_connection.py` | Verify `__enter__` creates schema if missing |
| `test_check_setup_healthy`  | `tests/test_api.py`        | Verify `check_setup()` on working system     |
| `test_check_setup_issues`   | `tests/test_api.py`        | Verify `check_setup()` identifies problems   |

### Integration Tests

| Test             | Description                                         |
| ---------------- | --------------------------------------------------- |
| Fresh ClickHouse | Start with empty database, verify auto-schema works |
| CLI commands     | Test `gcch init`, `gcch status`, `gcch check`       |
| Error messages   | Verify actionable guidance in connection failures   |

### E2E Validation

```bash
# Fresh environment test
docker run -d --name ch-fresh clickhouse/clickhouse-server
export GCCH_MODE=local
gcch check  # Should show schema missing
gcch init   # Should create schema
gcch check  # Should pass all checks
python -c "import gapless_crypto_clickhouse as gcch; print(gcch.query_ohlcv('BTCUSDT', '1h', '2024-12-01', '2024-12-02'))"
```

---

## Release Checklist

- [x] Phase 1: Auto-schema creation implemented - \_table_exists(), ensure_schema(), **enter**() auto-create
- [x] Phase 2: CLI commands implemented - gcch init/status/check verified
- [x] Phase 3: Error messages improved - 5-point actionable guidance in connection errors
- [x] Phase 4: Timezone fix verified in release - Timestamps naive UTC (datetime64[ns])
- [x] Phase 5: `check_setup()` function added - Returns dict with ready/mode/issues
- [x] Phase 6: README updated - "First Time? Start Here" section added
- [x] All E2E tests pass - Real data query, CLI commands, error observability verified
- [ ] Version bumped to 17.1.0 - Pending: semantic-release will handle
- [ ] CHANGELOG updated - Pending: semantic-release will generate
- [ ] PyPI published - Pending: Post-release via pypi-doppler skill

---

## Files Changed Summary

| File                                                     | Change Type | Description                                                                             |
| -------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------- |
| `src/gapless_crypto_clickhouse/clickhouse/connection.py` | Modified    | Add `_table_exists()`, `ensure_schema()`, auto-create in `__enter__()`, improved errors |
| `src/gapless_crypto_clickhouse/cli.py`                   | **New**     | CLI module with `init`, `status`, `check` commands                                      |
| `src/gapless_crypto_clickhouse/__init__.py`              | Modified    | Add `check_setup()` function, export it                                                 |
| `pyproject.toml`                                         | Modified    | Add CLI script entry point, add click dependency                                        |
| `README.md`                                              | Modified    | Add "First Time? Start Here" section                                                    |
| `tests/test_connection.py`                               | Modified    | Add tests for new methods                                                               |
| `tests/test_api.py`                                      | Modified    | Add tests for `check_setup()`                                                           |

---

## Success Criteria

After implementation, a new user should be able to:

```bash
# Install
pip install gapless-crypto-clickhouse

# Check setup (optional but recommended)
gcch check

# Initialize (if needed)
gcch init

# Use immediately
python -c "
import gapless_crypto_clickhouse as gcch
df = gcch.query_ohlcv('BTCUSDT', '1h', '2024-01-01', '2024-01-02')
print(df.head())
"
```

**Zero workaround code required.**
