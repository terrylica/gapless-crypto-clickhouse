#!/bin/bash
# Quick PyPI Publishing Script
# Usage: ./scripts/publish-to-pypi.sh

set -e

echo "🚀 Publishing to PyPI (Local Workflow)"
echo "======================================"

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
uv build
echo "   ✅ Built: dist/gapless_crypto_clickhouse-${CURRENT_VERSION}*"

# Step 4: Publish to PyPI
echo -e "\n📤 Step 4: Publishing to PyPI..."
echo "   Using credentials from ~/.pypirc"
uv publish
echo "   ✅ Published to PyPI"

echo -e "\n✅ Complete! Published v${CURRENT_VERSION} to PyPI"
echo "   View at: https://pypi.org/project/gapless-crypto-clickhouse/${CURRENT_VERSION}/"
