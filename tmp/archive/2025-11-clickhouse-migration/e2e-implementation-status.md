# E2E Validation Framework Implementation Status

**Date**: 2025-11-19
**Status**: Blocked on pytest-asyncio/playwright event loop conflict

## Implementation Complete ✅

### Documentation (Doc-as-Code Synchronized)

- ✅ ADR-0013 (MADR format): `docs/decisions/0013-autonomous-validation-framework.md`
- ✅ Implementation Plan (Google Design Doc): `docs/plan/0013-autonomous-validation-framework/plan.md` (adr-id=0013)
- ✅ E2E Testing Guide: `docs/validation/E2E_TESTING_GUIDE.md`
- ✅ Screenshot Baseline Guide: `docs/validation/SCREENSHOT_BASELINE.md`
- ✅ Updated: README.md, CLAUDE.md with E2E references

### Implementation

- ✅ PEP 723 Bootstrap Script: `scripts/run_validation.py` (zero-setup, auto-install dependencies)
- ✅ E2E Test Infrastructure: `tests/e2e/conftest.py` (Playwright fixtures, browser config)
- ✅ CH-UI Tests: `tests/e2e/test_ch_ui_dashboard.py` (6 tests: happy path, errors, edge cases)
- ✅ ClickHouse Play Tests: `tests/e2e/test_clickhouse_play.py` (6 tests: happy path, errors, edge cases)
- ✅ CI/CD Integration: `.github/workflows/ci.yml` (browser caching, Python 3.13 matrix, concurrency groups)
- ✅ Scheduled Validation: `.github/workflows/e2e-validation.yml` (every 6 hours)
- ✅ Configuration: `pytest.ini` (markers, coverage, timeout)
- ✅ Dependencies: `pyproject.toml` (Playwright 1.56+, pytest-playwright 0.6+)

### Validation

- ✅ ADR↔plan↔code synchronization verified (automated validation script)
- ✅ Artifact validation passed (structure, linting, documentation)
- ✅ Semantic-release triggered (v1.3.0 created successfully)

## Blocking Issue ❌

**Problem**: pytest-asyncio and pytest-playwright event loop conflict

**Error**: `RuntimeError: Runner.run() cannot be called from a running event loop`

**Root Cause**: Both plugins try to manage the async event loop:

- pytest-asyncio (v0.21+): Creates Runner per test
- pytest-playwright (v0.6+): Provides async fixtures expecting event loop

**Attempts Made** (7 iterations):

1. ❌ Removed custom page fixture → Resolved setup errors, but conflict remains
2. ❌ Removed @pytest.mark.asyncio → Tests not recognized as async
3. ❌ Set asyncio_mode = strict → Tests fail "async functions not supported"
4. ❌ Added collection hook to remove markers → Fixtures not initialized ("assert None is not None")
5. ❌ Removed pytest-asyncio dependency → Not installed in CI, tests fail
6. ❌ Re-added pytest-asyncio + asyncio_mode = auto → Event loop conflict returns
7. ❌ Set asyncio_default_fixture_loop_scope = function → Event loop conflict persists

## Technical Analysis

### Conflict Mechanics

```python
# pytest-asyncio behavior (auto mode)
@pytest.mark.asyncio
async def test_example(page):  # page from pytest-playwright
    # pytest-asyncio creates new Runner here
    runner = asyncio.Runner()
    runner.run(test_coro)  # ← ERROR: playwright's loop already running
```

### Version Matrix

- pytest: 8.4.2
- pytest-asyncio: 0.21.0+
- pytest-playwright: 0.6.0+ (includes pytest-playwright 0.7.1 in CI)
- playwright: 1.56.0
- Python: 3.12/3.13

## Recommended Solutions (Ordered by Viability)

### Solution 1: Use pytest-playwright's Native Async Support ⭐ RECOMMENDED

**Approach**: pytest-playwright 0.4.0+ supports async natively without pytest-asyncio

**Implementation**:

1. Pin pytest-playwright to version that doesn't require pytest-asyncio
2. OR upgrade to latest pytest-playwright (1.x) with built-in async support
3. Remove pytest-asyncio from dev dependencies entirely
4. Remove asyncio configuration from pytest.ini

**Research Needed**: Check pytest-playwright changelog for versions with native async

### Solution 2: Use Synchronous Playwright Tests

**Approach**: Rewrite tests as sync functions with sync Playwright API

**Implementation**:

```python
@pytest.mark.e2e
def test_example(page):  # Sync function
    page.goto("http://localhost:5521")
    # ... sync API calls
```

**Pros**: No event loop conflicts
**Cons**: Loses async benefits, requires test rewrite

### Solution 3: Separate Test Environments

**Approach**: Run E2E tests in separate pytest invocation without pytest-asyncio

**Implementation**:

1. Create `tests/e2e/pytest.ini` (isolated configuration)
2. Remove pytest-asyncio configuration for E2E tests only
3. Run E2E tests separately: `pytest tests/e2e/ -c tests/e2e/pytest.ini`

**Pros**: Clean separation
**Cons**: More complex CI configuration

### Solution 4: Custom Event Loop Policy

**Approach**: Override pytest-asyncio's event loop with playwright's

**Implementation** (in `tests/e2e/conftest.py`):

```python
import pytest
from playwright.async_api import async_playwright

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use playwright's event loop policy to prevent conflicts."""
    # Custom implementation needed
    pass
```

**Research Needed**: Investigate playwright's internal event loop management

## Impact Assessment

**Blocked Features**:

- ✅ Framework fully implemented and documented
- ❌ E2E tests cannot execute in CI (blocking release)
- ✅ All other validation layers working (static, unit, integration)

**Workaround Available**: Manual E2E testing possible locally

**Release Impact**: Cannot release v1.3.0 with E2E feature until tests pass

## Next Steps (Prioritized)

1. **Research**: Check latest pytest-playwright documentation for async configuration
2. **Test Locally**: Verify which solution works in local environment first
3. **Implement**: Apply chosen solution
4. **Validate**: Ensure tests pass in CI
5. **Document**: Update guides with final configuration
6. **Release**: Complete semantic-release cycle (v1.3.0)

## Lessons Learned

1. **Plugin Compatibility**: Always verify async plugin compatibility before implementation
2. **Version Pinning**: Consider pinning to specific tested versions
3. **Early CI Testing**: Test in CI environment early to catch integration issues
4. **Fallback Strategies**: Have sync test approach as backup option

## References

- pytest-playwright docs: https://playwright.dev/python/docs/test-runners
- pytest-asyncio docs: https://pytest-asyncio.readthedocs.io/
- Issue discussions: Check pytest-playwright GitHub issues for similar problems

---

**Status**: Awaiting decision on solution approach

**Assignee**: Implementation team

**Priority**: High (blocking feature release)
