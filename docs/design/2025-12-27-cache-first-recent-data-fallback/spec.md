---
adr: 2025-12-27-cache-first-recent-data-fallback
source: ~/.claude/plans/idempotent-humming-eich.md
implementation-status: in-progress
phase: implementation
last-updated: 2025-12-27
---

# Cache-First Architecture with REST API Fallback - Implementation Spec

**ADR**: [Cache-First Architecture with REST API Fallback](/docs/adr/2025-12-27-cache-first-recent-data-fallback.md)

## Goal

Enable `query_ohlcv()` to return same-day/recent data by falling back to REST API when CDN archives are unavailable (HTTP 404), while upgrading retry logic to exponential backoff with jitter (AWS best practice).

**Target Release**: v17.2.0

---

## Problem Statement

When requesting same-day or recent data, CDN archives don't exist yet:

```python
query_ohlcv("BTCUSDT", "1h", "2025-12-27", "2025-12-27")  # Today
```

1. Step 1: Checks ClickHouse → empty
2. Step 2: Attempts CDN download → **HTTP 404** (daily ZIP not published yet)
3. Step 3: Query returns empty DataFrame
4. Step 4: Gap detection fails (no baseline data)

**Expected Behavior**:

1. Step 2: CDN 404 → **Fallback to REST API** → Insert to ClickHouse
2. Data is cached for subsequent queries
3. Historical data still uses CDN (22x faster)

---

## Implementation Tasks

### Phase 1: Add RETRY_JITTER Constant (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/constants/network.py`

#### Task 1.1: Add jitter and exponential max constants

```python
RETRY_JITTER: Final[float] = 5.0
"""Random jitter added to retry delays (±seconds) to prevent thundering herd."""

RETRY_EXP_MAX: Final[int] = 60
"""Maximum delay cap for exponential backoff in seconds."""

RETRY_EXP_ATTEMPTS: Final[int] = 5
"""Number of retry attempts for exponential backoff (more than linear)."""
```

#### Task 1.2: Add to **all** exports

Add `"RETRY_JITTER"`, `"RETRY_EXP_MAX"`, `"RETRY_EXP_ATTEMPTS"` to module exports.

**Verification**:

- [ ] Constants importable from `gapless_crypto_clickhouse.constants`
- [ ] Self-validating assertions pass

---

### Phase 2: Upgrade REST Client Retry Logic (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/gap_filling/rest_client.py`

#### Task 2.1: Import new constants

```python
from ..constants import (
    # ... existing imports ...
    RETRY_EXP_ATTEMPTS,
    RETRY_EXP_MAX,
    RETRY_JITTER,
)
```

#### Task 2.2: Replace linear backoff with exponential + jitter

```python
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,  # Changed from wait_incrementing
)

@retry(
    stop=stop_after_attempt(RETRY_EXP_ATTEMPTS),  # 5 instead of 3
    wait=wait_exponential_jitter(
        initial=RETRY_BASE_DELAY,
        max=RETRY_EXP_MAX,
        jitter=RETRY_JITTER,
    ),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, RateLimitError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry attempt {retry_state.attempt_number}/{RETRY_EXP_ATTEMPTS} "
        f"after error: {retry_state.outcome.exception()}"
    ),
)
def fetch_klines_with_retry(...):
```

**Verification**:

- [ ] Retry timing follows exponential pattern: ~1s → ~2s → ~4s → ~8s → ~16s (±5s jitter)
- [ ] Rate limit handling still respects `retry_after` header
- [ ] All existing tests pass

---

### Phase 3: Add Recent Month Detection (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/query_api.py`

#### Task 3.1: Add \_is_recent_month() helper

```python
def _is_recent_month(year: int, month: int, lookback_days: int = 2) -> bool:
    """Check if month is within recent window where CDN archives may not exist.

    CDN publishes monthly/daily archives with a lag. This function identifies
    months that should fallback to REST API on HTTP 404.

    Args:
        year: Year to check
        month: Month to check (1-12)
        lookback_days: Days of CDN publication lag (default: 2)

    Returns:
        True if month is recent (within lookback window)
    """
    from datetime import datetime, timedelta

    # Get first day of the month
    month_start = datetime(year, month, 1)

    # Calculate cutoff (now - lookback)
    cutoff = datetime.now() - timedelta(days=lookback_days)

    # Month is "recent" if it starts after the cutoff
    # or if it's the current month
    return month_start >= cutoff.replace(day=1)
```

**Verification**:

- [ ] Returns True for current month
- [ ] Returns True for previous month if within lookback window
- [ ] Returns False for months older than lookback window

---

### Phase 4: Add REST API Ingest Function (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/query_api.py`

#### Task 4.1: Add \_ingest_recent_from_api() function

```python
def _ingest_recent_from_api(
    connection: ClickHouseConnection,
    symbol: str,
    timeframe: str,
    year: int,
    month: int,
    instrument_type: InstrumentType,
) -> int:
    """Ingest recent data from REST API when CDN unavailable.

    Called as fallback when CDN returns HTTP 404 for recent months.
    Reuses existing fetch_gap_data() infrastructure.

    Args:
        connection: Active ClickHouse connection
        symbol: Trading pair symbol
        timeframe: Timeframe string
        year: Year to ingest
        month: Month to ingest (1-12)
        instrument_type: "spot" or "futures-um"

    Returns:
        Number of rows ingested

    Raises:
        Exception: If API fetch or insertion fails
    """
    from datetime import datetime

    # Calculate month boundaries
    start_time = datetime(year, month, 1)
    if month == 12:
        end_time = datetime(year + 1, 1, 1)
    else:
        end_time = datetime(year, month + 1, 1)

    # Cap end_time at current time for current month
    now = datetime.now()
    if end_time > now:
        end_time = now

    logger.info(
        f"Ingesting {symbol} {timeframe} via REST API: "
        f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}"
    )

    # Reuse existing REST client
    api_data = fetch_gap_data(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
        instrument_type=instrument_type,
    )

    if not api_data:
        logger.warning(f"No data from REST API for {symbol} {year}-{month:02d}")
        return 0

    # Convert to ClickHouse format and insert
    df = _convert_api_data_to_dataframe(api_data, symbol, timeframe, instrument_type)
    rows = connection.insert_dataframe(df, table="ohlcv")

    logger.info(f"Ingested {rows} rows from REST API for {symbol} {year}-{month:02d}")
    return rows
```

**Verification**:

- [ ] Calls fetch_gap_data() with correct parameters
- [ ] Handles current month (caps end_time at now)
- [ ] Returns 0 for empty API response (no exception)
- [ ] Inserts data to ClickHouse

---

### Phase 5: Modify Auto-Ingest with 404 Fallback (P0 - Critical)

**Files to modify**:

- `src/gapless_crypto_clickhouse/query_api.py`

#### Task 5.1: Add import for HTTPError

```python
from urllib.error import HTTPError
```

#### Task 5.2: Modify \_auto_ingest_date_range() exception handling

```python
def _auto_ingest_date_range(
    loader: ClickHouseBulkLoader,
    connection: ClickHouseConnection,  # NEW: Add connection parameter
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    instrument_type: InstrumentType,
) -> int:
    """Auto-ingest data for date range by month.

    Falls back to REST API for recent months when CDN returns HTTP 404.
    """
    # ... existing code ...

    try:
        rows = loader.ingest_month(symbol, timeframe, year, month)
        total_rows += rows
        logger.info(f"Ingested {rows} rows for {symbol} {year}-{month:02d}")
    except HTTPError as e:
        if e.code == 404 and _is_recent_month(year, month):
            # NEW: Fallback to REST API for recent data
            logger.info(
                f"CDN archive unavailable for {symbol} {year}-{month:02d} "
                f"(HTTP 404), falling back to REST API"
            )
            rows = _ingest_recent_from_api(
                connection, symbol, timeframe, year, month, instrument_type
            )
            total_rows += rows
        else:
            # Re-raise for historical data 404s (genuine missing data)
            logger.warning(
                f"Failed to ingest {symbol} {year}-{month:02d}: {e} "
                f"(month may not exist yet)"
            )
    except Exception as e:
        logger.warning(
            f"Failed to ingest {symbol} {year}-{month:02d}: {e} "
            f"(month may not exist yet)"
        )
```

#### Task 5.3: Update caller in query_ohlcv()

Pass `connection` (the ClickHouseConnection) to `_auto_ingest_date_range()`:

```python
_auto_ingest_date_range(
    loader, conn, sym, timeframe, start_date, end_date, instrument_type
)
```

**Verification**:

- [ ] CDN 404 for recent month triggers REST API fallback
- [ ] CDN 404 for historical data logs warning (no fallback)
- [ ] Same-day query returns data

---

### Phase 6: Add Tests (P1 - High)

**Files to create/modify**:

- `tests/test_query_api.py`
- `tests/test_rest_client_unit.py`

#### Task 6.1: Test \_is_recent_month()

```python
def test_is_recent_month_current():
    """Current month should be detected as recent."""
    now = datetime.now()
    assert _is_recent_month(now.year, now.month) is True

def test_is_recent_month_old():
    """Month from a year ago should not be recent."""
    now = datetime.now()
    old_year = now.year - 1
    assert _is_recent_month(old_year, now.month) is False
```

#### Task 6.2: Test REST API fallback

```python
def test_auto_ingest_cdn_fallback(mocker):
    """HTTP 404 for recent month should trigger REST API fallback."""
    # Mock CDN to return 404
    mocker.patch.object(
        ClickHouseBulkLoader,
        "ingest_month",
        side_effect=HTTPError(None, 404, "Not Found", {}, None),
    )
    # Mock REST API
    mock_fetch = mocker.patch(
        "gapless_crypto_clickhouse.query_api.fetch_gap_data",
        return_value=[{"timestamp": datetime.now(), ...}],
    )

    # Call with recent date
    _auto_ingest_date_range(loader, conn, "BTCUSDT", "1h", "2025-12-27", "2025-12-27", "spot")

    # Verify REST API was called
    mock_fetch.assert_called_once()
```

#### Task 6.3: Test exponential backoff timing

```python
def test_exponential_backoff_timing():
    """Retry delays should follow exponential pattern with jitter."""
    # This test validates the tenacity configuration
    from tenacity import wait_exponential_jitter

    wait_fn = wait_exponential_jitter(initial=1, max=60, jitter=5)

    # First retry: ~1s (±5s jitter)
    delay_1 = wait_fn(make_retry_state(attempt=1))
    assert 0 <= delay_1 <= 6

    # Second retry: ~2s (±5s jitter)
    delay_2 = wait_fn(make_retry_state(attempt=2))
    assert 0 <= delay_2 <= 7

    # Third retry: ~4s (±5s jitter)
    delay_3 = wait_fn(make_retry_state(attempt=3))
    assert 0 <= delay_3 <= 9
```

**Verification**:

- [ ] All new tests pass
- [ ] Existing tests still pass
- [ ] Code coverage maintained

---

## Testing Plan

### Unit Tests

| Test                            | Location                    | Description                              |
| ------------------------------- | --------------------------- | ---------------------------------------- |
| `test_is_recent_month_current`  | `tests/test_query_api.py`   | Verify current month detected as recent  |
| `test_is_recent_month_old`      | `tests/test_query_api.py`   | Verify old months not detected as recent |
| `test_auto_ingest_cdn_fallback` | `tests/test_query_api.py`   | Verify REST API fallback on CDN 404      |
| `test_exponential_backoff`      | `tests/test_rest_client.py` | Verify retry timing                      |

### Integration Tests

| Test             | Description                                               |
| ---------------- | --------------------------------------------------------- |
| Same-day query   | `query_ohlcv("BTCUSDT", "1h", today, today)` returns data |
| Mixed date range | Query spanning CDN + REST API data                        |
| Cached query     | Second query for same-day uses ClickHouse cache           |

### E2E Validation

```bash
# Same-day data test
python -c "
import gapless_crypto_clickhouse as gcch
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
df = gcch.query_ohlcv('BTCUSDT', '1h', today, today)
print(f'Retrieved {len(df)} rows for today')
assert len(df) > 0, 'Expected data for today'
"
```

---

## Release Checklist

- [ ] Phase 1: RETRY_JITTER constant added to network.py
- [ ] Phase 2: REST client upgraded to exponential backoff + jitter
- [ ] Phase 3: `_is_recent_month()` helper added
- [ ] Phase 4: `_ingest_recent_from_api()` function added
- [ ] Phase 5: `_auto_ingest_date_range()` modified with 404 fallback
- [ ] Phase 6: All tests added and passing
- [ ] Version bumped to 17.2.0 (semantic-release will handle)
- [ ] CHANGELOG updated (semantic-release will generate)

---

## Files Changed Summary

| File                                                       | Change Type | Description                                                                               |
| ---------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------- |
| `src/gapless_crypto_clickhouse/constants/network.py`       | Modified    | Add RETRY_JITTER, RETRY_EXP_MAX, RETRY_EXP_ATTEMPTS                                       |
| `src/gapless_crypto_clickhouse/gap_filling/rest_client.py` | Modified    | Upgrade to wait_exponential_jitter                                                        |
| `src/gapless_crypto_clickhouse/query_api.py`               | Modified    | Add `_is_recent_month()`, `_ingest_recent_from_api()`, modify `_auto_ingest_date_range()` |
| `tests/test_query_api.py`                                  | Modified    | Add tests for recent month detection and fallback                                         |
| `tests/test_rest_client_unit.py`                           | Modified    | Add exponential backoff tests                                                             |

---

## Success Criteria

After implementation, a user should be able to:

```python
import gapless_crypto_clickhouse as gcch
from datetime import datetime

# Query today's data - works even though CDN doesn't have it yet
today = datetime.now().strftime('%Y-%m-%d')
df = gcch.query_ohlcv('BTCUSDT', '1h', today, today)

# Data is cached - second query is instant
df2 = gcch.query_ohlcv('BTCUSDT', '1h', today, today)  # Uses ClickHouse cache
```

**No empty DataFrames for valid same-day queries.**
