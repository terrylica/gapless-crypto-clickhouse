# ADR-0035: CI/CD Production Validation Policy

**Status**: Superseded by ADR-0038
**Date**: 2025-01-22
**Deciders**: Engineering Team
**Related**: ADR-0027 (Local-Only PyPI Publishing), ADR-0038 (Real Binance Data Validation)

> **Note (2025-11-25)**: This ADR's synthetic validation approach has been superseded by ADR-0038's real Binance data validation. The policy principles (local-first development + production validation exception) remain valid, but the implementation details (synthetic test data, separate validation scripts) are replaced by the 9-stage real data pipeline.

## Context and Problem Statement

The workspace-wide policy prohibits unit testing and linting in GitHub Actions (local-first development philosophy). However, production infrastructure validation requires:

1. **ClickHouse Cloud AWS connectivity**: Cannot be tested locally (requires production credentials via Doppler)
2. **Schema deployment validation**: Must verify deployed schema matches `schema.sql` (ORDER BY optimization from ADR-0034)
3. **External service health monitoring**: Binance CDN availability affects data collection (22x performance advantage)
4. **Scheduled monitoring**: Independent of code changes, detects infrastructure degradation

**Core Tension**: Local-first development vs production infrastructure validation requirements.

## Decision Drivers

1. **Production readiness**: ClickHouse Cloud (v25.8.1.8702) requires deployment validation
2. **Zero-gap guarantee**: Binance CDN outages block data collection (must detect within hours)
3. **Schema correctness**: ADR-0034 ORDER BY optimization must be verified in production
4. **Deduplication integrity**: ReplacingMergeTree + deterministic versioning requires round-trip testing
5. **Local-first philosophy**: Preserve fast feedback loops for development (5-30s vs 2-5min CI/CD)

## Considered Options

### Option 1: Strict Local-Only (No CI/CD Validation)

**Approach**: Remove ALL GitHub Actions workflows except semantic-release. Developers manually validate production before releases.

**Pros**:

- Consistent with workspace policy
- Zero CI/CD costs
- Maximum developer autonomy

**Cons**:

- ClickHouse Cloud schema drift undetected (manual checks only)
- Binance CDN outages discovered reactively (user reports)
- No scheduled health monitoring
- Deployment validation burden on developers

### Option 2: Full CI/CD Testing (Reverse Policy)

**Approach**: Keep existing `.github/workflows/ci.yml` with unit tests, linting, integration tests.

**Pros**:

- Comprehensive automated validation
- Catches regressions before merge
- Industry standard practice

**Cons**:

- Violates workspace policy
- Slow feedback (2-5min vs 30s local)
- Developers wait for CI before iterating

### Option 3: Hybrid - Production Validation Exception (SELECTED)

**Approach**:

- **Remove** from CI/CD: Unit tests, linting, formatting, local integration tests
- **Add** to CI/CD: Production validation (ClickHouse Cloud, Binance CDN, scheduled health checks)
- **Keep** local: Development testing (pytest, ruff, mypy)

**Pros**:

- Preserves local-first development (fast iteration)
- Validates production infrastructure (unavailable locally)
- Scheduled monitoring (independent of code changes)
- Aligns with ADR-0027 philosophy (local development, CI/CD for production)

**Cons**:

- Policy complexity (exception requires documentation)
- Developers must discipline (run tests locally before commit)

## Decision Outcome

**Chosen**: Option 3 (Hybrid - Production Validation Exception)

**Rationale**: Production infrastructure validation is fundamentally different from code quality validation:

| Validation Type              | Location  | Rationale                                        |
| ---------------------------- | --------- | ------------------------------------------------ |
| Unit tests                   | Local     | Fast feedback, no external dependencies          |
| Linting/formatting           | Local     | Instant feedback, no infrastructure needed       |
| **ClickHouse Cloud schema**  | **CI/CD** | Requires Doppler credentials + production access |
| **Binance CDN availability** | **CI/CD** | External service, scheduled monitoring needed    |
| **Write/read round-trip**    | **CI/CD** | Validates production ReplacingMergeTree behavior |

### Policy Update

**Updated Workspace Policy**:

```bash
Local-First Development (Preserved):
- ❌ NO unit testing in GitHub Actions
- ❌ NO linting/formatting in CI/CD
- ✅ Developers validate locally before commit (5-30s feedback)

Production Validation Exception (NEW):
- ✅ ClickHouse Cloud schema validation in CI/CD
- ✅ External service health checks (Binance CDN)
- ✅ Scheduled monitoring (every 6 hours, independent of code changes)
- ✅ Write/read round-trip correctness (production deduplication)

Rationale: Production environments require credentials and infrastructure
unavailable in local development. Scheduled monitoring detects external
service degradation independent of code changes.
```

## Implementation

### Workflow Changes

**Delete**: `.github/workflows/ci.yml`

- Removes: test-fast (pytest, ruff), test-e2e (Docker integration), benchmark

**Create**: `.github/workflows/production-validation.yml`

- Trigger: Scheduled cron every 6 hours (`0 */6 * * *`)
- Jobs:
  1. **clickhouse-cloud-validation**: Schema validation + write/read round-trip
  2. **binance-cdn-availability**: HTTP HEAD request to CloudFront CDN
  3. **simplified-e2e-validation**: 3-layer checks (environment → data flow → query)

**Keep**: `.github/workflows/release.yml`

- No changes (already compliant: semantic-release only)

### Validation Scripts

**`scripts/validate_clickhouse_cloud.py`** (PEP 723 self-contained):

- Schema validation: `deploy-clickhouse-schema.py --dry-run`
- ORDER BY verification: `(symbol, timeframe, toStartOfHour(timestamp), timestamp)`
- Write/read round-trip: Insert 100 BTCUSDT 1h bars → query with FINAL → verify deduplication
- Cleanup: Remove test data after validation

**`scripts/validate_binance_cdn.py`** (PEP 723 self-contained):

- HTTP HEAD request to Binance Public Data Repository (CloudFront)
- 5s timeout
- Exit code 0 (success) / 1 (failure)

### Developer Workflow

**Before commit** (local-first validation):

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -v --cov=src
```text

**Before push** (integration tests against Homebrew ClickHouse):

```bash
uv run pytest -m integration
```text

**Manual production validation** (if needed):

```bash
doppler run --project aws-credentials --config prd -- uv run scripts/validate_clickhouse_cloud.py
```

## Consequences

### Positive

1. **Fast local development**: Preserved 5-30s feedback loops (vs 2-5min CI/CD)
2. **Production monitoring**: ClickHouse Cloud + Binance CDN health checks every 6 hours
3. **Schema drift detection**: ORDER BY optimization (ADR-0034) verified in production
4. **Deduplication validation**: ReplacingMergeTree correctness tested via round-trip
5. **Policy alignment**: Extends ADR-0027 philosophy (local development, CI/CD for production)

### Negative

1. **Developer discipline required**: No automated checks prevent broken code from merging
2. **Policy complexity**: Exception requires documentation and team communication
3. **CI/CD costs**: Scheduled monitoring consumes GitHub Actions minutes (minimal: ~4 runs/day)

### Neutral

1. **Pre-commit hooks** (optional): Can enforce local validation before commit
2. **Team size**: Policy works best for small teams (3-10 developers) with strong discipline

## Validation Criteria

**Acceptance Criteria**:

- [x] Production validation workflow runs every 6 hours without manual intervention
- [x] ClickHouse Cloud schema drift detected within 6 hours (16s validation)
- [x] Binance CDN outages detected within 6 hours (12s validation)
- [x] Write/read round-trip validates deduplication correctness (100 rows in/out)
- [x] `.github/workflows/ci.yml` deleted (no unit tests/linting)
- [x] Documentation updated (CLAUDE.md + global workspace CLAUDE.md)

**Rollback Criteria**:

- If developer discipline fails (>3 broken commits/week), revert to Option 2 (full CI/CD testing)
- If production validation unreliable (>10% false positives), redesign validation scripts

## References

- ADR-0027: Local-Only PyPI Publishing (workspace-wide policy foundation)
- ADR-0034: Schema Optimization for Prop Trading (ORDER BY validation requirement)
- ADR-0005: ClickHouse Migration (ReplacingMergeTree deduplication design)
- Global workspace `~/.claude/CLAUDE.md`: GitHub Actions policy
- ClickHouse Cloud deployment: `scripts/deploy-clickhouse-schema.py`

---

## Implementation Status

**Date**: 2025-01-24
**Status**: ✅ **COMPLETE - ALL VALIDATIONS PASSING**

**Final Test Results** (Run 19621000233 - 2025-01-24 01:56 UTC):

1. ✅ **ClickHouse Cloud Validation** - PASSED (16s)
   - Schema validation: SharedReplacingMergeTree with shard/replica parameters
   - Write/read round-trip: 100 rows inserted, 100 rows retrieved
   - Deduplication: Verified correctness with duplicate insert test
   - Cleanup: All test data removed successfully

2. ✅ **Binance CDN Availability** - PASSED (12s)
   - Both CloudFront endpoints responding: 200 OK
   - 22x performance advantage confirmed available
   - 5s timeout handling working correctly

3. ✅ **Simplified E2E Validation** - PASSED (17s)
   - Layer 1: Environment validated (ClickHouse Cloud connection)
   - Layer 2: Data flow validated (pandas DataFrame insert)
   - Layer 3: Query validated (FINAL deduplication working)

**Bugs Fixed During Implementation**:

1. ClickHouse Cloud engine format (flexible validation for shard/replica parameters)
2. Insert data format (`client.insert_df()` with pandas DataFrame)
3. Test data integrity (unique timestamps with `timedelta(hours=i)`)
4. Error logging (traceback for debugging)
5. Dead code cleanup (removed unused log file creation)

**Scheduled Monitoring**: Workflow runs every 6 hours (cron: `0 */6 * * *`)

**Next Workflow Run**: Automatic (no manual intervention required)
