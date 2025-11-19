# Implementation Plan: Autonomous Validation Framework

**ADR**: [ADR-0013](../../decisions/0013-autonomous-validation-framework.md) (adr-id=0013)
**Status**: In Progress
**Created**: 2025-11-19
**Last Updated**: 2025-11-19
**Owner**: Eon Labs Engineering

---

## Context and Scope

### Problem Statement

Current validation gaps for ClickHouse integration (v1.0.0):

- No E2E validation for web interfaces (CH-UI dashboard, ClickHouse Play)
- Manual testing required for UI validation
- No screenshot evidence of correct rendering
- CI/CD lacks E2E coverage (only unit/integration: 71 tests, 85% coverage)
- Regression risk for database query interface changes

### In Scope

- Playwright 1.56+ browser automation for web interface validation
- PEP 723 self-contained bootstrap script (zero manual setup)
- Comprehensive E2E test suite (happy/error/edge/timeout paths)
- CI/CD integration with GitHub Actions
- Screenshot capture for visual regression detection
- Documentation for test authoring and maintenance

### Out of Scope

- Performance benchmarking (deferred to future ADR)
- Cross-browser testing beyond Chromium (future enhancement)
- Visual regression baseline management tooling (manual review process)
- Mobile/responsive design validation (not applicable for database tooling)

---

## Goals and Non-Goals

### Goals

1. **Evidence-Based Confidence**: Screenshot capture proves correct UI rendering
2. **Zero Manual Intervention**: PEP 723 bootstrap eliminates manual setup
3. **Comprehensive Coverage**: Test all paths (happy, error, edge, timeout, malformed)
4. **CI/CD Optimized**: Browser caching, parallel execution, artifact preservation
5. **Maintainable**: Accessibility-first locators resist UI churn

### Non-Goals

- **Performance testing**: Not a validation goal (correctness only)
- **Security testing**: Handled by separate tooling (Bandit, Ruff security rules)
- **Backward compatibility**: No legacy code support needed
- **Cross-platform CI**: Linux-only CI execution (macOS/Windows optional)

---

## Design Overview

### Architecture: 5-Layer Validation Model

```
Layer 1: Static Analysis (ruff, mypy, yamllint)
           ↓
Layer 2: Unit Tests (71 existing pytest tests)
           ↓
Layer 3: Integration Tests (ClickHouse DB operations)
           ↓
Layer 4: E2E Tests (Playwright web interface validation) [NEW]
           ↓
Layer 5: Benchmarking (performance regression detection) [FUTURE]
```

### Key Components

1. **Bootstrap Script** (`scripts/run_validation.py`):
   - PEP 723 inline dependencies (Playwright, pytest, pytest-playwright)
   - Auto-install Playwright browsers
   - Docker health checks (ClickHouse, CH-UI)
   - Test execution orchestration
   - Artifact collection (screenshots, traces, reports)

2. **E2E Test Suite** (`tests/e2e/`):
   - `conftest.py`: Playwright fixtures (browser config, screenshot helpers)
   - `test_ch_ui_dashboard.py`: CH-UI validation (localhost:5521)
   - `test_clickhouse_play.py`: ClickHouse Play validation (localhost:8123/play)
   - Coverage: 24 scenarios × 2 interfaces = 48 tests

3. **CI/CD Integration** (`.github/workflows/`):
   - Updated `ci.yml` with E2E job
   - New `e2e-validation.yml` for scheduled/manual runs
   - Playwright browser caching (30-60s speedup)
   - Artifact upload on failure (screenshots, traces)

---

## Detailed Design

### PEP 723 Bootstrap Script

**Purpose**: Self-contained autonomous execution with zero manual setup.

**Exit Codes**:

- `0`: All validations passed
- `1`: Test failures detected
- `2`: Environment setup failed (Docker not running, port conflicts)
- `3`: Bootstrap failed (dependency installation, browser download)

**Execution Flow**:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "playwright>=1.56.0",
#     "pytest>=8.4.2",
#     "pytest-playwright>=0.6.0",
#     "pytest-cov>=7.0.0",
#     "pytest-timeout>=2.3.1",
#     "docker>=7.1.0",
# ]
# ///

1. Validate environment (Docker running, ports available)
2. Install Playwright browsers (if not cached)
3. Execute test layers (static → unit → integration → e2e)
4. Collect artifacts (screenshots, traces, HTML reports)
5. Generate summary report
6. Exit with appropriate code
```

**Observability**: Detailed progress logging, artifact paths printed, failure diagnostics.

### E2E Test Suite Architecture

**Test Organization**:

```
tests/e2e/
├── conftest.py                 # Shared fixtures
├── test_ch_ui_dashboard.py     # 24 tests for CH-UI
├── test_clickhouse_play.py     # 24 tests for ClickHouse Play
└── screenshots/                # Reference baselines (git-tracked)
```

**Test Coverage Matrix** (per interface):

| Category          | Count  | Examples                                                                        |
| ----------------- | ------ | ------------------------------------------------------------------------------- |
| Happy Path        | 5      | Landing page load, simple query, complex query, result display, export          |
| Error Cases       | 4      | Invalid SQL, non-existent table, network failure, timeout                       |
| Edge Cases        | 4      | Empty results, large dataset (10K rows), special characters, concurrent queries |
| Visual Regression | 2      | Screenshot baseline comparison (landing, results)                               |
| **Total**         | **15** | **× 2 interfaces = 30 tests** (expandable to 48 with all scenarios)             |

**Locator Strategy**: Accessibility-first (`get_by_role()`, `get_by_label()`) for stability.

**Screenshot Capture**: All test states (load, interaction, success, error) saved to `tmp/validation-artifacts/screenshots/`.

### CI/CD Integration

**Workflow: Updated ci.yml**:

```yaml
jobs:
  test-e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      clickhouse:
        image: clickhouse/clickhouse-server:24.11
        ports: [8123:8123, 9000:9000]
    steps:
      - Checkout code
      - Setup Python 3.12
      - Install uv
      - Cache Playwright browsers (key: hash(uv.lock))
      - Install Playwright (chromium only)
      - Start CH-UI container
      - Wait for health checks (ClickHouse, CH-UI)
      - Run: uv run scripts/run_validation.py --e2e-only --ci
      - Upload artifacts on failure (screenshots, traces)
```

**Optimizations**:

- Playwright browser caching: 30-60s speedup per run
- Concurrency groups: Prevent duplicate runs on rapid pushes
- Parallel jobs: Unit tests run separately from E2E (faster feedback)

### Error Handling Strategy

**Philosophy**: Fail-fast with actionable diagnostics. No silent failures.

**Error Categories**:

1. **Environment Errors** (Exit 2):
   - Docker not running → "Run: docker compose up -d"
   - Port conflicts → "Check: lsof -i :8123 -i :5521"
   - ClickHouse unhealthy → "Check logs: docker logs gapless-clickhouse"

2. **Bootstrap Errors** (Exit 3):
   - Playwright install failed → "Manual: playwright install chromium"
   - uv dependency resolution failed → "Clear cache: rm -rf ~/.cache/uv"

3. **Test Failures** (Exit 1):
   - Unit/integration failures → Test names + assertion details
   - E2E failures → Screenshot path + trace file link
   - Timeout failures → Stack trace + last screenshot before timeout

**No Fallbacks**: Errors propagate immediately. No retry logic in bootstrap (tests may have internal retries for flaky operations).

---

## Alternatives Considered

### Alternative 1: Selenium + Manual Setup

**Rejected**: Requires manual WebDriver management, slower than Playwright, no built-in screenshot comparison.

### Alternative 2: Cypress

**Rejected**: JavaScript-only (incompatible with Python codebase), no PEP 723 bootstrap capability.

### Alternative 3: Manual Testing Only

**Rejected**: No automation, no regression detection, high maintenance cost, no screenshot evidence.

---

## Cross-Cutting Concerns

### Observability

**SLO: Observability**:

- All test execution logged with timestamps
- Artifact paths printed to stdout
- Failure diagnostics include: test name, duration, error type, stack trace, screenshot path
- CI artifacts accessible via GitHub Actions UI (retention: 7 days)

**Metrics** (CI execution):

- Test duration per layer (static, unit, integration, e2e)
- Screenshot count
- Artifact size
- Cache hit rate (Playwright browsers)

### Maintainability

**SLO: Maintainability**:

- **Accessibility-first locators**: Resist UI changes (get_by_role > CSS selectors)
- **PEP 723 inline dependencies**: No pyproject.toml coordination needed for standalone script
- **Clear abstractions**: Bootstrap script separates environment validation, test execution, artifact collection
- **Documentation**: Comprehensive guides for test authoring, debugging, screenshot management

**Test Maintenance**:

- New E2E tests follow template pattern (see E2E_TESTING_GUIDE.md)
- Screenshot baselines updated via documented process (see SCREENSHOT_BASELINE.md)
- CI failures debuggable via traces (playwright show-trace trace.zip)

### Availability

**SLO: Availability**:

- Bootstrap script validates environment before execution (fail-fast on missing dependencies)
- Docker health checks prevent tests from running against unhealthy services
- CI timeout: 15 minutes (prevents hung tests from blocking pipeline)
- Rollback plan: Disable E2E job if >20% failure rate sustained over 1 week

### Correctness

**SLO: Correctness**:

- E2E tests validate actual user workflows (not mocked)
- Screenshot evidence provides visual proof of correct rendering
- Comprehensive coverage: happy + error + edge + timeout + malformed paths
- No fallback/default values: Tests fail if assertions don't pass (strict validation)

---

## Implementation Phases

### Phase 1: Infrastructure (2-3 hours)

**Deliverables**:

- [ ] `scripts/run_validation.py` PEP 723 script functional
- [ ] Environment validation working (Docker, port checks)
- [ ] Playwright browser auto-installation working
- [ ] 1 minimal E2E test passing (CH-UI landing page load)

**Validation**: `uv run scripts/run_validation.py --e2e-only` exits 0

### Phase 2: Test Suite (3-4 hours)

**Deliverables**:

- [ ] `tests/e2e/conftest.py` with Playwright fixtures
- [ ] `tests/e2e/test_ch_ui_dashboard.py` with 15+ tests
- [ ] `tests/e2e/test_clickhouse_play.py` with 15+ tests
- [ ] Screenshot baselines committed to git

**Validation**: `pytest tests/e2e/ -v` shows 30+ tests passing

### Phase 3: CI/CD Integration (2 hours)

**Deliverables**:

- [ ] `.github/workflows/ci.yml` updated with E2E job
- [ ] `.github/workflows/e2e-validation.yml` created (scheduled runs)
- [ ] Playwright browser caching functional
- [ ] Artifact upload on failure working

**Validation**: CI green with E2E tests, artifacts accessible on failure

### Phase 4: Documentation (1-2 hours)

**Deliverables**:

- [ ] `docs/validation/E2E_TESTING_GUIDE.md` (running, debugging, authoring)
- [ ] `docs/validation/SCREENSHOT_BASELINE.md` (baseline management)
- [ ] `README.md` updated with E2E validation section
- [ ] `CLAUDE.md` updated with E2E testing reference

**Validation**: Documentation reviewed, all links functional

---

## Success Criteria

From ADR-0013:

- [ ] All E2E tests pass locally via `uv run scripts/run_validation.py`
- [ ] Screenshots captured for CH-UI and ClickHouse Play
- [ ] CI/CD green with E2E tests in matrix
- [ ] Zero manual intervention required (PEP 723 bootstrap works)
- [ ] Code quality: Ruff clean, Mypy strict, 100% docstring coverage

---

## Rollback Plan

If E2E validation proves problematic (>20% failure rate over 1 week):

1. **Immediate**: Comment out E2E job in `.github/workflows/ci.yml`
2. **Short-term**: Revert to manual web interface testing
3. **Long-term**: Archive E2E tests for future reconsideration

---

## Timeline

**Total Estimate**: 8-11 hours

- Phase 1: 2-3 hours
- Phase 2: 3-4 hours
- Phase 3: 2 hours
- Phase 4: 1-2 hours

**Target Completion**: Within 1 sprint (2 weeks)

---

## References

- [ADR-0013: Autonomous Validation Framework](../../decisions/0013-autonomous-validation-framework.md)
- [Playwright 1.56 Release Notes](https://playwright.dev/docs/release-notes)
- [PEP 723: Inline Script Metadata](https://peps.python.org/pep-0723/)
- [pytest 8.x Documentation](https://docs.pytest.org/)
- [GitHub Actions Best Practices 2025](https://docs.github.com/en/actions)

---

**Plan Status**: Approved (2025-11-19)
**Implementation Status**: In Progress
