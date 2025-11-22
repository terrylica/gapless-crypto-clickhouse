---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Development Commands Reference

## Purpose

Complete command reference for testing, code quality, building, and CI/CD workflows.

## Testing Commands

### Full Test Suite

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=src/gapless_crypto_clickhouse --cov-report=html
```

**Expected**: 30+ tests pass, 85%+ coverage for SDK entry points

### Specific Test Files

```bash
# Run collector tests
uv run pytest tests/test_binance_collector.py -v

# Run gap filler tests
uv run pytest tests/test_gap_filler.py -v

# Run validation tests
uv run pytest tests/test_validation_storage.py -v
```

### Test Markers

```bash
# Run unit tests only
uv run pytest -m unit

# Run integration tests only
uv run pytest -m integration

# Skip integration tests
uv run pytest -m "not integration"
```

**Markers**:

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (use real data)

### E2E Testing

```bash
# Full E2E suite (requires Docker services)
docker-compose up -d
uv run pytest tests/e2e/ -v

# E2E validation script (PEP 723 bootstrap)
uv run scripts/run_validation.py

# E2E only via marker
uv run pytest -m e2e -v

# ClickHouse Play only (CI subset)
uv run pytest tests/e2e/test_clickhouse_play.py -v

# With screenshots and tracing
uv run pytest tests/e2e/ -v --screenshot=only-on-failure --tracing=retain-on-failure
```

**Markers**: `@pytest.mark.e2e` - End-to-end tests requiring Playwright and running services

**Services Required**:

- ClickHouse: localhost:8123 (HTTP), localhost:9000 (native)
- CH-UI: localhost:5521 (web interface, local testing only)

**Note**: CI runs ClickHouse Play tests only (CH-UI requires interactive config). Full 12-test suite available locally.

### CLI Functionality Tests

```bash
# Test CLI help
uv run gapless-crypto-data --help

# Test basic collection
uv run gapless-crypto-data --symbol SOLUSDT --timeframes 1h --start 2024-01-01 --end 2024-01-02

# Test gap filling
uv run gapless-crypto-data --fill-gaps --directory ./sample_data

# Test multi-symbol support
uv run gapless-crypto-data --symbol BTCUSDT,ETHUSDT --timeframes 1h,4h
```

## Code Quality Commands

### Formatting (Ruff)

```bash
# Format all code
uv run ruff format .

# Check formatting without changes
uv run ruff format --check .

# Format specific directory
uv run ruff format src/gapless_crypto_clickhouse/
```

**Standard**: Ruff default formatting (PEP 8 compatible, Black-style)

### Linting (Ruff)

```bash
# Lint and auto-fix issues
uv run ruff check --fix .

# Lint without auto-fix (CI mode)
uv run ruff check .

# Lint specific file
uv run ruff check src/gapless_crypto_clickhouse/collectors/binance_public_data_collector.py

# Show all violations (including fixed)
uv run ruff check --diff .
```

**Ruleset**: Ruff default (pycodestyle, pyflakes, isort, pydocstyle subset)

**Key rules**:

- E/W - pycodestyle (PEP 8 style)
- F - pyflakes (logical errors)
- I - isort (import sorting)
- N - pep8-naming (naming conventions)

### Type Checking (mypy)

```bash
# Type check entire codebase
uv run mypy src/

# Type check with strict mode
uv run mypy --strict src/gapless_crypto_clickhouse/

# Type check specific module
uv run mypy src/gapless_crypto_clickhouse/validation/

# Show error codes
uv run mypy --show-error-codes src/
```

**Standard**: PEP 561 compliance via `py.typed` marker

**Configuration**: `pyproject.toml` → `[tool.mypy]`

### File Encoding Validation

Required for CI to pass:

```bash
# Validate all Python and Markdown files are UTF-8
find src/ tests/ examples/ -name "*.py" -o -name "*.md" | xargs file --mime-encoding
```

**Expected**: All files report `us-ascii` or `utf-8` (no `iso-8859-1` or other encodings)

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run hooks on all files
uv run pre-commit run --all-files

# Run specific hook
uv run pre-commit run ruff --all-files

# Update hook versions
uv run pre-commit autoupdate
```

**Hooks**:

- ruff format (code formatting)
- ruff check (linting)
- trailing-whitespace (file cleanup)
- end-of-file-fixer (file cleanup)
- check-yaml (YAML validation)

## Build Commands

### Package Building

```bash
# Build source distribution and wheel
uv build

# Build wheel only
uv build --wheel

# Build source distribution only
uv build --sdist
```

**Output**: `dist/` directory with `.whl` and `.tar.gz` files

**Version**: Extracted from `src/gapless_crypto_clickhouse/__init__.py`

### Local Installation

```bash
# Install editable package
uv tool install --editable .

# Verify CLI is installed
gapless-crypto-data --version

# Uninstall
uv tool uninstall gapless-crypto-data
```

**Use case**: Testing CLI before publishing

### Dependency Management

```bash
# Update dependencies
uv sync --upgrade

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>

# Remove dependency
uv remove <package-name>

# Lock dependencies without installing
uv lock
```

**Lock file**: `uv.lock` (auto-generated, committed to repo)

## CI/CD Commands

### GitHub Actions Workflows

**Location**: `.github/workflows/`

#### CI Pipeline (`ci-cd.yml`)

**Triggers**:

- Push to `main` or `develop` branches
- Pull requests to `main`

**Jobs**:

1. **Test** (Python 3.9-3.12 matrix)
   - Install dependencies (`uv sync --dev`)
   - Run pytest
   - Upload coverage

2. **Lint**
   - Run ruff format check
   - Run ruff check

3. **Type Check**
   - Run mypy on `src/`

4. **Encoding Check**
   - Validate UTF-8 encoding

5. **CLI Test**
   - Test `--help` and basic collection

6. **Build**
   - Build package with `uv build`
   - Verify wheel integrity

**IMPORTANT**: Automated PyPI publishing was removed in v3.0.0 (ADR-0027).

**Workspace Policy**: Local-only PyPI publishing enforced across all repositories.

**Current Workflow**:

1. **GitHub Actions** (`.github/workflows/release.yml`): Automated versioning ONLY
   - Analyzes conventional commits
   - Updates versions in pyproject.toml, package.json
   - Creates GitHub release and tag
   - Generates CHANGELOG.md

2. **Local Publishing** (`./scripts/publish-to-pypi.sh`): Manual PyPI upload
   - Pulls latest release commit
   - Builds package locally
   - Publishes to PyPI with Doppler credentials
   - CI detection guards prevent accidental CI execution

**See**: [PUBLISHING.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/PUBLISHING.md) for complete workflow.

---

### Local CI Simulation

```bash
# Run all CI checks locally
uv run ruff format --check .
uv run ruff check .
uv run mypy src/
uv run pytest -v
find src/ tests/ examples/ -name "*.py" -o -name "*.md" | xargs file --mime-encoding
uv build
```

**Use case**: Verify changes before pushing (catch CI failures early)

### PyPI Publishing

**Canonical Guide**: See [PUBLISHING.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/PUBLISHING.md) for complete workflow.

**Quick Reference** (Local-Only Publishing):

```bash
# After GitHub Actions completes versioning
git pull origin main

# Publish using Doppler-managed credentials
./scripts/publish-to-pypi.sh
```

**Key Points**:

- ✅ Uses Doppler for credential management (no plaintext tokens)
- ✅ CI detection guards prevent accidental CI publishing
- ✅ Repository verification prevents fork abuse
- ✅ ~30 seconds locally vs 3-5 minutes in CI

**Why Local-Only?** See [ADR-0027](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/decisions/0027-local-only-pypi-publishing.md) for architectural decision.

## Performance Profiling

### Memory Profiling

```bash
# Install memory profiler
uv add --dev memory-profiler

# Profile script
uv run python -m memory_profiler examples/complete_workflow.py
```

### Time Profiling

```bash
# Profile with cProfile
uv run python -m cProfile -o profile.stats examples/complete_workflow.py

# Analyze with snakeviz
uv add --dev snakeviz
uv run snakeviz profile.stats
```

### Benchmark Collection

```bash
# Time full collection
time uv run gapless-crypto-data --symbol BTCUSDT --timeframes 1h --start 2024-01-01 --end 2024-01-31

# Compare CSV vs Parquet output
time uv run gapless-crypto-data --output-format csv ...
time uv run gapless-crypto-data --output-format parquet ...
```

## Documentation Commands

### Generate API Docs

```bash
# Install doc dependencies
uv add --dev pdoc3

# Generate HTML docs
uv run pdoc --html --output-dir docs/api src/gapless_crypto_clickhouse

# Serve docs locally
uv run pdoc --http localhost:8080 src/gapless_crypto_clickhouse
```

### Validate Documentation Links

```bash
# Check for broken links (requires npm/markdown-link-check)
find docs/ -name "*.md" | xargs npx markdown-link-check
```

## Cleanup Commands

### Remove Build Artifacts

```bash
# Remove build directories
rm -rf dist/ build/ *.egg-info/

# Remove pytest cache
rm -rf .pytest_cache/

# Remove ruff cache
rm -rf .ruff_cache/

# Remove mypy cache
rm -rf .mypy_cache/
```

### Remove Virtual Environment

```bash
# Delete virtual environment
rm -rf .venv/

# Recreate from scratch
uv sync --dev
```

### Clear Validation Database

```bash
# Remove validation history
rm ~/.cache/gapless-crypto-data/validation.duckdb

# Verify removal
ls ~/.cache/gapless-crypto-data/
```

## Development Workflow

### Standard Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# ... edit code ...

# 3. Format and lint
uv run ruff format .
uv run ruff check --fix .

# 4. Type check
uv run mypy src/

# 5. Run tests
uv run pytest -v

# 6. Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat: add my feature"

# 7. Push and create PR
git push origin feature/my-feature
```

### Pre-commit Checklist

Before committing, ensure:

- [ ] Code formatted: `uv run ruff format .`
- [ ] Linting passes: `uv run ruff check .`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] All tests pass: `uv run pytest`
- [ ] Encoding valid: `find src/ tests/ -name "*.py" | xargs file --mime-encoding`
- [ ] Documentation updated (if API changed)

### Pre-PR Checklist

Before creating pull request:

- [ ] All CI checks pass locally
- [ ] New tests added for new features
- [ ] Coverage maintained (85%+ for SDK entry points)
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Version bumped in `__init__.py` (if applicable)

## SLOs (Service Level Objectives)

### Correctness

- **Zero ruff violations**: All code passes `ruff check`
- **Zero type errors**: All code passes `mypy --strict` for SDK entry points
- **100% test pass rate**: All tests must pass before merge

### Observability

- **Fast feedback**: Local checks complete in <1 minute
- **CI feedback**: Full CI pipeline completes in <5 minutes
- **Clear errors**: Failed checks provide actionable error messages

### Maintainability

- **Standard tools**: ruff, mypy, pytest (no custom tooling)
- **Single source of truth**: pyproject.toml for all tool configuration
- **Reproducible**: uv.lock ensures consistent dependency versions

## Related Documentation

- **Development Setup**: [SETUP.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/development/SETUP.md)
- **SDK Quality Standards**: [docs/sdk-quality-standards.yaml](/Users/terryli/eon/gapless-crypto-clickhouse/docs/sdk-quality-standards.yaml)
- **Architecture Overview**: [docs/architecture/OVERVIEW.md](/Users/terryli/eon/gapless-crypto-clickhouse/docs/architecture/OVERVIEW.md)
