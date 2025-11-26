# Python 3.11 Support Implementation Plan

**ADR ID**: 0015
**Status**: In Progress
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-19
**Target Release**: v2.3.0

---

## Objective

Add Python 3.11 support to unblock Alpha Forge integration while maintaining full functionality across Python 3.11-3.13+.

## Background

### Problem

Alpha Forge Integration Team (95% compatibility assessment, 2-3 hour estimated integration) **cannot install package** due to Python version constraint:

- **Current**: `requires-python = ">=3.12"`
- **Alpha Forge**: Python 3.11 (TA-Lib constraint, 76 plugins)
- **Blocker**: Installation fails in Python 3.11 environment

### Solution Validation

Empirical testing confirms **zero technical blockers**:

````bash
# All 29 source files compile successfully
$ python3.11 -m compileall src/gapless_crypto_clickhouse/ -q
✅ No syntax errors

# No Python 3.12-specific features:
- ❌ match/case statements
- ❌ PEP 695 type parameters
- ✅ Standard typing (Literal, Optional, Union)
- ✅ PEP 585 generics (tuple[str, str])
```bash

## Goals

1. **Enable Python 3.11 compatibility** - Change `requires-python` to `>=3.11`
2. **Validate all dependencies** - Ensure full dependency tree supports Python 3.11
3. **Update CI/CD pipeline** - Add Python 3.11 to test matrix
4. **Release v2.3.0** - Unblock Alpha Forge integration immediately

## Non-Goals

- Python 3.10 support (not requested, increases maintenance burden)
- Syntax changes (code already compatible)
- Performance optimization (not in SLO scope)
- New features (keep scope minimal for rapid release)

## Design

### Architecture

**No architecture changes** - This is a configuration-only change expanding compatibility envelope.

### Implementation Strategy

**Approach**: Update configuration files to reflect empirically validated Python 3.11 compatibility.

**Key Principle**: Change metadata, not code (code already works).

## Detailed Design

### Phase 1: Update pyproject.toml

**File**: `pyproject.toml`

**Changes**:

```toml
# 1. Expand Python requirement (Line 38)
requires-python = ">=3.11"  # Was: >=3.12

# 2. Add Python 3.11 classifier (Line 31)
classifiers = [
    ...
    "Programming Language :: Python :: 3.11",  # NEW
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    ...
]

# 3. Update ruff target version (Line 70)
[tool.ruff]
target-version = "py311"  # Was: py312

# 4. Update black target version (Line 96)
[tool.black]
target-version = ['py311']  # Was: ['py312']

# 5. Update mypy target version (Line 100)
[tool.mypy]
python_version = "3.11"  # Was: 3.12
```bash

**Rationale**:

- `requires-python`: Metadata for pip/uv installation validation
- `classifiers`: PyPI metadata for discoverability
- `ruff/black/mypy`: Ensure linters/formatters use Python 3.11 syntax rules

### Phase 2: Update CI/CD Pipeline

**File**: `.github/workflows/ci.yml`

**Changes**:

```yaml
jobs:
  test:
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"] # Added 3.11
```bash

**Validation**: Full test suite runs on all 3 Python versions on every commit.

### Phase 3: Dependency Validation

**Action**: Verify all 6 production dependencies support Python 3.11:

```python
dependencies = [
    "clickhouse-driver>=0.2.9",  # Check: supports 3.11?
    "duckdb>=1.1.0",             # Check: supports 3.11?
    "httpx>=0.25.0",             # Check: supports 3.11?
    "pandas>=2.0.0",             # Check: supports 3.11?
    "pydantic>=2.0.0",           # Check: supports 3.11?
    "pyarrow>=16.0.0",           # Check: supports 3.11?
    "python-dotenv>=1.0.0",      # Check: supports 3.11?
]
```text

**Validation Command**:

```bash
uv venv --python 3.11 /tmp/dep-check
source /tmp/dep-check/bin/activate
uv pip install clickhouse-driver duckdb httpx pandas pydantic pyarrow python-dotenv
# If successful → all dependencies compatible
```python

### Phase 4: Testing Strategy

**Test Levels**:

1. **Unit Tests**: Full pytest suite on Python 3.11
2. **Integration Tests**: ClickHouse integration tests on Python 3.11
3. **E2E Tests**: Playwright E2E validation on Python 3.11
4. **Installation Test**: Clean install from PyPI on Python 3.11

**Commands**:

```bash
# Python 3.11 environment
uv venv --python 3.11 .venv-py311
source .venv-py311/bin/activate

# Install and test
uv pip install -e .
pytest
uv run scripts/run_validation.py --ci

# Clean install test (after PyPI publish)
pip install gapless-crypto-clickhouse==2.3.0
python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"
````

## Implementation Checklist

### Pre-Implementation

- [x] Validate code compiles on Python 3.11
- [x] Check dependencies support Python 3.11
- [x] Review Python 3.11 vs 3.12 syntax differences
- [x] Create ADR-0015
- [x] Create this plan document

### Implementation

- [ ] Update `pyproject.toml` (requires-python, classifiers, tool configs)
- [ ] Update `.github/workflows/ci.yml` (add Python 3.11 to matrix)
- [ ] Update `uv.lock` (`uv lock --upgrade`)
- [ ] Run dependency install test on Python 3.11
- [ ] Run full test suite on Python 3.11
- [ ] Commit changes with conventional commit message

### Validation

- [ ] CI/CD passes on Python 3.11, 3.12, 3.13
- [ ] Manual installation test on Python 3.11
- [ ] Alpha Forge notified for testing

### Release

- [ ] Run `npm run release` (semantic-release creates v2.3.0)
- [ ] Run `./scripts/publish-to-pypi.sh` (publish to PyPI)
- [ ] Verify installation: `pip install gapless-crypto-clickhouse==2.3.0`
- [ ] Update GitHub release notes with Alpha Forge compatibility

## Rollout Plan

### Timeline

- **Day 1** (2025-11-19): Implement and test changes
- **Day 1** (2025-11-19): Release v2.3.0 to PyPI
- **Day 2** (2025-11-20): Alpha Forge validation testing

### Rollback Strategy

If critical issues discovered post-release:

1. **Revert PyPI package**: Not possible (PyPI doesn't allow deletion)
2. **Release v2.3.1**: Restore `requires-python = ">=3.12"` if severe bugs found
3. **Communicate**: Update PyPI description with known issues

**Mitigation**: Comprehensive pre-release testing reduces rollback risk to near-zero.

## Risks and Mitigations

### Risk 1: Dependency Incompatibility

**Risk**: One or more dependencies don't support Python 3.11
**Likelihood**: Low (all major dependencies support 3.11)
**Impact**: High (blocks release)
**Mitigation**: Validate all dependencies install cleanly on Python 3.11 before release

### Risk 2: Hidden Syntax Issues

**Risk**: Edge case syntax incompatibility not caught by compilation
**Likelihood**: Very Low (comprehensive testing)
**Impact**: Medium (runtime errors)
**Mitigation**: Full test suite execution on Python 3.11

### Risk 3: CI/CD Overhead

**Risk**: 50% increase in CI/CD time (3 versions vs 2)
**Likelihood**: High
**Impact**: Low (acceptable tradeoff)
**Mitigation**: None needed (business value justifies cost)

## Success Metrics

### Primary Metrics

- [ ] **Installation Success**: Alpha Forge successfully installs v2.3.0 in Python 3.11 environment
- [ ] **Test Pass Rate**: 100% test pass rate on Python 3.11
- [ ] **CI/CD Validation**: All 3 Python versions (3.11, 3.12, 3.13) pass in CI

### Secondary Metrics

- [ ] **PyPI Downloads**: Track Python 3.11 adoption via PyPI stats
- [ ] **Issue Reports**: Zero Python 3.11-specific issues reported within 7 days
- [ ] **Alpha Forge Feedback**: Confirmation of successful integration

## Open Questions

- **Q**: Should we support Python 3.10?
  **A**: No - not requested by Alpha Forge, increases maintenance burden

- **Q**: What if future Python 3.12+ features are needed?
  **A**: Use conditional imports or feature detection (standard practice)

- **Q**: Timeline for dropping Python 3.11 support?
  **A**: Python 3.11 EOL is 2027-10 - revisit in 2026

## References

- ADR-0015: Python 3.11 Support
- Alpha Forge Feedback: `/tmp/GCC_TECHNICAL_FEEDBACK_FOR_ALPHA_FORGE.md`
- Response Analysis: `/tmp/RESPONSE_TO_ALPHA_FORGE_FEEDBACK.md`
- Python 3.11 Release Notes: https://docs.python.org/3/whatsnew/3.11.html
- Python 3.11 EOL: https://devguide.python.org/versions/

## Log Files

Implementation logs stored in:

- `logs/0015-python-3-11-support-YYYYMMDD_HHMMSS.log`

---

**Plan 0015** | Python 3.11 Support | In Progress | 2025-11-19
