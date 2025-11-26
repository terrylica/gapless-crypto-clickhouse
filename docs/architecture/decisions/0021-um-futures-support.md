# UM Futures Support with Timestamp Precision Enhancement

**Status**: Accepted
**Date**: 2025-11-19
**Deciders**: Terry Li
**Related ADRs**: [ADR-0004 (Superseded QuestDB Futures)](0004-futures-support-implementation.md), [ADR-0020 (Multi-Symbol Batch API)](0020-multi-symbol-batch-api.md)
**Related Plans**: [0021-um-futures-support](../../development/plan/0021-um-futures-support/plan.md)

## Context and Problem Statement

Current documentation claims "USDT-margined futures support (400+ symbols)" but implementation only supports spot data. Alpha Forge feedback identified this as a critical documentation vs reality gap requiring immediate resolution.

**Current State**: Only spot data collection via Binance Vision API
**Required**: Full UM futures support with 713 validated symbols
**Critical Discovery**: Binance transitioned spot data to **microsecond precision** (DateTime64(6)) on January 1, 2025, while futures remain milliseconds

## Decision Drivers

- **Documentation Accuracy**: Fulfill claims made in README/llms.txt/CLAUDE.md
- **Alpha Forge Integration**: Enable production-grade futures data access
- **Symbol Coverage**: 713 validated futures symbols (binance-futures-availability package)
- **Schema Prepared**: ClickHouse `instrument_type` column already exists
- **Minimal Code Changes**: URL routing + API endpoint selection only
- **Timestamp Precision**: Must handle dual precision (spot=μs, futures=ms)
- **SLO Focus**: Availability, correctness, observability, maintainability

## Considered Options

### Option 1: Add instrument_type Parameter with Enum-Driven Routing (CHOSEN)

**Pattern**: String literal parameter with conditional URL/endpoint routing

**Architecture**:

```python
# API Layer
def download(
    symbol: str,
    timeframe: str,
    instrument_type: Literal["spot", "futures-um"] = "spot",
    **kwargs
) -> pd.DataFrame:
    collector = BinancePublicDataCollector(
        symbol=symbol,
        instrument_type=instrument_type
    )

# Collector Layer
class BinancePublicDataCollector:
    SPOT_BASE_URL = "https://data.binance.vision/data/spot"
    FUTURES_BASE_URL = "https://data.binance.vision/data/futures/um"

    def __init__(self, instrument_type: str = "spot"):
        self.base_url = (
            f"{self.SPOT_BASE_URL}/monthly/klines"
            if instrument_type == "spot"
            else f"{self.FUTURES_BASE_URL}/monthly/klines"
        )
```text

**Pros**:

- ✅ Minimal code duplication (URL path + API endpoint differences only)
- ✅ 100% backward compatible (default to "spot")
- ✅ Follows ADR-0004/DSM proven pattern (MarketType enum)
- ✅ Reuses existing validation, caching, gap filling
- ✅ Simple for 2 types (spot, futures-um)

**Cons**:

- ⚠️ If/else pattern doesn't scale well beyond 2-3 types
- ⚠️ CM futures (coin-margined) will require additional if/else logic
- ⚠️ Symbol transformation not supported (needed for CM: BTCUSDT → BTCUSD_PERP)

**DSM Pattern Alignment**:

The data-source-manager repository uses `MarketType` enum with properties:

```python
# DSM Pattern (for reference - not implemented in v3.2.0)
class MarketType(Enum):
    SPOT = auto()
    FUTURES_USDT = auto()  # UM futures
    FUTURES_COIN = auto()   # CM futures

    @property
    def vision_api_path(self) -> str:
        if self.name == "SPOT": return "spot"
        if self.name == "FUTURES_USDT": return "futures/um"
        if self.name == "FUTURES_COIN": return "futures/cm"
```text

**Rationale for Not Using Enum in v3.2.0**:

- String literal sufficient for 2 types (spot, futures-um)
- Enum adds complexity without clear benefit for current scope
- Can refactor to enum in v3.3.0 when adding CM futures (non-breaking)

---

### Option 2: Create Separate FuturesDataCollector Class

**Pattern**: Inheritance or composition with separate collector classes

**Architecture**:

```python
class SpotDataCollector(BinancePublicDataCollector):
    BASE_URL = "https://data.binance.vision/data/spot"
    API_URL = "https://api.binance.com/api/v3/klines"

class FuturesDataCollector(BinancePublicDataCollector):
    BASE_URL = "https://data.binance.vision/data/futures/um"
    API_URL = "https://fapi.binance.com/fapi/v1/klines"
```python

**Pros**:

- ✅ Clear separation of concerns
- ✅ Each class owns its URL/endpoint configuration
- ✅ Extensible via inheritance

**Cons**:

- ❌ **80% code duplication** across classes:
  - CSV parsing logic (12→11 column normalization)
  - Date range calculation (monthly file generation)
  - ZIP file handling (download, extract, validate)
  - ClickHouse ingestion (DataFrame → ReplacingMergeTree)
  - Gap detection and filling
  - Error handling and retry logic
- ❌ **API complexity**: Users must choose correct collector class
- ❌ **Maintenance burden**: Bug fixes require changes in multiple classes
- ❌ **Testing overhead**: Each class needs full test suite

**Code Duplication Analysis**:

| Component            | Lines   | Duplicated Across Classes        |
| -------------------- | ------- | -------------------------------- |
| CSV parsing          | 45      | ✅ Same 12→11 normalization      |
| Date range logic     | 60      | ✅ Identical monthly/daily logic |
| ZIP handling         | 80      | ✅ Same extract/validate         |
| ClickHouse ingestion | 120     | ✅ Same ReplacingMergeTree logic |
| Gap filling          | 95      | ✅ Same detection algorithm      |
| **Total**            | **400** | **80% duplication**              |

**Verdict**: Rejected due to massive code duplication and maintenance burden

---

### Option 3: Fix Documentation Only (Defer Implementation)

**Pattern**: Remove false futures claims from v3.1.1 documentation

**Architecture**: No code changes, only documentation updates

**Pros**:

- ✅ Zero implementation risk
- ✅ No testing required
- ✅ Fast turnaround (1 hour)

**Cons**:

- ❌ Doesn't solve user need (Alpha Forge requires futures data)
- ❌ Loses competitive advantage (713 symbols vs spot-only alternatives)
- ❌ Delays inevitable implementation (will need futures eventually)
- ❌ Breaks user trust (documented feature removal)

**Verdict**: Rejected - doesn't address core user requirement

---

### Option 4: Add Async API with asyncio (Over-Engineering)

**Pattern**: `async def download_async()` with aiohttp

**Pros**:

- ✅ Modern async/await pattern
- ✅ Scales to thousands of concurrent requests

**Cons**:

- ❌ Overkill (ThreadPoolExecutor sufficient for I/O-bound CDN downloads)
- ❌ Requires async ecosystem adoption (aiohttp, asyncio)
- ❌ More complex for users (async/await syntax, event loops)
- ❌ No measurable performance benefit over threads for CDN downloads
- ❌ Breaks sync API compatibility

**Verdict**: Rejected - threads handle I/O-bound downloads efficiently

---

## Decision Outcome

**Chosen option**: **Option 1 - Add instrument_type parameter with conditional routing**

**Implementation Strategy**:

1. **Timestamp Precision Fix** (CRITICAL - New Requirement):
   - Update ClickHouse schema: `DateTime64(3)` → `DateTime64(6)` (milliseconds → microseconds)
   - Add format detection utility: Detect spot data precision (μs vs ms)
   - Conversion logic: Normalize futures milliseconds → microseconds during ingestion
   - Migration: Update existing spot data (if collected after Jan 1, 2025)

2. **API Layer Enhancement**:
   - Add `instrument_type: Literal["spot", "futures-um"] = "spot"` parameter to:
     - `fetch_data()`
     - `download()`
     - `download_multiple()`
     - `fill_gaps()`
     - `get_supported_symbols()`
   - Add validation: `_validate_instrument_type()` function
   - Pass parameter through call chain: API → Collector → GapFiller

3. **URL Routing**:
   - Spot: `https://data.binance.vision/data/spot/monthly/klines`
   - UM Futures: `https://data.binance.vision/data/futures/um/monthly/klines`

4. **API Endpoint Selection**:
   - Spot: `https://api.binance.com/api/v3/klines`
   - UM Futures: `https://fapi.binance.com/fapi/v1/klines`

5. **Symbol Integration**:
   - Package: `binance-futures-availability>=1.0.0`
   - Count: 713 perpetual symbols (validated daily via S3 Vision probes)
   - Quality: 95%+ SLA, production-tested since 2025-11-12

6. **Schema Enhancement**:

   ```sql
   -- Timestamp precision upgrade (CRITICAL)
   ALTER TABLE ohlcv MODIFY COLUMN timestamp DateTime64(6);

   -- Future-proof funding rate column
   ALTER TABLE ohlcv
   ADD COLUMN IF NOT EXISTS funding_rate Nullable(Float64) CODEC(Gorilla, LZ4)
   AFTER taker_buy_quote_asset_volume;
   ```

**Rationale**:

- Minimal code changes (URL routing only, no duplication)
- 100% backward compatible (default parameter value)
- Proven pattern from ADR-0004 (QuestDB era) and DSM
- Reuses existing validation/caching/gap-filling infrastructure
- Future-proof: funding_rate column ready for separate implementation
- **Timestamp precision:** Handles Binance's Jan 1, 2025 format transition

## Implementation Details

### Timestamp Precision Handling (New Critical Requirement)

**Problem**: Binance Vision API changed spot data to microseconds (Jan 1, 2025), but futures remain milliseconds.

**Solution**: Universal microsecond precision with automatic conversion

**Schema**:

```sql
-- Before (INCORRECT after Jan 1, 2025)
timestamp DateTime64(3)  -- Millisecond precision

-- After (CORRECT for both spot and futures)
timestamp DateTime64(6)  -- Microsecond precision
```text

**Conversion Logic**:

```python
def normalize_timestamp(timestamp_ms: int, source_precision: str) -> int:
    """Convert timestamps to microseconds.

    Args:
        timestamp_ms: Raw timestamp from Binance CSV
        source_precision: "milliseconds" or "microseconds"

    Returns:
        Timestamp in microseconds (DateTime64(6) compatible)
    """
    if source_precision == "microseconds":
        return timestamp_ms  # Already microseconds
    elif source_precision == "milliseconds":
        return timestamp_ms * 1000  # Convert ms → μs
    else:
        raise ValueError(f"Unknown precision: {source_precision}")
```text

**Format Detection**:

```python
def detect_timestamp_precision(csv_path: Path) -> str:
    """Detect timestamp precision from CSV file.

    Logic:
    - Spot data (after Jan 1, 2025): 1704067200000000 (16 digits = microseconds)
    - Futures data: 1704067200000 (13 digits = milliseconds)
    - Spot data (before Jan 1, 2025): 1704067200000 (13 digits = milliseconds)
    """
    df = pd.read_csv(csv_path, nrows=1)
    timestamp = df.iloc[0, 0]  # First column is timestamp

    if timestamp > 1e15:  # 16 digits
        return "microseconds"
    else:  # 13 digits
        return "milliseconds"
```text

### URL Patterns

| Instrument Type | Vision API URL                                       | REST API URL                      |
| --------------- | ---------------------------------------------------- | --------------------------------- |
| spot            | `data.binance.vision/data/spot/monthly/klines`       | `api.binance.com/api/v3/klines`   |
| futures-um      | `data.binance.vision/data/futures/um/monthly/klines` | `fapi.binance.com/fapi/v1/klines` |

### CSV Format Normalization

Both spot and futures produce **11 columns** after normalization:

- **Spot**: 11 columns (no header)
- **Futures**: 12 columns with header → drop "Ignore" column → 11 columns

**Normalization**:

```python
# Futures CSV: 12 columns with header
columns_futures = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_asset_volume", "number_of_trades",
    "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume",
    "ignore"  # ← DROP THIS COLUMN
]

# After normalization: 11 columns (same as spot)
df = pd.read_csv(csv_path, usecols=range(11))  # Drop last column
```text

### Symbol Source

**Package**: `binance-futures-availability>=1.0.0`

**Integration**:

```python
from binance_futures_availability.config.symbol_loader import load_symbols

def get_supported_symbols(instrument_type: str = "spot") -> List[str]:
    if instrument_type == "futures-um":
        return load_symbols("perpetual")  # 713 symbols
    else:
        collector = BinancePublicDataCollector()
        return list(collector.known_symbols.keys())  # 20 symbols
```text

**Quality Metrics**:

- 713 perpetual symbols
- Daily S3 Vision validation (95%+ SLA)
- DuckDB availability tracking (2019-09-25 to present)
- Auto-updated via GitHub Actions (3:00 AM UTC daily)

### Schema Changes

```sql
-- Phase 1: Timestamp precision upgrade (CRITICAL)
ALTER TABLE ohlcv MODIFY COLUMN timestamp DateTime64(6);

-- Phase 2: Future-proof funding rate column
ALTER TABLE ohlcv
ADD COLUMN IF NOT EXISTS funding_rate Nullable(Float64) CODEC(Gorilla, LZ4)
AFTER taker_buy_quote_asset_volume;

-- Verify schema
DESCRIBE TABLE ohlcv;
```

**Column Characteristics**:

- `funding_rate`: Nullable(Float64) - NULL for spot data and unpopulated futures rows
- **NOT** in ORDER BY - Avoids nullable key restrictions
- **NOT** in `_version` hash - Updates don't create new versions
- Gorilla codec - Optimal compression for float time-series
- Population deferred - Requires separate API endpoint (`/fapi/v1/fundingRate`)

## Consequences

### Positive

- ✅ **Fulfills Documentation**: Resolves documentation vs reality gap
- ✅ **713 Validated Symbols**: vs 20 spot symbols (36x increase)
- ✅ **100% Backward Compatible**: Default parameter preserves existing behavior
- ✅ **Future-Proof Schema**: Funding rate column ready for v3.3.0
- ✅ **Timestamp Precision**: Handles Binance's Jan 1, 2025 format transition
- ✅ **Proven Pattern**: Aligns with ADR-0004 and DSM MarketType design
- ✅ **Minimal Code Changes**: URL routing only (no duplication)

### Negative

- ⚠️ **Dependency Added**: binance-futures-availability (well-maintained, 95%+ SLA)
- ⚠️ **Schema Migration Required**: DateTime64(6) upgrade (one-time, zero downtime)
- ⚠️ **Funding Rate Unpopulated**: Column exists but NULL initially (documented)
- ⚠️ **Explicit Opt-In Required**: Users must pass `instrument_type="futures-um"`

### Neutral

- Same 11-column CSV format (after normalization)
- Same timeframe support (16 intervals: 1s-1mo)
- Same validation logic (zero-gap guarantee maintained)
- Symbol transformation not needed for UM (CM futures will require this)

## Validation Criteria

### Acceptance Criteria

- [ ] Timestamp precision: DateTime64(6) for both spot and futures
- [ ] All existing spot code works unchanged (backward compatibility)
- [ ] `instrument_type="futures-um"` downloads futures data successfully
- [ ] 713 symbols loaded from binance-futures-availability
- [ ] Gap filling uses correct API endpoint (fapi.binance.com)
- [ ] ClickHouse funding_rate column added (nullable, unpopulated)
- [ ] All tests pass (27 total: 15 original + 12 critical from audit)

### SLO Impact

- **Availability**: Improved (713 futures symbols available)
- **Correctness**: Maintained (timestamp precision fix prevents data corruption)
- **Observability**: Enhanced (instrument_type tracking, format detection)
- **Maintainability**: Minimal increase (URL routing only, no duplication)

## Compliance

- **OSS Libraries**: Uses binance-futures-availability (MIT license)
- **Error Handling**: Raise+propagate pattern (ValueError for invalid instrument_type)
- **Backward Compatibility**: 100% (default instrument_type="spot")
- **Auto-Validation**: 27 tests validate spot, futures, and edge cases

## Future Work

### v3.3.0 (Coin-Margined Futures)

- Coin-margined futures support (CM, requires symbol transformation)
- Symbol transformation: `BTCUSDT` → `BTCUSD_PERP` for CM
- Consider enum pattern refactor (scales better for 3+ types)

### v3.4.0 (Funding Rate Collection)

- Funding rate collection via `/fapi/v1/fundingRate` API endpoint
- Separate workflow (not available in Vision klines data)
- Populate existing `funding_rate` column (no schema migration)

### v3.x.0 (Potential Refactor)

- Extract validation to `utils/validation.py` (reduce duplication)
- Refactor to `InstrumentType` enum with properties (DSM pattern)
- Centralize URL routing logic (eliminate if/else across layers)

---

**ADR-0021** | UM Futures Support | Accepted | 2025-11-19
