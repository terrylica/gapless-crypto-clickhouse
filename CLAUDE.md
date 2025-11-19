# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gapless Crypto ClickHouse is a ClickHouse-based cryptocurrency data collection tool providing authentic Binance data with zero-gap guarantee. 22x faster than API-only approaches via Binance Public Data Repository (CloudFront CDN).

**Core Capability**: Collect complete historical OHLCV data with microstructure metrics (11-column format) for 13 timeframes (1s to 1d) across 400+ trading pairs.

## Quick Navigation

### Architecture

- [Architecture Overview](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/OVERVIEW.md) - Core components, data flow, SLOs
- [Data Format Specification](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/DATA_FORMAT.md) - 11-column microstructure format

### Usage Guides

- [Data Collection Guide](/Users/terryli/eon/gapless-crypto-clickhouse/docs/guides/DATA_COLLECTION.md) - CLI usage, dual data source strategy, troubleshooting
- [Python API Reference](/Users/terryli/eon/gapless-crypto-clickhouse/docs/guides/python-api.md) - Function-based and class-based APIs, complete examples

### Validation System

- [Validation Overview](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/OVERVIEW.md) - 5-layer validation pipeline, DuckDB persistence
- [ValidationStorage Specification](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/STORAGE.md) - Database schema, API methods
- [AI Agent Query Patterns](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/QUERY_PATTERNS.md) - Common patterns for validation analysis
- [E2E Testing Guide](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/E2E_TESTING_GUIDE.md) - Playwright E2E validation, screenshot evidence, debugging
- [Screenshot Baseline Management](/Users/terryli/eon/gapless-crypto-clickhouse/docs/validation/SCREENSHOT_BASELINE.md) - Visual regression detection workflow

### Development

- [Development Setup](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/SETUP.md) - Environment setup, IDE configuration, troubleshooting
- [Development Commands](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/COMMANDS.md) - Testing, code quality, build, CI/CD
- [CLI Migration Guide](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/CLI_MIGRATION_GUIDE.md) - Migrating from gapless-crypto-data to gapless-crypto-clickhouse
- [Publishing Guide](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/PUBLISHING.md) - PyPI publishing workflow

### Validated Workflows

**Multi-Agent Methodologies** - Extracted from production use (ClickHouse migration):

- [`multi-agent-e2e-validation`](/Users/terryli/.claude/skills/multi-agent-e2e-validation/SKILL.md) - Parallel E2E validation workflow for database refactors (3-layer model: environment → data flow → query interface). Discovered 5 critical bugs (100% failure rate) before release.
- [`multi-agent-performance-profiling`](/Users/terryli/.claude/skills/multi-agent-performance-profiling/SKILL.md) - 5-agent parallel profiling workflow for bottleneck identification. Proved ClickHouse ingests at 1.1M rows/sec (11x faster than target), revealing download as true bottleneck (90% of time).

**When to use**: Database migrations, pipeline refactors, performance investigations, pre-release validation

**Key principle**: Spawn multiple investigation agents in parallel using single message with multiple Task calls → integrate findings → prioritize fixes by severity/impact

## SDK Quality Standards

**Primary Use Case**: Programmatic API consumption (`import gapless_crypto_clickhouse`) by downstream packages and AI coding agents

**Specification**: [`docs/sdk-quality-standards.yaml`](/Users/terryli/eon/gapless-crypto-clickhouse/docs/sdk-quality-standards.yaml) - Machine-readable standards

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
- USDT-margined futures support (400+ symbols)
- High-performance bulk loading (1.1M rows/sec validated)
