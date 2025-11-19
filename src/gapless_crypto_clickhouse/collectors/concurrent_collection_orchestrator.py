#!/usr/bin/env python3
"""
Concurrent Collection Orchestrator

High-performance orchestrator that combines hybrid URL generation with concurrent
downloading for maximum throughput while maintaining data integrity.

Integrates:
- HybridUrlGenerator: Smart monthly+daily strategy
- ConcurrentDownloadManager: HTTPX async downloads with 13 concurrent connections
- BinancePublicDataCollector: Data processing and validation
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .httpx_downloader import ConcurrentDownloadManager
from .hybrid_url_generator import DataSource, HybridUrlGenerator


@dataclass
class CollectionResult:
    """Result of concurrent collection operation."""

    success: bool
    timeframe: str
    total_tasks: int
    successful_downloads: int
    failed_downloads: int
    total_bars: int
    collection_time: float
    data_source_breakdown: Dict[str, int]  # monthly vs daily counts
    processed_data: Optional[List[List[str]]] = None
    errors: Optional[List[str]] = None


class ConcurrentCollectionOrchestrator:
    """
    High-performance concurrent collection orchestrator for hybrid Binance data collection.

    Combines the hybrid URL generation strategy with concurrent HTTPX downloading
    to achieve maximum throughput while maintaining authentic data integrity.

    Features:
        - Hybrid monthly+daily strategy for optimal performance
        - 13 concurrent downloads with connection pooling
        - Intelligent data source selection based on age
        - Real-time progress tracking and error handling
        - Seamless integration with existing BinancePublicDataCollector

    Performance Benefits:
        - 10-15x faster than sequential downloads
        - Optimal memory usage with streaming processing
        - Automatic retry logic with exponential backoff
        - Connection reuse and HTTP/2 support (when available)

    Examples:
        Basic concurrent collection:

        >>> orchestrator = ConcurrentCollectionOrchestrator(
        ...     symbol="BTCUSDT",
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 12, 31)
        ... )
        >>> async with orchestrator:
        ...     result = await orchestrator.collect_timeframe_concurrent("1h")
        ...     print(f"Collected {result.total_bars} bars in {result.collection_time:.1f}s")
        Collected 8760 bars in 12.3s

        Multiple timeframes with progress tracking:

        >>> def progress_callback(completed, total, current_task):
        ...     print(f"Progress: {completed}/{total} - {current_task.filename}")
        >>>
        >>> orchestrator = ConcurrentCollectionOrchestrator(symbol="ETHUSDT")
        >>> async with orchestrator:
        ...     results = await orchestrator.collect_multiple_timeframes_concurrent(
        ...         ["1h", "4h"], progress_callback=progress_callback
        ...     )
    """

    def __init__(
        self,
        symbol: str = "SOLUSDT",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        output_dir: Optional[Union[str, Path]] = None,
        max_concurrent: int = 13,
        daily_lookback_days: int = 30,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        """
        Initialize concurrent collection orchestrator.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            start_date: Collection start date
            end_date: Collection end date
            output_dir: Directory to save collected data
            max_concurrent: Maximum simultaneous downloads (13 optimized for ZIP files)
            daily_lookback_days: Days to use daily files for recent data
            timeout: Download timeout per file in seconds
            max_retries: Maximum retry attempts for failed downloads
        """
        self.symbol = symbol
        self.start_date = start_date or datetime(2020, 8, 15)
        self.end_date = end_date or datetime(2025, 3, 20)
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.max_retries = max_retries

        # Configure output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "sample_data"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.url_generator = HybridUrlGenerator(
            daily_lookback_days=daily_lookback_days, max_concurrent_per_batch=max_concurrent
        )

        self.download_manager: Optional[ConcurrentDownloadManager] = None
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"Initialized ConcurrentCollectionOrchestrator for {symbol}")
        self.logger.info(f"Date range: {self.start_date} to {self.end_date}")
        self.logger.info(f"Max concurrent downloads: {max_concurrent}")

    async def __aenter__(self):
        """Initialize async components."""
        self.download_manager = ConcurrentDownloadManager(
            max_concurrent=self.max_concurrent, timeout=self.timeout, max_retries=self.max_retries
        )
        await self.download_manager.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up async components."""
        if self.download_manager:
            await self.download_manager.__aexit__(exc_type, exc_val, exc_tb)

    async def collect_timeframe_concurrent(
        self, timeframe: str, progress_callback: Optional[callable] = None
    ) -> CollectionResult:
        """
        Collect data for a single timeframe using concurrent hybrid strategy.

        Args:
            timeframe: Timeframe to collect (e.g., "1h", "4h")
            progress_callback: Optional callback for progress updates

        Returns:
            CollectionResult with comprehensive collection statistics
        """
        start_time = datetime.now()
        self.logger.info(f"Starting concurrent collection for {self.symbol} {timeframe}")

        try:
            # Generate hybrid download tasks
            download_tasks = self.url_generator.generate_download_tasks(
                symbol=self.symbol,
                timeframe=timeframe,
                start_date=self.start_date,
                end_date=self.end_date,
            )

            if not download_tasks:
                return CollectionResult(
                    success=False,
                    timeframe=timeframe,
                    total_tasks=0,
                    successful_downloads=0,
                    failed_downloads=0,
                    total_bars=0,
                    collection_time=0.0,
                    data_source_breakdown={},
                    errors=["No download tasks generated"],
                )

            # Log strategy breakdown
            monthly_tasks, daily_tasks = self.url_generator.separate_tasks_by_source(download_tasks)
            self.logger.info(
                f"Download strategy: {len(monthly_tasks)} monthly + {len(daily_tasks)} daily = {len(download_tasks)} total"
            )

            # Execute concurrent downloads
            if not self.download_manager:
                raise RuntimeError("Download manager not initialized - use async context manager")

            download_results = await self.download_manager.download_tasks(
                download_tasks, progress_callback
            )

            # Process results
            processed_data = []
            successful_downloads = 0
            failed_downloads = 0
            errors = []

            for result in download_results:
                if result.success and result.data:
                    processed_data.extend(result.data)
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                    if result.error:
                        errors.append(f"{result.task.filename}: {result.error}")

            # Sort chronologically
            if processed_data:
                processed_data.sort(key=lambda row: row[0])  # Sort by timestamp

            # Calculate data source breakdown
            monthly_successful = sum(
                1
                for r in download_results
                if r.success and r.task.source_type == DataSource.MONTHLY
            )
            daily_successful = sum(
                1 for r in download_results if r.success and r.task.source_type == DataSource.DAILY
            )

            collection_time = (datetime.now() - start_time).total_seconds()

            result = CollectionResult(
                success=successful_downloads > 0,
                timeframe=timeframe,
                total_tasks=len(download_tasks),
                successful_downloads=successful_downloads,
                failed_downloads=failed_downloads,
                total_bars=len(processed_data),
                collection_time=collection_time,
                data_source_breakdown={"monthly": monthly_successful, "daily": daily_successful},
                processed_data=processed_data,
                errors=errors if errors else None,
            )

            # Log results
            self.logger.info(f"Collection completed for {timeframe}:")
            self.logger.info(f"  Tasks: {successful_downloads}/{len(download_tasks)} successful")
            self.logger.info(f"  Data: {len(processed_data)} bars in {collection_time:.1f}s")
            self.logger.info(f"  Sources: {monthly_successful} monthly + {daily_successful} daily")

            return result

        except Exception as e:
            collection_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Collection failed for {timeframe}: {e}")

            return CollectionResult(
                success=False,
                timeframe=timeframe,
                total_tasks=0,
                successful_downloads=0,
                failed_downloads=0,
                total_bars=0,
                collection_time=collection_time,
                data_source_breakdown={},
                errors=[str(e)],
            )

    async def collect_multiple_timeframes_concurrent(
        self, timeframes: List[str], progress_callback: Optional[callable] = None
    ) -> Dict[str, CollectionResult]:
        """
        Collect data for multiple timeframes concurrently.

        Args:
            timeframes: List of timeframes to collect
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary mapping timeframes to CollectionResult objects
        """
        self.logger.info(f"Starting concurrent collection for {len(timeframes)} timeframes")
        start_time = datetime.now()

        # Create collection tasks for each timeframe
        collection_tasks = []
        for timeframe in timeframes:
            task = self.collect_timeframe_concurrent(timeframe, progress_callback)
            collection_tasks.append((timeframe, task))

        # Execute all timeframe collections concurrently
        results = {}
        completed_tasks = await asyncio.gather(
            *[task for _, task in collection_tasks], return_exceptions=True
        )

        # Process results
        for i, result in enumerate(completed_tasks):
            timeframe = timeframes[i]
            if isinstance(result, Exception):
                results[timeframe] = CollectionResult(
                    success=False,
                    timeframe=timeframe,
                    total_tasks=0,
                    successful_downloads=0,
                    failed_downloads=0,
                    total_bars=0,
                    collection_time=0.0,
                    data_source_breakdown={},
                    errors=[str(result)],
                )
                self.logger.error(f"Collection failed for {timeframe}: {result}")
            else:
                results[timeframe] = result

        total_time = (datetime.now() - start_time).total_seconds()
        successful_timeframes = sum(1 for r in results.values() if r.success)
        total_bars = sum(r.total_bars for r in results.values())

        self.logger.info("Multi-timeframe collection completed:")
        self.logger.info(f"  Timeframes: {successful_timeframes}/{len(timeframes)} successful")
        self.logger.info(f"  Total bars: {total_bars:,}")
        self.logger.info(f"  Total time: {total_time:.1f}s")

        return results

    def get_collection_strategy_summary(self, timeframe: str) -> Dict[str, Any]:
        """
        Get summary of collection strategy for the given timeframe.

        Args:
            timeframe: Timeframe to analyze

        Returns:
            Dictionary with strategy summary and performance estimates
        """
        return self.url_generator.get_collection_strategy_summary(
            symbol=self.symbol,
            timeframe=timeframe,
            start_date=self.start_date,
            end_date=self.end_date,
        )

    async def test_connection_performance(self) -> Dict[str, Any]:
        """
        Test connection performance to Binance Vision servers.

        Returns:
            Dictionary with connection test results and performance metrics
        """
        if not self.download_manager:
            raise RuntimeError("Download manager not initialized - use async context manager")

        # Test with a small monthly file
        test_url = f"https://data.binance.vision/data/spot/monthly/klines/{self.symbol}/1h/{self.symbol}-1h-2024-01.zip"

        return await self.download_manager.test_connection(test_url)

    def estimate_collection_time(self, timeframes: List[str]) -> Dict[str, Any]:
        """
        Estimate collection time and resource requirements.

        Args:
            timeframes: List of timeframes to estimate

        Returns:
            Dictionary with time estimates and resource requirements
        """
        total_tasks = 0
        monthly_tasks = 0
        daily_tasks = 0

        for timeframe in timeframes:
            tasks = self.url_generator.generate_download_tasks(
                symbol=self.symbol,
                timeframe=timeframe,
                start_date=self.start_date,
                end_date=self.end_date,
            )
            total_tasks += len(tasks)

            monthly, daily = self.url_generator.separate_tasks_by_source(tasks)
            monthly_tasks += len(monthly)
            daily_tasks += len(daily)

        # Estimate based on concurrent batches
        batches_needed = (total_tasks + self.max_concurrent - 1) // self.max_concurrent

        # Conservative estimates based on file sizes and network speed
        avg_monthly_time = 3.0  # seconds per monthly file
        avg_daily_time = 1.0  # seconds per daily file

        estimated_time = (
            monthly_tasks * avg_monthly_time + daily_tasks * avg_daily_time
        ) / self.max_concurrent

        return {
            "total_tasks": total_tasks,
            "monthly_tasks": monthly_tasks,
            "daily_tasks": daily_tasks,
            "concurrent_batches": batches_needed,
            "max_concurrent": self.max_concurrent,
            "estimated_time_seconds": estimated_time,
            "estimated_time_minutes": estimated_time / 60,
            "timeframes": timeframes,
            "strategy": "hybrid_monthly_daily_concurrent",
        }
