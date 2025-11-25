# Doppler Token Permissions Fix - Manual Procedure

**Issue**: Pushover notifications failing in release-validation workflow due to insufficient Doppler token permissions.

**Status**: Requires manual fix

**Priority**: Medium (non-blocking - validation still runs and stores results in ClickHouse)

---

## Problem Statement

The GitHub Actions `DOPPLER_TOKEN` secret only has access to the `aws-credentials` project, but the release-validation workflow also needs access to the `notifications` project to fetch Pushover credentials.

**Error**:

```
Unable to fetch secrets
Doppler Error: This token does not have access to requested project 'notifications'
---
❌ Failed to send Pushover notification
Error: PUSHOVER_APP_TOKEN or PUSHOVER_USER_KEY not set
```

**Impact**:

- ✅ Release validation still runs successfully
- ✅ Validation results still stored in ClickHouse
- ❌ Pushover mobile alerts not sent
- ❌ No immediate notification of validation failures

---

## Root Cause

The current `DOPPLER_TOKEN` was scoped to only the `aws-credentials` project when it was created. Doppler tokens can be scoped to:

1. Specific projects (current configuration)
2. All projects (recommended for this use case)
3. Multiple specific projects

The release-validation workflow needs access to **two projects**:

- `aws-credentials` (for ClickHouse Cloud credentials)
- `notifications` (for Pushover credentials)

---

## Solution: Create New Doppler Token

### Step 1: Create New Service Token in Doppler

1. Log in to Doppler dashboard: https://dashboard.doppler.com
2. Navigate to **Access** tab in the top navigation
3. Click **Service Tokens** in the left sidebar
4. Click **Generate** button

### Step 2: Configure Token Scope

**Token Configuration**:

- **Name**: `GitHub Actions - Release Validation` (descriptive name)
- **Access**: Select **All Projects** (recommended)
  - Alternative: Select specific projects (`aws-credentials` + `notifications`)
- **Configs**:
  - For `aws-credentials`: Select `prd` config
  - For `notifications`: Select `prd` config

**Recommended**: Choose "All Projects" to avoid this issue in the future if you add more validation steps that need other Doppler projects.

### Step 3: Copy Token Value

1. Click **Generate** to create the token
2. **IMPORTANT**: Copy the token value immediately (it won't be shown again)
3. Store it temporarily in a secure location (password manager or clipboard)

### Step 4: Update GitHub Secrets

1. Navigate to GitHub repository: https://github.com/terrylica/gapless-crypto-clickhouse
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Find the `DOPPLER_TOKEN` secret
4. Click **Update** (or **Remove** then **New repository secret**)
5. Paste the new token value
6. Click **Update secret** (or **Add secret**)

---

## Verification

### Test 1: Manual Workflow Dispatch

1. Go to **Actions** tab in GitHub
2. Select **Release Validation** workflow
3. Click **Run workflow** dropdown
4. Enter a recent release version (e.g., `v12.0.1`)
5. Click **Run workflow**
6. Wait for workflow to complete
7. Check workflow logs for Pushover notification success

**Expected Output**:

```
✅ Pushover notification sent successfully
```

### Test 2: Verify Doppler Access

Run this locally to verify the new token has access to both projects:

```bash
# Set the new Doppler token
export DOPPLER_TOKEN="<new-token-value>"

# Test aws-credentials project access
doppler secrets get CLICKHOUSE_HOST --project aws-credentials --config prd --plain

# Test notifications project access
doppler secrets get PUSHOVER_APP_TOKEN --project notifications --config prd --plain

# Both commands should return values without errors
```

**Expected**: Both commands succeed and return secret values.

### Test 3: Trigger Real Release

The next time semantic-release creates a new version, the release-validation workflow will automatically trigger and should now successfully send Pushover notifications.

---

## Rollback Plan

If the new token causes issues:

1. Revert to old token value in GitHub Secrets
2. Pushover notifications will fail again (non-blocking)
3. Validation still runs and stores results in ClickHouse

**No risk to release process** - validation workflow has `continue-on-error: true` at multiple levels.

---

## Alternative Solution: Use Separate Secrets

If you prefer not to use a single Doppler token with access to multiple projects, you can create two separate tokens:

1. `DOPPLER_TOKEN_AWS` - scoped to `aws-credentials` project
2. `DOPPLER_TOKEN_NOTIFICATIONS` - scoped to `notifications` project

**Trade-off**: Requires updating `.github/workflows/release-validation.yml` to use different tokens for different secret fetches. More complex but more granular access control.

**Recommendation**: Use single token with "All Projects" access for simplicity. The token is already stored in GitHub Secrets (encrypted at rest), and scoping at the GitHub repository level provides sufficient security.

---

## Timeline

**Expected Duration**: 10-15 minutes

- 5 minutes: Create new Doppler token
- 2 minutes: Update GitHub secret
- 5 minutes: Test and verify
- 3 minutes: Monitor next automatic validation run

**Priority**: Can be done at any time (non-blocking)

---

## Related Documentation

- [Doppler Service Tokens Documentation](https://docs.doppler.com/docs/service-tokens)
- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [ADR-0037 Production Validation](../../architecture/decisions/0037-release-validation-observability.md) - Issue #5
- [Plan 0037](plan.md) - Full implementation plan

---

## Post-Fix Validation Checklist

After completing this fix, update the following:

- [ ] Doppler token created with access to both projects
- [ ] GitHub `DOPPLER_TOKEN` secret updated
- [ ] Manual workflow dispatch test successful
- [ ] Pushover notification received on mobile device
- [ ] ADR-0037 validation checklist updated (mark Pushover items as complete)
- [ ] This document archived or marked as "COMPLETED"

---

**Status**: PENDING - Awaiting manual completion
**Created**: 2025-01-25
**Owner**: Repository maintainer with Doppler and GitHub admin access
