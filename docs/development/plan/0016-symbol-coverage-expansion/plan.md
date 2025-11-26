# Symbol Coverage Expansion Implementation Plan

**ADR ID**: 0016
**Status**: In Progress
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-19
**Target Release**: v2.4.0

---

## Objective

Expand symbol coverage from 6 to 20 symbols with **dual coverage for both spot and UM-margined perpetual futures markets**.

## Background

### Problem

Current 6-symbol limitation prevents cross-sectional analysis strategies:

- **Market Coverage**: Only ~30% of crypto market cap
- **Strategy Limitation**: Insufficient for relative value/market-neutral strategies
- **Alpha Forge Requirement**: Minimum 20 symbols for production deployment

### Solution

Add 14 new symbols (total: 20) with **mandatory dual coverage**:

- ✅ Available on Binance Spot market
- ✅ Available on Binance UM-margined perpetual futures
- ✅ Top 20 by market capitalization
- ✅ Sufficient historical data (listing before 2024-01-01)

## Goals

1. **Expand to 20 symbols** - Add 14 new symbols to `known_symbols` dictionary
2. **Dual Market Coverage** - Validate spot + futures availability for all symbols
3. **Accurate Listing Dates** - Prevent invalid historical data requests
4. **Update Documentation** - Reflect new symbol count across all docs
5. **Test Coverage** - Validate both spot and futures data ingestion

## Non-Goals

- Symbols 21-50 (defer to future releases based on demand)
- Auto-discovery from Binance API (manual curation sufficient for now)
- Symbol categorization by sector (defer to v3.0)
- Historical data backfill (users fetch on-demand)

## Design

### Symbol Selection Criteria

**Mandatory requirements**:

1. Top 20 by market capitalization (CoinMarketCap/CoinGecko)
2. Available on Binance Spot market
3. Available on Binance UM-margined perpetual futures
4. Listing date < 2024-01-01 (sufficient historical data)
5. High trading volume (top 30 by 24h volume)

### Selected Symbols (14 New)

| Symbol    | Rank | Spot | Futures | Listing Date | Validation |
| --------- | ---- | ---- | ------- | ------------ | ---------- |
| BNBUSDT   | #3   | ✅   | ✅      | 2017-11-06   | Required   |
| XRPUSDT   | #5   | ✅   | ✅      | 2018-05-04   | Required   |
| DOGEUSDT  | #8   | ✅   | ✅      | 2021-05-05   | Required   |
| AVAXUSDT  | #11  | ✅   | ✅      | 2020-09-22   | Required   |
| MATICUSDT | #16  | ✅   | ✅      | 2019-04-26   | Required   |
| LTCUSDT   | #18  | ✅   | ✅      | 2018-01-23   | Required   |
| UNIUSDT   | #19  | ✅   | ✅      | 2020-09-17   | Required   |
| ATOMUSDT  | #21  | ✅   | ✅      | 2019-04-22   | Required   |
| FTMUSDT   | #27  | ✅   | ✅      | 2019-10-31   | Required   |
| NEARUSDT  | #28  | ✅   | ✅      | 2020-11-02   | Required   |
| ALGOUSDT  | #31  | ✅   | ✅      | 2019-06-20   | Required   |
| SANDUSDT  | #38  | ✅   | ✅      | 2020-08-13   | Required   |
| MANAUSDT  | #42  | ✅   | ✅      | 2020-12-14   | Required   |
| APEUSDT   | #48  | ✅   | ✅      | 2022-03-17   | Required   |

**Total**: 6 existing + 14 new = 20 symbols

## Detailed Design

### Implementation Changes

#### 1. Update BinancePublicDataCollector

**File**: `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py`

**Location**: Lines 280-287

**Change**:

````python
# Before (6 symbols)
self.known_symbols = {
    "BTCUSDT": "2017-08-17",
    "ETHUSDT": "2017-08-17",
    "SOLUSDT": "2020-08-11",
    "ADAUSDT": "2018-04-17",
    "DOTUSDT": "2020-08-19",
    "LINKUSDT": "2019-01-16",
}

# After (20 symbols with dual coverage documentation)
self.known_symbols = {
    # Existing symbols (validated for spot + futures)
    "BTCUSDT": "2017-08-17",   # #1 market cap
    "ETHUSDT": "2017-08-17",   # #2 market cap
    "SOLUSDT": "2020-08-11",   # #4 market cap
    "ADAUSDT": "2018-04-17",   # #9 market cap
    "DOTUSDT": "2020-08-19",   # #13 market cap
    "LINKUSDT": "2019-01-16",  # #14 market cap

    # New symbols (spot + futures dual coverage validated 2025-11-19)
    "BNBUSDT": "2017-11-06",   # #3 market cap
    "XRPUSDT": "2018-05-04",   # #5 market cap
    "DOGEUSDT": "2021-05-05",  # #8 market cap
    "AVAXUSDT": "2020-09-22",  # #11 market cap
    "MATICUSDT": "2019-04-26", # #16 market cap
    "LTCUSDT": "2018-01-23",   # #18 market cap
    "UNIUSDT": "2020-09-17",   # #19 market cap
    "ATOMUSDT": "2019-04-22",  # #21 market cap
    "FTMUSDT": "2019-10-31",   # #27 market cap
    "NEARUSDT": "2020-11-02",  # #28 market cap
    "ALGOUSDT": "2019-06-20",  # #31 market cap
    "SANDUSDT": "2020-08-13",  # #38 market cap
    "MANAUSDT": "2020-12-14",  # #42 market cap
    "APEUSDT": "2022-03-17",   # #48 market cap
}
```text

#### 2. Update Type Hints

**File**: `src/gapless_crypto_clickhouse/api.py`

**Location**: Lines 69-88

**Change**:

```python
# Before
SupportedSymbol = Literal[
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "ADAUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",  # Already in type hints but not in known_symbols
    "AVAXUSDT",   # Already in type hints but not in known_symbols
    # ... (inconsistent with actual coverage)
]

# After (consistent with known_symbols)
SupportedSymbol = Literal[
    # Top 20 by market cap (spot + futures dual coverage)
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "MATICUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "FTMUSDT",
    "NEARUSDT", "ALGOUSDT", "SANDUSDT", "MANAUSDT", "APEUSDT",
]
```bash

#### 3. Update Documentation

**Files to update**:

1. **README.md** (multiple locations)
   - Symbol count: "6 supported symbols" → "20 supported symbols"
   - Example lists: Add new symbols to examples

2. **docs/architecture/DATA_FORMAT.md**
   - Update supported symbols list

3. **docs/guides/python-api.md**
   - Update `get_supported_symbols()` output examples
   - Add examples with new symbols

4. **API docstrings**
   - `get_supported_symbols()`: Update expected output
   - Function examples: Use diverse symbol sets

### Data Availability Validation

**Validation Method**: Manual curl test to Binance Public Data Repository

**Spot Market Validation**:

```bash
# Test each new symbol for spot data availability
for symbol in BNBUSDT XRPUSDT DOGEUSDT AVAXUSDT MATICUSDT LTCUSDT UNIUSDT ATOMUSDT FTMUSDT NEARUSDT ALGOUSDT SANDUSDT MANAUSDT APEUSDT; do
  echo "Checking $symbol spot..."
  curl -s "https://data.binance.vision/?prefix=data/spot/monthly/klines/${symbol}/1d/" | grep -q ".zip"
  if [ $? -eq 0 ]; then
    echo "  ✅ Spot data available"
  else
    echo "  ❌ Spot data MISSING - blocker!"
  fi
done
```text

**Futures Market Validation**:

```bash
# Test each new symbol for UM-margined futures data availability
for symbol in BNBUSDT XRPUSDT DOGEUSDT AVAXUSDT MATICUSDT LTCUSDT UNIUSDT ATOMUSDT FTMUSDT NEARUSDT ALGOUSDT SANDUSDT MANAUSDT APEUSDT; do
  echo "Checking $symbol futures..."
  curl -s "https://data.binance.vision/?prefix=data/futures/um/monthly/klines/${symbol}/1d/" | grep -q ".zip"
  if [ $? -eq 0 ]; then
    echo "  ✅ Futures data available"
  else
    echo "  ❌ Futures data MISSING - blocker!"
  fi
done
```bash

**Expected Result**: All 14 symbols must show ✅ for BOTH spot and futures.

### Test Strategy

**Test Coverage Requirements**:

1. **Unit Tests** (`tests/test_symbol_expansion.py`):

```python
def test_symbol_count():
    """Verify 20 symbols available."""
    from gapless_crypto_clickhouse import get_supported_symbols
    symbols = get_supported_symbols()
    assert len(symbols) == 20

def test_new_symbols_present():
    """Verify all new symbols added."""
    from gapless_crypto_clickhouse import get_supported_symbols
    symbols = get_supported_symbols()
    new_symbols = ["BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "MATICUSDT",
                   "LTCUSDT", "UNIUSDT", "ATOMUSDT", "FTMUSDT", "NEARUSDT",
                   "ALGOUSDT", "SANDUSDT", "MANAUSDT", "APEUSDT"]
    for symbol in new_symbols:
        assert symbol in symbols, f"{symbol} missing from supported symbols"

def test_listing_dates_accurate():
    """Verify listing dates prevent pre-listing requests."""
    from gapless_crypto_clickhouse.collectors import BinancePublicDataCollector
    import warnings

    # APE listed 2022-03-17, requesting 2020 data should warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        collector = BinancePublicDataCollector(
            symbol="APEUSDT",
            start_date="2020-01-01",
            end_date="2024-01-01"
        )
        assert len(w) > 0
        assert "before" in str(w[0].message).lower()
```text

2. **Integration Tests** (spot + futures):

```python
def test_spot_data_fetch_new_symbols():
    """Verify spot data fetching works for new symbols."""
    import gapless_crypto_clickhouse as gcch
    df = gcch.fetch_data("BNBUSDT", "1d", start="2024-01-01", end="2024-01-02")
    assert len(df) > 0
    assert "open" in df.columns

def test_futures_data_fetch_new_symbols():
    """Verify futures data ingestion works for new symbols."""
    from gapless_crypto_clickhouse.clickhouse import ClickHouseConnection
    from gapless_crypto_clickhouse.collectors.clickhouse_bulk_loader import ClickHouseBulkLoader

    with ClickHouseConnection() as conn:
        loader = ClickHouseBulkLoader(conn, instrument_type="futures")
        rows = loader.ingest_month("BNBUSDT", "1d", year=2024, month=1)
        assert rows > 0  # Should successfully ingest futures data
````

## Implementation Checklist

### Pre-Implementation

- [x] Create ADR-0016
- [x] Create this plan document
- [ ] Validate spot data availability for all 14 new symbols
- [ ] Validate futures data availability for all 14 new symbols
- [ ] Document listing dates from Binance historical data

### Implementation

- [ ] Update `known_symbols` in BinancePublicDataCollector
- [ ] Update `SupportedSymbol` type hints in api.py
- [ ] Update README.md symbol count and examples
- [ ] Update docs/architecture/DATA_FORMAT.md
- [ ] Update docs/guides/python-api.md
- [ ] Update API docstrings

### Validation

- [ ] Run unit tests (symbol count, new symbols present)
- [ ] Run integration tests (spot data fetch)
- [ ] Run integration tests (futures data fetch)
- [ ] Manual spot data validation (curl tests)
- [ ] Manual futures data validation (curl tests)
- [ ] CI/CD passes on all Python versions

### Release

- [ ] Commit with conventional commit message
- [ ] semantic-release creates v2.4.0
- [ ] Publish to PyPI
- [ ] Verify on PyPI: 20 symbols documented
- [ ] Notify Alpha Forge of expanded coverage

## Rollout Plan

### Timeline

- **Day 1 (2025-11-19)**: Implementation + validation
- **Day 1 (2025-11-19)**: Release v2.4.0 to PyPI
- **Day 2 (2025-11-20)**: Alpha Forge testing with 20 symbols

### Validation Steps

1. **Pre-Release**: Manual curl validation for all 14 symbols (spot + futures)
2. **Post-Release**: Install from PyPI and verify `get_supported_symbols()` returns 20
3. **Integration Test**: Fetch data for 1 new symbol (spot + futures)

### Rollback Strategy

If critical data availability issues found:

1. Identify problematic symbols
2. Remove from `known_symbols` in hotfix
3. Release v2.4.1 with reduced symbol list
4. Communicate removal to users

**Mitigation**: Comprehensive pre-release validation reduces rollback risk.

## Risks and Mitigations

### Risk 1: Futures Data Unavailable for Some Symbols

**Risk**: One or more symbols missing futures market data
**Likelihood**: Low (validated before implementation)
**Impact**: High (blocks dual coverage promise)
**Mitigation**: Validate ALL symbols before committing code changes

### Risk 2: Incorrect Listing Dates

**Risk**: Listing date errors cause invalid data requests
**Likelihood**: Medium (manual data entry)
**Impact**: Medium (warnings issued, no data fetched)
**Mitigation**: Cross-reference listing dates from multiple sources (Binance, CoinMarketCap)

### Risk 3: Symbol Delisting/Suspension

**Risk**: Binance delists or suspends trading for a symbol post-release
**Likelihood**: Very Low (top market cap symbols)
**Impact**: Low (users get clear error messages)
**Mitigation**: Monitor Binance announcements, update in patch release if needed

## Success Metrics

### Primary Metrics

- [ ] `get_supported_symbols()` returns 20 symbols
- [ ] All 20 symbols fetch spot data successfully
- [ ] All 20 symbols ingest futures data successfully
- [ ] Zero data availability errors in CI/CD
- [ ] Alpha Forge confirms 20-symbol coverage

### Secondary Metrics

- [ ] Documentation accurately reflects 20-symbol support
- [ ] Type hints consistent with actual coverage
- [ ] CI/CD runtime < 10 minutes (despite increased test surface)

## Open Questions

- **Q**: Should we add more than 20 symbols?
  **A**: No - 20 meets Alpha Forge minimum, defer 21-50 based on demand

- **Q**: What if a symbol is delisted?
  **A**: Issue warning, remove in next release, maintain backward compatibility

- **Q**: How often to update symbol list?
  **A**: Quarterly review based on market cap changes

## References

- ADR-0016: Symbol Coverage Expansion
- ADR-0004: USDT-Margined Futures Support
- Binance Public Data: https://data.binance.vision
- Alpha Forge Feedback: Priority 2 requirement

## Log Files

Implementation logs stored in:

- `logs/0016-symbol-coverage-expansion-YYYYMMDD_HHMMSS.log`

---

**Plan 0016** | Symbol Coverage Expansion | In Progress | 2025-11-19
