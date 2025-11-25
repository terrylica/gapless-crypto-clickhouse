# Release Validation Observability Flow - Implementation Plan

**Metadata:**

- adr-id: 0037
- Status: In Progress
- Created: 2025-01-22
- Last Updated: 2025-01-25

---

## Plan

Implement automated post-release validation workflow that validates GitHub Release, PyPI package version, and production environment health after each semantic-release deployment. Store all validation results in ClickHouse for observability and alerting.

### Objectives

1. **Observability**: Capture all release validation metrics in ClickHouse
2. **Non-blocking**: Never fail releases due to validation issues
3. **Alerting**: Send Pushover notifications on validation failures
4. **Automation**: Trigger automatically after semantic-release completion

### Components

1. **Earthly Pipeline** (`Earthfile`) - Canonical validation orchestration
   - 5 validation targets (github-release, pypi-version, production-health, write-to-clickhouse, send-pushover)
   - Non-blocking execution (exit 0 on failures)
   - Artifact export to host filesystem

2. **ClickHouse Schema** (`monitoring.validation_results`)
   - 13 columns (event_time, validation_type, status, etc.)
   - SharedMergeTree engine (ClickHouse Cloud)
   - Stores all validation results regardless of pass/fail

3. **Validation Scripts** (5 Python scripts)
   - `validate_github_release.py` - Check GitHub Release exists
   - `validate_pypi_version.py` - Verify PyPI version matches release tag
   - `validate_production_health.py` - Test ClickHouse Cloud connectivity
   - `write_validation_results.py` - Insert validation results to ClickHouse
   - `send_pushover_notification.py` - Send mobile alerts

4. **GitHub Actions Workflow** (`.github/workflows/release-validation.yml`)
   - Triggered by semantic-release completion
   - Fetches secrets from Doppler
   - Runs Earthly pipeline
   - Uploads artifacts to GitHub Actions

---

## Context

### Background

**Problem**: No automated validation of releases after semantic-release deployment. Manual verification required to confirm:

- GitHub Release was created successfully
- PyPI package version matches release tag
- Production environment is healthy and accessible

**Solution**: Implement observability-first validation flow that automatically validates all release aspects and stores metrics in ClickHouse.

### Previous Work

This plan is a continuation from the previous session where ADR-0037 was implemented. The previous session completed:

- ✅ ADR-0037 written in MADR format
- ✅ ClickHouse monitoring schema created
- ✅ 5 validation scripts implemented
- ✅ Earthly pipeline with 7 targets
- ✅ GitHub Actions workflow created
- ✅ Multi-agent DCTL validation discovered 3 critical issues
- ✅ All 3 issues fixed (workflow name, requests dependency, git_commit field)

### Current Session

**Focus**: Production deployment and validation of ADR-0037 implementation.

**Approach**:

1. Deploy ClickHouse schema to production
2. Trigger semantic-release to create new version
3. Monitor release-validation workflow execution
4. Identify and fix production issues
5. Document findings and update plan

---

## Task List

### Completed Tasks

- [x] Create ClickHouse monitoring schema (monitoring.validation_results)
- [x] Deploy schema to ClickHouse Cloud production
- [x] Implement 5 validation scripts
- [x] Create Earthly pipeline with 7 targets
- [x] Create GitHub Actions release-validation workflow
- [x] Fix workflow name mismatch (Release → Semantic Release)
- [x] Add requests dependency to pyproject.toml
- [x] Add git_commit parameter to all validation scripts
- [x] Commit changes and push to GitHub
- [x] **Fix ClickHouse Cloud database creation compatibility** (Issue #4)
- [x] **Fix GitHub Actions tag fetching** (Issue #1)
- [x] **Fix ClickHouse insert schema mismatch** (Issue #2)
- [x] Monitor v12.0.1 release validation workflow
- [x] Query ClickHouse to verify validation data

### Pending Tasks

- [ ] Fix Earthly artifact export to host filesystem (Issue #3)
- [ ] Document Doppler token permissions fix (Issue #5 - manual)
- [ ] Update ADR-0037 with production findings
- [ ] Consider implementing ETag-based artifact caching (future optimization)

---

## Production Findings

### First Production Run (v12.0.0)

**Date**: 2025-01-25 01:08 UTC

**Results**: 5 issues discovered (100% failure rate before release)

#### Issue #1: Tag Detection Returning v0.0.0 (CRITICAL - FIXED)

**Error**:

```
Release Version: v0.0.0
Release URL: https://github.com/terrylica/gapless-crypto-clickhouse/releases/tag/v0.0.0
```

**Root Cause**: GitHub Actions `checkout@v4` defaults to `fetch-tags: false`. The `git describe --tags --abbrev=0` command returned fallback value.

**Fix**: Added to `.github/workflows/release-validation.yml`:

```yaml
- name: Checkout code
  uses: actions/checkout@v4
  with:
    fetch-depth: 0 # Fetch all history for tags
    fetch-tags: true # Explicitly fetch tags
```

**Validation**: Second production run showed correct version (v12.0.1)

---

#### Issue #2: ClickHouse Insert Schema Mismatch (CRITICAL - FIXED)

**Error**:

```
Failed inserts: 3
  - Failed to insert github-release-result.json: Insert data column count does not match column names
  - Failed to insert production-health-result.json: Insert data column count does not match column names
  - Failed to insert pypi-version-result.json: Insert data column count does not match column names
```

**Root Cause Analysis**:

1. Using dict format for insert instead of list format
2. Missing required columns: event_date, symbol, timeframe
3. Schema has 13 columns (excluding auto-generated validation_id), but only 9 were provided

**ClickHouse Schema**:

```sql
CREATE TABLE monitoring.validation_results (
    event_time DateTime,
    event_date Date,
    validation_id UUID DEFAULT generateUUIDv4(),
    validation_type LowCardinality(String),
    release_version String,
    git_commit String,
    symbol String DEFAULT '',
    timeframe String DEFAULT '',
    status Enum8('passed' = 1, 'failed' = 2, 'warning' = 3),
    error_message String DEFAULT '',
    duration_ms UInt32 DEFAULT 0,
    validation_context Map(String, String),
    environment LowCardinality(String) DEFAULT 'production'
) ENGINE = SharedMergeTree('/clickhouse/tables/{uuid}/{shard}', '{replica}')
ORDER BY (event_date, validation_type, release_version, event_time);
```

**Fix**: Changed `scripts/write_validation_results.py` to use list format with explicit column names:

```python
# Column names for explicit insert (excluding auto-generated validation_id)
column_names = [
    "event_time", "event_date", "validation_type",
    "release_version", "git_commit", "symbol", "timeframe",
    "status", "error_message", "duration_ms",
    "validation_context", "environment"
]

# List format matching column order
event_time = datetime.now(timezone.utc)
row = [
    event_time,
    event_time.date(),
    data.get("validation_type", "unknown"),
    data.get("release_version", ""),
    data.get("git_commit", ""),
    "",  # symbol (empty for release validations)
    "",  # timeframe (empty for release validations)
    status,
    data.get("error_message", ""),
    data.get("duration_ms", 0),
    data.get("validation_context", {}),
    "production"
]

# Insert with explicit column names
client.insert("monitoring.validation_results", [row], column_names=column_names)
```

**Test Validation**:

```bash
# Created test file /tmp/validation-test/test-result.json
doppler run --project aws-credentials --config prd -- \
  python3 scripts/write_validation_results.py --results-dir /tmp/validation-test/

# Result: ✅ All validation results written to ClickHouse (1/1 inserts successful)
```

**Production Validation**: Second production run showed:

```
Total files: 3
Successful inserts: 3
Failed inserts: 0
✅ All validation results written to ClickHouse
```

---

#### Issue #3: Earthly Artifact Export (MEDIUM - UNFIXED)

**Error**:

```
##[warning]No files were found with the provided path: artifacts/*.json.
No artifacts will be uploaded.
```

**Root Cause**: The `BUILD` command in Earthly doesn't automatically copy artifacts from child targets to parent target.

**Attempted Fix** (did NOT work):

```earthly
release-validation-pipeline:
    FROM +validation-base

    # Run all validation targets
    BUILD +github-release-check
    BUILD +pypi-version-check
    BUILD +production-health-check
    BUILD +write-to-clickhouse
    BUILD +send-pushover-alert

    # Collect artifacts from each validation target
    COPY +github-release-check/github-release-result.json ./artifacts/
    COPY +pypi-version-check/pypi-version-result.json ./artifacts/
    COPY +production-health-check/production-health-result.json ./artifacts/

    # Export all artifacts to host filesystem
    SAVE ARTIFACT ./artifacts/*.json AS LOCAL ./artifacts/
```

**Status**: UNFIXED - Remains an open issue. Validation results are successfully stored in ClickHouse, but not uploaded as GitHub Actions artifacts.

**Impact**: Medium severity - doesn't block validation functionality, just prevents artifact download from GitHub Actions UI.

**Next Investigation**: Need to understand Earthly's BUILD vs RUN behavior, possibly need different approach for artifact collection.

---

#### Issue #4: ClickHouse Cloud Database Creation (CRITICAL - FIXED)

**Error**:

```
Code: 344. DB::Exception: Only queries like `CREATE DATABASE <database>` are supported for creating database.
Current query is CREATE DATABASE IF NOT EXISTS monitoring ENGINE = Ordinary. (SUPPORT_IS_DISABLED)
```

**Root Cause**: ClickHouse Cloud has stricter SQL requirements than self-hosted ClickHouse. It doesn't support `IF NOT EXISTS` or `ENGINE` clauses in `CREATE DATABASE` statements.

**Fix**: Changed `scripts/deploy-monitoring-schema.py`:

```python
# BEFORE (failed on ClickHouse Cloud):
client.command("CREATE DATABASE IF NOT EXISTS monitoring ENGINE = Ordinary")

# AFTER (ClickHouse Cloud compatible):
try:
    client.command("CREATE DATABASE monitoring")
    log_with_timestamp("✅ Database 'monitoring' created")
except Exception as e:
    error_msg = str(e)
    # Database already exists (code 81 or 82)
    if "already exists" in error_msg.lower() or "code: 81" in error_msg or "code: 82" in error_msg:
        log_with_timestamp("✅ Database 'monitoring' already exists")
    else:
        raise
```

**Validation**:

```bash
doppler run --project aws-credentials --config prd -- \
  python3 scripts/deploy-monitoring-schema.py

# Output:
# ✅ Database 'monitoring' already exists
# ✅ Table 'validation_results' created (or already exists)
# ✅ DEPLOYMENT SUCCESSFUL
```

---

#### Issue #5: Doppler Token Permissions (MEDIUM - MANUAL FIX REQUIRED)

**Error**:

```
Unable to fetch secrets
Doppler Error: This token does not have access to requested project 'notifications'
---
❌ Failed to send Pushover notification
Error: PUSHOVER_APP_TOKEN or PUSHOVER_USER_KEY not set
```

**Root Cause**: The `DOPPLER_TOKEN` secret in GitHub Actions only has access to `aws-credentials` project, not `notifications` project.

**Fix Required**: Manual update of GitHub secrets (DOPPLER_TOKEN) to include notifications project access.

**Impact**: Medium severity - prevents Pushover mobile alerts, but validation still runs and stores results in ClickHouse.

**Documentation**: Will be documented as separate task for manual completion.

---

### Second Production Run (v12.0.1)

**Date**: 2025-01-25 01:13 UTC

**Results**: 3 critical fixes validated, 2 issues remain open

**Tag Detection**: ✅ FIXED

- Before: v0.0.0
- After: v12.0.1 (correct)

**ClickHouse Inserts**: ✅ FIXED

- Before: 0/3 successful
- After: 3/3 successful

**Validation Results**:

- ✅ GitHub Release: PASSED (v12.0.1 release exists)
- ✅ Production Health: PASSED (ClickHouse Cloud healthy)
- ❌ PyPI Version: FAILED (expected - v12.0.1 not yet published to PyPI)

**Remaining Issues**:

- ❌ Earthly artifact export (Issue #3)
- ❌ Doppler token permissions (Issue #5)

---

### ClickHouse Data Verification

**Query**: All validation results for v12.0.1

**Results**: 3 records correctly stored

**Sample Record** (GitHub Release Validation):

```json
{
  "event_time": "2025-11-25 01:14:05",
  "event_date": "2025-11-25",
  "validation_id": "72d34e94-7855-4108-8b0a-a513d5c15ba2",
  "validation_type": "github_release",
  "release_version": "v12.0.1",
  "git_commit": "a33e08026132556b222e4ccc0798d0fb6206117f",
  "symbol": "",
  "timeframe": "",
  "status": "passed",
  "error_message": "",
  "duration_ms": 226,
  "validation_context": {
    "tag_name": "v12.0.1",
    "release_url": "https://github.com/terrylica/gapless-crypto-clickhouse/releases/tag/v12.0.1",
    "published_at": "2025-11-25T01:13:21Z",
    "target_commit": "main",
    "asset_count": "0"
  },
  "environment": "production"
}
```

**Verification**: ✅ All fields correctly populated

- ✅ git_commit field present
- ✅ validation_context contains rich metadata
- ✅ status enum values working (passed/failed)
- ✅ Timestamps accurate
- ✅ UUIDs auto-generated

**Conclusion**: Observability goal of ADR-0037 is **fully working** in production.

---

### Third Production Run (v12.0.5)

**Date**: 2025-11-25 03:17 UTC

**Context**: Continuation session focused on fixing Earthly artifact export (Issue #3)

**Results**: 1 critical fix validated (secret passing), 1 new issue identified (Earthly CI mode)

**Secret Passing**: ✅ FIXED

**Problem**: v12.0.4 failed with "unable to lookup secret 'GITHUB_TOKEN': not found"

**Root Cause**: Bash variable substitution failing when multiple `earthly` commands execute sequentially

**Fix Applied**:
1. Created new "Fetch Doppler secrets" step that stores secrets in GitHub Actions step outputs
2. Changed all secret passing from bash variables to GitHub Actions template syntax
3. Examples:
   - BEFORE: `export GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"` then `--secret GITHUB_TOKEN="$GITHUB_TOKEN"`
   - AFTER: `--secret GITHUB_TOKEN="${{ secrets.GITHUB_TOKEN }}"` (direct template syntax)

**Validation**: All validation targets executed successfully, no "secret not found" errors

**ClickHouse Inserts**: ✅ SUCCESSFUL

- Before (v12.0.4): Validation never ran (secret error)
- After (v12.0.5): 3/3 successful inserts

**Validation Results**:

- ✅ GitHub Release: PASSED (176ms)
- ✅ Production Health: PASSED (36,813ms / 36.8 seconds)
- ❌ PyPI Version: FAILED (expected - v12.0.5 not yet published to PyPI)

**Artifact Export**: ❌ STILL BROKEN

**Symptom**: "No files were found with the provided path: artifacts/*.json"

**Root Cause Identified**: `EARTHLY_CI=true` environment variable sets Earthly to `--ci` mode, which is equivalent to `--no-output --strict`. This **disables** `SAVE ARTIFACT AS LOCAL` export to host filesystem.

**Evidence**: Workflow logs show "Local Output Summary 🎁 (disabled)" for all Earthly builds.

**Solution Designed**: Remove `EARTHLY_CI=true` and add `--strict` flag explicitly to all earthly commands. This maintains CI-appropriate strict mode while enabling artifact export.

**References**:
- [Earthly Issue #4297](https://github.com/earthly/earthly/issues/4297)
- [Stack Overflow - Earthly + GitLab CI](https://stackoverflow.com/questions/78048916/how-to-save-an-artifact-locally-using-earthly-and-gitlab-ci-cd)

---

### Fourth Production Run (v12.0.6)

**Date**: 2025-11-25 03:24 UTC

**Context**: Testing Earthly artifact export fix (--strict flag)

**Results**: Cannot validate fix - infrastructure issue

**Artifact Export Fix**: ✅ IMPLEMENTED (UNTESTED)

**Changes Applied**:
1. Removed `EARTHLY_CI: true` environment variable from workflow
2. Added `--strict` flag to all 5 earthly commands:
   - `github-release-check`
   - `pypi-version-check`
   - `production-health-check`
   - `write-to-clickhouse`
   - `send-pushover-alert`

**Expected Outcome**: Earthly should export artifacts to `./artifacts/` directory, GitHub Actions upload should succeed

**Actual Outcome**: ❌ GITHUB API RATE LIMIT

**Error**: `API rate limit exceeded for 172.215.209.67` during Earthly setup step

**Impact**: Earthly was never installed, validation targets never executed, artifact export fix could not be tested

**ClickHouse Data**: No validation records for v12.0.6 (validation didn't run)

**Status**: Fix implementation complete, awaiting next release to validate

---

### Continuation Session Summary (v12.0.3 - v12.0.6)

**Versions Released**: 4 versions (v12.0.3, v12.0.4, v12.0.5, v12.0.6)

**Issues Fixed**: 2 critical issues

1. ✅ **Issue #4.1: Earthly Secret Passing** (v12.0.5)
   - Changed from bash variable substitution to GitHub Actions template syntax
   - All secrets now passed reliably to Earthly commands
   - Validation targets execute successfully

2. ✅ **Issue #3: Earthly Artifact Export** (v12.0.6)
   - Root cause identified: `EARTHLY_CI=true` disables artifact export
   - Fix implemented: Use `--strict` flag instead
   - **Status**: UNTESTED (blocked by GitHub API rate limit)

**Issues Remaining**: 2 medium-severity issues

1. ❌ **Issue #3: Earthly Artifact Export** - Fix implemented but untested
2. ❌ **Issue #5: Doppler Token Permissions** - Manual fix required

**Core Observability**: ✅ FULLY WORKING

- v12.0.5 validation data successfully stored in ClickHouse
- GitHub Release, Production Health, and PyPI Version checks all executed
- Non-blocking design confirmed (releases succeed despite validation failures)

**Key Insights**:

1. **GitHub Actions Template Syntax Superior to Bash Variables**: Direct template syntax (`${{ }}`) resolves before bash execution, avoiding scope/quoting issues
2. **EARTHLY_CI Environment Variable Pitfall**: Setting `EARTHLY_CI=true` silently disables all artifact export, no warnings in logs
3. **GitHub API Rate Limiting**: Infrastructure issue beyond control, affects Earthly setup action
4. **Non-Blocking Design Success**: 4 releases completed successfully despite validation issues (v12.0.2, v12.0.4, v12.0.6 validation failed, releases still succeeded)

---

## Next Steps

### Immediate (Priority 1)

1. **Validate Earthly artifact export fix** (Issue #3 - v12.0.7+)
   - Fix implemented: `--strict` flag instead of `EARTHLY_CI=true`
   - Awaiting next release to test (blocked by GitHub API rate limit in v12.0.6)
   - Expected: artifacts/*.json files exported to GitHub Actions runner
   - Success criteria: "Upload validation artifacts" step succeeds

2. **Update ADR-0037** with continuation session findings
   - Add v12.0.3 - v12.0.6 production findings
   - Document secret passing fix and Earthly CI mode discovery
   - Update lessons learned with GitHub Actions template syntax insights

### Short-term (Priority 2)

3. **Document Doppler token fix** (Issue #5)
   - Create step-by-step guide for updating GitHub secrets
   - Include screenshots of Doppler token creation
   - Add to CLAUDE.md or separate operations doc

4. **Add monitoring queries** to validation documentation
   - Example queries for common observability patterns
   - Dashboard suggestions for Grafana/Metabase
   - Alert thresholds recommendations

### Long-term (Priority 3)

5. **Implement ETag-based artifact caching**
   - Reduce bandwidth for repeated artifact downloads
   - Store ETags in validation_context
   - Skip re-download if ETag matches

6. **Add performance metrics** to validation results
   - Track validation duration trends over time
   - Identify performance regressions
   - Set SLOs for validation latency

---

## Lessons Learned

### What Worked Well

1. **Multi-agent DCTL validation** - Discovered 3 issues before first production run
2. **Non-blocking design** - Validation failures didn't break releases
3. **Observability-first** - All validation results captured regardless of pass/fail
4. **Test-driven fixes** - Created test data to verify ClickHouse insert fix before production

### What Didn't Work

1. **Earthly artifact export pattern** - COPY + SAVE ARTIFACT in pipeline target didn't work as expected
2. **Initial ClickHouse insert format** - Used dict instead of list, missing columns
3. **Tag fetching assumption** - Didn't realize checkout@v4 defaults to fetch-tags: false

### Key Insights

1. **ClickHouse Cloud compatibility** - Requires simpler SQL syntax than self-hosted (no IF NOT EXISTS, no ENGINE for CREATE DATABASE)
2. **Explicit column names critical** - ClickHouse insert() requires list format with explicit column_names parameter for robust schema compatibility
3. **GitHub Actions defaults** - Always specify fetch-depth and fetch-tags explicitly when working with git tags
4. **Production validation essential** - Despite multi-agent validation, 2 additional issues were discovered only in production (tag fetching, ClickHouse Cloud SQL)

---

## References

- ADR-0037: `/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/decisions/0037-release-validation-observability.md`
- Earthfile: `/Users/terryli/eon/gapless-crypto-clickhouse/Earthfile`
- GitHub Actions Workflow: `/Users/terryli/eon/gapless-crypto-clickhouse/.github/workflows/release-validation.yml`
- ClickHouse Schema: `/Users/terryli/eon/gapless-crypto-clickhouse/scripts/deploy-monitoring-schema.py`
- Validation Scripts: `/Users/terryli/eon/gapless-crypto-clickhouse/scripts/validate_*.py`
