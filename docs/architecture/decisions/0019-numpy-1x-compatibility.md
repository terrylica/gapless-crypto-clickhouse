# NumPy 1.x Compatibility for Alpha Forge Integration

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Terry Li
**Related ADRs**: None
**Related Plans**: [0019-numpy-1x-compatibility](../../development/plan/0019-numpy-1x-compatibility/plan.md)

## Context and Problem Statement

Alpha Forge AI agents identified a CRITICAL BLOCKER preventing integration: NumPy version conflict.

**Alpha Forge Requirement**: `numpy>=1.24.0,<2.0.0` (TA-Lib constraint)
**Current GCC State**: `numpy 2.2.6` (via pandas 2.3.2)
**Result**: Cannot install both packages in same Python environment

**Impact**: Blocks Alpha Forge integration despite excellent package quality scores (A- overall, 90/100).

**Question**: Should we add explicit NumPy 1.x constraints to enable Alpha Forge integration?

## Decision Drivers

- **Integration Urgency**: Alpha Forge ready to integrate pending this fix
- **Backward Compatibility**: Must maintain existing functionality
- **Ecosystem Compatibility**: TA-Lib widely used in quant finance (NumPy 1.x requirement common)
- **Risk Assessment**: Research shows low risk (no NumPy 2.x-specific features used)
- **SLO Focus**: Availability (enables Alpha Forge), Correctness (maintain existing behavior)

## Considered Options

1. **Add NumPy 1.x constraints** (lock to `numpy>=1.23.2,<2.0.0` and `pandas>=2.0.0,<2.2.0`)
2. **Keep current NumPy 2.x** (reject Alpha Forge integration)
3. **Support both NumPy 1.x and 2.x** (complex testing matrix)
4. **Create separate package** (gapless-crypto-clickhouse-numpy1)

## Decision Outcome

**Chosen option**: Add NumPy 1.x constraints

**Rationale**:

### Why NumPy 1.x Constraints

**Codebase Analysis**:

Research shows minimal NumPy usage in codebase:

- **Direct NumPy usage**: 1 file only (`validation/storage.py`)
- **Usage pattern**: Basic type checking for JSON serialization
- **APIs used**: `np.integer`, `np.int64`, `np.floating`, `np.float64`, `np.bool_`, `np.ndarray`, `.tolist()`
- **Assessment**: All APIs stable since NumPy 1.23.2

**Pandas Compatibility**:

Pandas version compatibility with NumPy:

- **pandas 2.0.x/2.1.x**: NumPy 1.x only (incompatible with NumPy 2.0+)
- **pandas 2.2.x+**: NumPy 1.x and 2.x compatible

Current pandas usage analysis:

- **pandas version**: Currently `>=2.0.0` (no upper bound)
- **pandas APIs used**: `read_csv()`, `to_datetime()`, `Timedelta()`, `concat()`, `read_parquet()`, `to_parquet()`
- **Assessment**: All APIs stable since pandas 2.0.0, no 2.3-specific features detected

**Risk Analysis**:

| Risk Category               | Level | Mitigation                              |
| --------------------------- | ----- | --------------------------------------- |
| pandas API breaking changes | LOW   | No version-specific features used       |
| NumPy API breaking changes  | LOW   | Minimal usage, basic type checking only |
| Dependency conflicts        | NONE  | All deps support NumPy 1.24+            |
| Test coverage               | GOOD  | Existing tests will catch issues        |

### Implementation Strategy

**Dependency Specification**:

```toml
# pyproject.toml
dependencies = [
    "numpy>=1.23.2,<2.0.0",  # NEW: Explicit NumPy 1.x constraint
    "pandas>=2.0.0,<2.2.0",   # NEW: Upper bound for NumPy 1.x compatibility
    # ... other dependencies unchanged
]
```bash

**Why these versions**:

1. **`numpy>=1.23.2,<2.0.0`**:
   - Satisfies Alpha Forge requirement (`>=1.24.0,<2.0.0`)
   - Uses 1.23.2 as minimum (pandas 2.0 requirement for Python 3.11+)
   - Locks out NumPy 2.x entirely

2. **`pandas>=2.0.0,<2.2.0`**:
   - Locks to pandas 2.0.x or 2.1.x (both NumPy 1.x compatible)
   - Prevents auto-upgrade to pandas 2.2+ (which supports NumPy 2.x)
   - Maintains all existing functionality (no breaking changes)

**Validation Plan**:

1. Update `pyproject.toml` with new constraints
2. Run `uv lock --upgrade` to regenerate lockfile
3. Verify resolved versions (pandas 2.0.x/2.1.x, numpy 1.x)
4. Run full test suite (unit + integration + E2E)
5. Manual verification of core workflows

## Consequences

### Positive

- ✅ **Unblocks Alpha Forge Integration**: Enables immediate integration without workarounds
- ✅ **Broader Ecosystem Compatibility**: TA-Lib requirement common in quant finance
- ✅ **Low Risk**: Codebase analysis shows minimal NumPy usage, stable pandas APIs
- ✅ **Maintains Functionality**: No breaking changes to existing code
- ✅ **Clear Constraints**: Explicit dependencies prevent version drift

### Negative

- ⚠️ **Locks to Older NumPy**: Cannot use NumPy 2.x features (but none currently used)
- ⚠️ **Locks to Older pandas**: Cannot use pandas 2.2+ features (but none currently needed)
- ⚠️ **Future Migration Needed**: Eventually need to support NumPy 2.x when TA-Lib updates

### Neutral

- NumPy 2.x adoption in ecosystem still ongoing (many libraries NumPy 1.x-only)
- pandas 2.0.x/2.1.x still widely used and maintained
- Lock-in is temporary (until TA-Lib supports NumPy 2.x)

## Validation Criteria

### Acceptance Criteria

- [ ] Package installs successfully with `numpy>=1.24.0,<2.0.0`
- [ ] Resolved numpy version is 1.x (likely 1.26.x)
- [ ] Resolved pandas version is 2.0.x or 2.1.x
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] Manual verification of core workflows succeeds
- [ ] Alpha Forge can install without dependency conflicts

### SLO Impact

- **Availability**: Improved (enables Alpha Forge integration)
- **Correctness**: No change (same functionality, different versions)
- **Observability**: No change (same logging/monitoring)
- **Maintainability**: Slight increase (dependency constraints to maintain)

## Migration Path

**For existing users**:

- No migration required (automatic via `pip install --upgrade`)
- Existing code continues working unchanged
- NumPy downgrade transparent (no API changes)
- pandas downgrade transparent (no API changes)

**For Alpha Forge integration**:

```bash
# After v3.1.0 release
pip install gapless-crypto-clickhouse>=3.1.0
# → Installs with NumPy 1.x (compatible with TA-Lib)
```

**For future NumPy 2.x support**:

- Monitor TA-Lib for NumPy 2.x support
- When available, update constraints to `numpy>=1.23.2,<3.0.0`
- Test with both NumPy 1.x and 2.x
- Release as minor version (backward compatible)

## References

- Alpha Forge Feedback: 7 AI agents probe report
- NumPy Version Compatibility: https://numpy.org/devdocs/release.html
- pandas Version Compatibility: https://pandas.pydata.org/docs/whatsnew/
- TA-Lib NumPy Requirement: https://github.com/TA-Lib/ta-lib-python/issues

## Compliance

- **OSS Libraries**: NumPy and pandas are standard OSS dependencies
- **Error Handling**: No changes (existing raise+propagate pattern maintained)
- **Backward Compatibility**: Full backward compatibility (version constraint only)
- **Auto-Validation**: Test suite validates compatibility

## Future Work

- **NumPy 2.x Support**: When TA-Lib supports NumPy 2.x, expand constraints
- **pandas 2.2+ Features**: Evaluate if newer pandas features beneficial
- **Dual Support**: Consider supporting both NumPy 1.x and 2.x in future

---

**ADR-0019** | NumPy 1.x Compatibility | Accepted | 2025-11-19
