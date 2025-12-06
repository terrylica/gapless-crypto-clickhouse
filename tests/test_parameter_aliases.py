"""Tests for parameter aliases (start/end vs start_date/end_date)."""

import pytest

import gapless_crypto_clickhouse as gcch


def test_legacy_start_end_parameters_download():
    """Legacy start/end parameters continue working in download()."""
    df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0
    assert "timestamp" in df.columns


def test_new_start_date_end_date_aliases_download():
    """New start_date/end_date aliases work correctly in download()."""
    df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0
    assert "timestamp" in df.columns


def test_both_forms_produce_same_results_download():
    """Legacy and new forms produce identical results in download()."""
    df1 = gcch.download("BTCUSDT", "1h", start="2024-01-01", end="2024-01-02")
    df2 = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end_date="2024-01-02")

    assert len(df1) == len(df2)
    # Both should have same data
    assert df1["timestamp"].min() == df2["timestamp"].min()
    assert df1["timestamp"].max() == df2["timestamp"].max()


def test_conflict_start_and_start_date_raises_error_download():
    """Specifying both start and start_date raises ValueError in download()."""
    with pytest.raises(ValueError, match="Cannot specify both 'start' and 'start_date'"):
        gcch.download("BTCUSDT", "1h", start="2024-01-01", start_date="2024-01-02")


def test_conflict_end_and_end_date_raises_error_download():
    """Specifying both end and end_date raises ValueError in download()."""
    with pytest.raises(ValueError, match="Cannot specify both 'end' and 'end_date'"):
        gcch.download("BTCUSDT", "1h", end="2024-06-30", end_date="2024-07-01")


def test_legacy_start_end_parameters_fetch_data():
    """Legacy start/end parameters continue working in fetch_data()."""
    df = gcch.fetch_data("ETHUSDT", "4h", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0
    assert "timestamp" in df.columns


def test_new_start_date_end_date_aliases_fetch_data():
    """New start_date/end_date aliases work correctly in fetch_data()."""
    df = gcch.fetch_data("ETHUSDT", "4h", start_date="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0
    assert "timestamp" in df.columns


def test_both_forms_produce_same_results_fetch_data():
    """Legacy and new forms produce identical results in fetch_data()."""
    df1 = gcch.fetch_data("SOLUSDT", "1d", start="2024-01-01", end="2024-01-02")
    df2 = gcch.fetch_data("SOLUSDT", "1d", start_date="2024-01-01", end_date="2024-01-02")

    assert len(df1) == len(df2)
    assert df1["timestamp"].min() == df2["timestamp"].min()
    assert df1["timestamp"].max() == df2["timestamp"].max()


def test_conflict_start_and_start_date_raises_error_fetch_data():
    """Specifying both start and start_date raises ValueError in fetch_data()."""
    with pytest.raises(ValueError, match="Cannot specify both 'start' and 'start_date'"):
        gcch.fetch_data("BTCUSDT", "1h", start="2024-01-01", start_date="2024-01-02")


def test_conflict_end_and_end_date_raises_error_fetch_data():
    """Specifying both end and end_date raises ValueError in fetch_data()."""
    with pytest.raises(ValueError, match="Cannot specify both 'end' and 'end_date'"):
        gcch.fetch_data("BTCUSDT", "1h", end="2024-06-30", end_date="2024-07-01")


def test_mixed_legacy_and_new_works():
    """Can use start with end_date (mixed forms)."""
    df = gcch.download("BTCUSDT", "1h", start="2024-01-01", end_date="2024-01-02")
    assert len(df) > 0

    # Or the reverse
    df = gcch.download("BTCUSDT", "1h", start_date="2024-01-01", end="2024-01-02")
    assert len(df) > 0
