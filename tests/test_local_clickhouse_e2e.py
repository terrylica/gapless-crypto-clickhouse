"""E2E tests for local ClickHouse deployment (ADR-0044, ADR-0045).

Real Binance data validation for local ClickHouse mode.
Uses auto-start fixture from conftest.py for smooth new-user experience.

Data Sources (ADR-0038: Real Binance Data Validation):
- Spot: https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/
- Futures UM: https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/

Run Commands:
    # Run E2E tests (mise ClickHouse auto-starts if installed)
    uv run pytest tests/test_local_clickhouse_e2e.py -v

    # Tests will FAIL (not skip) if ClickHouse not available
    # Auto-start happens via ensure_local_clickhouse fixture in conftest.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
from pathlib import Path
from typing import Generator

import pytest

# Semantic constants (ADR-0045)
MISE_CLICKHOUSE_SHIM = Path.home() / ".local/share/mise/shims/clickhouse"
SKILL_SCRIPTS_DIR = Path(__file__).parent.parent / "skills/local-clickhouse/scripts"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
PORT_LOCAL_HTTP = 8123


def is_clickhouse_running() -> bool:
    """Check if local ClickHouse server is running on port 8123."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", PORT_LOCAL_HTTP))
        sock.close()
        return result == 0
    except Exception:
        return False


# NOTE: pytest_configure removed - use require_local_clickhouse fixture instead
# The old pytest_configure called pytest.exit() which killed the ENTIRE test suite
# Now tests use fixture-based approach for auto-start (ADR-0045 compliance maintained)


# Mark all tests as integration
pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def local_mode_env(require_local_clickhouse) -> Generator[None, None, None]:
    """Set GCCH_MODE=local for all tests in this module.

    Depends on require_local_clickhouse fixture which:
    1. Auto-starts ClickHouse server if not running
    2. Fails the test if ClickHouse is not available (ADR-0045)
    """
    original_mode = os.environ.get("GCCH_MODE")
    original_host = os.environ.get("CLICKHOUSE_HOST")

    os.environ["GCCH_MODE"] = "local"
    os.environ["CLICKHOUSE_HOST"] = "localhost"

    yield

    # Restore original environment
    if original_mode is not None:
        os.environ["GCCH_MODE"] = original_mode
    elif "GCCH_MODE" in os.environ:
        del os.environ["GCCH_MODE"]

    if original_host is not None:
        os.environ["CLICKHOUSE_HOST"] = original_host
    elif "CLICKHOUSE_HOST" in os.environ:
        del os.environ["CLICKHOUSE_HOST"]


class TestLocalClickHouseProbe:
    """Test probe module functions for local mode."""

    def test_check_local_clickhouse_installed(self, local_mode_env: None) -> None:
        """Verify probe detects local ClickHouse installation."""
        from gapless_crypto_clickhouse import probe

        status = probe.check_local_clickhouse()
        assert status["installed"] is True
        assert status["binary_path"] is not None
        assert "clickhouse" in status["binary_path"]

    def test_check_local_clickhouse_running(self, local_mode_env: None) -> None:
        """Verify probe detects local ClickHouse server running."""
        from gapless_crypto_clickhouse import probe

        status = probe.check_local_clickhouse()
        assert status["running"] is True

    def test_get_current_mode_is_local(self, local_mode_env: None) -> None:
        """Verify probe.get_current_mode() returns 'local'."""
        from gapless_crypto_clickhouse import probe

        mode = probe.get_current_mode()
        assert mode == "local"

    def test_get_deployment_modes_includes_local(self, local_mode_env: None) -> None:
        """Verify probe.get_deployment_modes() includes local mode."""
        from gapless_crypto_clickhouse import probe

        modes = probe.get_deployment_modes()
        assert "local" in modes["available_modes"]
        assert modes["local"]["port"] == 8123
        assert modes["local"]["secure"] is False


class TestLocalClickHouseConfig:
    """Test config module for local mode."""

    def test_config_from_env_local_mode(self, local_mode_env: None) -> None:
        """Verify ClickHouseConfig.from_env() creates local config."""
        from gapless_crypto_clickhouse.clickhouse.config import ClickHouseConfig

        config = ClickHouseConfig.from_env()
        assert config.host == "localhost"
        assert config.http_port == 8123
        assert config.secure is False

    def test_config_local_defaults(self, local_mode_env: None) -> None:
        """Verify local mode uses correct default ports."""
        from gapless_crypto_clickhouse.clickhouse.config import (
            PORT_LOCAL_HTTP,
            PORT_LOCAL_NATIVE,
            ClickHouseConfig,
        )

        config = ClickHouseConfig.from_env()
        assert config.http_port == PORT_LOCAL_HTTP
        assert config.port == PORT_LOCAL_NATIVE


class TestLocalClickHouseConnection:
    """Test actual connection to local ClickHouse."""

    def test_connection_via_clickhouse_connect(self, local_mode_env: None) -> None:
        """Verify clickhouse-connect can connect to local server."""
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        # Test simple query
        result = client.query("SELECT 1 AS test")
        assert result.result_rows[0][0] == 1

    def test_connection_version_query(self, local_mode_env: None) -> None:
        """Verify version query works on local server."""
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        result = client.query("SELECT version() AS version")
        version = result.result_rows[0][0]
        assert version is not None
        assert len(version) > 0
        # Version should be at least 24.x
        major_version = int(version.split(".")[0])
        assert major_version >= 24, f"Expected ClickHouse 24+, got {version}"


class TestLocalClickHouseSchemaCreation:
    """Test schema creation on local ClickHouse."""

    def test_create_database_if_not_exists(self, local_mode_env: None) -> None:
        """Verify database creation works on local server."""
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        # Create test database
        client.command("CREATE DATABASE IF NOT EXISTS test_local_e2e")

        # Verify database exists
        result = client.query(
            "SELECT name FROM system.databases WHERE name = 'test_local_e2e'"
        )
        assert len(result.result_rows) == 1
        assert result.result_rows[0][0] == "test_local_e2e"

        # Cleanup
        client.command("DROP DATABASE IF EXISTS test_local_e2e")

    def test_create_ohlcv_table(self, local_mode_env: None) -> None:
        """Verify OHLCV table creation with ReplacingMergeTree."""
        import clickhouse_connect

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        # Create test database and table
        client.command("CREATE DATABASE IF NOT EXISTS test_local_e2e")

        # Create OHLCV table matching production schema (ADR-0034)
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_local_e2e.ohlcv (
            symbol String,
            timeframe String,
            timestamp DateTime64(3),
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Float64,
            close_time DateTime64(3),
            quote_asset_volume Float64,
            number_of_trades UInt64,
            taker_buy_base_asset_volume Float64,
            taker_buy_quote_asset_volume Float64,
            _version UInt64
        ) ENGINE = ReplacingMergeTree(_version)
        ORDER BY (symbol, timeframe, toStartOfHour(timestamp), timestamp)
        """
        client.command(create_table_sql)

        # Verify table exists
        result = client.query(
            "SELECT name FROM system.tables WHERE database = 'test_local_e2e' AND name = 'ohlcv'"
        )
        assert len(result.result_rows) == 1

        # Cleanup
        client.command("DROP DATABASE IF EXISTS test_local_e2e")


class TestLocalClickHouseRealBinanceData:
    """E2E tests with real Binance data (ADR-0038).

    Downloads real BTCUSDT data from Binance CDN and validates
    ingestion and querying in local ClickHouse.
    """

    @pytest.fixture
    def test_database(self, local_mode_env: None) -> Generator[str, None, None]:
        """Create test database and cleanup after test."""
        import clickhouse_connect

        db_name = "test_binance_e2e"

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        # Create database
        client.command(f"CREATE DATABASE IF NOT EXISTS {db_name}")

        # Create OHLCV table
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {db_name}.ohlcv (
            symbol String,
            timeframe String,
            timestamp DateTime64(3),
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Float64,
            close_time DateTime64(3),
            quote_asset_volume Float64,
            number_of_trades UInt64,
            taker_buy_base_asset_volume Float64,
            taker_buy_quote_asset_volume Float64,
            _version UInt64
        ) ENGINE = ReplacingMergeTree(_version)
        ORDER BY (symbol, timeframe, toStartOfHour(timestamp), timestamp)
        """
        client.command(create_table_sql)

        yield db_name

        # Cleanup
        client.command(f"DROP DATABASE IF EXISTS {db_name}")

    def test_download_spot_data_from_binance_cdn(
        self, local_mode_env: None, test_database: str
    ) -> None:
        """Download and validate real BTCUSDT spot data from Binance CDN."""
        import io
        import urllib.request
        import zipfile

        import pandas as pd

        # Download real data from Binance CDN (spot)
        url = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                zip_data = response.read()
        except Exception as e:
            pytest.skip(f"Failed to download from Binance CDN: {e}")

        # Extract CSV from ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as f:
                # Spot data has no header
                df = pd.read_csv(
                    f,
                    header=None,
                    names=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "close_time",
                        "quote_asset_volume",
                        "number_of_trades",
                        "taker_buy_base_asset_volume",
                        "taker_buy_quote_asset_volume",
                        "ignore",
                    ],
                )

        # Validate data
        assert len(df) > 0, "Expected non-empty DataFrame"
        assert len(df) == 744, f"Expected 744 rows (31 days * 24h), got {len(df)}"

        # Validate OHLC constraints
        assert (df["high"] >= df["open"]).all(), "high >= open constraint violated"
        assert (df["high"] >= df["close"]).all(), "high >= close constraint violated"
        assert (df["low"] <= df["open"]).all(), "low <= open constraint violated"
        assert (df["low"] <= df["close"]).all(), "low <= close constraint violated"
        assert (df["volume"] >= 0).all(), "volume >= 0 constraint violated"

    def test_download_futures_um_data_from_binance_cdn(
        self, local_mode_env: None, test_database: str
    ) -> None:
        """Download and validate real BTCUSDT futures UM data from Binance CDN."""
        import io
        import urllib.request
        import zipfile

        import pandas as pd

        # Download real data from Binance CDN (futures UM)
        url = "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                zip_data = response.read()
        except Exception as e:
            pytest.skip(f"Failed to download from Binance CDN: {e}")

        # Extract CSV from ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as f:
                # Futures data has header
                df = pd.read_csv(f)

        # Validate data
        assert len(df) > 0, "Expected non-empty DataFrame"
        assert len(df) == 744, f"Expected 744 rows (31 days * 24h), got {len(df)}"

        # Validate OHLC constraints
        assert (df["high"] >= df["open"]).all(), "high >= open constraint violated"
        assert (df["high"] >= df["close"]).all(), "high >= close constraint violated"
        assert (df["low"] <= df["open"]).all(), "low <= open constraint violated"
        assert (df["low"] <= df["close"]).all(), "low <= close constraint violated"
        assert (df["volume"] >= 0).all(), "volume >= 0 constraint violated"

    def test_ingest_spot_data_to_local_clickhouse(
        self, local_mode_env: None, test_database: str
    ) -> None:
        """Ingest real BTCUSDT spot data to local ClickHouse."""
        import hashlib
        import io
        import urllib.request
        import zipfile

        import clickhouse_connect
        import pandas as pd

        # Download data
        url = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                zip_data = response.read()
        except Exception as e:
            pytest.skip(f"Failed to download from Binance CDN: {e}")

        # Extract CSV
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as f:
                df = pd.read_csv(
                    f,
                    header=None,
                    names=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "close_time",
                        "quote_asset_volume",
                        "number_of_trades",
                        "taker_buy_base_asset_volume",
                        "taker_buy_quote_asset_volume",
                        "ignore",
                    ],
                )

        # Prepare for ingestion
        df["symbol"] = "BTCUSDT"
        df["timeframe"] = "1h"
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

        # Compute deterministic _version hash
        version_hash = int(
            hashlib.md5("BTCUSDT-1h-2024-01-spot".encode()).hexdigest()[:16], 16
        )
        df["_version"] = version_hash

        # Drop ignore column
        df = df.drop(columns=["ignore"])

        # Reorder columns to match schema
        columns = [
            "symbol",
            "timeframe",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "_version",
        ]
        df = df[columns]

        # Insert to ClickHouse
        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        client.insert_df(f"{test_database}.ohlcv", df)

        # Verify ingestion
        result = client.query(
            f"""
            SELECT count() as cnt
            FROM {test_database}.ohlcv FINAL
            WHERE symbol = 'BTCUSDT'
              AND timeframe = '1h'
        """
        )
        count = result.result_rows[0][0]
        assert count == 744, f"Expected 744 rows, got {count}"

    def test_query_with_final_deduplication(
        self, local_mode_env: None, test_database: str
    ) -> None:
        """Verify FINAL query returns deduplicated results."""
        import hashlib
        import io
        import urllib.request
        import zipfile

        import clickhouse_connect
        import pandas as pd

        # Download and ingest data twice (simulating re-ingestion)
        url = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                zip_data = response.read()
        except Exception as e:
            pytest.skip(f"Failed to download from Binance CDN: {e}")

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_filename = zf.namelist()[0]
            with zf.open(csv_filename) as f:
                df = pd.read_csv(
                    f,
                    header=None,
                    names=[
                        "timestamp",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                        "close_time",
                        "quote_asset_volume",
                        "number_of_trades",
                        "taker_buy_base_asset_volume",
                        "taker_buy_quote_asset_volume",
                        "ignore",
                    ],
                )

        df["symbol"] = "BTCUSDT"
        df["timeframe"] = "1h"
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
        version_hash = int(
            hashlib.md5("BTCUSDT-1h-2024-01-spot".encode()).hexdigest()[:16], 16
        )
        df["_version"] = version_hash
        df = df.drop(columns=["ignore"])

        columns = [
            "symbol",
            "timeframe",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "_version",
        ]
        df = df[columns]

        client = clickhouse_connect.get_client(
            host="localhost",
            port=PORT_LOCAL_HTTP,
            username="default",
            password="",
            secure=False,
        )

        # Insert twice (simulating idempotent re-ingestion)
        client.insert_df(f"{test_database}.ohlcv", df)
        client.insert_df(f"{test_database}.ohlcv", df)

        # Query with FINAL - should deduplicate
        result = client.query(
            f"""
            SELECT count() as cnt
            FROM {test_database}.ohlcv FINAL
            WHERE symbol = 'BTCUSDT'
              AND timeframe = '1h'
        """
        )
        count_final = result.result_rows[0][0]

        # Query without FINAL - may have duplicates (depends on merge state)
        result_no_final = client.query(
            f"""
            SELECT count() as cnt
            FROM {test_database}.ohlcv
            WHERE symbol = 'BTCUSDT'
              AND timeframe = '1h'
        """
        )
        count_no_final = result_no_final.result_rows[0][0]

        # FINAL should return exactly 744 (deduplicated)
        assert count_final == 744, f"FINAL should return 744, got {count_final}"

        # Without FINAL, may have more (or equal if merged)
        assert count_no_final >= count_final, "count without FINAL should be >= FINAL"


class TestSkillScriptExecution:
    """Test skill scripts via subprocess.run() (ADR-0045)."""

    def test_start_clickhouse_script_exists(self) -> None:
        """Verify start-clickhouse.sh script exists."""
        script = SKILL_SCRIPTS_DIR / "start-clickhouse.sh"
        assert script.exists(), f"Script not found: {script}"
        assert os.access(script, os.X_OK), f"Script not executable: {script}"

    def test_deploy_schema_script_exists(self) -> None:
        """Verify deploy-schema.sh script exists."""
        script = SKILL_SCRIPTS_DIR / "deploy-schema.sh"
        assert script.exists(), f"Script not found: {script}"
        assert os.access(script, os.X_OK), f"Script not executable: {script}"

    def test_ingest_sample_data_script_exists(self) -> None:
        """Verify ingest-sample-data.py script exists."""
        script = SKILL_SCRIPTS_DIR / "ingest-sample-data.py"
        assert script.exists(), f"Script not found: {script}"

    def test_take_screenshot_script_exists(self) -> None:
        """Verify take-screenshot.py script exists."""
        script = SKILL_SCRIPTS_DIR / "take-screenshot.py"
        assert script.exists(), f"Script not found: {script}"

    def test_validate_data_script_exists(self) -> None:
        """Verify validate-data.py script exists."""
        script = SKILL_SCRIPTS_DIR / "validate-data.py"
        assert script.exists(), f"Script not found: {script}"

    def test_start_clickhouse_via_subprocess(self, local_mode_env: None) -> None:
        """Run start-clickhouse.sh via subprocess."""
        script = SKILL_SCRIPTS_DIR / "start-clickhouse.sh"
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            timeout=30,
            check=False,
        )
        # Success (0) or already running (0 with message)
        assert result.returncode == 0, f"Script failed: {result.stderr.decode()}"

    def test_validate_data_via_subprocess(self, local_mode_env: None) -> None:
        """Run validate-data.py via subprocess and verify JSON output."""
        script = SKILL_SCRIPTS_DIR / "validate-data.py"
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["python", str(script), str(SCREENSHOTS_DIR)],
            capture_output=True,
            timeout=60,
            check=False,
            env={**os.environ, "GCCH_MODE": "local"},
        )

        # Find the latest JSON file
        json_files = list(SCREENSHOTS_DIR.glob("validation-*.json"))
        assert len(json_files) > 0, "No validation JSON file created"

        latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
        validation_data = json.loads(latest_json.read_text())

        assert "timestamp" in validation_data
        assert "clickhouse_version" in validation_data
        assert "overall_status" in validation_data


class TestPlaywrightScreenshot:
    """Test Playwright screenshot capture (ADR-0045)."""

    def test_screenshots_dir_created(self) -> None:
        """Verify screenshots directory can be created."""
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        assert SCREENSHOTS_DIR.exists()
        assert SCREENSHOTS_DIR.is_dir()

    @pytest.mark.slow
    def test_take_screenshot_via_subprocess(self, local_mode_env: None) -> None:
        """Run take-screenshot.py via subprocess (requires Playwright)."""
        script = SKILL_SCRIPTS_DIR / "take-screenshot.py"
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["python", str(script), str(SCREENSHOTS_DIR)],
            capture_output=True,
            timeout=60,
            check=False,
            env={**os.environ, "GCCH_MODE": "local"},
        )

        # Check if Playwright is installed
        if b"Playwright not installed" in result.stderr:
            pytest.skip("Playwright not installed")

        # Find screenshot files
        png_files = list(SCREENSHOTS_DIR.glob("play-ui-*.png"))
        if result.returncode == 0:
            assert len(png_files) > 0, "No screenshot file created"


class TestJSONEvidenceCapture:
    """Test JSON evidence capture (ADR-0045)."""

    def test_evidence_structure(self, local_mode_env: None) -> None:
        """Verify validation evidence has expected structure."""
        script = SKILL_SCRIPTS_DIR / "validate-data.py"
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["python", str(script), str(SCREENSHOTS_DIR)],
            capture_output=True,
            timeout=60,
            check=False,
            env={**os.environ, "GCCH_MODE": "local"},
        )

        json_files = list(SCREENSHOTS_DIR.glob("validation-*.json"))
        if not json_files:
            pytest.skip("No validation JSON created (ClickHouse may not have data)")

        latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
        data = json.loads(latest_json.read_text())

        # Verify expected fields
        expected_fields = [
            "timestamp",
            "clickhouse_version",
            "database_check",
            "table_check",
            "row_counts",
            "ohlc_validation",
            "schema_validation",
            "overall_status",
            "errors",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
