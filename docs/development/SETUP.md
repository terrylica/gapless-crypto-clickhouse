---
version: "1.0.0"
last_updated: "2025-10-27"
canonical_source: true
supersedes: []
---

# Development Environment Setup

## Purpose

Complete guide to setting up a local development environment for gapless-crypto-data contributions.

## Prerequisites

### Required Tools

**Python**: 3.9+ (3.12+ recommended for latest features)

**uv**: Fast Python package manager and project manager

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via Homebrew
brew install uv
```

**Git**: Version control

```bash
# Verify installation
git --version
```

### Optional Tools

**Docker + Colima**: For containerized testing (optional)

```bash
brew install colima docker
colima start
```

## Initial Setup

### Clone Repository

```bash
git clone https://github.com/terrylica/gapless-crypto-data.git
cd gapless-crypto-data
```

### Install Dependencies

```bash
# Install all dependencies including dev dependencies
uv sync --dev
```

**What this does**:

- Creates `.venv/` virtual environment
- Installs production dependencies
- Installs development dependencies (pytest, ruff, mypy, etc.)
- Sets up pre-commit hooks (if configured)

### Virtual Environment Activation

**Using `uv run` (Recommended)**:

```bash
# Run commands directly without activation
uv run pytest
uv run gapless-crypto-data --help
uv run python examples/simple_api_examples.py
```

**Manual activation (Optional)**:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Then run commands directly
pytest
gapless-crypto-data --help
```

**Note**: `uv run` automatically uses the virtual environment, no activation needed.

## Verify Installation

### Run Tests

```bash
# Run full test suite
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_binance_collector.py -v
```

**Expected**: All tests pass (30+ tests)

### Test CLI

```bash
# Verify CLI is installed
uv run gapless-crypto-data --help

# Test basic collection (uses sample data)
uv run gapless-crypto-data --symbol SOLUSDT --timeframes 1h --start 2024-01-01 --end 2024-01-02
```

**Expected**: CLI help output, sample data collection succeeds

### Test Package Installation

```bash
# Build package
uv build

# Test local installation
uv tool install --editable .

# Verify installed CLI
gapless-crypto-data --version
```

**Expected**: Package builds successfully, CLI accessible globally

## Development Tools

### Code Formatting (Ruff)

```bash
# Format all code
uv run ruff format .

# Check formatting without changes
uv run ruff format --check .
```

**Standard**: Ruff default formatting (PEP 8 compatible)

### Linting (Ruff)

```bash
# Lint and auto-fix issues
uv run ruff check --fix .

# Lint without auto-fix
uv run ruff check .

# Lint specific file
uv run ruff check src/gapless_crypto_data/collectors/binance_public_data_collector.py
```

**Rules**: Ruff default ruleset (includes pycodestyle, pyflakes, isort)

### Type Checking (mypy)

```bash
# Type check entire codebase
uv run mypy src/

# Type check specific module
uv run mypy src/gapless_crypto_data/validation/
```

**Standard**: PEP 561 compliance via `py.typed` marker

### File Encoding Validation

Required for CI to pass:

```bash
# Validate all Python and Markdown files are UTF-8
find src/ tests/ examples/ -name "*.py" -o -name "*.md" | xargs file --mime-encoding
```

**Expected**: All files report `us-ascii` or `utf-8`

## Configuration Files

### `pyproject.toml`

Main project configuration:

- Package metadata (name, version, dependencies)
- Build system configuration (Hatchling)
- Tool configurations (ruff, mypy, pytest)

**Location**: `/Users/terryli/eon/gapless-crypto-data/pyproject.toml`

### `.python-version`

Python version specification for `uv`:

```
3.12
```

**Effect**: `uv` automatically uses Python 3.12 for this project

### `uv.lock`

Dependency lock file (auto-generated):

- Pinned versions for reproducible builds
- Do not edit manually
- Regenerate with `uv sync`

## Testing Configuration

### pytest Settings

**Location**: `pyproject.toml` → `[tool.pytest.ini_options]`

**Key settings**:

- Test discovery: `tests/` directory
- Markers: `@pytest.mark.integration`, `@pytest.mark.unit`
- Coverage: Enabled for `src/gapless_crypto_data/`

### Sample Data

**Location**: `/Users/terryli/eon/gapless-crypto-data/src/gapless_crypto_data/sample_data/`

**Purpose**: Real data files for end-to-end tests

- SOLUSDT data (multiple timeframes)
- Used by `tests/test_validation_storage.py`
- Committed to repository for reproducible tests

## Environment Variables

### Optional Configuration

**Data Collection**:

- `BINANCE_API_KEY` - Not required (public data)
- `OUTPUT_DIR` - Override default output directory

**Testing**:

- `PYTEST_MARKERS` - Filter tests by marker (`unit`, `integration`)

**Cache**:

- `XDG_CACHE_HOME` - Override XDG cache directory (default: `~/.cache/`)

### Validation Database

**Location**: `~/.cache/gapless-crypto-data/validation.duckdb`

**Behavior**:

- Auto-created on first validation with `store_report=True`
- Persistent across sessions
- Clear for fresh start: `rm ~/.cache/gapless-crypto-data/validation.duckdb`

## IDE Setup

### VS Code

**Recommended Extensions**:

- Python (Microsoft)
- Pylance
- Ruff

**Settings** (`.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "ruff.enable": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

### PyCharm

**Project Interpreter**:

1. File → Settings → Project → Python Interpreter
2. Select `.venv/bin/python`

**External Tools**:

- Add `uv run pytest` as test runner
- Add `uv run ruff format` as formatter

## Common Issues

### Issue: `uv: command not found`

**Solution**: Install `uv` via curl or Homebrew (see Prerequisites)

### Issue: Tests fail with `ModuleNotFoundError`

**Solution**: Reinstall dependencies

```bash
uv sync --dev --reinstall
```

### Issue: Virtual environment corrupted

**Solution**: Delete and recreate

```bash
rm -rf .venv
uv sync --dev
```

### Issue: Pre-commit hooks fail

**Solution**: Install hooks

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

## SLOs (Service Level Objectives)

### Correctness

- **All tests pass**: 100% pass rate required for commits
- **Type safety**: mypy strict mode for SDK entry points
- **Linting**: Zero ruff violations for new code

### Observability

- **Test coverage**: 85%+ for SDK entry points, 70%+ for core engines
- **CI feedback**: All checks pass before merge
- **Clear error messages**: Setup issues provide actionable guidance

### Maintainability

- **Reproducible builds**: `uv.lock` ensures consistent dependencies
- **Standard tools**: ruff, mypy, pytest (no custom tooling)
- **Fast setup**: `uv sync --dev` completes in <30 seconds

## Related Documentation

- **Development Commands**: [COMMANDS.md](/Users/terryli/eon/gapless-crypto-data/docs/development/COMMANDS.md)
- **CLI Migration Guide**: [CLI_MIGRATION_GUIDE.md](/Users/terryli/eon/gapless-crypto-data/docs/development/CLI_MIGRATION_GUIDE.md) (planned)
- **Publishing Guide**: [PUBLISHING.md](/Users/terryli/eon/gapless-crypto-data/docs/development/PUBLISHING.md) (planned)
- **SDK Quality Standards**: [docs/sdk-quality-standards.yaml](/Users/terryli/eon/gapless-crypto-data/docs/sdk-quality-standards.yaml)
