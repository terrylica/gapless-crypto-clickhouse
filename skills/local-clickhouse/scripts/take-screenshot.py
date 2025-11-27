#!/usr/bin/env python3
"""ADR-0045: Capture Playwright screenshot of ClickHouse Play UI.

Navigates to local ClickHouse Play UI and captures a screenshot
showing the query interface with sample data.

Usage:
    python take-screenshot.py [output_dir]
    # Default output: tests/screenshots/play-ui-{timestamp}.png

Exit codes:
    0: Success
    1: ClickHouse not available
    2: Playwright failed
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Semantic constants (ADR-0045)
PORT_LOCAL_HTTP = 8123
PLAY_UI_URL = f"http://localhost:{PORT_LOCAL_HTTP}/play"
DEFAULT_SCREENSHOTS_DIR = "tests/screenshots"
SCREENSHOT_PATTERN = "play-ui-{timestamp}.png"
SAMPLE_QUERY = "SELECT symbol, timeframe, count() as rows FROM ohlcv FINAL GROUP BY symbol, timeframe ORDER BY rows DESC LIMIT 10"


def check_clickhouse_available() -> bool:
    """Check if local ClickHouse is running."""
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", PORT_LOCAL_HTTP))
        sock.close()
        return result == 0
    except Exception:
        return False


def main() -> int:
    """Capture Play UI screenshot."""
    # Determine output directory
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_SCREENSHOTS_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check ClickHouse availability
    if not check_clickhouse_available():
        print(f"ERROR: ClickHouse not running on localhost:{PORT_LOCAL_HTTP}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = output_dir / SCREENSHOT_PATTERN.format(timestamp=timestamp)

        print(f"Opening Play UI: {PLAY_UI_URL}")
        print(f"Screenshot will be saved to: {screenshot_path}")

        with sync_playwright() as p:
            # Launch browser (headless for automation)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # Navigate to Play UI
            page.goto(PLAY_UI_URL)
            page.wait_for_load_state("networkidle")

            # Type query into the editor
            # Play UI uses Monaco editor, need to click and type
            editor = page.locator("textarea, .monaco-editor")
            if editor.count() > 0:
                page.click(".monaco-editor")
                page.keyboard.type(SAMPLE_QUERY)
                page.wait_for_timeout(500)  # Let editor update

            # Click Run button
            run_button = page.locator("text=Run")
            if run_button.count() > 0:
                run_button.click()
                page.wait_for_timeout(2000)  # Wait for query results

            # Take screenshot
            page.screenshot(path=str(screenshot_path), full_page=False)
            browser.close()

        print(f"Screenshot saved: {screenshot_path}")
        return 0

    except ImportError:
        print("ERROR: Playwright not installed. Run: uv pip install playwright && playwright install chromium", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: Screenshot failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
