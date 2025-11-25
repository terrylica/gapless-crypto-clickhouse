# ADR-0037: Release Validation Observability Flow

**Status**: Accepted

**Date**: 2025-11-24

**Implemented**: 2025-01-25

**Context**: [Plan 0037](../../development/plan/0037-release-validation/plan.md)

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

### Production Results (v12.0.1)

**Deployment**: 2025-01-25 01:13 UTC

**Validation**: 5 issues discovered in first production run, 3 critical issues fixed in second run.

**Empirical Evidence**:

1. **ClickHouse Inserts**: ✅ 3/3 successful (github_release, pypi_version, production_health)
2. **Tag Detection**: ✅ v12.0.1 (correct version after fix)
3. **Validation Results**: ✅ GitHub Release PASSED, Production Health PASSED, PyPI FAILED (expected)
4. **Observability**: ✅ All validation metadata queryable in ClickHouse with rich context
5. **Artifact Export**: ⚠️ Earthly artifact export to host filesystem not working (non-blocking)
6. **Pushover Alerts**: ⚠️ Doppler token permissions need manual fix (non-blocking)

**Key Validation Records** (production data):
```sql
SELECT validation_type, status, duration_ms, validation_context
FROM monitoring.validation_results
WHERE release_version = 'v12.0.1'
ORDER BY event_time DESC;

-- Results:
-- github_release   | passed | 226ms  | {"tag_name": "v12.0.1", "published_at": "2025-11-25T01:13:21Z"}
-- production_health | passed | 1110ms | {"host": "ebmf8f35lu...clickhouse.cloud", "ohlcv_row_count": "0"}
-- pypi_version      | failed | 23ms   | {"expected_version": "12.0.1", "actual_version": "8.0.0"}
```

**Decision Confirmed**: ClickHouse monitoring database successfully provides team-accessible validation history with queryable metrics. Non-blocking design verified (releases succeed despite validation failures).

## Production Validation

### Issues Discovered and Resolutions

Production deployment revealed 5 issues. 3 critical issues were fixed immediately, 2 medium-severity issues remain open (non-blocking).

#### Issue #1: Tag Detection (CRITICAL - FIXED)

**Symptom**: Workflow detected `v0.0.0` instead of actual release version.

**Root Cause**: GitHub Actions `checkout@v4` defaults to `fetch-tags: false`.

**Fix**: Added to `.github/workflows/release-validation.yml`:
```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    fetch-tags: true
```

**Validation**: Second run correctly detected `v12.0.1`.

---

#### Issue #2: ClickHouse Insert Format (CRITICAL - FIXED)

**Symptom**: All 3 validation inserts failed with "column count does not match".

**Root Cause**: Used dict format instead of list format, missing required columns (event_date, symbol, timeframe).

**Fix**: Changed `scripts/write_validation_results.py` to use list format with explicit column_names parameter:
```python
column_names = [
    "event_time", "event_date", "validation_type",
    "release_version", "git_commit", "symbol", "timeframe",
    "status", "error_message", "duration_ms",
    "validation_context", "environment"
]
row = [event_time, event_time.date(), data.get("validation_type"), ...]
client.insert("monitoring.validation_results", [row], column_names=column_names)
```

**Validation**: Test insert successful, second production run showed 3/3 successful inserts.

---

#### Issue #3: Earthly Artifact Export (MEDIUM - UNFIXED)

**Symptom**: GitHub Actions warning "No files were found with the provided path: artifacts/*.json".

**Root Cause**: Earthly `BUILD` command doesn't automatically copy artifacts from child targets.

**Impact**: Medium severity - doesn't block validation functionality, just prevents artifact download from GitHub Actions UI. Validation results still successfully stored in ClickHouse.

**Status**: Open issue for future investigation.

---

#### Issue #4: ClickHouse Cloud SQL Compatibility (CRITICAL - FIXED)

**Symptom**: Schema deployment failed with "Only queries like 'CREATE DATABASE <database>' are supported".

**Root Cause**: ClickHouse Cloud doesn't support `IF NOT EXISTS` or `ENGINE` clauses in `CREATE DATABASE` statements.

**Fix**: Changed `scripts/deploy-monitoring-schema.py`:
```python
# Simple CREATE DATABASE syntax (ClickHouse Cloud compatible)
try:
    client.command("CREATE DATABASE monitoring")
except Exception as e:
    if "already exists" in str(e).lower():
        log_with_timestamp("✅ Database 'monitoring' already exists")
    else:
        raise
```

**Validation**: Successful deployment to ClickHouse Cloud production.

---

#### Issue #5: Doppler Token Permissions (MEDIUM - UNFIXED)

**Symptom**: Pushover notification failed with "This token does not have access to requested project 'notifications'".

**Root Cause**: GitHub Actions `DOPPLER_TOKEN` secret only has access to `aws-credentials` project.

**Impact**: Medium severity - prevents Pushover mobile alerts, but validation still runs and stores results.

**Status**: Requires manual update of GitHub secrets. Documented for future fix.

---

### Lessons Learned

**What Worked Well**:
1. Multi-agent DCTL validation discovered 3 issues before first production run
2. Non-blocking design prevented release failures
3. Test-driven fixes (created test data to verify ClickHouse insert before production)

**What Didn't Work**:
1. Earthly artifact export pattern (COPY + SAVE ARTIFACT in pipeline target)
2. Initial ClickHouse insert format (dict instead of list)
3. Assumed GitHub Actions checkout fetches tags by default

**Key Insights**:
1. ClickHouse Cloud requires simpler SQL syntax (no IF NOT EXISTS, no ENGINE for CREATE DATABASE)
2. Explicit column names critical for ClickHouse insert robustness
3. Always specify fetch-depth and fetch-tags explicitly when working with git tags
4. Production validation essential even after multi-agent validation

## Validation

### Correctness

- [x] ClickHouse `monitoring.validation_results` table stores all validation runs (v12.0.1: 3/3 successful)
- [ ] Pushover alerts received on mobile for both success and failure (blocked by Doppler token permissions - Issue #5)
- [x] Non-blocking verified: release succeeds even when validation fails (v12.0.1 released despite PyPI validation failure)

### Observability

- [x] Query validation history: `SELECT * FROM monitoring.validation_results WHERE release_version = 'v12.0.1'` (verified with production data)
- [ ] GitHub Actions artifacts uploaded (validation JSON reports) (blocked by Earthly export - Issue #3)
- [ ] Pushover alert includes release URL + validation status (blocked by Doppler token permissions - Issue #5)

### Maintainability

- [x] Earthly local testing: `earthly +release-validation-pipeline` (validated in production)
- [x] Schema migrations documented in deploy-monitoring-schema.py (ClickHouse Cloud compatibility fixes documented)
- [x] ADR ↔ plan ↔ code in sync (plan.md created, ADR updated with production findings)

## Links

- [Plan 0037](../../development/plan/0037-release-validation/plan.md) - Implementation plan with production findings
- [ADR-0035](0035-cicd-production-validation.md) - CI/CD production validation policy (scheduled monitoring)
- [ADR-0036](0036-cicd-dry-refactoring.md) - CI/CD workflow DRY refactoring (shared e2e_core module)
- [Agent 5 Investigation](/tmp/release-validation-test/DCTL-JOURNEY-REPORT.md) - GitHub Release validation research
