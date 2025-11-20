# UM Futures Support Implementation Plan

**ADR ID**: 0021
**Status**: In Progress
**Owner**: Terry Li
**Created**: 2025-11-19
**Updated**: 2025-11-19
**Target Release**: v3.2.0

---

## Objective

Implement complete USDT-margined perpetual futures data collection with **timestamp precision enhancement** to fulfill documentation promises and enable Alpha Forge integration.

**Critical Enhancement**: Fix timestamp precision to handle Binance's January 1, 2025 format transition (spot data now uses **microseconds** instead of milliseconds).

## Background

### Problem

**Documentation vs Reality Gap**: Current v3.1.1 documentation claims "USDT-margined futures support (400+ symbols)" but implementation only collects spot data. Alpha Forge identified this as a blocker for production integration.

**Timestamp Precision Issue**: Discovered during 5-agent audit - Binance Vision API transitioned spot data to **microsecond precision** (DateTime64(6)) on January 1, 2025, while futures remain in milliseconds. Current schema uses DateTime64(3), causing **1000x timestamp errors** for spot data collected after 2025-01-01.

### Solution

Add `instrument_type` parameter across API with enum-driven URL/endpoint routing, integrate `binance-futures-availability` for 713 validated symbols, and **upgrade schema to DateTime64(6)** with automatic format detection and conversion.

## Context

### Audit Findings Summary (5-Agent Parallel Audit)

**Audit Date**: 2025-11-19
**Audit Location**: `/tmp/um-futures-audit/`
**Overall Status**: Conditional Approval (critical fixes required)

| Agent         | Focus                 | Rating | Key Finding                                          |
| ------------- | --------------------- | ------ | ---------------------------------------------------- |
| Technical     | API/Schema validation | 6/10   | **BLOCKER**: Timestamp precision (μs vs ms)          |
| Architecture  | Design patterns       | 8.5/10 | ✅ Solid design, enum pattern for v3.3.0             |
| Feasibility   | Timeline/complexity   | 5/10   | ⚠️ 40-73% underestimated (11h → 23h)                 |
| Testing       | Coverage/scenarios    | 6/10   | ⚠️ 12 critical test gaps identified                  |
| Documentation | UX/clarity            | 6/10   | ⚠️ False v3.1.1 claims, funding_rate warnings needed |

**Critical Issues Addressed**:

1. ✅ Timestamp precision fix (DateTime64(6)) - included in v3.2.0
2. ✅ Timeline adjusted (11h → 23h conservative estimate)
3. ✅ Test coverage expanded (15 → 27 tests)
4. ✅ Documentation enhanced (funding_rate warnings, "What's New" section)
5. ⚠️ v3.1.1 doc fix deferred (implement features first)

### Related Work

- **ADR-0004**: Superseded QuestDB futures implementation (same pattern, different DB)
- **ADR-0020**: Multi-Symbol Batch API (provides concurrent download foundation)
- **binance-futures-availability**: 713 validated symbols with daily S3 probes

## Goals

1. **Timestamp Precision Fix** - Upgrade to DateTime64(6) for microsecond support
2. **Add instrument_type Parameter** - "spot" (default) or "futures-um"
3. **URL Routing** - Route to correct Vision API path per instrument type
4. **API Endpoint Selection** - Use futures REST API for gap filling
5. **Symbol Integration** - Load 713 futures symbols from binance-futures-availability
6. **Schema Enhancement** - Add nullable funding_rate column (future-proof)
7. **100% Backward Compatible** - All existing spot code works unchanged
8. **Comprehensive Testing** - 27 tests (15 original + 12 critical from audit)

## Non-Goals

- Funding rate data collection (deferred - requires separate `/fapi/v1/fundingRate` API)
- Coin-margined futures (CM, deferred - requires symbol transformation)
- Async API (ThreadPoolExecutor sufficient for I/O-bound operations)
- Performance optimization (spot performance already validated at 1.1M rows/sec)
- Fixing v3.1.1 documentation (implement features first, update docs after)

## Design

### Timestamp Precision Architecture (NEW - Critical Fix)

**Problem Statement**: Binance Vision API format transition

| Date              | Spot Data Format             | Futures Data Format      |
| ----------------- | ---------------------------- | ------------------------ |
| Before 2025-01-01 | Milliseconds (13 digits)     | Milliseconds (13 digits) |
| After 2025-01-01  | **Microseconds (16 digits)** | Milliseconds (13 digits) |

**Current Schema** (INCORRECT):

```sql
timestamp DateTime64(3)  -- Millisecond precision
```

**Impact**: Spot data after Jan 1, 2025 has timestamps off by 1000x

**Solution**: Universal microsecond precision

```sql
-- New schema (CORRECT for both spot and futures)
timestamp DateTime64(6)  -- Microsecond precision
```

**Format Detection**:

```python
def detect_timestamp_precision(timestamp: int) -> str:
    """Detect precision from timestamp magnitude.

    Args:
        timestamp: Raw timestamp from Binance CSV

    Returns:
        "microseconds" or "milliseconds"

    Examples:
        1704067200000000 (16 digits) → "microseconds"
        1704067200000 (13 digits) → "milliseconds"
    """
    if timestamp > 1e15:  # 16 digits
        return "microseconds"
    else:  # 13 digits
        return "milliseconds"
```

**Conversion Logic**:

```python
def normalize_timestamp_to_microseconds(
    timestamp: int,
    source_precision: str
) -> int:
    """Normalize all timestamps to microseconds.

    Args:
        timestamp: Raw timestamp
        source_precision: Detected precision level

    Returns:
        Timestamp in microseconds (DateTime64(6) compatible)
    """
    if source_precision == "microseconds":
        return timestamp  # Already correct
    elif source_precision == "milliseconds":
        return timestamp * 1000  # ms → μs
    else:
        raise ValueError(f"Unknown precision: {source_precision}")
```

### API Layer Changes

**Functions Updated**:

- `fetch_data()` - Add instrument_type parameter
- `download()` - Add instrument_type parameter
- `download_multiple()` - Add instrument_type parameter
- `get_supported_symbols()` - Add instrument_type parameter
- `fill_gaps()` - Add instrument_type parameter

**New Validation Function**:

```python
def _validate_instrument_type(instrument_type: str) -> None:
    """Validate instrument_type is 'spot' or 'futures-um'."""
    valid_types = {"spot", "futures-um"}
    if instrument_type not in valid_types:
        raise ValueError(
            f"Invalid instrument_type '{instrument_type}'. "
            f"Must be one of: {', '.join(sorted(valid_types))}"
        )
```

**Symbol Loading**:

```python
from binance_futures_availability.config.symbol_loader import load_symbols

def get_supported_symbols(
    instrument_type: Literal["spot", "futures-um"] = "spot"
) -> List[str]:
    """Get supported symbols for instrument type."""
    _validate_instrument_type(instrument_type)

    if instrument_type == "futures-um":
        return load_symbols("perpetual")  # 713 symbols
    else:
        collector = BinancePublicDataCollector()
        return list(collector.known_symbols.keys())  # 20 symbols
```

### Collector Layer Changes

**BinancePublicDataCollector URL Routing**:

```python
class BinancePublicDataCollector:
    """Ultra-fast data collection with spot and UM futures support."""

    SPOT_BASE_URL = "https://data.binance.vision/data/spot"
    FUTURES_BASE_URL = "https://data.binance.vision/data/futures/um"

    def __init__(
        self,
        symbol: str = "SOLUSDT",
        start_date: str = "2020-08-15",
        end_date: str = "2025-03-20",
        output_dir: Optional[Union[str, Path]] = None,
        output_format: str = "csv",
        instrument_type: str = "spot",  # NEW PARAMETER
    ):
        # Validate instrument_type FIRST (fail fast)
        if instrument_type not in ("spot", "futures-um"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. "
                f"Must be 'spot' or 'futures-um'"
            )

        self.instrument_type = instrument_type

        # Set base_url based on instrument_type
        self.base_url = (
            f"{self.SPOT_BASE_URL}/monthly/klines"
            if instrument_type == "spot"
            else f"{self.FUTURES_BASE_URL}/monthly/klines"
        )

        # Rest of initialization...
```

### Gap Filler Layer Changes

**UniversalGapFiller API Endpoint Selection**:

```python
class UniversalGapFiller:
    """Universal gap detection with spot and futures support."""

    SPOT_API_URL = "https://api.binance.com/api/v3/klines"
    FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/klines"

    def __init__(self, instrument_type: str = "spot"):
        if instrument_type not in ("spot", "futures-um"):
            raise ValueError(
                f"Invalid instrument_type: '{instrument_type}'. "
                f"Must be 'spot' or 'futures-um'"
            )

        self.instrument_type = instrument_type
        self.api_url = (
            self.SPOT_API_URL if instrument_type == "spot"
            else self.FUTURES_API_URL
        )
```

### ClickHouse Schema Changes

**Schema Migration SQL**:

```sql
-- Phase 1: Upgrade timestamp precision (CRITICAL)
ALTER TABLE ohlcv MODIFY COLUMN timestamp DateTime64(6);

-- Phase 2: Add funding_rate column (future-proof)
ALTER TABLE ohlcv
ADD COLUMN IF NOT EXISTS funding_rate Nullable(Float64) CODEC(Gorilla, LZ4)
AFTER taker_buy_quote_asset_volume;

-- Verification
DESCRIBE TABLE ohlcv;
```

**Column Characteristics**:

- `timestamp`: DateTime64(6) - Universal microsecond precision
- `funding_rate`: Nullable(Float64) - NULL for spot and unpopulated futures
- NOT in ORDER BY - Avoids nullable key restrictions
- NOT in `_version` hash - Updates don't create new versions
- Gorilla codec - Optimal compression for float time-series

## Implementation Checklist

### Phase 0: Setup & Documentation (0.5h)

**Context**: Create foundational documents and logging infrastructure

- [x] Create ADR-0021 (MADR format with enhanced alternative analysis)
- [x] Create this plan document (Google Design Doc format)
- [x] Set up logs/ directory for implementation tracking
- [ ] Copy audit artifacts from /tmp/um-futures-audit/ to docs/

**Task List Sync**: Tasks 1-3 in todo list

---

### Phase 1: Timestamp Precision Fix (2.5h)

**Context**: Handle Binance's Jan 1, 2025 format transition (spot→μs, futures→ms)

- [ ] Implement `detect_timestamp_precision()` utility function
  - Location: `src/gapless_crypto_clickhouse/utils/timestamp_utils.py`
  - Input: Integer timestamp from CSV
  - Output: "microseconds" or "milliseconds"
  - Logic: Magnitude-based detection (>1e15 = microseconds)

- [ ] Implement `normalize_timestamp_to_microseconds()` conversion
  - Location: `src/gapless_crypto_clickhouse/utils/timestamp_utils.py`
  - Input: Timestamp + detected precision
  - Output: Normalized microsecond timestamp
  - Logic: Multiply milliseconds by 1000

- [ ] Update CSV parsing to use timestamp utilities
  - Location: `src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py`
  - Detect precision on first row
  - Apply conversion if needed
  - Validate output timestamps

- [ ] Update ClickHouse schema
  - File: `src/gapless_crypto_clickhouse/clickhouse/schema.sql`
  - Change: `DateTime64(3)` → `DateTime64(6)`
  - Document: Add comment explaining dual precision support

- [ ] Update DATA_FORMAT.md with precision documentation
  - Section: Add "Timestamp Precision" subsection
  - Explain: Spot (μs after 2025-01-01) vs Futures (ms)
  - Examples: Show format detection logic

- [ ] Test timestamp conversion
  - Unit test: Detect precision correctly
  - Unit test: Convert milliseconds → microseconds
  - Integration test: Parse real spot CSV (post-2025-01-01)
  - Integration test: Parse real futures CSV (still milliseconds)

**Dependencies**: None (foundational change)

**Validation**:

```bash
uv run pytest tests/test_timestamp_utils.py -v
```

**Auto-Fix Strategy**: If tests fail, adjust magnitude threshold or conversion multiplier

**Task List Sync**: Task 4 in todo list

---

### Phase 2: Dependencies (0.25h)

**Context**: Add binance-futures-availability for 713 validated symbols

- [ ] Update pyproject.toml
  - Add: `binance-futures-availability>=1.0.0` to dependencies list
  - Location: After existing dependencies, before dev dependencies

- [ ] Regenerate lockfile
  - Command: `uv lock --upgrade`
  - Expected: Resolve binance-futures-availability and its dependencies

- [ ] Verify installation
  - Command: `uv sync`
  - Test import: `python -c "from binance_futures_availability.config.symbol_loader import load_symbols; print(len(load_symbols('perpetual')))"`
  - Expected output: `713`

**Dependencies**: None

**Validation**:

```bash
uv run python -c "from binance_futures_availability.config.symbol_loader import load_symbols; assert len(load_symbols('perpetual')) == 713"
```

**Auto-Fix Strategy**: If import fails, check package name spelling or version constraints

**Task List Sync**: Task 5 in todo list

---

### Phase 3: ClickHouse Schema Migration (1.75h)

**Context**: Apply DateTime64(6) and funding_rate schema changes with production validation

- [ ] Update schema.sql with DateTime64(6)
  - File: `src/gapless_crypto_clickhouse/clickhouse/schema.sql`
  - Change timestamp precision
  - Add funding_rate column

- [ ] Create migration verification script
  - File: `scripts/verify_schema_migration.py`
  - Check: Column exists, correct type, nullable settings
  - Output: Pass/fail with error details

- [ ] Test ALTER TABLE idempotency (CRITICAL - from audit)
  - Create test ClickHouse instance
  - Run ALTER TABLE twice
  - Verify: No errors, no duplicate columns
  - Validate: Schema unchanged after second run

- [ ] Test zero-downtime migration
  - Insert data before migration
  - Run ALTER TABLE
  - Query data during migration
  - Verify: No connection errors, data accessible

- [ ] Document rollback procedure
  - File: `docs/development/plan/0021-um-futures-support/rollback.md`
  - Steps: How to revert DateTime64(6) → DateTime64(3)
  - Warning: Data loss implications

- [ ] Update DATA_FORMAT.md with funding_rate documentation
  - Section: Add "funding_rate Column (v3.2.0+)" subsection
  - Status: NULL initially, populated in future release
  - Use case: Funding rate collection workflow

**Dependencies**: Phase 0 complete

**Validation**:

```bash
uv run python scripts/verify_schema_migration.py
```

**Auto-Fix Strategy**: If migration fails, check ClickHouse version compatibility or nullable constraints

**Task List Sync**: Task 6 in todo list

---

### Phase 4: API Layer Implementation (3.5h)

**Context**: Add instrument_type parameter to 5 public functions with validation

- [ ] Add `_validate_instrument_type()` function
  - Location: `src/gapless_crypto_clickhouse/api.py` (after imports)
  - Logic: Check against {"spot", "futures-um"}
  - Error: Raise ValueError with helpful message

- [ ] Update `_validate_symbol()` signature
  - Add: `instrument_type` parameter for context
  - Purpose: Future validation logic may differ by type

- [ ] Update `fetch_data()` signature
  - Add: `instrument_type: Literal["spot", "futures-um"] = "spot"`
  - Call: `_validate_instrument_type(instrument_type)`
  - Pass: `instrument_type` to BinancePublicDataCollector

- [ ] Update `download()` signature
  - Add: `instrument_type: Literal["spot", "futures-um"] = "spot"`
  - Call: `_validate_instrument_type(instrument_type)`
  - Pass: `instrument_type` to fetch_data()

- [ ] Update `download_multiple()` signature
  - Add: `instrument_type: Literal["spot", "futures-um"] = "spot"`
  - Call: `_validate_instrument_type(instrument_type)`
  - Pass: `instrument_type` to download() calls

- [ ] Update `get_supported_symbols()` implementation
  - Add: `instrument_type: Literal["spot", "futures-um"] = "spot"`
  - Logic: If futures-um, call `load_symbols("perpetual")`
  - Logic: If spot, return existing known_symbols
  - Verify: 713 symbols for futures-um, 20 for spot

- [ ] Update `fill_gaps()` signature
  - Add: `instrument_type: Literal["spot", "futures-um"] = "spot"`
  - Pass: `instrument_type` to UniversalGapFiller constructor

- [ ] Update `_perform_gap_filling()` internal function
  - Add: `instrument_type` parameter
  - Pass: To UniversalGapFiller constructor

- [ ] Add InstrumentType type alias
  - Location: After imports in api.py
  - Definition: `InstrumentType = Literal["spot", "futures-um"]`

- [ ] Update docstrings for ALL functions
  - Parameter: instrument_type documentation
  - Examples: Show both spot and futures usage
  - Warnings: funding_rate NULL for futures (prominent)

**Dependencies**: Phase 2 complete (binance-futures-availability installed)

**Validation**:

```bash
uv run pytest tests/test_api.py -k instrument_type -v
```

**Auto-Fix Strategy**: If validation errors occur, check type hint imports and function signatures

**Task List Sync**: Task 7 in todo list

---

### Phase 5: Collector Layer Implementation (1.75h)

**Context**: URL routing for spot vs futures-um Vision API

- [ ] Add URL constants to BinancePublicDataCollector
  - SPOT_BASE_URL: "https://data.binance.vision/data/spot"
  - FUTURES_BASE_URL: "https://data.binance.vision/data/futures/um"

- [ ] Update **init**() signature
  - Add: `instrument_type: str = "spot"` parameter
  - Validate: instrument_type in ("spot", "futures-um")
  - Set: self.instrument_type = instrument_type

- [ ] Implement URL routing logic
  - Set: self.base_url based on instrument_type
  - Spot: f"{SPOT_BASE_URL}/monthly/klines"
  - Futures: f"{FUTURES_BASE_URL}/monthly/klines"

- [ ] Update class docstring
  - Add: "Supports spot and UM futures" description
  - Examples: Show futures usage
  - Symbol counts: 20 spot, 713 futures-um

- [ ] Integrate timestamp precision utilities (from Phase 1)
  - Import: From timestamp_utils module
  - Detect: Precision on first CSV row
  - Convert: Apply normalization to all timestamps
  - Validate: Output timestamps in microseconds

- [ ] Test URL generation
  - Unit test: Spot URL correct
  - Unit test: Futures URL correct
  - Integration test: Download real futures data

**Dependencies**: Phase 1 (timestamp utils), Phase 4 (API layer) complete

**Validation**:

```bash
uv run pytest tests/test_binance_public_data_collector.py -v
```

**Auto-Fix Strategy**: If URL generation fails, check string formatting or base URL constants

**Task List Sync**: Task 8 in todo list

---

### Phase 6: Gap Filler Layer Implementation (0.75h)

**Context**: API endpoint selection for gap filling (spot vs futures REST API)

- [ ] Add API endpoint constants
  - SPOT_API_URL: "https://api.binance.com/api/v3/klines"
  - FUTURES_API_URL: "https://fapi.binance.com/fapi/v1/klines"

- [ ] Update **init**() signature
  - Add: `instrument_type: str = "spot"` parameter
  - Validate: instrument_type in ("spot", "futures-um")
  - Set: self.api_url based on instrument_type

- [ ] Update fill_gap() method
  - Replace: Hardcoded API URL with self.api_url
  - Verify: Correct endpoint used for each type

- [ ] Update class docstring
  - Add: "Supports spot and futures" description
  - API endpoints: Document both URLs

- [ ] Test API endpoint selection
  - Unit test: Spot endpoint correct
  - Unit test: Futures endpoint correct
  - Integration test: Gap fill with futures API

**Dependencies**: Phase 4 complete

**Validation**:

```bash
uv run pytest tests/test_universal_gap_filler.py -v
```

**Auto-Fix Strategy**: If endpoint selection fails, check URL constants or conditional logic

**Task List Sync**: Task 9 in todo list

---

### Phase 7: Type Hints (0.25h)

**Context**: Ensure type safety with proper annotations

- [ ] Verify InstrumentType type alias exported
  - Location: `src/gapless_crypto_clickhouse/__init__.py`
  - Check: Available for external use

- [ ] Run mypy type checking
  - Command: `uv run mypy src/gapless_crypto_clickhouse/`
  - Expected: Zero type errors

- [ ] Run pyright type checking
  - Command: `uv run pyright src/gapless_crypto_clickhouse/`
  - Expected: Zero type errors

- [ ] Verify all function signatures
  - Check: All parameters have type hints
  - Check: All return types annotated
  - Check: Literal["spot", "futures-um"] used consistently

**Dependencies**: Phases 4-6 complete

**Validation**:

```bash
uv run mypy src/gapless_crypto_clickhouse/ --strict
```

**Auto-Fix Strategy**: Add missing type hints or adjust Literal definitions

**Task List Sync**: Part of task 7-9 validation

---

### Phase 8: Comprehensive Testing (6h) - EXPANDED FROM AUDIT

**Context**: 27 tests total (15 original + 12 critical from audit findings)

#### Original Tests (15 tests, 2-3h)

**Backward Compatibility (4 tests)**:

- [ ] test_fetch_data_default_spot - Verify default behavior unchanged
- [ ] test_download_default_spot - Existing code works unchanged
- [ ] test_get_supported_symbols_default_spot - Returns 20 symbols
- [ ] test_download_multiple_default_spot - Batch defaults to spot

**Futures Functionality (4 tests)**:

- [ ] test_fetch_data_futures - instrument_type="futures-um" works
- [ ] test_download_futures - Downloads futures data
- [ ] test_get_supported_symbols_futures - Returns 713 symbols
- [ ] test_download_multiple_futures - Batch futures download

**Validation (3 tests)**:

- [ ] test_invalid_instrument_type - Rejects invalid values
- [ ] test_invalid_instrument_type_in_download - Validation at download level
- [ ] test_invalid_instrument_type_in_get_symbols - Validation at symbol level

**Collector Layer (2 tests)**:

- [ ] test_collector_spot_url - Spot URL generation correct
- [ ] test_collector_futures_url - Futures URL generation correct

**Gap Filler Layer (2 tests)**:

- [ ] test_gap_filler_spot_endpoint - Spot API endpoint correct
- [ ] test_gap_filler_futures_endpoint - Futures API endpoint correct

#### Critical Tests from Audit (12 tests, 3-4h)

**BLOCKER Tests (3 tests) - MUST HAVE**:

- [ ] test_futures_csv_12_to_11_column_transformation
  - **Purpose**: Verify "Ignore" column dropped correctly
  - **Risk**: Data corruption across entire futures dataset
  - **Validation**: Read futures CSV, verify 11 columns, no "Ignore" column

- [ ] test_funding_rate_column_initially_null
  - **Purpose**: Document funding_rate behavior (NULL in v3.2.0)
  - **Risk**: User confusion about data completeness
  - **Validation**: Download futures data, verify funding_rate column exists but all NULL

- [ ] test_funding_rate_column_migration_idempotent
  - **Purpose**: Schema migration can run multiple times safely
  - **Risk**: Production deployment failures
  - **Validation**: Run ALTER TABLE twice, verify no errors

**HIGH Priority Tests (3 tests) - Strong Recommendation**:

- [ ] test_futures_symbol_not_available_on_vision
  - **Purpose**: 404 handling for unavailable symbols
  - **Risk**: Crashes with unhelpful errors
  - **Validation**: Try download with unavailable symbol, expect clear error

- [ ] test_futures_api_rate_limit_recovery
  - **Purpose**: Gap filling handles rate limits gracefully
  - **Risk**: Silent failures during gap filling
  - **Validation**: Mock rate limit response, verify retry logic

- [ ] test_download_multiple_futures_with_spot_only_symbol
  - **Purpose**: Mixed market error handling
  - **Risk**: Partial failures unclear
  - **Validation**: Try futures-um download with spot-only symbol, expect clear error

**MEDIUM Priority Tests (6 tests) - Nice to Have**:

- [ ] test_futures_spot_data_sanity_check
  - **Purpose**: Data quality validation
  - **Validation**: Compare spot vs futures OHLCV, verify reasonable similarity

- [ ] test_concurrent_spot_and_futures_downloads
  - **Purpose**: File conflict prevention
  - **Validation**: Download same symbol as spot and futures concurrently

- [ ] test_funding_rate_column_removal_for_rollback
  - **Purpose**: Rollback safety validation
  - **Validation**: DROP COLUMN, verify old queries work

- [ ] test_instrument_type_case_insensitive
  - **Purpose**: Case handling validation
  - **Validation**: Try "SPOT", expect helpful error (or accept if case-insensitive)

- [ ] test_binance_futures_availability_import_error
  - **Purpose**: Missing dependency handling
  - **Validation**: Mock import failure, expect helpful error

- [ ] test_futures_batch_download_50_symbols
  - **Purpose**: Large batch performance
  - **Validation**: Download 50 symbols, verify <5min, no timeouts

**Dependencies**: Phases 1-7 complete

**Validation**:

```bash
# Run all 27 tests
uv run pytest tests/test_um_futures_support.py -v

# Run specific test categories
uv run pytest tests/test_um_futures_support.py -k "blocker" -v
uv run pytest tests/test_um_futures_support.py -k "high_priority" -v
```

**Auto-Fix Strategy**: If tests fail, fix implementation immediately before proceeding

**Task List Sync**: Task 10 in todo list

---

### Phase 9: Documentation (2.5h) - ENHANCED FROM AUDIT

**Context**: Add "What's New", funding_rate warnings, migration guide

- [ ] Create "What's New in v3.2.0" section
  - Location: Top of README.md (before Quick Start)
  - Content: Highlight futures support, 713 symbols, timestamp precision
  - Examples: Show basic futures download
  - Prominence: Make discoverable (users won't find feature otherwise)

- [ ] Add funding_rate NULL warnings
  - Location: ALL function docstrings (fetch_data, download, etc.)
  - Warning: "funding_rate column exists but NULL in v3.2.0"
  - Future: "Will be populated in v3.3.0 via /fapi/v1/fundingRate"

- [ ] Create migration guide section
  - Location: README.md or separate MIGRATION.md
  - Content: v3.1.1 → v3.2.0 upgrade steps
  - Breaking changes: None (fully backward compatible)
  - New features: instrument_type parameter, timestamp precision

- [ ] Update README.md Quick Start
  - Add: Futures examples after spot examples
  - Show: Single symbol futures download
  - Show: Multi-symbol batch futures download
  - Show: get_supported_symbols for futures (713 symbols)

- [ ] Update llms.txt SDK documentation
  - Update: Function signatures with instrument_type
  - Examples: Both spot and futures usage
  - Version: Update to 3.2.0
  - Symbol counts: 20 spot, 713 futures-um

- [ ] Update CLAUDE.md implementation details
  - Features: Add UM futures support
  - Core capability: Update to "20 spot + 713 futures"
  - Network architecture: Document dual API endpoints
  - Current architecture: Update validated features list

- [ ] Copy improved examples from audit
  - Source: `/tmp/um-futures-audit/improved_examples.md`
  - Destination: Integrate into README.md and llms.txt
  - Benefit: Save tokens, use pre-validated content

- [ ] Update DATA_FORMAT.md
  - Timestamp precision: Document microsecond vs millisecond
  - funding_rate: Document NULL status and future plans
  - Format detection: Explain automatic conversion

**Dependencies**: Phases 1-8 complete (all features implemented and tested)

**Validation**: Manual review of documentation clarity

**Task List Sync**: Task 11 in todo list

---

### Phase 10: Release (1.25h)

**Context**: Semantic release with conventional commit

- [ ] Run complete test suite
  - Command: `uv run pytest`
  - Expected: All 27 tests pass
  - Check: Coverage report shows new code covered

- [ ] Run type checking
  - Command: `uv run mypy src/`
  - Expected: Zero type errors

- [ ] Create conventional commit
  - Format: `feat(api): add UM futures support with 713 validated symbols`
  - Body: Include audit findings summary, breaking changes (none)
  - Footer: Reference ADR-0021, Plan-0021

- [ ] Push to GitHub
  - Command: `git push origin main`
  - Verify: CI passes on GitHub

- [ ] Run semantic-release
  - Command: `GH_TOKEN="$(gh auth token)" npx semantic-release --no-ci`
  - Expected: v3.2.0 tag created, CHANGELOG.md updated

- [ ] Verify GitHub release
  - Check: https://github.com/terrylica/gapless-crypto-clickhouse/releases/tag/v3.2.0
  - Verify: Release notes generated from commit

- [ ] Publish to PyPI
  - Script: `./scripts/publish-to-pypi.sh`
  - Expected: Package uploaded successfully
  - Verify: https://pypi.org/project/gapless-crypto-clickhouse/3.2.0/

- [ ] Test installation from PyPI
  - Command: `pip install gapless-crypto-clickhouse==3.2.0` in clean venv
  - Verify: futures support works
  - Test: `get_supported_symbols("futures-um")` returns 713

**Dependencies**: All phases 0-9 complete

**Validation**:

```bash
# Verify release
gh release view v3.2.0

# Verify PyPI
curl -s https://pypi.org/pypi/gapless-crypto-clickhouse/json | python3 -c "import sys, json; print(json.load(sys.stdin)['info']['version'])"
```

**Task List Sync**: Tasks 12-13 in todo list

---

## Task List (Synchronized with Todo List)

### Current Status (2025-11-19)

**Completed** ✅:

1. Create ADR-0021 MADR document
2. Create plan document (this file)
3. Set up logging directory

**In Progress** 🔄: 4. Implement timestamp precision fix (Phase 1)

**Pending** ⏳: 5. Add binance-futures-availability dependency (Phase 2) 6. Update ClickHouse schema (Phase 3) 7. Implement API layer changes (Phase 4) 8. Implement Collector layer changes (Phase 5) 9. Implement Gap Filler layer changes (Phase 6) 10. Write 27 tests (Phase 8) 11. Update documentation (Phase 9) 12. Run tests and validate (Phase 10) 13. Create conventional commit and release (Phase 10)

**Progress**: 3/13 tasks complete (23%)

---

## Detailed Design

### Error Handling Strategy

**Principle**: Raise+propagate (no fallback, no default, no retry, no silent failures)

**Validation Errors**:

```python
# Invalid instrument_type
raise ValueError(
    f"Invalid instrument_type '{value}'. "
    f"Must be one of: futures-um, spot"
)

# Invalid symbol for futures
raise ValueError(
    f"Symbol '{symbol}' not available for futures-um. "
    f"Use get_supported_symbols('futures-um') for valid symbols."
)
```

**Network Errors**:

```python
# 404 from Vision API (symbol not available)
raise DataCollectionError(
    f"Symbol '{symbol}' not available on Binance Vision for '{instrument_type}'. "
    f"Data may not exist for this date range."
)

# Rate limit from REST API
# Let httpx retry logic handle (existing behavior)
# No special futures-specific handling needed
```

### Concurrency Considerations

**ThreadPoolExecutor Usage**: Already implemented in `download_multiple()` (ADR-0020)

**Futures-Specific**: No changes needed, ThreadPoolExecutor handles both spot and futures

**Resource Management**:

- Connection pooling: httpx handles automatically
- Memory: Same as spot (11 columns per DataFrame)
- File handles: Same cleanup logic

### CSV Format Normalization

**Spot CSV** (no header, 11 columns):

```
1640995200000,46444.99,46445.00,46368.77,46393.00,45.33775,...
```

**Futures CSV** (with header, 12 columns):

```
open_time,open,high,low,close,volume,close_time,quote_asset_volume,number_of_trades,taker_buy_base_asset_volume,taker_buy_quote_asset_volume,ignore
1640995200000,46444.99,46445.00,46368.77,46393.00,45.33775,...,0
```

**Normalization Logic**:

```python
if instrument_type == "futures-um":
    # Read with header, drop last column
    df = pd.read_csv(csv_path, header=0, usecols=range(11))
else:
    # Read without header, all 11 columns
    df = pd.read_csv(csv_path, header=None, names=[...])
```

### Performance Characteristics

**Vision API Download**: Same as spot (22x faster than API-only)

**Futures API (gap filling)**:

- Endpoint: `fapi.binance.com/fapi/v1/klines`
- Rate limits: Similar to spot API
- Max limit: **1500** bars per request (vs 1000 for spot)

**ClickHouse Ingestion**: Same performance (1.1M rows/sec validated)

---

## Timeline

### Conservative Estimate (Recommended): 23 hours (3 business days)

| Phase                      | Duration | Cumulative | Notes                                    |
| -------------------------- | -------- | ---------- | ---------------------------------------- |
| 0. Setup & Documentation   | 0.5h     | 0.5h       | ADR, plan, logging                       |
| 1. Timestamp Precision Fix | 2.5h     | 3h         | **NEW** - Critical fix                   |
| 2. Dependencies            | 0.25h    | 3.25h      | binance-futures-availability             |
| 3. ClickHouse Schema       | 1.75h    | 5h         | DateTime64(6), funding_rate, idempotency |
| 4. API Layer               | 3.5h     | 8.5h       | 5 functions, validation, docstrings      |
| 5. Collector Layer         | 1.75h    | 10.25h     | URL routing, timestamp integration       |
| 6. Gap Filler Layer        | 0.75h    | 11h        | API endpoint selection                   |
| 7. Type Hints              | 0.25h    | 11.25h     | mypy/pyright validation                  |
| 8. Testing                 | 6h       | 17.25h     | **EXPANDED** - 27 tests                  |
| 9. Documentation           | 2.5h     | 19.75h     | **ENHANCED** - warnings, migration guide |
| 10. Release                | 1.25h    | 21h        | Commit, semantic-release, PyPI           |
| **BUFFER**                 | 2h       | **23h**    | Debugging, edge cases, unknowns          |

**Confidence**: High (85%)

### Original Plan Estimate (NOT RECOMMENDED): 11 hours

**Risk**: 90%+ probability of technical debt, insufficient testing, production issues

---

## Risks and Mitigations

### Risk 1: Timestamp Precision Migration Failure

**Risk**: DateTime64(6) migration breaks existing data
**Likelihood**: Low (ALTER TABLE is safe operation)
**Impact**: High (all timestamps corrupted)
**Mitigation**:

- Test migration on development ClickHouse first
- Verify idempotency (run twice, no errors)
- Document rollback procedure (ALTER MODIFY COLUMN back to DateTime64(3))
- Backup strategy: Export data before migration

### Risk 2: Symbol Availability Mismatch

**Risk**: Some futures symbols may not have data on Vision API
**Likelihood**: Low (713 symbols validated daily via binance-futures-availability)
**Impact**: Medium (download fails with 404)
**Mitigation**:

- Clear error messages with symbol name
- Suggest `get_supported_symbols('futures-um')` for valid list
- binance-futures-availability has 95%+ SLA

### Risk 3: Funding Rate Column Confusion

**Risk**: Users expect funding_rate to be populated
**Likelihood**: Medium (column exists but NULL)
**Impact**: Low (user confusion, not functional issue)
**Mitigation**:

- **Prominent warnings** in ALL function docstrings
- README callout section about NULL status
- DATA_FORMAT.md explains future population
- "What's New" section mentions deferred implementation

### Risk 4: CSV Normalization Failure

**Risk**: 12→11 column transformation drops wrong column
**Likelihood**: Low (simple usecols logic)
**Impact**: Critical (data corruption across futures dataset)
**Mitigation**:

- **BLOCKER test** validates transformation
- Integration test with real futures CSV
- Verify last column name is "ignore" (not a data column)

### Risk 5: API Endpoint Differences

**Risk**: Futures REST API has different rate limits or behavior
**Likelihood**: Low (both Binance APIs, similar structure)
**Impact**: Low (gap filling may hit limits)
**Mitigation**:

- Same retry logic applies to both endpoints
- Monitor gap filling failures in production
- Document any differences discovered (e.g., limit=1500 for futures)

---

## Success Metrics

### Primary Metrics

- [ ] All 27 tests pass (including 3 BLOCKER tests)
- [ ] Zero backward compatibility breaks (existing spot code works)
- [ ] Timestamp precision correct (spot=μs, futures=ms, output=μs)
- [ ] 713 futures symbols loaded successfully
- [ ] Schema migration idempotent (can run multiple times)
- [ ] funding_rate NULL warnings prominent in docs

### Secondary Metrics

- [ ] Type checking passes (mypy + pyright)
- [ ] Coverage ≥85% for new code (SDK quality standards)
- [ ] Documentation complete with examples
- [ ] v3.2.0 released to GitHub and PyPI
- [ ] Clean installation from PyPI works

### SLO Impact

- **Availability**: Improved (713 futures symbols available, timestamp precision prevents data loss)
- **Correctness**: Enhanced (timestamp precision fix, comprehensive testing)
- **Observability**: Improved (instrument_type tracking, format detection logging)
- **Maintainability**: Minimal increase (URL routing only, no code duplication)

---

## Rollback Strategy

### Indicators for Rollback

- Backward compatibility broken (existing spot code fails)
- Timestamp precision causing data corruption
- Futures data corruption (incorrect CSV parsing)
- ClickHouse schema migration failure
- Dependency conflicts (binance-futures-availability issues)
- > 5% test failures in production

### Rollback Procedure

**Step 1: Revert Git Commit**

```bash
# Identify commit hash
git log --oneline -5

# Revert to v3.1.1
git revert <v3.2.0-commit-hash>
git push origin main
```

**Step 2: Users Downgrade**

```bash
# Users can downgrade to v3.1.1
pip install gapless-crypto-clickhouse==3.1.1
```

**Step 3: Schema Rollback (if needed)**

```sql
-- Revert timestamp precision (CAUTION: data loss if microsecond data exists)
ALTER TABLE ohlcv MODIFY COLUMN timestamp DateTime64(3);

-- Remove funding_rate column
ALTER TABLE ohlcv DROP COLUMN funding_rate;
```

**Step 4: Communicate**

- GitHub issue explaining rollback reason
- Update README with temporary notice
- Notify Alpha Forge of temporary revert
- Plan fixes for next attempt

---

## References

### Audit Artifacts

Location: `/tmp/um-futures-audit/`

1. **TECHNICAL_AUDIT_REPORT.md** - All 9 technical issues with evidence
2. **CRITICAL_FIXES_REQUIRED.md** - Step-by-step timestamp precision fix
3. **architecture-audit-findings.md** - 8.5/10 rating with improvements
4. **timeline-feasibility-audit.md** - 23-hour breakdown with risks
5. **documentation_audit_findings.md** - 7 UX issues and fixes
6. **improved_examples.md** - Ready-to-use documentation improvements

### External Resources

- **Binance Vision API**: https://data.binance.vision
- **Binance Futures API**: https://fapi.binance.com/fapi/v1/klines
- **binance-futures-availability**: /Users/terryli/eon/binance-futures-availability
- **data-source-manager (DSM)**: /Users/terryli/eon/data-source-manager (pattern reference)

### Related ADRs & Plans

- **ADR-0004**: Superseded QuestDB futures implementation
- **ADR-0020**: Multi-Symbol Batch API (concurrent download foundation)
- **ADR-0021**: This implementation (UM Futures Support)
- **Plan-0020**: Multi-Symbol Batch API implementation (completed)

---

## Log Files

Implementation logs will be stored in:

```
logs/0021-um-futures-support-YYYYMMDD_HHMMSS.log
```

Format: nohup output from long-running tasks (if any)

---

**Plan 0021** | UM Futures Support | In Progress | 2025-11-19
