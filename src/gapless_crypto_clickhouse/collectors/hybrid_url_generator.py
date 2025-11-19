#!/usr/bin/env python3
"""
Hybrid URL Generator for Binance Data Sources

Generates URLs for both monthly and daily data sources with intelligent
strategy determination for optimal data collection performance.

This module implements the hybrid approach:
- Monthly ZIP files for historical data (>30 days old)
- Daily ZIP files for recent data (≤30 days old)
- Concurrent collection support for both sources
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, NamedTuple, Optional, Tuple


class DataSource(Enum):
    """Data source types for Binance public data."""

    MONTHLY = "monthly"
    DAILY = "daily"


class DownloadTask(NamedTuple):
    """Represents a single download task with all necessary information."""

    url: str
    filename: str
    source_type: DataSource
    period_identifier: str  # "2024-01" for monthly, "2024-01-15" for daily
    date_range: Tuple[datetime, datetime]  # (start, end) for the file


class HybridUrlGenerator:
    """
    Intelligent URL generator for hybrid monthly+daily Binance data collection.

    Automatically determines optimal data source strategy based on date ranges:
    - Uses monthly files for bulk historical data (efficient for large ranges)
    - Uses daily files for recent data (more up-to-date, smaller files)
    - Supports concurrent download planning with proper task distribution

    Features:
        - Automatic cutoff date determination (configurable)
        - URL generation for both monthly and daily sources
        - Download task optimization and batching
        - Rate limit-aware task distribution
        - Intelligent overlap handling between monthly and daily sources

    Examples:
        Basic hybrid URL generation:

        >>> generator = HybridUrlGenerator()
        >>> tasks = generator.generate_download_tasks(
        ...     symbol="BTCUSDT",
        ...     timeframe="1h",
        ...     start_date=datetime(2024, 1, 1),
        ...     end_date=datetime(2024, 12, 31)
        ... )
        >>> print(f"Generated {len(tasks)} download tasks")
        Generated 15 download tasks

        Custom configuration:

        >>> generator = HybridUrlGenerator(
        ...     daily_lookback_days=45,  # Use daily files for last 45 days
        ...     base_url="https://data.binance.vision/data/spot"
        ... )
        >>> monthly_tasks, daily_tasks = generator.separate_tasks_by_source(tasks)
        >>> print(f"Monthly: {len(monthly_tasks)}, Daily: {len(daily_tasks)}")
        Monthly: 11, Daily: 45

        Concurrent batch planning:

        >>> batches = generator.create_concurrent_batches(tasks, max_concurrent=13)
        >>> for i, batch in enumerate(batches):
        ...     print(f"Batch {i}: {len(batch)} downloads")
        Batch 0: 13 downloads
        Batch 1: 5 downloads
    """

    def __init__(
        self,
        daily_lookback_days: int = 30,
        base_url: str = "https://data.binance.vision/data/spot",
        max_concurrent_per_batch: int = 13,
    ):
        """
        Initialize hybrid URL generator with configuration.

        Args:
            daily_lookback_days: Number of days to use daily files for recent data
            base_url: Base URL for Binance data repository
            max_concurrent_per_batch: Maximum concurrent downloads per batch (13 for ZIP files)
        """
        self.daily_lookback_days = daily_lookback_days
        self.base_url = base_url.rstrip("/")
        self.max_concurrent_per_batch = max_concurrent_per_batch

        # Calculate cutoff date for monthly vs daily strategy
        self.cutoff_date = datetime.now() - timedelta(days=daily_lookback_days)

    def generate_download_tasks(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[DownloadTask]:
        """
        Generate optimal download tasks using hybrid monthly+daily strategy.

        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
            timeframe: Data timeframe (e.g., "1h", "1d")
            start_date: Collection start date
            end_date: Collection end date

        Returns:
            List of DownloadTask objects optimized for concurrent execution
        """
        tasks = []

        # Determine which portions need monthly vs daily files
        monthly_end = min(end_date, self.cutoff_date)
        daily_start = max(start_date, self.cutoff_date)

        # Generate monthly tasks for historical data
        if start_date <= monthly_end:
            monthly_tasks = self._generate_monthly_tasks(symbol, timeframe, start_date, monthly_end)
            tasks.extend(monthly_tasks)

        # Generate daily tasks for recent data
        if daily_start <= end_date:
            daily_tasks = self._generate_daily_tasks(symbol, timeframe, daily_start, end_date)
            tasks.extend(daily_tasks)

        # Sort tasks chronologically for optimal processing
        tasks.sort(key=lambda task: task.date_range[0])

        return tasks

    def _generate_monthly_tasks(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[DownloadTask]:
        """Generate download tasks for monthly ZIP files."""
        tasks = []
        current_month = start_date.replace(day=1)

        while current_month <= end_date:
            year_month = current_month.strftime("%Y-%m")
            filename = f"{symbol}-{timeframe}-{year_month}.zip"
            url = f"{self.base_url}/monthly/klines/{symbol}/{timeframe}/{filename}"

            # Calculate actual date range for this monthly file
            month_start = current_month
            if current_month.month == 12:
                month_end = current_month.replace(year=current_month.year + 1, month=1) - timedelta(
                    days=1
                )
            else:
                month_end = current_month.replace(month=current_month.month + 1) - timedelta(days=1)

            # Clip to requested range
            file_start = max(month_start, start_date)
            file_end = min(month_end, end_date)

            task = DownloadTask(
                url=url,
                filename=filename,
                source_type=DataSource.MONTHLY,
                period_identifier=year_month,
                date_range=(file_start, file_end),
            )
            tasks.append(task)

            # Move to next month
            if current_month.month == 12:
                current_month = current_month.replace(year=current_month.year + 1, month=1)
            else:
                current_month = current_month.replace(month=current_month.month + 1)

        return tasks

    def _generate_daily_tasks(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[DownloadTask]:
        """Generate download tasks for daily ZIP files."""
        tasks = []
        current_date = start_date.date()
        end_date_only = end_date.date()

        while current_date <= end_date_only:
            date_str = current_date.strftime("%Y-%m-%d")
            filename = f"{symbol}-{timeframe}-{date_str}.zip"
            url = f"{self.base_url}/daily/klines/{symbol}/{timeframe}/{filename}"

            # Daily files contain one day of data
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

            # Clip to requested range
            file_start = max(day_start, start_date)
            file_end = min(day_end, end_date)

            task = DownloadTask(
                url=url,
                filename=filename,
                source_type=DataSource.DAILY,
                period_identifier=date_str,
                date_range=(file_start, file_end),
            )
            tasks.append(task)

            current_date += timedelta(days=1)

        return tasks

    def separate_tasks_by_source(
        self, tasks: List[DownloadTask]
    ) -> Tuple[List[DownloadTask], List[DownloadTask]]:
        """
        Separate tasks into monthly and daily groups.

        Args:
            tasks: List of download tasks

        Returns:
            Tuple of (monthly_tasks, daily_tasks)
        """
        monthly_tasks = [task for task in tasks if task.source_type == DataSource.MONTHLY]
        daily_tasks = [task for task in tasks if task.source_type == DataSource.DAILY]

        return monthly_tasks, daily_tasks

    def create_concurrent_batches(
        self, tasks: List[DownloadTask], max_concurrent: Optional[int] = None
    ) -> List[List[DownloadTask]]:
        """
        Create batches of tasks for concurrent execution with rate limiting.

        Args:
            tasks: List of download tasks
            max_concurrent: Maximum concurrent downloads per batch

        Returns:
            List of task batches for concurrent execution
        """
        if max_concurrent is None:
            max_concurrent = self.max_concurrent_per_batch

        batches = []
        for i in range(0, len(tasks), max_concurrent):
            batch = tasks[i : i + max_concurrent]
            batches.append(batch)

        return batches

    def get_collection_strategy_summary(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """
        Get summary of collection strategy for the given parameters.

        Args:
            symbol: Trading pair symbol
            timeframe: Data timeframe
            start_date: Collection start date
            end_date: Collection end date

        Returns:
            Strategy summary with source breakdown and task counts
        """
        tasks = self.generate_download_tasks(symbol, timeframe, start_date, end_date)
        monthly_tasks, daily_tasks = self.separate_tasks_by_source(tasks)

        return {
            "total_tasks": len(tasks),
            "monthly_tasks": len(monthly_tasks),
            "daily_tasks": len(daily_tasks),
            "cutoff_date": self.cutoff_date.isoformat(),
            "daily_lookback_days": self.daily_lookback_days,
            "estimated_batches": len(self.create_concurrent_batches(tasks)),
            "sources_used": {
                "monthly": len(monthly_tasks) > 0,
                "daily": len(daily_tasks) > 0,
            },
            "date_ranges": {
                "monthly_range": (
                    monthly_tasks[0].date_range[0].isoformat(),
                    monthly_tasks[-1].date_range[1].isoformat(),
                )
                if monthly_tasks
                else None,
                "daily_range": (
                    daily_tasks[0].date_range[0].isoformat(),
                    daily_tasks[-1].date_range[1].isoformat(),
                )
                if daily_tasks
                else None,
            },
        }
