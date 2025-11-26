# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gapless Crypto ClickHouse is a ClickHouse-based cryptocurrency data collection tool providing authentic Binance data with zero-gap guarantee. 22x faster than API-only approaches via Binance Public Data Repository (CloudFront CDN).

**Core Capability**: Collect complete historical OHLCV data with microstructure metrics (11-column format) for 16 timeframes (13 standard: 1s-1d + 3 exotic: 3d, 1w, 1mo) across 713 trading pairs.

## Quick Navigation

### Architecture

- [Architecture Overview](docs/architecture/OVERVIEW.md) - Core components, data flow, SLOs
- [Data Format Specification](docs/architecture/DATA_FORMAT.md) - 11-column microstructure format

### Usage Guides

- [Data Collection Guide](docs/guides/DATA_COLLECTION.md) - CLI usage, dual data source strategy, troubleshooting
- [Python API Reference](docs/guides/python-api.md) - Function-based and class-based APIs, complete examples

### Validation System

- [Validation Architecture](docs/validation/ARCHITECTURE.md) - Three-layer model (CSV/ClickHouse/Performance), v6.0.0 compatibility
- [Validation Overview](docs/validation/OVERVIEW.md) - 5-layer validation pipeline, DuckDB persistence
- [ValidationStorage Specification](docs/validation/STORAGE.md) - Database schema, API methods
- [AI Agent Query Patterns](docs/validation/QUERY_PATTERNS.md) - Common patterns for validation analysis
- [E2E Testing Guide](docs/validation/E2E_TESTING_GUIDE.md) - Playwright E2E validation, screenshot evidence, debugging
- [Screenshot Baseline Management](docs/validation/SCREENSHOT_BASELINE.md) - Visual regression detection workflow

### Development

- [Development Setup](docs/development/SETUP.md) - Environment setup, IDE configuration, troubleshooting
- [Development Commands](docs/development/COMMANDS.md) - Testing, code quality, build, CI/CD
- [CLI Migration Guide](docs/development/CLI_MIGRATION_GUIDE.md) - Migrating from gapless-crypto-data to gapless-crypto-clickhouse
- [Publishing Guide](docs/development/PUBLISHING.md) - PyPI publishing workflow
- [`semantic-release`](~/.claude/skills/semantic-release/SKILL.md) - Automated versioning with Node.js semantic-release v25+, PyPI publishing with Doppler

## PyPI Publishing Architecture

**WORKSPACE-WIDE POLICY** (ADR-0027): All repositories enforce **local-only PyPI publishing**, never through CI/CD.

**GitHub Actions Role** (Versioning Only):

- ✅ Analyze conventional commits → determine version
- ✅ Update `pyproject.toml`, `package.json` versions
- ✅ Generate/update `CHANGELOG.md`
- ✅ Create git tag + GitHub release
- ✅ Commit version files back to repo `[skip ci]`
- ❌ **NO** package building (removed from `.releaserc.json`)
- ❌ **NO** PyPI publishing (publishCmd deleted entirely)

**Local Publishing** (via `pypi-doppler` skill):

- ✅ Pull latest release commit from GitHub
- ✅ Build package locally (`uv build`)
- ✅ Publish to PyPI (`uv publish` with Doppler credentials)
- ✅ CI detection guards (blocks if CI=true)
- ✅ Repository verification (prevents fork abuse)

**Rationale**:

- **Security**: No long-lived PyPI tokens in GitHub secrets
- **Speed**: 30s local vs 3-5min CI
- **Control**: Manual approval before production release
- **Flexibility**: Centralized credential management via Doppler

**Complete Workflow**: See [PUBLISHING.md](docs/development/PUBLISHING.md) for step-by-step guide, troubleshooting, and safety mechanisms.

### Validated Workflows

**Multi-Agent Methodologies** - Extracted from production use (ClickHouse migration):

- [`multi-agent-e2e-validation`](~/.claude/skills/multi-agent-e2e-validation/SKILL.md) - Parallel E2E validation workflow for database refactors (3-layer model: environment → data flow → query interface). Discovered 5 critical bugs (100% failure rate) before release.
- [`multi-agent-performance-profiling`](~/.claude/skills/multi-agent-performance-profiling/SKILL.md) - 5-agent parallel profiling workflow for bottleneck identification. Proved ClickHouse ingests at 1.1M rows/sec (11x faster than target), revealing download as true bottleneck (90% of time).

**When to use**: Database migrations, pipeline refactors, performance investigations, pre-release validation

**Key principle**: Spawn multiple investigation agents in parallel using single message with multiple Task calls → integrate findings → prioritize fixes by severity/impact

### ClickHouse Cloud Setup

**Production Infrastructure** - Credentials stored in Doppler (`aws-credentials/prd`) + 1Password (Engineering vault)

- [`clickhouse-cloud-service-setup`](skills/clickhouse-cloud-service-setup/SKILL.md) - Fetch service details from ClickHouse Cloud API (organization ID, service endpoints, configuration)
- [`clickhouse-cloud-credentials`](skills/clickhouse-cloud-credentials/SKILL.md) - Store API keys and connection details in Doppler + 1Password
- [`clickhouse-cloud-connection`](skills/clickhouse-cloud-connection/SKILL.md) - Test and validate ClickHouse Cloud connectivity

**When to use**: Setting up new ClickHouse Cloud services, rotating credentials, validating cloud connections

**Key principle**: Credentials proxied through Doppler/1Password, never hardcoded. Prescriptive workflows for repeatable cloud infrastructure setup.

### ClickHouse Schema Architecture

**Schema Version**: v2 (ADR-0034 optimized for prop trading, deployed 2025-01-22)

**Deployment Commands**:

```bash
# Deploy schema to ClickHouse Cloud
doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py

# Dry-run mode (preview SQL without executing)
doppler run --project aws-credentials --config prd -- python scripts/deploy-clickhouse-schema.py --dry-run
```

**ORDER BY Design (Symbol-First Indexing)**:

```sql
ORDER BY (symbol, timeframe, toStartOfHour(timestamp), timestamp)
```

**Rationale** (ADR-0034):

- **Symbol-first**: Trading queries filter by symbol first (e.g., "BTCUSDT") - 80% of query patterns
- **Timeframe-second**: Usually query one timeframe at a time (e.g., "1h")
- **Hour-bucketed timestamp**: Groups data by hour for efficient range scans
- **Full timestamp**: Deterministic ordering within each hour
- **Performance Impact**: 10-100x faster vs timestamp-first ORDER BY for symbol-specific queries

**FINAL Optimization (Client Configuration)**:

The `do_not_merge_across_partitions_select_final` setting reduces FINAL query overhead from 10-30% to 2-5%. Configure in client connections:

```python
# Example client configuration
settings = {
    "do_not_merge_across_partitions_select_final": 1,
}

client = clickhouse_connect.get_client(
    host=os.getenv("CLICKHOUSE_HOST"),
    port=int(os.getenv("CLICKHOUSE_PORT", "8443")),
    username=os.getenv("CLICKHOUSE_USER", "default"),
    password=os.getenv("CLICKHOUSE_PASSWORD"),
    secure=True,
    settings=settings,  # Apply optimization
)

# Query with FINAL (deduplicated results)
result = client.query("SELECT * FROM ohlcv FINAL WHERE symbol = 'BTCUSDT'")
```

**Reference**: [ADR-0034](docs/architecture/decisions/0034-schema-optimization-prop-trading.md) - Schema optimization for prop trading production readiness

### CI/CD Production Validation

**Policy** (ADR-0035, updated by ADR-0038, ADR-0039): Local-first development + production validation exception

**Local-First Development** (Developers run before commit):

```bash
# Code quality (local-only, NOT in CI/CD)
uv run ruff check .
uv run ruff format --check .

# Unit tests (local-only, NOT in CI/CD)
uv run pytest -v --cov=src

# Integration tests against Homebrew ClickHouse (local-only)
uv run pytest -m integration
```

**Production Validation** (GitHub Actions, scheduled every 6 hours):

**Workflow**: `.github/workflows/production-validation.yml`

- **Trigger**: Cron `0 */6 * * *` (00:00, 06:00, 12:00, 18:00 UTC)
- **Credentials**: Direct GitHub secrets (`CLICKHOUSE_HOST`, `CLICKHOUSE_PASSWORD`, etc.)

**Validation** (ADR-0038: Real Binance Data Validation):

Single-job Earthly-based 9-stage pipeline using real BTCUSDT data from Binance CDN:

1. CDN Download (HTTP GET, validates CDN availability)
2. ZIP Extract
3. CSV Parse + Format Detection (futures 12-col header, spot 12-col no header)
4. DataFrame Validation (OHLC, volume constraints)
5. \_version Hash Computation
6. ClickHouse Insert
7. Query FINAL
8. Deduplication Test
9. Schema Compliance (ORDER BY symbol-first from ADR-0034)

**Manual Production Validation**:

```bash
# Run real Binance data validation locally
doppler run --project aws-credentials --config prd -- uv run scripts/validate_binance_real_data.py
```

**Rationale**:

- Uses real Binance CDN data (not synthetic) for production-realistic validation
- Validates complete pipeline: CDN → CSV → DataFrame → ClickHouse → Query
- Scheduled monitoring detects infrastructure degradation independent of code changes

**Reference**: [ADR-0038](docs/architecture/decisions/0038-real-binance-data-validation.md) - Real Binance Data Validation

**CI/CD Architecture** (ADR-0036, updated by ADR-0039): 2-workflow system

**Active Workflows**:

1. **Release Workflow** (`.github/workflows/release.yml`):
   - Semantic versioning (analyze conventional commits)
   - Generate CHANGELOG.md
   - Create git tags + GitHub releases
   - **NO** package building or PyPI publishing (handled locally per ADR-0027)

2. **Production Validation Workflow** (`.github/workflows/production-validation.yml`):
   - Real Binance data validation via Earthly (9-stage pipeline)
   - Scheduled every 6 hours (cron: `0 */6 * * *`)

**Composite Actions**: Setup steps extracted to `.github/actions/`

- `setup-python-uv`: Python 3.12 + UV installation with dependency caching

**Reference**: [ADR-0039](docs/architecture/decisions/0039-validation-redundancy-cleanup.md) - Validation Redundancy Cleanup

### Release Validation Observability

**Non-Blocking Post-Release Validation** (ADR-0037): Automated verification flow triggered after semantic-release completion

**Validation Workflow** (`.github/workflows/release-validation.yml`):

- **Trigger**: Runs automatically after `release.yml` workflow completion (workflow_run event)
- **Behavior**: Non-blocking (`continue-on-error: true` at job + step level) - never fails releases
- **Scope**: 3-layer validation
  1. GitHub Release existence (exponential backoff retry: 5s → 10s → 20s)
  2. PyPI package version match (queries PyPI JSON API)
  3. Production environment health (ClickHouse Cloud connectivity + table verification)

**Storage Architecture**:

- **Database**: ClickHouse Cloud `monitoring` database
- **Table**: `validation_results` (SharedMergeTree with replication)
- **Schema**: event_time, validation_type, release_version, git_commit, status, error_message, duration_ms, validation_context, environment
- **ORDER BY**: (release_version, validation_type, event_time)
- **PARTITION BY**: toStartOfDay(event_date)
- **Retention**: Indefinite (all validation history preserved)

**Credentials** (via Doppler):

- **ClickHouse Cloud**: `aws-credentials/prd` (CLICKHOUSE_HOST, CLICKHOUSE_PASSWORD)
- **Pushover Alerts**: `notifications/prd` (PUSHOVER_APP_TOKEN, PUSHOVER_USER_KEY)

**Query Validation History**:

```bash
# Connect to ClickHouse Cloud
doppler run --project aws-credentials --config prd -- clickhouse-client

# Recent validation results
SELECT
    release_version,
    validation_type,
    status,
    error_message,
    duration_ms,
    event_time
FROM monitoring.validation_results
ORDER BY event_time DESC
LIMIT 10

# Validation summary by release
SELECT
    release_version,
    countIf(status = 'passed') AS passed,
    countIf(status = 'failed') AS failed,
    max(event_time) AS last_validation
FROM monitoring.validation_results
GROUP BY release_version
ORDER BY last_validation DESC
```

**Alerts**: Pushover notification sent with release version, validation status (✅/❌ per check), and GitHub Release link

**Rationale**:

- **Observability**: Centralized validation history accessible to entire team via ClickHouse Cloud
- **Non-blocking**: Validation failures never prevent releases (continue-on-error guarantees)
- **Early detection**: Identifies GitHub Release failures, PyPI version mismatches, production health issues within minutes
- **MTTR reduction**: Automated alerts eliminate manual verification, accelerate incident response

**Reference**: [ADR-0037](docs/architecture/decisions/0037-release-validation-observability.md) - Release validation observability flow

### Company Employee Onboarding

**Claude Code CLI Optimized** - Step-by-step workflow for 3-10 company employees using ClickHouse Cloud

- [`gapless-crypto-clickhouse-onboarding`](skills/gapless-crypto-clickhouse-onboarding/SKILL.md) - Complete onboarding workflow (Doppler OR .env file, <15 minute setup, connection testing, troubleshooting guide)

**When to use**: Company employee first-time setup, credential configuration, connection errors, mentions "onboarding" or "how do I connect to ClickHouse Cloud"

**Key principle**: Binary access model (admins have full Cloud access, non-admins use file-based API only). Flexible credential methods (Doppler recommended, .env fallback). Claude Code CLI agents guide through complete onboarding workflow with diagnostic test scripts and actionable troubleshooting.

## SDK Quality Standards

**Primary Use Case**: Programmatic API consumption (`import gapless_crypto_clickhouse`) by downstream packages and AI coding agents

**Specification**: [`docs/sdk-quality-standards.yaml`](docs/sdk-quality-standards.yaml) - Machine-readable standards

**Key Abstractions**:

- **Type Safety**: PEP 561 compliance via py.typed marker
- **AI Discoverability**: **probe** module, llms.txt
- **Structured Exceptions**: Machine-parseable error context
- **Coverage Strategy**: SDK entry points (85%+) > Core engines (70%+)

## Network Architecture

**CRITICAL - Empirically Validated (2025-01-19)**: DO NOT modify network implementation without evidence

**Data Source**: AWS S3 + CloudFront CDN (400+ edge locations, 99.99% SLA)

**Download Strategy (Dual Approach)**:

- **Monthly/Daily files**: urllib (simple HTTP, 2x faster for single large files)
- **Concurrent downloads**: httpx with connection pooling (gap filling, multiple small requests)

**Connection Pooling**:

- Used for concurrent API requests (gap filling via Binance REST API)
- NOT used for CloudFront downloads (each request routed to different edge server)
- Configuration: `max_keepalive_connections=20, max_connections=30, keepalive_expiry=30.0`

**Retry Logic**: CloudFront handles failover automatically (0% failure rate in production)

**Optimization Opportunity**: ETag-based caching for bandwidth reduction

## Authentication

**No authentication required** for primary data collection (public Binance data repository). Gap filling uses public Binance API endpoints (rate-limited but no auth required).

## Current Architecture

**Version**: v1.0.0 (ClickHouse database with optional file-based workflows)

**Canonical Reference**: `docs/CURRENT_ARCHITECTURE_STATUS.yaml`

**Production-Ready Features**:

- Core data collection (CDN + REST API dual source)
- ClickHouse database integration (ReplacingMergeTree with deduplication)
- Idempotent ingestion with deterministic versioning
- USDT-margined futures support (715 symbols)
- High-performance bulk loading (1.1M rows/sec validated)
