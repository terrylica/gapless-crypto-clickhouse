# Agent 1: PyPI Publishing Strategy Investigation Report

**Investigation Date**: 2025-11-18  
**Methodology**: DCTL (Dynamic CTL) - 4 TLIs completed iteratively  
**Agent Role**: Publishing Strategy Investigator

## Executive Summary

**Recommendation**: Create **gapless-crypto-clickhouse** as an **INDEPENDENT PyPI package** (NOT a namespace package or dependency).

**Rationale**: ClickHouse code is architecturally separate (1,454 lines), QuestDB is deprecated, and the codebase already follows independent module patterns. This aligns with Python packaging best practices for functionally independent components.

**Version Strategy**: Start at **v1.0.0** (independent versioning lifecycle).

---

## DCTL Investigation Progression

### TLI 1: Package Name Availability & Conventions

**Status**: ✅ COMPLETED

**Findings**:
- **gapless-crypto-clickhouse** is AVAILABLE on PyPI (404 response)
- **gapless-crypto-data** exists at v3.0.0 (local v4.0.0 not published yet)
- Naming follows PyPI conventions (lowercase, hyphens, ASCII-only)
- PEP 423 compliance: "gapless-crypto-*" pattern is valid and obvious

**Evidence**:
```bash
$ curl -s https://pypi.org/pypi/gapless-crypto-clickhouse/json
{"message": "Not Found"}

$ curl -s https://pypi.org/pypi/gapless-crypto-data/json | jq '.info.version'
"3.0.0"
```

**PyPI Naming Best Practices** (PEP 423):
- ✅ Lowercase with hyphens (not underscores)
- ✅ Descriptive and memorable
- ✅ Toplevel package name obvious to project (gapless-crypto-*)
- ✅ No deep hierarchies (Python culture prefers flat)

---

### TLI 2: Package Relationship Strategy & Versioning

**Status**: ✅ COMPLETED

**Findings**:

**ClickHouse Implementation Context** (ADR-0005):
- **Implementation**: v4.0.0 (breaking change from QuestDB)
- **Status**: ClickHouse complete, QuestDB deprecated
- **Architecture**: Completely separate codebases (1,454 lines ClickHouse code)
- **Migration driver**: "Future-proofing - more robust ecosystem, broader adoption"
- **Zero-gap strategy**: Application-level deterministic versioning (different from QuestDB)

**Package Relationship Analysis**:

1. **Independent Package** ✅ RECOMMENDED
   - **Pros**:
     - ClickHouse code is functionally independent (1,454 lines)
     - Separate version lifecycle (v1.0.0 → v2.0.0 independently)
     - Users install only what they need (`pip install gapless-crypto-clickhouse`)
     - Clearer deprecation timeline (gapless-crypto-data v5.0.0 removes QuestDB)
     - Aligns with Python culture: "flat is better than nested"
   - **Cons**:
     - Potential code duplication (collectors, utilities)
     - Two separate repos to maintain
   - **Use Case**: "Functionally independent packages that don't import from each other"

2. **Namespace Package** ❌ NOT RECOMMENDED
   - **Pros**:
     - Unified namespace (gapless_crypto.data, gapless_crypto.clickhouse)
     - Company branding (all packages under `gapless_crypto.*`)
   - **Cons**:
     - Confusing for beginners (PEP 420 namespace semantics)
     - Requires removing `__init__.py` from namespace dirs
     - Overkill for 2-3 packages (better for 10+ packages)
   - **Use Case**: "Large corpus of loosely-related packages from single company"

3. **Dependency Approach** ❌ NOT RECOMMENDED
   - **Pros**:
     - Clear dependency tree (gapless-crypto-clickhouse → gapless-crypto-data)
     - Code reuse via imports
   - **Cons**:
     - Forces QuestDB dependency (deprecated in v4.0.0)
     - Version coupling (breaking changes cascade)
     - Contradicts ADR-0005 migration rationale

**Version Numbering Decision**:
- **Start at v1.0.0** (NOT v4.0.0)
- **Rationale**: Independent package → independent version lifecycle
- **Precedent**: OpenAI's `openai` (v1.x) vs `openai-python-client` (v0.x) were versioned independently

---

### TLI 3: TestPyPI, Publishing Auth, Metadata

**Status**: ✅ COMPLETED

**Findings**:

**Existing Publishing Infrastructure**:
```yaml
# .github/workflows/publish.yml
- Trusted Publishing: ✅ ALREADY CONFIGURED
  - id-token: write (OIDC authentication)
  - Environment: "pypi" (requires manual approval)
  - Sigstore attestations: ✅ ENABLED (default in 2025)
  
- Build Strategy: ✅ BEST PRACTICE
  - Separate build/publish jobs (security isolation)
  - uv build (modern build tool)
  - pypa/gh-action-pypi-publish@release/v1

# .github/workflows/release.yml
- Semantic Release: ✅ AUTOMATED
  - semantic-release@25 (latest)
  - Conventional commits → version bump → GitHub release
```

**TestPyPI Strategy**:
- **Recommendation**: Add TestPyPI job BEFORE production PyPI publish
- **OIDC Audience**: `testpypi` (different from production `pypi`)
- **URL**: `repository-url: https://test.pypi.org/legacy/`
- **Use Case**: Validate package installation, dependency resolution, README rendering

**Publishing Authentication** (2025 Best Practices):
- ✅ **Trusted Publishing** (OIDC) - NO API tokens needed
- ✅ **GitHub Environments** - Manual approval gate for production
- ✅ **Sigstore Attestations** - Cryptographic provenance (default in 2025)
- ❌ **API Tokens** - Deprecated (security risk, rotation burden)

**Package Metadata Requirements** (pyproject.toml):

**Required Changes**:
```toml
[project]
name = "gapless-crypto-clickhouse"  # CHANGED from gapless-crypto-data
version = "1.0.0"  # CHANGED from 4.0.0 (independent versioning)
description = "ClickHouse integration for gapless crypto data collection with zero gaps guarantee. Provides high-performance OHLCV ingestion (1.1M rows/sec) and query interface for 400+ trading pairs across 13 timeframes."

keywords = [
    "cryptocurrency", "crypto", "binance", "clickhouse", "ohlcv",
    "trading-data", "time-series", "zero-gaps", "microstructure",
    "high-frequency-data", "database-ingestion", "query-api"
]

classifiers = [
    "Development Status :: 4 - Beta",  # CHANGED (new package, not Production/Stable)
    "Intended Audience :: Developers",
    "Intended Audience :: Financial and Insurance Industry",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Database",  # ADDED (ClickHouse integration)
    "Topic :: Office/Business :: Financial :: Investment",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

dependencies = [
    "clickhouse-driver>=0.2.9",  # KEEP
    "pandas>=2.0.0",              # KEEP
    "pydantic>=2.0.0",            # KEEP
    # REMOVE: duckdb, httpx, python-dotenv (validation/collection not needed)
]

[project.urls]
Homepage = "https://github.com/terrylica/gapless-crypto-clickhouse"
Documentation = "https://github.com/terrylica/gapless-crypto-clickhouse#readme"
Repository = "https://github.com/terrylica/gapless-crypto-clickhouse.git"
Issues = "https://github.com/terrylica/gapless-crypto-clickhouse/issues"
```

**PyPI Configuration** (GitHub repo settings):
1. Navigate to https://pypi.org/manage/account/publishing/
2. Add Trusted Publisher:
   - Package name: `gapless-crypto-clickhouse`
   - Repository: `terrylica/gapless-crypto-clickhouse`
   - Workflow: `publish.yml`
   - Environment: `pypi`

---

### TLI 4: Architectural Decision & File Modifications

**Status**: ✅ COMPLETED

**Findings**:

**ClickHouse Codebase Analysis**:
```
ClickHouse Module Breakdown (1,454 total lines):
- clickhouse/connection.py         239 lines
- clickhouse/config.py             115 lines
- clickhouse/__init__.py            17 lines
- clickhouse_query.py              643 lines
- collectors/clickhouse_bulk_loader.py  440 lines
```

**Architectural Patterns**:
```python
# src/gapless_crypto_data/__init__.py
__version__ = "4.0.0"
__all__ = [
    "fetch_data",  # Function-based API
    "BinancePublicDataCollector",  # Class-based API
    # NO ClickHouse exports (separate module)
]

# src/gapless_crypto_data/__init__.py (L1-76 docstring)
"""
Gapless Crypto Data v4.0.0 - USDT spot market data collection
CLI Removed in v4.0.0: ⚠️ The CLI was removed in v4.0.0. Use Python API.
"""
```

**Package Split Strategy Decision**:

**RECOMMENDATION: Independent Package**

**Evidence**:
1. **Functional Independence** ✅
   - ClickHouse module doesn't import from gapless-crypto-data core
   - Self-contained: connection, config, query, bulk_loader
   - Zero coupling to QuestDB (completely separate)

2. **Python Community Precedent** ✅
   - `requests` vs `requests-oauthlib` (independent)
   - `django` vs `django-rest-framework` (independent)
   - `sqlalchemy` vs `sqlalchemy-clickhouse` (independent)

3. **User Experience** ✅
   - Install only what you need: `pip install gapless-crypto-clickhouse`
   - Clear deprecation path: v5.0.0 removes QuestDB from gapless-crypto-data
   - Version independence: ClickHouse v1.0.0 → v2.0.0 without forcing gapless-crypto-data upgrade

4. **Namespace Package Overkill** ❌
   - PEP 420 adds complexity ("confusing for beginners")
   - Better for 10+ packages (not 2)
   - Python culture: "flat is better than nested"

**Files Requiring Modification** (for new repo):

**Core Package Structure**:
```
gapless-crypto-clickhouse/
├── pyproject.toml                    # NEW (metadata changes)
├── README.md                         # NEW (ClickHouse-specific docs)
├── CHANGELOG.md                      # NEW (v1.0.0 initial release)
├── src/gapless_crypto_clickhouse/
│   ├── __init__.py                   # MODIFIED (version, exports)
│   ├── clickhouse/
│   │   ├── __init__.py              # COPY from gapless-crypto-data
│   │   ├── connection.py            # COPY
│   │   ├── config.py                # COPY
│   │   └── schema.sql               # COPY
│   ├── clickhouse_query.py          # COPY
│   └── collectors/
│       └── clickhouse_bulk_loader.py # COPY
├── tests/                            # NEW (ClickHouse-specific tests)
├── .github/workflows/
│   ├── publish.yml                   # MODIFIED (package name)
│   └── release.yml                   # MODIFIED (semantic-release config)
└── docker-compose.yml                # COPY (ClickHouse container)
```

**Metadata Files**:
1. **pyproject.toml**: All fields (name, version, description, keywords, dependencies, URLs)
2. **README.md**: ClickHouse-specific usage, installation, examples
3. **CHANGELOG.md**: v1.0.0 initial release notes
4. **.github/workflows/publish.yml**: Package name in Trusted Publisher config
5. **.github/workflows/release.yml**: Repository-specific semantic-release config

**Code Files** (minimal changes):
1. **src/gapless_crypto_clickhouse/__init__.py**:
   - Update version to `1.0.0`
   - Update docstring (ClickHouse focus)
   - Export ClickHouse classes only

2. **All Python files**: Update imports from `gapless_crypto_data` → `gapless_crypto_clickhouse`

**Documentation**:
1. **README.md**: Installation, quick start, API reference, deployment
2. **docs/CLICKHOUSE_MIGRATION.md**: Adapt from gapless-crypto-data/docs
3. **ADR-0005**: Copy to new repo for context

---

## Final Recommendations

### Publishing Strategy

**Package Structure**:
```
PyPI Packages:
├── gapless-crypto-data (v3.0.0 → v4.0.0 → v5.0.0)
│   ├── QuestDB implementation (deprecated v4.0.0, removed v5.0.0)
│   └── Core collection utilities
└── gapless-crypto-clickhouse (v1.0.0 → ...)
    └── ClickHouse implementation (NEW, independent)
```

**Version Strategy**:
- **gapless-crypto-clickhouse**: Start at v1.0.0 (independent lifecycle)
- **Semantic versioning**: MAJOR.MINOR.PATCH
- **Breaking changes**: Increment MAJOR (v1.0.0 → v2.0.0)

**TestPyPI Workflow**:
1. Publish to TestPyPI first: `repository-url: https://test.pypi.org/legacy/`
2. Test installation: `pip install -i https://test.pypi.org/simple/ gapless-crypto-clickhouse`
3. Validate: README rendering, dependency resolution, import success
4. Publish to production PyPI after validation

**Trusted Publishing Setup**:
1. Create GitHub repo: `terrylica/gapless-crypto-clickhouse`
2. Configure PyPI Trusted Publisher:
   - Package: `gapless-crypto-clickhouse`
   - Repo: `terrylica/gapless-crypto-clickhouse`
   - Workflow: `publish.yml`
   - Environment: `pypi`
3. Configure TestPyPI Trusted Publisher (same steps, different URL)

### Ambiguities Requiring User Clarification

**Question 1**: Should gapless-crypto-clickhouse depend on gapless-crypto-data for shared utilities?
- **Option A**: Independent (copy utilities, no dependency)
- **Option B**: Dependency (reuse collectors, validation modules)
- **Recommendation**: Option A (aligns with independent package strategy)

**Question 2**: Repository structure for new package?
- **Option A**: New GitHub repo (`terrylica/gapless-crypto-clickhouse`)
- **Option B**: Monorepo with separate PyPI packages
- **Recommendation**: Option A (simpler Trusted Publishing, independent CI/CD)

**Question 3**: Deprecation timeline for gapless-crypto-data QuestDB code?
- **Current**: v4.0.0 deprecates, v5.0.0 removes
- **Impact**: Users should migrate to gapless-crypto-clickhouse before v5.0.0
- **Documentation**: Migration guide needed in both packages

### Next Steps (Suggested)

1. **Immediate** (Agent 2/3/4 tasks):
   - Agent 2: Package structure and dependency analysis
   - Agent 3: Code extraction and import path updates
   - Agent 4: Documentation and publishing workflow

2. **Pre-Publishing**:
   - Create new GitHub repo: `terrylica/gapless-crypto-clickhouse`
   - Copy ClickHouse code (1,454 lines) with import updates
   - Configure Trusted Publishing on PyPI + TestPyPI

3. **Publishing**:
   - Test on TestPyPI first
   - Validate installation and imports
   - Publish to production PyPI
   - Tag v1.0.0 release

4. **Post-Publishing**:
   - Update gapless-crypto-data README (link to clickhouse package)
   - Add deprecation warnings in v4.0.0
   - Publish v5.0.0 (remove QuestDB code)

---

## References

**PyPI/TestPyPI**:
- PEP 423: Naming conventions - https://peps.python.org/pep-0423/
- Trusted Publishing - https://docs.pypi.org/trusted-publishers/
- pypa/gh-action-pypi-publish - https://github.com/pypa/gh-action-pypi-publish

**Package Splitting**:
- Namespace Packages (PEP 420) - https://packaging.python.org/en/latest/guides/packaging-namespace-packages/
- When to split packages - https://py-pkgs.org/04-package-structure.html

**Versioning**:
- Semantic Versioning - https://semver.org/
- Python versioning spec - https://packaging.python.org/en/latest/discussions/versioning/

**Existing Infrastructure**:
- ADR-0005: ClickHouse Migration - `/Users/terryli/eon/gapless-crypto-data/docs/decisions/0005-clickhouse-migration.md`
- Publish workflow - `/Users/terryli/eon/gapless-crypto-data/.github/workflows/publish.yml`
- Release workflow - `/Users/terryli/eon/gapless-crypto-data/.github/workflows/release.yml`
