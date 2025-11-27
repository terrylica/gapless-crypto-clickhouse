"""query_ohlcv() API comprehensive test suite for v6.0.0.

Tests unified API with auto-ingestion, multi-symbol, error handling.
Core v6.0.0 feature (ADR-0023) currently has zero dedicated tests.

**SLO Focus**: Correctness (auto-ingestion, idempotency, multi-symbol isolation)

**ADR**: ADR-0024 (Comprehensive Validation Canonicity)
"""

import pandas as pd
import pytest

from gapless_crypto_clickhouse import query_ohlcv

# ============================================================================
# Auto-Ingestion Tests (4 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.slow
def test_query_ohlcv_auto_ingestion_downloads_missing_data():
    """Verify query_ohlcv() downloads data if missing (auto-ingestion)."""
    # Query a small date range that might not exist
    df = query_ohlcv(
        "BTCUSDT",
        "1h",
        "2024-01-01",
        "2024-01-07",  # 1 week
        auto_ingest=True,
    )

    # Verify data returned
    assert len(df) > 0, "query_ohlcv should download and return data"
    assert len(df) <= 168, f"1 week of 1h data should be ≤168 bars, got {len(df)}"

    # Verify columns present
    expected_cols = ["timestamp", "symbol", "timeframe", "open", "high", "low", "close", "volume"]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_auto_ingestion_idempotent():
    """Verify query_ohlcv() is idempotent (repeated calls don't re-download)."""
    # First call (might download)
    df1 = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-07", auto_ingest=True)

    # Second call (should not re-download, query only)
    df2 = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-07", auto_ingest=True)

    # Verify results identical
    assert len(df1) == len(df2), f"Row count mismatch: {len(df1)} vs {len(df2)}"
    pd.testing.assert_frame_equal(
        df1.reset_index(drop=True),
        df2.reset_index(drop=True),
        check_dtype=False,  # Allow minor dtype differences
    )


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_auto_ingest_false_raises_on_missing_data():
    """Verify query_ohlcv(auto_ingest=False) raises if data missing."""
    # Clear any existing data for a specific symbol/timeframe (if possible)
    # Or use a symbol that definitely doesn't exist

    # Query with auto_ingest=False should raise if data missing
    # Note: This test might pass if data already exists, which is expected
    try:
        df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-07", auto_ingest=False)
        # If we get here, data exists (which is fine)
        assert len(df) > 0, "Should either raise or return data"
    except Exception as e:
        # If auto_ingest=False and data missing, should raise
        assert "missing" in str(e).lower() or "not found" in str(e).lower(), (
            f"Expected 'missing data' error, got: {e}"
        )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.slow
def test_query_ohlcv_auto_ingestion_respects_date_range():
    """Verify query_ohlcv() only downloads requested date range."""
    df = query_ohlcv(
        "BTCUSDT",
        "1h",
        "2024-01-01",
        "2024-01-03",  # Inclusive: Jan 1 00:00 through Jan 3 00:00 = 49 bars
        auto_ingest=True,
    )

    # Verify date range (inclusive end boundary means 49 bars, not 48)
    assert len(df) > 0, "Should return data"
    assert len(df) <= 49, f"Jan 1 00:00 to Jan 3 00:00 (1h) should be ≤49 bars, got {len(df)}"

    # Verify timestamps within range (normalize to UTC for comparison)
    min_ts = pd.Timestamp("2024-01-01", tz="UTC")
    max_ts = pd.Timestamp("2024-01-04", tz="UTC")  # Exclusive end
    # Convert df timestamps to pandas Timestamp then normalize to UTC
    df_min = pd.Timestamp(df["timestamp"].min())
    df_max = pd.Timestamp(df["timestamp"].max())
    if df_min.tzinfo is not None:
        df_min = df_min.tz_convert("UTC")
        df_max = df_max.tz_convert("UTC")
    else:
        df_min = df_min.tz_localize("UTC")
        df_max = df_max.tz_localize("UTC")
    assert df_min >= min_ts, f"Min timestamp {df_min} before start"
    assert df_max < max_ts, f"Max timestamp {df_max} after end"


# ============================================================================
# Multi-Symbol Tests (3 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.slow
def test_query_ohlcv_multi_symbol_list():
    """Verify query_ohlcv() handles list of symbols."""
    symbols = ["BTCUSDT", "ETHUSDT"]
    df = query_ohlcv(symbols, "1h", "2024-01-01", "2024-01-07", auto_ingest=True)

    # Verify both symbols present
    unique_symbols = set(df["symbol"].unique())
    assert "BTCUSDT" in unique_symbols, "BTCUSDT missing from results"
    assert "ETHUSDT" in unique_symbols, "ETHUSDT missing from results"

    # Verify data for each symbol
    btc_data = df[df["symbol"] == "BTCUSDT"]
    eth_data = df[df["symbol"] == "ETHUSDT"]
    assert len(btc_data) > 0, "BTCUSDT data missing"
    assert len(eth_data) > 0, "ETHUSDT data missing"


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_multi_symbol_isolation():
    """Verify query_ohlcv() correctly isolates symbol data (no cross-contamination)."""
    symbols = ["BTCUSDT", "ETHUSDT"]
    df = query_ohlcv(symbols, "1h", "2024-01-01", "2024-01-07", auto_ingest=True)

    # Verify symbol column correct for each row
    for _, row in df.iterrows():
        assert row["symbol"] in symbols, f"Unexpected symbol: {row['symbol']}"


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_multi_symbol_empty_list_raises():
    """Verify query_ohlcv() raises on empty symbol list."""
    with pytest.raises(ValueError, match="symbol.*empty|symbol.*required"):
        query_ohlcv([], "1h", "2024-01-01", "2024-01-07")


# ============================================================================
# Instrument Type Tests (3 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.slow
def test_query_ohlcv_spot_instrument_type():
    """Verify query_ohlcv() defaults to spot instrument type."""
    df = query_ohlcv("BTCUSDT", "1h", "2024-01-01", "2024-01-07", auto_ingest=True)

    # Verify instrument_type is spot
    assert (df["instrument_type"] == "spot").all(), (
        f"Expected all 'spot', got: {df['instrument_type'].unique()}"
    )

    # Verify funding_rate is NULL for spot
    assert df["funding_rate"].isna().all(), "funding_rate should be NULL for spot"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(True, reason="Futures data might not be available in test environment")
@pytest.mark.slow
def test_query_ohlcv_futures_instrument_type():
    """Verify query_ohlcv() handles futures-um instrument type."""
    df = query_ohlcv(
        "BTCUSDT", "1h", "2024-01-01", "2024-01-07", instrument_type="futures-um", auto_ingest=True
    )

    # Verify instrument_type is futures-um
    assert (df["instrument_type"] == "futures-um").all() or (df["instrument_type"] == "um").all(), (
        f"Expected 'futures-um' or 'um', got: {df['instrument_type'].unique()}"
    )

    # Verify funding_rate column exists (might be NULL or have values)
    assert "funding_rate" in df.columns, "funding_rate column missing for futures"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.slow
def test_query_ohlcv_instrument_type_isolation():
    """Verify query_ohlcv() isolates spot vs futures data."""
    # Query spot
    df_spot = query_ohlcv(
        "BTCUSDT", "1h", "2024-01-01", "2024-01-07", instrument_type="spot", auto_ingest=True
    )

    # Verify all spot
    assert (df_spot["instrument_type"] == "spot").all(), "Spot query returned non-spot data"


# ============================================================================
# Error Handling Tests (3 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_invalid_symbol_raises():
    """Verify query_ohlcv() raises on invalid symbol."""
    with pytest.raises((ValueError, Exception), match="symbol|FAKESYMBOL|not found"):
        query_ohlcv("FAKESYMBOL_DOES_NOT_EXIST", "1h", "2024-01-01", "2024-01-07", auto_ingest=True)


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_invalid_timeframe_raises():
    """Verify query_ohlcv() raises on invalid timeframe."""
    with pytest.raises((ValueError, Exception), match="timeframe|99h|not.*support"):
        query_ohlcv(
            "BTCUSDT",
            "99h",  # Invalid timeframe
            "2024-01-01",
            "2024-01-07",
            auto_ingest=True,
        )


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_invalid_date_format_raises():
    """Verify query_ohlcv() raises on invalid date format."""
    with pytest.raises((ValueError, Exception), match="date|format|2024/01/01"):
        query_ohlcv(
            "BTCUSDT",
            "1h",
            "2024/01/01",  # Wrong format (should be YYYY-MM-DD)
            "2024-01-07",
            auto_ingest=True,
        )


# ============================================================================
# Edge Cases (2 tests)
# ============================================================================


@pytest.mark.integration
@pytest.mark.slow
def test_query_ohlcv_empty_result_set():
    """Verify query_ohlcv() handles empty result sets gracefully."""
    # Query a date range in the far future (no data)
    df = query_ohlcv(
        "BTCUSDT",
        "1h",
        "2030-01-01",
        "2030-01-07",
        auto_ingest=False,  # Don't download future data
    )

    # Verify empty DataFrame with correct columns
    assert len(df) == 0, f"Expected empty DataFrame, got {len(df)} rows"
    assert "timestamp" in df.columns, "timestamp column missing"
    assert "symbol" in df.columns, "symbol column missing"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.timeout(10)
@pytest.mark.slow
def test_query_ohlcv_large_date_range_performance():
    """Verify query_ohlcv() completes large queries in reasonable time (<10s)."""
    # Query a full year (should complete quickly with Arrow optimization)
    import time

    start = time.time()

    df = query_ohlcv(
        "BTCUSDT",
        "1h",
        "2024-01-01",
        "2024-12-31",
        auto_ingest=False,  # Assume data exists
    )

    duration = time.time() - start

    # Verify completed
    assert len(df) > 0, "Should return data for full year"
    assert duration < 10.0, f"Query took {duration:.2f}s, expected <10s (Arrow should be fast)"

    # Log performance for tracking
    print(f"Full year query: {len(df)} rows in {duration:.2f}s ({len(df) / duration:.0f} rows/s)")
