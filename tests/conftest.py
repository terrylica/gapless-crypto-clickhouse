"""
Pytest configuration and shared fixtures for gapless-crypto-data tests.

Session-scoped fixtures download real Binance data once per test session
and cache for reuse across all tests. This eliminates synthetic data usage
in integration tests while maintaining fast test execution.

ClickHouse Auto-Start (ADR-0044, ADR-0045):
    The `ensure_local_clickhouse` fixture automatically starts the local
    ClickHouse server if a clickhouse binary can be found. This provides a
    smooth new-user experience without manual server management.

    Discovery is PATH-first and toolchain-agnostic; see `_clickhouse_binary`.
    It is deliberately not tied to any one toolchain manager, because it was
    previously pinned to a mise shim path that ceased to exist.
"""

import os
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

# =============================================================================
# LOCAL CLICKHOUSE AUTO-START (ADR-0044, ADR-0045)
# =============================================================================

PORT_LOCAL_HTTP = 8123
STARTUP_TIMEOUT_SEC = 15

# Where to look for the clickhouse binary, in order.
#
# This used to be a single hardcoded constant pointing at mise's shim directory
# (`~/.local/share/mise/shims/clickhouse`). mise was retired machine-wide -- proto is the
# only toolchain manager -- so that path stopped existing and `_is_clickhouse_installed()`
# became permanently False. The result was not a skip but 12 hard ERRORs out of
# tests/test_local_clickhouse_e2e.py (ADR-0045 mandates fail-hard, and
# `require_local_clickhouse` honours it), on a machine where ClickHouse was installed all
# along at /opt/homebrew/bin/clickhouse. The error even told the reader to fix it by
# installing a tool this machine deliberately does not have.
#
# PATH first, because that is what proto's shims, Homebrew, and a plain system install all
# feed into -- it is the tool-agnostic answer and needs no updating when the toolchain
# manager changes again. The explicit paths afterwards are a fallback for a shell whose
# PATH has not been through profile activation (a bare pytest run from an IDE, say). The
# mise entry is retained ONLY so a machine that still has one keeps working; it is
# deliberately last and must not be reinstated as the primary.
_CLICKHOUSE_FALLBACK_PATHS = (
    Path.home() / ".proto/shims/clickhouse",
    Path("/opt/homebrew/bin/clickhouse"),
    Path("/usr/local/bin/clickhouse"),
    Path.home() / ".local/share/mise/shims/clickhouse",
)


def _clickhouse_binary() -> Path | None:
    """Resolve the clickhouse binary, or None if it is not installed anywhere we look."""
    found = shutil.which("clickhouse")
    if found:
        return Path(found)
    for candidate in _CLICKHOUSE_FALLBACK_PATHS:
        if candidate.is_file():
            return candidate
    return None


def _is_clickhouse_installed() -> bool:
    """Check whether a clickhouse binary is available by any means."""
    return _clickhouse_binary() is not None


def _is_clickhouse_running() -> bool:
    """Check if local ClickHouse server is running on port 8123."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", PORT_LOCAL_HTTP))
        sock.close()
        return result == 0
    except Exception:
        return False


def _start_clickhouse_server() -> bool:
    """Start local ClickHouse server in daemon mode.

    Returns:
        True if server started successfully, False otherwise.
    """
    binary = _clickhouse_binary()
    if binary is None:
        return False

    if _is_clickhouse_running():
        return True  # Already running

    # `clickhouse server` writes its data tree (store/, metadata/, metadata_dropped/,
    # cores/, status, uuid) relative to the working directory and offers no --path flag.
    # Started from the repo checkout it litters the repo root with untracked server state
    # -- which is exactly what happened the first time these tests actually ran. Give it a
    # directory of its own outside the repo.
    data_dir = Path(
        os.environ.get("CLICKHOUSE_DATA_DIR")
        or Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
        / "gapless-crypto-clickhouse"
        / "server"
    )
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Start server in daemon mode
        subprocess.run(
            [str(binary), "server", "--daemon"],
            check=True,
            capture_output=True,
            timeout=10,
            cwd=data_dir,
        )

        # Wait for server to be ready
        for _ in range(STARTUP_TIMEOUT_SEC):
            if _is_clickhouse_running():
                return True
            time.sleep(1)

        return False
    except (subprocess.SubprocessError, OSError):
        return False


@pytest.fixture(scope="session")
def ensure_local_clickhouse():
    """Session-scoped fixture that auto-starts local ClickHouse if available.

    This fixture provides a smooth new-user experience:
    - If mise ClickHouse is installed: auto-starts server if not running
    - If not installed: returns status dict (tests can skip based on this)

    Usage in tests:
        def test_something(ensure_local_clickhouse):
            if not ensure_local_clickhouse["available"]:
                pytest.skip("Local ClickHouse not available")
            # ... test code ...

    Returns:
        dict: Status with keys:
            - installed: bool - mise ClickHouse is installed
            - running: bool - server is running (or was started)
            - available: bool - ready for use (installed AND running)
            - error: str | None - error message if startup failed
    """
    status = {
        "installed": _is_clickhouse_installed(),
        "running": False,
        "available": False,
        "error": None,
    }

    if not status["installed"]:
        searched = ", ".join(str(p) for p in _CLICKHOUSE_FALLBACK_PATHS)
        status["error"] = (
            "clickhouse binary not found on PATH or at any known location "
            f"({searched}). Install it (e.g. `brew install clickhouse`) or put it on PATH."
        )
        return status

    # Try to start if not running
    if _is_clickhouse_running():
        status["running"] = True
        status["available"] = True
    else:
        if _start_clickhouse_server():
            status["running"] = True
            status["available"] = True
        else:
            status["error"] = f"Failed to start ClickHouse server within {STARTUP_TIMEOUT_SEC}s"

    return status


@pytest.fixture(scope="session")
def require_local_clickhouse(ensure_local_clickhouse):
    """Session-scoped fixture that REQUIRES local ClickHouse to be available.

    Fails the test immediately if ClickHouse is not available.
    Use this for tests that absolutely require ClickHouse.

    Usage:
        def test_database_query(require_local_clickhouse):
            # This test will fail (not skip) if ClickHouse unavailable
            # ... test code ...
    """
    if not ensure_local_clickhouse["available"]:
        pytest.fail(
            f"Local ClickHouse required but not available: "
            f"{ensure_local_clickhouse.get('error', 'Unknown error')}"
        )
    return ensure_local_clickhouse


@pytest.fixture
def test_data_dir():
    """Path to test data fixtures directory."""
    return Path(__file__).parent / "fixtures" / "test_data"


@pytest.fixture
def test_data_large_dir():
    """Path to large test data fixtures directory."""
    return Path(__file__).parent / "fixtures" / "test_data_large"


@pytest.fixture
def project_root():
    """Path to project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_data_dir():
    """Path to sample data directory in source."""
    return Path(__file__).parent.parent / "src" / "gapless_crypto_clickhouse" / "sample_data"


@pytest.fixture(scope="session")
def real_btcusdt_1h_sample(tmp_path_factory):
    """Real BTCUSDT 1h data from Binance (2 days, ~48 rows).

    Downloads once per pytest session and caches for all tests. This replaces
    synthetic OHLCV data generation in integration tests with authentic Binance
    market data.

    SLO Targets:
        Correctness: Tests validate against real Binance OHLCV structure
        Maintainability: Single fixture eliminates 3+ synthetic data generators

    Returns:
        pd.DataFrame: Real BTCUSDT 1h OHLCV data (2024-01-01 to 2024-01-02)
    """
    from gapless_crypto_clickhouse.collectors.binance_public_data_collector import (
        BinancePublicDataCollector,
    )

    # Session-scoped temp directory (persists across all tests in session)
    cache_dir = tmp_path_factory.mktemp("real_data_cache")

    try:
        # Download real Binance data once
        collector = BinancePublicDataCollector(
            symbol="BTCUSDT",
            start_date="2024-01-01",
            end_date="2024-01-02",
            output_dir=cache_dir,
        )

        # Collect data (creates CSV file)
        result = collector.collect_timeframe_data("1h")

        if result is None:
            pytest.skip("Failed to download real Binance data - network issue")

        # Find the created CSV file and read it
        csv_files = list(cache_dir.glob("*.csv"))
        if not csv_files:
            pytest.skip("No CSV file created - data collection failed")

        csv_file = csv_files[0]
        df = pd.read_csv(csv_file, comment="#")

        if len(df) == 0:
            pytest.skip("Downloaded data is empty")

        return df

    except Exception as e:
        # Graceful skip on network failure
        pytest.skip(f"Real data download failed: {e}")


@pytest.fixture
def real_btcusdt_1h_sample_copy(real_btcusdt_1h_sample):
    """Copy of real BTCUSDT data for mutation tests.

    Use this when tests need to modify the DataFrame (e.g., introducing gaps,
    testing validation). Prevents tests from affecting each other through
    shared state.

    Returns:
        pd.DataFrame: Fresh copy of real BTCUSDT 1h data
    """
    return real_btcusdt_1h_sample.copy()


# =============================================================================
# Gap Filling Fixtures (ADR-0041)
# =============================================================================


@pytest.fixture
def sample_gap_dataframe():
    """Sample gap DataFrame for gap filling unit tests.

    Returns a DataFrame matching the structure from detect_gaps() with
    fixed dates for reproducibility.

    Returns:
        pd.DataFrame: Gap DataFrame with gap_start, gap_end, missing_rows columns
    """
    return pd.DataFrame(
        {
            "gap_start": [
                pd.Timestamp("2024-11-01 00:00:00", tz="UTC"),
                pd.Timestamp("2024-11-03 12:00:00", tz="UTC"),
            ],
            "gap_end": [
                pd.Timestamp("2024-11-01 06:00:00", tz="UTC"),
                pd.Timestamp("2024-11-03 18:00:00", tz="UTC"),
            ],
            "missing_rows": [6, 6],
        }
    )


@pytest.fixture
def sample_api_kline_response():
    """Sample Binance API kline response for mocking.

    Returns a list of kline arrays matching the Binance REST API format:
    [open_time, open, high, low, close, volume, close_time,
     quote_volume, trades, taker_buy_base, taker_buy_quote, ignore]

    Returns:
        List[List]: Raw kline data from Binance API (3 rows for testing)
    """
    base_time = int(datetime(2024, 11, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    hour_ms = 3600 * 1000

    return [
        [
            base_time,  # open_time
            "95000.00",  # open
            "95500.00",  # high
            "94800.00",  # low
            "95200.00",  # close
            "1234.567",  # volume
            base_time + hour_ms - 1,  # close_time
            "117300000.00",  # quote_asset_volume
            50000,  # number_of_trades
            "600.123",  # taker_buy_base_asset_volume
            "57000000.00",  # taker_buy_quote_asset_volume
            "0",  # ignore
        ],
        [
            base_time + hour_ms,
            "95200.00",
            "95800.00",
            "95100.00",
            "95600.00",
            "1456.789",
            base_time + 2 * hour_ms - 1,
            "139200000.00",
            52000,
            "700.456",
            "66900000.00",
            "0",
        ],
        [
            base_time + 2 * hour_ms,
            "95600.00",
            "96000.00",
            "95400.00",
            "95900.00",
            "1678.901",
            base_time + 3 * hour_ms - 1,
            "161200000.00",
            55000,
            "800.789",
            "76800000.00",
            "0",
        ],
    ]


@pytest.fixture
def sample_api_candle_dicts():
    """Sample candle dictionaries from fetch_gap_data().

    Returns structured dictionaries matching the output of fetch_gap_data()
    after conversion from raw API response.

    Note: Timestamps are naive UTC (codebase convention per connection.py:205).
    fetch_gap_data() returns naive UTC datetimes.

    Returns:
        List[dict]: Candle dictionaries with naive UTC datetime objects
    """
    # Naive UTC datetimes (no tzinfo) - matches fetch_gap_data() output
    return [
        {
            "timestamp": datetime(2024, 11, 1, 0, 0, 0),  # naive UTC
            "open": 95000.00,
            "high": 95500.00,
            "low": 94800.00,
            "close": 95200.00,
            "volume": 1234.567,
            "close_time": datetime(2024, 11, 1, 0, 59, 59),  # naive UTC
            "quote_asset_volume": 117300000.00,
            "number_of_trades": 50000,
            "taker_buy_base_asset_volume": 600.123,
            "taker_buy_quote_asset_volume": 57000000.00,
        },
        {
            "timestamp": datetime(2024, 11, 1, 1, 0, 0),  # naive UTC
            "open": 95200.00,
            "high": 95800.00,
            "low": 95100.00,
            "close": 95600.00,
            "volume": 1456.789,
            "close_time": datetime(2024, 11, 1, 1, 59, 59),  # naive UTC
            "quote_asset_volume": 139200000.00,
            "number_of_trades": 52000,
            "taker_buy_base_asset_volume": 700.456,
            "taker_buy_quote_asset_volume": 66900000.00,
        },
        {
            "timestamp": datetime(2024, 11, 1, 2, 0, 0),  # naive UTC
            "open": 95600.00,
            "high": 96000.00,
            "low": 95400.00,
            "close": 95900.00,
            "volume": 1678.901,
            "close_time": datetime(2024, 11, 1, 2, 59, 59),  # naive UTC
            "quote_asset_volume": 161200000.00,
            "number_of_trades": 55000,
            "taker_buy_base_asset_volume": 800.789,
            "taker_buy_quote_asset_volume": 76800000.00,
        },
    ]
