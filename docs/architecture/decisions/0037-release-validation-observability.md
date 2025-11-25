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

### Production Results (v12.0.1 - v12.0.9)

**Timeline**:

| Version | Date                 | Status     | Key Result                                                   |
| ------- | -------------------- | ---------- | ------------------------------------------------------------ |
| v12.0.1 | 2025-01-25 01:13 UTC | ✅ Success | Core observability working, 3/3 ClickHouse inserts           |
| v12.0.2 | 2025-01-25 02:15 UTC | ⚠️ Partial | GitHub API rate limit blocked Earthly setup                  |
| v12.0.3 | 2025-01-25 02:45 UTC | ❌ Failed  | Earthly artifact export fix (COPY/BUILD pattern) didn't work |
| v12.0.4 | 2025-01-25 03:00 UTC | ❌ Failed  | Direct target calls failed (secret passing issue)            |
| v12.0.5 | 2025-01-25 03:17 UTC | ✅ Success | Secret passing fixed, 3/3 ClickHouse inserts                 |
| v12.0.6 | 2025-01-25 03:24 UTC | ⚠️ Blocked | Artifact export fix implemented, GitHub API rate limit       |
| v12.0.9 | 2025-01-25 08:17 UTC | ⏳ Pending | Issue #5 fix (Doppler multi-project → direct GitHub secrets) |

**v12.0.1 Empirical Evidence**:

1. **ClickHouse Inserts**: ✅ 3/3 successful (github_release, pypi_version, production_health)
2. **Tag Detection**: ✅ v12.0.1 (correct version after fix)
3. **Validation Results**: ✅ GitHub Release PASSED, Production Health PASSED, PyPI FAILED (expected)
4. **Observability**: ✅ All validation metadata queryable in ClickHouse with rich context
5. **Artifact Export**: ⚠️ Earthly artifact export to host filesystem not working (non-blocking)
6. **Pushover Alerts**: ⚠️ Doppler token permissions need manual fix (non-blocking)

**v12.0.5 Empirical Evidence**:

1. **ClickHouse Inserts**: ✅ 3/3 successful
2. **Secret Passing**: ✅ Fixed with GitHub Actions template syntax
3. **Validation Results**: ✅ GitHub Release PASSED (176ms), Production Health PASSED (36.8s), PyPI FAILED (expected)
4. **Artifact Export**: ❌ Still not working (root cause identified: EARTHLY_CI environment variable)

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

#### Issue #3: Earthly Artifact Export (MEDIUM - FIXED in v12.0.6)

**Symptom**: GitHub Actions warning "No files were found with the provided path: artifacts/\*.json".

**Root Cause Analysis** (v12.0.5 investigation):

1. Initial hypothesis: Earthly `BUILD` command doesn't automatically copy artifacts from child targets
2. Attempted fix (v12.0.3): Use `COPY` before `BUILD` in pipeline target - FAILED
3. Attempted fix (v12.0.4): Call individual targets directly from GitHub Actions - FAILED (secret passing issue)
4. **Actual root cause discovered**: `EARTHLY_CI=true` environment variable sets Earthly to `--ci` mode, equivalent to `--no-output --strict`, **silently disabling** `SAVE ARTIFACT AS LOCAL` exports
5. **Evidence**: Workflow logs showed "Local Output Summary 🎁 (disabled)" for all Earthly builds

**Fix Applied** (v12.0.6):

```yaml
# BEFORE (v12.0.5 and earlier):
env:
  EARTHLY_CI: true  # This disables all artifact export!

# AFTER (v12.0.6):
# Removed EARTHLY_CI, added --strict flag explicitly to each command
earthly --strict \
  --secret GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}" \
  +github-release-check
```

**Impact**: Medium severity - doesn't block validation functionality, just prevents artifact download from GitHub Actions UI.

**Status**: ✅ FIXED and VALIDATED in v12.0.8

**Validation Evidence** (v12.0.8):

- Workflow logs: "Local Output Summary 🎁" (no longer "(disabled)")
- 3 files uploaded: `github-release-result.json`, `pypi-version-result.json`, `production-health-result.json`
- Artifact ID: 4670097842 (1200 bytes, downloadable for 90 days)

**References**:

- [Earthly Issue #4297](https://github.com/earthly/earthly/issues/4297)
- [Stack Overflow - Earthly + GitLab CI](https://stackoverflow.com/questions/78048916/how-to-save-an-artifact-locally-using-earthly-and-gitlab-ci-cd)

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

#### Issue #4.1: Earthly Secret Passing (CRITICAL - FIXED in v12.0.5)

**Symptom**: v12.0.4 failed with "unable to lookup secret 'GITHUB_TOKEN': not found".

**Root Cause**: Bash variable substitution failing when multiple `earthly` commands execute sequentially in the same step.

**Analysis**:

```yaml
# BEFORE (v12.0.4 - FAILED):
export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"
earthly --secret GITHUB_TOKEN="$GITHUB_TOKEN" +github-release-check # $GITHUB_TOKEN was empty
```

When multiple `earthly` commands execute sequentially, bash variables don't reliably pass to `--secret` flags due to environment scope or quoting issues.

**Fix Applied** (v12.0.5):

1. Created separate "Fetch Doppler secrets" step storing secrets in GitHub Actions step outputs
2. Changed all secret passing from bash variables to GitHub Actions template syntax

```yaml
# AFTER (v12.0.5):
# Secrets fetched in prior step, stored in step outputs
earthly --strict \
  --secret GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}" \  # Direct template syntax
  --secret CLICKHOUSE_HOST="${{ steps.doppler_secrets.outputs.clickhouse_host }}" \
  +production-health-check
```

**Validation**: v12.0.5 validation ran successfully with 3/3 records stored in ClickHouse.

**Key Insight**: GitHub Actions template syntax (`${{ }}`) resolves before bash execution, avoiding variable scope/quoting issues entirely.

---

#### Issue #5: Doppler Token Permissions (MEDIUM - FIXED in v12.0.9)

**Symptom**: Pushover notification failed with "This token does not have access to requested project 'notifications'".

**Root Cause**: GitHub Actions `DOPPLER_TOKEN` secret only has access to `aws-credentials` project, but workflow needs secrets from both `aws-credentials` (ClickHouse) and `notifications` (Pushover) projects.

**Analysis**:

1. Doppler Service Tokens are project/config-scoped (cannot access multiple projects)
2. Doppler Service Accounts (multi-project access) require Team/Enterprise plan
3. Doppler GitHub App auto-sync requires Dashboard configuration

**Fix Applied** (v12.0.9):

1. Synced secrets directly from Doppler to GitHub using CLI:
   ```bash
   # ClickHouse secrets from aws-credentials/prd
   gh secret set CLICKHOUSE_HOST -R terrylica/gapless-crypto-clickhouse \
     --body "$(doppler secrets get CLICKHOUSE_HOST --project aws-credentials --config prd --plain)"
   # ... repeat for CLICKHOUSE_PORT, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD

   # Pushover secrets from notifications/prd
   gh secret set PUSHOVER_APP_TOKEN -R terrylica/gapless-crypto-clickhouse \
     --body "$(doppler secrets get PUSHOVER_APP_TOKEN --project notifications --config prd --plain)"
   # ... repeat for PUSHOVER_USER_KEY
   ```

2. Modified workflow to use direct `${{ secrets.* }}` references instead of runtime Doppler fetching:
   ```yaml
   # BEFORE (runtime Doppler fetch - FAILED):
   --secret CLICKHOUSE_HOST="${{ steps.doppler_secrets.outputs.clickhouse_host }}"

   # AFTER (direct GitHub secrets - WORKS):
   --secret CLICKHOUSE_HOST="${{ secrets.CLICKHOUSE_HOST }}"
   ```

3. Removed "Fetch Doppler secrets" step and "Setup Doppler CLI" action entirely

**Impact**: Workflow no longer depends on runtime `DOPPLER_TOKEN` authentication. Secrets are pre-synced to GitHub repository secrets.

**Maintenance**: When Doppler secrets rotate, re-run the sync commands above or configure Doppler GitHub App for automatic sync.

---

### Lessons Learned

**What Worked Well**:

1. Multi-agent DCTL validation discovered 3 issues before first production run
2. Non-blocking design prevented release failures (4 releases succeeded despite validation issues)
3. Test-driven fixes (created test data to verify ClickHouse insert before production)
4. Iterative debugging with production releases (v12.0.3 → v12.0.4 → v12.0.5 → v12.0.6)

**What Didn't Work**:

1. Earthly artifact export pattern (COPY + SAVE ARTIFACT in pipeline target)
2. Initial ClickHouse insert format (dict instead of list)
3. Assumed GitHub Actions checkout fetches tags by default
4. Bash variable substitution for passing secrets to Earthly commands
5. EARTHLY_CI=true environment variable silently disabled artifact export
6. Single `DOPPLER_TOKEN` for multi-project secrets (Free plan limitation)

**Key Insights**:

1. ClickHouse Cloud requires simpler SQL syntax (no IF NOT EXISTS, no ENGINE for CREATE DATABASE)
2. Explicit column names critical for ClickHouse insert robustness
3. Always specify fetch-depth and fetch-tags explicitly when working with git tags
4. Production validation essential even after multi-agent validation
5. **GitHub Actions template syntax (`${{ }}`) superior to bash variables** - resolves before bash execution, avoiding scope/quoting issues
6. **EARTHLY_CI environment variable pitfall** - Setting `EARTHLY_CI=true` silently disables all artifact export with no warnings in logs. Use `--strict` flag explicitly instead.
7. **GitHub API rate limiting** - Infrastructure issue beyond control, affects Earthly setup action. Non-blocking design mitigates impact.
8. **Doppler multi-project secret access** - Free plan Service Tokens are project-scoped. Solution: sync secrets to GitHub using CLI (`doppler secrets get` + `gh secret set`), reference via `${{ secrets.* }}`.

## Validation

### Correctness

- [x] ClickHouse `monitoring.validation_results` table stores all validation runs (v12.0.1: 3/3, v12.0.5: 3/3)
- [ ] Pushover alerts received on mobile for both success and failure (Issue #5 FIXED in v12.0.9, pending validation)
- [x] Non-blocking verified: release succeeds even when validation fails (v12.0.2, v12.0.4, v12.0.6 released despite validation issues)

### Observability

- [x] Query validation history: `SELECT * FROM monitoring.validation_results WHERE release_version IN ('v12.0.1', 'v12.0.5')` (verified with production data)
- [x] GitHub Actions artifacts uploaded (validation JSON reports) (v12.0.8: Artifact ID 4670097842, 3 files, 1200 bytes)
- [ ] Pushover alert includes release URL + validation status (Issue #5 FIXED in v12.0.9, pending validation)

### Maintainability

- [x] Earthly local testing: `earthly --strict +github-release-check` (use --strict instead of EARTHLY_CI)
- [x] Schema migrations documented in deploy-monitoring-schema.py (ClickHouse Cloud compatibility fixes documented)
- [x] ADR ↔ plan ↔ code in sync (plan.md updated with v12.0.3-v12.0.6 findings, ADR updated)

## Links

- [Plan 0037](../../development/plan/0037-release-validation/plan.md) - Implementation plan with production findings
- [ADR-0035](0035-cicd-production-validation.md) - CI/CD production validation policy (scheduled monitoring)
- [ADR-0036](0036-cicd-dry-refactoring.md) - CI/CD workflow DRY refactoring (shared e2e_core module)
- [Agent 5 Investigation](/tmp/release-validation-test/DCTL-JOURNEY-REPORT.md) - GitHub Release validation research
