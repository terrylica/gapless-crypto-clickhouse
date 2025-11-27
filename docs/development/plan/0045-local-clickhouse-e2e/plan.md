# Plan 0045: Local ClickHouse E2E Validation Workflow

**ADR**: [ADR-0045](../../../architecture/decisions/0045-local-clickhouse-e2e-validation.md)

**Status**: Done

**Author**: Claude Code

**Last Updated**: 2025-11-26

---

## Overview

Formalize the "show and tell" demonstration workflow that proves local ClickHouse mode (ADR-0044) works with real Binance data into a reusable, validated pattern.

### Goals

1. Consolidate skill into `local-clickhouse` with executable scripts
2. pytest E2E invokes skill scripts via `subprocess.run()`
3. Capture evidence: screenshots (Playwright) + JSON + query results
4. Fail hard if mise ClickHouse not installed (no skip)

### Non-Goals

- CI integration (mise not available in GitHub Actions)
- Docker containerization (uses native mise installation)
- Earthly target (local-only workflow)

---

## Context

### Problem

ADR-0044 implementation created an ad-hoc "show and tell" workflow:

1. Start mise ClickHouse
2. Deploy schema
3. Ingest real Binance data
4. Visualize in Play UI

This workflow is undocumented and not reproducible.

### Solution

Formalize into:

- **Skill**: Prescriptive scripts in `skills/local-clickhouse/scripts/`
- **pytest E2E**: Invokes scripts, captures evidence
- **Full circle**: Skill contains scripts, pytest invokes them

### Semantic Constants

```python
# Paths
MISE_CLICKHOUSE_SHIM = "~/.local/share/mise/shims/clickhouse"
SKILL_SCRIPTS_DIR = "skills/local-clickhouse/scripts"
SCREENSHOTS_DIR = "tests/screenshots"

# Ports (from ADR-0044)
PORT_LOCAL_HTTP = 8123
PORT_LOCAL_NATIVE = 9000

# Evidence filenames
SCREENSHOT_PATTERN = "play-ui-{timestamp}.png"
VALIDATION_JSON_PATTERN = "validation-{timestamp}.json"
```

---

## Task List

| #   | Task                         | Status | Notes                                         |
| --- | ---------------------------- | ------ | --------------------------------------------- |
| 1   | Create ADR-0045              | Done   | MADR format                                   |
| 2   | Create plan directory        | Done   | Google Design Doc format                      |
| 3   | Rename skill directory       | Done   | `clickhouse-local-setup` → `local-clickhouse` |
| 4   | Create start-clickhouse.sh   | Done   | Uses mise shims path                          |
| 5   | Create deploy-schema.sh      | Done   | Calls existing deploy script                  |
| 6   | Create ingest-sample-data.py | Done   | Uses query_ohlcv()                            |
| 7   | Create take-screenshot.py    | Done   | Playwright + Play UI                          |
| 8   | Create validate-data.py      | Done   | JSON evidence output                          |
| 9   | Update SKILL.md              | Done   | Add E2E workflow section                      |
| 10  | Update pytest E2E            | Done   | Fail hard + subprocess + Playwright           |
| 11  | Update .gitignore            | Done   | Add tests/screenshots/                        |
| 12  | Update CLAUDE.md             | Done   | Update skill reference                        |
| 13  | Run validation               | Done   | 26 config tests pass, all scripts compile     |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    skills/local-clickhouse/                      │
├─────────────────────────────────────────────────────────────────┤
│  SKILL.md (merged + expanded)                                    │
│  scripts/                                                        │
│    ├── start-clickhouse.sh      → mise shims                    │
│    ├── deploy-schema.sh         → calls existing script         │
│    ├── ingest-sample-data.py    → query_ohlcv(auto_ingest=True) │
│    ├── take-screenshot.py       → Playwright Play UI            │
│    └── validate-data.py         → JSON evidence                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ subprocess.run()
┌─────────────────────────────────────────────────────────────────┐
│              tests/test_local_clickhouse_e2e.py                  │
├─────────────────────────────────────────────────────────────────┤
│  • Fail hard if mise ClickHouse not installed (no skip)         │
│  • Invokes skill scripts via subprocess.run()                   │
│  • Playwright screenshot capture                                 │
│  • JSON evidence output                                          │
│  • Output: tests/screenshots/ (gitignored)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Script Invocation Pattern

```python
import subprocess
from pathlib import Path

SKILL_SCRIPTS = Path("skills/local-clickhouse/scripts")

def test_start_clickhouse():
    result = subprocess.run(
        [SKILL_SCRIPTS / "start-clickhouse.sh"],
        capture_output=True,
        timeout=30,
        check=False,  # Handle return code manually
    )
    # Success OR already running
    assert result.returncode == 0 or b"already running" in result.stderr
```

### Fail Hard Pattern

```python
import shutil
import pytest

MISE_CLICKHOUSE = Path.home() / ".local/share/mise/shims/clickhouse"

def pytest_configure(config):
    """Fail hard if mise ClickHouse not available."""
    if not MISE_CLICKHOUSE.exists():
        pytest.exit(
            f"mise ClickHouse required: {MISE_CLICKHOUSE}\n"
            "Install: mise install clickhouse",
            returncode=1,
        )
```

### Evidence Capture

```python
from datetime import datetime
import json

def capture_validation_evidence(results: dict) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path("tests/screenshots") / f"validation-{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, default=str))
    return output_path
```

---

## SLOs

| Metric          | Target                                        |
| --------------- | --------------------------------------------- |
| Availability    | Scripts work on macOS with mise ClickHouse    |
| Correctness     | Real Binance data validates OHLC constraints  |
| Observability   | Screenshots + JSON evidence captured          |
| Maintainability | Scripts in skill, tests invoke via subprocess |

---

## Success Criteria

- [x] Skill renamed to `local-clickhouse`
- [x] 5 scripts created in `scripts/` directory
- [x] pytest E2E fails hard if no mise ClickHouse
- [x] pytest invokes skill scripts via subprocess
- [x] Playwright screenshots saved to `tests/screenshots/`
- [x] JSON validation evidence captured
- [x] All tests pass locally (26 config tests)
- [x] .gitignore updated for screenshots
- [x] CLAUDE.md updated with new skill name
