#!/bin/bash
# Quick PyPI Publishing Script
# Usage: ./scripts/publish-to-pypi.sh
# Requires: Doppler CLI with PYPI_TOKEN secret

set -e

# ============================================================================
# CRITICAL: CI DETECTION GUARD (Prevents accidental CI execution)
# ============================================================================
# This script enforces WORKSPACE-WIDE POLICY: PyPI publishing must ONLY
# happen on local machines, NEVER in CI/CD pipelines.
# See: docs/development/PUBLISHING.md and ADR-0027
# ============================================================================

if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] || [ -n "$GITLAB_CI" ] || [ -n "$JENKINS_URL" ] || [ -n "$CIRCLECI" ]; then
    echo "❌ ERROR: This script must ONLY be run on your LOCAL machine"
    echo ""
    echo "   Detected CI environment variables:"
    echo "   - CI: ${CI:-<not set>}"
    echo "   - GITHUB_ACTIONS: ${GITHUB_ACTIONS:-<not set>}"
    echo "   - GITLAB_CI: ${GITLAB_CI:-<not set>}"
    echo "   - JENKINS_URL: ${JENKINS_URL:-<not set>}"
    echo "   - CIRCLECI: ${CIRCLECI:-<not set>}"
    echo ""
    echo "   This project enforces LOCAL-ONLY PyPI publishing for:"
    echo "   - Security: No long-lived PyPI tokens in GitHub secrets"
    echo "   - Speed: 30 seconds locally vs 3-5 minutes in CI"
    echo "   - Control: Manual approval step before production release"
    echo ""
    echo "   Publishing should NEVER happen in CI/CD pipelines."
    echo "   This is a WORKSPACE-WIDE POLICY for all repositories."
    echo ""
    echo "   See: docs/development/PUBLISHING.md (ADR-0027)"
    exit 1
fi

# ============================================================================
# REPOSITORY VERIFICATION (Prevents fork abuse)
# ============================================================================

EXPECTED_REPO="terrylica/gapless-crypto-clickhouse"
if [ -n "$GITHUB_REPOSITORY" ] && [ "$GITHUB_REPOSITORY" != "$EXPECTED_REPO" ]; then
    echo "❌ ERROR: Wrong repository detected"
    echo ""
    echo "   Expected: $EXPECTED_REPO"
    echo "   Got: $GITHUB_REPOSITORY"
    echo ""
    echo "   This script should only run in the official repository."
    echo "   If you forked this repo, update EXPECTED_REPO in this script."
    exit 1
fi

echo "🚀 Publishing to PyPI (Local Workflow)"
echo "======================================"

# Step 0: Verify Doppler token is available
echo -e "\n🔐 Step 0: Verifying Doppler credentials..."
if ! doppler secrets get PYPI_TOKEN --plain > /dev/null 2>&1; then
    echo "   ❌ ERROR: PYPI_TOKEN not found in Doppler"
    echo "   Run: doppler secrets set PYPI_TOKEN='your-token'"
    exit 1
fi
echo "   ✅ Doppler token verified"

# Step 1: Pull latest release commit from GitHub
echo -e "\n📥 Step 1: Pulling latest release commit..."
git pull origin main
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "   Current version: v${CURRENT_VERSION}"

# Step 2: Clean old builds
echo -e "\n🧹 Step 2: Cleaning old builds..."
rm -rf dist/ build/ *.egg-info
echo "   ✅ Cleaned"

# Step 3: Build package
echo -e "\n📦 Step 3: Building package..."
uv build 2>&1 | grep -E "(Building|Successfully built)" || uv build
echo "   ✅ Built: dist/gapless_crypto_clickhouse-${CURRENT_VERSION}*"

# Step 4: Publish to PyPI using Doppler token
echo -e "\n📤 Step 4: Publishing to PyPI..."
echo "   Using PYPI_TOKEN from Doppler"
PYPI_TOKEN=$(doppler secrets get PYPI_TOKEN --plain)
uv publish --token "${PYPI_TOKEN}" 2>&1 | grep -E "(Uploading|succeeded|Failed)" || \
  uv publish --token "${PYPI_TOKEN}"
echo "   ✅ Published to PyPI"

# Step 5: Verify
echo -e "\n🔍 Step 5: Verifying on PyPI..."
sleep 3
curl -s https://pypi.org/pypi/gapless-crypto-clickhouse/${CURRENT_VERSION}/json > /dev/null 2>&1 && \
  echo "   ✅ Verified: https://pypi.org/project/gapless-crypto-clickhouse/${CURRENT_VERSION}/" || \
  echo "   ⏳ Still propagating (check in 30 seconds)"

echo -e "\n✅ Complete! Published v${CURRENT_VERSION} to PyPI"
