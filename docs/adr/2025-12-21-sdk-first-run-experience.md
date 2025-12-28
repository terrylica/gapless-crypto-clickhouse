---
status: accepted
date: 2025-12-21
decision-maker: Terry Li
consulted: [Alpha-Forge User, PyPI Package Consumers]
research-method: multi-agent
clarification-iterations: 2
perspectives: [Developer Experience, SDK Design, Error Handling, CLI Patterns]
---

# SDK First-Run Experience Improvement

**Design Spec**: [Implementation Spec](/docs/design/2025-12-21-sdk-first-run-experience/spec.md)

## Context and Problem Statement

Downstream package consumers (e.g., alpha-forge) experience significant friction when first integrating `gapless-crypto-clickhouse`. A real-world integration session revealed 7 distinct friction points requiring ~50 lines of manual workaround code and ~1 hour of debugging time.

The core issues are:

1. **Schema not auto-created** - Users must manually extract `schema.sql` from package internals
2. **No CLI for setup** - Package explicitly states "No CLI - machine interface only"
3. **Connection errors unhelpful** - Generic urllib3 errors with no actionable guidance
4. **Gap filling timezone bug** - REST API fails on non-UTC systems (fixed in HEAD, unreleased)
5. **No unified setup check** - Must call multiple probe functions manually

### Before: First-Time User Experience

```
 ⏮️ Before: First-Time User Experience

      ╭─────────────────────────╮
      │          User           │
      ╰─────────────────────────╯
        │
        │
        ∨
      ┌─────────────────────────┐
      │      query_ohlcv()      │
      └─────────────────────────┘
        │
        │ fails
        ∨
      ╔═════════════════════════╗
      ║  SchemaValidationError  ║
      ║ Table 'ohlcv' not found ║
      ╚═════════════════════════╝
        │
        │
        ∨
      ╭─────────────────────────╮
      │       User Stuck        │
      │   (~1 hour debugging)   │
      ╰─────────────────────────╯
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏮️ Before: First-Time User Experience"; flow: south; }
[ User ] { shape: rounded; }
[ query_ohlcv() ]
[ SchemaValidationError\nTable 'ohlcv' not found ] { border: double; }
[ User Stuck\n(~1 hour debugging) ] { shape: rounded; }

[ User ] -> [ query_ohlcv() ]
[ query_ohlcv() ] -- fails --> [ SchemaValidationError\nTable 'ohlcv' not found ]
[ SchemaValidationError\nTable 'ohlcv' not found ] -> [ User Stuck\n(~1 hour debugging) ]
```

</details>

### After: First-Time User Experience

```
⏭️ After: First-Time User Experience

   ╭──────────────────────╮
   │         User         │
   ╰──────────────────────╯
     │
     │
     ∨
   ┌──────────────────────┐
   │    query_ohlcv()     │
   └──────────────────────┘
     │
     │
     ∨
   ┌──────────────────────┐
   │     __enter__()      │
   └──────────────────────┘
     │
     │
     ∨
   ┌──────────────────────┐
   │   _table_exists()?   │ ─┐
   └──────────────────────┘  │
     │                       │
     │ No                    │
     ∨                       │
   ┌──────────────────────┐  │
   │ [+] ensure_schema()  │  │ Yes
   └──────────────────────┘  │
     │                       │
     │                       │
     ∨                       │
   ┌──────────────────────┐  │
   │  Schema Validation   │ <┘
   └──────────────────────┘
     │
     │
     ∨
   ┌──────────────────────┐
   │ Auto-Ingest from CDN │
   └──────────────────────┘
     │
     │
     ∨
    ══════════════════════
   ║       Success        ║
   ║    (<2 min total)    ║
    ══════════════════════
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "⏭️ After: First-Time User Experience"; flow: south; }
[ User ] { shape: rounded; }
[ query_ohlcv() ]
[ __enter__() ]
[ _table_exists()? ]
[ ensure_schema() ] { label: "[+] ensure_schema()"; }
[ Schema Validation ]
[ Auto-Ingest from CDN ]
[ Success\n(<2 min total) ] { shape: rounded; border: double; }

[ User ] -> [ query_ohlcv() ]
[ query_ohlcv() ] -> [ __enter__() ]
[ __enter__() ] -> [ _table_exists()? ]
[ _table_exists()? ] -- No --> [ ensure_schema() ]
[ ensure_schema() ] -> [ Schema Validation ]
[ _table_exists()? ] -- Yes --> [ Schema Validation ]
[ Schema Validation ] -> [ Auto-Ingest from CDN ]
[ Auto-Ingest from CDN ] -> [ Success\n(<2 min total) ]
```

</details>

## Decision Drivers

- **Consumer friction**: ~1 hour debugging for first-time users is unacceptable
- **SDK quality standards**: Package should "just work" without manual setup
- **AI agent compatibility**: probe module exists but isn't surfaced on errors
- **Downstream dependencies**: alpha-forge and similar packages need seamless integration

## Considered Options

1. **Auto-schema creation + CLI + improved errors** (recommended)
2. **Documentation-only improvements** (insufficient)
3. **Breaking API changes with required init()** (too disruptive)

## Decision Outcome

Chosen option: **Option 1 - Auto-schema creation + CLI + improved errors**

Implement three P0 changes for v17.1.0:

1. **Auto-schema creation**: Add `ensure_schema()` method, auto-create table in `__enter__()` if missing
2. **CLI commands**: Add `gcch init`, `gcch status`, `gcch check` commands
3. **Improved errors**: Wrap connection errors with probe module guidance

### Consequences

**Good**:

- Zero workaround code required for new users
- Time to first successful query: ~1 hour → <2 minutes
- Existing users unaffected (auto-create is additive)

**Bad**:

- New dependency: `click>=8.0.0` for CLI
- Slightly larger package size

**Neutral**:

- CLI commands are optional (Python API still works without them)

## Architecture

```
                                                                         🏗️ SDK Architecture with First-Run Improvements


  ┌─────────────────────┐
  │                     │
  │                     │
  │                ┌────┼──────────────────────────────────────────────┐
  ∨                │    │                                              ∨
┌───────────────┐  │  ╭──────────────╮     ┌───────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐  missing   ┌─────────────────────┐     ┌────────────┐     ╔════════════╗
│ query_ohlcv() │ ─┘  │  User Code   │ ──> │ [+] check_setup() │ ──> │ ClickHouseConnection │ ──> │ [+] _table_exists() │ ─────────> │ [+] ensure_schema() │ ──> │ schema.sql │ ──> ║ ClickHouse ║
└───────────────┘     ╰──────────────╯     └───────────────────┘     └──────────────────────┘     └─────────────────────┘            └─────────────────────┘     └────────────┘     ╚════════════╝
                        │                                              ∧                            │                                                                                 ∧
                        │                                              │                            │ exists                                                                          │
                        ∨                                              │                            ∨                                                                                 │
                      ┌──────────────┐                                 │                          ┌─────────────────────┐                                                             │
                      │ [+] gcch CLI │ ────────────────────────────────┘                          │   SchemaValidator   │ ────────────────────────────────────────────────────────────┘
                      └──────────────┘                                                            └─────────────────────┘
```

<details>
<summary>graph-easy source</summary>

```
graph { label: "🏗️ SDK Architecture with First-Run Improvements"; flow: east; }
[ User Code ] { shape: rounded; }
[ gcch CLI\n(init/status/check) ] { label: "[+] gcch CLI"; }
[ check_setup() ] { label: "[+] check_setup()"; }
[ query_ohlcv() ]
[ ClickHouseConnection ]
[ _table_exists() ] { label: "[+] _table_exists()"; }
[ ensure_schema() ] { label: "[+] ensure_schema()"; }
[ schema.sql ]
[ SchemaValidator ]
[ ClickHouse ] { border: double; }

[ User Code ] -> [ gcch CLI\n(init/status/check) ]
[ User Code ] -> [ check_setup() ]
[ User Code ] -> [ query_ohlcv() ]
[ gcch CLI\n(init/status/check) ] -> [ ClickHouseConnection ]
[ check_setup() ] -> [ ClickHouseConnection ]
[ query_ohlcv() ] -> [ ClickHouseConnection ]
[ ClickHouseConnection ] -> [ _table_exists() ]
[ _table_exists() ] -- missing --> [ ensure_schema() ]
[ ensure_schema() ] -> [ schema.sql ]
[ schema.sql ] -> [ ClickHouse ]
[ _table_exists() ] -- exists --> [ SchemaValidator ]
[ SchemaValidator ] -> [ ClickHouse ]
```

</details>

### Component Changes

| Component        | Change                                                         | Impact                   |
| ---------------- | -------------------------------------------------------------- | ------------------------ |
| `connection.py`  | Add `_table_exists()`, `ensure_schema()`, modify `__enter__()` | Auto-schema creation     |
| `cli.py`         | New file with Click-based CLI                                  | `gcch init/status/check` |
| `pyproject.toml` | Add script entry point + click dependency                      | CLI availability         |
| `__init__.py`    | Add `check_setup()` function                                   | Unified diagnostics      |
| `README.md`      | Add "First Time? Start Here" section                           | Discoverability          |

### Data Flow

```
First Query (before):
  query_ohlcv() → SchemaValidationError: Table 'ohlcv' not found → USER STUCK

First Query (after):
  query_ohlcv() → __enter__() → _table_exists() = False → ensure_schema() → validation → SUCCESS
```

## Validation

### Success Criteria

- [ ] Fresh ClickHouse install: `gcch init` creates schema without manual SQL
- [ ] `gcch check` returns exit code 0 on healthy system
- [ ] Connection error shows probe module guidance
- [ ] `check_setup()` returns actionable issues dict
- [ ] alpha-forge integration works without workarounds

### Testing Plan

| Test                        | Location                   | Description                     |
| --------------------------- | -------------------------- | ------------------------------- |
| `test_table_exists`         | `tests/test_connection.py` | Verify `_table_exists()` method |
| `test_ensure_schema`        | `tests/test_connection.py` | Verify schema creation          |
| `test_auto_schema_creation` | `tests/test_connection.py` | Verify `__enter__` auto-creates |
| `test_cli_init`             | `tests/test_cli.py`        | Verify `gcch init` command      |
| `test_check_setup`          | `tests/test_api.py`        | Verify `check_setup()` function |

## Decision Log

| Date       | Decision                                      | Rationale                                           |
| ---------- | --------------------------------------------- | --------------------------------------------------- |
| 2025-12-21 | Use Click for CLI                             | Standard Python CLI framework, minimal overhead     |
| 2025-12-21 | Auto-create in `__enter__()` not `__init__()` | Matches existing health_check + validation pattern  |
| 2025-12-21 | Keep `check_setup()` separate from CLI        | Enables programmatic diagnostics without subprocess |

## Related Decisions

- **ADR-0024**: Comprehensive Validation Canonicity (schema validation pattern)
- **ADR-0041**: Gap filling timezone fix (included in this release)
- **ADR-0044**: Local ClickHouse option (dual-mode support)

## More Information

- [Implementation Spec](/docs/design/2025-12-21-sdk-first-run-experience/spec.md)
- [Global Plan](/Users/terryli/.claude/plans/bubbly-tumbling-twilight.md) (ephemeral)
- [Alpha-Forge Integration Feedback](#context-and-problem-statement)
