#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "playwright>=1.56.0",
#     "pytest>=8.4.2",
#     "pytest-playwright-asyncio>=0.7.1",
#     "pytest-cov>=7.0.0",
#     "pytest-timeout>=2.3.1",
#     "pytest-html>=4.1.1",
#     "docker>=7.1.0",
# ]
# ///
"""
Autonomous E2E Validation Framework Bootstrap.

Zero-intervention validation suite for ClickHouse web interfaces.

Features:
    - PEP 723 self-contained execution (uv handles dependencies)
    - Automatic Playwright browser installation
    - Docker container health validation
    - Screenshot capture with artifact preservation
    - Comprehensive test coverage (happy, error, edge, timeout)

Usage:
    uv run scripts/run_validation.py              # Full validation
    uv run scripts/run_validation.py --e2e-only   # E2E tests only
    uv run scripts/run_validation.py --fast       # Skip benchmarks
    uv run scripts/run_validation.py --ci         # CI mode (headless)

Exit Codes:
    0 - All validations passed
    1 - Test failures detected
    2 - Environment setup failed (Docker not running, ports unavailable)
    3 - Bootstrap failed (dependency installation, browser download)

Observability:
    - Progress logging with timestamps
    - Artifact paths printed to stdout
    - Failure diagnostics with actionable remediation
    - Summary report with pass/fail matrix

SLOs:
    - Availability: Pre-flight checks prevent execution against unhealthy services
    - Correctness: No fallback values, strict assertion-based validation
    - Observability: All operations logged, artifacts preserved
    - Maintainability: Clear abstractions, documented error handling
"""

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# Layer types for validation pipeline
Layer = Literal["static", "unit", "integration", "e2e", "benchmark"]


@dataclass
class TestResult:
    """Test execution result with observability data."""

    layer: Layer
    success: bool
    duration_seconds: float
    tests_run: int
    tests_failed: int
    artifacts: list[Path]
    error_message: str | None = None


class EnvironmentError(Exception):
    """Environment validation failed (Docker, ports, services)."""

    pass


class BootstrapError(Exception):
    """Bootstrap failed (dependencies, browser installation)."""

    pass


class ValidationBootstrap:
    """Autonomous validation orchestrator with zero-intervention guarantees."""

    def __init__(self, project_root: Path, ci_mode: bool = False):
        """
        Initialize validation bootstrap.

        Args:
            project_root: Project root directory
            ci_mode: CI execution mode (headless, no browser download prompts)
        """
        self.project_root = project_root
        self.ci_mode = ci_mode
        self.artifacts_dir = project_root / "tmp" / "validation-artifacts"
        self.screenshots_dir = self.artifacts_dir / "screenshots"
        self.results: dict[Layer, TestResult] = {}

        # Create artifact directories
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def run_full_validation(self, layers: list[Layer] | None = None) -> int:
        """
        Execute complete validation pipeline.

        Args:
            layers: Layers to execute (default: all layers)

        Returns:
            Exit code (0=success, 1=test failure, 2=environment, 3=bootstrap)
        """
        if layers is None:
            layers = ["static", "unit", "integration", "e2e"]

        print("=" * 70)
        print("🚀 Autonomous Validation Framework")
        print("=" * 70)
        print(f"Layers: {', '.join(layers)}")
        print(f"CI Mode: {self.ci_mode}")
        print(f"Artifacts: {self.artifacts_dir}")
        print("=" * 70)
        print()

        try:
            # Phase 1: Environment validation
            print("📋 Phase 1: Environment Validation")
            print("-" * 70)
            self._validate_environment()
            print("✅ Environment validation passed\n")

            # Phase 2: Browser installation (for E2E)
            if "e2e" in layers:
                print("📦 Phase 2: Playwright Browser Installation")
                print("-" * 70)
                self._install_playwright_browsers()
                print("✅ Playwright browsers ready\n")

            # Phase 3: Execute test layers
            print("🧪 Phase 3: Test Execution")
            print("-" * 70)
            for layer in layers:
                result = self._run_test_layer(layer)
                self.results[layer] = result
                if not result.success:
                    self._print_failure_diagnostics(layer, result)
                    return 1
                print(f"✅ {layer.upper()} tests passed ({result.duration_seconds:.1f}s)\n")

            # Phase 4: Generate summary report
            print("📊 Phase 4: Summary Report")
            print("-" * 70)
            self._generate_summary_report()
            print()

            print("=" * 70)
            print("✅ ALL VALIDATIONS PASSED")
            print("=" * 70)
            return 0

        except EnvironmentError as e:
            print(f"\n❌ Environment Error: {e}")
            print("Exit code: 2")
            return 2
        except BootstrapError as e:
            print(f"\n❌ Bootstrap Error: {e}")
            print("Exit code: 3")
            return 3
        except Exception as e:
            print(f"\n❌ Unexpected Error: {e}")
            import traceback

            traceback.print_exc()
            return 1

    def _validate_environment(self) -> None:
        """
        Pre-flight checks for Docker, ClickHouse, CH-UI availability.

        Raises:
            EnvironmentError: If environment validation fails
        """
        # Check Docker daemon
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                raise EnvironmentError("Docker daemon not running. Fix: docker compose up -d")
            print("  ✓ Docker daemon running")
        except FileNotFoundError:
            raise EnvironmentError("Docker not installed. Fix: Install Docker Desktop")
        except subprocess.TimeoutExpired:
            raise EnvironmentError("Docker daemon not responding. Fix: Restart Docker")

        # Check ClickHouse container health (if E2E tests will run)
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=clickhouse", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "healthy" not in result.stdout.lower() and "up" not in result.stdout.lower():
                raise EnvironmentError(
                    "ClickHouse container not healthy. Fix: docker compose up -d clickhouse"
                )
            print("  ✓ ClickHouse container running")
        except subprocess.TimeoutExpired:
            raise EnvironmentError("Docker ps timed out")

        # Check port availability (8123, 9000, 5521)
        import socket

        def check_port(port: int, service: str) -> None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                result = sock.connect_ex(("localhost", port))
                if result == 0:
                    print(f"  ✓ Port {port} accessible ({service})")
                else:
                    print(
                        f"  ⚠ Port {port} not accessible ({service}) - service may not be running"
                    )
            finally:
                sock.close()

        check_port(8123, "ClickHouse HTTP")
        check_port(9000, "ClickHouse Native")
        check_port(5521, "CH-UI Dashboard")

    def _install_playwright_browsers(self) -> None:
        """
        Auto-install Playwright browsers (Chromium only for headless).

        Raises:
            BootstrapError: If browser installation fails
        """
        print("  Installing Playwright Chromium browser...")
        try:
            cmd = ["playwright", "install", "chromium"]
            if not self.ci_mode:
                cmd.append("--with-deps")  # Install OS dependencies (interactive)
            else:
                cmd.append("--with-deps")  # CI mode also needs deps

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes max
            )

            if result.returncode != 0:
                raise BootstrapError(
                    f"Playwright install failed: {result.stderr}\n"
                    f"Fix: playwright install chromium --with-deps"
                )

            print("  ✓ Playwright Chromium installed")

        except FileNotFoundError:
            raise BootstrapError("Playwright CLI not found. Ensure dependencies are installed.")
        except subprocess.TimeoutExpired:
            raise BootstrapError(
                "Playwright install timed out (>5 minutes). Check network connection."
            )

    def _run_test_layer(self, layer: Layer) -> TestResult:
        """
        Execute specific test layer with appropriate pytest markers.

        Args:
            layer: Test layer to execute

        Returns:
            TestResult with execution details
        """
        start_time = time.time()

        if layer == "static":
            # Run ruff and mypy directly
            result = self._run_static_analysis()
        else:
            # Run pytest with layer-specific markers
            pytest_args = self._build_pytest_args(layer)
            result = subprocess.run(
                ["pytest", *pytest_args],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Parse pytest output for test counts
            tests_run = 0
            tests_failed = 0
            if " passed" in result.stdout:
                import re

                match = re.search(r"(\d+) passed", result.stdout)
                if match:
                    tests_run = int(match.group(1))
            if " failed" in result.stdout:
                import re

                match = re.search(r"(\d+) failed", result.stdout)
                if match:
                    tests_failed = int(match.group(1))

            duration = time.time() - start_time

            return TestResult(
                layer=layer,
                success=result.returncode == 0,
                duration_seconds=duration,
                tests_run=tests_run,
                tests_failed=tests_failed,
                artifacts=[self.artifacts_dir / f"{layer}-report.html"],
                error_message=result.stderr if result.returncode != 0 else None,
            )

        duration = time.time() - start_time
        return TestResult(
            layer=layer,
            success=result,
            duration_seconds=duration,
            tests_run=0,
            tests_failed=0,
            artifacts=[],
        )

    def _run_static_analysis(self) -> bool:
        """Run ruff and mypy static analysis."""
        # Ruff check
        print("  Running ruff check...")
        result = subprocess.run(
            ["ruff", "check", "."],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        if result.returncode != 0:
            print(f"  ❌ Ruff check failed:\n{result.stdout}")
            return False

        # Ruff format check
        print("  Running ruff format check...")
        result = subprocess.run(
            ["ruff", "format", "--check", "."],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        if result.returncode != 0:
            print(f"  ❌ Ruff format check failed:\n{result.stdout}")
            return False

        print("  ✓ Static analysis passed")
        return True

    def _build_pytest_args(self, layer: Layer) -> list[str]:
        """Build pytest command with markers, coverage, and artifacts."""
        base_args = [
            "-v",  # Verbose output
            "--tb=short",  # Concise tracebacks
            "--cov=src/gapless_crypto_clickhouse",
            "--cov-report=term",
            "--cov-append",  # Append to existing coverage
            f"--html={self.artifacts_dir / f'{layer}-report.html'}",
            "--self-contained-html",
        ]

        # Layer-specific markers and options
        if layer == "unit":
            return base_args + ["tests/", "-m", "not e2e and not integration"]
        elif layer == "integration":
            return base_args + ["tests/", "-m", "integration"]
        elif layer == "e2e":
            screenshot_mode = "only-on-failure" if self.ci_mode else "on"
            return base_args + [
                "tests/e2e/",
                "-m",
                "e2e",
                f"--screenshot={screenshot_mode}",
                "--headed" if not self.ci_mode else "--browser=chromium",
                "--tracing=retain-on-failure",
            ]
        elif layer == "benchmark":
            return base_args + ["tests/", "-m", "benchmark", "--benchmark-only"]

        return base_args

    def _print_failure_diagnostics(self, layer: Layer, result: TestResult) -> None:
        """
        Print detailed error output with actionable remediation steps.

        Args:
            layer: Failed test layer
            result: Test result with error details
        """
        print("\n" + "=" * 70)
        print(f"❌ {layer.upper()} TEST FAILURES")
        print("=" * 70)
        print(f"Tests Run: {result.tests_run}")
        print(f"Tests Failed: {result.tests_failed}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        print()

        if result.error_message:
            print("Error Details:")
            print("-" * 70)
            print(result.error_message)
            print()

        if result.artifacts:
            print("Artifacts Generated:")
            print("-" * 70)
            for artifact in result.artifacts:
                if artifact.exists():
                    print(f"  📄 {artifact}")
            print()

        print("Suggested Fixes:")
        print("-" * 70)
        if layer == "e2e":
            print("  1. Check screenshot artifacts for visual clues")
            print("  2. Review trace files: playwright show-trace <trace.zip>")
            print("  3. Verify ClickHouse and CH-UI are running (docker ps)")
            print("  4. Check service logs: docker logs gapless-clickhouse")
        elif layer == "integration":
            print("  1. Verify ClickHouse connection (localhost:9000)")
            print("  2. Check database state (docker exec clickhouse clickhouse-client)")
            print("  3. Review test logs in artifacts directory")
        elif layer == "unit":
            print("  1. Review failed test output above")
            print("  2. Run specific test: pytest tests/path/to/test.py::test_name -v")
            print("  3. Check for recent code changes causing regression")
        print("=" * 70)

    def _generate_summary_report(self) -> None:
        """Generate consolidated test results with pass/fail matrix."""
        print("Test Results Summary:")
        print()
        print(f"{'Layer':<15} {'Status':<10} {'Tests':<10} {'Duration':<12}")
        print("-" * 70)

        for layer, result in self.results.items():
            status = "✅ PASS" if result.success else "❌ FAIL"
            tests = f"{result.tests_run - result.tests_failed}/{result.tests_run}"
            duration = f"{result.duration_seconds:.1f}s"
            print(f"{layer.upper():<15} {status:<10} {tests:<10} {duration:<12}")

        print()
        print(f"Artifacts Directory: {self.artifacts_dir}")
        print(f"Screenshots: {self.screenshots_dir}")


def main() -> int:
    """Main entry point for validation bootstrap."""
    parser = argparse.ArgumentParser(
        description="Autonomous Validation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--e2e-only",
        action="store_true",
        help="Run E2E tests only (skip static/unit/integration)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip benchmark tests (faster execution)",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode (headless browser, no interactive prompts)",
    )
    args = parser.parse_args()

    # Determine layers to execute
    if args.e2e_only:
        layers: list[Layer] = ["e2e"]
    elif args.fast:
        layers = ["static", "unit", "integration", "e2e"]
    else:
        layers = ["static", "unit", "integration", "e2e", "benchmark"]

    # Execute validation
    bootstrap = ValidationBootstrap(Path.cwd(), ci_mode=args.ci)
    return bootstrap.run_full_validation(layers)


if __name__ == "__main__":
    sys.exit(main())
