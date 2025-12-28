---
title: Python Version Management with importlib.metadata
adr: 2025-12-27-importlib-metadata-version-management
created: 2025-12-27
status: accepted
---

# Python Version Management with importlib.metadata

**ADR**: [Use importlib.metadata for Python Version Management](/docs/adr/2025-12-27-importlib-metadata-version-management.md)

---

## Problem Statement

`__version__` in `__init__.py` is hardcoded and drifts from `pyproject.toml` because semantic-release doesn't update it. Need single source of truth.

---

## Decision Summary

| Choice           | Selected Option                                         |
| ---------------- | ------------------------------------------------------- |
| Version approach | **importlib.metadata** (single source of truth)         |
| cc-skills update | **Yes** - add Python guidance to semantic-release skill |
| Consistency test | **Yes** - validate versions match                       |

---

## Current Problem

```
semantic-release runs
    ├─ Updates pyproject.toml ✅ (via sed)
    ├─ Updates package.json ✅ (via sed)
    └─ __init__.py unchanged ❌ (hardcoded "17.1.0")
```

**Result**: `__version__` drifts from actual release version.

---

## Solution: importlib.metadata Pattern

Replace hardcoded version with runtime discovery:

```python
# Before (hardcoded - BAD)
__version__ = "17.1.0"

# After (dynamic - GOOD)
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("gapless-crypto-clickhouse")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"  # Fallback for editable installs
```

**Benefits**:

- Single source of truth: `pyproject.toml`
- No more version drift
- No sed commands needed for `__init__.py`
- Aligns with cc-skills semantic-release skill recommendation

---

## Implementation Plan

### Phase 1: Update gapless-crypto-clickhouse

#### 1.1 Modify `__init__.py` (lines 84-86)

**File**: `src/gapless_crypto_clickhouse/__init__.py`

```python
# Replace:
__version__ = "17.1.0"

# With:
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("gapless-crypto-clickhouse")
except PackageNotFoundError:
    # Development mode or editable install without metadata
    __version__ = "0.0.0+dev"
```

#### 1.2 Add Version Consistency Test

**File**: `tests/test_version_consistency.py` (new file)

```python
"""Test version consistency across all sources."""
import json
import tomllib
from pathlib import Path

import gapless_crypto_clickhouse


def test_version_matches_pyproject():
    """Ensure __version__ matches pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    pyproject_version = pyproject["project"]["version"]
    package_version = gapless_crypto_clickhouse.__version__

    # Skip check for development installs
    if package_version == "0.0.0+dev":
        return

    assert package_version == pyproject_version, \
        f"__version__ ({package_version}) != pyproject.toml ({pyproject_version})"


def test_version_matches_package_json():
    """Ensure __version__ matches package.json."""
    package_json_path = Path(__file__).parent.parent / "package.json"
    with open(package_json_path) as f:
        package_json = json.load(f)

    package_json_version = package_json["version"]
    package_version = gapless_crypto_clickhouse.__version__

    # Skip check for development installs
    if package_version == "0.0.0+dev":
        return

    assert package_version == package_json_version, \
        f"__version__ ({package_version}) != package.json ({package_json_version})"
```

#### 1.3 Simplify `.releaserc.json`

**File**: `.releaserc.json`

Remove `__init__.py` from any future consideration (it's no longer needed):

```json
// prepareCmd stays the same (only updates pyproject.toml and package.json)
// No changes needed - __init__.py now reads from metadata
```

### Phase 2: Update cc-skills semantic-release Skill

#### 2.1 Add Python Version Guidance

**File**: `~/eon/cc-skills/plugins/itp/skills/semantic-release/references/python-projects-nodejs-semantic-release.md`

Add section:

```markdown
## Runtime Version Access (Python)

### Recommended: importlib.metadata

Use `importlib.metadata` to read version from package metadata at runtime:

\`\`\`python

# **init**.py

from importlib.metadata import version, PackageNotFoundError

try:
**version** = version("your-package-name")
except PackageNotFoundError:
**version** = "0.0.0+dev" # Development fallback
\`\`\`

### Anti-pattern: Hardcoded Version

**Do NOT use hardcoded version strings:**

\`\`\`python

# ❌ BAD - requires manual sync with pyproject.toml

**version** = "1.2.3"
\`\`\`

This creates version drift because semantic-release updates `pyproject.toml`
but not `__init__.py`.
```

#### 2.2 Update SKILL.md

**File**: `~/eon/cc-skills/plugins/itp/skills/semantic-release/SKILL.md`

Add to "Python Projects" section:

```markdown
### Python `__version__` Pattern

**Always use `importlib.metadata`** - never hardcode version strings:

\`\`\`python
from importlib.metadata import version, PackageNotFoundError

try:
**version** = version("package-name")
except PackageNotFoundError:
**version** = "0.0.0+dev"
\`\`\`

This reads from `pyproject.toml` at runtime, ensuring single source of truth.
```

---

## Files to Modify

| File                                                             | Change                                                    |
| ---------------------------------------------------------------- | --------------------------------------------------------- |
| `src/gapless_crypto_clickhouse/__init__.py`                      | Replace hardcoded `__version__` with `importlib.metadata` |
| `tests/test_version_consistency.py`                              | New file - version consistency tests                      |
| `~/eon/cc-skills/.../python-projects-nodejs-semantic-release.md` | Add `importlib.metadata` guidance                         |
| `~/eon/cc-skills/.../SKILL.md`                                   | Add Python `__version__` pattern                          |
| `docs/adr/2025-12-27-importlib-metadata-version-management.md`   | New ADR                                                   |

---

## Verification Steps

1. Run `uv pip install -e .` to install in editable mode
2. Verify `python -c "import gapless_crypto_clickhouse; print(gapless_crypto_clickhouse.__version__)"` outputs correct version
3. Run `uv run pytest tests/test_version_consistency.py -v`
4. Verify `gcch --version` shows correct version

---

## Success Criteria

1. `__version__` reads from `pyproject.toml` at runtime via `importlib.metadata`
2. Version consistency test passes
3. cc-skills semantic-release skill updated with Python guidance
4. ADR documents the architectural decision
5. No more version drift after releases
