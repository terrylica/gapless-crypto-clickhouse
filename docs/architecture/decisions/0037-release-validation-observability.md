# ADR-0037: Release Validation Observability Flow

**Status**: Proposed

**Date**: 2025-11-24

**Context**: [Plan 0037](../../development/plan/0037-release-validation-observability/plan.md)

## Context and Problem Statement

After semantic-release creates GitHub releases, we need observability to verify:

1. GitHub Release was created successfully
2. PyPI package version matches release tag
3. Production environment (ClickHouse Cloud) remains healthy

Current gap: No automated validation runs post-release. Manual verification required, increasing MTTR for release failures.

**SLO Impact**: Affects observability (blind spot in release pipeline) and availability (undetected failures delay incident response).

## Decision Drivers

- **Non-blocking validation**: Release success must not depend on validation outcome
- **Observability-first**: Structured metrics storage for trend analysis and alerting
- **Cloud-first architecture**: Validation metadata accessible team-wide (not local-only like CSV validation)
- **Reuse existing patterns**: Leverage production-validation scripts, Doppler credentials, Pushover notifications
- **Idiomatic ClickHouse**: Follow system table patterns (MergeTree, time-series partitioning)

## Considered Options

1. **Extend ValidationStorage (DuckDB)** - Consistent with CSV validation but local-only
2. **ClickHouse monitoring database** - Cloud-accessible, team-wide, idiomatic patterns
3. **GitHub Actions artifacts only** - Simplest but limited queryability (90-day retention)

## Decision Outcome

**Chosen option**: ClickHouse monitoring database with Earthly validation pipeline.

**Rationale**:

- **ClickHouse** chosen over DuckDB extension for cloud accessibility (OHLCV data already in cloud, validation metadata should follow)
- **MergeTree engine** chosen over ReplacingMergeTree (validation records immutable, no deduplication needed, avoids FINAL overhead)
- **Earthly** chosen for encapsulating validation logic (local testability, reproducible builds)
- **Doppler secrets** chosen for credential management (existing pattern, supports RUN --secret in Earthly)

### Consequences

**Good**:

- Team-accessible validation history (ClickHouse Cloud)
- Queryable metrics for trend analysis (SQL interface)
- Non-blocking workflow (release succeeds even if validation fails)
- Reuses existing infrastructure (ClickHouse Cloud, Doppler, Pushover)

**Bad**:

- Dual database architecture (CSV validation→DuckDB, release validation→ClickHouse)
- Additional operational complexity (monitoring schema deployment)
- ClickHouse write dependency in CI/CD

**Neutral**:

- Validation metadata small (<1KB/release, ~50 releases/year = 50KB/year)

## Validation

### Correctness

- [ ] ClickHouse `monitoring.validation_results` table stores all validation runs
- [ ] Pushover alerts received on mobile for both success and failure
- [ ] Non-blocking verified: release succeeds even when validation fails

### Observability

- [ ] Query validation history: `SELECT * FROM monitoring.validation_results WHERE release_version = 'v9.1.0'`
- [ ] GitHub Actions artifacts uploaded (validation JSON reports)
- [ ] Pushover alert includes release URL + validation status

### Maintainability

- [ ] Earthly local testing: `earthly +release-validation-pipeline`
- [ ] Schema migrations documented in deploy-monitoring-schema.py
- [ ] ADR ↔ plan ↔ code in sync

## Links

- [Plan 0037](../../development/plan/0037-release-validation-observability/plan.md) - Implementation plan
- [ADR-0035](0035-cicd-production-validation.md) - CI/CD production validation policy (scheduled monitoring)
- [ADR-0036](0036-cicd-dry-refactoring.md) - CI/CD workflow DRY refactoring (shared e2e_core module)
- [Agent 5 Investigation](/tmp/release-validation-test/DCTL-JOURNEY-REPORT.md) - GitHub Release validation research
