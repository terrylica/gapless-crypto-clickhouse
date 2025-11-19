# PyPI Package Fork Implementation Plan

**Author**: Claude Code (Eon Labs)
**Created**: 2025-11-18
**Updated**: 2025-11-18
**Status**: Implementation
**ADR**: [ADR-0011](../../decisions/0011-pypi-package-fork-clickhouse.md) (adr-id=0011)

---

## Summary

Fork `main-clickhouse` branch as independent `gapless-crypto-clickhouse` PyPI package with separate repository, full module rename, and version reset to 1.0.0. Enable external user feedback for ClickHouse implementation without disrupting mature `gapless-crypto-data` (v3.3.0).

**Scope**:
- New GitHub repository: `terrylica/gapless-crypto-clickhouse`
- Module rename: `gapless_crypto_data` → `gapless_crypto_clickhouse`
- Package rename: `gapless-crypto-data` → `gapless-crypto-clickhouse`
- Version reset: 4.0.0 → 1.0.0
- ~150 files updated (source, tests, examples, documentation)

**Out of Scope**:
- Migration guide for v3.3.0 users (no migration needed - fork for new users)
- Deprecation of original package (both packages actively maintained)
- Cross-package dependencies (accept code duplication)

---

## Background

### Problem

Current `main-clickhouse` branch (v4.0.0) diverged 44 commits from `origin/main` (v3.3.0) with incompatible architecture:

| Aspect | origin/main (v3.3.0) | main-clickhouse (v4.0.0) |
|--------|----------------------|---------------------------|
| **Database** | None (CSV-only) | ClickHouse ReplacingMergeTree |
| **Python** | 3.9-3.13 | 3.12-3.13 only |
| **CLI** | Present | Removed |
| **Dependencies** | httpx, pandas, duckdb | + clickhouse-driver, python-dotenv |
| **Futures** | No | Yes (USDT-margined) |

Publishing both as `gapless-crypto-data` creates package identity collision on PyPI.

### Goals

1. **Independent Distribution**: Publish ClickHouse implementation for external feedback
2. **Zero Disruption**: Existing v3.3.0 users unaffected
3. **Clear Positioning**: Users understand which package suits their use case (file-based vs database-first)
4. **Maintainability**: Standard workflows (separate repos, Trusted Publishing)

### Non-Goals

- Merging v3.x and v4.x codebases
- Creating migration path from v3.3.0 to v4.0.0
- Shared code extraction to third package
- Monorepo architecture

---

## Design

### Repository Strategy

**Approach**: Separate repository (`terrylica/gapless-crypto-clickhouse`)

**Rationale**:
- Clearest separation of concerns (file-based vs database-first)
- Standard GitHub workflow (no custom CI/CD logic)
- Independent stars, issues, releases
- Simpler PyPI Trusted Publishing configuration

**Alternatives Rejected**:
- Monorepo: Complex CI/CD triggers, path-based workflow detection
- Git worktree: Package name collision, shared `.gitignore`, manual lifecycle management

### Module Naming

**Approach**: Full rename `gapless_crypto_data` → `gapless_crypto_clickhouse`

**Rationale**:
- Matches PyPI name convention (kebab → snake_case)
- Prevents import confusion between packages
- Clear ClickHouse branding in code

**Breaking Change**: All import paths change
- Before: `import gapless_crypto_data as gcd`
- After: `import gapless_crypto_clickhouse as gcc`

### Version Strategy

**Approach**: Reset to v1.0.0 (fresh start)

**Rationale**:
- New package identity = new version lifecycle
- Independent semantic versioning (no coupling to v3.x/v4.x)
- Industry standard for forks/spinoffs
- Clear signal: not a continuation of `gapless-crypto-data`

### Code Sharing Strategy

**Approach**: Copy shared utilities, accept duplication

**Shared Code** (~4 files, ~800 lines):
- `api.py` (function-based API)
- `utils/` (etag_cache, error_handling, etc.)
- `gap_filling/` (universal gap filler)
- `collectors/binance_public_data_collector.py`

**Rationale**:
- No cross-package dependencies
- Simpler deployment (no version coupling)
- Faster iteration (no coordinated releases)
- Can extract to `gapless-crypto-core` later if duplication becomes painful

**Trade-off**: Bug fixes must be manually synced between packages

---

## Implementation Plan

### Phase 1: Repository Creation (Local Preparation)

**Objective**: Create new repository structure in separate directory

**Steps**:
1. Create directory: `/Users/terryli/eon/gapless-crypto-clickhouse/`
2. Copy all files from `main-clickhouse` branch
3. Initialize git: `git init && git remote add origin git@github.com:terrylica/gapless-crypto-clickhouse.git`

**Deliverables**:
- New directory with complete codebase copy
- Git initialized (not yet pushed)

**Validation**: Directory exists with all files present

---

### Phase 2: Module Rename

**Objective**: Rename Python package directory and update all imports

**Steps**:

1. **Rename directory**:
   ```bash
   mv src/gapless_crypto_data src/gapless_crypto_clickhouse
   ```

2. **Update imports in source files** (~28 files):
   - Pattern: `from gapless_crypto_data` → `from gapless_crypto_clickhouse`
   - Files: All `.py` files in `src/gapless_crypto_clickhouse/`

3. **Update imports in test files** (~21 files):
   - Pattern: Same as source files
   - Files: All `.py` files in `tests/`

4. **Update imports in example files** (~6 files):
   - Pattern: Same as source files
   - Files: All `.py` files in `examples/`

**Deliverables**:
- Renamed module directory: `src/gapless_crypto_clickhouse/`
- All import statements updated

**Validation**:
```bash
# Check no old imports remain
grep -r "from gapless_crypto_data" src/ tests/ examples/
grep -r "import gapless_crypto_data" src/ tests/ examples/
# Expected: No matches
```

---

### Phase 3: Package Metadata Update

**Objective**: Update `pyproject.toml` with new package identity

**Changes**:

| Field | Before | After |
|-------|--------|-------|
| `name` | `gapless-crypto-data` | `gapless-crypto-clickhouse` |
| `version` | `4.0.0` | `1.0.0` |
| `description` | Generic crypto data | ClickHouse-based cryptocurrency data collection |
| `keywords` | crypto, binance, data | clickhouse, crypto, binance, database, time-series |
| `packages` | `["src/gapless_crypto_data"]` | `["src/gapless_crypto_clickhouse"]` |
| GitHub URLs | `gapless-crypto-data` | `gapless-crypto-clickhouse` |
| `known-first-party` | `["gapless_crypto_data"]` | `["gapless_crypto_clickhouse"]` |

**Dependencies** (keep minimal for ClickHouse focus):
- Keep: `clickhouse-driver`, `pandas`, `pyarrow`, `python-dotenv`
- Consider removing: `duckdb` (validation only), `httpx` (not core to ClickHouse)

**Deliverables**: Updated `pyproject.toml`

**Validation**: `uv build` succeeds, package name is `gapless_crypto_clickhouse-1.0.0-py3-none-any.whl`

---

### Phase 4: Documentation Updates

**Objective**: Update all documentation with new package identity

**Critical Files**:

1. **README.md** (50+ changes):
   - Title: `# Gapless Crypto ClickHouse`
   - Installation: `pip install gapless-crypto-clickhouse`
   - Imports: `import gapless_crypto_clickhouse as gcc`
   - Add positioning section: "When to use this package"
   - Cross-reference: Link to `gapless-crypto-data` for file-based workflows

2. **CLAUDE.md**:
   - Project overview: Update package name
   - Repository paths: Update to new repo URL

3. **llms.txt**:
   - Package name, imports, PyPI URL, GitHub URL

4. **DOCUMENTATION.md**:
   - Version number: 4.0.0 → 1.0.0
   - Package name throughout

**Medium-Priority Files** (~100 files in `docs/`):
- All ADRs referencing package name
- All guides (`docs/guides/`)
- All development docs (`docs/development/`)

**Low-Priority Files**:
- `CHANGELOG.md`: Consider fresh start or fork history
- Milestone docs: Selectively apply relevant history

**Deliverables**: All documentation updated

**Validation**: `grep -r "gapless-crypto-data" docs/` returns zero matches (excluding historical context)

---

### Phase 5: Configuration & Deployment Files

**Objective**: Update deployment configurations for new package

**Files**:

1. **docker-compose.yml**:
   - Volume paths: Update to `gapless_crypto_clickhouse`
   - Container names: Already standardized to `gapless-clickhouse`

2. **deployment/systemd/gapless-crypto-collector.service**:
   - Module path: `python -m gapless_crypto_clickhouse.collectors...`

3. **.github/workflows/publish.yml**:
   - Package name references (if any)
   - Workflow already uses `uv build` (auto-detects from pyproject.toml)

4. **.github/workflows/publish-testpypi.yml** (new file):
   - Create TestPyPI validation workflow
   - Trigger: Push to main
   - Publishes to https://test.pypi.org

**Deliverables**:
- Updated deployment configs
- New TestPyPI workflow

**Validation**: `docker-compose up -d` succeeds, workflows pass linting

---

### Phase 6: Validation & Testing

**Objective**: Comprehensive validation before publishing

**Automated Checks**:

1. **Grep validation** (zero old references):
   ```bash
   grep -r "gapless-crypto-data" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules
   grep -r "gapless_crypto_data" . --exclude-dir=.git --exclude-dir=.venv
   ```
   Expected: Only historical references in CHANGELOGs/ADRs

2. **Import validation**:
   ```bash
   python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"
   ```
   Expected: `1.0.0`

3. **Test suite**:
   ```bash
   uv run pytest tests/ -v
   ```
   Expected: All tests pass

4. **Build validation**:
   ```bash
   uv build
   ls -lh dist/
   ```
   Expected: `gapless_crypto_clickhouse-1.0.0-py3-none-any.whl`

**Manual Checks**:
- [ ] README renders correctly (check Markdown)
- [ ] All example code runs without errors
- [ ] ClickHouse integration works (`docker-compose up -d` → ingest → query)

**Deliverables**: All validations pass

---

### Phase 7: PyPI Trusted Publishing Setup

**Objective**: Configure Trusted Publishing for secure PyPI deployment

**Steps**:

1. **Create GitHub repository** (Web UI or `gh` CLI):
   ```bash
   gh repo create terrylica/gapless-crypto-clickhouse --public \
     --description "ClickHouse-based cryptocurrency data collection with zero-gap guarantee"
   ```

2. **Register TestPyPI Trusted Publisher**:
   - URL: https://test.pypi.org/manage/account/publishing/
   - Package: `gapless-crypto-clickhouse`
   - Owner: `terrylica`
   - Repository: `gapless-crypto-clickhouse`
   - Workflow: `publish-testpypi.yml`
   - Environment: `testpypi`

3. **Register Production PyPI Trusted Publisher**:
   - URL: https://pypi.org/manage/account/publishing/
   - Same details, but `environment: pypi`

4. **Push code to GitHub**:
   ```bash
   git add .
   git commit -m "chore: fork from gapless-crypto-data main-clickhouse branch"
   git push -u origin main
   ```

**Deliverables**:
- GitHub repository live
- PyPI Trusted Publishers registered
- Code pushed to GitHub

**Validation**: GitHub Actions workflow triggers, TestPyPI publish succeeds

---

### Phase 8: TestPyPI Validation

**Objective**: Validate package on TestPyPI before production

**Steps**:

1. **Monitor GitHub Actions**: Workflow `publish-testpypi.yml` runs on push to main

2. **Install from TestPyPI**:
   ```bash
   pip install -i https://test.pypi.org/simple/ gapless-crypto-clickhouse
   ```

3. **Test installation**:
   ```bash
   python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"
   # Expected: 1.0.0
   ```

4. **Verify TestPyPI page**:
   - URL: https://test.pypi.org/project/gapless-crypto-clickhouse/
   - Check: README renders, metadata correct, classifiers appropriate

**Deliverables**: Successful TestPyPI installation and validation

**Validation**: Package installs, imports work, README renders

---

### Phase 9: Production PyPI Publish

**Objective**: Publish v1.0.0 to production PyPI

**Steps**:

1. **Create git tag**:
   ```bash
   git tag -a v1.0.0 -m "feat: initial release of gapless-crypto-clickhouse

   ClickHouse-based cryptocurrency data collection forked from gapless-crypto-data.

   Features:
   - USDT-margined futures support
   - ReplacingMergeTree with deterministic versioning
   - Zero-gap guarantee via ClickHouse
   - Production-ready schema validated at 108M rows"

   git push origin v1.0.0
   ```

2. **Create GitHub Release** (Web UI):
   - Go to: https://github.com/terrylica/gapless-crypto-clickhouse/releases/new
   - Tag: `v1.0.0`
   - Title: `v1.0.0 - Initial Release`
   - Description: Copy from tag message
   - Click "Publish release"

3. **Monitor Workflow**: `.github/workflows/publish.yml` triggers on release

4. **Verify Production PyPI**:
   - URL: https://pypi.org/project/gapless-crypto-clickhouse/
   - Check: Package live, README renders, installable

**Deliverables**: v1.0.0 published to PyPI

**Validation**:
```bash
pip install gapless-crypto-clickhouse
python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"
# Expected: 1.0.0
```

---

### Phase 10: Documentation & Announcement

**Objective**: Update related documentation and communicate release

**Steps**:

1. **Update original package README** (in `terrylica/gapless-crypto-data`):
   Add section:
   ```markdown
   ## Related Packages

   For ClickHouse database workflows, see [gapless-crypto-clickhouse](https://pypi.org/project/gapless-crypto-clickhouse/) - optimized for persistent storage, multi-symbol queries, and production data pipelines.
   ```

2. **Create GitHub Discussion** (in `gapless-crypto-clickhouse`):
   - Title: "gapless-crypto-clickhouse v1.0.0 Released"
   - Content: Explain fork strategy, positioning, when to use

3. **Update PyPI classifiers** (if needed):
   - Ensure `Development Status :: 4 - Beta` is appropriate
   - Verify all classifiers accurate

**Deliverables**:
- Cross-reference in original package
- Announcement published

**Validation**: Community can discover both packages clearly

---

## SLO Compliance

### Availability

**Metric**: PyPI package availability
**Target**: 99.9% (inherits from PyPI SLA)
**Implementation**: PyPI Trusted Publishing (OIDC) ensures consistent upload workflow
**Monitoring**: GitHub Actions workflow status, PyPI package status page

### Correctness

**Metric**: Package rename completeness
**Target**: Zero old package references in public-facing code
**Implementation**: Automated grep validation in CI/CD
**Validation**: `grep -r "gapless-crypto-data"` returns only historical ADR/CHANGELOG references

### Observability

**Metric**: Pre-production feedback via TestPyPI
**Target**: All commits to main validate on TestPyPI before production
**Implementation**: `.github/workflows/publish-testpypi.yml` runs on every push
**Monitoring**: TestPyPI installation success rate

### Maintainability

**Metric**: Documentation completeness
**Target**: All 150+ files updated with new package identity
**Implementation**: Systematic file-by-file updates with validation
**Validation**: `grep` checks + manual review of critical files (README, CLAUDE.md, pyproject.toml)

---

## Error Handling

### Build Failures

**Policy**: Raise and propagate (fail CI/CD pipeline)
**Implementation**: `uv build` exit code checked in GitHub Actions
**No Fallback**: Do not publish partial builds or skip validation steps

### Import Errors

**Policy**: Fail fast (no silent module import failures)
**Implementation**: Test suite imports all modules explicitly
**No Default**: Do not provide fallback imports or compatibility shims

### Publishing Failures

**Policy**: Halt deployment (no partial publishes)
**Implementation**: GitHub Actions `fail-fast: true` (default)
**No Retry**: Manual investigation required if publish fails

---

## OSS Library Preference

**Rationale**: Use community-maintained tools over custom implementations

**Build System**: Hatchling (via UV) - not custom build scripts
**Publishing**: `pypa/gh-action-pypi-publish` - not custom `twine` invocations
**Version Management**: `semantic-release` - not manual version bumping
**Python Management**: UV - not custom virtualenv setup
**CI/CD**: GitHub Actions - not custom Jenkins/CircleCI

---

## Validation Checklist

**Pre-Publish** (Phase 6):
- [ ] `grep -r "gapless-crypto-data"` returns only historical references
- [ ] `grep -r "gapless_crypto_data"` returns only historical references
- [ ] `python -c "import gapless_crypto_clickhouse"` succeeds
- [ ] `uv run pytest tests/ -v` passes
- [ ] `uv build` creates `gapless_crypto_clickhouse-1.0.0-py3-none-any.whl`

**TestPyPI** (Phase 8):
- [ ] `pip install -i https://test.pypi.org/simple/ gapless-crypto-clickhouse` succeeds
- [ ] TestPyPI README renders correctly
- [ ] TestPyPI metadata accurate

**Production PyPI** (Phase 9):
- [ ] `pip install gapless-crypto-clickhouse` succeeds
- [ ] PyPI README renders correctly
- [ ] Package metadata accurate
- [ ] GitHub release created

**Post-Publish** (Phase 10):
- [ ] Original package README updated with cross-reference
- [ ] Announcement published
- [ ] Both packages clearly positioned

---

## Rollback Plan

### If TestPyPI Validation Fails

**Action**: Fix issues, commit, push again (TestPyPI allows re-uploads)
**Impact**: Zero (production not affected)

### If Production PyPI Publish Fails Mid-Workflow

**Action**: Delete failed release tag, fix issues, re-tag and re-release
**Impact**: Low (package not yet discoverable on PyPI)
**Note**: Cannot delete PyPI packages once published (only yank versions)

### If Post-Publish Issues Discovered

**Action**: Publish v1.0.1 with fixes (semantic versioning patch release)
**Impact**: Low (users can pin to v1.0.1)
**Note**: Cannot unpublish v1.0.0 (PyPI policy), can only yank

---

## Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Repository Creation | 15 min | None |
| 2. Module Rename | 30 min | Phase 1 |
| 3. Package Metadata | 15 min | Phase 2 |
| 4. Documentation | 60 min | Phase 3 |
| 5. Configs | 15 min | Phase 4 |
| 6. Validation | 30 min | Phase 5 |
| 7. PyPI Setup | 15 min | Phase 6 |
| 8. TestPyPI | 20 min | Phase 7 |
| 9. Production | 10 min | Phase 8 |
| 10. Announcement | 10 min | Phase 9 |

**Total**: ~3.5 hours (recommend single work session for atomicity)

---

## Success Criteria

**Definition of Done**:
1. ✅ New repository `terrylica/gapless-crypto-clickhouse` live on GitHub
2. ✅ Package `gapless-crypto-clickhouse==1.0.0` published to PyPI
3. ✅ Zero `gapless-crypto-data` references in codebase (excluding historical docs)
4. ✅ All tests pass with new imports
5. ✅ TestPyPI validation successful before production
6. ✅ README clearly positions package (ClickHouse-first vs file-based)
7. ✅ Cross-reference added to original package README
8. ✅ PyPI Trusted Publishing configured (no API tokens)

**Acceptance Test**:
```bash
# From clean environment
pip install gapless-crypto-clickhouse
python -c "
import gapless_crypto_clickhouse as gcc
print(f'Version: {gcc.__version__}')
print(f'Package: {gcc.__name__}')
assert gcc.__version__ == '1.0.0'
assert 'gapless_crypto_clickhouse' in gcc.__name__
"
```

---

## References

- **ADR-0011**: [PyPI Package Fork for ClickHouse Distribution](../../decisions/0011-pypi-package-fork-clickhouse.md)
- **Agent Reports**: `tmp/pypi-package-split/` (5-agent parallel investigation)
- **ADR-0005**: ClickHouse Migration (context for v4.0.0)
- **PyPI Trusted Publishing**: https://docs.pypi.org/trusted-publishers/
- **Semantic Release**: https://semantic-release.gitbook.io/
