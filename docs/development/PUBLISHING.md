---
version: "1.0.0"
last_updated: "2025-10-28"
canonical_source: true
supersedes: []
---

# Publishing Guide: Automated PyPI Publishing with GitHub Actions

This guide explains how to set up secure, automated publishing to PyPI using GitHub Actions with Trusted Publishing (OIDC).

## 🔐 Security Overview

This setup uses **Trusted Publishing** - the most secure method for PyPI publishing in 2025:

- ✅ No long-lived API tokens stored anywhere
- ✅ Short-lived OIDC tokens exchanged automatically
- ✅ Digital attestations with Sigstore signatures
- ✅ Environment-based manual approval for production releases

## 📋 Setup Checklist

### 1. Configure PyPI Trusted Publishing

#### For PyPI (Production)

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new trusted publisher with these details:
   - **PyPI project name**: `gapless-crypto-data`
   - **Owner**: `terrylica` (your GitHub username)
   - **Repository name**: `gapless-crypto-data`
   - **Workflow filename**: `publish.yml`
   - **Environment name**: `pypi`

#### For TestPyPI (Testing)

1. Go to https://test.pypi.org/manage/account/publishing/
2. Add a new trusted publisher with these details:
   - **TestPyPI project name**: `gapless-crypto-data`
   - **Owner**: `terrylica` (your GitHub username)
   - **Repository name**: `gapless-crypto-data`
   - **Workflow filename**: `publish.yml`
   - **Environment name**: `testpypi`

### 2. Create GitHub Environments

#### Create PyPI Environment (Production)

1. Go to your repository: https://github.com/terrylica/gapless-crypto-data
2. Navigate to **Settings** → **Environments**
3. Click **New Environment** and name it `pypi`
4. Configure protection rules:
   - ✅ **Required reviewers**: Add yourself as a required reviewer
   - ✅ **Wait timer**: 0 minutes (optional)
   - ✅ **Prevent self-review**: Unchecked (since you're the sole maintainer)

#### Create TestPyPI Environment (Testing)

1. Click **New Environment** and name it `testpypi`
2. No protection rules needed (auto-publishes on main branch pushes)

### 3. Repository Secrets (Not Needed)

❌ **No secrets required!** Trusted Publishing eliminates the need for API tokens.

## 🚀 Publishing Workflows

### Automatic TestPyPI Publishing

- **Trigger**: Every push to `main` branch
- **Purpose**: Test releases and validation
- **URL**: https://test.pypi.org/p/gapless-crypto-data
- **Installation**: `pip install -i https://test.pypi.org/simple/ gapless-crypto-data`

### Manual PyPI Publishing

- **Trigger**: GitHub release creation
- **Purpose**: Production releases
- **Approval**: Requires manual approval in `pypi` environment
- **URL**: https://pypi.org/p/gapless-crypto-data
- **Installation**: `pip install gapless-crypto-data`

## 📦 Release Process

### 1. Prepare Release

```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Commit changes
git add .
git commit -m "chore: prepare release v1.0.1"
git push origin main
```

### 2. Create GitHub Release

```bash
# Create and push tag
git tag v1.0.1
git push origin v1.0.1

# Or use GitHub web interface:
# 1. Go to Releases → Create a new release
# 2. Choose tag: v1.0.1 (create new tag)
# 3. Release title: "v1.0.1"
# 4. Generate release notes automatically
# 5. Click "Publish release"
```

### 3. Approve PyPI Publication

1. GitHub Actions will start the `publish-to-pypi` job
2. Navigate to **Actions** tab in your repository
3. Click on the running workflow
4. Click **Review deployments**
5. Select `pypi` environment and click **Approve and deploy**

## 🔍 Monitoring & Verification

### Workflow Status

- **TestPyPI**: Check https://github.com/terrylica/gapless-crypto-data/actions
- **PyPI**: Monitor the `publish-to-pypi` job for approval requests

### Package Verification

```bash
# Verify TestPyPI upload
pip install -i https://test.pypi.org/simple/ gapless-crypto-data==<version>

# Verify PyPI upload
pip install gapless-crypto-data==<version>

# Test installation
python -c "from gapless_crypto_data import BinancePublicDataCollector; print('✅ Import successful')"
```

### Digital Attestations

- Automatic signing with Sigstore
- Attestations visible on PyPI package pages
- Release artifacts include `.sigstore` signature files

## 🛡️ Security Features

### Built-in Protections

- **OIDC Authentication**: No long-lived tokens
- **Environment Approval**: Manual review for production
- **Workflow Isolation**: Separate build/publish jobs
- **Digital Signatures**: Sigstore attestations
- **Audit Trail**: Complete GitHub Actions logs

### Best Practices Implemented

- ✅ Per-job permissions (minimal privilege)
- ✅ Pinned Action versions for reproducibility
- ✅ Separate environments for testing/production
- ✅ Comprehensive validation before publishing
- ✅ File encoding validation (UTF-8/ASCII only)
- ✅ Automated linting and testing

## 🔧 Troubleshooting

### Common Issues

#### "Trusted publishing exchange failure"

- Verify PyPI trusted publisher configuration
- Check environment name matches exactly: `pypi` or `testpypi`
- Ensure workflow filename is `publish.yml`

#### "Missing id-token permission"

- Confirm `permissions: id-token: write` is set
- Check per-job permissions in workflow

#### "Environment protection rules"

- Verify you're added as a required reviewer for `pypi` environment
- Check environment name spelling in workflow

### Debug Commands

```bash
# Check workflow syntax
yamllint .github/workflows/publish.yml

# Validate package build locally
uv build
twine check dist/*

# Test upload to TestPyPI (manual backup)
uv publish --repository testpypi
```

## 📚 References

- [PyPI Trusted Publishing Documentation](https://docs.pypi.org/trusted-publishers/)
- [GitHub Actions Publishing Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- [pypa/gh-action-pypi-publish](https://github.com/pypa/gh-action-pypi-publish)
- [Sigstore Python](https://github.com/sigstore/sigstore-python)

---

✨ **Result**: Secure, automated PyPI publishing with zero stored credentials and production-grade protections.
