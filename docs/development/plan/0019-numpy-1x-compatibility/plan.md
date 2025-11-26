# NumPy 1.x Compatibility Implementation Plan

**ADR ID**: 0019
**Status**: Complete
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-20
**Completed**: 2025-11-20
**Released**: v3.1.0

---

## Objective

Add explicit NumPy 1.x constraints to enable Alpha Forge integration by resolving critical dependency conflict.

## Background

### Problem

Alpha Forge AI agents probe identified CRITICAL BLOCKER:

```text
Alpha Forge requires: numpy>=1.24.0,<2.0.0 (TA-Lib constraint)
GCC currently has: numpy 2.2.6 (via pandas 2.3.2)
Result: Cannot install both in same environment
```

**Impact**: Blocks Alpha Forge integration despite excellent package quality (A- grade, 90/100 score).

### Solution

Add explicit NumPy 1.x constraints:

````toml
# Before
dependencies = [
    "pandas>=2.0.0",  # No numpy constraint, resolves to latest
]

# After
dependencies = [
    "numpy>=1.23.2,<2.0.0",  # Explicit NumPy 1.x lock
    "pandas>=2.0.0,<2.2.0",   # Upper bound for NumPy 1.x compatibility
]
```text

## Goals

1. **Add NumPy 1.x Constraint** - Lock to `numpy>=1.23.2,<2.0.0`
2. **Add pandas Upper Bound** - Lock to `pandas>=2.0.0,<2.2.0`
3. **Validate Compatibility** - Ensure all tests pass with NumPy 1.x
4. **Maintain Functionality** - Zero breaking changes to existing code
5. **Enable Alpha Forge** - Unblock integration immediately

## Non-Goals

- Supporting both NumPy 1.x and 2.x simultaneously (defer to future)
- Upgrading to NumPy 2.x-specific features (not needed)
- Rewriting code for NumPy compatibility (no changes needed)

## Design

### Dependency Resolution Strategy

**Principle**: Lock to NumPy 1.x via explicit constraints and pandas upper bound

**Implementation**:

```toml
# pyproject.toml dependencies section
dependencies = [
    "clickhouse-driver>=0.2.9",
    "duckdb>=1.1.0",
    "httpx>=0.25.0",
    "numpy>=1.23.2,<2.0.0",  # NEW: Explicit NumPy 1.x constraint
    "pandas>=2.0.0,<2.2.0",   # MODIFIED: Add upper bound
    "pydantic>=2.0.0",
    "pyarrow>=16.0.0",
    "python-dotenv>=1.0.0",
]
```bash

**Why these versions**:

1. **`numpy>=1.23.2,<2.0.0`**:
   - Lower bound: 1.23.2 (pandas 2.0 minimum for Python 3.11+)
   - Upper bound: Exclude NumPy 2.x entirely
   - Satisfies Alpha Forge: `>=1.24.0,<2.0.0` ✓

2. **`pandas>=2.0.0,<2.2.0`**:
   - Locks to pandas 2.0.x or 2.1.x
   - Both versions: NumPy 1.x compatible, NumPy 2.x incompatible
   - Prevents auto-upgrade to pandas 2.2+ (NumPy 2.x compatible)

### Expected Resolution

After `uv lock --upgrade`:

````

pandas==2.0.3 or 2.1.4 (latest NumPy 1.x-only version)
numpy==1.26.4 (latest 1.x version)

````python

### Compatibility Validation

**Research Findings**:

| Category     | Assessment                   | Evidence                                         |
| ------------ | ---------------------------- | ------------------------------------------------ |
| NumPy Usage  | MINIMAL                      | 1 file, basic type checking only                 |
| NumPy APIs   | STABLE                       | `np.integer`, `.tolist()` - available since 1.23 |
| pandas Usage | NO VERSION-SPECIFIC FEATURES | All APIs stable since 2.0.0                      |
| pandas APIs  | STANDARD                     | `read_csv()`, `to_datetime()`, `concat()`        |
| Dependencies | COMPATIBLE                   | All support NumPy 1.24+                          |

**Risk Assessment**: LOW (no breaking changes expected)

## Implementation Checklist

### Pre-Implementation

- [x] Create ADR-0019
- [x] Create this plan document
- [ ] Backup current lockfile (`cp uv.lock uv.lock.backup`)

### Implementation

- [ ] Update `pyproject.toml`:
  - Add `numpy>=1.23.2,<2.0.0` to dependencies
  - Modify pandas: `pandas>=2.0.0` → `pandas>=2.0.0,<2.2.0`
- [ ] Regenerate lockfile: `uv lock --upgrade`
- [ ] Verify resolved versions:
  - `grep "name = \"numpy\"" uv.lock` → should show version 1.x
  - `grep "name = \"pandas\"" uv.lock` → should show 2.0.x or 2.1.x
- [ ] Install dependencies: `uv sync`

### Validation

- [ ] Run unit tests: `uv run pytest tests/`
- [ ] Check for deprecation warnings
- [ ] Verify core workflows:
  - Download data with `download()`
  - ClickHouse bulk load
  - Gap filling operations
  - Validation pipeline
- [ ] Manual verification:

  ```python
  import numpy as np
  import pandas as pd
  import gapless_crypto_clickhouse as gcch

  print(f"NumPy: {np.__version__}")  # Should be 1.x
  print(f"pandas: {pd.__version__}")  # Should be 2.0.x or 2.1.x

  # Test basic operation
  df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
  print(f"Downloaded {len(df)} rows")  # Should succeed
````

### Documentation

- [ ] Update CHANGELOG.md with dependency changes
- [ ] Document NumPy 1.x requirement in README (if needed)
- [ ] Update Alpha Forge notification document

### Release

- [ ] Commit with conventional commit message
- [ ] semantic-release creates v3.1.0
- [ ] Verify GitHub release notes
- [ ] Publish to PyPI
- [ ] Notify Alpha Forge team

## Rollout Plan

### Timeline

- **Implementation**: 2025-11-19 (30 minutes)
- **Testing**: 2025-11-19 (30 minutes)
- **Release**: v3.1.0 same day
- **Alpha Forge Notification**: Immediately after release

### Validation Steps

1. **Dependency Resolution**: Verify lockfile shows NumPy 1.x
2. **Unit Tests**: All existing tests pass
3. **Integration Tests**: Core workflows execute successfully
4. **Manual Verification**: Import and basic operations work
5. **Alpha Forge Test**: Can install with TA-Lib without conflicts

### Rollback Strategy

**If critical issues found**:

```bash
# Restore previous lockfile
cp uv.lock.backup uv.lock

# Revert pyproject.toml changes
git checkout pyproject.toml

# Reinstall original dependencies
uv sync
```

**Indicators for rollback**:

- Test suite failures (>5% tests fail)
- Import errors with NumPy/pandas
- ClickHouse operations fail
- Data quality issues detected

## Risks and Mitigations

### Risk 1: pandas API Breaking Changes

**Risk**: pandas 2.3 → 2.0/2.1 introduces breaking changes
**Likelihood**: Very Low (backward compatibility within 2.x)
**Impact**: High (broken functionality)
**Mitigation**:

- Research confirmed no version-specific features used
- Test suite will catch any issues
- Rollback plan available

### Risk 2: NumPy Type System Changes

**Risk**: NumPy 2.x → 1.x type system differences break code
**Likelihood**: Low (minimal NumPy usage, basic APIs)
**Impact**: Medium (JSON serialization in validation)
**Mitigation**:

- Only basic type checking used (`isinstance()`)
- APIs stable since NumPy 1.23
- Isolated to one file (`validation/storage.py`)

### Risk 3: Dependency Conflicts

**Risk**: Other dependencies require NumPy 2.x
**Likelihood**: Very Low (all checked, support 1.24+)
**Impact**: High (installation failure)
**Mitigation**:

- Verified all dependencies compatible:
  - clickhouse-driver: no numpy dependency
  - duckdb: no numpy dependency
  - httpx: no numpy dependency
  - pyarrow: supports NumPy 1.x and 2.x
  - pydantic: no numpy dependency

## Success Metrics

### Primary Metrics

- [ ] Package installs with `numpy<2.0.0` constraint
- [ ] Resolved NumPy version is 1.x (1.26.x expected)
- [ ] Resolved pandas version is 2.0.x or 2.1.x
- [ ] All unit tests pass (0 failures)
- [ ] All integration tests pass (0 failures)
- [ ] Alpha Forge can install without conflicts

### Secondary Metrics

- [ ] No deprecation warnings during tests
- [ ] No performance regression (within 5%)
- [ ] Zero bug reports related to NumPy/pandas versions

## Open Questions

- **Q**: When will TA-Lib support NumPy 2.x?
  **A**: Monitor TA-Lib GitHub for updates, no ETA currently

- **Q**: Should we support both NumPy 1.x and 2.x?
  **A**: Defer to future work (after TA-Lib supports 2.x)

- **Q**: Will this affect existing users?
  **A**: Yes (auto-downgrade on upgrade), but transparent (no code changes)

## References

- ADR-0019: NumPy 1.x Compatibility
- Alpha Forge Feedback: AI agents probe report (NumPy blocker)
- NumPy Release Notes: https://numpy.org/devdocs/release.html
- pandas Release Notes: https://pandas.pydata.org/docs/whatsnew/
- Python Agent Research: Dependency compatibility analysis

## Log Files

Implementation logs stored in:

- `logs/0019-numpy-1x-compatibility-YYYYMMDD_HHMMSS.log`

---

**Plan 0019** | NumPy 1.x Compatibility | In Progress | 2025-11-19
