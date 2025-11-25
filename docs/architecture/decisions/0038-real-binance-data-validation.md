# ADR-0038: Real Binance Data Validation

**Status**: Accepted

**Date**: 2025-11-25

**Context**: [Plan 0038](../../development/plan/0038-real-binance-data-validation/plan.md)

## Context and Problem Statement

Existing validation scripts (`validate_clickhouse_cloud.py`, `validate_e2e_simple.py`) use synthetic data with fake symbols (`VALIDATION_TEST_BTCUSDT`, `E2E_TEST`). This creates a blind spot where:

1. Real Binance CDN data format changes go undetected
2. Schema transformations (11-column CSV → 18-column ClickHouse) are untested with production data
3. Deduplication correctness relies on fabricated version hashes

**Requirement**: Validate the complete data pipeline using real Binance Vision data as the source of truth.

## Decision Drivers

- **Correctness**: Real data validates actual CDN format, not assumptions
- **Observability**: Earthly-based pipeline produces structured JSON artifacts
- **Maintainability**: Single consolidated script replaces two legacy scripts
- **Availability**: Non-blocking validation (exit 0 on failure)

## Considered Options

1. **Enhance synthetic validation** - Add more fake data scenarios
2. **Real data validation (selected)** - Download actual Binance CDN data
3. **Mock-based testing** - Mock CDN responses locally

## Decision Outcome

**Chosen option**: Real Binance data validation with Earthly integration.

**Rationale**:

- Real data from `data.binance.vision` is deterministic (historical data doesn't change)
- 2024-01-01 BTCUSDT provides stable test fixture (24 bars × 2 formats)
- Earthly encapsulation enables local testing and CI/CD reproducibility
- Data stays permanently in ClickHouse (no cleanup) - validates idempotent ingestion

### Implementation

**New Script**: `scripts/validate_binance_real_data.py`

**Test Data**:
| Format | URL | Rows |
|--------|-----|------|
| Futures | `data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-01.zip` | 24 |
| Spot | `data.binance.vision/data/spot/daily/klines/BTCUSDT/1h/BTCUSDT-1h-2024-01-01.zip` | 24 |

**9-Stage Pipeline**:
1. CDN Download (HTTP 200, ZIP > 0 bytes)
2. ZIP Extract (single CSV per archive)
3. CSV Parse + Format Detection (futures: 12-col header, spot: 11-col no header)
4. DataFrame Validation (OHLC constraints, volume constraints)
5. _version Hash Computation (SHA256 deterministic)
6. ClickHouse Insert (48 total rows: 24 futures + 24 spot)
7. Query FINAL (verify 24 rows per instrument_type)
8. Deduplication Test (re-insert produces 24, not 48)
9. Schema Compliance (18 columns, symbol-first ORDER BY)

**Deleted Scripts**:
- `scripts/validate_clickhouse_cloud.py` (synthetic `VALIDATION_TEST_BTCUSDT`)
- `scripts/validate_e2e_simple.py` (synthetic `E2E_TEST`)

### Consequences

**Good**:
- Real data validates actual CDN format and transformation logic
- Consolidated script reduces maintenance burden
- Earthly integration enables reproducible CI/CD
- Permanent data validates idempotent ingestion pattern

**Bad**:
- Network dependency (CDN must be reachable)
- Real BTCUSDT data mixed with test data (distinguished by timestamp: 2024-01-01)

**Neutral**:
- 48 rows of historical data permanent in production ClickHouse (~2KB)

## Validation

### Correctness
- [ ] 9-stage pipeline passes locally
- [ ] Futures format (12-col header) correctly parsed
- [ ] Spot format (11-col no header) correctly parsed
- [ ] Deduplication verified (re-insert doesn't double count)

### Observability
- [ ] JSON artifact exported: `binance-validation-result.json`
- [ ] Structured validation context (row counts, timestamps, hashes)
- [ ] Earthly target integrates with release-validation workflow

### Maintainability
- [ ] Legacy scripts deleted
- [ ] Single validation script covers both formats
- [ ] ADR ↔ plan ↔ code in sync

## Links

- [Plan 0038](../../development/plan/0038-real-binance-data-validation/plan.md)
- [ADR-0035](0035-cicd-production-validation.md) - CI/CD production validation policy
- [ADR-0037](0037-release-validation-observability.md) - Release validation observability flow
