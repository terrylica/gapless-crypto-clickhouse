"""REST client for Binance API with robust retry logic.

This module provides a battle-tested REST client for fetching klines data from
Binance API with automatic retry handling for rate limits and transient failures.

Ported from data-source-manager with modifications for gapless-crypto-clickhouse.

ADR-0040: query_ohlcv() gap filling implementation
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_incrementing,
)

logger = logging.getLogger(__name__)

# Constants
REST_CHUNK_SIZE = 1000  # Binance API limit per request
API_MAX_RETRIES = 3  # Number of retry attempts
API_TIMEOUT = 30.0  # Request timeout in seconds
API_BASE_DELAY = 1.0  # Base delay between retries

# API endpoints
SPOT_API_URL = "https://api.binance.com/api/v3/klines"
FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"


class RateLimitError(Exception):
    """Exception raised when Binance API returns rate limit response (418/429)."""

    def __init__(self, retry_after: int = 60, message: str = "Rate limited by API"):
        self.retry_after = retry_after
        self.message = message
        super().__init__(self.message)


class APIError(Exception):
    """Exception raised for Binance API errors."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"API error {code}: {message}")


@retry(
    stop=stop_after_attempt(API_MAX_RETRIES),
    wait=wait_incrementing(start=1, increment=1, max=3),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, RateLimitError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry attempt {retry_state.attempt_number}/{API_MAX_RETRIES} "
        f"after error: {retry_state.outcome.exception()}"
    ),
)
def fetch_klines_with_retry(
    base_url: str,
    params: dict[str, Any],
    timeout: float = API_TIMEOUT,
) -> List[List[Any]]:
    """Fetch klines data from Binance API with automatic retry.

    Args:
        base_url: API endpoint URL (spot or futures)
        params: Request parameters (symbol, interval, startTime, endTime, limit)
        timeout: Request timeout in seconds

    Returns:
        List of kline data arrays from Binance API

    Raises:
        RateLimitError: If rate limited (HTTP 418/429)
        APIError: If API returns error response
        httpx.TimeoutException: If request times out (will retry)
        httpx.NetworkError: If network error occurs (will retry)
    """
    response = httpx.get(base_url, params=params, timeout=timeout)

    # Handle rate limiting (418 = IP banned, 429 = rate limited)
    if response.status_code in (418, 429):
        retry_after = int(response.headers.get("retry-after", 60))
        logger.warning(f"Rate limited (HTTP {response.status_code}), waiting {retry_after}s")
        time.sleep(retry_after)
        raise RateLimitError(retry_after=retry_after)

    # Handle other HTTP errors
    if response.status_code != 200:
        raise APIError(response.status_code, response.text)

    data = response.json()

    # Check for API error in response
    if isinstance(data, dict) and "code" in data:
        raise APIError(data.get("code", -1), data.get("msg", "Unknown error"))

    return data


def calculate_chunks(
    start_ms: int,
    end_ms: int,
    interval_ms: int,
    chunk_size: int = REST_CHUNK_SIZE,
    max_chunks: int = 100,
) -> List[Tuple[int, int]]:
    """Calculate chunk boundaries for a time range.

    Binance API limits results to 1000 records per request.
    This function splits large time ranges into API-compatible chunks.

    Args:
        start_ms: Start time in milliseconds
        end_ms: End time in milliseconds
        interval_ms: Interval duration in milliseconds
        chunk_size: Maximum records per chunk (default: 1000)
        max_chunks: Maximum number of chunks to create (safety limit)

    Returns:
        List of (chunk_start_ms, chunk_end_ms) tuples
    """
    # Calculate max time range per chunk
    max_range_ms = interval_ms * chunk_size

    chunks = []
    current_start = start_ms
    loop_count = 0

    while current_start < end_ms and loop_count < max_chunks:
        chunk_end = min(current_start + max_range_ms, end_ms)
        chunks.append((current_start, chunk_end))
        current_start = chunk_end
        loop_count += 1

    if loop_count >= max_chunks:
        logger.warning(f"Reached max chunk limit ({max_chunks}) for time range")

    return chunks


def get_interval_ms(timeframe: str) -> int:
    """Get interval duration in milliseconds for a timeframe string.

    Args:
        timeframe: Timeframe string (e.g., "1h", "4h", "1d")

    Returns:
        Interval duration in milliseconds

    Raises:
        ValueError: If timeframe is not recognized
    """
    interval_map = {
        "1s": 1000,
        "1m": 60 * 1000,
        "3m": 3 * 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "30m": 30 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "2h": 2 * 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "6h": 6 * 60 * 60 * 1000,
        "8h": 8 * 60 * 60 * 1000,
        "12h": 12 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
        "3d": 3 * 24 * 60 * 60 * 1000,
        "1w": 7 * 24 * 60 * 60 * 1000,
        "1M": 30 * 24 * 60 * 60 * 1000,
    }

    if timeframe not in interval_map:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    return interval_map[timeframe]


def fetch_gap_data(
    symbol: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
    instrument_type: str = "spot",
) -> Optional[List[dict]]:
    """Fetch gap data from Binance REST API with chunking support.

    High-level function that handles chunking for large time ranges
    and converts raw API response to structured dictionaries.

    Args:
        symbol: Trading pair symbol (e.g., "BTCUSDT")
        timeframe: Timeframe string (e.g., "1h")
        start_time: Gap start time
        end_time: Gap end time
        instrument_type: "spot" or "futures-um"

    Returns:
        List of candle dictionaries with full microstructure data,
        or None if API returns no data

    Raises:
        ValueError: If instrument_type is invalid
        APIError: If API returns error response
    """
    # Select API endpoint
    if instrument_type == "spot":
        base_url = SPOT_API_URL
    elif instrument_type == "futures-um":
        base_url = FUTURES_API_URL
    else:
        raise ValueError(f"Invalid instrument_type: {instrument_type}")

    # Convert to milliseconds
    start_ms = int(start_time.timestamp() * 1000)
    end_ms = int(end_time.timestamp() * 1000)
    interval_ms = get_interval_ms(timeframe)

    # Calculate chunks for large time ranges
    chunks = calculate_chunks(start_ms, end_ms, interval_ms)

    all_candles = []
    for chunk_start, chunk_end in chunks:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": chunk_start,
            "endTime": chunk_end,
            "limit": REST_CHUNK_SIZE,
        }

        logger.info(f"Fetching {symbol} {timeframe} chunk: {chunk_start} to {chunk_end}")

        raw_klines = fetch_klines_with_retry(base_url, params)

        if not raw_klines:
            continue

        # Convert raw klines to structured dictionaries
        for kline in raw_klines:
            # Binance kline format:
            # [0] open_time, [1] open, [2] high, [3] low, [4] close, [5] volume,
            # [6] close_time, [7] quote_volume, [8] trades, [9] taker_buy_base,
            # [10] taker_buy_quote, [11] ignore

            open_time_ms = int(kline[0])
            open_time = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)

            # Only include candles within requested range
            if start_time <= open_time < end_time:
                candle = {
                    "timestamp": open_time,
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": datetime.fromtimestamp(int(kline[6]) / 1000, tz=timezone.utc),
                    "quote_asset_volume": float(kline[7]),
                    "number_of_trades": int(kline[8]),
                    "taker_buy_base_asset_volume": float(kline[9]),
                    "taker_buy_quote_asset_volume": float(kline[10]),
                }
                all_candles.append(candle)

        # Brief delay between chunks to avoid rate limiting
        if len(chunks) > 1:
            time.sleep(API_BASE_DELAY)

    if not all_candles:
        logger.warning(f"No data returned from API for {symbol} {timeframe}")
        return None

    logger.info(f"Retrieved {len(all_candles)} candles from REST API")
    return all_candles
