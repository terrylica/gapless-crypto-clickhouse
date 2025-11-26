---
version: "2.0.0"
last_updated: "2025-11-22"
canonical_source: true
supersedes: ["1.0.0 (OIDC Trusted Publishing)"]
adr: "ADR-0027"
---

# Publishing Guide: Local-Only PyPI Publishing

> **🚨 CRITICAL: LOCAL-ONLY PYPI PUBLISHING**
>
> This project enforces **local-only PyPI publishing** as a workspace-wide policy.
>
> - ✅ **GitHub Actions**: Automated versioning (tags, releases, changelogs) ONLY
> - ❌ **GitHub Actions**: NO PyPI publishing (intentionally removed from config)
> - ✅ **Local Machine**: Manual PyPI publishing via `./scripts/publish-to-pypi.sh`
>
> **Why Local-Only?**
>
> - **Security**: No long-lived PyPI tokens in GitHub secrets
> - **Speed**: 30 seconds locally vs 3-5 minutes in CI
> - **Control**: Manual approval step before production release
> - **Flexibility**: Use Doppler credential management (`pypi-doppler` skill)
>
> **Architecture**: All repositories in `~/` follow this pattern (workspace-wide policy).
>
> See: ADR-0027 for architectural decision details

## Complete Release Workflow

### Step 1: Development & Commit (Conventional Commits)

```bash
# Make your changes
git add .

# Commit with conventional format (determines version bump)
git commit -m "feat: add new feature"  # MINOR bump (1.0.0 → 1.1.0)
# or
git commit -m "fix: correct bug"      # PATCH bump (1.0.0 → 1.0.1)
# or
git commit -m "feat!: breaking change" # MAJOR bump (1.0.0 → 2.0.0)

# Push to main
git push origin main
```

**Conventional Commit Types**:

- `feat:` - New feature (MINOR version bump)
- `fix:` - Bug fix (PATCH version bump)
- `docs:` - Documentation only (PATCH version bump)
- `perf:` - Performance improvement (PATCH version bump)
- `refactor:` - Code refactoring (NO version bump)
- `test:` - Test changes (NO version bump)
- `chore:` - Maintenance (NO version bump)
- `feat!:` or `BREAKING CHANGE:` - Breaking change (MAJOR version bump)

### Step 2: Automated Versioning (GitHub Actions - 40-60s)

**Automatically happens** when you push to main with conventional commits.

GitHub Actions workflow (`.github/workflows/release.yml`) will:

1. ✅ Analyze commits using `@semantic-release/commit-analyzer`
2. ✅ Determine next version (e.g., `v7.1.0`)
3. ✅ Update `pyproject.toml`, `package.json` versions
4. ✅ Generate and update `CHANGELOG.md`
5. ✅ Create git tag (`v7.1.0`)
6. ✅ Create GitHub release with release notes
7. ✅ Commit changes back to repo with `[skip ci]` message

**⚠️ PyPI publishing does NOT happen here** (by design - see ADR-0027)

**No action required** - just wait for workflow to complete (~1 minute).

### Step 3: Local PyPI Publishing (30 seconds)

**After GitHub Actions completes**, publish to PyPI locally:

```bash
# Pull the latest release commit
git pull origin main

# Publish to PyPI (uses pypi-doppler skill)
./scripts/publish-to-pypi.sh
```

**Expected output**:

```
🚀 Publishing to PyPI (Local Workflow)
======================================

🔐 Step 0: Verifying Doppler credentials...
   ✅ Doppler token verified

📥 Step 1: Pulling latest release commit...
   Current version: v7.1.0

🧹 Step 2: Cleaning old builds...
   ✅ Cleaned

📦 Step 3: Building package...
   ✅ Built: dist/gapless_crypto_clickhouse-7.1.0-py3-none-any.whl
   ✅ Built: dist/gapless_crypto_clickhouse-7.1.0.tar.gz

📤 Step 4: Publishing to PyPI...
   Using PYPI_TOKEN from Doppler
   ✅ Published to PyPI

🔍 Step 5: Verifying on PyPI...
   ✅ Verified: https://pypi.org/project/gapless-crypto-clickhouse/7.1.0/

✅ Complete! Published v7.1.0 to PyPI in 28 seconds
```

**Done!** Package is now live on PyPI.

## Architecture Details

### What GitHub Actions Does (Versioning Only)

```
.github/workflows/release.yml
├─ Trigger: Push to main branch
├─ Condition: Conventional commits detected (feat:, fix:, etc.)
│
├─ Step 1: Checkout repository
├─ Step 2: Setup Node.js + UV
├─ Step 3: Install semantic-release + plugins
├─ Step 4: Run semantic-release
│  ├─ @semantic-release/commit-analyzer → Determine version
│  ├─ @semantic-release/release-notes-generator → Generate CHANGELOG
│  ├─ @semantic-release/changelog → Write CHANGELOG.md
│  ├─ @semantic-release/exec::prepareCmd → Update versions in files
│  ├─ @semantic-release/npm → Update package.json (npmPublish: false)
│  ├─ @semantic-release/github → Create GitHub release
│  └─ @semantic-release/git → Commit + tag + push
│
└─ Result: GitHub release created, NO PyPI publishing
```

**Key Configuration** (`.releaserc.json`):

```json
{
  "@semantic-release/exec": {
    "_comment": "LOCAL-ONLY PUBLISHING: No publishCmd, no building in CI",
    "prepareCmd": "update versions only (no uv build)"
  }
}
```

### What Local Script Does (Publishing Only)

```
scripts/publish-to-pypi.sh
├─ Guard 1: CI detection (blocks if CI=true)
├─ Guard 2: Repository verification (prevents fork abuse)
│
├─ Step 0: Verify Doppler credentials (PYPI_TOKEN exists)
├─ Step 1: Pull latest release commit from GitHub
├─ Step 2: Clean old builds (rm -rf dist/)
├─ Step 3: Build package (uv build)
├─ Step 4: Publish to PyPI (uv publish with Doppler token)
└─ Step 5: Verify publication on PyPI
```

**Credential Management**:

- Token stored in Doppler: `claude-config/prd` → `PYPI_TOKEN`
- Script retrieves token: `doppler secrets get PYPI_TOKEN --plain`
- No plaintext token storage (encrypted Doppler vault)

## Safety Mechanisms

### Layer 1: No Publishing Config in `.releaserc.json`

**Configuration removed**:

- ❌ `publishCmd` deleted entirely (cleanest approach)
- ❌ `uv build` removed from `prepareCmd` (no artifacts in CI)

**Result**: No way for GitHub Actions to publish, even if credentials added.

### Layer 2: CI Detection Guards in Script

**Environment variables checked**:

- `CI` - Generic CI indicator
- `GITHUB_ACTIONS` - GitHub Actions
- `GITLAB_CI` - GitLab CI
- `JENKINS_URL` - Jenkins
- `CIRCLECI` - CircleCI

**Behavior**: Script exits with error if any detected.

**Test locally**:

```bash
# This should FAIL with error message
CI=true ./scripts/publish-to-pypi.sh

# Expected output:
# ❌ ERROR: This script must ONLY be run on your LOCAL machine
# ...workspace-wide policy explanation...
```

### Layer 3: Repository Verification

**Checks**:

- `GITHUB_REPOSITORY` environment variable
- Must match: `terrylica/gapless-crypto-clickhouse`

**Prevents**: Fork maintainers accidentally publishing to their own PyPI accounts.

### Layer 4: Documentation

**Clear warnings in**:

- This file (PUBLISHING.md)
- `.releaserc.json` (\_comment field)
- `.github/workflows/release.yml` (inline comment)
- `CLAUDE.md` (project memory)

**Prevents**: Future maintainers re-adding CI publishing.

## Prerequisites

### One-Time Setup (Already Complete)

✅ **Doppler CLI Installed**: `brew install dopplerhq/cli/doppler`
✅ **Doppler Authenticated**: `doppler login`
✅ **PYPI_TOKEN Stored**: In `claude-config/prd` Doppler project
✅ **Publish Script Created**: `scripts/publish-to-pypi.sh`
✅ **semantic-release Configured**: `.releaserc.json` (versioning only)

### Verifying Doppler Access

```bash
# Check you're logged in
doppler whoami

# Verify PYPI_TOKEN exists
doppler secrets get PYPI_TOKEN --project claude-config --config prd --plain

# If missing, set it
doppler secrets set PYPI_TOKEN='pypi-AgEIcHlwaS5vcmc...' --project claude-config --config prd
```

## Troubleshooting

### Issue: "PYPI_TOKEN not found in Doppler"

**Symptom**: Script fails at Step 0

**Fix**:

```bash
# Verify token exists
doppler secrets --project claude-config --config prd | grep PYPI_TOKEN

# If missing, get new token from PyPI
# Visit: https://pypi.org/manage/account/token/
# Create token with scope: "Entire account" or specific project
# Store in Doppler
doppler secrets set PYPI_TOKEN='your-token' --project claude-config --config prd
```

### Issue: "403 Forbidden from PyPI"

**Symptom**: Script fails at Step 4 with authentication error

**Root Cause**: Token expired or invalid (PyPI requires 2FA since 2024)

**Fix**:

1. Verify 2FA enabled on PyPI account
2. Create new token: https://pypi.org/manage/account/token/
3. Update Doppler: `doppler secrets set PYPI_TOKEN='new-token' --project claude-config --config prd`
4. Retry publish

### Issue: "Script blocked with CI detection error"

**Symptom**:

```
❌ ERROR: This script must ONLY be run on your LOCAL machine
Detected CI environment variables:
- CI: true
```

**Root Cause**: Running in CI environment OR `CI` variable set locally

**Fix**:

```bash
# Check if CI variable set in your shell
env | grep CI

# If set, unset it
unset CI
unset GITHUB_ACTIONS

# Retry publish
./scripts/publish-to-pypi.sh
```

**Expected behavior**: This is INTENTIONAL - script should ONLY run locally.

### Issue: "Version not updated in pyproject.toml"

**Symptom**: Local publish uses old version number

**Root Cause**: Didn't pull latest release commit from GitHub

**Fix**:

```bash
# Always pull before publishing
git pull origin main

# Verify version updated
grep '^version = ' pyproject.toml

# Retry publish
./scripts/publish-to-pypi.sh
```

### Issue: "GitHub Actions workflow failed"

**Symptom**: Release workflow shows red X

**Possible Causes**:

1. **Invalid conventional commit format** - Check commit message follows `type: description`
2. **No version bump warranted** - `chore:` and `refactor:` don't trigger releases
3. **`[skip ci]` in commit message** - Workflow intentionally skipped

**Fix**:

```bash
# Check recent workflow runs
gh run list --workflow=release.yml --limit 3

# View logs for specific run
gh run view <run-id> --log

# If no version bump needed, that's expected (not an error)
```

## Migration from OIDC Trusted Publishing

**Previous setup** (v1.0.0 of this document): Used PyPI OIDC Trusted Publishing with GitHub Actions.

**Current setup** (v2.0.0): Local-only publishing with Doppler credential management.

**Why changed**:

- Workspace-wide policy: No CI/CD for PyPI publishing
- Faster: 30s local vs 3-5min CI
- More control: Manual approval before production release
- Simpler: No GitHub environments or OIDC configuration needed

**No migration needed** - old workflow files were already disabled (`.github/workflows/publish.yml.disabled`).

## FAQ

### Q: Why not use GitHub Actions for publishing?

**A**: Workspace-wide policy decision (ADR-0027). Benefits:

- **Security**: No long-lived tokens in GitHub secrets
- **Speed**: 10x faster (30s vs 3-5min)
- **Control**: Manual review before each release
- **Flexibility**: Use Doppler for centralized credential management

### Q: What if I want to publish from CI?

**A**: Not supported by design. This is a workspace-wide policy for all repositories. If you need automated publishing, consider:

1. Re-evaluate if manual control is valuable (it usually is)
2. If absolutely necessary, fork and modify (not recommended)
3. Discuss with repository owner about policy exceptions

### Q: Can I dry-run the publish locally?

**A**: Yes, but requires modifying the script. Better approach:

```bash
# Build locally without publishing
uv build

# Inspect dist/ artifacts
ls -lh dist/

# If looks good, publish
./scripts/publish-to-pypi.sh
```

### Q: How do I test on TestPyPI first?

**A**: Modify `scripts/publish-to-pypi.sh` temporarily:

```bash
# Add --repository testpypi to uv publish command
uv publish --repository testpypi --token "${PYPI_TOKEN}"

# After testing, change back to:
uv publish --token "${PYPI_TOKEN}"
```

**Better**: Keep a separate `publish-to-testpypi.sh` script for testing.

### Q: What happens if I add DOPPLER_TOKEN to GitHub secrets?

**A**: Nothing. The `.releaserc.json` has no `publishCmd`, so semantic-release won't attempt publishing even with credentials available.

### Q: How do I publish a hotfix without waiting for GitHub Actions?

**A**: You can't skip GitHub Actions versioning. Workflow:

1. Push hotfix commit: `git commit -m "fix: critical bug"`
2. Wait for GitHub Actions (~1 min)
3. Pull and publish locally (~30s)
4. Total: ~90s (still faster than CI-only publishing)

**If absolutely urgent**: Manually update `pyproject.toml` version and build/publish, but this breaks semantic-release tracking (not recommended).

## Related Documentation

- **ADR-0027**: [`docs/architecture/decisions/0027-local-only-pypi-publishing.md`](docs/architecture/decisions/0027-local-only-pypi-publishing.md) - Architectural decision record
- **Plan**: [`docs/development/plan/0027-local-only-pypi-publishing/plan.md`](docs/development/plan/0027-local-only-pypi-publishing/plan.md) - Implementation plan
- **semantic-release Skill**: [`~/.claude/skills/semantic-release/SKILL.md`](~/.claude/skills/semantic-release/SKILL.md) - Local-first release workflow
- **pypi-doppler Skill**: Doppler-based PyPI publishing (credential management)

---

**Last Updated**: 2025-11-22 (ADR-0027 implementation)
**Supersedes**: v1.0.0 (OIDC Trusted Publishing workflow)
**Workspace Policy**: All repositories use local-only PyPI publishing
