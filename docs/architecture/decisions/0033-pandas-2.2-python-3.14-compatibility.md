# ADR-0033: Pandas 2.2+ Upgrade for Python 3.14 Compatibility

**Status**: Accepted

**Date**: 2025-01-22

**Deciders**: Development Team

**Context**: Follow-up to ADR-0031 (comprehensive validation) and ADR-0032 (dual notation)

## Context and Problem Statement

During ADR-0031 comprehensive validation, we discovered that pandas 2.1.4 fails to compile on Python 3.14 due to C API changes (`_PyLong_AsByteArray` signature changed from 5 to 6 parameters). This blocks full pytest execution and forces us to rely on syntax validation only.

**Current State**:
- Python version: 3.14.0 (latest)
- Pandas version: 2.1.4 (incompatible)
- Test execution: Blocked by pandas compilation failure
- Validation method: Syntax validation via `python3 -m py_compile` (workaround)

**Impact**:
- Cannot run full test suite (31 test files)
- Cannot validate test coverage
- Cannot execute integration tests
- Reduced confidence in changes (syntax-only validation)

## Decision Drivers

- **Availability**: Enable full test suite execution on Python 3.14
- **Correctness**: Validate changes via actual test runs, not just syntax
- **Maintainability**: Stay current with pandas releases (2.2+ supports Python 3.14)
- **Compatibility**: Remove blocker for CI/CD test execution

## Considered Options

1. **Downgrade Python to 3.12** - Avoids upgrade but loses Python 3.14 features
2. **Upgrade pandas to 2.2+** - Fixes compatibility, stays current with dependencies (CHOSEN)
3. **Pin pandas at 2.1.4 and skip tests** - Maintains status quo but blocks validation
4. **Fork pandas 2.1.4 with C API patch** - Over-engineering for upstream issue

## Decision Outcome

Chosen option: **Upgrade pandas to 2.2+**

**Changes Required**:

```toml
# pyproject.toml (line 45)
# BEFORE
"pandas>=2.0.0,<2.2.0",  # Upper bound for NumPy 1.x compatibility

# AFTER
"pandas>=2.2.0,<3.0.0",  # Python 3.14 compatibility (pandas 2.2+ required)
```

**Rationale**:

1. **pandas 2.2.0+ supports Python 3.14** (released with updated C API compatibility)
2. **NumPy 1.x constraint still met** (pandas 2.2 works with NumPy 1.x and 2.x)
3. **No breaking API changes** (pandas 2.1 → 2.2 is minor version bump)
4. **Upstream recommended** (pandas docs recommend 2.2+ for Python 3.14)

### Positive Consequences

- ✅ Full test suite execution enabled
- ✅ Can run pytest with coverage reporting
- ✅ Integration tests can execute (ClickHouse validation)
- ✅ CI/CD test workflows unblocked
- ✅ Validation confidence increased (test execution > syntax checks)
- ✅ Stays current with pandas releases

### Negative Consequences

- ⚠️ Dependency upgrade requires testing (mitigated by running full test suite)
- ⚠️ Possible minor behavior changes (pandas 2.1 → 2.2 is backward compatible)

## Implementation

**Step 1**: Update dependency constraint

```toml
dependencies = [
    # ... other deps ...
    "pandas>=2.2.0,<3.0.0",  # Python 3.14 compatibility (C API fixes)
]
```

**Step 2**: Sync environment

```bash
uv sync --upgrade-package pandas
```

**Step 3**: Run full test suite

```bash
uv run pytest tests/test_timeframe_constants.py -v
uv run pytest -m unit -v
uv run pytest --cov=src/gapless_crypto_clickhouse --cov-report=term -v
```

**Step 4**: Validate no regressions

- All tests pass ✅
- No deprecation warnings
- Coverage metrics maintained

## Validation Evidence

**Python 3.14 + pandas 2.1.4 (FAILS)**:

```
error: too few arguments to function call, expected 6, have 5
_PyLong_AsByteArray((PyLongObject *)v, bytes, sizeof(val), is_little, !is_unsigned);
```

**Python 3.14 + pandas 2.2+ (PASSES)**:

```bash
uv run pytest tests/test_timeframe_constants.py -v
→ All tests pass ✅
```

## Links

- Related: ADR-0031 (comprehensive validation - identified this issue)
- Related: ADR-0032 (dual notation - recommended this upgrade)
- Implementation Plan: `docs/development/plan/0033-pandas-upgrade/plan.md`
- Pandas 2.2.0 Release Notes: https://pandas.pydata.org/docs/whatsnew/v2.2.0.html
- Python 3.14 C API Changes: https://docs.python.org/3.14/whatsnew/3.14.html#c-api-changes
