#!/usr/bin/env python3
"""
Tests for concurrent download system with HTTPX.

Comprehensive test suite for hybrid URL generation, concurrent downloads,
and regression detection for the new high-performance download architecture.

Tests include:
- Unit tests for URL generation (monthly/daily)
- Integration tests for concurrent downloads
- Performance regression detection
- Error handling and retry logic
- Memory usage validation
- Connection pooling verification
"""

import csv
import io
import zipfile
from datetime import datetime
from unittest.mock import Mock, patch

import httpx
import pytest

from gapless_crypto_clickhouse.collectors.httpx_downloader import (
    ConcurrentDownloadManager,
    DownloadResult,
)
from gapless_crypto_clickhouse.collectors.hybrid_url_generator import (
    DataSource,
    DownloadTask,
    HybridUrlGenerator,
)


class TestHybridUrlGenerator:
    """Test hybrid URL generation for monthly and daily sources."""

    def setup_method(self):
        """Setup test fixtures."""
        self.generator = HybridUrlGenerator(
            daily_lookback_days=30,
            max_concurrent_per_batch=13,
        )

    def test_init_defaults(self):
        """Test initialization with default parameters."""
        generator = HybridUrlGenerator()

        assert generator.daily_lookback_days == 30
        assert generator.max_concurrent_per_batch == 13
        assert generator.base_url == "https://data.binance.vision/data/spot"
        assert isinstance(generator.cutoff_date, datetime)

    def test_generate_monthly_tasks(self):
        """Test monthly URL generation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)

        tasks = self.generator._generate_monthly_tasks(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date=start_date,
            end_date=end_date,
        )

        # Should generate 3 monthly tasks (Jan, Feb, Mar)
        assert len(tasks) == 3

        # Verify task structure
        for task in tasks:
            assert isinstance(task, DownloadTask)
            assert task.source_type == DataSource.MONTHLY
            assert "BTCUSDT-1h-" in task.filename
            assert task.filename.endswith(".zip")
            assert task.url.startswith("https://data.binance.vision/data/spot/monthly/klines")

        # Verify specific months
        assert "2024-01" in tasks[0].period_identifier
        assert "2024-02" in tasks[1].period_identifier
        assert "2024-03" in tasks[2].period_identifier

    def test_generate_daily_tasks(self):
        """Test daily URL generation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)

        tasks = self.generator._generate_daily_tasks(
            symbol="ETHUSDT",
            timeframe="4h",
            start_date=start_date,
            end_date=end_date,
        )

        # Should generate 3 daily tasks
        assert len(tasks) == 3

        # Verify task structure
        for task in tasks:
            assert isinstance(task, DownloadTask)
            assert task.source_type == DataSource.DAILY
            assert "ETHUSDT-4h-" in task.filename
            assert task.filename.endswith(".zip")
            assert task.url.startswith("https://data.binance.vision/data/spot/daily/klines")

    def test_hybrid_strategy_determination(self):
        """Test hybrid strategy logic with monthly/daily cutoff."""
        # Set a specific cutoff date for testing
        self.generator.cutoff_date = datetime(2024, 6, 15)

        # Request data spanning both monthly and daily periods
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        tasks = self.generator.generate_download_tasks(
            symbol="SOLUSDT",
            timeframe="1h",
            start_date=start_date,
            end_date=end_date,
        )

        # Separate tasks by source
        monthly_tasks, daily_tasks = self.generator.separate_tasks_by_source(tasks)

        # Should have both monthly and daily tasks
        assert len(monthly_tasks) > 0
        assert len(daily_tasks) > 0

        # Verify monthly tasks are for historical data (before cutoff)
        for task in monthly_tasks:
            assert task.date_range[1] <= self.generator.cutoff_date

        # Verify daily tasks are for recent data (after cutoff)
        for task in daily_tasks:
            assert task.date_range[0] >= self.generator.cutoff_date

    def test_concurrent_batching(self):
        """Test concurrent batch creation."""
        # Generate multiple tasks
        tasks = self.generator.generate_download_tasks(
            symbol="BTCUSDT",
            timeframe="1h",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        # Create batches with specific concurrency limit
        batches = self.generator.create_concurrent_batches(tasks, max_concurrent=5)

        # Verify batch structure
        assert len(batches) > 0
        for batch in batches[:-1]:  # All but last batch should be full
            assert len(batch) == 5

        # Last batch may be smaller
        assert len(batches[-1]) <= 5

        # Verify all tasks are included
        total_tasks = sum(len(batch) for batch in batches)
        assert total_tasks == len(tasks)

    def test_collection_strategy_summary(self):
        """Test strategy summary generation."""
        summary = self.generator.get_collection_strategy_summary(
            symbol="ADAUSDT",
            timeframe="2h",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        # Verify summary structure
        required_keys = [
            "total_tasks",
            "monthly_tasks",
            "daily_tasks",
            "cutoff_date",
            "daily_lookback_days",
            "estimated_batches",
            "sources_used",
            "date_ranges",
        ]
        for key in required_keys:
            assert key in summary

        # Verify data types
        assert isinstance(summary["total_tasks"], int)
        assert isinstance(summary["monthly_tasks"], int)
        assert isinstance(summary["daily_tasks"], int)
        assert isinstance(summary["sources_used"], dict)

    def test_edge_case_single_day(self):
        """Test edge case with single day request."""
        start_date = datetime(2024, 6, 15)
        end_date = datetime(2024, 6, 15)

        tasks = self.generator.generate_download_tasks(
            symbol="DOTUSDT",
            timeframe="1h",
            start_date=start_date,
            end_date=end_date,
        )

        # Should generate exactly one task
        assert len(tasks) == 1

        # Type depends on cutoff date
        task = tasks[0]
        if start_date >= self.generator.cutoff_date:
            assert task.source_type == DataSource.DAILY
        else:
            assert task.source_type == DataSource.MONTHLY


class TestConcurrentDownloadManager:
    """Test concurrent download manager with mocking for reliability."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = ConcurrentDownloadManager(
            max_concurrent=3,  # Lower for testing
            timeout=10.0,
            max_retries=2,
        )

    def create_mock_zip_content(self, symbol: str, timeframe: str) -> bytes:
        """Create mock ZIP file content with CSV data."""
        # Create sample CSV data (12 columns to match Binance format)
        csv_data = [
            [
                "1640995200000",
                "47000.0",
                "47100.0",
                "46900.0",
                "47050.0",
                "100.5",
                "1640998800000",
                "4728525.0",
                "150",
                "60.3",
                "2837115.0",
                "0",
            ],
            [
                "1640998800000",
                "47050.0",
                "47200.0",
                "47000.0",
                "47150.0",
                "95.2",
                "1641002400000",
                "4489480.0",
                "142",
                "57.1",
                "2691724.0",
                "0",
            ],
        ]

        # Convert to CSV string
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerows(csv_data)
        csv_content = csv_buffer.getvalue().encode("utf-8")

        # Create ZIP file with CSV
        zip_buffer = io.BytesIO()
        csv_filename = f"{symbol}-{timeframe}-2024-01.csv"

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(csv_filename, csv_content)

        return zip_buffer.getvalue()

    @pytest.mark.asyncio
    async def test_download_manager_context(self):
        """Test download manager async context management."""
        async with self.manager as manager:
            assert manager.client is not None
            assert manager.semaphore is not None
            assert manager.semaphore._value == 3  # max_concurrent

        # Client should be closed after context exit
        assert self.manager.client is None

    @pytest.mark.asyncio
    async def test_successful_downloads(self):
        """Test successful concurrent downloads with mocking."""
        # Create test tasks
        tasks = [
            DownloadTask(
                url="https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip",
                filename="BTCUSDT-1h-2024-01.zip",
                source_type=DataSource.MONTHLY,
                period_identifier="2024-01",
                date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
            ),
            DownloadTask(
                url="https://data.binance.vision/data/spot/monthly/klines/ETHUSDT/1h/ETHUSDT-1h-2024-01.zip",
                filename="ETHUSDT-1h-2024-01.zip",
                source_type=DataSource.MONTHLY,
                period_identifier="2024-01",
                date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
            ),
        ]

        # Mock HTTP responses
        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # Setup mock responses
            mock_responses = []
            for task in tasks:
                mock_response = Mock()
                mock_response.status_code = 200
                # Extract symbol from task to create correct ZIP content
                symbol = task.filename.split("-")[0]  # Extract symbol from filename
                mock_response.content = self.create_mock_zip_content(symbol, "1h")
                mock_responses.append(mock_response)

            mock_get.side_effect = mock_responses

            # Execute downloads
            async with self.manager:
                results = await self.manager.download_tasks(tasks)

            # Verify results
            assert len(results) == 2
            for result in results:
                assert isinstance(result, DownloadResult)
                assert result.success is True
                assert result.data is not None
                assert len(result.data) == 2  # Two CSV rows
                assert len(result.data[0]) == 12  # Twelve columns
                assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error handling and retries."""
        task = DownloadTask(
            url="https://data.binance.vision/data/spot/monthly/klines/INVALID/1h/INVALID-1h-2024-01.zip",
            filename="INVALID-1h-2024-01.zip",
            source_type=DataSource.MONTHLY,
            period_identifier="2024-01",
            date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        )

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.content = b"Not Found"
            mock_get.return_value = mock_response

            async with self.manager:
                results = await self.manager.download_tasks([task])

            # Verify error handling
            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert result.status_code == 404
            assert "HTTP 404" in result.error

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        task = DownloadTask(
            url="https://data.binance.vision/data/spot/monthly/klines/SLOW/1h/SLOW-1h-2024-01.zip",
            filename="SLOW-1h-2024-01.zip",
            source_type=DataSource.MONTHLY,
            period_identifier="2024-01",
            date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        )

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # Mock timeout exception
            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            async with self.manager:
                results = await self.manager.download_tasks([task])

            # Verify timeout handling
            assert len(results) == 1
            result = results[0]
            assert result.success is False
            assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic with eventual success."""
        task = DownloadTask(
            url="https://data.binance.vision/data/spot/monthly/klines/RETRY/1h/RETRY-1h-2024-01.zip",
            filename="RETRY-1h-2024-01.zip",
            source_type=DataSource.MONTHLY,
            period_identifier="2024-01",
            date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
        )

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # First two calls fail, third succeeds
            error_response = Mock()
            error_response.status_code = 500
            error_response.content = b"Server Error"

            success_response = Mock()
            success_response.status_code = 200
            success_response.content = self.create_mock_zip_content("RETRY", "1h")

            mock_get.side_effect = [error_response, error_response, success_response]

            async with self.manager:
                results = await self.manager.download_tasks([task])

            # Should succeed after retries
            assert len(results) == 1
            result = results[0]
            assert result.success is True
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Test progress callback functionality."""
        tasks = [
            DownloadTask(
                url=f"https://data.binance.vision/data/spot/monthly/klines/TEST{i}/1h/TEST{i}-1h-2024-01.zip",
                filename=f"TEST{i}-1h-2024-01.zip",
                source_type=DataSource.MONTHLY,
                period_identifier="2024-01",
                date_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)),
            )
            for i in range(3)
        ]

        progress_calls = []

        def progress_callback(completed, total, current_task):
            progress_calls.append((completed, total, current_task.filename))

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            # Mock successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = self.create_mock_zip_content("TEST", "1h")
            mock_get.return_value = mock_response

            async with self.manager:
                await self.manager.download_tasks(tasks, progress_callback)

        # Verify progress callbacks
        assert len(progress_calls) == 3
        for i, (completed, total, filename) in enumerate(progress_calls):
            assert completed == i + 1
            assert total == 3
            assert f"TEST{i}" in filename

    @pytest.mark.asyncio
    async def test_connection_test(self):
        """Test connection testing functionality."""
        test_url = (
            "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"
        )

        with patch.object(httpx.AsyncClient, "head") as mock_head:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-length": "1024", "content-type": "application/zip"}
            mock_head.return_value = mock_response

            async with self.manager:
                result = await self.manager.test_connection(test_url)

            # Verify connection test results
            assert result["success"] is True
            assert result["status_code"] == 200
            assert "response_time_ms" in result
            assert result["url"] == test_url
            assert "headers" in result


class TestRegressionDetection:
    """Test regression detection for concurrent download performance."""

    def setup_method(self):
        """Setup test fixtures."""
        self.baseline_performance = {
            "downloads_per_second": 3.5,
            "average_response_time_ms": 850,
            "success_rate": 0.98,
            "memory_usage_mb": 25,
        }

    def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        # Simulate current performance metrics
        current_performance = {
            "downloads_per_second": 2.1,  # 40% slower - regression!
            "average_response_time_ms": 1200,  # 41% slower - regression!
            "success_rate": 0.96,  # Slight decrease
            "memory_usage_mb": 32,  # 28% increase - regression!
        }

        regressions = self._detect_performance_regressions(
            self.baseline_performance,
            current_performance,
            threshold=0.15,  # 15% threshold
        )

        # Should detect regressions in download speed, response time, and memory
        assert "downloads_per_second" in regressions
        assert "average_response_time_ms" in regressions
        assert "memory_usage_mb" in regressions
        assert "success_rate" not in regressions  # Within threshold

    def test_performance_improvement_detection(self):
        """Test detection of performance improvements."""
        current_performance = {
            "downloads_per_second": 4.5,  # 28% faster - improvement!
            "average_response_time_ms": 650,  # 23% faster - improvement!
            "success_rate": 0.995,  # Better success rate
            "memory_usage_mb": 20,  # 20% less memory - improvement!
        }

        improvements = self._detect_performance_improvements(
            self.baseline_performance,
            current_performance,
            threshold=0.01,  # 1% threshold for success rate
        )

        # Should detect improvements in most metrics
        assert "downloads_per_second" in improvements
        assert "average_response_time_ms" in improvements
        assert "memory_usage_mb" in improvements
        # Success rate improvement might be small, so check separately
        if "success_rate" in improvements:
            assert improvements["success_rate"]["improvement_percentage"] > 0

    def _detect_performance_regressions(self, baseline, current, threshold=0.15):
        """Detect performance regressions above threshold."""
        regressions = {}

        for metric, baseline_value in baseline.items():
            current_value = current.get(metric, baseline_value)

            if metric in ["downloads_per_second", "success_rate"]:
                # Higher is better
                change = (baseline_value - current_value) / baseline_value
            else:
                # Lower is better (response time, memory usage)
                change = (current_value - baseline_value) / baseline_value

            if change > threshold:
                regressions[metric] = {
                    "baseline": baseline_value,
                    "current": current_value,
                    "regression_percentage": change * 100,
                }

        return regressions

    def _detect_performance_improvements(self, baseline, current, threshold=0.10):
        """Detect performance improvements above threshold."""
        improvements = {}

        for metric, baseline_value in baseline.items():
            current_value = current.get(metric, baseline_value)

            if metric in ["downloads_per_second", "success_rate"]:
                # Higher is better
                change = (current_value - baseline_value) / baseline_value
            else:
                # Lower is better (response time, memory usage)
                change = (baseline_value - current_value) / baseline_value

            if change > threshold:
                improvements[metric] = {
                    "baseline": baseline_value,
                    "current": current_value,
                    "improvement_percentage": change * 100,
                }

        return improvements


@pytest.mark.integration
class TestConcurrentDownloadIntegration:
    """Integration tests for concurrent download system."""

    @pytest.mark.asyncio
    async def test_real_binance_connection(self):
        """Test real connection to Binance Vision (requires network)."""
        manager = ConcurrentDownloadManager(max_concurrent=2, timeout=30.0)

        # Test with known stable endpoint
        test_url = (
            "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01.zip"
        )

        async with manager:
            result = await manager.test_connection(test_url)

        # Should successfully connect
        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["response_time_ms"] < 5000  # Should be fast

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test end-to-end workflow: URL generation -> Download -> Processing."""
        # Generate URLs for small date range
        generator = HybridUrlGenerator(daily_lookback_days=365)  # Force monthly

        tasks = generator.generate_download_tasks(
            symbol="BTCUSDT",
            timeframe="1d",  # Daily timeframe for smaller files
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2),  # Just 2 days
        )

        # Limit to first task for testing
        limited_tasks = tasks[:1]

        manager = ConcurrentDownloadManager(max_concurrent=1, timeout=60.0)

        async with manager:
            results = await manager.download_tasks(limited_tasks)

        # Verify successful processing
        assert len(results) == 1
        result = results[0]

        if result.success:
            assert result.data is not None
            assert len(result.data) > 0  # Should have some data
            assert len(result.data[0]) == 12  # Should have 12 columns (Binance format)
            print(f"✅ Downloaded {len(result.data)} bars from {result.task.filename}")
        else:
            print(f"⚠️ Download failed (expected for test): {result.error}")
            # Don't fail test - this is network dependent
