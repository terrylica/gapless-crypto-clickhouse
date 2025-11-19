# ADR-0011: PyPI Package Fork for ClickHouse Distribution

## Status

Proposed (2025-11-18)

## Context

### Problem Statement

Current main-clickhouse branch (v4.0.0) contains ClickHouse integration incompatible with origin/main (v3.3.0 CSV-only). User requires publishing ClickHouse-based implementation as separate PyPI package `gapless-crypto-clickhouse` to:

1. Obtain feedback from external users without affecting mature `gapless-crypto-data` package
2. Maintain independent version lifecycle for ClickHouse implementation
3. Allow parallel evolution of file-based (v3.x) and database-first (v4.x) approaches

**Current State**:
- **origin/main (v3.3.0)**: CSV-only collection, no database, Python 3.9-3.13, CLI present
- **main-clickhouse (v4.0.0)**: ClickHouse integration, Python 3.12-3.13 only, CLI removed, 44 commits divergence
- **Package collision**: Both branches would publish as `gapless-crypto-data` on PyPI

### Constraints

1. **Zero disruption**: Existing users of v3.3.0 must continue unaffected
2. **Independent lifecycle**: ClickHouse package must evolve without coupling to v3.x versioning
3. **Clear positioning**: Users must understand which package suits their use case
4. **Minimal maintenance overhead**: Avoid complex monorepo tooling or cross-package dependencies
5. **Standard workflows**: Use industry-standard approaches (separate repos, Trusted Publishing)

## Decision

**Fork main-clickhouse as independent `gapless-crypto-clickhouse` PyPI package** with separate GitHub repository, full module rename, and version reset to 1.0.0.

### Key Decisions

1. **Repository Strategy**: Separate repository (`terrylica/gapless-crypto-clickhouse`)
   - Rationale: Cleanest separation, standard GitHub workflow, independent stars/issues/releases

2. **Module Rename**: `gapless_crypto_data` → `gapless_crypto_clickhouse`
   - Rationale: Matches PyPI name convention, clear ClickHouse branding, prevents import confusion

3. **Version Numbering**: Start at v1.0.0 (fresh start)
   - Rationale: New package identity, independent semantic versioning lifecycle

4. **Code Sharing**: Copy shared utilities, accept duplication
   - Rationale: No cross-package dependencies, simpler deployment, faster iteration

5. **Package Relationship**: Fork (not evolution/alternative)
   - Rationale: Both packages actively maintained, users choose based on use case (file-based vs database-first)

## Implementation

### Repository Creation

```bash
# Create new GitHub repository
gh repo create terrylica/gapless-crypto-clickhouse --public

# Clone and initialize
cd /Users/terryli/eon/
git clone git@github.com:terrylica/gapless-crypto-clickhouse.git
cd gapless-crypto-clickhouse

# Copy from main-clickhouse branch
cp -r ../gapless-crypto-data/* .
cp -r ../gapless-crypto-data/.github .
```

### Module Rename

```bash
# Rename Python package directory
mv src/gapless_crypto_data src/gapless_crypto_clickhouse
```

**Files requiring import updates** (~150 files):
- All source files: `from gapless_crypto_data` → `from gapless_crypto_clickhouse`
- All test files: Update imports
- All examples: Update imports
- All documentation: Update package name references

### Package Metadata Changes

**pyproject.toml**:
```toml
[project]
name = "gapless-crypto-clickhouse"  # Changed from gapless-crypto-data
version = "1.0.0"  # Reset from 4.0.0
description = "ClickHouse-based cryptocurrency data collection..."
keywords = ["clickhouse", "cryptocurrency", "crypto", "binance", ...]
```

**Dependencies**:
- Keep: `clickhouse-driver`, `pandas`, `pyarrow`, `python-dotenv`
- Remove: `duckdb` (validation only, not needed for minimal package)
- Remove: `httpx` (not needed for ClickHouse-focused package)

### Publishing Infrastructure

**PyPI Trusted Publishing** (OIDC authentication):
1. Register at https://pypi.org/manage/account/publishing/
   - Package: `gapless-crypto-clickhouse`
   - Repository: `terrylica/gapless-crypto-clickhouse`
   - Workflow: `publish.yml`
   - Environment: `pypi`

2. TestPyPI validation before production:
   - Workflow: `.github/workflows/publish-testpypi.yml`
   - Trigger: Push to main
   - Validates: Build, installation, imports

**GitHub Actions Workflows**:
- `.github/workflows/publish.yml`: Production PyPI (on GitHub release)
- `.github/workflows/publish-testpypi.yml`: TestPyPI validation (on push to main)

### Documentation Strategy

**README.md positioning**:
- Lead with "ClickHouse-based cryptocurrency data collection"
- "When to use" decision matrix (database-first vs file-based)
- Cross-reference to `gapless-crypto-data` for file-based workflows
- No migration guides (fork for new users, not migration for existing users)

**AI Discoverability**:
- Update `llms.txt` with new package name, imports, URLs
- Update `CLAUDE.md` project overview
- Update `__probe__.py` metadata

## Validation

### Automated Checks

**Grep validation** (zero old references):
```bash
grep -r "gapless-crypto-data" . --exclude-dir=.git --exclude-dir=.venv
grep -r "gapless_crypto_data" . --exclude-dir=.git --exclude-dir=.venv
```

**Import validation**:
```bash
python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"
# Expected: 1.0.0
```

**Test suite**:
```bash
uv run pytest tests/ -v
# Expected: All tests pass with new import paths
```

**TestPyPI installation**:
```bash
pip install -i https://test.pypi.org/simple/ gapless-crypto-clickhouse
```

### Manual Checklist

- [ ] No `gapless-crypto-data` references in codebase
- [ ] No `gapless_crypto_data` imports in codebase
- [ ] All tests pass with new imports
- [ ] TestPyPI README renders correctly
- [ ] TestPyPI package installs successfully
- [ ] GitHub repository description updated
- [ ] PyPI Trusted Publisher registered

## Consequences

### Positive

- **Independent Evolution**: ClickHouse package can use Python 3.12+ features without affecting v3.x users
- **Clear Positioning**: Package name signals ClickHouse dependency (no surprises)
- **No Migration Pressure**: Existing users unaffected, new users choose based on use case
- **Standard Workflow**: Industry-standard approach (separate repos, Trusted Publishing)
- **Faster Iteration**: No version coupling or cross-package dependency management
- **Clean Branding**: Distinct GitHub repos with independent stars, issues, releases

### Negative

- **Code Duplication**: Shared utilities (~4 files) copied, must sync bug fixes manually
- **Maintenance Overhead**: Two repositories to maintain (can mitigate with clear ownership)
- **Breaking Change**: All import paths change for users migrating from v4.0.0 preview
- **Documentation Effort**: ~150 files require updates for package rename

### Neutral

- **Two Active Packages**: Both `gapless-crypto-data` and `gapless-crypto-clickhouse` receive updates independently
- **Version Reset**: v1.0.0 start signals new beginning (not continuation of v4.0.0)

## Alternatives Considered

### Alternative 1: Monorepo with Dual Packages

**Implementation**: Keep both in same repo with `packages/gapless-crypto-data/` and `packages/gapless-crypto-clickhouse/`

**Pros**: Shared git history, easier cross-package refactoring

**Cons**: Complex CI/CD triggers, path-based workflow detection, requires package rename anyway

**Verdict**: Rejected - adds complexity without solving core rename requirement

### Alternative 2: Keep Same Package Name

**Implementation**: Publish v4.0.0 as `gapless-crypto-data` with breaking ClickHouse dependency

**Pros**: No rename effort, simpler short-term

**Cons**: Misleading to users (hides database requirement), incompatible with Python 3.9-3.11 users, forces breaking upgrade

**Verdict**: Rejected - violates "zero disruption" constraint for existing users

### Alternative 3: Namespace Package

**Implementation**: `gapless.crypto.data` and `gapless.crypto.clickhouse` using PEP 420

**Pros**: Hierarchical organization, clear relationship

**Cons**: Overkill for 2 packages (better for 10+), confusing for beginners, non-standard for PyPI

**Verdict**: Rejected - adds complexity without significant benefit

## Compliance

- **Error Handling**: Raise and propagate (no fallback, no retry, no silent failures)
  - Import errors: Fail fast if `clickhouse-driver` missing
  - Connection errors: Propagate to caller (no automatic retry)
  - Build errors: Fail CI/CD pipeline (no partial publishes)

- **SLOs**:
  - **Availability**: PyPI Trusted Publishing ensures consistent publish workflow
  - **Correctness**: Automated validation (grep, imports, tests) prevents incomplete renames
  - **Observability**: TestPyPI validation provides pre-production feedback
  - **Maintainability**: Standard repo structure, conventional commits, semantic-release

- **OSS Preference**:
  - Use `pypa/gh-action-pypi-publish` (not custom upload scripts)
  - Use `astral-sh/setup-uv` (not manual UV installation)
  - Use GitHub Trusted Publishing (not API tokens)

- **Auto-Validation**:
  - TestPyPI workflow validates every push to main
  - Grep validation in CI/CD ensures complete rename
  - Test suite validates import paths

- **Semantic Release**:
  - Conventional commits: `feat: initial release of gapless-crypto-clickhouse`
  - GitHub release triggers production PyPI publish
  - Automated changelog generation

## References

- **Agent Reports**: See `tmp/pypi-package-split/` for 5-agent parallel investigation findings
- **Plan**: `docs/plan/0011-pypi-package-fork-clickhouse/plan.md`
- **ADR-0005**: ClickHouse Migration (context for v4.0.0 architecture)
- **ADR-0004**: Futures Support Implementation (ClickHouse-specific features)
- **PyPI Trusted Publishing**: https://docs.pypi.org/trusted-publishers/
- **PEP 621**: Storing project metadata in pyproject.toml

## Decision Makers

- Terry Li (2025-11-18)

## Approval Date

2025-11-18 (pending implementation)
