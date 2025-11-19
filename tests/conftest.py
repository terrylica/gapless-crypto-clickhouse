"""
Pytest configuration and shared fixtures for gapless-crypto-data tests.

Session-scoped fixtures download real Binance data once per test session
and cache for reuse across all tests. This eliminates synthetic data usage
in integration tests while maintaining fast test execution.
"""

from pathlib import Path

import pandas as pd
import pytest


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
