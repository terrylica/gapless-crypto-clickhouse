# E2E Testing Guide

**Version**: 1.0.0
**Last Updated**: 2025-11-19
**ADR**: [ADR-0013](../decisions/0013-autonomous-validation-framework.md)

---

## Overview

This guide covers end-to-end (E2E) testing of ClickHouse web interfaces using Playwright 1.56+ and pytest 8.x. E2E tests validate actual user workflows with screenshot evidence for visual regression detection.

**Test Targets**:

- CH-UI Dashboard (localhost:5521)
- ClickHouse Play (localhost:8123/play)

**SLOs**:

- **Correctness**: Validates actual UI workflows (no mocks)
- **Observability**: Screenshots captured for all test states
- **Maintainability**: Accessibility-first locators resist UI changes

---

## Quick Start

### Prerequisites

1. **Docker**: ClickHouse and CH-UI containers running
2. **Python 3.12+**: Project Python version
3. **uv**: Package manager (auto-installs dependencies)

### Running E2E Tests

```bash
# Full validation suite (static + unit + integration + e2e)
uv run scripts/run_validation.py

# E2E tests only
uv run scripts/run_validation.py --e2e-only

# CI mode (headless, no interactive prompts)
uv run scripts/run_validation.py --ci

# Direct pytest execution (requires manual browser install)
uv run pytest tests/e2e/ -v --screenshot=only-on-failure
```

### First-Time Setup

```bash
# Install dependencies (includes Playwright)
uv sync

# Install Playwright browsers (one-time setup)
uv run playwright install chromium --with-deps

# Verify installation
uv run playwright --version
```

---

## Test Organization

### Directory Structure

```
tests/e2e/
├── conftest.py                     # Shared fixtures (browser config, screenshots)
├── test_ch_ui_dashboard.py         # CH-UI validation tests
├── test_clickhouse_play.py         # ClickHouse Play validation tests
└── screenshots/                    # Reference baselines (git-tracked)
```

### Test Categories

| Category | Marker                                       | Purpose                                                                  |
| -------- | -------------------------------------------- | ------------------------------------------------------------------------ |
| E2E      | `@pytest.mark.e2e`                           | End-to-end browser automation tests                                      |
| Async    | `@pytest.mark.asyncio(loop_scope="session")` | Async test execution with session-scoped event loop (pytest-playwright-asyncio) |
| Timeout  | `@pytest.mark.timeout(N)`                    | Explicit timeout override (default: 300s)                                |

---

## Writing E2E Tests

### Basic Test Pattern

```python
import pytest
from playwright.async_api import Page, expect
from pathlib import Path

@pytest.mark.e2e
@pytest.mark.asyncio(loop_scope="session")
async def test_example(page: Page, screenshot_dir: Path):
    """
    Test description.

    Verifies:
        - Specific behavior 1
        - Specific behavior 2

    SLO: Correctness - Expected behavior verified
    """
    # Navigate to page
    await page.goto("http://localhost:5521")

    # Interact with UI
    input_field = page.locator("input[type=text]").first
    await input_field.fill("SELECT 1")

    # Execute action
    button = page.locator("button").first
    await button.click()

    # Wait for results
    await page.wait_for_timeout(2000)

    # Capture screenshot
    screenshot_path = screenshot_dir / "test-example.png"
    await page.screenshot(path=screenshot_path, full_page=True)
    print(f"    📸 Screenshot saved: {screenshot_path}")

    # Assertions (optional - screenshot is primary evidence)
    assert await input_field.is_enabled()
```

### pytest-asyncio Configuration

pytest-playwright-asyncio requires session-scoped event loop configuration in `pytest.ini`:

```ini
# pytest.ini
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
```

**Why session scope?**
- pytest-playwright-asyncio provides async fixtures (e.g., `page`) that expect a session-scoped event loop
- Function-scoped loops cause `RuntimeError: Runner.run() cannot be called from a running event loop`
- All E2E tests must use `@pytest.mark.asyncio(loop_scope="session")` for compatibility

**Package Requirements**:
- `pytest-playwright-asyncio>=0.7.1` (official async support, replaces `pytest-playwright`)
- `pytest-asyncio>=0.26.0` (required version for session-scoped fixtures)

See `pyproject.toml` dev dependencies for exact versions.

### Locator Strategies (Priority Order)

1. **Accessibility-first** (recommended):

   ```python
   # By role and name
   button = page.get_by_role("button", name="Execute")
   input = page.get_by_label("Query")
   heading = page.get_by_role("heading", name="Dashboard")
   ```

2. **Fallback to CSS selectors**:

   ```python
   # When accessibility attributes not available
   input = page.locator("textarea, input[type=text]").first
   button = page.locator("button").first
   ```

3. **Avoid fragile selectors**:

   ```python
   # ❌ Brittle - breaks on DOM changes
   button = page.locator("div > div > button:nth-child(3)")

   # ✅ Stable - survives refactoring
   button = page.get_by_role("button", name="Submit")
   ```

---

## Debugging Failed Tests

### Artifacts Generated

E2E test failures generate these artifacts:

```
tmp/validation-artifacts/
├── screenshots/               # Screenshots for all tests
│   ├── test-name-success.png
│   └── test-name-failure.png
├── e2e-report.html            # HTML test report
└── traces/                    # Playwright traces (if enabled)
    └── test-name-trace.zip
```

### Viewing Traces

```bash
# View trace file for detailed debugging
playwright show-trace tmp/validation-artifacts/traces/test-name-trace.zip
```

Trace viewer shows:

- Network requests/responses
- Console logs
- DOM snapshots at each step
- Screenshots at each action
- Timing information

### Common Failure Patterns

#### Timeout Waiting for Element

**Symptom**: `TimeoutError: Timeout 5000ms exceeded`

**Causes**:

1. Element selector incorrect
2. Page still loading (need to wait for networkidle)
3. Element hidden/disabled

**Fix**:

```python
# Wait for page load
await page.goto("http://localhost:5521", wait_until="networkidle")

# Increase timeout
await page.locator("button").wait_for(state="visible", timeout=10000)

# Check if element exists
if await page.locator("button").is_visible():
    await page.locator("button").click()
```

#### Flaky Tests (Intermittent Failures)

**Symptom**: Test passes sometimes, fails other times

**Causes**:

1. Race conditions (async operations)
2. Network timing variability
3. Animation/transition interference

**Fix**:

```python
# Use Playwright's auto-waiting
await expect(page.locator(".result")).to_be_visible()  # Retries until visible

# Wait for specific state
await page.wait_for_load_state("networkidle")

# Disable animations (in conftest.py)
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "reduced_motion": "reduce",  # Disable animations
    }
```

---

## Screenshot Management

See: [Screenshot Baseline Guide](./SCREENSHOT_BASELINE.md) for baseline management process.

### Screenshot Capture Patterns

```python
# Full page screenshot
await page.screenshot(path="full-page.png", full_page=True)

# Specific element screenshot
element = page.locator(".result-table")
await element.screenshot(path="element.png")

# Screenshot on failure (automatic via conftest.py)
# No manual capture needed - pytest-playwright-asyncio handles it
```

---

## CI/CD Integration

### GitHub Actions

E2E tests run automatically in CI via `.github/workflows/ci.yml`:

```yaml
test-e2e:
  name: E2E Tests (Playwright)
  runs-on: ubuntu-latest
  services:
    clickhouse:
      image: clickhouse/clickhouse-server:24.11
  steps:
    - Install dependencies
    - Cache Playwright browsers
    - Wait for ClickHouse health
    - Run E2E tests
    - Upload artifacts on failure
```

**Browser Caching**: Playwright browsers (~150MB) cached for 30-60s speedup.

**Artifacts**: Screenshots and traces uploaded on failure (retention: 7 days).

### CI Test Execution

**CI Scope** (GitHub Actions):
- ✅ Runs: `tests/e2e/test_clickhouse_play.py` (6 tests) - ClickHouse Play interface validation
- ❌ Skips: `tests/e2e/test_ch_ui_dashboard.py` (6 tests) - CH-UI requires interactive configuration

**Rationale**: CH-UI requires web-based connection configuration (not CI-friendly). ClickHouse Play provides sufficient E2E framework validation and async event loop testing.

**Local Testing** (full 12-test suite):
```bash
docker-compose up -d
uv run pytest tests/e2e/ -v
```

See `.github/workflows/ci.yml` lines 131-132 for CI configuration details.

### Scheduled Validation

Comprehensive E2E validation runs every 6 hours via `.github/workflows/e2e-validation.yml`:

- Full test suite execution
- Cross-browser testing (future: Firefox, WebKit)
- Performance benchmarks (future)

---

## Best Practices

### DO

✅ Use accessibility-first locators (`get_by_role`, `get_by_label`)
✅ Capture screenshots for all test states
✅ Wait for explicit states (networkidle, visible, attached)
✅ Test error paths (invalid input, network failures)
✅ Add descriptive docstrings with SLO annotations

### DON'T

❌ Use fragile CSS selectors (nth-child, complex paths)
❌ Add arbitrary sleeps (use Playwright's auto-waiting)
❌ Skip screenshot capture (evidence is critical)
❌ Test implementation details (focus on user workflows)
❌ Ignore flaky tests (fix root cause immediately)

---

## Troubleshooting

### Docker Not Running

**Error**: `Environment Error: Docker daemon not running`

**Fix**:

```bash
docker compose up -d
```

### ClickHouse Not Healthy

**Error**: `ClickHouse container not healthy`

**Fix**:

```bash
# Check container status
docker ps --filter name=clickhouse

# View logs
docker logs gapless-clickhouse

# Restart container
docker compose restart clickhouse
```

### Playwright Browsers Not Installed

**Error**: `Playwright executable doesn't exist`

**Fix**:

```bash
# Install browsers with OS dependencies
uv run playwright install chromium --with-deps
```

### Port Conflicts

**Error**: `Port 8123 not accessible`

**Fix**:

```bash
# Check what's using the port
lsof -i :8123

# Kill conflicting process or use different ports
```

---

## Performance Considerations

### Test Execution Times

| Layer       | Tests | Duration | Parallelizable |
| ----------- | ----- | -------- | -------------- |
| Static      | -     | ~5s      | No             |
| Unit        | 71    | ~5-10s   | Yes            |
| Integration | ~10   | ~20-30s  | Limited        |
| E2E         | ~12   | ~30-60s  | Limited        |

### Optimization Strategies

1. **Browser Caching**: Cache Playwright browsers (30-60s speedup)
2. **Parallel Execution**: Run unit tests in parallel (`pytest -n auto`)
3. **Selective Testing**: Run E2E only when UI code changes
4. **Headless Mode**: Use headless browser in CI (faster rendering)

---

## Related Documentation

- [ADR-0013: Autonomous Validation Framework](../decisions/0013-autonomous-validation-framework.md)
- [Screenshot Baseline Guide](./SCREENSHOT_BASELINE.md)
- [Validation Overview](./OVERVIEW.md)
- [Playwright Python Docs](https://playwright.dev/python/docs/intro)

---

**Questions?** See project CLAUDE.md or file an issue on GitHub.
