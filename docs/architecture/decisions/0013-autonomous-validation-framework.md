# ADR-0013: Autonomous Validation Framework

- **Status**: Accepted
- **Date**: 2025-11-19
- **Decision Makers**: Eon Labs Engineering
- **Consulted**: 5-agent research team (DCTL methodology)
- **Informed**: Development team, CI/CD stakeholders

## Context and Problem Statement

Current validation gaps for ClickHouse integration (v1.0.0):

- **No E2E validation** for CH-UI dashboard (localhost:5521) or ClickHouse Play interface (localhost:8123/play)
- **Manual testing required** for web interface validation
- **No screenshot evidence** of correct UI rendering
- **CI/CD lacks E2E coverage** - only unit/integration tests (71 tests, 85% coverage)
- **Regression risk** for database query interface changes

**Problem**: How do we validate end-to-end workflows autonomously without manual intervention?

## Research Methodology

5-agent parallel investigation (2025-11-19) using DCTL methodology:

1. **Agent 1**: Playwright 1.56+ features and best practices
2. **Agent 2**: Pytest 8.x patterns with PEP 723 integration
3. **Agent 3**: Python tooling 2025 (Ruff, Mypy, uv)
4. **Agent 4**: GitHub Actions 2025 workflows
5. **Agent 5**: Autonomous validation system design

**Key Finding**: Modern tooling enables fully autonomous validation with zero manual intervention.

## Decision Drivers

- **Evidence-Based Validation**: Screenshots provide visual proof of correct rendering
- **Zero Manual Intervention**: PEP 723 self-contained scripts with auto-bootstrap
- **2025 Best Practices**: Playwright 1.56+ AI agents, pytest 8.x, Ruff 0.14.5
- **CI/CD Integration**: GitHub Actions matrix testing with artifact preservation
- **Production Quality**: Comprehensive test coverage (happy path, errors, edge cases, timeouts)

## Considered Options

### Option 1: Selenium + Manual Setup (Rejected)

**Pros**:

- Established ecosystem
- Familiar to many developers

**Cons**:

- Requires manual WebDriver management
- Slower than Playwright (no auto-waiting)
- No built-in screenshot comparison
- WebDriver downloads not cacheable

### Option 2: Cypress (Rejected)

**Pros**:

- Good developer experience
- Built-in screenshot testing

**Cons**:

- JavaScript-only (incompatible with Python codebase)
- Requires separate test runner
- No PEP 723 bootstrap capability

### Option 3: Playwright 1.56+ + pytest + PEP 723 (Accepted)

**Pros**:

- **Native Python integration** (pytest-playwright-asyncio)
- **AI-powered test agents** (Planner, Generator, Healer in 1.56+)
- **Auto-waiting mechanisms** (eliminates flaky tests)
- **Screenshot validation** with Pixelmatch
- **PEP 723 bootstrap** (self-contained execution)
- **GitHub Actions optimized** (browser caching, artifacts)
- **Accessibility-first** locators (`get_by_role()`)

**Cons**:

- Newer than Selenium (less historical adoption)
- Requires Playwright browser installation (automated via bootstrap)

## Decision

**Implement autonomous validation framework** using Playwright 1.56+, pytest 8.x, and PEP 723 inline dependencies.

### Architecture

**5-Layer Validation Model**:

1. **Static Analysis**: Ruff 0.14.5 linting + Mypy 1.18 type checking
2. **Unit Tests**: Existing 71 pytest tests (fast, isolated)
3. **Integration Tests**: Component interaction validation
4. **E2E Tests** (NEW): Playwright web interface validation with screenshots
5. **Benchmarking** (NEW): Performance regression detection

### Key Decisions

1. **Playwright 1.56+ for E2E**:
   - Validate CH-UI dashboard (localhost:5521)
   - Validate ClickHouse Play (localhost:8123/play)
   - Screenshot capture for visual regression detection

2. **PEP 723 Self-Contained Bootstrap**:
   - `scripts/run_validation.py` with inline dependencies
   - Auto-installs: playwright, pytest, pytest-playwright-asyncio, pytest-asyncio>=0.26.0, pytest-cov
   - Zero manual setup (uv handles everything)

3. **Comprehensive Test Coverage**:
   - Happy path: Successful queries, dashboard loads
   - Error cases: Invalid queries, network failures
   - Edge cases: Empty results, large datasets
   - Timeout scenarios: Slow queries, hung connections

4. **CI/CD Integration**:
   - GitHub Actions matrix (Python 3.12, 3.13)
   - Playwright browser caching (30-60s speedup)
   - Screenshot artifacts on failure (debugging evidence)
   - Branch coverage reporting

## Consequences

### Positive

- **Evidence-Based Confidence**: Screenshots prove correct UI rendering
- **Autonomous Execution**: PEP 723 bootstrap eliminates manual setup
- **Fast Feedback**: Playwright auto-waiting reduces flaky tests
- **Production Quality**: Comprehensive coverage (happy, error, edge, timeout)
- **CI/CD Optimized**: Browser caching, parallel execution, artifact preservation
- **Maintainability**: Accessibility-first locators resist UI churn

### Negative

- **Initial Setup Cost**: ~2-3 hours to implement full framework
- **Browser Dependencies**: Requires Chromium installation (~150MB, cached)
- **Learning Curve**: Team needs Playwright training (offset by AI agents)
- **CI Time Increase**: E2E tests add 30-60s per run (acceptable for quality gain)

### Neutral

- **Technology Stack Expansion**: Adds Playwright to existing pytest ecosystem
- **Documentation Burden**: Requires usage guide (offset by autonomous bootstrap)

## Validation

### Success Criteria

- [ ] All E2E tests pass locally via `uv run scripts/run_validation.py`
- [ ] Screenshots captured for CH-UI and ClickHouse Play
- [ ] CI/CD green with E2E tests in matrix
- [ ] Zero manual intervention required (PEP 723 bootstrap works)
- [ ] Code quality: Ruff clean, Mypy strict, 100% docstring coverage

### Rollback Plan

If Playwright integration proves problematic:

1. Remove E2E tests from CI (keep unit/integration only)
2. Revert to manual testing for web interfaces
3. Archive Playwright code for future consideration

## Implementation Plan

See: `docs/development/plan/0013-autonomous-validation-framework/plan.md`

## Related Decisions

- **ADR-0012**: Documentation Accuracy Remediation (governance methodology)
- **CURRENT_ARCHITECTURE_STATUS.yaml**: v1.0.0 validation strategy

## References

- [Playwright 1.56 Release Notes](https://playwright.dev/docs/release-notes)
- [PEP 723: Inline Script Metadata](https://peps.python.org/pep-0723/)
- [pytest 8.3 Documentation](https://docs.pytest.org/)
- [GitHub Actions Best Practices 2025](https://docs.github.com/en/actions)
- Research findings: 5-agent DCTL investigation (2025-11-19)

---

**Supersedes**: None (new capability)
**Superseded By**: None
**Status History**:

- 2025-11-19: Proposed → Accepted (research completed, plan approved)
