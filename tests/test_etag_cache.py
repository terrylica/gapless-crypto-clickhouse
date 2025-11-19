"""Tests for ETag-based HTTP caching functionality.

Validates the ETag cache manager's ability to reduce bandwidth usage
by avoiding re-downloads of immutable Binance Vision data.

Test Organization (12 tests in 3 classes):
- TestETagCacheOperations: Lifecycle, persistence, metadata, statistics (5 tests)
- TestETagCacheErrorHandling: Corruption, invalidation, edge cases (5 tests)
- TestETagCacheCompliance: XDG Base Directory Specification (2 tests)

SLO Targets:
    Availability: 100% - handles cache corruption gracefully
    Correctness: 100% - cache mismatches trigger full download
    Observability: All cache hits/misses logged
"""

import json
import tempfile
from pathlib import Path

import pytest

from gapless_crypto_clickhouse.utils.etag_cache import ETagCache


class TestETagCacheOperations:
    """Test ETag cache operations: lifecycle, persistence, metadata, statistics."""

    def test_cache_lifecycle(self):
        """Test complete cache lifecycle: init → empty → update → retrieve."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache = ETagCache(cache_dir=cache_dir)

            # Verify initialization
            assert cache.cache_dir.exists()
            assert cache.cache_file == cache_dir / "etags.json"

            # Empty cache returns None
            etag = cache.get_etag("https://example.com/file.zip")
            assert etag is None

            # Update and retrieve
            test_url = "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"
            test_etag = "efcd0b4716abb9d950262a26fcb6ba43"
            test_size = 12845632

            cache.update_etag(test_url, test_etag, test_size)
            retrieved_etag = cache.get_etag(test_url)

            assert retrieved_etag == test_etag

    def test_persistence_across_instances(self):
        """Test that cache persists across ETagCache instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            test_url = "https://data.binance.vision/test.zip"
            test_etag = "abc123"

            # First instance - store ETag
            cache1 = ETagCache(cache_dir=cache_dir)
            cache1.update_etag(test_url, test_etag, 1024)

            # Second instance - retrieve ETag
            cache2 = ETagCache(cache_dir=cache_dir)
            retrieved_etag = cache2.get_etag(test_url)

            assert retrieved_etag == test_etag

    def test_metadata_structure(self):
        """Test cache entry metadata: fields, structure, timestamp format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))
            test_url = "https://example.com/file.zip"

            cache.update_etag(test_url, "etag123", 5000)

            # Read cache file directly to verify structure
            with open(cache.cache_file) as f:
                cache_data = json.load(f)

            assert test_url in cache_data
            entry = cache_data[test_url]

            # Verify all required fields
            assert "etag" in entry
            assert "last_checked" in entry
            assert "file_size" in entry
            assert entry["etag"] == "etag123"
            assert entry["file_size"] == 5000

            # Verify timestamp format (ISO 8601 UTC)
            timestamp = entry["last_checked"]
            assert timestamp.endswith("Z"), "Timestamp should be UTC (end with Z)"
            assert "T" in timestamp, "Timestamp should be ISO 8601 format (contain T)"

    def test_statistics_tracking(self):
        """Test cache statistics calculation: empty and with multiple entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))

            # Empty cache
            stats = cache.get_cache_stats()
            assert stats["total_entries"] == 0
            assert stats["total_cached_size"] == 0

            # Add multiple entries
            cache.update_etag("https://example.com/file1.zip", "etag1", 1000)
            cache.update_etag("https://example.com/file2.zip", "etag2", 2000)
            cache.update_etag("https://example.com/file3.zip", "etag3", 3000)

            stats = cache.get_cache_stats()
            assert stats["total_entries"] == 3
            assert stats["total_cached_size"] == 6000

    def test_statistics_after_operations(self):
        """Test statistics correctly update after invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))

            cache.update_etag("https://example.com/file1.zip", "etag1", 1000)
            cache.update_etag("https://example.com/file2.zip", "etag2", 2000)

            # After invalidation
            cache.invalidate("https://example.com/file1.zip")
            stats = cache.get_cache_stats()
            assert stats["total_entries"] == 1
            assert stats["total_cached_size"] == 2000


class TestETagCacheErrorHandling:
    """Test error handling: corruption, invalidation, edge cases."""

    def test_corrupted_cache_file_recovery(self):
        """Test corrupted cache file raises ValueError and auto-deletes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache_file = cache_dir / "etags.json"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Write invalid JSON
            with open(cache_file, "w") as f:
                f.write("{ invalid json }")

            # Should raise ValueError (not JSONDecodeError)
            with pytest.raises(ValueError, match="ETag cache corrupted"):
                ETagCache(cache_dir=cache_dir)

            # Cache file should be deleted
            assert not cache_file.exists()

    def test_empty_cache_file_valid(self):
        """Test that empty cache file doesn't cause errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache_file = cache_dir / "etags.json"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Write empty JSON object
            with open(cache_file, "w") as f:
                json.dump({}, f)

            # Should load successfully
            cache = ETagCache(cache_dir=cache_dir)
            assert cache.get_cache_stats()["total_entries"] == 0

    def test_invalidate_entry(self):
        """Test invalidate removes URL from cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))
            test_url = "https://example.com/file.zip"

            # Add entry
            cache.update_etag(test_url, "etag789", 3000)
            assert cache.get_etag(test_url) == "etag789"

            # Invalidate
            cache.invalidate(test_url)
            assert cache.get_etag(test_url) is None

    def test_invalidate_nonexistent_safe(self):
        """Test invalidating non-existent entry doesn't raise error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))

            # Should not raise
            cache.invalidate("https://example.com/nonexistent.zip")

    def test_clear_cache_operations(self):
        """Test clear cache: removes all entries, handles empty cache safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ETagCache(cache_dir=Path(tmpdir))

            # Add entries
            cache.update_etag("https://example.com/file1.zip", "etag1", 1000)
            cache.update_etag("https://example.com/file2.zip", "etag2", 2000)

            # Clear cache
            cache.clear_cache()

            # Verify empty
            assert cache.get_cache_stats()["total_entries"] == 0
            assert not cache.cache_file.exists()

            # Clear empty cache should be safe
            cache.clear_cache()


class TestETagCacheCompliance:
    """Test XDG Base Directory Specification compliance and configuration."""

    def test_xdg_default_location(self):
        """Test default cache uses XDG-compliant location."""
        cache = ETagCache()

        # Should be in ~/.cache/gapless-crypto-data/
        expected_parent = Path.home() / ".cache" / "gapless-crypto-data"
        assert cache.cache_dir == expected_parent
        assert cache.cache_file == expected_parent / "etags.json"

    def test_custom_cache_directory(self):
        """Test custom cache directory overrides default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = Path(tmpdir) / "custom_cache"
            cache = ETagCache(cache_dir=custom_dir)

            assert cache.cache_dir == custom_dir
            assert cache.cache_file == custom_dir / "etags.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
