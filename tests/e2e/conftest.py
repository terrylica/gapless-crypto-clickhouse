"""
E2E Test Fixtures and Configuration.

Playwright browser configuration and shared utilities for E2E validation
of ClickHouse web interfaces (CH-UI dashboard, ClickHouse Play).

Fixtures:
    - browser_context_args: Browser context configuration (viewport, video recording)
    - screenshot_dir: Artifact directory for test screenshots

Note: Uses pytest-playwright's built-in 'page' fixture (no custom override needed)

SLOs:
    - Observability: All page interactions logged, screenshots on failure
    - Maintainability: Accessibility-first fixture patterns
    - Correctness: No fallback configurations, explicit settings only
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def screenshot_dir(tmp_path_factory) -> Path:
    """
    Session-scoped directory for test screenshots.

    Returns:
        Path to screenshot directory (tmp/validation-artifacts/screenshots/)

    Observability:
        - Directory path logged during session setup
        - Persists across all E2E tests in session
    """
    artifacts = tmp_path_factory.mktemp("e2e-screenshots")
    print(f"\n📸 Screenshot directory: {artifacts}")
    return artifacts


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Playwright browser context configuration.

    Returns:
        Dict with browser context settings (viewport, video, etc.)

    Configuration:
        - Viewport: 1920x1080 (standard desktop resolution)
        - Video recording: Disabled (use tracing instead for smaller artifacts)
        - HTTPS errors: Ignored (localhost testing)
        - Timezone: UTC (consistent timestamps)

    SLOs:
        - Maintainability: Explicit configuration, no defaults
        - Correctness: No fallback values, all settings intentional
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,  # Localhost testing
        "timezone_id": "UTC",  # Consistent timestamps
        # Video disabled - use tracing for debugging (smaller artifacts)
        "record_video_dir": None,
    }


# pytest-asyncio compatibility hook
# Prevents pytest-asyncio from managing E2E tests (let playwright handle async)
def pytest_collection_modifyitems(items):
    """Remove asyncio markers from E2E tests to avoid event loop conflicts."""
    for item in items:
        if "e2e" in item.keywords:
            # Remove asyncio marker - pytest-playwright will handle async execution
            item.own_markers = [
                marker for marker in item.own_markers
                if marker.name != "asyncio"
            ]


# Markers configuration
def pytest_configure(config):
    """Register custom markers for E2E tests."""
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests requiring Playwright and running services",
    )
