"""ETag-based HTTP caching for immutable Binance Vision data.

CloudFront CDN provides ETags for all monthly ZIP files. Since historical data
is immutable, ETags enable bandwidth-efficient re-runs through 304 Not Modified
responses (90%+ bandwidth reduction).

SLO Targets:
    Availability: 100% - handles cache corruption gracefully
    Correctness: 100% - cache mismatches trigger full download
    Observability: All cache hits/misses logged
    Maintainability: Follows XDG Base Directory Specification

Architecture:
    - Cache location: $HOME/.cache/gapless-crypto-data/etags.json
    - Standard library only (pathlib + json)
    - Exception-only failure (no silent fallbacks)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ETagCache:
    """HTTP ETag cache manager for Binance Vision immutable data.

    Manages ETag-based caching to avoid re-downloading immutable historical data.
    Uses XDG Base Directory Specification for cache location.

    Cache Structure:
        {
            "https://data.binance.vision/.../BTCUSDT-1h-2024-01.zip": {
                "etag": "efcd0b4716abb9d950262a26fcb6ba43",
                "last_checked": "2025-10-16T16:30:00Z",
                "file_size": 12845632
            }
        }

    Examples:
        >>> cache = ETagCache()
        >>> cache.update_etag(url, "abc123", 1024000)
        >>> etag = cache.get_etag(url)
        >>> print(f"Cache hit: {etag}")
        Cache hit: abc123

    Note:
        Cache is persistent across runs. Corrupted cache files are automatically
        deleted and recreated. All errors propagate (exception-only failure).
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize ETag cache manager.

        Args:
            cache_dir: Override default cache directory location.
                      Default: $HOME/.cache/gapless-crypto-data/

        Raises:
            OSError: If cache directory creation fails
        """
        if cache_dir is None:
            # Follow XDG Base Directory Specification
            home = Path.home()
            self.cache_dir = home / ".cache" / "gapless-crypto-data"
        else:
            self.cache_dir = cache_dir

        self.cache_file = self.cache_dir / "etags.json"

        # Create cache directory if not exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load cache (or create empty)
        self._cache: Dict[str, Dict] = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict]:
        """Load cache from disk.

        Returns:
            Cache dictionary mapping URLs to ETag metadata

        Raises:
            json.JSONDecodeError: If cache file is corrupted (auto-deleted)
            OSError: If file read fails (propagated)
        """
        if not self.cache_file.exists():
            logger.debug(f"Cache file not found, creating new cache: {self.cache_file}")
            return {}

        try:
            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)
                logger.debug(f"Loaded ETag cache with {len(cache_data)} entries")
                return cache_data
        except json.JSONDecodeError as e:
            logger.error(f"Corrupted ETag cache file, deleting: {e}")
            self.cache_file.unlink()  # Delete corrupted cache
            raise ValueError(
                f"ETag cache corrupted at {self.cache_file}. "
                f"Deleted corrupted file. Original error: {e}"
            ) from e

    def _save_cache(self) -> None:
        """Save cache to disk.

        Raises:
            OSError: If file write fails (propagated)
            json.JSONEncodeError: If cache data not JSON-serializable (propagated)
        """
        with open(self.cache_file, "w") as f:
            json.dump(self._cache, f, indent=2)
        logger.debug(f"Saved ETag cache with {len(self._cache)} entries")

    def get_etag(self, url: str) -> Optional[str]:
        """Get ETag for URL from cache.

        Args:
            url: Full URL to Binance Vision file

        Returns:
            ETag string if cached, None if not found

        Examples:
            >>> cache = ETagCache()
            >>> etag = cache.get_etag("https://data.binance.vision/.../BTCUSDT-1h-2024-01.zip")
            >>> if etag:
            ...     print("Cache hit")
            ... else:
            ...     print("Cache miss")
        """
        entry = self._cache.get(url)
        if entry:
            logger.debug(f"Cache hit for {url}: {entry['etag']}")
            return entry["etag"]
        else:
            logger.debug(f"Cache miss for {url}")
            return None

    def update_etag(self, url: str, etag: str, file_size: int) -> None:
        """Update cache with new ETag metadata.

        Args:
            url: Full URL to Binance Vision file
            etag: ETag from HTTP response header
            file_size: Content-Length from HTTP response

        Raises:
            OSError: If cache save fails (propagated)
        """
        self._cache[url] = {
            "etag": etag,
            "last_checked": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "file_size": file_size,
        }
        self._save_cache()
        logger.debug(f"Updated cache for {url}: {etag}")

    def invalidate(self, url: str) -> None:
        """Remove URL from cache (ETag mismatch scenario).

        Args:
            url: Full URL to invalidate

        Raises:
            OSError: If cache save fails (propagated)
        """
        if url in self._cache:
            del self._cache[url]
            self._save_cache()
            logger.warning(f"Invalidated cache entry for {url}")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for observability.

        Returns:
            Dictionary with cache entry count and total cached file size
        """
        total_size = sum(entry.get("file_size", 0) for entry in self._cache.values())
        return {"total_entries": len(self._cache), "total_cached_size": total_size}

    def clear_cache(self) -> None:
        """Clear all cache entries.

        Raises:
            OSError: If cache file deletion fails (propagated)
        """
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cleared ETag cache")
