---
status: accepted
date: 2025-12-27
decision-maker: Terry Li
consulted:
  [
    Explore Agent (cc-skills),
    Explore Agent (Python patterns),
    Explore Agent (version config),
  ]
research-method: multi-agent-parallel
clarification-iterations: 3
perspectives: [Maintainability, Developer Experience, Standards Compliance]
---

# Use importlib.metadata for Python Version Management

**Design Spec**: [Implementation Spec](/docs/design/2025-12-27-importlib-metadata-version-management/spec.md)

## Context and Problem Statement

The `__version__` string in `src/gapless_crypto_clickhouse/__init__.py` is hardcoded and drifts from `pyproject.toml` because semantic-release only updates `pyproject.toml` and `package.json`, not `__init__.py`.

This creates version inconsistency where:

- `pyproject.toml` shows correct version (updated by semantic-release)
- `package.json` shows correct version (updated by semantic-release)
- `__init__.py.__version__` shows stale version (never updated)

### Before: Triple Version Sources (Drift Risk)

```
        ⏮️ Before: Triple Version Sources (Drift Risk)

┌──────────────────┐     ┌⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯┐
│   __init__.py    │     ⋮    Runtime     ⋮
│   ✗ Hardcoded    │ ──> ⋮  __version__   ⋮
└──────────────────┘     └⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯⋯┘
┌──────────────────┐     ┌────────────────┐     ┌─────────────┐
│ semantic-release │     │ pyproject.toml │     │ Wheel Build │
│                  │ ──> │   ✓ Updated    │ ──> │             │
└──────────────────┘     └────────────────┘     └─────────────┘
  │
  │
  ∨
┌──────────────────┐
│   package.json   │
│    ✓ Updated     │
└──────────────────┘
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏮️ Before: Triple Version Sources (Drift Risk)"; flow: east; }
[ semantic-release ] -> [ pyproject.toml\n✓ Updated ] -> [ Wheel Build ]
[ semantic-release ] -> [ package.json\n✓ Updated ]
[ __init__.py\n✗ Hardcoded ] -> [ Runtime\n__version__ ] { border: dotted; }
```

</details>

### After: Single Source of Truth (No Drift)

```
⏭️ After: Single Source of Truth (No Drift)

┌──────────────────┐     ┏━━━━━━━━━━━━━━━━┓     ┌─────────────┐     ┌──────────┐     ┌────────────────────┐     ╔═════════════╗
│ semantic-release │     ┃ pyproject.toml ┃     │ Wheel Build │     │ PKG-INFO │     │ importlib.metadata │     ║ __version__ ║
│                  │ ──> ┃     (SSoT)     ┃ ──> │             │ ──> │ metadata │ ──> │                    │ ──> ║ at runtime  ║
└──────────────────┘     ┗━━━━━━━━━━━━━━━━┛     └─────────────┘     └──────────┘     └────────────────────┘     ╚═════════════╝
  │
  │
  ∨
┌──────────────────┐
│   package.json   │
└──────────────────┘
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏭️ After: Single Source of Truth (No Drift)"; flow: east; }
[ semantic-release ] -> [ pyproject.toml\n(SSoT) ] { border: bold; } -> [ Wheel Build ]
[ semantic-release ] -> [ package.json ]
[ Wheel Build ] -> [ PKG-INFO\nmetadata ]
[ PKG-INFO\nmetadata ] -> [ importlib.metadata ]
[ importlib.metadata ] -> [ __version__\nat runtime ] { border: double; }
```

</details>

## Decision Drivers

- **Single Source of Truth**: Version should be defined in exactly one place
- **Automation Compatibility**: Must work with semantic-release workflow
- **Development Experience**: Must work in editable installs (`uv pip install -e .`)
- **Standards Compliance**: Follow PEP 517/518/621 and cc-skills recommendations

## Considered Options

1. **importlib.metadata** - Read version from package metadata at runtime
2. **Add **init**.py to sed prepareCmd** - Update hardcoded version during release
3. **Dynamic versioning (setuptools-scm)** - Generate version from git tags at build time

## Decision Outcome

**Chosen Option**: "importlib.metadata" because it provides true single source of truth without requiring additional release automation.

### Consequences

**Good**:

- Version defined only in `pyproject.toml`
- No version drift possible after releases
- No additional sed commands in `.releaserc.json`
- Aligns with cc-skills semantic-release skill recommendation
- Modern Python standard (Python 3.8+)

**Neutral**:

- Requires fallback for development installs without metadata

**Bad**:

- Package must be installed for version to be accessible (not just imported from source)

## Architecture

```
       🏗️ Version Resolution Architecture

       ┏━━━━━━━━━━━━━━━━━━━━┓
       ┃   pyproject.toml   ┃
       ┃       (SSoT)       ┃
       ┗━━━━━━━━━━━━━━━━━━━━┛
         │
         │
         ∨
       ┌────────────────────┐
       │      uv build      │
       └────────────────────┘
         │
         │
         ∨
       ┌────────────────────┐
       │    .whl package    │
       └────────────────────┘
         │
         │
         ∨
       ┌────────────────────┐
       │      PKG-INFO      │
       │      metadata      │
       └────────────────────┘
         │
         │
         ∨
       ┌────────────────────┐
       │ importlib.metadata │
       │     version()      │
       └────────────────────┘
         │
         │
         ∨
       ╔════════════════════╗
       ║    __version__     ║
       ╚════════════════════╝
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "🏗️ Version Resolution Architecture"; flow: south; }
[ pyproject.toml ] { border: bold; label: "pyproject.toml\n(SSoT)"; }
[ uv build ] { label: "uv build"; }
[ wheel ] { label: ".whl package"; }
[ metadata ] { label: "PKG-INFO\nmetadata"; }
[ importlib ] { label: "importlib.metadata\nversion()"; }
[ runtime ] { border: double; label: "__version__"; }

[ pyproject.toml ] -> [ uv build ] -> [ wheel ] -> [ metadata ]
[ metadata ] -> [ importlib ] -> [ runtime ]
```

</details>

### Version Flow After Change

```
pyproject.toml (SSoT)
        │
        ▼ (semantic-release updates)
   git tag v17.2.0
        │
        ▼ (wheel build includes)
   PKG-INFO metadata
        │
        ▼ (importlib.metadata reads)
   __version__ at runtime
```

## Validation

- Version consistency test validates `__version__` matches `pyproject.toml`
- `gcch --version` displays correct version
- Package import shows correct version

## More Information

- **cc-skills semantic-release skill**: Explicitly recommends `importlib.metadata` pattern
- **PEP 566**: Metadata for Python Software Packages 2.1
- **PEP 621**: Storing project metadata in pyproject.toml
